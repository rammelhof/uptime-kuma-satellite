"""Textual TUI for Uptime Kuma Satellite.

This module re-exports from the new package structure for backward compatibility.
"""

from .app import SatApp, run_tui
from .main_screen import MainScreen
from .editor_screen import MonitorEditorScreen

__all__ = ["SatApp", "run_tui", "MainScreen", "MonitorEditorScreen"]
