"""Template engine for log and push messages.

Supports global templates (aggregated push messages) and per-monitor
templates (individual monitor status messages). Templates use a simple
{variable} syntax.

Global template variables:
    {hostname}  - The configured hostname
    {up}        - Number of monitors that are UP
    {down}      - Number of monitors that are DOWN
    {total}     - Total number of monitors checked
    {messages}  - Comma-separated list of individual monitor messages

Per-monitor template variables (always available):
    {name}      - Monitor name
    {status}    - "UP" or "DOWN"
    {message}   - Raw message from the monitor check
    {type}      - Monitor type name (e.g., "cpu_usage")

Per-monitor type-specific variables (filled by each monitor):
    cpu_usage:     {cpu_usage} {num_cores} {min_core} {max_core} {threshold}
    memory_usage:  {memory_usage} {memory_used_mb} {memory_total_mb} {swap_used_mb} {swap_total_mb} {threshold}
    disk_space:    {disk_path} {disk_free_percent} {disk_free_gb} {disk_total_gb} {threshold}
    ping:          {ping_host} {ping_avg_ms} {ping_count} {ping_timeout}
    load_average:  {load1} {load5} {load15} {load_per_core} {num_cores} {threshold}
    service:       {service_host} {service_port} {service_timeout}
    process:       {process_name} {process_count} {process_pids}
    process_count: {process_pattern} {process_count} {process_min} {process_max} {process_pids}
    file_exists:   {file_path}
    file_age:      {file_path} {file_age_seconds} {file_max_age}
    log_file:      {log_path} {log_lookback_minutes} {log_error_count} {log_last_error} {log_max_errors}
    uptime:        {uptime_seconds} {uptime_formatted} {uptime_min_seconds}

Default templates can be overridden per-monitor or globally.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Default global template ──────────────────────────────────────────
# Format: [STATUS] hostname: up=X down=Y total=N: msg1, msg2, ...
DEFAULT_GLOBAL_TEMPLATE = (
    "{hostname}: "
    "[UP] {up} | [DOWN] {down} | Total: {total} | {messages}"
)

# ── Default per-monitor templates ────────────────────────────────────
# Each template is a dict with "up" and "down" variants.
# If only one is given, it's used for both statuses.
DEFAULT_MONITOR_TEMPLATES: dict[str, dict[str, str]] = {
    "cpu_usage": {
        "up": "{name}: [UP] CPU {cpu_usage:.1f}% ({num_cores} cores, {min_core:.0f}-{max_core:.0f}%) | threshold: {threshold}%",
        "down": "{name}: [DOWN] CPU {cpu_usage:.1f}% ({num_cores} cores, {min_core:.0f}-{max_core:.0f}%) | threshold: {threshold}%",
    },
    "memory_usage": {
        "up": "{name}: [UP] Memory {memory_usage:.1f}% ({memory_used_mb:.0f}/{memory_total_mb:.0f}MB) | threshold: {threshold}%",
        "down": "{name}: [DOWN] Memory {memory_usage:.1f}% ({memory_used_mb:.0f}/{memory_total_mb:.0f}MB) | threshold: {threshold}%",
    },
    "disk_space": {
        "up": "{name}: [UP] Disk {disk_free_percent:.1f}% free ({disk_free_gb:.1f}/{disk_total_gb:.1f}GB) on {disk_path} | threshold: {threshold}%",
        "down": "{name}: [DOWN] Disk {disk_free_percent:.1f}% free ({disk_free_gb:.1f}/{disk_total_gb:.1f}GB) on {disk_path} | threshold: {threshold}%",
    },
    "ping": {
        "up": "{name}: [UP] {ping_host} reachable (avg {ping_avg_ms:.0f}ms)",
        "down": "{name}: [DOWN] {ping_host} unreachable",
    },
    "load_average": {
        "up": "{name}: [UP] Load 1m={load1:.2f}, 5m={load5:.2f}, 15m={load15:.2f} | threshold: {threshold}",
        "down": "{name}: [DOWN] Load 1m={load1:.2f}, 5m={load5:.2f}, 15m={load15:.2f} | threshold: {threshold}",
    },
    "service": {
        "up": "{name}: [UP] {service_host}:{service_port} reachable",
        "down": "{name}: [DOWN] {service_host}:{service_port} unreachable",
    },
    "process": {
        "up": "{name}: [UP] Process '{process_name}' running ({process_count} match(es), PIDs: {process_pids})",
        "down": "{name}: [DOWN] Process '{process_name}' NOT running",
    },
    "process_count": {
        "up": "{name}: [UP] {process_count} process(es) matching '{process_pattern}' (min={process_min}, max={process_max})",
        "down": "{name}: [DOWN] {process_count} process(es) matching '{process_pattern}' (min={process_min}, max={process_max})",
    },
    "file_exists": {
        "up": "{name}: [UP] File {file_path} exists",
        "down": "{name}: [DOWN] File {file_path} missing",
    },
    "file_age": {
        "up": "{name}: [UP] File {file_path} fresh ({file_age_seconds:.0f}s < {file_max_age}s)",
        "down": "{name}: [DOWN] File {file_path} too old ({file_age_seconds:.0f}s > {file_max_age}s)",
    },
    "log_file": {
        "up": "{name}: [UP] No errors in {log_path} (lookback: {log_lookback_minutes}min, max_errors: {log_max_errors})",
        "down": "{name}: [DOWN] {log_error_count} error(s) in {log_path} (last: {log_last_error[:100]})",
    },
    "uptime": {
        "up": "{name}: [UP] System uptime: {uptime_formatted} (min: {uptime_min_formatted})",
        "down": "{name}: [DOWN] System uptime {uptime_formatted} < minimum {uptime_min_formatted}. Possible reboot.",
    },
}

# ── Template variable help text for each monitor type ────────────────
TEMPLATE_VAR_HELP: dict[str, list[str]] = {
    "cpu_usage": [
        "Template variables: {name}, {status}, {type}, {message}, {cpu_usage}, {num_cores}, "
        "{min_core}, {max_core}, {threshold}",
    ],
    "memory_usage": [
        "Template variables: {name}, {status}, {type}, {message}, {memory_usage}, {memory_used_mb}, "
        "{memory_total_mb}, {swap_used_mb}, {swap_total_mb}, {threshold}",
    ],
    "disk_space": [
        "Template variables: {name}, {status}, {type}, {message}, {disk_path}, {disk_free_percent}, "
        "{disk_free_gb}, {disk_total_gb}, {threshold}",
    ],
    "ping": [
        "Template variables: {name}, {status}, {type}, {message}, {ping_host}, {ping_avg_ms}, "
        "{ping_count}, {ping_timeout}",
    ],
    "load_average": [
        "Template variables: {name}, {status}, {type}, {message}, {load1}, {load5}, {load15}, "
        "{load_per_core}, {num_cores}, {threshold}",
    ],
    "service": [
        "Template variables: {name}, {status}, {type}, {message}, {service_host}, {service_port}, "
        "{service_timeout}",
    ],
    "process": [
        "Template variables: {name}, {status}, {type}, {message}, {process_name}, {process_count}, "
        "{process_pids}",
    ],
    "process_count": [
        "Template variables: {name}, {status}, {type}, {message}, {process_pattern}, {process_count}, "
        "{process_min}, {process_max}, {process_pids}",
    ],
    "file_exists": [
        "Template variables: {name}, {status}, {type}, {message}, {file_path}",
    ],
    "file_age": [
        "Template variables: {name}, {status}, {type}, {message}, {file_path}, {file_age_seconds}, "
        "{file_max_age}",
    ],
    "log_file": [
        "Template variables: {name}, {status}, {type}, {message}, {log_path}, {log_lookback_minutes}, "
        "{log_error_count}, {log_last_error}, {log_max_errors}",
    ],
    "uptime": [
        "Template variables: {name}, {status}, {type}, {message}, {uptime_seconds}, {uptime_formatted}, "
        "{uptime_min_seconds}, {uptime_min_formatted}",
    ],
}


class TemplateEngine:
    """Simple template engine supporting {variable} and {variable:format} syntax."""

    @staticmethod
    def render(template: str, variables: dict[str, Any]) -> str:
        """Render a template string with the given variables.

        Supports both simple {variable} and format {variable:.1f} syntax.
        Unrecognized variables are left as-is (e.g., {unknown} stays {unknown}).
        """
        import re
        
        def replace_match(match: re.Match) -> str:
            full = match.group(0)  # e.g., "{cpu_usage:.1f}"
            var_name = match.group(1)  # e.g., "cpu_usage"
            format_spec = match.group(2) if match.lastindex and match.lastindex >= 2 else ""  # e.g., ".1f"
            
            if var_name not in variables:
                return full  # Leave unknown variables as-is
            
            value = variables[var_name]
            
            if format_spec:
                # Apply format spec
                try:
                    return format(value, format_spec)
                except (ValueError, TypeError):
                    return str(value)
            
            # Simple replacement
            if value is None:
                return "N/A"
            return str(value)
        
        # Match {variable} or {variable:format}
        # Group 1: variable name, Group 2 (optional): format spec
        pattern = r"\{([^}:]+)(?::([^}]*))?\}"
        result = re.sub(pattern, replace_match, template)
        
        # Clean up any remaining unformatted {unknown} placeholders
        result = re.sub(r"\{([^}]+)\}", r"\1", result)
        
        return result


class TemplateManager:
    """Manages global and per-monitor-type templates.

    Attributes:
        global_template: Template string for aggregated push messages.
        monitor_templates: User-overridden per-monitor-type templates
            (dict of {monitor_type: {"up": str, "down": str}}).
    """

    def __init__(
        self,
        global_template: str | None = None,
        monitor_templates: dict[str, dict[str, str]] | None = None,
    ) -> None:
        # Empty string means "no template configured" (opt-in behavior)
        # None means "use default template" (for explicit default)
        self.global_template = global_template if global_template is not None else ""
        self.monitor_templates = monitor_templates or {}

    @property
    def effective_templates(self) -> dict[str, dict[str, str]]:
        """Merge defaults with user overrides."""
        merged: dict[str, dict[str, str]] = {}
        for monitor_type, defaults in DEFAULT_MONITOR_TEMPLATES.items():
            merged[monitor_type] = dict(defaults)  # copy defaults
        # Apply user overrides
        for monitor_type, overrides in self.monitor_templates.items():
            if monitor_type in merged:
                merged[monitor_type].update(overrides)
            else:
                merged[monitor_type] = dict(overrides)
        return merged

    def get_monitor_template(self, monitor_type: str, status: str) -> str:
        """Get the template for a specific monitor type and status.

        Falls back to the global template if no monitor-specific template exists.
        """
        templates = self.effective_templates
        # Normalize status to lowercase for lookup
        status_key = status.lower()
        if monitor_type in templates:
            variant = templates[monitor_type].get(status_key)
            if variant:
                return variant
        # Fallback: use the other variant
        for variant_key in ("up", "down"):
            if monitor_type in templates:
                return templates[monitor_type].get(variant_key, self.global_template)
        return self.global_template

    def render_global_message(
        self,
        hostname: str,
        results: list[dict[str, Any]],
    ) -> str:
        """Render the global aggregated message.

        Args:
            hostname: The system hostname.
            results: List of result dicts with keys:
                - monitor_name, status, message, monitor_type, data

        Returns:
            Rendered global message string.
        """
        up_count = sum(1 for r in results if r["status"] == "UP")
        down_count = sum(1 for r in results if r["status"] == "DOWN")
        total = len(results)

        # Build per-monitor messages for the global message
        individual_messages = []
        for r in results:
            name = r["monitor_name"]
            status = r["status"]
            monitor_type = r["monitor_type"]
            # Use the monitor's own template to render its message
            monitor_template = self.get_monitor_template(monitor_type, status)
            variables = {
                "name": name,
                "status": status,
                "message": r["message"],
                "type": monitor_type,
            }
            variables.update(r.get("data", {}))
            individual_msg = TemplateEngine.render(monitor_template, variables)
            individual_messages.append(individual_msg)

        messages_str = " | ".join(individual_messages)

        return TemplateEngine.render(
            self.global_template,
            {
                "hostname": hostname,
                "up": up_count,
                "down": down_count,
                "total": total,
                "messages": messages_str,
            },
        )

    def get_available_monitor_types(self) -> list[tuple[str, bool]]:
        """Get all registered monitor types with their current template status."""
        from .monitors import MonitorRegistry
        types = MonitorRegistry.list_types()
        result = []
        for t in types:
            has_custom = t in self.monitor_templates
            result.append((t, has_custom))
        return result

    def render_monitor_message(
        self,
        monitor_name: str,
        monitor_type: str,
        status: str,
        message: str,
        data: dict[str, Any],
    ) -> str:
        """Render an individual monitor's message using its template.

        Args:
            monitor_name: Name of the monitor.
            monitor_type: Type of the monitor (e.g., "cpu_usage").
            status: "UP" or "DOWN".
            message: Raw message from the monitor.
            data: Monitor-specific data variables.

        Returns:
            Rendered message string.
        """
        template = self.get_monitor_template(monitor_type, status)
        variables: dict[str, Any] = {
            "name": monitor_name,
            "status": status,
            "message": message,
            "type": monitor_type,
        }
        variables.update(data)
        return TemplateEngine.render(template, variables)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary for config persistence."""
        result: dict[str, Any] = {}
        if self.global_template and self.global_template != DEFAULT_GLOBAL_TEMPLATE:
            result["global_template"] = self.global_template
        if self.monitor_templates:
            result["monitor_templates"] = self.monitor_templates
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TemplateManager:
        """Deserialize from a dictionary loaded from config."""
        return cls(
            global_template=data.get("global_template"),
            monitor_templates=data.get("monitor_templates"),
        )
