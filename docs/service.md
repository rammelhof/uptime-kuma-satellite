# Service Management

## Install as a System Service

The satellite can run as a background service that auto-starts on boot.

```bash
# Configure
uks setup -u "http://your-uptime-kuma/api/push/YOUR_API_KEY"

# Install the service
sudo uks service install
```

## Platform-Specific Service Managers

| Platform | Service Manager | Requirements |
|----------|----------------|--------------|
| Linux | systemd | `sudo` privileges |
| macOS | launchd | `sudo` privileges |
| Windows | Windows Service | `pip install pywin32`, Administrator |

## Linux (systemd)

The service is installed as `/etc/systemd/system/uptime-kuma-satellite.service`.

```bash
# Start the service
sudo systemctl start uptime-kuma-satellite

# Stop the service
sudo systemctl stop uptime-kuma-satellite

# Enable auto-start on boot
sudo systemctl enable uptime-kuma-satellite

# Disable auto-start
sudo systemctl disable uptime-kuma-satellite

# View logs
sudo journalctl -u uptime-kuma-satellite -f
```

## macOS (launchd)

```bash
# Start the service
sudo launchctl load /Library/LaunchDaemons/uptime-kuma-satellite.plist

# Stop the service
sudo launchctl bootout system/uptime-kuma-satellite

# Check status
launchctl list uptime-kuma-satellite
```

## Windows

```powershell
# Check service status
uks service status

# Start the service
net start "uptime-kuma-satellite"

# Stop the service
net stop "uptime-kuma-satellite"

# Uninstall the service
uks service uninstall
```

> See [docs/windows.md](windows.md) for detailed Windows service configuration.

## Service Log Locations

| Platform | Log Path |
|----------|----------|
| Linux | `/var/log/uptime-kuma-satellite/satellite.log` |
| macOS | `/var/log/uptime-kuma-satellite/satellite.log` |
| Windows | `C:\ProgramData\uptime-kuma-satellite\satellite.log` |

## Custom Config Path

You can override the default system-wide config with `-c`:

```bash
# Use a custom config file
uks setup -c /etc/uptime-kuma-satellite/custom-config.yaml -u "http://your-uptime-kuma/api/push/YOUR_API_KEY"
sudo uks service install -c /etc/uptime-kuma-satellite/custom-config.yaml
```
