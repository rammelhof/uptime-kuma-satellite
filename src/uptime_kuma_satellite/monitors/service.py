"""Service monitor - check if a TCP port is open."""

from __future__ import annotations

import logging
import socket
import time

from . import BaseMonitor, MonitorRegistry
from ..models import MonitorConfig, MonitorResult, MonitorStatus

logger = logging.getLogger(__name__)


@MonitorRegistry.register
class ServiceMonitor(BaseMonitor):
    """Check if a TCP service is reachable on a given host:port."""

    type_name = "service"

    def validate_config(self) -> list[str]:
        errors = []
        if "host" not in self.config.params:
            errors.append("Missing 'host' parameter")
        if "port" not in self.config.params:
            errors.append("Missing 'port' parameter")
        return errors

    def check(self) -> MonitorResult:
        start = time.monotonic()
        host = self.config.params.get("host", "localhost")
        port = self.config.params.get("port", 80)
        timeout = self.config.params.get("timeout_seconds", 5)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.close()
            elapsed = (time.monotonic() - start) * 1000
            self._last_data = {
                "service_host": host,
                "service_port": port,
                "service_timeout": timeout,
            }
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.UP,
                message=f"Service {host}:{port} is reachable",
                ping_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            self._last_data = {
                "service_host": host,
                "service_port": port,
                "service_timeout": timeout,
            }
            return MonitorResult(
                monitor_name=self.config.name,
                monitor_type=self.type_name,
                status=MonitorStatus.DOWN,
                message=f"Service {host}:{port} unreachable: {e}",
                ping_ms=elapsed,
            )
