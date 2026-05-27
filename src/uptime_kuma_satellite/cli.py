"""CLI entry point using Typer."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import typer

from .config import ConfigManager, DEFAULT_CONFIG_FILE
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
    interval: int = typer.Option(60, "--interval", "-i", help="Check interval in seconds"),
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
        interval_seconds=interval,
        params=parsed_params,
    ))
    mgr.save(svc_config)
    typer.echo(f"✓ Added monitor '{name}' (type: {monitor_type}, interval: {interval}s)")


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
    typer.echo(f"\n{'Name':<25} {'Type':<18} {'Enabled':<10} {'Interval':<10}")
    typer.echo("-" * 65)

    for m in svc_config.monitors:
        typer.echo(f"{m.name:<25} {m.monitor_type:<18} {str(m.enabled):<10} {m.interval_seconds:<10}")

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

    results: list = []
    with UptimeKumaClient(svc_config.push_url) as client:
        for monitor in svc_config.monitors:
            if not monitor.enabled:
                typer.echo(f"⊘ {monitor.name}: disabled")
                continue
            try:
                instance = MonitorRegistry.create(monitor)
                result = instance.check()
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

    scheduler = Scheduler(svc_config.push_url)
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


if __name__ == "__main__":
    app()
