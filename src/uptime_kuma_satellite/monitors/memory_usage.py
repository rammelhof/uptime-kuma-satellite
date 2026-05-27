"""Memory usage monitor."""

from __future__ import annotations

import logging
import os
import resource
import time

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
            if os.path.exists("/proc/meminfo"):
                meminfo = {}
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            key = parts[0].strip()
                            val = parts[1].strip().split()[0]
                            meminfo[key] = int(val)
                total = meminfo.get("MemTotal", 1)
                available = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
                used_percent = ((total - available) / total) * 100 if total > 0 else 0
                used_mb = (total - available) / 1024
                total_mb = total / 1024
            else:
                import resource
                usage = resource.getrusage(resource.RUSAGE_SELF)
                used_mb = usage.ru_maxrss / 1024
                total_mb = 16384  # fallback assumption
                used_percent = (used_mb / total_mb) * 100

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Error reading memory usage: {e}",
                ping_ms=elapsed,
            )

        elapsed = (time.monotonic() - start) * 1000

        if used_percent > max_percent:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Memory usage high: {used_percent:.1f}% ({used_mb:.0f}MB/{total_mb:.0f}MB) (threshold: {max_percent}%)",
                ping_ms=elapsed,
            )
        else:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.UP,
                message=f"Memory usage OK: {used_percent:.1f}% ({used_mb:.0f}MB/{total_mb:.0f}MB) (threshold: {max_percent}%)",
                ping_ms=elapsed,
            )
