"""Tests for CLI template commands."""

from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from uptime_kuma_satellite.cli import app
from uptime_kuma_satellite.config import ConfigManager
from uptime_kuma_satellite.models import ServiceConfig


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def config_path(tmp_path: Path):
    """Create a minimal config file and return its path."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "push_url: http://localhost:3001/api/push/test123\n"
        "hostname: test-host\n"
        "default_interval: 60\n"
        "monitors:\n"
        "  - name: cpu-test\n"
        "    type: cpu_usage\n"
        "    enabled: true\n"
        "    params: {}\n"
    )
    return config_file


class TestTemplateShow:
    """Tests for `uks template show`."""

    def test_show_all_defaults(self, runner, config_path):
        result = runner.invoke(app, ["template", "show", "-c", str(config_path)])
        assert result.exit_code == 0
        assert "Global Template" in result.stdout
        assert "Per-Monitor-Type Templates" in result.stdout
        assert "using default" in result.stdout

    def test_show_global_only(self, runner, config_path):
        result = runner.invoke(app, ["template", "show", "-c", str(config_path), "-g"])
        assert result.exit_code == 0
        assert "using default" in result.stdout

    def test_show_global_with_custom_template(self, runner, config_path):
        # First set a custom template
        runner.invoke(
            app,
            [
                "template",
                "set",
                "-c",
                str(config_path),
                "-g",
                "Custom: {up}/{total} UP",
            ],
        )
        result = runner.invoke(app, ["template", "show", "-c", str(config_path), "-g"])
        assert result.exit_code == 0
        assert "Custom: {up}/{total} UP" in result.stdout

    def test_show_monitor_type(self, runner, config_path):
        result = runner.invoke(
            app, ["template", "show", "-c", str(config_path), "-m", "cpu_usage"]
        )
        assert result.exit_code == 0
        assert "cpu_usage" in result.stdout
        assert "using default" in result.stdout

    def test_show_monitor_type_with_custom(self, runner, config_path):
        runner.invoke(
            app,
            [
                "template",
                "set",
                "-c",
                str(config_path),
                "-m",
                "cpu_usage",
                "--up",
                "CPU: {cpu_usage:.1f}%",
            ],
        )
        result = runner.invoke(
            app, ["template", "show", "-c", str(config_path), "-m", "cpu_usage"]
        )
        assert result.exit_code == 0
        assert "custom" in result.stdout.lower()
        assert "CPU: {cpu_usage:.1f}%" in result.stdout

    def test_show_monitor_type_with_default_comparison(self, runner, config_path):
        result = runner.invoke(
            app,
            [
                "template",
                "show",
                "-c",
                str(config_path),
                "-m",
                "cpu_usage",
                "-d",
            ],
        )
        assert result.exit_code == 0
        assert "Default template" in result.stdout
        assert "cpu_usage" in result.stdout

    def test_show_unknown_monitor_type(self, runner, config_path):
        result = runner.invoke(
            app, ["template", "show", "-c", str(config_path), "-m", "nonexistent"]
        )
        assert result.exit_code != 0
        assert "Unknown monitor type" in result.stdout


class TestTemplateSet:
    """Tests for `uks template set`."""

    def test_set_global_template(self, runner, config_path):
        result = runner.invoke(
            app,
            [
                "template",
                "set",
                "-c",
                str(config_path),
                "-g",
                "{hostname}: {up} UP",
            ],
        )
        assert result.exit_code == 0
        assert "Global template set" in result.stdout

        # Verify config was saved
        mgr = ConfigManager(config_path)
        config = mgr.load()
        assert config.global_template == "{hostname}: {up} UP"

    def test_set_monitor_template_up_only(self, runner, config_path):
        result = runner.invoke(
            app,
            [
                "template",
                "set",
                "-c",
                str(config_path),
                "-m",
                "cpu_usage",
                "--up",
                "CPU OK",
            ],
        )
        assert result.exit_code == 0
        assert "UP set" in result.stdout

        mgr = ConfigManager(config_path)
        config = mgr.load()
        assert config.monitor_templates["cpu_usage"]["up"] == "CPU OK"
        # DOWN should not be set
        assert "down" not in config.monitor_templates["cpu_usage"]

    def test_set_monitor_template_down_only(self, runner, config_path):
        result = runner.invoke(
            app,
            [
                "template",
                "set",
                "-c",
                str(config_path),
                "-m",
                "cpu_usage",
                "--down",
                "CPU HIGH",
            ],
        )
        assert result.exit_code == 0
        assert "DOWN set" in result.stdout

        mgr = ConfigManager(config_path)
        config = mgr.load()
        assert config.monitor_templates["cpu_usage"]["down"] == "CPU HIGH"

    def test_set_monitor_template_both(self, runner, config_path):
        result = runner.invoke(
            app,
            [
                "template",
                "set",
                "-c",
                str(config_path),
                "-m",
                "cpu_usage",
                "--up",
                "CPU OK",
                "--down",
                "CPU HIGH",
            ],
        )
        assert result.exit_code == 0
        assert "UP set" in result.stdout
        assert "DOWN set" in result.stdout

        mgr = ConfigManager(config_path)
        config = mgr.load()
        assert config.monitor_templates["cpu_usage"]["up"] == "CPU OK"
        assert config.monitor_templates["cpu_usage"]["down"] == "CPU HIGH"

    def test_set_global_and_monitor_together(self, runner, config_path):
        result = runner.invoke(
            app,
            [
                "template",
                "set",
                "-c",
                str(config_path),
                "-g",
                "{hostname}: {up} UP",
                "-m",
                "cpu_usage",
                "--up",
                "CPU OK",
            ],
        )
        assert result.exit_code == 0
        assert "Global template set" in result.stdout
        assert "UP set" in result.stdout

        mgr = ConfigManager(config_path)
        config = mgr.load()
        assert config.global_template == "{hostname}: {up} UP"
        assert config.monitor_templates["cpu_usage"]["up"] == "CPU OK"

    def test_set_monitor_unknown_type(self, runner, config_path):
        result = runner.invoke(
            app,
            [
                "template",
                "set",
                "-c",
                str(config_path),
                "-m",
                "nonexistent",
                "--up",
                "test",
            ],
        )
        assert result.exit_code != 0
        assert "Unknown monitor type" in result.stdout

    def test_set_monitor_no_up_or_down(self, runner, config_path):
        result = runner.invoke(
            app,
            [
                "template",
                "set",
                "-c",
                str(config_path),
                "-m",
                "cpu_usage",
            ],
        )
        assert result.exit_code != 0
        assert "at least --up or --down" in result.stdout


class TestTemplateReset:
    """Tests for `uks template reset`."""

    def test_reset_global(self, runner, config_path):
        # First set a custom template
        runner.invoke(
            app,
            [
                "template",
                "set",
                "-c",
                str(config_path),
                "-g",
                "Custom",
            ],
        )
        result = runner.invoke(app, ["template", "reset", "-c", str(config_path), "-g"])
        assert result.exit_code == 0
        assert "Global template reset" in result.stdout

        mgr = ConfigManager(config_path)
        config = mgr.load()
        assert config.global_template == ""

    def test_reset_monitor_type(self, runner, config_path):
        # First set a custom template
        runner.invoke(
            app,
            [
                "template",
                "set",
                "-c",
                str(config_path),
                "-m",
                "cpu_usage",
                "--up",
                "Custom CPU",
            ],
        )
        result = runner.invoke(
            app, ["template", "reset", "-c", str(config_path), "-m", "cpu_usage"]
        )
        assert result.exit_code == 0
        assert "reset to default" in result.stdout

        mgr = ConfigManager(config_path)
        config = mgr.load()
        assert "cpu_usage" not in config.monitor_templates

    def test_reset_monitor_type_not_set(self, runner, config_path):
        result = runner.invoke(
            app, ["template", "reset", "-c", str(config_path), "-m", "cpu_usage"]
        )
        assert result.exit_code == 0
        assert "No custom template" in result.stdout

    def test_reset_monitor_unknown_type(self, runner, config_path):
        result = runner.invoke(
            app, ["template", "reset", "-c", str(config_path), "-m", "nonexistent"]
        )
        assert result.exit_code != 0
        assert "Unknown monitor type" in result.stdout


class TestTemplateVars:
    """Tests for `uks template vars`."""

    def test_show_vars_cpu_usage(self, runner, config_path):
        result = runner.invoke(app, ["template", "vars", "cpu_usage"])
        assert result.exit_code == 0
        assert "cpu_usage" in result.stdout
        assert "Common variables" in result.stdout
        assert "Type-specific variables" in result.stdout
        assert "{cpu_usage}" in result.stdout
        assert "{num_cores}" in result.stdout

    def test_show_vars_ping(self, runner, config_path):
        result = runner.invoke(app, ["template", "vars", "ping"])
        assert result.exit_code == 0
        assert "{ping_host}" in result.stdout
        assert "{ping_avg_ms}" in result.stdout

    def test_show_vars_unknown_type(self, runner, config_path):
        result = runner.invoke(app, ["template", "vars", "nonexistent"])
        assert result.exit_code != 0
        assert "Unknown monitor type" in result.stdout

    def test_show_vars_with_custom_config(self, runner, config_path):
        result = runner.invoke(
            app, ["template", "vars", "-c", str(config_path), "cpu_usage"]
        )
        assert result.exit_code == 0
        assert "{cpu_usage}" in result.stdout


class TestTemplateConsistency:
    """Tests for -c option consistency across template commands."""

    @pytest.mark.parametrize(
        "cmd",
        [
            ["template", "show", "-c", "dummy"],
            ["template", "set", "-c", "dummy", "-g", "test"],
            ["template", "set", "-c", "dummy", "-m", "cpu_usage", "--up", "test"],
            ["template", "reset", "-c", "dummy", "-g"],
            ["template", "vars", "-c", "dummy", "cpu_usage"],
        ],
    )
    def test_all_template_commands_accept_config_flag(self, runner, config_path, cmd):
        """All template commands should accept -c/--config."""
        # Replace dummy with actual path for commands that load config
        cmd = [str(config_path) if p == "dummy" else p for p in cmd]
        result = runner.invoke(app, cmd)
        # Should not fail with "no such option" - exit code may vary due to other reasons
        assert "no such option" not in result.stdout.lower() or result.exit_code == 0
