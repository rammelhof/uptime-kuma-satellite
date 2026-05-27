"""Tests for all monitor implementations."""

import os
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import importlib

import psutil
import pytest

from uptime_kuma_satellite.models import MonitorConfig, MonitorStatus
from uptime_kuma_satellite.monitors import MonitorRegistry
from uptime_kuma_satellite.monitors.uptime import UptimeMonitor


# Track which modules are built-in so we can reload them
_BUILTIN_MODULES = [
    "uptime_kuma_satellite.monitors.file_exists",
    "uptime_kuma_satellite.monitors.file_age",
    "uptime_kuma_satellite.monitors.disk_space",
    "uptime_kuma_satellite.monitors.process",
    "uptime_kuma_satellite.monitors.process_count",
    "uptime_kuma_satellite.monitors.uptime",
    "uptime_kuma_satellite.monitors.service",
    "uptime_kuma_satellite.monitors.cpu_usage",
    "uptime_kuma_satellite.monitors.memory_usage",
    "uptime_kuma_satellite.monitors.load_average",
    "uptime_kuma_satellite.monitors.ping",
    "uptime_kuma_satellite.monitors.log_file",
]


@pytest.fixture(autouse=True)
def fresh_registry():
    """Ensure a clean registry with all built-in monitors."""
    MonitorRegistry.reset()
    # Re-import to re-register (Python caches, so we reload)
    for mod_name in _BUILTIN_MODULES:
        if mod_name in importlib.sys.modules:
            importlib.reload(importlib.import_module(mod_name))
        else:
            importlib.import_module(mod_name)
    yield
    MonitorRegistry.reset()


@pytest.fixture
def tmp_file():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        f.write(b"test content")
        path = f.name
    yield path
    os.unlink(path)


