"""Cross-platform service installation and management."""

from __future__ import annotations

import logging
import os
import platform
import shutil
import sys
import textwrap
from pathlib import Path
from typing import Any

logger = logging.getLogger("uks.service")

# Service name used across all platforms
SERVICE_NAME = "uptime-kuma-satellite"
SERVICE_DISPLAY_NAME = "Uptime Kuma Satellite"


def _get_executable_path() -> str:
    """Get the path to the uks executable."""
    # Check if running from a virtual environment
    if hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix):
        # Running in a venv
        return os.path.join(sys.prefix, "bin", "uks")
    
    # Try to find uks in PATH
    uks_path = shutil.which("uks")
    if uks_path:
        return uks_path
    
    # Fallback: use python -m
    return sys.executable


def get_system_config_file() -> Path:
    """Get the system-wide config file path for the current platform."""
    from .config import get_system_config_file as _get_system_config_file
    return _get_system_config_file()


def _is_admin() -> bool:
    """Check if the current process has admin/root privileges."""
    if platform.system() == "Windows":
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    return os.geteuid() == 0


def _detect_platform() -> str:
    """Detect the current platform."""
    system = platform.system()
    if system == "Linux":
        # Check for systemd
        if Path("/run/systemd/system").exists():
            return "systemd"
        return "linux-other"
    elif system == "Darwin":
        return "launchd"
    elif system == "Windows":
        return "windows"
    return "unknown"


