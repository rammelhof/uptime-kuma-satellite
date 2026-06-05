"""CLI entry point using Typer."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import typer

from .config import ConfigManager, get_system_config_file
from .models import MonitorConfig, ServiceConfig
from .monitors import MonitorRegistry
from .scheduler import Scheduler

app = typer.Typer(
    name="uks",
    help="Uptime Kuma Satellite - monitor your infrastructure and report to Uptime Kuma",
    add_completion=False,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("uks")


def _get_log_path(platform: str, config_path: Path) -> str:
    """Get the log file path for the given platform."""
    if platform == "windows":
        from .config import get_system_config_dir
        return str(get_system_config_dir() / "satellite.log")
    return "/var/log/uptime-kuma-satellite/satellite.log"


def _get_config(config_path: Path | None = None) -> tuple[ConfigManager, ServiceConfig]:
    """Load or create a default config."""
    mgr = ConfigManager(config_path)
    config = mgr.load()
    if not config.push_url:
        typer.echo("No configuration found. Run 'uks setup' first.")
        raise typer.Exit(1)
    return mgr, config


@app.command()
def setup(
    push_url: str = typer.Option(..., "--push-url", "-u", help="Uptime Kuma Push API URL"),
    config: Path = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Initialize or update the configuration."""
    mgr = ConfigManager(config)
    config = mgr.load()
    config.push_url = push_url
    mgr.save(config)
    typer.echo(f"✓ Configuration saved to {mgr.config_path}")


