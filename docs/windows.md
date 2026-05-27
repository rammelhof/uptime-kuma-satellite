# Windows Installation

## Windows Service Support

For Windows service support, install the optional dependency:

```powershell
pip install -e ".[windows]"
```

Then run PowerShell as Administrator:

```powershell
uks service install
```

## Windows Service Configuration

The Windows service uses the following configuration file by default:

```
C:\ProgramData\uptime-kuma-satellite\config.yaml
```

**Important:** The service starts automatically on boot and monitors this config file for changes.

### Configuring the Service

You can configure the Windows service by editing the config file directly:

```powershell
notepad "C:\ProgramData\uptime-kuma-satellite\config.yaml"
```

The configuration file supports the same options as the standard config:

```yaml
push_url: http://your-uptime-kuma/api/push/YOUR_API_KEY
hostname: my-windows-pc
default_interval: 60
monitors:
  - name: root-disk
    type: disk_space
    enabled: true
    interval: 300
    params:
      path: C:\
      min_percent: 10
```

### Adding or Modifying Monitors

1. Open the config file with admin privileges
2. Edit the `monitors` section
3. Save the file
4. Restart the service for changes to take effect

```powershell
# Restart the service
net stop "uptime-kuma-satellite"
net start "uptime-kuma-satellite"

# Or using Services management (services.msc)
```

> **Tip:** You can also use the CLI commands with the `-c` flag to specify a custom config path:
>
> ```powershell
> uks setup -c "C:\ProgramData\uptime-kuma-satellite\config.yaml" -u "http://your-uptime-kuma/api/push/YOUR_API_KEY"
> ```

## Managing the Windows Service

```powershell
# Check service status
uks service status

# Start the service
net start "uptime-kuma-satellite"

# Stop the service
net stop "uptime-kuma-satellite"

# Uninstall the service (preserves your config)
uks service uninstall
```

> **Note:** If you uninstall the service and want to keep your configuration, the config file at `C:\ProgramData\uptime-kuma-satellite\config.yaml` will be preserved. Reinstalling the service will automatically use this existing configuration.

## Windows Service Log Location

```
C:\ProgramData\uptime-kuma-satellite\satellite.log
```
