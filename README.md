# Uptime Kuma Satellite

A cross-platform monitoring service that reports to [Uptime Kuma](https://github.com/louislam/uptime-kuma) via the Push API.

[![PyPI license](https://img.shields.io/pypi/l/ansicolortags.svg)](https://pypi.python.org/pypi/ansicolortags/)
[![Made by AI](https://img.shields.io/badge/Made%20by-AI-lightgrey?style=for-badge)](https://github.com/mefengl/made-by-ai)

## Features

- **CLI & TUI**: Configure and manage monitors via command line or interactive terminal UI
- **Customizable Templates**: Customize message formats for push notifications via CLI or TUI
- **Extensible Monitor Plugins**: Easy to add new monitor types
- **Cross-Platform**: Works on Linux, macOS, and Windows
- **System Service**: Install as a background service on all platforms (systemd, launchd, Windows)
- **Push API Compatible**: Reports directly to Uptime Kuma's Push monitoring endpoint

## Quick Links

| Topic | Documentation |
|-------|---------------|
| **Installation** | [docs/installation.md](docs/installation.md) |
| **Quick Start / Usage** | [docs/usage.md](docs/usage.md) |
| **Monitor Types** | [docs/monitors.md](docs/monitors.md) |
| **Service Management** | [docs/service.md](docs/service.md) |
| **Configuration** | [docs/configuration.md](docs/configuration.md) |
| **CLI Reference** | [docs/cli-reference.md](docs/cli-reference.md) |
| **Message Templates** | [docs/templates.md](docs/templates.md) |
| **Development** | [docs/development.md](docs/development.md) |
| **Windows Setup** | [docs/windows.md](docs/windows.md) |

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│   CLI/TUI   │────▶│  Scheduler   │────▶│  Monitor Plugins │
│  (Typer)    │     │  (asyncio)   │     │  (extensible)    │
└─────────────┘     └──────────────┘     └──────────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   HTTP Client│────▶ Uptime Kuma
                    │  (httpx)     │     Push API
                    └──────────────┘
```

## Adding Custom Monitors

Create a new monitor by subclassing `BaseMonitor` and registering it with `MonitorRegistry`:

```python
from uptime_kuma_satellite.monitors import BaseMonitor, MonitorRegistry
from uptime_kuma_satellite.models import MonitorConfig, MonitorResult, MonitorStatus

@MonitorRegistry.register
class MyCustomMonitor(BaseMonitor):
    type_name = "my_custom"

    def validate_config(self) -> list[str]:
        """Validate monitor-specific configuration. Return list of error messages."""
        errors = []
        if "my_param" not in self.config.params:
            errors.append("Missing 'my_param' parameter")
        return errors

    def check(self) -> MonitorResult:
        # Your monitoring logic here
        my_param = self.config.params.get("my_param", "default")

        # Store data for template rendering (optional)
        self._last_data = {
            "my_value": 42,
            "my_param": my_param,
        }

        return MonitorResult(
            monitor_name=self.config.name,
            monitor_type=self.type_name,
            status=MonitorStatus.UP,
            message="Everything is fine",
            ping_ms=12.5,  # optional: check duration in milliseconds
        )
```

### Key Points

- **`type_name`**: Unique string identifier used in config to reference this monitor type.
- **`check()`**: Called on each monitoring interval. Must return a `MonitorResult`.
- **`validate_config()`**: Called when the monitor is created. Return a list of error strings (empty list = valid).
- **`_last_data`**: Dict stored during `check()` and exposed via `get_template_vars()` for message template rendering.
- **`MonitorResult.data`**: Extra data dict attached to the result (separate from template vars).
- **`ping_ms`**: Optional timing field for the check duration.

### Built-in Monitor Types

| Type | Description |
|------|-------------|
| `file_exists` | Check if a file exists |
| `file_age` | Check if a file is older than a threshold |
| `disk_space` | Check free disk space percentage |
| `service` | Check TCP port connectivity |
| `process` | Check if a process is running |
| `process_count` | Check that N processes match a pattern |
| `uptime` | Alert on unexpected reboots |
| `cpu_usage` | Check CPU usage percentage |
| `memory_usage` | Check memory usage percentage |
| `load_average` | Check system load average |
| `ping` | Check network reachability via ICMP |
| `log_file` | Monitor log file for error patterns |

See [docs/monitors.md](docs/monitors.md) for full details on each built-in monitor type.

## License

MIT
