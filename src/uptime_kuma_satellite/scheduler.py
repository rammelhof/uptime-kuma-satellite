"""Scheduler that runs monitors at configured intervals."""

from __future__ import annotations

import asyncio
import logging
import threading

from .client import UptimeKumaClient
from .models import MonitorConfig, MonitorResult, MonitorStatus
from .monitors import MonitorRegistry

logger = logging.getLogger(__name__)


class Scheduler:
    """Runs monitors at their configured intervals and sends aggregated reports."""

    def __init__(self, push_url: str) -> None:
        self.push_url = push_url
        self._running = False
        self._config: dict[str, MonitorConfig] = {}

    def _collect_results(self, client: UptimeKumaClient) -> list[MonitorResult]:
        """Run all enabled monitors and collect results."""
        results: list[MonitorResult] = []
        for monitor in self._config.values():
            if not monitor.enabled:
                continue
            try:
                instance = MonitorRegistry.create(monitor)
                result = instance.check()
                results.append(result)
            except Exception as e:
                logger.error("Monitor '%s' failed: %s", monitor.name, e)
                results.append(MonitorResult(
                    monitor_name=monitor.name,
                    monitor_type=monitor.monitor_type,
                    status=MonitorStatus.DOWN,
                    message=f"Error: {e}",
                ))
        return results

    def _run_cycle(self, client: UptimeKumaClient) -> None:
        """Run one complete cycle: check all monitors, send one aggregated report."""
        results = self._collect_results(client)
        if results:
            client.report_aggregated(results)
            up = sum(1 for r in results if r.status == MonitorStatus.UP)
            down = len(results) - up
            logger.info(
                "Cycle complete: %d UP, %d DOWN of %d monitor(s)",
                up, down, len(results),
            )

    def start(self, configs: list[MonitorConfig]) -> None:
        """Start the scheduler with the given monitor configs."""
        self._running = True
        self._config = {m.name: m for m in configs}

        loop = asyncio.new_event_loop()

        def _run() -> None:
            with UptimeKumaClient(self.push_url) as client:
                # Run all monitors once immediately and send aggregated report
                self._run_cycle(client)

            loop.call_soon_threadsafe(loop.stop)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        self._thread = thread
        logger.info("Scheduler started with %d monitors", len(configs))

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if hasattr(self, "_thread"):
            self._thread.join(timeout=5)
        logger.info("Scheduler stopped")
