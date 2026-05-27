"""SatApp and run_tui() for Uptime Kuma Satellite TUI."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Static

from .main_screen import MainScreen


class SatApp(App):
    """Main application."""

    CSS = """
    #title {
        text-align: center;
        text-style: bold;
        color: $primary;
        height: 3;
        content-align: center middle;
    }

    #status-bar {
        height: 3;
        content-align: center middle;
        margin-bottom: 1;
    }

    #monitors-table {
        height: 1fr;
        margin: 0 1;
    }

    #message-bar {
        height: 3;
        content-align: center middle;
        color: $text-muted;
    }

    #editor-dialog {
        width: 70;
        height: 60;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
        layout: vertical;
    }

    #dialog-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    #type-help {
        margin-bottom: 1;
        content-align: center middle;
    }

    #label-name, #label-type, #label-interval {
        margin-bottom: 0;
    }

    #name-input, #type-select, #interval-input {
        margin-bottom: 1;
    }

    #params-container {
        border: solid $boost;
        padding: 1 2;
        height: 12;
        margin-bottom: 1;
        layout: vertical;
        overflow-y: auto;
    }

    #params-container > Label {
        margin-left: 1;
        margin-bottom: 0;
    }

    #params-container > Input {
        margin-left: 1;
        margin-bottom: 0;
    }

    #dialog-buttons {
        layout: horizontal;
        align: center middle;
        margin-top: 1;
    }

    #dialog-buttons Button {
        width: 16;
        margin: 0 1;
    }

    #editor-hint {
        text-align: center;
        margin-top: 1;
        padding-bottom: 1;
    }
    """

    def __init__(self, config_path: Path | None = None) -> None:
        super().__init__()
        self._config_path = config_path

    def on_mount(self) -> None:
        self.push_screen(MainScreen(self._config_path))


def run_tui(config_path: Path | None = None) -> None:
    """Run the TUI application."""
    app = SatApp(config_path)
    app.run()
