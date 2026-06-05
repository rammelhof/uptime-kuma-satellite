"""Memory usage monitor - cross-platform (Linux, macOS, Windows)."""

from __future__ import annotations

import logging
import time

import psutil

from . import BaseMonitor, MonitorRegistry
from ..models import MonitorConfig, MonitorResult, MonitorStatus

logger = logging.getLogger(__name__)


@MonitorRegistry.register
class MemoryUsageMonitor(BaseMonitor):
    """Check current memory usage percentage."""

    type_name = "memory_usage"

    def validate_config(self) -> list[str]:
        errors = []
        if "max_percent" not in self.config.params:
            errors.append("Missing 'max_percent' parameter")
        return errors

    def check(self) -> MonitorResult:
        start = time.monotonic()
        max_percent = self.config.params.get("max_percent", 90)

        try:
            mem = psutil.virtual_memory()
            used_percent = mem.percent
            used_mb = mem.used / (1024 * 1024)
            total_mb = mem.total / (1024 * 1024)
            swap = psutil.swap_memory()
            swap_used_mb = swap.used / (1024 * 1024)
            swap_total_mb = swap.total / (1024 * 1024)
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            self._last_data = {"threshold": max_percent}
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Error reading memory usage: {e}",
                ping_ms=elapsed,
            )

        elapsed = (time.monotonic() - start) * 1000

        # Store data for template rendering
        self._last_data = {
            "memory_usage": used_percent,
            "memory_used_mb": used_mb,
            "memory_total_mb": total_mb,
            "swap_used_mb": swap_used_mb,
            "swap_total_mb": swap_total_mb,
            "threshold": max_percent,
        }

        if used_percent > max_percent:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Memory usage high: {used_percent:.1f}% ({used_mb:.0f}MB/{total_mb:.0f}MB) (swap: {swap_used_mb:.0f}MB/{swap_total_mb:.0f}MB) (threshold: {max_percent}%)",
                ping_ms=elapsed,
            )
        else:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.UP,
                message=f"Memory usage OK: {used_percent:.1f}% ({used_mb:.0f}MB/{total_mb:.0f}MB) (swap: {swap_used_mb:.0f}MB/{swap_total_mb:.0f}MB) (threshold: {max_percent}%)",
                ping_ms=elapsed,
            )
