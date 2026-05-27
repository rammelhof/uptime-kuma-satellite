"""Tests for the monitor registry and base classes."""

import pytest
from uptime_kuma_satellite.models import MonitorConfig, MonitorResult, MonitorStatus
from uptime_kuma_satellite.monitors import BaseMonitor, MonitorRegistry


class DummyMonitor(BaseMonitor):
    type_name = "dummy"

    def check(self) -> MonitorResult:
        return MonitorResult(
            monitor_name=self.config.name,
            monitor_type=self.type_name,
            status=MonitorStatus.UP,
            message="dummy ok",
        )


class TestMonitorRegistry:
    """Tests for the MonitorRegistry."""

    def setup_method(self) -> None:
        MonitorRegistry.reset()

    def test_register_and_get(self) -> None:
        MonitorRegistry.register(DummyMonitor)
        cls = MonitorRegistry.get("dummy")
        assert cls is not None
        assert cls.type_name == "dummy"

    def test_list_types(self) -> None:
        MonitorRegistry.register(DummyMonitor)
        types = MonitorRegistry.list_types()
        assert "dummy" in types

    def test_create_monitor(self) -> None:
        MonitorRegistry.register(DummyMonitor)
        config = MonitorConfig(name="test", monitor_type="dummy")
        instance = MonitorRegistry.create(config)
        assert isinstance(instance, DummyMonitor)
        assert instance.config.name == "test"

    def test_unknown_type(self) -> None:
        config = MonitorConfig(name="test", monitor_type="nonexistent")
        with pytest.raises(ValueError, match="Unknown monitor type"):
            MonitorRegistry.create(config)

    def test_reset(self) -> None:
        MonitorRegistry.register(DummyMonitor)
        MonitorRegistry.reset()
        assert MonitorRegistry.get("dummy") is None

    def test_missing_type_name(self) -> None:
        class BadMonitor(BaseMonitor):
            type_name = None  # type: ignore[assignment]

            def check(self) -> MonitorResult:
                ...

        with pytest.raises(TypeError, match="type_name"):
            MonitorRegistry.register(BadMonitor)


class TestMonitorResult:
    """Tests for MonitorResult model."""

    def test_to_push_params_up(self) -> None:
        result = MonitorResult(
            monitor_name="test",
            monitor_type="dummy",
            status=MonitorStatus.UP,
            message="all good",
            ping_ms=42.5,
        )
        params = result.to_push_params()
        assert params["status"] == "up"
        assert params["msg"] == "all good"
        assert params["ping"] == "42"

    def test_to_push_params_down(self) -> None:
        result = MonitorResult(
            monitor_name="test",
            monitor_type="dummy",
            status=MonitorStatus.DOWN,
            message="file missing: /tmp/test.txt",
        )
        params = result.to_push_params()
        assert params["status"] == "down"
        assert params["msg"] == "file missing: /tmp/test.txt"
        assert "ping" not in params

    def test_monitor_config_validation(self) -> None:
        with pytest.raises(ValueError, match="name cannot be empty"):
            MonitorConfig(name="", monitor_type="dummy")

        with pytest.raises(ValueError, match="Interval must be"):
            MonitorConfig(name="test", monitor_type="dummy", interval_seconds=0)


class TestMonitorConfig:
    """Tests for MonitorConfig model."""

    def test_defaults(self) -> None:
        config = MonitorConfig(name="test", monitor_type="dummy")
        assert config.enabled is True
        assert config.interval_seconds == 60
        assert config.params == {}