@app.command()
def add_monitor(
    name: str = typer.Option(..., "--name", "-n", help="Monitor name"),
    monitor_type: str = typer.Option(..., "--type", "-t", help="Monitor type"),
    params: str = typer.Option("{}", "--params", "-p", help="Monitor parameters as JSON string"),
    config: Path = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Add a new monitor to the configuration."""


    mgr, svc_config = _get_config(config)

    available = MonitorRegistry.list_types()
    if monitor_type not in available:
        typer.echo(f"Unknown monitor type: {monitor_type}")
        typer.echo(f"Available types: {', '.join(available)}")
        raise typer.Exit(1)

    # Parse JSON params
    try:
        parsed_params = json.loads(params)
    except json.JSONDecodeError as e:
        typer.echo(f"Invalid JSON for params: {e}")
        raise typer.Exit(1)

    # Check if monitor with same name already exists
    for m in svc_config.monitors:
        if m.name == name:
            typer.echo(f"Monitor '{name}' already exists. Use 'update-monitor' to modify it.")
            raise typer.Exit(1)

    svc_config.monitors.append(MonitorConfig(
        name=name,
        monitor_type=monitor_type,
        enabled=True,
        params=parsed_params,
    ))
    mgr.save(svc_config)
    typer.echo(f"✓ Added monitor '{name}' (type: {monitor_type})")


@app.command()
def remove_monitor(
    name: str = typer.Option(..., "--name", "-n", help="Monitor name to remove"),
    config: Path = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Remove a monitor from the configuration."""
    mgr, svc_config = _get_config(config)

    before = len(svc_config.monitors)
    svc_config.monitors = [m for m in svc_config.monitors if m.name != name]
    if len(svc_config.monitors) == before:
        typer.echo(f"Monitor '{name}' not found.")
        raise typer.Exit(1)
    mgr.save(svc_config)
    typer.echo(f"✓ Removed monitor '{name}'")


@app.command()
def list_monitors(
    config: Path = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """List all configured monitors."""
    _, svc_config = _get_config(config)

    typer.echo(f"\nPush URL: {svc_config.push_url}")
    typer.echo(f"Hostname: {svc_config.hostname}")
    typer.echo(f"Default interval: {svc_config.default_interval}s")
    typer.echo(f"\n{'Name':<25} {'Type':<18} {'Enabled':<10}")
    typer.echo("-" * 55)

    for m in svc_config.monitors:
        typer.echo(f"{m.name:<25} {m.monitor_type:<18} {str(m.enabled):<10}")

    typer.echo(f"\nTotal: {len(svc_config.monitors)} monitor(s)")


@app.command()
def run_once(
    config: Path = typer.Option(None, "--config", "-c", help="Config file path"),
    skip_invalid: bool = typer.Option(False, "--skip-invalid", "-s", help="Skip monitors with invalid config"),
) -> None:
    """Run all monitors once and send a single aggregated push request."""
    mgr, svc_config = _get_config(config)

    from .client import UptimeKumaClient
    from .monitors import MonitorRegistry
    from .template import TemplateManager

    results: list = []
    template_mgr = TemplateManager(
        global_template=svc_config.global_template,
        monitor_templates=svc_config.monitor_templates,
    )
    with UptimeKumaClient(
        svc_config.push_url,
        hostname=svc_config.hostname,
        template_mgr=template_mgr,
    ) as client:
        for monitor in svc_config.monitors:
            if not monitor.enabled:
                typer.echo(f"⊘ {monitor.name}: disabled")
                continue
            try:
                instance = MonitorRegistry.create(monitor)
                result = instance.check()
                result.data = instance.get_template_vars()
                results.append(result)
                status_icon = "✓" if result.status.value == "up" else "✗"
                typer.echo(f"{status_icon} [{result.status.value.upper():>4}] {result.monitor_name}: {result.message}")
            except ValueError as e:
                if skip_invalid:
                    typer.echo(f"⊘ {monitor.name}: skipped ({e})")
                else:
                    raise

        # Send a single aggregated report
        if results:
            client.report_aggregated(results)


@app.command()
def run(
    config: Path = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Run the satellite service in the background."""
    mgr, svc_config = _get_config(config)

    typer.echo(f"Starting Uptime Kuma Satellite...")
    typer.echo(f"Push URL: {svc_config.push_url}")
    typer.echo(f"Monitors: {len(svc_config.monitors)}")
    typer.echo("Press Ctrl+C to stop.")

    scheduler = Scheduler(
        svc_config.push_url,
        config_path=config,
        default_interval=svc_config.default_interval,
        hostname=svc_config.hostname,
        global_template=svc_config.global_template,
        monitor_templates=svc_config.monitor_templates,
    )
    scheduler.start(svc_config.monitors)

    try:
        while True:

            time.sleep(1)
    except KeyboardInterrupt:
        typer.echo("\nStopping...")
        scheduler.stop()


@app.command()
def list_types() -> None:
    """List all available monitor types."""
    available = MonitorRegistry.list_types()
    typer.echo("Available monitor types:")
    for t in available:
        typer.echo(f"  - {t}")


@app.command()
def info(
    monitor_type: str = typer.Argument(..., help="Monitor type to show info for"),
) -> None:
    """Show configuration info for a monitor type."""
    from .monitors import MonitorRegistry
    monitor_class = MonitorRegistry.get(monitor_type)
    if not monitor_class:
        typer.echo(f"Unknown monitor type: {monitor_type}")
        raise typer.Exit(1)

    typer.echo(f"Monitor type: {monitor_type}")
    typer.echo(f"Class: {monitor_class.__name__}")
    typer.echo(f"Module: {monitor_class.__module__}")


@app.command()
def tui(
    config: Path = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Launch the interactive TUI for managing monitors."""
    from .tui import SatApp
    app_instance = SatApp(config_path=config)
    app_instance.run()


# ── Template Management ───────────────────────────────────────────────

template_app = typer.Typer(
    name="template",
    help="Manage message templates for push notifications",
    add_completion=False,
)
app.add_typer(template_app, name="template")


@template_app.command("show")
def template_show(
    config: Path = typer.Option(None, "--config", "-c", help="Config file path"),
    global_only: bool = typer.Option(False, "--global", "-g", help="Show only the global template"),
    monitor_type: str = typer.Option(None, "--monitor", "-m", help="Show template for a specific monitor type"),
    show_default: bool = typer.Option(False, "--default", "-d", help="Show default template for comparison"),
) -> None:
    """Show current template configuration."""
    from .template import (
        DEFAULT_GLOBAL_TEMPLATE,
        DEFAULT_MONITOR_TEMPLATES,
        TemplateManager,
    )

    mgr, svc_config = _get_config(config)
    template_mgr = TemplateManager(
        global_template=svc_config.global_template,
        monitor_templates=svc_config.monitor_templates,
    )

    if global_only:
        if template_mgr.global_template:
            typer.echo("Global template (custom):")
            typer.echo(f"  {template_mgr.global_template}")
        else:
            typer.echo("No global template set (using default)")
        if show_default:
            typer.echo(f"\nDefault global template:")
            typer.echo(f"  {DEFAULT_GLOBAL_TEMPLATE}")
        return

    if monitor_type:
        # Show template for a specific monitor type
        available = MonitorRegistry.list_types()
        if monitor_type not in available:
            typer.echo(f"Unknown monitor type: {monitor_type}")
            typer.echo(f"Available types: {', '.join(available)}")
            raise typer.Exit(1)

        effective = template_mgr.effective_templates
        type_templates = effective.get(monitor_type, {})
        has_custom = monitor_type in svc_config.monitor_templates

        typer.echo(f"Template for '{monitor_type}':")
        if has_custom:
            typer.echo("  (custom)")
            up_t = type_templates.get("up", "")
            down_t = type_templates.get("down", "")
            if up_t:
                typer.echo(f"  UP:   {up_t}")
            if down_t:
                typer.echo(f"  DOWN: {down_t}")
        else:
            typer.echo("  (using default)")

        if show_default:
            defaults = DEFAULT_MONITOR_TEMPLATES.get(monitor_type, {})
            typer.echo(f"\nDefault template for '{monitor_type}':")
            default_up = defaults.get("up", "")
            default_down = defaults.get("down", "")
            if default_up:
                typer.echo(f"  UP:   {default_up}")
            if default_down:
                typer.echo(f"  DOWN: {default_down}")
        return

    # Show all templates
    typer.echo("=== Global Template ===")
    if template_mgr.global_template:
        typer.echo(f"  {template_mgr.global_template}")
    else:
        typer.echo("  (not set - using default)")
    if show_default:
        typer.echo(f"\nDefault global:")
        typer.echo(f"  {DEFAULT_GLOBAL_TEMPLATE}")

    typer.echo("\n=== Per-Monitor-Type Templates ===")
    types_with_custom = template_mgr.get_available_monitor_types()
    for mtype, has_custom in types_with_custom:
        effective = template_mgr.effective_templates
        type_templates = effective.get(mtype, {})
        up_t = type_templates.get("up", "")
        down_t = type_templates.get("down", "")
        prefix = "[CUSTOM] " if has_custom else "[default]"
        if up_t:
            typer.echo(f"  {prefix}{mtype} UP:   {up_t}")
        if down_t:
            typer.echo(f"  {prefix}{mtype} DOWN: {down_t}")


@template_app.command("set")
def template_set(
    config: Path = typer.Option(None, "--config", "-c", help="Config file path"),
    global_template: str = typer.Option(None, "--global", "-g", help="Set global template string"),
    monitor_type: str = typer.Option(None, "--monitor", "-m", help="Monitor type to set template for"),
    up_template: str = typer.Option(None, "--up", help="Set UP status template for monitor type"),
    down_template: str = typer.Option(None, "--down", help="Set DOWN status template for monitor type"),
) -> None:
    """Set a template (global or per-monitor-type)."""
    mgr, svc_config = _get_config(config)

    if global_template is not None:
        svc_config.global_template = global_template
        typer.echo(f"✓ Global template set")

    if monitor_type:
        available = MonitorRegistry.list_types()
        if monitor_type not in available:
            typer.echo(f"Unknown monitor type: {monitor_type}")
            typer.echo(f"Available types: {', '.join(available)}")
            raise typer.Exit(1)

        if up_template is None and down_template is None:
            typer.echo("Specify at least --up or --down for monitor type templates")
            raise typer.Exit(1)

        # Initialize monitor_templates if needed
        if svc_config.monitor_templates is None:
            svc_config.monitor_templates = {}

        if monitor_type not in svc_config.monitor_templates:
            svc_config.monitor_templates[monitor_type] = {}

        if up_template is not None:
            svc_config.monitor_templates[monitor_type]["up"] = up_template
            typer.echo(f"✓ Template for '{monitor_type}' UP set")
        if down_template is not None:
            svc_config.monitor_templates[monitor_type]["down"] = down_template
            typer.echo(f"✓ Template for '{monitor_type}' DOWN set")

    mgr.save(svc_config)


@template_app.command("reset")
def template_reset(
    config: Path = typer.Option(None, "--config", "-c", help="Config file path"),
    global_only: bool = typer.Option(False, "--global", "-g", help="Reset global template to default"),
    monitor_type: str = typer.Option(None, "--monitor", "-m", help="Reset template for a specific monitor type"),
) -> None:
    """Reset template(s) to defaults."""
    mgr, svc_config = _get_config(config)

    if global_only:
        svc_config.global_template = ""
        typer.echo("✓ Global template reset to default")

    if monitor_type:
        available = MonitorRegistry.list_types()
        if monitor_type not in available:
            typer.echo(f"Unknown monitor type: {monitor_type}")
            typer.echo(f"Available types: {', '.join(available)}")
            raise typer.Exit(1)

        if svc_config.monitor_templates and monitor_type in svc_config.monitor_templates:
            del svc_config.monitor_templates[monitor_type]
            typer.echo(f"✓ Template for '{monitor_type}' reset to default")
        else:
            typer.echo(f"No custom template for '{monitor_type}' to reset")

    mgr.save(svc_config)


@template_app.command("vars")
def template_vars(
    config: Path = typer.Option(None, "--config", "-c", help="Config file path"),
    monitor_type: str = typer.Argument(..., help="Monitor type to show variables for"),
) -> None:
    """Show available template variables for a monitor type."""
    from .template import TEMPLATE_VAR_HELP

    mgr, svc_config = _get_config(config)

    available = MonitorRegistry.list_types()
    if monitor_type not in available:
        typer.echo(f"Unknown monitor type: {monitor_type}")
        typer.echo(f"Available types: {', '.join(available)}")
        raise typer.Exit(1)

    typer.echo(f"Template variables for '{monitor_type}':")
    typer.echo("")

    # Common variables
    typer.echo("  Common variables (all types):")
    typer.echo("    {name}      - Monitor name")
    typer.echo("    {status}    - UP or DOWN")
    typer.echo("    {type}      - Monitor type")
    typer.echo("    {message}   - Raw monitor message")

    # Type-specific variables
    help_text = TEMPLATE_VAR_HELP.get(monitor_type, [])
    if help_text:
        typer.echo("")
        typer.echo("  Type-specific variables:")
        # Extract just the variable names from the help text
        var_line = help_text[0]
        if ": " in var_line:
            var_line = var_line.split(": ", 1)[1]
        typer.echo(f"    {var_line}")


# ── Service Management ─────────────────────────────────────────────────

service_app = typer.Typer(
    name="service",
    help="Install, uninstall, and manage the satellite as a system service",
    add_completion=False,
)
app.add_typer(service_app, name="service")


@service_app.command()
def install(
    config: Path = typer.Option(None, "--config", "-c", help="Config file path (default: system-wide)"),
) -> None:
    """Install the satellite as a system service (auto-starts on boot)."""
    from .service_manager import get_service_manager

    mgr = get_service_manager(config)
    typer.echo(f"Platform: {mgr.platform}")
    typer.echo(f"Config: {mgr.config_path}")
    typer.echo("")
    typer.echo("Installing service...")
    mgr.install()
    typer.echo("")
    typer.echo("✓ Service installed. It will start automatically on boot.")
    log_path = _get_log_path(mgr.platform, mgr.config_path)
    typer.echo(f"  View logs: {log_path}")


@service_app.command()
def uninstall() -> None:
    """Uninstall the satellite system service (does not delete config)."""
    from .service_manager import get_service_manager

    mgr = get_service_manager()
    typer.echo(f"Platform: {mgr.platform}")
    typer.echo("")
    typer.echo("Uninstalling service...")
    mgr.uninstall()
    typer.echo("")
    typer.echo("✓ Service uninstalled. Your config file is preserved.")


@service_app.command()
def status(
    config: Path = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Check the current status of the satellite service."""
    from .service_manager import get_service_manager

    mgr = get_service_manager(config)
    typer.echo(f"Platform: {mgr.platform}")
    typer.echo(f"Service: uptime-kuma-satellite")
    typer.echo("")
    mgr.status()


if __name__ == "__main__":
    app()
