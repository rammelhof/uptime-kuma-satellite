"""File existence monitor."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from . import BaseMonitor, MonitorRegistry
from ..models import MonitorConfig, MonitorResult, MonitorStatus

logger = logging.getLogger(__name__)


@MonitorRegistry.register
class FileExistsMonitor(BaseMonitor):
    """Check if a file exists."""

    type_name = "file_exists"

    def validate_config(self) -> list[str]:
        errors = []
        if "path" not in self.config.params:
            errors.append("Missing 'path' parameter")
        return errors

    def check(self) -> MonitorResult:
        start = time.monotonic()
        path_str = self.config.params.get("path", "")
        path = Path(path_str)

        exists = path.exists()
        elapsed = (time.monotonic() - start) * 1000

        # Store data for template rendering
        self._last_data = {"file_path": path_str}

        if exists:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.UP,
                message=f"File exists: {path_str}",
                ping_ms=elapsed,
            )
        else:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"File missing: {path_str}",
                ping_ms=elapsed,
            )
