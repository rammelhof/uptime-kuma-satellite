"""Load average monitor - cross-platform via psutil."""

from __future__ import annotations

import logging
import time

import psutil

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
            # psutil.getloadavg() works on Linux and macOS
            load1, load5, load15 = psutil.getloadavg()
            num_cores = psutil.cpu_count(logical=True) or 1
            # Also report load per core for context
            load_per_core = load1 / num_cores
        except AttributeError:
            # Windows: psutil doesn't have getloadavg, estimate from CPU usage
            try:
                cpu_busy = psutil.cpu_percent(interval=1)
                load1 = load5 = load15 = cpu_busy / 100.0
                num_cores = psutil.cpu_count(logical=True) or 1
                load_per_core = load1 / num_cores
            except Exception as e:
                elapsed = (time.monotonic() - start) * 1000
                self._last_data = {
                    "load1": 0.0, "load5": 0.0, "load15": 0.0,
                    "load_per_core": 0.0, "num_cores": 1, "threshold": max_load,
                }
                return MonitorResult(
                    monitor_name=self.config.name,
                    monitor_type=self.type_name,
                    status=MonitorStatus.DOWN,
                    message=f"Error reading load average: {e}",
                    ping_ms=elapsed,
                )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            self._last_data = {
                "load1": 0.0, "load5": 0.0, "load15": 0.0,
                "load_per_core": 0.0, "num_cores": 1, "threshold": max_load,
            }
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Error reading load average: {e}",
                ping_ms=elapsed,
            )

        elapsed = (time.monotonic() - start) * 1000

        # Store data for template rendering
        self._last_data = {
            "load1": load1, "load5": load5, "load15": load15,
            "load_per_core": load_per_core, "num_cores": num_cores,
            "threshold": max_load,
        }

        if load1 >= max_load:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Load average high: 1m={load1:.2f}, 5m={load5:.2f}, 15m={load15:.2f} (per-core: {load_per_core:.2f}, {num_cores} cores) (threshold: {max_load})",
                ping_ms=elapsed,
            )
        else:
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.UP,
                message=f"Load average OK: 1m={load1:.2f}, 5m={load5:.2f}, 15m={load15:.2f} (per-core: {load_per_core:.2f}, {num_cores} cores) (threshold: {max_load})",
                ping_ms=elapsed,
            )
