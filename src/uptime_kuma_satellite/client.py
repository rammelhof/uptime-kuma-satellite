"""HTTP client for reporting to Uptime Kuma Push API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .models import MonitorResult, MonitorStatus

logger = logging.getLogger(__name__)


class UptimeKumaClient:
    """Client for the Uptime Kuma Push API."""

    def __init__(self, push_url: str, timeout: float = 10.0) -> None:
        self.push_url = push_url
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def report(self, result: MonitorResult) -> bool:
        """Send a monitoring result to Uptime Kuma."""
        params = result.to_push_params()
        try:
            response = self._client.get(self.push_url, params=params)
            if response.status_code == 200:
                logger.debug(
                    "Reported %s: %s - %s",
                    result.monitor_name,
                    result.status.value,
                    result.message,
                )
                return True
            else:
                logger.error(
                    "Failed to report %s: HTTP %d - %s",
                    result.monitor_name,
                    response.status_code,
                    response.text[:200],
                )
                return False
        except httpx.RequestError as e:
            logger.error("Failed to report %s: %s", result.monitor_name, e)
            return False

    def report_aggregated(self, results: list[MonitorResult]) -> bool:
        """Aggregate all monitor results and send a single push request.
        
        If all monitors are UP, sends one UP status.
        If any monitor is DOWN, sends one DOWN status with details.
        """
        if not results:
            return True

        # Determine overall status
        all_up = all(r.status == MonitorStatus.UP for r in results)
        overall_status = MonitorStatus.UP if all_up else MonitorStatus.DOWN

        # Build message with details
        if all_up:
            # All monitors up - send summary
            details = "; ".join(
                f"{r.monitor_name}: {r.message}" for r in results
            )
            message = f"All {len(results)} monitor(s) OK: {details}"
        else:
            # Some monitors down - send failure details
            down_monitors = [r for r in results if r.status == MonitorStatus.DOWN]
            up_count = len(results) - len(down_monitors)
            
            # Collect failure details
            failures = []
            for r in down_monitors:
                failures.append(f"{r.monitor_name}: {r.message}")
            
            message = f"{len(down_monitors)} of {len(results)} monitor(s) DOWN ({up_count} OK): " + "; ".join(failures)

        # Calculate average ping from all results
        avg_ping = sum(r.ping_ms for r in results) / len(results)

        # Build params
        params: dict[str, str] = {
            "status": overall_status.value,
            "msg": message,
        }
        if avg_ping > 0:
            params["ping"] = f"{avg_ping:.0f}"

        try:
            response = self._client.get(self.push_url, params=params)
            if response.status_code == 200:
                logger.info(
                    "Aggregated report: %s - %s",
                    overall_status.value,
                    message[:100],
                )
                return True
            else:
                logger.error(
                    "Failed to send aggregated report: HTTP %d - %s",
                    response.status_code,
                    response.text[:200],
                )
                return False
        except httpx.RequestError as e:
            logger.error("Failed to send aggregated report: %s", e)
            return False

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "UptimeKumaClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
