#!/usr/bin/env python3
"""Debug script to test TUI edit dialog rendering."""
import sys
from pathlib import Path

# Ensure we're using the local package
sys.path.insert(0, str(Path(__file__).parent / "src"))

from textual.app import App
from textual.widgets import Static
from uptime_kuma_satellite.tui import SatApp, MainScreen
from uptime_kuma_satellite.tui.editor_screen import MonitorEditorScreen
from uptime_kuma_satellite.config import ConfigManager
from uptime_kuma_satellite.models import ServiceConfig, MonitorConfig
import tempfile

# Create a test config
with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False, mode='w') as f:
    config_path = Path(f.name)

config_mgr = ConfigManager(config_path)
config = ServiceConfig(
    push_url='http://localhost:3001/push/test-key',
    hostname='test-host',
)
config.monitors.append(MonitorConfig(
    name='test-monitor',
    monitor_type='service',
    interval_seconds=60,
    params={'host': 'localhost', 'port': 80},
))
config_mgr.save(config)
print(f"Config saved to: {config_path}")
print(f"Monitor: {config.monitors[0].name}, type: {config.monitors[0].monitor_type}")

# Create the app
app = SatApp(config_path)

# Test 1: Create the screen directly
print("\n=== Test 1: Create MonitorEditorScreen ===")
mock_main = type('MockMainScreen', (), {'config': config})()
screen = MonitorEditorScreen(mock_main, is_edit=True, edit_index=0)
print(f"Screen created: {screen}")
print(f"Screen _initial_name: {screen._initial_name}")
print(f"Screen _initial_type: {screen._initial_type}")
print(f"Screen _initial_interval: {screen._initial_interval}")
print(f"Screen _selected_type: {screen._selected_type}")

# Test 2: Check compose output with mock app
print("\n=== Test 2: Check compose output with mock app ===")
class MockApp(App):
    CSS = SatApp.CSS
    BINDINGS = []
    
    def compose(self):
        yield Static("Mock")

mock_app = MockApp()

# Push the screen to the mock app
mock_app.push_screen(screen)

# Now compose should work
composers = list(screen.compose())
print(f"Number of composables: {len(composers)}")
for i, comp in enumerate(composers):
    print(f"  {i}: {type(comp).__name__} - {comp}")

# Test 3: Check Select widget value
print("\n=== Test 3: Check Select widget ===")
for comp in composers:
    if hasattr(comp, 'id') and comp.id == "type-select":
        print(f"Select widget found!")
        print(f"  Select value: {comp.value}")
        print(f"  Select choices: {comp.choices}")
        break

# Test 4: Check Input widget values
print("\n=== Test 4: Check Input widgets ===")
for comp in composers:
    if hasattr(comp, 'id'):
        if comp.id == "name-input":
            print(f"Name input: value={comp.value}")
        elif comp.id == "interval-input":
            print(f"Interval input: value={comp.value}")

# Clean up
config_path.unlink()
print("\n=== Done ===")
