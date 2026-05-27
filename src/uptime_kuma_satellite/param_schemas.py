"""Parameter field schemas for monitor types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParamField:
    """Definition of a single parameter input field."""
    key: str
    label: str
    kind: str = "text"  # text, number, path
    default: str = ""
    help: str = ""


PARAM_SCHEMAS: dict[str, list[ParamField]] = {
    "file_exists": [
        ParamField("path", "File Path", "path", "/tmp/monitor.txt",
                   "Full path to the file to check existence for"),
    ],
    "file_age": [
        ParamField("path", "File Path", "path", "/tmp/latest.log",
                   "Maximum allowed file age in seconds (1 hour = 3600)"),
        ParamField("max_age_seconds", "Max Age (seconds)", "number", "3600",
                   "Maximum allowed file age in seconds (1 hour = 3600)"),
    ],
    "disk_space": [
        ParamField("path", "Mount Point", "path", "/",
                   "Disk mount point to check (e.g., /, /home, C:\\)"),
        ParamField("min_percent", "Min Free %", "number", "10",
                   "Alert when free space drops below this percentage"),
    ],
    "service": [
        ParamField("host", "Host", "text", "localhost",
                   "Hostname or IP address to check"),
        ParamField("port", "Port", "number", "80",
                   "TCP port number to check"),
        ParamField("timeout_seconds", "Timeout (seconds)", "number", "5",
                   "Connection timeout in seconds"),
    ],
    "process": [
        ParamField("name", "Process Name", "text", "nginx",
                   "Process name or command to search for"),
    ],
    "cpu_usage": [
        ParamField("max_percent", "Max CPU %", "number", "90",
                   "Alert when CPU usage exceeds this percentage"),
    ],
    "memory_usage": [
        ParamField("max_percent", "Max Memory %", "number", "90",
                   "Alert when memory usage exceeds this percentage"),
    ],
    "load_average": [
        ParamField("max_load", "Max Load", "number", "2.0",
                   "Alert when 1-minute load average exceeds this value"),
    ],
    "ping": [
        ParamField("host", "Host", "text", "8.8.8.8",
                   "Hostname or IP to ping"),
        ParamField("count", "Ping Count", "number", "3",
                   "Number of ping packets to send"),
        ParamField("timeout_seconds", "Timeout (seconds)", "number", "5",
                   "Timeout per ping in seconds"),
    ],
    "log_file": [
        ParamField("path", "Log File Path", "path", "/var/log/app/error.log",
                   "Path to the log file to monitor"),
        ParamField("lookback_minutes", "Lookback (minutes)", "number", "60",
                   "How far back in the log to search for errors"),
        ParamField("max_errors", "Max Errors", "number", "1",
                   "Alert if this many or more errors are found"),
    ],
}

HELP_TEXTS: dict[str, str] = {
    "file_exists": "Checks if a file exists at the specified path.",
    "file_age": "Checks if a file is older than a threshold.",
    "disk_space": "Checks free disk space percentage on a mount point.",
    "service": "Checks if a TCP port is open and reachable.",
    "process": "Checks if a named process is currently running.",
    "cpu_usage": "Checks current CPU usage percentage.",
    "memory_usage": "Checks current memory usage percentage.",
    "load_average": "Checks system load average.",
    "ping": "Checks network reachability via ICMP ping.",
    "log_file": "Monitors a log file for recent error entries.",
}


def get_param_schema(monitor_type: str) -> list[ParamField]:
    """Get the parameter schema for a monitor type."""
    return PARAM_SCHEMAS.get(monitor_type, [
        ParamField("key", "Parameter", "text", "", "Enter parameter key=value"),
    ])


def get_type_help(monitor_type: str) -> str:
    """Get a help description for a monitor type."""
    return HELP_TEXTS.get(monitor_type, "")
