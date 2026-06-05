"""Scheduler that runs monitors at configured intervals."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from pathlib import Path

from .client import UptimeKumaClient
from .config import ConfigManager
from .models import MonitorConfig, MonitorResult, MonitorStatus
from .monitors import MonitorRegistry

logger = logging.getLogger(__name__)


class Scheduler:
    """Runs monitors at their configured intervals and sends aggregated reports."""

    def __init__(
        self,
        push_url: str,
        config_path: Path | None = None,
        default_interval: int = 60,
        hostname: str = "",
        global_template: str = "",
        monitor_templates: dict[str, dict[str, str]] | None = None,
    ) -> None:
        self.push_url = push_url
        self.default_interval = default_interval
        self.hostname = hostname
        self.global_template = global_template
        self.monitor_templates = monitor_templates or {}
        self._running = False
        self._config: dict[str, MonitorConfig] = {}
        self._config_path = config_path
        self._last_mtime: float | None = None

    def _reload_config(self) -> bool:
        """Reload config from file and update all settings. Returns True if config changed."""
        if not self._config_path or not self._config_path.exists():
            return False

        try:
            current_mtime = os.path.getmtime(self._config_path)
        except OSError:
            return False

        # No change since last check
        if current_mtime == self._last_mtime:
            return False

        logger.info("Config file changed, reloading...")
        try:
            config_mgr = ConfigManager(self._config_path)
            config = config_mgr.load()

            if not config.push_url:
                logger.warning("Config has no push URL, skipping reload")
                return False

            self._config = {m.name: m for m in config.monitors}
            self.push_url = config.push_url
            self.default_interval = config.default_interval
            self.hostname = config.hostname
            self.global_template = config.global_template
            self.monitor_templates = config.monitor_templates
            self._last_mtime = current_mtime

            logger.info("Config reloaded: %d monitors, interval=%ds, hostname=%s", len(self._config), self.default_interval, self.hostname)
            return True
        except Exception as e:
            logger.error("Failed to reload config: %s", e)
            return False

    def _collect_results(self, client: UptimeKumaClient) -> list[MonitorResult]:
        """Run all enabled monitors and collect results."""
        results: list[MonitorResult] = []
        for monitor in self._config.values():
            if not monitor.enabled:
                continue
            try:
                instance = MonitorRegistry.create(monitor)
                result = instance.check()
                result.data = instance.get_template_vars()
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
        self._stop_event = asyncio.Event()

        loop = asyncio.new_event_loop()
        self._loop = loop

        def _run() -> None:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._start_async())

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        self._thread = thread
        logger.info("Scheduler started with %d monitors", len(configs))

    async def _start_async(self) -> None:
        """Async main loop: run monitors at the global interval."""
        # Load config immediately so we use the correct interval/hostname/url
        if self._config_path and self._config_path.exists():
            self._reload_config()

        schedule_interval = self.default_interval
        logger.info("Schedule interval: %ds (global interval)", schedule_interval)

        from .template import TemplateManager

        self._client = UptimeKumaClient(
            self.push_url,
            hostname=self.hostname,
            template_mgr=TemplateManager(
                global_template=self.global_template,
                monitor_templates=self.monitor_templates,
            ),
        )

        # Run all monitors once immediately
        self._run_cycle(self._client)

        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=schedule_interval,
                )
            except asyncio.TimeoutError:
                pass

            # Watch for config file changes
            if self._config_path:
                config_changed = self._reload_config()

                # Re-create client if push_url or hostname changed
                if config_changed:
                    new_interval = self.default_interval
                    if new_interval != schedule_interval:
                        schedule_interval = new_interval
                        logger.info("Schedule interval changed to %ds", schedule_interval)

                    self._client.close()
                    self._client = UptimeKumaClient(
                        self.push_url,
                        hostname=self.hostname,
                        template_mgr=TemplateManager(
                            global_template=self.global_template,
                            monitor_templates=self.monitor_templates,
                        ),
                    )

            self._run_cycle(self._client)

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if hasattr(self, "_stop_event") and self._stop_event:
            self._stop_event.set()
        if hasattr(self, "_loop") and self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if hasattr(self, "_thread"):
            self._thread.join(timeout=5)
        if hasattr(self, "_client"):
            self._client.close()
        logger.info("Scheduler stopped")
