"""Monitor plugin base class and registry."""

from __future__ import annotations

import abc
import logging
from typing import Any

from ..models import MonitorConfig, MonitorResult

logger = logging.getLogger(__name__)


class BaseMonitor(abc.ABC):
    """Base class for all monitors.

    Subclasses implement the `check` method to perform a specific
    monitoring task and return a MonitorResult.
    """

    type_name: str = "base"

    def __init__(self, config: MonitorConfig) -> None:
        self.config = config
        self._last_data: dict[str, Any] = {}

    @abc.abstractmethod
    def check(self) -> MonitorResult:
        """Execute the monitor check and return the result."""
        ...

    def get_template_vars(self) -> dict[str, Any]:
        """Return template variables specific to this monitor type.

        Returns data computed during the last check() call.
        Subclasses should override to provide type-specific variables
        (e.g., {cpu_usage}, {disk_free_percent}, etc.) and set self._last_data
        in their check() method.
        """
        return dict(self._last_data)

    def validate_config(self) -> list[str]:
        """Validate monitor-specific configuration.

        Returns a list of error messages (empty if valid).
        """
        return []


class MonitorRegistry:
    """Registry for monitor plugins.

    Use the @registry.register() decorator or call register() directly.
    """

    _registry: dict[str, type[BaseMonitor]] = {}

    @classmethod
    def register(cls, monitor_class: type[BaseMonitor]) -> type[BaseMonitor]:
        """Register a monitor class in the global registry."""
        type_name = getattr(monitor_class, "type_name", None)
        if not type_name:
            raise TypeError(f"{monitor_class.__name__} must have a non-empty type_name attribute")
        cls._registry[type_name] = monitor_class
        logger.info("Registered monitor: %s (%s)", type_name, monitor_class.__name__)
        return monitor_class

    @classmethod
    def get(cls, monitor_type: str) -> type[BaseMonitor] | None:
        """Get a monitor class by type name."""
        return cls._registry.get(monitor_type)

    @classmethod
    def list_types(cls) -> list[str]:
        """List all registered monitor type names."""
        return sorted(cls._registry.keys())

    @classmethod
    def create(cls, config: MonitorConfig) -> BaseMonitor:
        """Create a monitor instance from config."""
        monitor_class = cls.get(config.monitor_type)
        if monitor_class is None:
            available = ", ".join(cls.list_types())
            raise ValueError(
                f"Unknown monitor type: {config.monitor_type}. "
                f"Available: {available}"
            )
        instance = monitor_class(config)
        errors = instance.validate_config()
        if errors:
            raise ValueError(f"Invalid config for {config.monitor_type}: {'; '.join(errors)}")
        return instance

    @classmethod
    def reset(cls) -> None:
        """Reset the registry (useful for testing)."""
        cls._registry.clear()


def _auto_register_builtin_monitors() -> None:
    """Auto-register all built-in monitor modules."""
    import uptime_kuma_satellite.monitors.file_exists  # noqa: F401
    import uptime_kuma_satellite.monitors.file_age  # noqa: F401
    import uptime_kuma_satellite.monitors.disk_space  # noqa: F401
    import uptime_kuma_satellite.monitors.process  # noqa: F401
    import uptime_kuma_satellite.monitors.service  # noqa: F401
    import uptime_kuma_satellite.monitors.cpu_usage  # noqa: F401
    import uptime_kuma_satellite.monitors.memory_usage  # noqa: F401
    import uptime_kuma_satellite.monitors.load_average  # noqa: F401
    import uptime_kuma_satellite.monitors.ping  # noqa: F401
    import uptime_kuma_satellite.monitors.log_file  # noqa: F401
    import uptime_kuma_satellite.monitors.process_count  # noqa: F401
    import uptime_kuma_satellite.monitors.uptime  # noqa: F401


# Auto-register all built-in monitors on import
_auto_register_builtin_monitors()