class TestFileExistsMonitor:
    def test_file_exists(self, tmp_file):
        config = MonitorConfig(
            name="test", monitor_type="file_exists",
            params={"path": tmp_file}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        assert result.status == MonitorStatus.UP
        assert tmp_file in result.message

    def test_file_missing(self):
        config = MonitorConfig(
            name="test", monitor_type="file_exists",
            params={"path": "/nonexistent/path/file.txt"}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        assert result.status == MonitorStatus.DOWN
        assert "missing" in result.message.lower()

    def test_missing_params(self):
        config = MonitorConfig(name="test", monitor_type="file_exists", params={})
        with pytest.raises(ValueError, match="Missing 'path'"):
            MonitorRegistry.create(config)


class TestFileAgeMonitor:
    def test_file_fresh(self, tmp_file):
        config = MonitorConfig(
            name="test", monitor_type="file_age",
            params={"path": tmp_file, "max_age_seconds": 3600}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        assert result.status == MonitorStatus.UP

    def test_file_too_old(self, tmp_file):
        # Set mtime to 2 days ago
        old_time = os.path.getmtime(tmp_file) - (2 * 86400)
        os.utime(tmp_file, (old_time, old_time))

        config = MonitorConfig(
            name="test", monitor_type="file_age",
            params={"path": tmp_file, "max_age_seconds": 3600}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        assert result.status == MonitorStatus.DOWN
        assert "too old" in result.message.lower()

    def test_file_missing(self):
        config = MonitorConfig(
            name="test", monitor_type="file_age",
            params={"path": "/nonexistent/file.txt", "max_age_seconds": 3600}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        assert result.status == MonitorStatus.DOWN


class TestDiskSpaceMonitor:
    def test_disk_ok(self):
        config = MonitorConfig(
            name="test", monitor_type="disk_space",
            params={"path": "/", "min_percent": 0.001}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        # Should succeed (we're checking with very low threshold)
        assert result.status in (MonitorStatus.UP, MonitorStatus.DOWN)
        assert "disk" in result.message.lower() or "free" in result.message.lower()

    def test_disk_error_handling(self):
        with patch("psutil.disk_usage", side_effect=OSError("no such file")):
            config = MonitorConfig(
                name="test", monitor_type="disk_space",
                params={"path": "/nonexistent", "min_percent": 10}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.DOWN
            assert "cannot read" in result.message.lower()

    def test_missing_params(self):
        config = MonitorConfig(name="test", monitor_type="disk_space", params={})
        with pytest.raises(ValueError, match="Missing 'path'"):
            MonitorRegistry.create(config)


class TestServiceMonitor:
    def test_unreachable_service(self):
        config = MonitorConfig(
            name="test", monitor_type="service",
            params={"host": "127.0.0.1", "port": 19999, "timeout_seconds": 1}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        assert result.status == MonitorStatus.DOWN

    def test_missing_params(self):
        config = MonitorConfig(name="test", monitor_type="service", params={})
        with pytest.raises(ValueError, match="Missing 'host'"):
            MonitorRegistry.create(config)

    def test_service_timeout(self):
        import socket
        with patch("socket.socket") as mock_socket:
            sock = MagicMock()
            sock.connect.side_effect = socket.timeout("timed out")
            mock_socket.return_value = sock
            config = MonitorConfig(
                name="test", monitor_type="service",
                params={"host": "192.0.2.1", "port": 80, "timeout_seconds": 1}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.DOWN
            assert "unreachable" in result.message.lower()


class TestProcessMonitor:
    def test_process_running(self):
        mock_proc = MagicMock()
        mock_proc.info = {"pid": 1234, "name": "python", "cmdline": ["python3"]}
        mock_proc_iter = MagicMock(return_value=[mock_proc])

        with patch("psutil.process_iter", mock_proc_iter):
            config = MonitorConfig(
                name="test", monitor_type="process",
                params={"name": "python"}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.UP
            assert "1 match" in result.message

    def test_process_not_running(self):
        mock_proc_iter = MagicMock(return_value=[])

        with patch("psutil.process_iter", mock_proc_iter):
            config = MonitorConfig(
                name="test", monitor_type="process",
                params={"name": "nonexistent_xyz"}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.DOWN

    def test_process_by_cmdline(self):
        mock_proc = MagicMock()
        mock_proc.info = {"pid": 999, "name": "node", "cmdline": ["node", "worker.js"]}
        mock_proc_iter = MagicMock(return_value=[mock_proc])

        with patch("psutil.process_iter", mock_proc_iter):
            config = MonitorConfig(
                name="test", monitor_type="process",
                params={"name": "worker.js"}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.UP

    def test_process_access_denied(self):
        """Test process monitor handles AccessDenied gracefully."""
        def iter_with_access_denied(*args, **kwargs):
            mock_proc = MagicMock()
            mock_proc.info = {"pid": 1, "name": "system", "cmdline": ["system"]}
            yield mock_proc
            raise psutil.AccessDenied(pid=1)

        with patch("psutil.process_iter", side_effect=iter_with_access_denied):
            config = MonitorConfig(
                name="test", monitor_type="process",
                params={"name": "system"}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            # AccessDenied from process_iter is caught in outer try/except
            assert result.status == MonitorStatus.DOWN
            assert "error" in result.message.lower()

    def test_missing_params(self):
        config = MonitorConfig(name="test", monitor_type="process", params={})
        with pytest.raises(ValueError, match="Missing 'name'"):
            MonitorRegistry.create(config)


class TestCPUUsageMonitor:
    def test_cpu_check(self):
        config = MonitorConfig(
            name="test", monitor_type="cpu_usage",
            params={"max_percent": 99.9}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        # Should complete without error
        assert result.monitor_type == "cpu_usage"
        assert result.status in (MonitorStatus.UP, MonitorStatus.DOWN)

    def test_high_cpu_threshold(self):
        config = MonitorConfig(
            name="test", monitor_type="cpu_usage",
            params={"max_percent": 0.001}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        assert result.status == MonitorStatus.DOWN

    def test_cpu_per_core_reporting(self):
        def cpu_percent_side_effect(interval=None, percpu=False):
            if percpu:
                return [10.0, 20.0, 30.0]
            return 75.5

        with patch("psutil.cpu_percent", side_effect=cpu_percent_side_effect):
            config = MonitorConfig(
                name="test", monitor_type="cpu_usage",
                params={"max_percent": 50}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.DOWN
            assert "cores" in result.message.lower()
            assert "per-core" in result.message.lower()

    def test_cpu_error_handling(self):
        with patch("psutil.cpu_percent", side_effect=OSError("read error")):
            config = MonitorConfig(
                name="test", monitor_type="cpu_usage",
                params={"max_percent": 90}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.DOWN
            assert "error" in result.message.lower()


class TestMemoryUsageMonitor:
    def test_memory_check(self):
        config = MonitorConfig(
            name="test", monitor_type="memory_usage",
            params={"max_percent": 99.9}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        assert result.monitor_type == "memory_usage"
        assert result.status in (MonitorStatus.UP, MonitorStatus.DOWN)

    def test_memory_swap_in_output(self):
        config = MonitorConfig(
            name="test", monitor_type="memory_usage",
            params={"max_percent": 99.9}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        assert "swap" in result.message.lower()

    def test_memory_error_handling(self):
        with patch("psutil.virtual_memory", side_effect=OSError("read error")):
            config = MonitorConfig(
                name="test", monitor_type="memory_usage",
                params={"max_percent": 90}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.DOWN
            assert "error" in result.message.lower()


class TestLoadAverageMonitor:
    def test_load_check(self):
        config = MonitorConfig(
            name="test", monitor_type="load_average",
            params={"max_load": 999.0}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        assert result.monitor_type == "load_average"
        assert "load average" in result.message.lower()

    def test_high_load_threshold(self):
        config = MonitorConfig(
            name="test", monitor_type="load_average",
            params={"max_load": 0.0}  # Very low threshold
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        # With 0.0 threshold, any load should be DOWN
        assert result.status == MonitorStatus.DOWN

    def test_load_per_core_reporting(self):
        with patch("psutil.getloadavg", return_value=(2.5, 2.0, 1.8)):
            with patch("psutil.cpu_count", return_value=4):
                config = MonitorConfig(
                    name="test", monitor_type="load_average",
                    params={"max_load": 0.5}
                )
                instance = MonitorRegistry.create(config)
                result = instance.check()
                assert result.status == MonitorStatus.DOWN
                assert "per-core" in result.message.lower()
                assert "cores" in result.message.lower()

    def test_load_error_handling(self):
        with patch("psutil.getloadavg", side_effect=OSError("permission denied")):
            config = MonitorConfig(
                name="test", monitor_type="load_average",
                params={"max_load": 1.0}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.DOWN
            assert "error" in result.message.lower()

    def test_load_windows_fallback(self):
        """Test load average when getloadavg is unavailable (Windows)."""
        with patch("psutil.getloadavg", side_effect=AttributeError("no getloadavg")):
            with patch("psutil.cpu_percent", return_value=45.0):
                with patch("psutil.cpu_count", return_value=2):
                    config = MonitorConfig(
                        name="test", monitor_type="load_average",
                        params={"max_load": 0.3}
                    )
                    instance = MonitorRegistry.create(config)
                    result = instance.check()
                    assert result.status == MonitorStatus.DOWN
                    assert "per-core" in result.message.lower()


class TestPingMonitor:
    def test_ping_localhost(self):
        config = MonitorConfig(
            name="test", monitor_type="ping",
            params={"host": "127.0.0.1", "count": 1, "timeout_seconds": 3}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        # May be UP or DOWN depending on ping availability
        assert result.monitor_type == "ping"
        assert result.status in (MonitorStatus.UP, MonitorStatus.DOWN)

    def test_ping_success_with_avg_time(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = (
            "PING 8.8.8.8 (8.8.8.8): 56 data bytes\n"
            "64 bytes from 8.8.8.8: icmp_seq=0 ttl=117 time=14.2 ms\n"
            "\n"
            "--- 8.8.8.8 ping statistics ---\n"
            "1 packets transmitted, 1 packets received, 0.0% packet loss\n"
            "round-trip min/avg/max = 14.2/14.2/14.2 ms\n"
        )
        with patch("subprocess.run", return_value=mock_result):
            config = MonitorConfig(
                name="test", monitor_type="ping",
                params={"host": "8.8.8.8", "count": 1, "timeout_seconds": 5}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.UP
            assert "14" in result.message  # ping time extracted

    def test_ping_timeout(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ping", timeout=5)):
            config = MonitorConfig(
                name="test", monitor_type="ping",
                params={"host": "192.0.2.1", "count": 1, "timeout_seconds": 1}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.DOWN
            assert "timed out" in result.message.lower()

    def test_ping_unreachable(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            config = MonitorConfig(
                name="test", monitor_type="ping",
                params={"host": "192.0.2.1", "count": 1, "timeout_seconds": 1}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.DOWN
            assert "unreachable" in result.message.lower()

    def test_ping_general_error(self):
        with patch("subprocess.run", side_effect=PermissionError("permission denied")):
            config = MonitorConfig(
                name="test", monitor_type="ping",
                params={"host": "localhost", "count": 1, "timeout_seconds": 5}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.DOWN
            assert "error" in result.message.lower()

    def test_ping_windows_command(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            with patch("platform.system", return_value="Windows"):
                config = MonitorConfig(
                    name="test", monitor_type="ping",
                    params={"host": "8.8.8.8", "count": 2, "timeout_seconds": 5}
                )
                instance = MonitorRegistry.create(config)
                result = instance.check()
                assert result.status == MonitorStatus.UP
                # Windows uses -n for count, -w for timeout in ms
                call_args = mock_run.call_args
                assert call_args[0][0][1] == "-n"
                assert call_args[0][0][3] == "-w"


class TestLogFileMonitor:
    def test_log_file_no_errors(self, tmp_file):
        with open(tmp_file, "w") as f:
            f.write("INFO: everything is fine\n")
            f.write("DEBUG: all good\n")

        config = MonitorConfig(
            name="test", monitor_type="log_file",
            params={"path": tmp_file, "lookback_minutes": 60, "max_errors": 1}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        assert result.status == MonitorStatus.UP

    def test_log_file_with_errors(self, tmp_file):
        with open(tmp_file, "w") as f:
            f.write("INFO: starting\n")
            f.write("ERROR: something went wrong\n")

        config = MonitorConfig(
            name="test", monitor_type="log_file",
            params={"path": tmp_file, "lookback_minutes": 60, "max_errors": 1}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        assert result.status == MonitorStatus.DOWN
        assert "error" in result.message.lower()

    def test_log_file_missing(self):
        config = MonitorConfig(
            name="test", monitor_type="log_file",
            params={"path": "/nonexistent/log.txt", "lookback_minutes": 60, "max_errors": 1}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        assert result.status == MonitorStatus.DOWN

    def test_log_file_custom_error_patterns(self, tmp_file):
        with open(tmp_file, "w") as f:
            f.write("WARN: something bad\n")
            f.write("ALERT: critical issue\n")

        config = MonitorConfig(
            name="test", monitor_type="log_file",
            params={"path": tmp_file, "lookback_minutes": 60, "max_errors": 1,
                    "error_patterns": "WARN|ALERT"}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        assert result.status == MonitorStatus.DOWN
        assert "error" in result.message.lower()

    def test_log_file_read_error(self, tmp_path):
        """Test log_file monitor when file is unreadable."""
        config = MonitorConfig(
            name="test", monitor_type="log_file",
            params={"path": "/etc/shadow", "lookback_minutes": 60, "max_errors": 1}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        assert result.status == MonitorStatus.DOWN


class TestProcessCountMonitor:
    def test_min_count_met(self):
        mock_proc = MagicMock()
        mock_proc.info = {"pid": 1234, "name": "worker", "cmdline": ["python worker.py"]}
        mock_proc_iter = MagicMock(return_value=[mock_proc])

        with patch("psutil.process_iter", mock_proc_iter):
            config = MonitorConfig(
                name="test", monitor_type="process_count",
                params={"pattern": "worker", "min_count": 1, "max_count": 100}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.UP
            assert "1 process" in result.message

    def test_min_count_not_met(self):
        mock_proc_iter = MagicMock(return_value=[])

        with patch("psutil.process_iter", mock_proc_iter):
            config = MonitorConfig(
                name="test", monitor_type="process_count",
                params={"pattern": "missing", "min_count": 1}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.DOWN
            assert "minimum" in result.message.lower()

    def test_max_count_exceeded(self):
        mock_procs = []
        for i in range(3):
            p = MagicMock()
            p.info = {"pid": i + 1111, "name": "overflow", "cmdline": ["overflow"]}
            mock_procs.append(p)
        mock_proc_iter = MagicMock(return_value=mock_procs)

        with patch("psutil.process_iter", mock_proc_iter):
            config = MonitorConfig(
                name="test", monitor_type="process_count",
                params={"pattern": "overflow", "min_count": 1, "max_count": 2}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.DOWN
            assert "maximum" in result.message.lower()

    def test_no_max_count(self):
        mock_proc = MagicMock()
        mock_proc.info = {"pid": 42, "name": "solo", "cmdline": ["solo"]}
        mock_proc_iter = MagicMock(return_value=[mock_proc])

        with patch("psutil.process_iter", mock_proc_iter):
            config = MonitorConfig(
                name="test", monitor_type="process_count",
                params={"pattern": "solo", "min_count": 1}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.UP

    def test_missing_params(self):
        config = MonitorConfig(name="test", monitor_type="process_count", params={})
        with pytest.raises(ValueError, match="Missing 'pattern'"):
            MonitorRegistry.create(config)


class TestUptimeMonitor:
    def test_uptime_ok(self):
        with patch("psutil.boot_time", return_value=time.time() - 7200):
            config = MonitorConfig(
                name="test", monitor_type="uptime",
                params={"min_uptime_seconds": 300}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.UP
            assert "uptime" in result.message.lower()

    def test_uptime_too_short(self):
        with patch("psutil.boot_time", return_value=time.time() - 60):
            config = MonitorConfig(
                name="test", monitor_type="uptime",
                params={"min_uptime_seconds": 300}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.DOWN
            assert "reboot" in result.message.lower()

    def test_uptime_format(self):
        assert UptimeMonitor._format_seconds(3661) == "1h 1m"
        assert UptimeMonitor._format_seconds(86400) == "1d"
        assert UptimeMonitor._format_seconds(90061) == "1d 1h 1m"
        assert UptimeMonitor._format_seconds(30) == "<1m"

    def test_uptime_error_handling(self):
        with patch("psutil.boot_time", side_effect=OSError("read error")):
            config = MonitorConfig(
                name="test", monitor_type="uptime",
                params={"min_uptime_seconds": 300}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()
            assert result.status == MonitorStatus.DOWN
            assert "error" in result.message.lower()

    def test_missing_params(self):
        config = MonitorConfig(name="test", monitor_type="uptime", params={})
        with pytest.raises(ValueError, match="Missing 'min_uptime_seconds'"):
            MonitorRegistry.create(config)
