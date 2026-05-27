"""Process monitor - check if a process is running."""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import time

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

        running = False
        matched_process = ""

        if platform.system() == "Windows":
            import subprocess
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {proc_name}", "/FO", "CSV", "/NH"],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.strip().splitlines():
                    if proc_name.lower() in line.lower():
                        running = True
                        matched_process = line
                        break
            except Exception as e:
                elapsed = (time.monotonic() - start) * 1000
                return MonitorResult(
                    monitor_name=self.config.name,
                    monitor_type=self.type_name,
                    status=MonitorStatus.DOWN,
                    message=f"Error checking process '{proc_name}': {e}",
                    ping_ms=elapsed,
                )
        else:
            try:
                import subprocess
                result = subprocess.run(
                    ["pgrep", "-f", proc_name],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    running = True
                    pids = result.stdout.strip().splitlines()
                    matched_process = f"PIDs: {', '.join(pids[:5])}"
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

        if running:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.UP,
                message=f"Process '{proc_name}' is running. {matched_process}",
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
