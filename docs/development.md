# Development

## Development Setup

For developers who want to modify or contribute to the code:

```bash
# 1. Clone the repository
git clone https://github.com/rammelhof/uptime-kuma-satellite.git
cd uptime-kuma-satellite

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install in editable mode with dev dependencies
pip install -e ".[dev]"

# 4. Run tests
pytest
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/uptime_kuma_satellite
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

## Project Structure

```
uptime-kuma-satellite/
├── src/
│   └── uptime_kuma_satellite/
│       ├── cli.py                 # CLI entry point (Typer)
│       ├── config.py              # Config file handling
│       ├── models.py              # Data models
│       ├── service_manager.py     # Cross-platform service management
│       ├── windows_service.py     # Windows service implementation
│       └── monitors/
│           ├── __init__.py        # Monitor registry
│           ├── base.py            # BaseMonitor class
│           ├── file_exists.py     # File existence check
│           ├── file_age.py        # File age check
│           ├── disk_space.py      # Disk space check
│           ├── service.py         # TCP port check
│           ├── process.py         # Process check
│           ├── process_count.py   # Process count check
│           ├── uptime.py          # Uptime check
│           ├── cpu_usage.py       # CPU usage check
│           ├── memory_usage.py    # Memory usage check
│           ├── load_average.py    # Load average check
│           ├── ping.py            # Ping check
│           └── log_file.py        # Log file monitor
├── tests/                         # Test suite
├── docs/                          # Documentation
├── pyproject.toml                 # Project configuration
└── README.md                      # Main README
```

## Building a Wheel Package

```bash
pip install build
python -m build
```

The wheel will be generated in the `dist/` directory.
