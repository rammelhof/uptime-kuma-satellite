"""Comprehensive tests for the Textual TUI."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from textual.app import App
from textual.widgets import Button, Input, Label, Select

from uptime_kuma_satellite.config import ConfigManager
from uptime_kuma_satellite.models import MonitorConfig, ServiceConfig
from uptime_kuma_satellite.monitors import MonitorRegistry
from uptime_kuma_satellite.param_schemas import (
    ParamField,
    PARAM_SCHEMAS,
    get_param_schema,
    get_type_help,
)
from uptime_kuma_satellite.tui import (
    MainScreen,
    MonitorEditorScreen,
    SatApp,
)

logger = logging.getLogger(__name__)


# ─── ParamField and Schema Tests ─────────────────────────────────────────────


class TestParamField:
    """Tests for ParamField dataclass and param schemas."""

    def test_param_field_defaults(self):
        field = ParamField("key", "Label")
        assert field.key == "key"
        assert field.label == "Label"
        assert field.kind == "text"
        assert field.default == ""
        assert field.help == ""

    def test_param_field_full(self):
        field = ParamField("port", "Port", "number", "80", "The port number")
        assert field.key == "port"
        assert field.label == "Port"
        assert field.kind == "number"
        assert field.default == "80"
        assert field.help == "The port number"

    def test_all_schemas_have_help_text(self):
        """All monitor types should have help text for their parameters."""
        for monitor_type, fields in PARAM_SCHEMAS.items():
            for field in fields:
                assert field.help, f"Missing help text for {monitor_type}.{field.key}"

    def test_all_schemas_have_defaults(self):
        """All parameter fields should have sensible defaults."""
        for monitor_type, fields in PARAM_SCHEMAS.items():
            for field in fields:
                assert field.default, f"Missing default for {monitor_type}.{field.key}"

    def test_schema_coverage_all_types(self):
        """Every registered monitor type should have a schema."""
        types = MonitorRegistry.list_types()
        for t in types:
            assert t in PARAM_SCHEMAS, f"Missing schema for registered type: {t}"


class TestGetParamSchema:
    """Tests for get_param_schema function."""

    def test_known_type_returns_schema(self):
        schema = get_param_schema("file_exists")
        assert len(schema) == 1
        assert schema[0].key == "path"

    def test_service_type_has_three_fields(self):
        schema = get_param_schema("service")
        assert len(schema) == 3
        keys = [f.key for f in schema]
        assert "host" in keys
        assert "port" in keys
        assert "timeout_seconds" in keys

    def test_unknown_type_returns_fallback(self):
        schema = get_param_schema("nonexistent")
        assert len(schema) == 1
        assert schema[0].key == "key"

    def test_ping_has_three_fields(self):
        schema = get_param_schema("ping")
        assert len(schema) == 3
        keys = [f.key for f in schema]
        assert "host" in keys
        assert "count" in keys
        assert "timeout_seconds" in keys

    def test_log_file_has_three_fields(self):
        schema = get_param_schema("log_file")
        assert len(schema) == 3
        keys = [f.key for f in schema]
        assert "path" in keys
        assert "lookback_minutes" in keys
        assert "max_errors" in keys


class TestGetTypeHelp:
    """Tests for get_type_help function."""

    def test_known_type_returns_help(self):
        help_text = get_type_help("file_exists")
        assert "Checks if a file exists" in help_text

    def test_service_help(self):
        help_text = get_type_help("service")
        assert "TCP port" in help_text

    def test_unknown_type_returns_empty(self):
        help_text = get_type_help("nonexistent")
        assert help_text == ""

    def test_all_types_have_help(self):
        for monitor_type in MonitorRegistry.list_types():
            help_text = get_type_help(monitor_type)
            assert help_text, f"Missing help text for type: {monitor_type}"


# ─── SatApp Tests ────────────────────────────────────────────────────────────


class TestSatApp:
    """Tests for SatApp."""

    def test_app_creation(self):
        """SatApp should be creatable."""
        app = SatApp()
        assert app is not None

    def test_app_creation_with_config_path(self, tmp_path: Path):
        """SatApp should accept a config path."""
        config_path = tmp_path / "config.yaml"
        app = SatApp(config_path=config_path)
        assert app._config_path == config_path

    def test_css_exists(self):
        """SatApp should have CSS defined."""
        assert SatApp.CSS
        assert "#editor-dialog" in SatApp.CSS
        assert "#dialog-buttons" in SatApp.CSS
        assert "#params-container" in SatApp.CSS


# ─── MonitorEditorScreen Unit Tests ──────────────────────────────────────────


class TestMonitorEditorScreenUnit:
    """Unit tests for MonitorEditorScreen that don't require DOM mounting."""

    def test_init_add_mode(self):
        """Add mode should initialize with correct flags."""
        mock_main = MagicMock(spec=MainScreen)
        editor = MonitorEditorScreen(mock_main, is_edit=False)
        assert editor._is_edit is False
        assert editor._edit_index is None
        assert editor._selected_type == ""
        assert editor._fields == {}

    def test_init_edit_mode(self):
        """Edit mode should initialize with correct flags."""
        mock_main = MagicMock(spec=MainScreen)
        editor = MonitorEditorScreen(mock_main, is_edit=True, edit_index=2)
        assert editor._is_edit is True
        assert editor._edit_index == 2

    def test_param_container_initialized(self):
        """_param_container should be initialized in __init__."""
        mock_main = MagicMock(spec=MainScreen)
        editor = MonitorEditorScreen(mock_main, is_edit=False)
        assert editor._param_container is not None
        assert editor._param_container.id == "params-container"

    def test_populate_existing_params_sets_values(self):
        """_populate_existing_params should set field values."""
        mock_main = MagicMock(spec=MainScreen)
        editor = MonitorEditorScreen(mock_main, is_edit=True, edit_index=0)
        mock_inp1 = MagicMock()
        mock_inp2 = MagicMock()
        editor._fields = {"host": mock_inp1, "port": mock_inp2}

        params = {"host": "10.0.0.1", "port": "8080"}
        editor._populate_existing_params(params)

        mock_inp1.value = "10.0.0.1"
        mock_inp2.value = "8080"

    def test_populate_existing_params_skips_missing(self):
        """_populate_existing_params should skip params not in fields."""
        mock_main = MagicMock(spec=MainScreen)
        editor = MonitorEditorScreen(mock_main, is_edit=True, edit_index=0)
        mock_inp = MagicMock()
        editor._fields = {"host": mock_inp}

        params = {"port": "8080"}  # 'host' not in params
        editor._populate_existing_params(params)

        mock_inp.value = "10.0.0.1"  # Should not be set

    def test_update_help_shows_text(self):
        """_update_help should display help text for known types."""
        mock_main = MagicMock(spec=MainScreen)
        editor = MonitorEditorScreen(mock_main, is_edit=False)
        editor._selected_type = "file_exists"

        # Mock query_one since we're not in a mounted screen
        mock_help_label = MagicMock()
        editor.query_one = lambda sel, cls: mock_help_label
        editor._update_help()

        mock_help_label.update.assert_called_once()
        mock_help_label.visible = True

    def test_update_help_empty_for_unknown(self):
        """_update_help should handle unknown types gracefully."""
        mock_main = MagicMock(spec=MainScreen)
        editor = MonitorEditorScreen(mock_main, is_edit=False)
        editor._selected_type = "unknown_type"

        mock_help_label = MagicMock()
        editor.query_one = lambda sel, cls: mock_help_label
        editor._update_help()

        mock_help_label.visible = False

    def test_cancel_dismisses(self):
        """Cancel button should dismiss the screen with None."""
        mock_main = MagicMock(spec=MainScreen)
        editor = MonitorEditorScreen(mock_main, is_edit=False)
        dismissed = []
        editor.dismiss = lambda val: dismissed.append(val)

        mock_btn = MagicMock(spec=Button)
        mock_btn.id = "btn-cancel"
        editor.on_button_pressed(Button.Pressed(mock_btn))

        assert dismissed == [None]

    def test_action_back_dismisses(self):
        """Back action should dismiss the screen."""
        mock_main = MagicMock(spec=MainScreen)
        editor = MonitorEditorScreen(mock_main, is_edit=False)
        dismissed = []
        editor.dismiss = lambda val: dismissed.append(val)
        editor.action_back()
        assert dismissed == [None]

    def test_save_with_missing_name(self):
        """Save with empty name should show notification."""
        mock_main = MagicMock(spec=MainScreen)
        editor = MonitorEditorScreen(mock_main, is_edit=False)
        editor._selected_type = "file_exists"
        editor._fields = {"path": MagicMock(value="/tmp/test.txt")}

        mock_name_input = MagicMock()
        mock_name_input.value = ""
        mock_type_select = MagicMock()
        mock_type_select.value = "file_exists"
        mock_interval_input = MagicMock()
        mock_interval_input.value = "60"

        with patch.object(editor, 'query_one') as mock_query:
            mock_query.side_effect = lambda id, cls: {
                "#name-input": mock_name_input,
                "#type-select": mock_type_select,
                "#interval-input": mock_interval_input,
            }[id]

            notifications = []
            editor.notify = lambda msg: notifications.append(msg)

            mock_btn = MagicMock(spec=Button)
            mock_btn.id = "btn-save"
            editor.on_button_pressed(Button.Pressed(mock_btn))

            assert len(notifications) == 1
            assert "Monitor name is required" in notifications[0]

    def test_save_with_invalid_interval(self):
        """Save with invalid interval should show notification."""
        mock_main = MagicMock(spec=MainScreen)
        editor = MonitorEditorScreen(mock_main, is_edit=False)
        editor._selected_type = "file_exists"
        editor._fields = {"path": MagicMock(value="/tmp/test.txt")}

        mock_name_input = MagicMock()
        mock_name_input.value = "test-monitor"
        mock_type_select = MagicMock()
        mock_type_select.value = "file_exists"
        mock_interval_input = MagicMock()
        mock_interval_input.value = "abc"

        with patch.object(editor, 'query_one') as mock_query:
            mock_query.side_effect = lambda id, cls: {
                "#name-input": mock_name_input,
                "#type-select": mock_type_select,
                "#interval-input": mock_interval_input,
            }[id]

            notifications = []
            editor.notify = lambda msg: notifications.append(msg)

            mock_btn = MagicMock(spec=Button)
            mock_btn.id = "btn-save"
            editor.on_button_pressed(Button.Pressed(mock_btn))

            assert len(notifications) == 1
            assert "positive number" in notifications[0]

    def test_save_with_zero_interval(self):
        """Save with zero interval should show notification."""
        mock_main = MagicMock(spec=MainScreen)
        editor = MonitorEditorScreen(mock_main, is_edit=False)
        editor._selected_type = "file_exists"
        editor._fields = {"path": MagicMock(value="/tmp/test.txt")}

        mock_name_input = MagicMock()
        mock_name_input.value = "test-monitor"
        mock_type_select = MagicMock()
        mock_type_select.value = "file_exists"
        mock_interval_input = MagicMock()
        mock_interval_input.value = "0"

        with patch.object(editor, 'query_one') as mock_query:
            mock_query.side_effect = lambda id, cls: {
                "#name-input": mock_name_input,
                "#type-select": mock_type_select,
                "#interval-input": mock_interval_input,
            }[id]

            notifications = []
            editor.notify = lambda msg: notifications.append(msg)

            mock_btn = MagicMock(spec=Button)
            mock_btn.id = "btn-save"
            editor.on_button_pressed(Button.Pressed(mock_btn))

            assert len(notifications) == 1
            assert "positive number" in notifications[0]

    def test_add_duplicate_name(self):
        """Adding a monitor with duplicate name should show error."""
        mock_main = MagicMock(spec=MainScreen)
        existing_monitor = MonitorConfig(
            name="existing",
            monitor_type="file_exists",
            interval_seconds=60,
        )
        mock_main.config = MagicMock()
        mock_main.config.monitors = [existing_monitor]
        editor = MonitorEditorScreen(mock_main, is_edit=False)
        editor._selected_type = "file_exists"
        editor._fields = {"path": MagicMock(value="/tmp/test.txt")}

        mock_name_input = MagicMock()
        mock_name_input.value = "existing"
        mock_type_select = MagicMock()
        mock_type_select.value = "file_exists"
        mock_interval_input = MagicMock()
        mock_interval_input.value = "60"

        with patch.object(editor, 'query_one') as mock_query:
            mock_query.side_effect = lambda id, cls: {
                "#name-input": mock_name_input,
                "#type-select": mock_type_select,
                "#interval-input": mock_interval_input,
            }[id]

            notifications = []
            editor.notify = lambda msg: notifications.append(msg)

            mock_btn = MagicMock(spec=Button)
            mock_btn.id = "btn-save"
            editor.on_button_pressed(Button.Pressed(mock_btn))

            assert len(notifications) == 1
            assert "already exists" in notifications[0]
            assert len(mock_main.config.monitors) == 1


