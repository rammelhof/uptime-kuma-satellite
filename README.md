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

Create a new monitor by subclassing `BaseMonitor`:

```python
from uptime_kuma_satellite.monitors import BaseMonitor, MonitorRegistry
from uptime_kuma_satellite.models import MonitorConfig, MonitorResult, MonitorStatus

@MonitorRegistry.register
class MyCustomMonitor(BaseMonitor):
    type_name = "my_custom"

    def check(self) -> MonitorResult:
        # Your monitoring logic here
        return MonitorResult(
            monitor_name=self.config.name,
            monitor_type=self.type_name,
            status=MonitorStatus.UP,
            message="Everything is fine",
        )
```

## License

MIT
