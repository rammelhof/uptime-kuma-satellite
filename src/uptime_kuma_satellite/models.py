"""Data models for the satellite service."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .template import DEFAULT_MONITOR_TEMPLATES, DEFAULT_GLOBAL_TEMPLATE


class MonitorStatus(enum.Enum):
    UP = "up"
    DOWN = "down"


@dataclass
class MonitorResult:
    """Result of a single monitor check."""
    monitor_name: str
    monitor_type: str
    status: MonitorStatus
    message: str = ""
    ping_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    data: dict[str, Any] = field(default_factory=dict)

    def to_push_params(self) -> dict[str, str]:
        """Convert to Uptime Kuma push API parameters."""
        params: dict[str, str] = {
            "status": self.status.value,
            "msg": self.message,
        }
        if self.ping_ms > 0:
            params["ping"] = f"{self.ping_ms:.0f}"
        return params


@dataclass
class MonitorConfig:
    """Configuration for a single monitor."""
    name: str
    monitor_type: str
    enabled: bool = True
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Monitor name cannot be empty")


@dataclass
class ServiceConfig:
    """Full service configuration."""
    push_url: str
    hostname: str = ""
    monitors: list[MonitorConfig] = field(default_factory=list)
    default_interval: int = 60
    global_template: str = ""
    monitor_templates: dict[str, dict[str, str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.push_url:
            raise ValueError("Push URL cannot be empty")
        if not self.hostname:
            import platform
            self.hostname = platform.node() or "unknown"
        # global_template stays empty by default - templates are opt-in
        # When set, it will use template rendering for push messages


def create_empty_service_config() -> ServiceConfig:
    """Create an empty service config for when no config file exists.

    This bypasses the push_url validation since no config file means
    the user hasn't configured anything yet.
    """
    obj = object.__new__(ServiceConfig)
    obj.push_url = ""
    obj.hostname = ""
    obj.monitors = []
    obj.default_interval = 60
    obj.global_template = ""
    obj.monitor_templates = {}
    return obj
