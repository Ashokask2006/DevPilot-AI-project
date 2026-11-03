import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tools import filesystem, terminal


def test_filesystem_rejects_symlink_escape(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("private", encoding="utf-8")

    escape = workspace / "escape"
    try:
        escape.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks are unavailable on this platform")

    result = filesystem.read_file(str(workspace), "escape/secret.txt")

    assert result["success"] is False
    assert "outside workspace boundaries" in result["error"]
    assert filesystem.is_within_workspace(str(workspace), str(escape / "secret.txt")) is False


def test_filesystem_reports_create_and_overwrite_correctly(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    created = filesystem.create_file(str(workspace), "nested/example.txt", "first")
    overwritten = filesystem.create_file(str(workspace), "nested/example.txt", "second")

    assert created["success"] is True
    assert created["action"] == "created"
    assert overwritten["success"] is True
    assert overwritten["action"] == "overwritten"


def test_terminal_commands_are_disabled_without_a_sandbox(tmp_path: Path) -> None:
    sentinel = tmp_path / "must-not-exist"

    result = terminal.run_command(str(tmp_path), f"touch {sentinel}")

    assert result["success"] is False
    assert result["execution_enabled"] is False
    assert "Docker sandbox" in result["error"]
    assert sentinel.exists() is False


def test_project_test_runner_is_disabled_without_a_sandbox(tmp_path: Path) -> None:
    result = terminal.run_tests(str(tmp_path))

    assert result["success"] is False
    assert result["execution_enabled"] is False