class ServiceManager:
    """Manages installing and uninstalling the satellite as a system service."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or get_system_config_file()
        self.platform = _detect_platform()
        self.executable = _get_executable_path()

    def install(self) -> None:
        """Install the satellite as a system service."""
        if not self.config_path.exists():
            logger.error(
                "Config file not found at %s. Run 'uks setup' first.",
                self.config_path,
            )
            raise SystemExit(1)

        installer = {
            "systemd": self._install_systemd,
            "launchd": self._install_launchd,
            "windows": self._install_windows,
        }.get(self.platform)

        if not installer:
            logger.error(
                "Service installation is not supported on this platform (%s). "
                "You can still run the satellite with 'uks run'.",
                self.platform,
            )
            raise SystemExit(1)

        try:
            installer()
            logger.info("Service installed successfully.")
        except PermissionError:
            logger.error(
                "Permission denied. Please run with sudo (Linux/macOS) or as Administrator (Windows)."
            )
            raise SystemExit(1)
        except Exception as e:
            logger.error("Failed to install service: %s", e)
            raise SystemExit(1)

    def uninstall(self) -> None:
        """Uninstall the satellite system service."""
        uninstaller = {
            "systemd": self._uninstall_systemd,
            "launchd": self._uninstall_launchd,
            "windows": self._uninstall_windows,
        }.get(self.platform)

        if not uninstaller:
            logger.error(
                "Service uninstallation is not supported on this platform (%s).",
                self.platform,
            )
            raise SystemExit(1)

        try:
            uninstaller()
            logger.info("Service uninstalled successfully.")
        except Exception as e:
            logger.error("Failed to uninstall service: %s", e)
            raise SystemExit(1)

    def status(self) -> None:
        """Show the current status of the service."""
        status_checker = {
            "systemd": self._status_systemd,
            "launchd": self._status_launchd,
            "windows": self._status_windows,
        }.get(self.platform)

        if not status_checker:
            logger.error("Service status is not supported on this platform (%s).", self.platform)
            raise SystemExit(1)

        try:
            status_checker()
        except Exception as e:
            logger.error("Failed to get service status: %s", e)
            raise SystemExit(1)

    def _get_service_user(self) -> str:
        """Get the user to run the service as."""
        return os.environ.get("SUDO_USER") or os.environ.get("USER") or ""

    def _get_service_group(self) -> str:
        """Get the group to run the service as."""
        import pwd
        try:
            user = self._get_service_user()
            if user:
                return pwd.getpwnam(user).pw_gid
        except KeyError:
            pass
        return str(os.getgid())

    # ── Linux / systemd ──────────────────────────────────────────────────

    def _install_systemd(self) -> None:
        """Install as a systemd service."""
        user = self._get_service_user()
        if not user:
            user = "root"

        unit_dir = Path("/etc/systemd/system")
        if not unit_dir.exists():
            raise PermissionError("Cannot write to /etc/systemd/system")

        # Determine log file location
        log_dir = Path("/var/log/uptime-kuma-satellite")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "satellite.log"

        unit_content = textwrap.dedent(f"""\
            [Unit]
            Description=Uptime Kuma Satellite - Push API Monitor
            After=network-online.target
            Wants=network-online.target

            [Service]
            Type=simple
            User={user}
            ExecStart={self.executable} run --config "{self.config_path}"
            Restart=on-failure
            RestartSec=5
            StandardOutput=append:{log_file}
            StandardError=append:{log_file}
            Environment=PYTHONUNBUFFERED=1

            [Install]
            WantedBy=multi-user.target
        """)

        unit_file = unit_dir / f"{SERVICE_NAME}.service"
        unit_file.write_text(unit_content)
        logger.info("Created systemd unit: %s", unit_file)

        # Reload systemd and enable/start the service
        import subprocess
        subprocess.run(["systemctl", "daemon-reload"], check=True, capture_output=True)
        subprocess.run(["systemctl", "enable", SERVICE_NAME], check=True, capture_output=True)
        subprocess.run(["systemctl", "start", SERVICE_NAME], check=True, capture_output=True)
        logger.info("Service enabled and started.")

    def _uninstall_systemd(self) -> None:
        """Uninstall the systemd service."""
        import subprocess
        subprocess.run(["systemctl", "stop", SERVICE_NAME], check=False, capture_output=True)
        subprocess.run(["systemctl", "disable", SERVICE_NAME], check=False, capture_output=True)
        subprocess.run(["systemctl", "daemon-reload"], check=True, capture_output=True)

        unit_file = Path(f"/etc/systemd/system/{SERVICE_NAME}.service")
        if unit_file.exists():
            unit_file.unlink()
            logger.info("Removed systemd unit: %s", unit_file)

        # Clean up log directory
        log_dir = Path("/var/log/uptime-kuma-satellite")
        if log_dir.exists():
            shutil.rmtree(log_dir, ignore_errors=True)
            logger.info("Removed log directory: %s", log_dir)

    def _status_systemd(self) -> None:
        """Check systemd service status."""
        import subprocess
        result = subprocess.run(
            ["systemctl", "status", SERVICE_NAME],
            capture_output=True,
            text=True,
        )
        print(result.stdout or result.stderr)

    # ── macOS / launchd ──────────────────────────────────────────────────

    def _install_launchd(self) -> None:
        """Install as a launchd service."""
        user = self._get_service_user()
        if not user:
            user = os.environ.get("USER", "root")

        home = Path.home()
        plist_dir = Path(f"/Library/LaunchDaemons")
        if not plist_dir.exists():
            plist_dir.mkdir(parents=True, exist_ok=True)

        # Determine log file
        log_dir = Path("/var/log/uptime-kuma-satellite")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "satellite.log"

        plist_content = textwrap.dedent(f"""\
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
                "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
            <plist version="1.0">
            <dict>
                <key>Label</key>
                <string>{SERVICE_NAME}</string>
                <key>ProgramArguments</key>
                <array>
                    <string>{self.executable}</string>
                    <string>run</string>
                    <string>--config</string>
                    <string>{self.config_path}</string>
                </array>
                <key>RunAtLoad</key>
                <true/>
                <key>KeepAlive</key>
                <true/>
                <key>WorkingDirectory</key>
                <string>{home}</string>
                <key>StandardOutPath</key>
                <string>{log_file}</string>
                <key>StandardErrorPath</key>
                <string>{log_file}</string>
                <key>EnvironmentVariables</key>
                <dict>
                    <key>PYTHONUNBUFFERED</key>
                    <string>1</string>
                </dict>
            </dict>
            </plist>
        """)

        plist_file = plist_dir / f"{SERVICE_NAME}.plist"
        plist_file.write_text(plist_content)
        logger.info("Created launchd plist: %s", plist_file)

        import subprocess
        subprocess.run(["launchctl", "bootout", "system", SERVICE_NAME], check=False, capture_output=True)
        subprocess.run(["launchctl", "load", str(plist_file)], check=True, capture_output=True)
        subprocess.run(["launchctl", "bgin", SERVICE_NAME, str(plist_file)], check=False, capture_output=True)
        logger.info("Service loaded and started.")

    def _uninstall_launchd(self) -> None:
        """Uninstall the launchd service."""
        import subprocess
        plist_file = Path(f"/Library/LaunchDaemons/{SERVICE_NAME}.plist")
        if plist_file.exists():
            subprocess.run(
                ["launchctl", "bootout", "system", str(plist_file)],
                check=False,
                capture_output=True,
            )
            plist_file.unlink()
            logger.info("Removed launchd plist: %s", plist_file)

        log_dir = Path("/var/log/uptime-kuma-satellite")
        if log_dir.exists():
            shutil.rmtree(log_dir, ignore_errors=True)
            logger.info("Removed log directory: %s", log_dir)

    def _status_launchd(self) -> None:
        """Check launchd service status."""
        import subprocess
        result = subprocess.run(
            ["launchctl", "list", SERVICE_NAME],
            capture_output=True,
            text=True,
        )
        print(result.stdout or result.stderr)

    # ── Windows ──────────────────────────────────────────────────────────

    def _install_windows(self) -> None:
        """Install as a Windows service using pywin32."""
        try:
            import win32serviceutil
            import win32service
            import win32event
            import servicemanager
        except ImportError:
            logger.error(
                "pywin32 is required for Windows service support. "
                "Install it with: pip install pywin32"
            )
            raise SystemExit(1)

        # Register the service
        win32serviceutil.InstallService(
            pythonClassString="uptime_kuma_satellite.windows_service.UptimeKumaSatelliteService",
            serviceName=SERVICE_NAME,
            displayName=SERVICE_DISPLAY_NAME,
            description="Uptime Kuma Satellite - Push API Monitor",
            startType=win32service.SERVICE_AUTO_START,
            exeArgs=" ".join([
                "run",
                "--config",
                str(self.config_path),
            ]),
        )

        # Start the service
        win32serviceutil.StartService(SERVICE_NAME)
        logger.info("Windows service installed and started.")

    def _uninstall_windows(self) -> None:
        """Uninstall the Windows service."""
        try:
            import win32serviceutil
        except ImportError:
            logger.error("pywin32 is required for Windows service management.")
            raise SystemExit(1)

        try:
            win32serviceutil.StopService(SERVICE_NAME)
        except Exception:
            pass  # Service might not be running

        win32serviceutil.RemoveService(SERVICE_NAME)
        logger.info("Windows service removed.")

    def _status_windows(self) -> None:
        """Check Windows service status."""
        try:
            import win32serviceutil
        except ImportError:
            logger.error("pywin32 is required for Windows service status.")
            raise SystemExit(1)

        try:
            state = win32serviceutil.QueryServiceStatus(SERVICE_NAME)
            state_name = {
                1: "STOPPED",
                2: "START_PENDING",
                3: "STOP_PENDING",
                4: "RUNNING",
                5: "CONTINUE_PENDING",
                6: "PAUSE_PENDING",
                7: "PAUSED",
            }.get(state[1], "UNKNOWN")
            print(f"Service: {SERVICE_NAME}")
            print(f"State: {state_name}")
        except Exception as e:
            print(f"Service not found or error: {e}")


def get_service_manager(config_path: Path | None = None) -> ServiceManager:
    """Factory function to get a platform-appropriate ServiceManager."""
    return ServiceManager(config_path)
