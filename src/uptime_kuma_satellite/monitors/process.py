"""Process monitor - check if a process is running via psutil."""

from __future__ import annotations

import logging
import time

import psutil

from . import BaseMonitor, MonitorRegistry
from ..models import MonitorConfig, MonitorResult, MonitorStatus

logger = logging.getLogger(__name__)


@MonitorRegistry.register
class ProcessMonitor(BaseMonitor):
    """Check if a process with a given name/command is running."""

    type_name = "process"

    def validate_config(self) -> list[str]:
        errors = []
        if "name" not in self.config.params:
            errors.append("Missing 'name' parameter (process name or command)")
        return errors

    def check(self) -> MonitorResult:
        start = time.monotonic()
        proc_name = self.config.params.get("name", "")

        try:
            matching = []
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    name = proc.info["name"] or ""
                    cmdline = " ".join(proc.info["cmdline"] or [])
                    if proc_name.lower() in name.lower() or proc_name.lower() in cmdline.lower():
                        matching.append(proc.info["pid"])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Error checking process '{proc_name}': {e}",
                ping_ms=elapsed,
            )

        elapsed = (time.monotonic() - start) * 1000

        if matching:
            pids = ", ".join(str(p) for p in matching[:5])
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.UP,
                message=f"Process '{proc_name}' is running ({len(matching)} match(es)). PIDs: {pids}",
                ping_ms=elapsed,
            )
        else:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Process '{proc_name}' is NOT running",
                ping_ms=elapsed,
            )
