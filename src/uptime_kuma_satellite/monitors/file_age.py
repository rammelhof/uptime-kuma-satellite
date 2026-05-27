"""File age monitor - checks if a file is older than a threshold."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from . import BaseMonitor, MonitorRegistry
from ..models import MonitorConfig, MonitorResult, MonitorStatus

logger = logging.getLogger(__name__)


@MonitorRegistry.register
class FileAgeMonitor(BaseMonitor):
    """Check if a file is older than a specified age threshold."""

    type_name = "file_age"

    def validate_config(self) -> list[str]:
        errors = []
        if "path" not in self.config.params:
            errors.append("Missing 'path' parameter")
        if "max_age_seconds" not in self.config.params:
            errors.append("Missing 'max_age_seconds' parameter")
        return errors

    def check(self) -> MonitorResult:
        start = time.monotonic()
        path_str = self.config.params.get("path", "")
        max_age = self.config.params.get("max_age_seconds", 3600)
        path = Path(path_str)

        if not path.exists():
            elapsed = (time.monotonic() - start) * 1000
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"File does not exist: {path_str}",
                ping_ms=elapsed,
            )

        mtime = path.stat().st_mtime
        age_seconds = time.time() - mtime
        elapsed = (time.monotonic() - start) * 1000

        if age_seconds > max_age:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"File too old ({age_seconds:.0f}s > {max_age}s): {path_str}",
                ping_ms=elapsed,
            )
        else:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.UP,
                message=f"File fresh ({age_seconds:.0f}s < {max_age}s): {path_str}",
                ping_ms=elapsed,
            )
