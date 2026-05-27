"""Textual TUI for Uptime Kuma Satellite."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Input,
    Label,
    Select,
    Static,
)

from ..config import ConfigManager
from ..models import MonitorConfig, MonitorResult, ServiceConfig, MonitorStatus
from ..monitors import MonitorRegistry
from ..client import UptimeKumaClient
from .editor_screen import MonitorEditorScreen

logger = logging.getLogger("uks.tui")


class MainScreen(Screen):
    """Main TUI screen with monitor status and controls."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "run_all", "Run All"),
        Binding("s", "save_config", "Save Config"),
        Binding("a", "add_monitor", "Add Monitor"),
        Binding("e", "edit_monitor", "Edit Monitor"),
        Binding("d", "delete_monitor", "Delete Monitor"),
        Binding("t", "toggle_monitor", "Toggle Monitor"),
        Binding("l", "load_config", "Load Config"),
    ]

    def __init__(self, config_path: Path | None = None) -> None:
        super().__init__()
        self.config_mgr = ConfigManager(config_path)
        self.config: ServiceConfig | None = None
        self._results: dict[str, dict] = {}

    def compose(self) -> ComposeResult:
        with Container():
            yield Static("Uptime Kuma Satellite", id="title")
            yield Label(id="status-bar")
            yield DataTable(id="monitors-table")
            yield Label(id="message-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._load_config()
        self._setup_table()

    def _load_config(self) -> None:
        try:
            self.config = self.config_mgr.load()
            if self.config.push_url:
                self._update_status_bar()
        except Exception as e:
            self._set_message(f"Error loading config: {e}")

    def _setup_table(self) -> None:
        table = self.query_one("#monitors-table", DataTable)
        table.add_columns("Name", "Type", "Status", "Interval", "Enabled", "Last Check", "Message")
        table.zebra_stripes = True
        table.cursor_type = "row"
        self._refresh_table()

    def _refresh_table(self) -> None:
        if not self.config:
            return

        table = self.query_one("#monitors-table", DataTable)
        table.clear()

        for monitor in self.config.monitors:
            result = self._results.get(monitor.name, {})
            status = result.get("status", "?")
            last_check = result.get("last_check", "-")
            message = result.get("message", "")

            table.add_row(
                monitor.name,
                monitor.monitor_type,
                status,
                f"{monitor.interval_seconds}s",
                "Yes" if monitor.enabled else "No",
                last_check,
                message[:50],
            )

    def _update_status_bar(self) -> None:
        if not self.config:
            return
        bar = self.query_one("#status-bar", Label)
        bar.update(
            f"Push URL: {self.config.push_url} | "
            f"Monitors: {len(self.config.monitors)} | "
            f"Config: {self.config_mgr.config_path}"
        )

    def _set_message(self, msg: str) -> None:
        self.query_one("#message-bar", Label).update(msg)

    def _get_selected_monitor(self) -> tuple[int, MonitorConfig] | None:
        """Get the currently selected monitor and its index."""
        table = self.query_one("#monitors-table", DataTable)
        row_index = table.cursor_row
        if row_index is None or row_index < 0:
            return None
        if row_index >= len(table.rows):
            return None
        row = table.get_row_at(row_index)
        if not row:
            return None
        name = row[0]
        for i, m in enumerate(self.config.monitors):
            if m.name == name:
                return (i, m)
        return None

    @on(DataTable.RowSelected, "#monitors-table")
    def _row_selected(self, event: DataTable.RowSelected) -> None:
        row_index = event.cursor_row
        table = event.data_table
        if row_index is None or row_index < 0 or row_index >= len(table.rows):
            return
        row = table.get_row_at(row_index)
        if row:
            name = row[0]
            mtype = row[1]
            self._set_message(f"Selected: {name} ({mtype}) — Press 'e' to edit, 'd' to delete")

    def _run_monitor(self, monitor: MonitorConfig) -> None:
        """Run a single monitor check."""
        try:
            instance = MonitorRegistry.create(monitor)
            result = instance.check()

            self._results[monitor.name] = {
                "status": result.status.value.upper(),
                "last_check": datetime.now().strftime("%H:%M:%S"),
                "message": result.message,
                "success": True,
            }
        except Exception as e:
            self._results[monitor.name] = {
                "status": "ERR",
                "last_check": datetime.now().strftime("%H:%M:%S"),
                "message": str(e),
                "success": False,
            }

    def action_run_all(self) -> None:
        if not self.config:
            return
        self._set_message("Running all monitors...")

        results: list = []
        for monitor in self.config.monitors:
            if monitor.enabled:
                self._run_monitor(monitor)
                entry = self._results.get(monitor.name, {})
                if entry.get("success"):
                    status = MonitorStatus.UP if entry["status"] == "UP" else MonitorStatus.DOWN
                    results.append(MonitorResult(
                        monitor_name=monitor.name,
                        monitor_type=monitor.monitor_type,
                        status=status,
                        message=entry["message"],
                    ))

        with UptimeKumaClient(self.config.push_url) as client:
            if results:
                client.report_aggregated(results)

        self._refresh_table()
        self._set_message("✓ All monitors completed")

    def action_save_config(self) -> None:
        if not self.config:
            return
        try:
            self.config_mgr.save(self.config)
            self._set_message("✓ Configuration saved")
        except Exception as e:
            self._set_message(f"✗ Save failed: {e}")

    def action_load_config(self) -> None:
        self._load_config()
        self._refresh_table()
        self._set_message("✓ Configuration reloaded")

    def action_add_monitor(self) -> None:
        self.app.push_screen(MonitorEditorScreen(self, is_edit=False))

    def action_edit_monitor(self) -> None:
        selected = self._get_selected_monitor()
        if not selected:
            self._set_message("No monitor selected. Use arrow keys to select one.")
            return
        idx, monitor = selected
        self.app.push_screen(MonitorEditorScreen(self, is_edit=True, edit_index=idx))

    def action_delete_monitor(self) -> None:
        if not self.config:
            return
        selected = self._get_selected_monitor()
        if not selected:
            self._set_message("No monitor selected")
            return
        idx, monitor = selected
        name = monitor.name
        self.config.monitors.pop(idx)
        self._refresh_table()
        self._set_message(f"Deleted monitor: {name}")

    def action_toggle_monitor(self) -> None:
        if not self.config:
            return
        selected = self._get_selected_monitor()
        if not selected:
            self._set_message("No monitor selected")
            return
        idx, monitor = selected
        monitor.enabled = not monitor.enabled
        self._refresh_table()
        self._set_message(f"Toggled: {monitor.name}")
