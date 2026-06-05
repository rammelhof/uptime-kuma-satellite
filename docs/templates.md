# Message Templates

Message templates let you customize how monitor status messages are formatted in push notifications to Uptime Kuma.

## Overview

Templates support two levels:

1. **Global template** — Controls the format of the aggregated push message sent to Uptime Kuma
2. **Per-monitor-type templates** — Control individual monitor status messages (UP/DOWN variants)

Templates use a simple `{variable}` syntax. You can also use format specifiers like `{cpu_usage:.1f}`.

## Global Template

The global template controls the format of the aggregated report sent to Uptime Kuma.

### Variables

| Variable | Description |
|----------|-------------|
| `{hostname}` | The configured hostname |
| `{up}` | Number of monitors that are UP |
| `{down}` | Number of monitors that are DOWN |
| `{total}` | Total number of monitors checked |
| `{messages}` | Pipe-separated list of individual monitor messages |

### Default

```
{hostname}: [UP] {up} | [DOWN] {down} | Total: {total} | {messages}
```

### Examples

```bash
# Simple summary
uks template set -g "{hostname}: {up}/{total} monitors UP"

# Detailed with timestamps
uks template set -g "[{timestamp}] {hostname} — {down} alert(s): {messages}"
```

## Per-Monitor-Type Templates

Each monitor type has separate templates for UP and DOWN states. You can override either or both.

### Common Variables (all types)

| Variable | Description |
|----------|-------------|
| `{name}` | Monitor name |
| `{status}` | "UP" or "DOWN" |
| `{type}` | Monitor type name |
| `{message}` | Raw message from the monitor check |

### Type-Specific Variables

| Monitor Type | Variables |
|-------------|-----------|
| `cpu_usage` | `{cpu_usage}`, `{num_cores}`, `{min_core}`, `{max_core}`, `{threshold}` |
| `memory_usage` | `{memory_usage}`, `{memory_used_mb}`, `{memory_total_mb}`, `{swap_used_mb}`, `{swap_total_mb}`, `{threshold}` |
| `disk_space` | `{disk_path}`, `{disk_free_percent}`, `{disk_free_gb}`, `{disk_total_gb}`, `{threshold}` |
| `ping` | `{ping_host}`, `{ping_avg_ms}`, `{ping_count}`, `{ping_timeout}` |
| `load_average` | `{load1}`, `{load5}`, `{load15}`, `{load_per_core}`, `{num_cores}`, `{threshold}` |
| `service` | `{service_host}`, `{service_port}`, `{service_timeout}` |
| `process` | `{process_name}`, `{process_count}`, `{process_pids}` |
| `process_count` | `{process_pattern}`, `{process_count}`, `{process_min}`, `{process_max}`, `{process_pids}` |
| `file_exists` | `{file_path}` |
| `file_age` | `{file_path}`, `{file_age_seconds}`, `{file_max_age}` |
| `log_file` | `{log_path}`, `{log_lookback_minutes}`, `{log_error_count}`, `{log_last_error}`, `{log_max_errors}` |
| `uptime` | `{uptime_seconds}`, `{uptime_formatted}`, `{uptime_min_seconds}`, `{uptime_min_formatted}` |

### Examples

```bash
# Custom CPU template
uks template set -m cpu_usage \
  --up "CPU OK: {cpu_usage:.1f}% ({num_cores} cores)" \
  --down "CPU ALERT: {cpu_usage:.1f}% exceeds threshold!"

# Simple ping template
uks template set -m ping --up "Pinging {ping_host}: {ping_avg_ms:.0f}ms" --down "Ping to {ping_host} failed"

# Minimal disk template
uks template set -m disk_space --up "Disk OK: {disk_free_percent:.0f}% free" --down "Disk LOW: {disk_free_percent:.0f}% free"
```

## Viewing Templates

### Show all templates

```bash
uks template show
```

### Show global template only

```bash
uks template show -g
```

### Show template for a specific monitor type

```bash
uks template show -m cpu_usage
```

### Show default template for comparison

```bash
uks template show -m cpu_usage -d
```

### Show available variables for a type

```bash
uks template vars cpu_usage
```

## Managing Templates

### Set templates

```bash
# Set global template
uks template set -g "{hostname}: {up}/{total} UP"

# Set per-monitor template (both UP and DOWN)
uks template set -m service --up "Service OK" --down "Service DOWN"
```

### Reset to defaults

```bash
# Reset global template
uks template reset -g

# Reset specific monitor type
uks template reset -m cpu_usage
```

## Format Specifiers

Templates support Python-style format specifiers for numeric values:

| Specifier | Example | Result |
|-----------|---------|--------|
| `{value:.1f}` | `{cpu_usage:.1f}` | `45.3` |
| `{value:.0f}` | `{ping_avg_ms:.0f}` | `12` |
| `{value:.2f}` | `{load1:.2f}` | `1.23` |
| `{value:.1f}` | `{disk_free_gb:.1f}` | `15.4` |

## Using the TUI

You can also edit templates interactively through the TUI:

```bash
uks tui
```

Then click **"Edit Templates"** in the main screen. The template editor has two tabs:
- **Global Template** — Edit the aggregated message format
- **Monitor Templates** — Select a monitor type and edit its UP/DOWN templates

## Configuration File

Templates are stored in the config file under the `templates` key:

```yaml
push_url: http://your-uptime-kuma/api/push/YOUR_API_KEY
hostname: my-server
default_interval: 60
templates:
  global_template: "{hostname}: {up}/{total} monitors UP"
  monitor_templates:
    cpu_usage:
      up: "CPU OK: {cpu_usage:.1f}%"
      down: "CPU HIGH: {cpu_usage:.1f}%"
monitors:
  - name: cpu-test
    type: cpu_usage
    enabled: true
    params: {}
```

> **Note:** The `templates` section is optional. If omitted, default templates are used.
