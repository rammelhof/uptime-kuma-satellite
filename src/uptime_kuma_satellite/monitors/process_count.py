"""Process count monitor - check how many processes match a pattern via psutil."""

from __future__ import annotations

import logging
import time

import psutil

from . import BaseMonitor, MonitorRegistry
from ..models import MonitorConfig, MonitorResult, MonitorStatus

logger = logging.getLogger(__name__)


@MonitorRegistry.register
class ProcessCountMonitor(BaseMonitor):
    """Check that the number of processes matching a pattern is within a range."""

    type_name = "process_count"

    def validate_config(self) -> list[str]:
        errors = []
        if "pattern" not in self.config.params:
            errors.append("Missing 'pattern' parameter (process name or command pattern)")
        return errors

    def check(self) -> MonitorResult:
        start = time.monotonic()
        pattern = self.config.params.get("pattern", "")
        min_count = self.config.params.get("min_count", 1)
        max_count = self.config.params.get("max_count", 0)
        if max_count == 0:
            max_count = None

        try:
            matching_pids = []
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    name = proc.info["name"] or ""
                    cmdline = " ".join(proc.info["cmdline"] or [])
                    if pattern.lower() in name.lower() or pattern.lower() in cmdline.lower():
                        matching_pids.append(proc.info["pid"])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Error checking process count for '{pattern}': {e}",
                ping_ms=elapsed,
            )

        count = len(matching_pids)
        elapsed = (time.monotonic() - start) * 1000

        # Check min_count
        if count < min_count:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Found {count} process(es) matching '{pattern}' (minimum {min_count} expected). PIDs: {', '.join(str(p) for p in matching_pids[:10])}",
                ping_ms=elapsed,
            )

        # Check max_count if specified
        if max_count is not None and count > max_count:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Found {count} process(es) matching '{pattern}' (maximum {max_count} allowed). PIDs: {', '.join(str(p) for p in matching_pids[:10])}",
                ping_ms=elapsed,
            )

        return MonitorResult(
            monitor_name=self.config.name,
            monitor_type=self.type_name,
            status=MonitorStatus.UP,
            message=f"Found {count} process(es) matching '{pattern}' (min={min_count}, max={max_count}). PIDs: {', '.join(str(p) for p in matching_pids[:10])}",
            ping_ms=elapsed,
        )
