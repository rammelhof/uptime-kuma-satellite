# Configuration

## Config File Location

The config file is stored system-wide by default:

| Platform | Config Path |
|----------|-------------|
| Linux | `/etc/uptime-kuma-satellite/config.yaml` |
| macOS | `/opt/uptime-kuma-satellite/config.yaml` |
| Windows | `%ProgramData%\uptime-kuma-satellite\config.yaml` |

Override with the `-c` / `--config` flag:

```bash
uks setup -c /path/to/custom/config.yaml -u "http://your-uptime-kuma/api/push/YOUR_API_KEY"
```

## Config File Format

```yaml
push_url: http://your-uptime-kuma/api/push/YOUR_API_KEY
hostname: my-server
default_interval: 60
templates:
  global_template: "{hostname}: {up}/{total} monitors UP"
  monitor_templates:
    cpu_usage:
      up: "CPU OK: {cpu_usage:.1f}%"
      down: "CPU ALERT: {cpu_usage:.1f}%!"
    ping:
      up: "Pinging {ping_host}: {ping_avg_ms:.0f}ms"
monitors:
  - name: root-disk
    type: disk_space
    enabled: true
    params:
      path: /
      min_percent: 10
  - name: web-service
    type: service
    enabled: true
    params:
      host: localhost
      port: 8080
      timeout_seconds: 5
```

## Config Options

| Option | Description | Default |
|--------|-------------|---------|
| `push_url` | Uptime Kuma Push API URL (required) | — |
| `hostname` | Hostname reported to Uptime Kuma | system hostname |
| `default_interval` | Default interval in seconds for monitors | 60 |

### Template Options

| Option | Description | Default |
|--------|-------------|---------|
| `templates.global_template` | Format string for aggregated push messages | See [templates](../templates.md) |
| `templates.monitor_templates` | Per-monitor-type UP/DOWN templates | See [templates](../templates.md) |

The `templates` section is optional. If omitted, default templates are used.

## Monitor Config Options

Each monitor entry supports:

| Option | Description | Required |
|--------|-------------|----------|
| `name` | Unique monitor name | Yes |
| `type` | Monitor type (e.g. `disk_space`, `cpu_usage`) | Yes |
| `enabled` | Whether the monitor is active | No (default: `true`) |
| `interval` | Check interval in seconds | No (uses `default_interval`) |
| `params` | Monitor-specific parameters | Yes |

## Managing Config via CLI

It's recommended to use the CLI to manage your config rather than editing the YAML directly:

```bash
# Initialize or update the Push API URL
uks setup -u "http://your-uptime-kuma/api/push/YOUR_API_KEY"

# Add a monitor
uks add-monitor -n "root-disk" -t disk_space \
  --params '{"path": "/", "min_percent": 10}'

# List current config
uks list-monitors

# Remove a monitor
uks remove-monitor -n "old-monitor"
```

### Managing Templates via CLI

```bash
# Show all templates
uks template show

# Set a global template
uks template set -g "{hostname}: {up}/{total} monitors UP"

# Set per-monitor templates
uks template set -m cpu_usage \
  --up "CPU OK: {cpu_usage:.1f}%" \
  --down "CPU HIGH: {cpu_usage:.1f}%!"

# Show available variables for a type
uks template vars cpu_usage

# Reset templates to defaults
uks template reset -g
uks template reset -m cpu_usage
```

> See [docs/templates.md](../templates.md) for full template documentation.
