"""Configuration file management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from .models import MonitorConfig, ServiceConfig, create_empty_service_config

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "uptime-kuma-satellite"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"


class ConfigManager:
    """Manages loading and saving the service configuration."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or DEFAULT_CONFIG_FILE

    def load(self) -> ServiceConfig:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            logger.info("No config file found at %s", self.config_path)
            return create_empty_service_config()

        with open(self.config_path, "r") as f:
            data = yaml.safe_load(f) or {}

        monitors = []
        for m in data.get("monitors", []):
            monitors.append(MonitorConfig(
                name=m["name"],
                monitor_type=m["type"],
                enabled=m.get("enabled", True),
                interval_seconds=m.get("interval", data.get("default_interval", 60)),
                params=m.get("params", {}),
            ))

        push_url = data.get("push_url", "")
        if not push_url:
            return create_empty_service_config()
        return ServiceConfig(
            push_url=push_url,
            hostname=data.get("hostname", ""),
            monitors=monitors,
            default_interval=data.get("default_interval", 60),
        )

    def save(self, config: ServiceConfig) -> None:
        """Save configuration to YAML file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        data: dict[str, Any] = {
            "push_url": config.push_url,
            "hostname": config.hostname,
            "default_interval": config.default_interval,
            "monitors": [
                {
                    "name": m.name,
                    "type": m.monitor_type,
                    "enabled": m.enabled,
                    "interval": m.interval_seconds,
                    "params": m.params,
                }
                for m in config.monitors
            ],
        }

        with open(self.config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        logger.info("Config saved to %s", self.config_path)

    @property
    def exists(self) -> bool:
        return self.config_path.exists()
