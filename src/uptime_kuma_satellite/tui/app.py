"""SatApp and run_tui() for Uptime Kuma Satellite TUI."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from .main_screen import MainScreen


class SatApp(App):
    """Main application."""

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
    ]

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

    #global-config {
        height: 16;
        margin: 0 1;
        layout: horizontal;
    }

    #config-left {
        width: 50%;
        layout: vertical;
    }

    #config-right {
        width: 50%;
        layout: vertical;
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

    #help-footer {
        height: 3;
        content-align: center middle;
        color: $text-muted;
        background: $boost;
        text-style: dim;
    }

    #editor-dialog {
        width: 70;
        height: 43;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
        layout: vertical;
        overflow-y: auto;
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

    #label-name, #label-type, #label-push-url, #label-hostname, #label-interval, 
    #label-global-template, #label-monitor-type {
        margin-bottom: 0;
    }

    #name-input, #type-select, #push-url-input, #hostname-input, #interval-input, 
    #global-template-input, #monitor-type-input, #up-template-input, #down-template-input {
        margin-bottom: 1;
    }

    #params-container {
        border: solid $boost;
        padding: 1 2;
        height: 15;
        margin-bottom: 0;
        margin-top: 0;
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
        margin-top: 0;
        margin-bottom: 0;
    }

    #dialog-buttons Button {
        width: 16;
        margin: 0 1;
    }

    #editor-hint {
        text-align: center;
        margin-top: 0;
        padding-bottom: 0;
    }

    #template-editor {
        width: 80;
        height: 43;
        border: solid $primary;
        background: $surface;
        padding: 0 1;
        layout: vertical;
        overflow-y: auto;
    }

    #template-tabs {
        layout: horizontal;
        margin-bottom: 0;
        height: 3;
        padding: 0;
    }

    #template-tabs Button {
        width: 50%;
        text-align: center;
        padding: 0;
    }

    #template-tabs Button#btn-tab-global {
        border-left: none;
    }

    #template-tabs Button#btn-tab-monitor {
        border-right: none;
    }

    #global-section, #monitor-section {
        layout: vertical;
        padding: 0;
        height: 1fr;
        overflow-y: auto;
    }

    #global-section > *, #monitor-section > * {
        margin-left: 0;
        margin-right: 0;
    }

    #selected-type-info {
        margin-top: 0;
        margin-bottom: 0;
    }

    #selected-type-vars {
        margin-top: 0;
        margin-bottom: 0;
        width: 100%;
    }

    #monitor-type-help {
        margin-top: 0;
        margin-bottom: 0;
    }

    #monitor-types-table {
        height: 12;
        margin-bottom: 0;
    }

    #template-buttons {
        layout: horizontal;
        align: center middle;
        margin-top: 0;
        margin-bottom: 0;
        padding: 0;
        height: 3;
    }

    #template-buttons Button {
        width: 18;
        margin: 0;
    }

    #template-hint {
        text-align: center;
        margin-top: 0;
        margin-bottom: 0;
        padding: 0;
        height: 1;
    }

    #global-default-hint {
        margin-top: 0;
        margin-bottom: 0;
    }

    #global-default-value {
        margin-top: 0;
        margin-bottom: 0;
        padding-left: 1;
        color: $success;
    }

    #global-vars-help {
        margin-top: 0;
        margin-bottom: 0;
    }

    #label-up-template, #label-down-template {
        margin-top: 0;
        margin-bottom: 0;
    }

    #up-template-input, #down-template-input {
        margin-top: 0;
        margin-bottom: 0;
    }

    #up-vars-help, #down-vars-help {
        margin-top: 0;
        margin-bottom: 0;
    }

    #label-default {
        margin-top: 0;
        margin-bottom: 0;
    }

    #default-preview {
        margin-top: 0;
        margin-bottom: 0;
        color: $text-muted;
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
