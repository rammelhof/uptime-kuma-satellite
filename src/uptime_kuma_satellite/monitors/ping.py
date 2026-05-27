"""Ping/ICMP monitor - check network reachability."""

from __future__ import annotations

import logging
import platform
import subprocess
import time

from . import BaseMonitor, MonitorRegistry
from ..models import MonitorConfig, MonitorResult, MonitorStatus

logger = logging.getLogger(__name__)


@MonitorRegistry.register
class PingMonitor(BaseMonitor):
    """Check network reachability via ping."""

    type_name = "ping"

    def validate_config(self) -> list[str]:
        errors = []
        if "host" not in self.config.params:
            errors.append("Missing 'host' parameter")
        return errors

    def check(self) -> MonitorResult:
        start = time.monotonic()
        host = self.config.params.get("host", "localhost")
        count = self.config.params.get("count", 3)
        timeout = self.config.params.get("timeout_seconds", 5)

        try:
            if platform.system() == "Windows":
                cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), host]
            else:
                cmd = ["ping", "-c", str(count), "-W", str(timeout), host]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout * count + 10,
            )

            elapsed = (time.monotonic() - start) * 1000

            if result.returncode == 0:
                # Try to extract avg ping time from output
                ping_ms = 0.0
                for line in result.stdout.splitlines():
                    if "avg" in line.lower() or "avrg" in line.lower():
                        parts = line.split("/")
                        for p in parts:
                            try:
                                ping_ms = float(p.strip().rstrip("ms"))
                                break
                            except ValueError:
                                continue
                        break

                return MonitorResult(
                    monitor_name=self.config.name,
                    monitor_type=self.type_name,
                    status=MonitorStatus.UP,
                    message=f"Host {host} is reachable (avg ping: {ping_ms:.0f}ms)",
                    ping_ms=ping_ms if ping_ms > 0 else elapsed,
                )
            else:
                return MonitorResult(
                    monitor_name=self.config.name,
                    monitor_type=self.type_name,
                    status=MonitorStatus.DOWN,
                    message=f"Host {host} is unreachable",
                    ping_ms=elapsed,
                )

        except subprocess.TimeoutExpired:
            elapsed = (time.monotonic() - start) * 1000
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Host {host} ping timed out after {timeout}s",
                ping_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Error pinging {host}: {e}",
                ping_ms=elapsed,
            )
