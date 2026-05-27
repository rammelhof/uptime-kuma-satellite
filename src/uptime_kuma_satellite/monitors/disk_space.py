"""Disk free space monitor."""

from __future__ import annotations

import logging
import shutil
import time

from . import BaseMonitor, MonitorRegistry
from ..models import MonitorConfig, MonitorResult, MonitorStatus

logger = logging.getLogger(__name__)


@MonitorRegistry.register
class DiskSpaceMonitor(BaseMonitor):
    """Check disk free space on a mount point."""

    type_name = "disk_space"

    def validate_config(self) -> list[str]:
        errors = []
        if "path" not in self.config.params:
            errors.append("Missing 'path' parameter")
        if "min_percent" not in self.config.params:
            errors.append("Missing 'min_percent' parameter")
        return errors

    def check(self) -> MonitorResult:
        start = time.monotonic()
        path_str = self.config.params.get("path", "/")
        min_percent = self.config.params.get("min_percent", 10)

        try:
            import shutil
            total, used, free = shutil.disk_usage(path_str)
            free_percent = (free / total) * 100 if total > 0 else 0
            free_gb = free / (1024 ** 3)
            total_gb = total / (1024 ** 3)
        except OSError as e:
            elapsed = (time.monotonic() - start) * 1000
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Cannot read disk usage for {path_str}: {e}",
                ping_ms=elapsed,
            )

        elapsed = (time.monotonic() - start) * 1000

        if free_percent < min_percent:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Low disk space on {path_str}: {free_percent:.1f}% free ({free_gb:.1f}GB of {total_gb:.1f}GB)",
                ping_ms=elapsed,
            )
        else:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.UP,
                message=f"Disk OK on {path_str}: {free_percent:.1f}% free ({free_gb:.1f}GB of {total_gb:.1f}GB)",
                ping_ms=elapsed,
            )
