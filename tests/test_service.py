"""Tests for the service manager."""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from uptime_kuma_satellite.service_manager import (
    SERVICE_NAME,
    SERVICE_DISPLAY_NAME,
    ServiceManager,
    _detect_platform,
    _get_config_path,
    _get_executable_path,
    get_service_manager,
)


class TestDetectPlatform:
    """Tests for platform detection."""

    def test_linux_systemd(self):
        with patch("platform.system", return_value="Linux"):
            with patch("pathlib.Path.exists", return_value=True):
                assert _detect_platform() == "systemd"

    def test_linux_no_systemd(self):
        with patch("platform.system", return_value="Linux"):
            with patch("pathlib.Path.exists", return_value=False):
                assert _detect_platform() == "linux-other"

    def test_macos(self):
        with patch("platform.system", return_value="Darwin"):
            assert _detect_platform() == "launchd"

    def test_windows(self):
        with patch("platform.system", return_value="Windows"):
            assert _detect_platform() == "windows"


class TestHelpers:
    """Tests for helper functions."""

    def test_get_config_path(self):
        path = _get_config_path()
        assert isinstance(path, Path)
        assert path.name == "config.yaml"

    def test_get_executable_path(self):
        path = _get_executable_path()
        assert isinstance(path, str)
        assert len(path) > 0

    def test_get_service_manager(self):
        mgr = get_service_manager()
        assert isinstance(mgr, ServiceManager)

    def test_get_service_manager_with_path(self, tmp_path: Path):
        config_file = tmp_path / "custom.yaml"
        config_file.write_text("test: true")
        mgr = get_service_manager(config_file)
        assert mgr.config_path == config_file


class TestServiceManagerLinux:
    """Tests for Linux service management."""

    @pytest.fixture
    def systemd_mgr(self, tmp_path: Path) -> ServiceManager:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("push_url: http://test/api/push/key\n")
        with patch("platform.system", return_value="Linux"):
            with patch("pathlib.Path.exists", return_value=False):
                mgr = ServiceManager(config_file)
        return mgr

    def test_install_systemd_missing_config(self):
        mgr = ServiceManager(Path("/nonexistent/config.yaml"))
        with patch("platform.system", return_value="Linux"):
            with patch("pathlib.Path.exists", return_value=False):
                with pytest.raises(SystemExit):
                    mgr.install()

    def test_install_systemd_creates_unit(self, systemd_mgr: ServiceManager):
        """Test that systemd unit file is created with correct content."""
        unit_dir = MagicMock()
        unit_file = MagicMock()
        unit_dir.exists.return_value = True
        unit_dir.__truediv__ = lambda self, name: unit_file

        with patch.object(systemd_mgr, "_get_service_user", return_value="testuser"):
            with patch.object(systemd_mgr, "_get_service_group", return_value="1000"):
                with patch("pathlib.Path.mkdir"):
                    with patch(
                        "pathlib.Path.__truediv__",
                        return_value=unit_file,
                    ):
                        with patch("subprocess.run"):
                            systemd_mgr._install_systemd()

        # Verify unit file was written
        assert unit_file.write_text.called
        content = unit_file.write_text.call_args[0][0]
        assert "ExecStart" in content
        assert "testuser" in content
        assert "Restart=on-failure" in content

    def test_uninstall_systemd(self, systemd_mgr: ServiceManager):
        with patch("subprocess.run") as mock_run:
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.unlink"):
                    systemd_mgr._uninstall_systemd()
            # Should call systemctl stop, disable, daemon-reload
            calls = [c[0][0] for c in mock_run.call_args_list]
            assert any("stop" in str(c) for c in calls)
            assert any("disable" in str(c) for c in calls)

    def test_status_systemd(self, systemd_mgr: ServiceManager):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Active: active", stderr="")
            with patch("builtins.print"):
                systemd_mgr._status_systemd()
            assert mock_run.called


class TestServiceManagerMacOS:
    """Tests for macOS service management."""

    @pytest.fixture
    def launchd_mgr(self, tmp_path: Path) -> ServiceManager:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("push_url: http://test/api/push/key\n")
        with patch("platform.system", return_value="Darwin"):
            mgr = ServiceManager(config_file)
        return mgr

    def test_install_launchd(self, launchd_mgr: ServiceManager):
        plist_file = MagicMock()
        with patch("pathlib.Path.mkdir"):
            with patch(
                "pathlib.Path.__truediv__",
                return_value=plist_file,
            ):
                with patch("subprocess.run"):
                    launchd_mgr._install_launchd()

        assert plist_file.write_text.called
        content = plist_file.write_text.call_args[0][0]
        assert "uptime-kuma-satellite" in content
        assert "Label" in content

    def test_uninstall_launchd(self, launchd_mgr: ServiceManager):
        with patch("subprocess.run"):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.unlink", return_value=None):
                    launchd_mgr._uninstall_launchd()


class TestServiceManagerWindows:
    """Tests for Windows service management."""

    @pytest.fixture
    def windows_mgr(self, tmp_path: Path) -> ServiceManager:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("push_url: http://test/api/push/key\n")
        with patch("platform.system", return_value="Windows"):
            mgr = ServiceManager(config_file)
        return mgr

    def test_install_windows_no_pywin32(self, windows_mgr: ServiceManager):
        with patch.dict(sys.modules, {"win32serviceutil": None}):
            with pytest.raises(SystemExit):
                windows_mgr._install_windows()

    def test_install_windows_with_pywin32(self, windows_mgr: ServiceManager):
        mock_win32 = MagicMock()
        with patch.dict(sys.modules, {
            "win32serviceutil": mock_win32,
            "win32service": MagicMock(),
            "win32event": MagicMock(),
            "servicemanager": MagicMock(),
        }):
            windows_mgr._install_windows()
            assert mock_win32.InstallService.called
            assert mock_win32.StartService.called

    def test_uninstall_windows(self, windows_mgr: ServiceManager):
        mock_win32 = MagicMock()
        with patch.dict(sys.modules, {"win32serviceutil": mock_win32}):
            windows_mgr._uninstall_windows()
            assert mock_win32.StopService.called
            assert mock_win32.RemoveService.called

    def test_status_windows(self, windows_mgr: ServiceManager):
        mock_win32 = MagicMock()
        mock_win32.QueryServiceStatus.return_value = (SERVICE_NAME, 4)  # RUNNING
        with patch.dict(sys.modules, {"win32serviceutil": mock_win32}):
            with patch("builtins.print") as mock_print:
                windows_mgr._status_windows()
                assert mock_print.called


class TestServiceCommandIntegration:
    """Integration tests for service commands."""

    def test_service_manager_detects_platform(self):
        """Service manager should detect the current platform."""
        mgr = ServiceManager()
        assert mgr.platform in ("systemd", "launchd", "windows", "linux-other", "unknown")

    def test_service_manager_has_config_path(self, tmp_path: Path):
        """Service manager should accept a config path."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("push_url: http://test/key\n")
        mgr = ServiceManager(config_file)
        assert mgr.config_path == config_file

    def test_service_name_constants(self):
        """Service name constants should be set."""
        assert SERVICE_NAME == "uptime-kuma-satellite"
        assert SERVICE_DISPLAY_NAME == "Uptime Kuma Satellite"
