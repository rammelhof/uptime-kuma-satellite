"""Load average monitor."""

from __future__ import annotations

import logging
import os
import time

from . import BaseMonitor, MonitorRegistry
from ..models import MonitorConfig, MonitorResult, MonitorStatus

logger = logging.getLogger(__name__)


@MonitorRegistry.register
class LoadAverageMonitor(BaseMonitor):
    """Check system load average against a threshold."""

    type_name = "load_average"

    def validate_config(self) -> list[str]:
        errors = []
        if "max_load" not in self.config.params:
            errors.append("Missing 'max_load' parameter")
        return errors

    def check(self) -> MonitorResult:
        start = time.monotonic()
        max_load = self.config.params.get("max_load", 1.0)

        try:
            load1, load5, load15 = os.getloadavg()
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Error reading load average: {e}",
                ping_ms=elapsed,
            )

        elapsed = (time.monotonic() - start) * 1000

        if load1 >= max_load:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Load average high: 1m={load1:.2f}, 5m={load5:.2f}, 15m={load15:.2f} (threshold: {max_load})",
                ping_ms=elapsed,
            )
        else:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.UP,
                message=f"Load average OK: 1m={load1:.2f}, 5m={load5:.2f}, 15m={load15:.2f} (threshold: {max_load})",
                ping_ms=elapsed,
            )
