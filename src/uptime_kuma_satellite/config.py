"""Configuration file management."""

from __future__ import annotations

import logging
import os
import platform
from pathlib import Path
from typing import Any

import yaml

from .models import MonitorConfig, ServiceConfig, create_empty_service_config
from .template import TemplateManager

logger = logging.getLogger(__name__)


def get_system_config_dir() -> Path:
    """Get the system-wide config directory for the current platform."""
    system = platform.system()
    if system == "Windows":
        program_data = os.environ.get("ProgramData", "C:\\ProgramData")
        return Path(program_data) / "uptime-kuma-satellite"
    elif system == "Darwin":
        return Path("/opt/uptime-kuma-satellite")
    else:  # Linux and others
        return Path("/etc/uptime-kuma-satellite")


def get_system_config_file() -> Path:
    """Get the system-wide config file path for the current platform."""
    return get_system_config_dir() / "config.yaml"


class ConfigManager:
    """Manages loading and saving the service configuration."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or get_system_config_file()

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
                params=m.get("params", {}),
            ))

        push_url = data.get("push_url", "")
        if not push_url:
            return create_empty_service_config()
        
        # Load templates from service-level config
        templates_data = data.get("templates", {})
        global_template = templates_data.get("global_template", data.get("global_template", ""))
        monitor_templates = templates_data.get("monitor_templates", {})
        
        return ServiceConfig(
            push_url=push_url,
            hostname=data.get("hostname", ""),
            monitors=monitors,
            default_interval=data.get("default_interval", 60),
            global_template=global_template,
            monitor_templates=monitor_templates,
        )

    def save(self, config: ServiceConfig) -> None:
        """Save configuration to YAML file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Build template manager for serialization
        template_mgr = TemplateManager(
            global_template=config.global_template,
            monitor_templates=config.monitor_templates,
        )
        template_data = template_mgr.to_dict()

        data: dict[str, Any] = {
            "push_url": config.push_url,
            "hostname": config.hostname,
            "default_interval": config.default_interval,
        }
        if template_data:
            data["templates"] = template_data
        data["monitors"] = [
            {
                "name": m.name,
                "type": m.monitor_type,
                "enabled": m.enabled,
                "params": m.params,
            }
            for m in config.monitors
        ]

        with open(self.config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        logger.info("Config saved to %s", self.config_path)

    @property
    def exists(self) -> bool:
        return self.config_path.exists()
