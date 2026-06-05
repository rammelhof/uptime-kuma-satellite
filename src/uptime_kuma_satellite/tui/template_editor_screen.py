"""Template editor screen for editing global and per-monitor-type templates."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Label

from ..template import (
    DEFAULT_GLOBAL_TEMPLATE,
    DEFAULT_MONITOR_TEMPLATES,
    TEMPLATE_VAR_HELP,
    TemplateManager,
)


class TemplateEditorScreen(Screen):
    """Screen for editing global and per-monitor-type message templates."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("ctrl+t", "toggle_tab", "Toggle Tab", priority=True),
        Binding("ctrl+e", "edit_selected", "Edit Selected", priority=True),
    ]

    def __init__(self, main_screen: Any, template_mgr: TemplateManager) -> None:
        super().__init__()
        self._main_screen = main_screen
        self._template_mgr = template_mgr
        self._active_tab: str = "global"  # "global" or "monitor"

    def compose(self) -> ComposeResult:
        with Container(id="template-editor"):
            # Tabs as buttons
            with Container(id="template-tabs"):
                yield Button("Global Template", id="btn-tab-global", variant="primary")
                yield Button("Monitor Templates", id="btn-tab-monitor", variant="default")

            # Global template section
            with Vertical(id="global-section"):
                yield Label("[bold]Global Template[/] (applied to aggregated push messages)")
                yield Input(id="global-template-input")
                yield Label(
                    "[dim]Variables: {hostname} {up} {down} {total} {messages}[/dim]",
                    id="global-vars-help",
                )
                yield Label(
                    "[dim]Default: \"\"\"[/dim]",
                    id="global-default-hint",
                )
                yield Label(
                    f"[dim]{DEFAULT_GLOBAL_TEMPLATE}[/dim]",
                    id="global-default-value",
                )

            # Monitor template section
            with Vertical(id="monitor-section"):
                yield Label("[bold]Per-Monitor-Type Templates[/]")
                yield Label(
                    "[dim]Shared by all monitors of the same type.[/dim]",
                    id="monitor-type-help",
                )

                # Table of monitor types
                yield DataTable(id="monitor-types-table")

                # Selected type info
                yield Label(id="selected-type-info")
                yield Label(id="selected-type-vars")

                # UP template editor
                yield Label("[bold]UP Template:[/]", id="label-up-template")
                yield Input(id="up-template-input")
                yield Label(
                    "[dim]Common variables: {name} {status} {message} {type}[/dim]\n"
                    "[dim]Type-specific variables are listed below[/dim]",
                    id="up-vars-help",
                )

                # DOWN template editor
                yield Label("[bold]DOWN Template:[/]", id="label-down-template")
                yield Input(id="down-template-input")
                yield Label(
                    "[dim]Common variables: {name} {status} {message} {type}[/dim]\n"
                    "[dim]Type-specific variables are listed below[/dim]",
                    id="down-vars-help",
                )

                # Default template preview
                yield Label("[dim]Default for reference:[/]", id="label-default")
                yield Label(id="default-preview")

            # Buttons
            with Container(id="template-buttons"):
                yield Button("Save", id="btn-save-template")
                yield Button("Reset", id="btn-reset-template", variant="default")
                yield Button("Cancel", id="btn-cancel-template", variant="default")

            # Hint bar at bottom
            yield Label(
                "[dim]Ctrl+T: Toggle | Ctrl+E: Edit | Esc: Close[/dim]",
                id="template-hint",
            )

    def on_mount(self) -> None:
        self._setup_global_tab()
        self._setup_monitor_tab()
        # Hide monitor section initially
        self.query_one("#monitor-section", Vertical).display = False

    def _setup_global_tab(self) -> None:
        """Setup the global template tab."""
        template_input = self.query_one("#global-template-input", Input)
        template_input.value = self._template_mgr.global_template
        self._update_default_hint()

    def _setup_monitor_tab(self) -> None:
        """Setup the monitor template tab with a table of all monitor types."""
        table = self.query_one("#monitor-types-table", DataTable)
        
        # Only clear columns once to avoid duplicate columns on toggle
        if table.columns:
            table.clear()
        else:
            table.add_columns("Monitor Type", "Custom?", "Preview")
            table.zebra_stripes = True

        # Populate with all registered monitor types
        types_with_custom = self._template_mgr.get_available_monitor_types()
        for monitor_type, has_custom in types_with_custom:
            preview = self._get_template_preview(monitor_type)
            table.add_row(monitor_type, "✓" if has_custom else " ", preview)

    def _get_template_preview(self, monitor_type: str) -> str:
        """Get a short preview of the template for a monitor type."""
        templates = self._template_mgr.effective_templates
        type_templates = templates.get(monitor_type, {})
        up_template = type_templates.get("up", "")
        # Truncate for preview
        if len(up_template) > 40:
            return up_template[:40] + "..."
        return up_template

    def _update_default_hint(self) -> None:
        """Update the default template hint."""
        template_input = self.query_one("#global-template-input", Input)
        hint = self.query_one("#global-default-hint", Label)
        default_value = self.query_one("#global-default-value", Label)
        
        if template_input.value == DEFAULT_GLOBAL_TEMPLATE:
            hint.update("[dim]✓ Using default template[/dim]")
            default_value.display = False
        elif template_input.value == "":
            hint.update("[dim]Empty - will use default[/dim]")
            default_value.display = True
        else:
            hint.update("[dim]Custom template[/dim]")
            default_value.display = True

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in monitor types table."""
        row_index = event.cursor_row
        if row_index is None:
            return
        row = event.data_table.get_row_at(row_index)
        if not row:
            return
        
        monitor_type = row[0]
        self._load_monitor_template(monitor_type)

    def _load_monitor_template(self, monitor_type: str) -> None:
        """Load the template for a specific monitor type."""
        # Update selected type info
        info_label = self.query_one("#selected-type-info", Label)
        info_label.update(f"[bold]Type:[/bold] {monitor_type}")
        
        # Update variables help with line breaks
        vars_label = self.query_one("#selected-type-vars", Label)
        help_text = TEMPLATE_VAR_HELP.get(monitor_type, [])
        if help_text:
            vars_label.update(f"[dim]Available variables: {help_text[0]}[/dim]")
        else:
            vars_label.update("[dim]No type-specific variables[/dim]")
        
        # Load templates
        up_input = self.query_one("#up-template-input", Input)
        down_input = self.query_one("#down-template-input", Input)
        
        templates = self._template_mgr.effective_templates
        type_templates = templates.get(monitor_type, {})
        up_input.value = type_templates.get("up", "")
        down_input.value = type_templates.get("down", "")
        
        # Show default preview
        default_preview = self.query_one("#default-preview", Label)
        default_templates = DEFAULT_MONITOR_TEMPLATES.get(monitor_type, {})
        default_up = default_templates.get("up", "")
        default_down = default_templates.get("down", "")
        if len(default_up) > 60:
            default_up = default_up[:60] + "..."
        if len(default_down) > 60:
            default_down = default_down[:60] + "..."
        default_preview.update(
            f"[dim]Default UP: {default_up}[/dim]\n"
            f"[dim]Default DOWN: {default_down}[/dim]"
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        input_id = event.input.id
        if input_id == "global-template-input":
            self._update_default_hint()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        # Tab buttons
        if event.button.id == "btn-tab-global":
            if self._active_tab != "global":
                self.action_tab_global()
            return
        if event.button.id == "btn-tab-monitor":
            if self._active_tab != "monitor":
                self.action_tab_monitor()
            return
        # Action buttons
        if event.button.id == "btn-cancel-template":
            self.dismiss(None)
            return
        
        if event.button.id == "btn-reset-template":
            if self._active_tab == "global":
                self.query_one("#global-template-input", Input).value = DEFAULT_GLOBAL_TEMPLATE
                self._update_default_hint()
            else:
                # Reset to default for selected type
                table = self.query_one("#monitor-types-table", DataTable)
                row_index = table.cursor_row
                if row_index is not None:
                    row = table.get_row_at(row_index)
                    if row:
                        monitor_type = row[0]
                        defaults = DEFAULT_MONITOR_TEMPLATES.get(monitor_type, {})
                        self.query_one("#up-template-input", Input).value = defaults.get("up", "")
                        self.query_one("#down-template-input", Input).value = defaults.get("down", "")
                        self._load_monitor_template(monitor_type)
            return
        
        if event.button.id == "btn-save-template":
            self._save_templates()
            self.dismiss(True)
            return

    def action_toggle_tab(self) -> None:
        """Toggle between global and monitor tabs."""
        if self._active_tab == "global":
            self.action_tab_monitor()
        else:
            self.action_tab_global()

    def action_tab_global(self) -> None:
        self._active_tab = "global"
        self.query_one("#global-section", Vertical).display = True
        self.query_one("#monitor-section", Vertical).display = False
        self.query_one("#btn-tab-global", Button).variant = "primary"
        self.query_one("#btn-tab-monitor", Button).variant = "default"
        self._setup_global_tab()

    def action_tab_monitor(self) -> None:
        self._active_tab = "monitor"
        self.query_one("#global-section", Vertical).display = False
        self.query_one("#monitor-section", Vertical).display = True
        self.query_one("#btn-tab-global", Button).variant = "default"
        self.query_one("#btn-tab-monitor", Button).variant = "primary"
        self._setup_monitor_tab()
        self.refresh()

    def action_edit_selected(self) -> None:
        """Edit the currently selected monitor (Ctrl+E)."""
        if self._active_tab != "monitor":
            self.action_tab_monitor()
            # After switching, fall through to load the selected type
        
        table = self.query_one("#monitor-types-table", DataTable)
        row_index = table.cursor_row
        if row_index is None:
            self.notify("No monitor type selected", title="Error")
            return
        
        row = table.get_row_at(row_index)
        if not row:
            self.notify("No monitor type selected", title="Error")
            return
        
        monitor_type = row[0]
        
        # Load the template info into the UI
        self._load_monitor_template(monitor_type)
        
        # Focus the UP template input
        self.query_one("#up-template-input", Input).focus()
        self.notify(f"Editing template for '{monitor_type}'", title="Edit")

    def _save_templates(self) -> None:
        """Save the edited templates."""
        if self._active_tab == "global":
            global_value = self.query_one("#global-template-input", Input).value
            self._main_screen.config.global_template = global_value if global_value else ""
            self._main_screen._template_mgr = TemplateManager(
                global_template=self._main_screen.config.global_template,
                monitor_templates=self._main_screen.config.monitor_templates,
            )
            self._main_screen.notify("✓ Global template saved")
        
        else:  # monitor tab
            # Get selected monitor type from table
            table = self.query_one("#monitor-types-table", DataTable)
            row_index = table.cursor_row
            if row_index is None:
                self._main_screen.notify("No monitor type selected", title="Error")
                return
            
            row = table.get_row_at(row_index)
            if not row:
                self._main_screen.notify("No monitor type selected", title="Error")
                return
            
            monitor_type = row[0]
            
            up_template = self.query_one("#up-template-input", Input).value
            down_template = self.query_one("#down-template-input", Input).value
            
            # Build custom template dict
            custom_template: dict[str, str] = {}
            if up_template:
                custom_template["up"] = up_template
            if down_template:
                custom_template["down"] = down_template
            
            # Save to config
            if self._main_screen.config:
                # Store at the service level (per-type)
                if custom_template:
                    self._main_screen.config.monitor_templates[monitor_type] = custom_template
                elif monitor_type in self._main_screen.config.monitor_templates:
                    # Remove if empty
                    del self._main_screen.config.monitor_templates[monitor_type]
                
                # Update template manager
                self._main_screen._template_mgr = TemplateManager(
                    global_template=self._main_screen.config.global_template,
                    monitor_templates=self._main_screen.config.monitor_templates,
                )
                
                self._main_screen.notify(f"✓ Template for '{monitor_type}' saved")
                self._main_screen._refresh_table()

    def action_back(self) -> None:
        self.dismiss(False)
