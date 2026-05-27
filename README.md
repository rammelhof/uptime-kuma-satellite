# Uptime Kuma Satellite

A cross-platform monitoring service that reports to [Uptime Kuma](https://github.com/louislam/uptime-kuma) via the Push API.

## Features

- **CLI & TUI**: Configure and manage monitors via command line or interactive terminal UI
- **Extensible Monitor Plugins**: Easy to add new monitor types
- **Cross-Platform**: Works on Linux, macOS, and Windows
- **Push API Compatible**: Reports directly to Uptime Kuma's Push monitoring endpoint

## Installation

```bash
cd uptime-kuma-satellite
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Quick Start

### 1. Configure

```bash
# Set up your Push API URL
uks setup -u "http://your-uptime-kuma/api/push/YOUR_API_KEY"
```

### 2. Add Monitors

```bash
# File existence check
uks add-monitor -n "app-logs" -t file_exists -i 60

# File age check (alert if file older than 1 hour)
uks add-monitor -n "backup-check" -t file_age -i 300 \
  --params '{"path": "/var/backups/latest.tar.gz", "max_age_seconds": 3600}'

# Disk space check (alert if less than 10% free)
uks add-monitor -n "root-disk" -t disk_space -i 300 \
  --params '{"path": "/", "min_percent": 10}'

# Service check (TCP port)
uks add-monitor -n "web-service" -t service -i 60 \
  --params '{"host": "localhost", "port": 8080}'

# Process check
uks add-monitor -n "nginx" -t process -i 60 \
  --params '{"name": "nginx"}'

# CPU usage check
uks add-monitor -n "cpu" -t cpu_usage -i 60 \
  --params '{"max_percent": 90}'

# Memory usage check
uks add-monitor -n "memory" -t memory_usage -i 60 \
  --params '{"max_percent": 90}'

# Load average check
uks add-monitor -n "load" -t load_average -i 60 \
  --params '{"max_load": 2.0}'

# Ping check
uks add-monitor -n "google-dns" -t ping -i 120 \
  --params '{"host": "8.8.8.8", "count": 2}'

# Log file monitor
uks add-monitor -n "app-errors" -t log_file -i 300 \
  --params '{"path": "/var/log/myapp/app.log", "lookback_minutes": 60}'
```

### 3. Run

```bash
# Run all monitors once
uks run-once

# Run continuously in background
uks run

# Or use the TUI
uks tui
```

### 4. Manage

```bash
# List monitors
uks list-monitors

# Remove a monitor
uks remove-monitor -n "old-monitor"

# List available monitor types
uks list-types
```

## Monitor Types

| Type | Description | Required Params |
|------|-------------|-----------------|
| `file_exists` | Check if a file exists | `path` |
| `file_age` | Check if a file is older than threshold | `path`, `max_age_seconds` |
| `disk_space` | Check disk free space | `path`, `min_percent` |
| `service` | Check TCP port connectivity | `host`, `port` |
| `process` | Check if a process is running | `name` |
| `cpu_usage` | Check CPU usage percentage | `max_percent` |
| `memory_usage` | Check memory usage percentage | `max_percent` |
| `load_average` | Check system load average | `max_load` |
| `ping` | Check network reachability | `host` |
| `log_file` | Monitor log file for errors | `path`, `lookback_minutes` |

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

## Config File

Configuration is stored in `~/.config/uptime-kuma-satellite/config.yaml`:

```yaml
push_url: http://your-uptime-kuma/api/push/YOUR_API_KEY
hostname: my-server
default_interval: 60
monitors:
  - name: root-disk
    type: disk_space
    enabled: true
    interval: 300
    params:
      path: /
      min_percent: 10
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/uptime_kuma_satellite
```

## License

MIT
