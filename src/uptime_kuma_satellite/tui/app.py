"""SatApp and run_tui() for Uptime Kuma Satellite TUI."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult

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
        layout: grid;
        grid-size: 2;
        grid-gutter: 1 2;
    }

    #dialog-title {
        text-align: center;
        text-style: bold;
        column-span: 2;
        margin-bottom: 1;
    }

    #type-help {
        column-span: 2;
        margin-bottom: 1;
        content-align: center middle;
    }

    #params-container {
        column-span: 2;
        border: solid $boost;
        padding: 1 2;
        min-height: 3;
    }

    #params-container Label {
        margin-left: 1;
    }

    #params-container Input {
        margin-left: 1;
        margin-bottom: 1;
    }

    #dialog-buttons {
        align: center middle;
        column-span: 2;
        height: auto;
        padding: 0 1;
    }

    #editor-hint {
        text-align: center;
        column-span: 2;
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
