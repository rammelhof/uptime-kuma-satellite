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
| `uks add-monitor -n <name> -t <type> [-p <json>] [-c <path>]` | Add a new monitor |
| `uks remove-monitor -n <name> [-c <path>]` | Remove a monitor |
| `uks list-monitors [-c <path>]` | List all monitors |
| `uks run-once [-s] [-c <path>]` | Run all monitors once, send aggregated report |
| `uks run [-c <path>]` | Run continuously in background |
| `uks tui` | Launch the interactive terminal UI |
| `uks list-types` | List available monitor types |
| `uks info <type>` | Show details about a monitor type |
| `uks template show [-g] [-m <type>] [-d] [-c <path>]` | Show current template configuration |
| `uks template set [-g <tmpl>] [-m <type>] [--up <tmpl>] [--down <tmpl>] [-c <path>]` | Set a template |
| `uks template reset [-g] [-m <type>] [-c <path>]` | Reset template(s) to defaults |
| `uks template vars <type> [-c <path>]` | Show available template variables for a monitor type |
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
| `-p`, `--params <json>` | JSON string of monitor-specific parameters |

## Template Commands

### Template Show

| Flag | Description |
|------|-------------|
| `-g`, `--global` | Show only the global template |
| `-m`, `--monitor <type>` | Show template for a specific monitor type |
| `-d`, `--default` | Show default template for comparison |

### Template Set

| Flag | Description |
|------|-------------|
| `-g`, `--global <tmpl>` | Set global template string |
| `-m`, `--monitor <type>` | Monitor type to set template for |
| `--up <tmpl>` | Set UP status template for monitor type |
| `--down <tmpl>` | Set DOWN status template for monitor type |

### Template Reset

| Flag | Description |
|------|-------------|
| `-g`, `--global` | Reset global template to default |
| `-m`, `--monitor <type>` | Reset template for a specific monitor type |

### Template Vars

| Flag | Description |
|------|-------------|
| `-c`, `--config <path>` | Config file path (see global options) |

## Examples

```bash
# Set up the Push API URL
uks setup -u "http://192.168.1.100:3001/api/push/abc123xyz"

# Add a disk space monitor with 5-minute interval
uks add-monitor -n "root-disk" -t disk_space \
  --params '{"path": "/", "min_percent": 10}'

# Add a process monitor (no custom params needed)
uks add-monitor -n "nginx" -t process \
  --params '{"name": "nginx"}'

# Run all monitors once and send results
uks run-once

# Run with a custom config file
uks run-once -c /path/to/config.yaml

# ── Template Management ──────────────────────────────────────────

# Show all current templates
uks template show

# Show global template only
uks template show -g

# Show a specific monitor type's template with defaults
uks template show -m cpu_usage -d

# Set a custom global template
uks template set -g "{hostname}: {up}/{total} monitors UP"

# Set with custom config file
uks template set -c /path/to/config.yaml -g "{hostname}: {up}/{total} monitors UP"

# Set per-monitor templates (both UP and DOWN)
uks template set -m cpu_usage \
  --up "CPU OK: {cpu_usage:.1f}% ({num_cores} cores)" \
  --down "CPU ALERT: {cpu_usage:.1f}% exceeds threshold!"

# Set only the UP template for a monitor type
uks template set -m ping --up "Ping {ping_host}: {ping_avg_ms:.0f}ms"

# Show available template variables for a type
uks template vars cpu_usage

# Reset templates to defaults
uks template reset -g           # Reset global template
uks template reset -m cpu_usage # Reset CPU monitor template

# ── Service Management ───────────────────────────────────────────

# Check service status
uks service status
```
