"""CPU usage monitor."""

from __future__ import annotations

import logging
import os
import time

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
            # Use /proc/stat for Linux, psutil-like approach
            if os.path.exists("/proc/stat"):
                with open("/proc/stat", "r") as f:
                    line = f.readline()
                fields = line.split()
                # user, nice, system, idle, iowait, irq, softirq, steal
                idle = int(fields[4]) if len(fields) > 4 else 0
                total = sum(int(x) for x in fields[1:])
                idle_pct = (idle / total) * 100 if total > 0 else 100
                usage_pct = 100 - idle_pct
            else:
                # Fallback: use os.getloadavg() and assume 1 core
                load_avg = os.getloadavg()[0]
                usage_pct = min(load_avg * 100, 100)

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Error reading CPU usage: {e}",
                ping_ms=elapsed,
            )

        elapsed = (time.monotonic() - start) * 1000

        if usage_pct > max_percent:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"CPU usage high: {usage_pct:.1f}% (threshold: {max_percent}%)",
                ping_ms=elapsed,
            )
        else:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.UP,
                message=f"CPU usage OK: {usage_pct:.1f}% (threshold: {max_percent}%)",
                ping_ms=elapsed,
            )
