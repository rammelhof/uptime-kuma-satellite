"""Integration tests with mock server."""

import importlib
import sys
import threading
import time
from pathlib import Path

import pytest

# Import mock server from tests directory
sys.path.insert(0, str(Path(__file__).parent))
mock_server = importlib.import_module("mock_server")
MockKumaHandler = mock_server.MockKumaHandler
start_mock_server = mock_server.start_mock_server

from uptime_kuma_satellite.client import UptimeKumaClient
from uptime_kuma_satellite.models import MonitorConfig, MonitorResult, MonitorStatus
from uptime_kuma_satellite.monitors import MonitorRegistry

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
    for mod_name in _BUILTIN_MODULES:
        if mod_name in importlib.sys.modules:
            importlib.reload(importlib.import_module(mod_name))
        else:
            importlib.import_module(mod_name)
    yield
    MonitorRegistry.reset()


class TestIntegration:
    """Integration tests with mock Uptime Kuma server."""

    def test_report_to_mock_server(self, tmp_path: Path):
        """Test that monitors report correctly to a mock Uptime Kuma server."""
        server = start_mock_server(port=18765)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        time.sleep(0.2)

        try:
            test_file = tmp_path / "test.txt"
            test_file.write_text("hello")

            client = UptimeKumaClient("http://127.0.0.1:18765/api/push/test123")

            config = MonitorConfig(
                name="test-file",
                monitor_type="file_exists",
                params={"path": str(test_file)}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()

            success = client.report(result)
            assert success is True

            assert len(MockKumaHandler.received_reports) == 1
            report = MockKumaHandler.received_reports[0]
            assert report["status"] == "up"
            assert "test.txt" in report["msg"]
            assert report["path"] == "/api/push/test123"

            client.close()
        finally:
            server.shutdown()

    def test_down_monitor_to_mock_server(self, tmp_path: Path):
        """Test that DOWN status is reported correctly."""
        server = start_mock_server(port=18766)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        time.sleep(0.2)

        try:
            client = UptimeKumaClient("http://127.0.0.1:18766/api/push/test456")

            config = MonitorConfig(
                name="missing-file",
                monitor_type="file_exists",
                params={"path": "/nonexistent/file.txt"}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()

            success = client.report(result)
            assert success is True

            report = MockKumaHandler.received_reports[0]
            assert report["status"] == "down"
            assert "missing" in report["msg"].lower()

            client.close()
        finally:
            server.shutdown()

    def test_multiple_monitors(self, tmp_path: Path):
        """Test reporting multiple monitors."""
        server = start_mock_server(port=18767)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        time.sleep(0.2)

        try:
            client = UptimeKumaClient("http://127.0.0.1:18767/api/push/multi")

            test_file = tmp_path / "exists.txt"
            test_file.write_text("content")

            config1 = MonitorConfig(
                name="file-check",
                monitor_type="file_exists",
                params={"path": str(test_file)}
            )
            instance1 = MonitorRegistry.create(config1)
            result1 = instance1.check()
            client.report(result1)

            config2 = MonitorConfig(
                name="disk-check",
                monitor_type="disk_space",
                params={"path": "/", "min_percent": 0.001}
            )
            instance2 = MonitorRegistry.create(config2)
            result2 = instance2.check()
            client.report(result2)

            assert len(MockKumaHandler.received_reports) == 2
            assert MockKumaHandler.received_reports[0]["status"] == "up"
            client.close()
        finally:
            server.shutdown()

    def test_monitor_with_ping(self, tmp_path: Path):
        """Test that ping is included in the report."""
        server = start_mock_server(port=18768)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        time.sleep(0.2)

        try:
            client = UptimeKumaClient("http://127.0.0.1:18768/api/push/ping-test")

            config = MonitorConfig(
                name="file-check",
                monitor_type="file_exists",
                params={"path": "/tmp"}
            )
            instance = MonitorRegistry.create(config)
            result = instance.check()

            client.report(result)
            report = MockKumaHandler.received_reports[0]

            assert "ping" in report
            assert float(report["ping"]) >= 0

            client.close()
        finally:
            server.shutdown()
