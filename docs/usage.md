# Usage / Quick Start

## 1. Configure

Set up your Push API URL to tell the satellite where to send reports:

```bash
uks setup -u "http://your-uptime-kuma/api/push/YOUR_API_KEY"
```

This creates the config file at `/etc/uptime-kuma-satellite/config.yaml` on Linux, `/opt/...` on macOS, or `%ProgramData%...\config.yaml` on Windows.

## 2. Add Monitors

### File Checks

```bash
# Check if a file exists
uks add-monitor -n "app-logs" -t file_exists -i 60

# Check if a file is older than a threshold (alert if file older than 1 hour)
uks add-monitor -n "backup-check" -t file_age -i 300 \
  --params '{"path": "/var/backups/latest.tar.gz", "max_age_seconds": 3600}'
```

### Disk & System Resources

```bash
# Disk space check (alert if less than 10% free)
uks add-monitor -n "root-disk" -t disk_space -i 300 \
  --params '{"path": "/", "min_percent": 10}'

# CPU usage check
uks add-monitor -n "cpu" -t cpu_usage -i 60 \
  --params '{"max_percent": 90}'

# Memory usage check
uks add-monitor -n "memory" -t memory_usage -i 60 \
  --params '{"max_percent": 90}'

# Load average check
uks add-monitor -n "load" -t load_average -i 60 \
  --params '{"max_load": 2.0}'

# Reboot alert (alert if uptime drops below 5 minutes)
uks add-monitor -n "reboot-alert" -t uptime -i 300 \
  --params '{"min_uptime_seconds": 300}'
```

### Services & Processes

```bash
# TCP port check
uks add-monitor -n "web-service" -t service -i 60 \
  --params '{"host": "localhost", "port": 8080}'

# Process check (ensure a process is running)
uks add-monitor -n "nginx" -t process -i 60 \
  --params '{"name": "nginx"}'

# Process count check (ensure N processes matching a pattern)
uks add-monitor -n "worker-pool" -t process_count -i 60 \
  --params '{"pattern": "celery.worker", "min_count": 4, "max_count": 8}'
```

### Network & Logs

```bash
# Ping check
uks add-monitor -n "google-dns" -t ping -i 120 \
  --params '{"host": "8.8.8.8", "count": 2}'

# Log file monitor
uks add-monitor -n "app-errors" -t log_file -i 300 \
  --params '{"path": "/var/log/myapp/app.log", "lookback_minutes": 60}'

# Log file monitor with custom error patterns
uks add-monitor -n "app-warnings" -t log_file -i 300 \
  --params '{"path": "/var/log/myapp/app.log", "lookback_minutes": 60, "error_patterns": "WARN|ALERT|CRITICAL"}'
```

> See [docs/monitors.md](../monitors.md) for a full list of monitor types and their parameters.

## 3. Run

```bash
# Run all monitors once (with aggregated push report)
uks run-once

# Skip monitors with invalid configuration
uks run-once --skip-invalid

# Run continuously in background
uks run

# Or use the interactive TUI
uks tui
```

## 4. Manage

```bash
# List all configured monitors
uks list-monitors

# Remove a monitor
uks remove-monitor -n "old-monitor"

# Show details about a monitor type
uks info service

# List available monitor types
uks list-types
```

## 5. Install as Service

```bash
# Install as a system service (auto-starts on boot)
sudo uks service install

# Check service status
uks service status

# Uninstall the service (preserves your config)
sudo uks service uninstall
```

> See [docs/service.md](../service.md) for platform-specific service management details.

## 6. Monitor Type Info

```bash
# View details about a specific monitor type
uks info service
# Monitor type: service
# Class: ServiceMonitor
# Module: uptime_kuma_satellite.monitors.service
```
