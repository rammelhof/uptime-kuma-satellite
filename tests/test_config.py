"""Tests for config manager and HTTP client."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from uptime_kuma_satellite.models import MonitorConfig, ServiceConfig
from uptime_kuma_satellite.config import ConfigManager


class TestConfigManager:
    """Tests for ConfigManager."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        mgr = ConfigManager(config_path)

        config = ServiceConfig(
            push_url="http://test.local/api/push/abc123",
            hostname="test-host",
            default_interval=120,
            monitors=[
                MonitorConfig(name="m1", monitor_type="file_exists", params={"path": "/tmp/test.txt"}),
                MonitorConfig(name="m2", monitor_type="service", params={"host": "localhost", "port": 80}),
            ],
        )
        mgr.save(config)

        loaded = mgr.load()
        assert loaded.push_url == "http://test.local/api/push/abc123"
        assert loaded.hostname == "test-host"
        assert loaded.default_interval == 120
        assert len(loaded.monitors) == 2
        assert loaded.monitors[0].name == "m1"
        assert loaded.monitors[1].name == "m2"

    def test_load_empty(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        mgr = ConfigManager(config_path)

        # No file exists - should return empty config without raising
        loaded = mgr.load()
        assert loaded.push_url == ""
        assert len(loaded.monitors) == 0

    def test_load_empty_file(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_path.write_text("")
        mgr = ConfigManager(config_path)

        loaded = mgr.load()
        assert loaded.push_url == ""

    def test_config_validation(self) -> None:
        with pytest.raises(ValueError, match="Push URL cannot be empty"):
            ServiceConfig(push_url="")

    def test_config_default_hostname(self) -> None:
        config = ServiceConfig(push_url="http://test.local/api/push/abc")
        assert config.hostname  # Should be a non-empty hostname


class TestUptimeKumaClient:
    """Tests for UptimeKumaClient."""

    def test_report_success(self) -> None:
        from uptime_kuma_satellite.client import UptimeKumaClient
        from uptime_kuma_satellite.models import MonitorResult, MonitorStatus

        with patch("httpx.Client") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "OK"

            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = UptimeKumaClient("http://test.local/api/push/abc")
            result = MonitorResult(
                monitor_name="test",
                monitor_type="file_exists",
                status=MonitorStatus.UP,
                message="all good",
                ping_ms=10.5,
            )
            success = client.report(result)
            assert success is True
            mock_client.get.assert_called_once()

    def test_report_failure(self) -> None:
        from uptime_kuma_satellite.client import UptimeKumaClient
        from uptime_kuma_satellite.models import MonitorResult, MonitorStatus
        import httpx

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            mock_client_class.return_value = mock_client

            client = UptimeKumaClient("http://test.local/api/push/abc")
            result = MonitorResult(
                monitor_name="test",
                monitor_type="file_exists",
                status=MonitorStatus.DOWN,
                message="file missing",
            )
            success = client.report(result)
            assert success is False

    def test_context_manager(self) -> None:
        from uptime_kuma_satellite.client import UptimeKumaClient

        with patch("httpx.Client"):
            with UptimeKumaClient("http://test.local/api/push/abc") as client:
                pass
            # Should not raise

    def test_report_aggregated_all_up(self) -> None:
        """Test aggregated reporting when all monitors are UP."""
        from uptime_kuma_satellite.client import UptimeKumaClient
        from uptime_kuma_satellite.models import MonitorResult, MonitorStatus

        with patch("httpx.Client") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = UptimeKumaClient("http://test.local/api/push/abc")
            results = [
                MonitorResult(monitor_name="m1", monitor_type="file_exists",
                              status=MonitorStatus.UP, message="file exists", ping_ms=5.0),
                MonitorResult(monitor_name="m2", monitor_type="disk_space",
                              status=MonitorStatus.UP, message="disk ok", ping_ms=10.0),
            ]
            success = client.report_aggregated(results)
            assert success is True
            mock_client.get.assert_called_once()

            # Check the aggregated params
            call_args = mock_client.get.call_args
            params = call_args[1]["params"]
            assert params["status"] == "up"
            assert "All 2 monitor(s) OK" in params["msg"]

    def test_report_aggregated_some_down(self) -> None:
        """Test aggregated reporting when some monitors are DOWN."""
        from uptime_kuma_satellite.client import UptimeKumaClient
        from uptime_kuma_satellite.models import MonitorResult, MonitorStatus

        with patch("httpx.Client") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = UptimeKumaClient("http://test.local/api/push/abc")
            results = [
                MonitorResult(monitor_name="m1", monitor_type="file_exists",
                              status=MonitorStatus.UP, message="file exists"),
                MonitorResult(monitor_name="m2", monitor_type="service",
                              status=MonitorStatus.DOWN, message="connection refused"),
            ]
            success = client.report_aggregated(results)
            assert success is True

            call_args = mock_client.get.call_args
            params = call_args[1]["params"]
            assert params["status"] == "down"
            assert "1 of 2 monitor(s) DOWN" in params["msg"]
            assert "m2" in params["msg"]

    def test_report_aggregated_empty(self) -> None:
        """Test aggregated reporting with no results."""
        from uptime_kuma_satellite.client import UptimeKumaClient

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            client = UptimeKumaClient("http://test.local/api/push/abc")
            success = client.report_aggregated([])
            assert success is True
            mock_client.get.assert_not_called()
