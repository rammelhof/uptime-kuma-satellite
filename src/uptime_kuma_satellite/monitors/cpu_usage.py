"""CPU usage monitor - cross-platform via psutil."""

from __future__ import annotations

import logging
import time

import psutil

from . import BaseMonitor, MonitorRegistry
from ..models import MonitorConfig, MonitorResult, MonitorStatus

logger = logging.getLogger(__name__)


@MonitorRegistry.register
class CPUUsageMonitor(BaseMonitor):
    """Check current CPU usage percentage."""

    type_name = "cpu_usage"

    def validate_config(self) -> list[str]:
        errors = []
        if "max_percent" not in self.config.params:
            errors.append("Missing 'max_percent' parameter")
        return errors

    def check(self) -> MonitorResult:
        start = time.monotonic()
        max_percent = self.config.params.get("max_percent", 90)

        try:
            usage_pct = psutil.cpu_percent(interval=1)
            per_core = psutil.cpu_percent(interval=0, percpu=True)
            num_cores = len(per_core)
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            self._last_data = {"threshold": max_percent}
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Error reading CPU usage: {e}",
                ping_ms=elapsed,
            )

        elapsed = (time.monotonic() - start) * 1000
        min_core = min(per_core) if per_core else 0
        max_core = max(per_core) if per_core else 0

        # Store data for template rendering
        self._last_data = {
            "cpu_usage": usage_pct,
            "num_cores": num_cores,
            "min_core": min_core,
            "max_core": max_core,
            "threshold": max_percent,
        }

        if usage_pct > max_percent:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"CPU usage high: {usage_pct:.1f}% ({num_cores} cores, per-core: {min_core:.0f}-{max_core:.0f}%) (threshold: {max_percent}%)",
                ping_ms=elapsed,
            )
        else:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.UP,
                message=f"CPU usage OK: {usage_pct:.1f}% ({num_cores} cores, per-core: {min_core:.0f}-{max_core:.0f}%) (threshold: {max_percent}%)",
                ping_ms=elapsed,
            )
