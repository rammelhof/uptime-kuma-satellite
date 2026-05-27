# CLI Reference

## Global Options

All commands accept:

| Flag | Description |
|------|-------------|
| `-c`, `--config <path>` | Specify a custom config file path |

## Commands

| Command | Description |
|---------|-------------|
| `uks setup -u <url>` | Initialize/update Push API URL |
| `uks add-monitor -n <name> -t <type> [-i <interval>] [-p <json>] [-c <path>]` | Add a new monitor |
| `uks remove-monitor -n <name> [-c <path>]` | Remove a monitor |
| `uks list-monitors [-c <path>]` | List all monitors |
| `uks run-once [-s] [-c <path>]` | Run all monitors once, send aggregated report |
| `uks run [-c <path>]` | Run continuously in background |
| `uks tui` | Launch the interactive terminal UI |
| `uks list-types` | List available monitor types |
| `uks info <type>` | Show details about a monitor type |
| `uks service install [-c <path>]` | Install as a system service (auto-starts on boot) |
| `uks service uninstall` | Uninstall the system service |
| `uks service status` | Check service status |

## Run-once Options

| Flag | Description |
|------|-------------|
| `-s`, `--skip-invalid` | Skip monitors with invalid configuration |

## Add-Monitor Options

| Flag | Description |
|------|-------------|
| `-n`, `--name <name>` | Monitor name (required) |
| `-t`, `--type <type>` | Monitor type (required) |
| `-i`, `--interval <seconds>` | Check interval in seconds |
| `-p`, `--params <json>` | JSON string of monitor-specific parameters |

## Examples

```bash
# Set up the Push API URL
uks setup -u "http://192.168.1.100:3001/api/push/abc123xyz"

# Add a disk space monitor with 5-minute interval
uks add-monitor -n "root-disk" -t disk_space -i 300 \
  --params '{"path": "/", "min_percent": 10}'

# Add a process monitor (no custom params needed)
uks add-monitor -n "nginx" -t process -i 60 \
  --params '{"name": "nginx"}'

# Run all monitors once and send results
uks run-once

# Run with a custom config file
uks run-once -c /path/to/config.yaml

# Check service status
uks service status
```
