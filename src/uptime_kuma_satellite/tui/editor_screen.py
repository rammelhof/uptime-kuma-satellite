"""Monitor editor screen for adding/editing monitors."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select

from ..param_schemas import get_param_schema, get_type_help
from ..models import MonitorConfig
from ..monitors import MonitorRegistry


class MonitorEditorScreen(Screen):
    """Screen for adding or editing a monitor with per-field parameter inputs."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def __init__(self, main_screen: Any, is_edit: bool, edit_index: int | None = None) -> None:
        super().__init__()
        self._main_screen = main_screen
        self._is_edit = is_edit
        self._edit_index = edit_index
        self._selected_type = ""
        self._fields: dict[str, Input] = {}
        self._param_container = Container(id="params-container")

    def compose(self) -> ComposeResult:
        with Container(id="editor-dialog"):
            yield Label(id="dialog-title")
            yield Label(id="type-help")

            yield Label("Name:", id="label-name")
            yield Input(id="name-input")

            yield Label("Type:", id="label-type")
            yield Select(
                [(t, t) for t in MonitorRegistry.list_types()],
                id="type-select",
            )

            yield Label("Interval (seconds):", id="label-interval")
            yield Input(value="60", id="interval-input")

            # Parameter fields container
            yield self._param_container

            with Container(id="dialog-buttons"):
                yield Button("Save", id="btn-save")
                yield Button("Cancel", id="btn-cancel", variant="default")

            yield Label("[dim]Press Esc or click Cancel to exit[/dim]", id="editor-hint")

    def on_mount(self) -> None:
        if self._is_edit and self._edit_index is not None:
            self._setup_edit_mode()
        else:
            self._setup_add_mode()

    def _setup_edit_mode(self) -> None:
        """Setup for edit mode."""
        monitor = self._main_screen.config.monitors[self._edit_index]
        self.query_one("#dialog-title", Label).update(f"Edit Monitor: {monitor.name}")
        self.query_one("#name-input", Input).value = monitor.name
        self.query_one("#interval-input", Input).value = str(monitor.interval_seconds)

        self._selected_type = monitor.monitor_type
        self.query_one("#type-select", Select).value = monitor.monitor_type

        widgets = self._build_param_fields()
        for w in widgets:
            self._param_container.mount(w)
        self._populate_existing_params(monitor.params)
        self._update_help()

    def _setup_add_mode(self) -> None:
        """Setup for add mode."""
        self.query_one("#dialog-title", Label).update("Add New Monitor")
        first_type = MonitorRegistry.list_types()[0] if MonitorRegistry.list_types() else ""
        self._selected_type = first_type
        widgets = self._build_param_fields()
        for w in widgets:
            self._param_container.mount(w)
        self._update_help()
        self.query_one("#name-input", Input).focus()

    def _populate_existing_params(self, params: dict[str, Any]) -> None:
        """Update input field values with existing params (for edit mode)."""
        for key, inp in self._fields.items():
            if key in params:
                inp.value = str(params[key])

    def _build_param_fields(self) -> list:
        """Build parameter input fields based on selected type.
        
        Returns a list of widgets (Label, Input, Label triples) for each field.
        The caller is responsible for mounting them.
        """
        self._fields.clear()
        schema = get_param_schema(self._selected_type)

        existing_params = {}
        if self._is_edit and self._edit_index is not None:
            existing_params = self._main_screen.config.monitors[self._edit_index].params

        widgets: list = []
        for field in schema:
            widgets.append(Label(f"{field.label}:"))

            inp = Input(
                value=str(existing_params.get(field.key, field.default)),
                id=f"input-{field.key}",
            )
            self._fields[field.key] = inp
            widgets.append(inp)

            widgets.append(Label(f"[dim]{field.help}[/dim]"))

        return widgets

    def _update_help(self) -> None:
        """Update the help text for the selected monitor type."""
        help_label = self.query_one("#type-help", Label)
        help_text = get_type_help(self._selected_type)
        if help_text:
            help_label.update(f"[dim]{help_text}[/dim]")
            help_label.visible = True
        else:
            help_label.visible = False

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle type selection change."""
        value = event.value
        if isinstance(value, tuple):
            value = value[0]
        if value == self._selected_type:
            return
        self._selected_type = value
        self._update_help()
        widgets = self._build_param_fields()
        for child in list(self._param_container.children):
            child.remove()
        for w in widgets:
            self._param_container.mount(w)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
            return
        if event.button.id != "btn-save":
            return

        name = self.query_one("#name-input", Input).value
        monitor_type = self._get_selected_type()
        interval_str = self.query_one("#interval-input", Input).value

        if not self._validate_form(name, interval_str):
            return

        params = self._collect_params()

        if self._is_edit and self._edit_index is not None:
            self._update_monitor(name, monitor_type, interval_str, params)
            self._main_screen._refresh_table()
            self.dismiss(None)
        elif self._add_monitor(name, monitor_type, interval_str, params):
            self._main_screen._refresh_table()
            self.dismiss(None)

    def _get_selected_type(self) -> str:
        """Extract monitor type from Select widget."""
        value = self.query_one("#type-select", Select).value
        return value[0] if isinstance(value, tuple) else value

    def _validate_form(self, name: str, interval_str: str) -> bool:
        """Validate form inputs. Returns True if valid."""
        if not name:
            self.notify("Monitor name is required")
            return False
        try:
            interval = int(interval_str)
            if interval < 1:
                raise ValueError()
        except ValueError:
            self.notify("Interval must be a positive number")
            return False
        return True

    def _collect_params(self) -> dict[str, Any]:
        """Collect and convert parameter values from input fields."""
        params: dict[str, Any] = {}
        for key, inp in self._fields.items():
            val = inp.value.strip()
            if not val:
                continue
            field = next((f for f in get_param_schema(self._selected_type) if f.key == key), None)
            if field and field.kind == "number":
                try:
                    params[key] = float(val) if "." in val else int(val)
                except ValueError:
                    params[key] = val
            else:
                params[key] = val
        return params

    def _update_monitor(self, name: str, monitor_type: str, interval_str: str, params: dict[str, Any]) -> None:
        """Update an existing monitor."""
        monitor = self._main_screen.config.monitors[self._edit_index]
        monitor.name = name
        monitor.monitor_type = monitor_type
        monitor.interval_seconds = int(interval_str)
        monitor.params = params
        self.notify(f"✓ Updated monitor '{name}'")

    def _add_monitor(self, name: str, monitor_type: str, interval_str: str, params: dict[str, Any]) -> bool:
        """Add a new monitor after checking for duplicates. Returns True on success."""
        for m in self._main_screen.config.monitors:
            if m.name == name:
                self.notify(f"Monitor '{name}' already exists")
                return False
        self._main_screen.config.monitors.append(MonitorConfig(
            name=name,
            monitor_type=monitor_type,
            interval_seconds=int(interval_str),
            params=params,
        ))
        self.notify(f"✓ Added monitor '{name}'")
        return True

    def action_back(self) -> None:
        self.dismiss(None)
