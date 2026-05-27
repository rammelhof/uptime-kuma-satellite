# Monitor Types

## Monitor Type Reference

| Type | Description | Required Params |
|------|-------------|-----------------|
| `file_exists` | Check if a file exists | `path` |
| `file_age` | Check if a file is older than threshold | `path`, `max_age_seconds` |
| `disk_space` | Check disk free space | `path`, `min_percent` |
| `service` | Check TCP port connectivity | `host`, `port`, `timeout_seconds` |
| `process` | Check if a process is running | `name` |
| `process_count` | Check that N processes matching a pattern are running | `pattern`, `min_count`, `max_count` |
| `uptime` | Check system uptime (anti-reboot alert, minimum 5 min uptime) | `min_uptime_seconds` |
| `cpu_usage` | Check CPU usage percentage | `max_percent` |
| `memory_usage` | Check memory usage percentage | `max_percent` |
| `load_average` | Check system load average | `max_load` |
| `ping` | Check network reachability via ICMP | `host`, `count`, `timeout_seconds` |
| `log_file` | Monitor log file for errors | `path`, `lookback_minutes`, `max_errors`, `error_patterns` |

## Cross-Platform Support

All monitors work on Linux, macOS, and Windows:

| Monitor Type | Linux | macOS | Windows |
|-------------|-------|-------|---------|
| `file_exists` | ✓ | ✓ | ✓ |
| `file_age` | ✓ | ✓ | ✓ |
| `disk_space` | ✓ | ✓ | ✓ |
| `service` | ✓ | ✓ | ✓ |
| `process` | ✓ | ✓ | ✓ |
| `process_count` | ✓ | ✓ | ✓ |
| `uptime` | ✓ | ✓ | ✓ |
| `cpu_usage` | `/proc/stat` | `sysctl` | `GetSystemTimes` API |
| `memory_usage` | `/proc/meminfo` | `resource` module | `GlobalMemoryStatusEx` API |
| `load_average` | `os.getloadavg()` | `os.getloadavg()` | `GetSystemTimes` API |
| `ping` | ✓ | ✓ | ✓ |
| `log_file` | ✓ | ✓ | ✓ |

## Monitor Type Details

### `file_exists`
Check if a file exists on the filesystem.

```bash
uks add-monitor -n "app-logs" -t file_exists -i 60
```

### `file_age`
Alert if a file hasn't been updated within the specified age.

```bash
uks add-monitor -n "backup-check" -t file_age -i 300 \
  --params '{"path": "/var/backups/latest.tar.gz", "max_age_seconds": 3600}'
```

### `disk_space`
Check free disk space percentage.

```bash
uks add-monitor -n "root-disk" -t disk_space -i 300 \
  --params '{"path": "/", "min_percent": 10}'
```

### `service`
Check TCP port connectivity.

```bash
uks add-monitor -n "web-service" -t service -i 60 \
  --params '{"host": "localhost", "port": 8080}'
```

### `process`
Check if a named process is running.

```bash
uks add-monitor -n "nginx" -t process -i 60 \
  --params '{"name": "nginx"}'
```

### `process_count`
Check that N processes matching a pattern are running.

```bash
uks add-monitor -n "worker-pool" -t process_count -i 60 \
  --params '{"pattern": "celery.worker", "min_count": 4, "max_count": 8}'
```

### `uptime`
Alert if system uptime drops below a threshold (useful for detecting unexpected reboots).

```bash
uks add-monitor -n "reboot-alert" -t uptime -i 300 \
  --params '{"min_uptime_seconds": 300}'
```

### `cpu_usage`
Check CPU usage percentage.

```bash
uks add-monitor -n "cpu" -t cpu_usage -i 60 \
  --params '{"max_percent": 90}'
```

### `memory_usage`
Check memory usage percentage.

```bash
uks add-monitor -n "memory" -t memory_usage -i 60 \
  --params '{"max_percent": 90}'
```

### `load_average`
Check system load average.

```bash
uks add-monitor -n "load" -t load_average -i 60 \
  --params '{"max_load": 2.0}'
```

### `ping`
Check network reachability via ICMP.

```bash
uks add-monitor -n "google-dns" -t ping -i 120 \
  --params '{"host": "8.8.8.8", "count": 2}'
```

### `log_file`
Monitor a log file for error patterns within a lookback window.

```bash
uks add-monitor -n "app-errors" -t log_file -i 300 \
  --params '{"path": "/var/log/myapp/app.log", "lookback_minutes": 60}'

# With custom error patterns
uks add-monitor -n "app-warnings" -t log_file -i 300 \
  --params '{"path": "/var/log/myapp/app.log", "lookback_minutes": 60, "error_patterns": "WARN|ALERT|CRITICAL"}'
```
