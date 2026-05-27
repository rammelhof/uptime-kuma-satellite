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
monitors:
  - name: root-disk
    type: disk_space
    enabled: true
    interval: 300
    params:
      path: /
      min_percent: 10
  - name: web-service
    type: service
    enabled: true
    interval: 60
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
uks add-monitor -n "root-disk" -t disk_space -i 300 \
  --params '{"path": "/", "min_percent": 10}'

# List current config
uks list-monitors

# Remove a monitor
uks remove-monitor -n "old-monitor"
```
