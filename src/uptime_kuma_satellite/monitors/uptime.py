"""Uptime monitor - verify the system has been up for at least N seconds."""

from __future__ import annotations

import logging
import time

import psutil

from . import BaseMonitor, MonitorRegistry
from ..models import MonitorConfig, MonitorResult, MonitorStatus

logger = logging.getLogger(__name__)


@MonitorRegistry.register
class UptimeMonitor(BaseMonitor):
    """Check that the system has been running for at least a minimum duration.

    Useful as an anti-reboot alert: if a machine unexpectedly reboots,
    this monitor will go DOWN until uptime exceeds the threshold.
    """

    type_name = "uptime"

    def validate_config(self) -> list[str]:
        errors = []
        if "min_uptime_seconds" not in self.config.params:
            errors.append("Missing 'min_uptime_seconds' parameter")
        return errors

    def check(self) -> MonitorResult:
        start = time.monotonic()
        min_uptime = self.config.params.get("min_uptime_seconds", 300)

        try:
            boot_seconds = time.time() - psutil.boot_time()
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Error determining uptime: {e}",
                ping_ms=elapsed,
            )

        elapsed = (time.monotonic() - start) * 1000

        if boot_seconds < min_uptime:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"System uptime {self._format_seconds(boot_seconds)} is less than minimum {self._format_seconds(min_uptime)}. Possible recent reboot.",
                ping_ms=elapsed,
            )

        return MonitorResult(
            monitor_name=self.config.name,
            monitor_type=self.type_name,
            status=MonitorStatus.UP,
            message=f"System uptime: {self._format_seconds(boot_seconds)} (minimum: {self._format_seconds(min_uptime)})",
            ping_ms=elapsed,
        )

    @staticmethod
    def _format_seconds(seconds: float) -> str:
        """Format seconds into human-readable uptime string."""
        days = int(seconds) // 86400
        hours = (int(seconds) % 86400) // 3600
        minutes = (int(seconds) % 3600) // 60

        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")

        return " ".join(parts) if parts else "<1m"
