import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.engine import AgentEngine
from app.tools.registry import ToolRegistry


def _tool_definition(registry: ToolRegistry, name: str) -> dict:
    return next(
        definition
        for definition in registry.get_tool_definitions()
        if definition["name"] == name
    )


def test_error_tool_schemas_match_python_signatures() -> None:
    registry = ToolRegistry()

    for definition in registry.get_tool_definitions():
        tool_name = definition["name"]
        schema_parameters = set(definition["parameters"].get("properties", {}))
        required_parameters = set(definition["parameters"].get("required", []))
        function_parameters = set(inspect.signature(registry._tools[tool_name]).parameters)
        function_parameters.remove("workspace_root")

        assert schema_parameters <= function_parameters
        assert required_parameters <= function_parameters

    expected_parameters = {
        "analyse_errors": {"error_output"},
        "fix_errors": {"file_path", "target", "replacement"},
    }

    for tool_name, expected in expected_parameters.items():
        definition = _tool_definition(registry, tool_name)
        schema_parameters = set(definition["parameters"]["properties"])
        required_parameters = set(definition["parameters"].get("required", []))

        assert schema_parameters == expected
        assert required_parameters == expected


def test_registry_dispatches_analyse_errors_with_error_output(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source_file = workspace / "broken.py"
    source_file.write_text("raise ValueError('broken')\n", encoding="utf-8")
    error_output = (
        "Traceback (most recent call last):\n"
        f'  File "{source_file}", line 1, in <module>\n'
        "ValueError: broken\n"
    )

    result = ToolRegistry().execute_tool(
        "analyse_errors",
        str(workspace),
        {"error_output": error_output},
    )

    assert result["success"] is True
    assert result["has_errors"] is True
    assert result["tracebacks"] == [
        {
            "language": "python",
            "file": "broken.py",
            "line": 1,
            "function": "unknown",
            "type": "traceback",
        }
    ]
    assert result["exceptions"] == [{"type": "ValueError", "message": "broken"}]


def test_registry_dispatches_fix_errors_as_safe_file_edit(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source_file = workspace / "example.py"
    source_file.write_text("result = 'broken'\n", encoding="utf-8")

    result = ToolRegistry().execute_tool(
        "fix_errors",
        str(workspace),
        {
            "file_path": "example.py",
            "target": "'broken'",
            "replacement": "'fixed'",
        },
    )

    assert result["success"] is True
    assert result["path"] == "example.py"
    assert source_file.read_text(encoding="utf-8") == "result = 'fixed'\n"


def test_agent_engine_delegates_tool_dispatch_to_registry(tmp_path: Path) -> None:
    class RecordingRegistry:
        def __init__(self) -> None:
            self.calls = []

        def execute_tool(
            self,
            tool_name: str,
            workspace_root: str,
            arguments: dict,
        ) -> dict:
            self.calls.append((tool_name, workspace_root, arguments))
            return {"success": True, "tool": tool_name}

    registry = RecordingRegistry()
    engine = object.__new__(AgentEngine)
    engine.workspace_root = str(tmp_path)
    engine.registry = registry
    arguments = {"error_output": "ValueError: broken"}

    result = engine._execute_tool("analyse_errors", arguments)

    assert result == {"success": True, "tool": "analyse_errors"}
    assert registry.calls == [("analyse_errors", str(tmp_path), arguments)]


def test_execution_tools_remain_disabled_through_registry(tmp_path: Path) -> None:
    registry = ToolRegistry()
    sentinel = tmp_path / "must-not-exist"

    command_result = registry.execute_tool(
        "run_command",
        str(tmp_path),
        {"command": f"touch {sentinel}"},
    )
    tests_result = registry.execute_tool("run_tests", str(tmp_path), {})

    assert command_result["success"] is False
    assert command_result["execution_enabled"] is False
    assert tests_result["success"] is False
    assert tests_result["execution_enabled"] is False
    assert sentinel.exists() is False
