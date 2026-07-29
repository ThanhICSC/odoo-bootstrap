"""Integration tests for the CLI using Typer's test runner."""

import pytest
from typer.testing import CliRunner

from odoo_bootstrap.main import app

runner = CliRunner()


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "1.0.0" in result.output


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "odoo-bootstrap" in result.output.lower() or "Usage" in result.output


def test_init_help():
    result = runner.invoke(app, ["init", "--help"])
    assert result.exit_code == 0
    assert "workspace" in result.output.lower() or "version" in result.output.lower()


def test_doctor_help():
    result = runner.invoke(app, ["doctor", "--help"])
    assert result.exit_code == 0


def test_create_project_help():
    result = runner.invoke(app, ["create-project", "--help"])
    assert result.exit_code == 0


def test_status_help():
    result = runner.invoke(app, ["status", "--help"])
    assert result.exit_code == 0


def test_backup_help():
    result = runner.invoke(app, ["backup", "--help"])
    assert result.exit_code == 0


def test_restore_help():
    result = runner.invoke(app, ["restore", "--help"])
    assert result.exit_code == 0