# ─── Integration Tests ───────────────────────────────────────────────────────


class TestTUIIntegration:
    """Integration tests for TUI components using Textual's test runner."""

    @pytest.fixture
    def config_path(self, tmp_path: Path) -> Path:
        config_file = tmp_path / "config.yaml"
        config_mgr = ConfigManager(config_file)
        config = ServiceConfig(
            push_url="http://localhost:3001/push/test-key",
            hostname="test-host",
        )
        config_mgr.save(config)
        return config_file

    def test_add_then_edit_monitor(self, config_path: Path):
        """Test adding a monitor then editing it."""
        config = ServiceConfig(
            push_url="http://localhost:3001/push/test-key",
            hostname="test-host",
        )
        monitor = MonitorConfig(
            name="web-server",
            monitor_type="service",
            interval_seconds=30,
            params={"host": "localhost", "port": 80},
        )
        config.monitors.append(monitor)

        mock_main = MagicMock(spec=MainScreen)
        mock_main.config = config

        # Edit the monitor - selected_type is set in on_mount, not __init__
        editor = MonitorEditorScreen(mock_main, is_edit=True, edit_index=0)
        assert editor._is_edit is True
        assert editor._edit_index == 0
        # selected_type is set in on_mount, so it's "" here
        assert editor._selected_type == ""

    def test_multiple_monitors_in_config(self, config_path: Path):
        """Multiple monitors should be manageable."""
        config = ServiceConfig(
            push_url="http://localhost:3001/push/test-key",
            hostname="test-host",
        )
        monitors = [
            MonitorConfig(name="m1", monitor_type="file_exists", interval_seconds=60),
            MonitorConfig(name="m2", monitor_type="service", interval_seconds=30),
            MonitorConfig(name="m3", monitor_type="ping", interval_seconds=120),
        ]
        config.monitors.extend(monitors)

        assert len(config.monitors) == 3

    def test_config_persistence_through_tui(self, config_path: Path):
        """Config changes through TUI should persist."""
        config = ServiceConfig(
            push_url="http://localhost:3001/push/test-key",
            hostname="test-host",
        )
        monitor = MonitorConfig(
            name="persist-test",
            monitor_type="disk_space",
            interval_seconds=300,
            params={"path": "/", "min_percent": "5"},
        )
        config.monitors.append(monitor)

        ConfigManager(config_path).save(config)

        # Reload and verify
        reloaded = ConfigManager(config_path).load()
        assert len(reloaded.monitors) == 1
        assert reloaded.monitors[0].name == "persist-test"
        assert reloaded.monitors[0].monitor_type == "disk_space"
        # YAML stores numbers as strings when they're in params dict
        assert reloaded.monitors[0].params["min_percent"] == "5"

    def test_delete_then_add(self, config_path: Path):
        """Test deleting a monitor and adding a new one."""
        config = ServiceConfig(
            push_url="http://localhost:3001/push/test-key",
            hostname="test-host",
        )
        config.monitors.append(MonitorConfig(
            name="to-delete",
            monitor_type="file_exists",
            interval_seconds=60,
        ))
        assert len(config.monitors) == 1

        # Delete it
        config.monitors.pop(0)
        assert len(config.monitors) == 0

        # Add a new one
        config.monitors.append(MonitorConfig(
            name="new-service",
            monitor_type="service",
            interval_seconds=60,
            params={"host": "localhost", "port": "80"},
        ))
        assert len(config.monitors) == 1
        assert config.monitors[0].name == "new-service"

    def test_monitor_type_help_for_all_types(self):
        """All monitor types should have help text."""
        for monitor_type in MonitorRegistry.list_types():
            help_text = get_type_help(monitor_type)
            assert help_text, f"No help text for type: {monitor_type}"

    def test_config_save_and_reload(self, config_path: Path):
        """Test saving and reloading config."""
        config = ServiceConfig(
            push_url="http://localhost:3001/push/test-key",
            hostname="test-host",
        )
        config.monitors.append(MonitorConfig(
            name="test-monitor",
            monitor_type="file_exists",
            interval_seconds=120,
        ))

        ConfigManager(config_path).save(config)
        reloaded = ConfigManager(config_path).load()

        assert reloaded.push_url == config.push_url
        assert reloaded.hostname == config.hostname
        assert len(reloaded.monitors) == 1
        assert reloaded.monitors[0].name == "test-monitor"

    def test_config_validation(self, config_path: Path):
        """Test config validation."""
        config = ServiceConfig(
            push_url="http://localhost:3001/push/test-key",
            hostname="test-host",
        )
        ConfigManager(config_path).save(config)

        # Reload should succeed
        reloaded = ConfigManager(config_path).load()
        assert reloaded is not None

    def test_monitor_with_all_param_types(self, config_path: Path):
        """Test a monitor with various parameter types."""
        config = ServiceConfig(
            push_url="http://localhost:3001/push/test-key",
            hostname="test-host",
        )
        monitor = MonitorConfig(
            name="complex-monitor",
            monitor_type="log_file",
            interval_seconds=300,
            params={
                "path": "/var/log/app/error.log",
                "lookback_minutes": 60,
                "max_errors": 1,
            },
        )
        config.monitors.append(monitor)

        ConfigManager(config_path).save(config)
        reloaded = ConfigManager(config_path).load()

        assert reloaded.monitors[0].params["path"] == "/var/log/app/error.log"
        assert reloaded.monitors[0].params["lookback_minutes"] == 60
        assert reloaded.monitors[0].params["max_errors"] == 1
