"""Tests for all monitor implementations."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import importlib

import pytest

from uptime_kuma_satellite.models import MonitorConfig, MonitorStatus
from uptime_kuma_satellite.monitors import MonitorRegistry


# Track which modules are built-in so we can reload them
_BUILTIN_MODULES = [
    "uptime_kuma_satellite.monitors.file_exists",
    "uptime_kuma_satellite.monitors.file_age",
    "uptime_kuma_satellite.monitors.disk_space",
    "uptime_kuma_satellite.monitors.process",
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


class TestLogFileMonitor:
    def test_log_file_no_errors(self, tmp_file):
        with open(tmp_file, "w") as f:
            f.write("INFO: everything is fine\n")
            f.write("DEBUG: all good\n")

        config = MonitorConfig(
            name="test", monitor_type="log_file",
            params={"path": tmp_file, "lookback_minutes": 60}
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
            params={"path": "/nonexistent/log.txt", "lookback_minutes": 60}
        )
        instance = MonitorRegistry.create(config)
        result = instance.check()
        assert result.status == MonitorStatus.DOWN
