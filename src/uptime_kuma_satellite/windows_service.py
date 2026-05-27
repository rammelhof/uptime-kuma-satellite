"""Windows service implementation for Uptime Kuma Satellite.

This module is used by pywin32 to run the satellite as a Windows service.
"""

from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path

import win32service
import win32serviceutil
import win32event
import servicemanager

from .config import get_system_config_file, get_system_config_dir, ConfigManager
from .models import ServiceConfig
from .scheduler import Scheduler

logger = logging.getLogger("uks.windows_service")

# Set up logging for the Windows service
LOG_FILE = get_system_config_dir() / "satellite.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)


class UptimeKumaSatelliteService(win32serviceutil.ServiceFramework):
    """Windows service wrapper for the Uptime Kuma Satellite."""

    _svc_name_ = "uptime-kuma-satellite"
    _svc_display_name_ = "Uptime Kuma Satellite"
    _svc_description_ = "Uptime Kuma Satellite - Push API Monitor"

    def __init__(self, args: list[str]) -> None:
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.scheduler: Scheduler | None = None
        from .config import get_system_config_file
        self.config_path = get_system_config_file()
        self._parse_args(args)

    def _parse_args(self, args: list[str]) -> None:
        """Parse command-line arguments passed by pywin32."""
        i = 0
        while i < len(args):
            if args[i] == "--config" and i + 1 < len(args):
                self.config_path = Path(args[i + 1])
                i += 2
            else:
                i += 1

    def SvcStop(self) -> None:
        """Handle the stop request."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        if self.scheduler:
            self.scheduler.stop()

    def SvcDoRun(self) -> None:
        """Main service entry point."""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )

        logger.info("Starting Uptime Kuma Satellite service...")
        logger.info("Config: %s", self.config_path)

        try:
            config_mgr = ConfigManager(self.config_path)
            config = config_mgr.load()

            if not config.push_url:
                logger.error("No push URL configured. Service will exit.")
                return

            logger.info("Starting with %d monitors", len(config.monitors))
            self.scheduler = Scheduler(config.push_url, self.config_path)
            self.scheduler.start(config.monitors)

            # Wait for stop event
            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
        except Exception as e:
            logger.error("Service failed to start: %s", e)
            servicemanager.LogErrorMsg(f"Service failed: {e}")

        logger.info("Service stopped.")


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(UptimeKumaSatelliteService)
