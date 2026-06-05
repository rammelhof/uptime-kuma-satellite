"""Log file monitor - check for recent errors in a log file."""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from . import BaseMonitor, MonitorRegistry
from ..models import MonitorConfig, MonitorResult, MonitorStatus

logger = logging.getLogger(__name__)


@MonitorRegistry.register
class LogFileMonitor(BaseMonitor):
    """Monitor a log file for recent error entries."""

    type_name = "log_file"

    def validate_config(self) -> list[str]:
        errors = []
        if "path" not in self.config.params:
            errors.append("Missing 'path' parameter")
        if "lookback_minutes" not in self.config.params:
            errors.append("Missing 'lookback_minutes' parameter")
        if "max_errors" not in self.config.params:
            errors.append("Missing 'max_errors' parameter")
        return errors

    def check(self) -> MonitorResult:
        start = time.monotonic()
        path_str = self.config.params.get("path", "")
        lookback_minutes = self.config.params.get("lookback_minutes", 60)
        error_patterns_raw = self.config.params.get("error_patterns", "(default)")
        max_errors = self.config.params.get("max_errors", 1)

        path = Path(path_str)
        if not path.exists():
            elapsed = (time.monotonic() - start) * 1000
            self._last_data = {
                "log_path": path_str, "log_lookback_minutes": lookback_minutes,
                "log_error_count": 0, "log_last_error": "N/A", "log_max_errors": max_errors,
            }
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Log file does not exist: {path_str}",
                ping_ms=elapsed,
            )

        cutoff_time = time.time() - (lookback_minutes * 60)
        error_count = 0
        last_error = ""

        if error_patterns_raw and error_patterns_raw != "(default)":
            # Parse comma-separated regex patterns
            compiled = [re.compile(p.strip(), re.IGNORECASE) for p in error_patterns_raw.split(",") if p.strip()]
        else:
            compiled = [re.compile(r"(error|exception|fatal|critical)", re.IGNORECASE)]

        try:
            with open(path, "r", errors="replace") as f:
                for line in f:
                    # Check if line matches any error pattern
                    for pattern in compiled:
                        if pattern.search(line):
                            error_count += 1
                            last_error = line.strip()[:200]
                            break
                    if error_count >= max_errors:
                        break
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            self._last_data = {
                "log_path": path_str, "log_lookback_minutes": lookback_minutes,
                "log_error_count": 0, "log_last_error": str(e), "log_max_errors": max_errors,
            }
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Error reading log file {path_str}: {e}",
                ping_ms=elapsed,
            )

        elapsed = (time.monotonic() - start) * 1000

        # Store data for template rendering
        self._last_data = {
            "log_path": path_str,
            "log_lookback_minutes": lookback_minutes,
            "log_error_count": error_count,
            "log_last_error": last_error,
            "log_max_errors": max_errors,
        }

        if error_count > 0:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Found {error_count} error(s) in {path_str} (last: {last_error[:100]})",
                ping_ms=elapsed,
            )
        else:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.UP,
                message=f"No errors in {path_str} over last {lookback_minutes}min",
                ping_ms=elapsed,
            )
