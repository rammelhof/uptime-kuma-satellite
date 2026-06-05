"""HTTP client for reporting to Uptime Kuma Push API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .models import MonitorResult, MonitorStatus
from .template import TemplateManager

logger = logging.getLogger(__name__)


class UptimeKumaClient:
    """Client for the Uptime Kuma Push API."""

    def __init__(
        self,
        push_url: str,
        timeout: float = 10.0,
        hostname: str = "",
        template_mgr: TemplateManager | None = None,
    ) -> None:
        self.push_url = push_url
        self.timeout = timeout
        self.hostname = hostname
        self.template_mgr = template_mgr or TemplateManager()
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

    def report_with_templates(
        self,
        results: list[MonitorResult],
        template_mgr: TemplateManager | None = None,
    ) -> bool:
        """Send aggregated results using template rendering.

        Args:
            results: List of MonitorResult objects.
            template_mgr: Optional template manager. Uses self.template_mgr if not provided.

        Returns:
            True if the report was sent successfully.
        """
        if not results:
            return True

        tm = template_mgr or self.template_mgr

        # Build result dicts with template data
        result_dicts: list[dict[str, Any]] = []
        for r in results:
            result_dicts.append({
                "monitor_name": r.monitor_name,
                "monitor_type": r.monitor_type,
                "status": r.status.value.upper(),
                "message": r.message,
                "data": {},  # Will be filled by caller if needed
            })

        message = tm.render_global_message(self.hostname, result_dicts)

        # Determine overall status
        all_up = all(r.status == MonitorStatus.UP for r in results)
        overall_status = MonitorStatus.UP if all_up else MonitorStatus.DOWN

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
                    "Template report: %s - %s",
                    overall_status.value,
                    message,
                )
                return True
            else:
                logger.error(
                    "Failed to send template report: HTTP %d - %s",
                    response.status_code,
                    response.text[:200],
                )
                return False
        except httpx.RequestError as e:
            logger.error("Failed to send template report: %s", e)
            return False

    def report_aggregated(self, results: list[MonitorResult]) -> bool:
        """Aggregate all monitor results and send a single push request.

        Uses template rendering if a global template is configured.
        Falls back to the original non-template format.
        """
        if not results:
            return True

        # Determine overall status
        all_up = all(r.status == MonitorStatus.UP for r in results)
        overall_status = MonitorStatus.UP if all_up else MonitorStatus.DOWN

        # Build message
        # Only use templates if a global template is explicitly set
        if self.template_mgr.global_template:
            result_dicts: list[dict[str, Any]] = []
            for r in results:
                result_dicts.append({
                    "monitor_name": r.monitor_name,
                    "monitor_type": r.monitor_type,
                    "status": r.status.value.upper(),
                    "message": r.message,
                    "data": r.data,
                })
            message = self.template_mgr.render_global_message(self.hostname, result_dicts)
        else:
            # Original non-template behavior
            hostname_prefix = f"{self.hostname}: " if self.hostname else ""
            if all_up:
                details = "; ".join(
                    f"{r.monitor_name}: {r.message}" for r in results
                )
                message = f"{hostname_prefix}All {len(results)} monitor(s) OK: {details}"
            else:
                down_monitors = [r for r in results if r.status == MonitorStatus.DOWN]
                up_count = len(results) - len(down_monitors)
                failures = []
                for r in down_monitors:
                    failures.append(f"{r.monitor_name}: {r.message}")
                message = f"{hostname_prefix}{len(down_monitors)} of {len(results)} monitor(s) DOWN ({up_count} OK): " + "; ".join(failures)

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
                    message,
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

    async def __aenter__(self) -> "UptimeKumaClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        self.close()
