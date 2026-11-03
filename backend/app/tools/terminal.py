"""Terminal tools for DevPilot AI.

Project commands are intentionally disabled until they can run inside a
purpose-built, restricted Docker sandbox. The application must never execute
agent-provided commands on the backend host.
"""

from typing import Any, Dict, Optional


EXECUTION_DISABLED_MESSAGE = (
    "Project command execution is disabled until the Docker sandbox is implemented."
)


def _disabled_result() -> Dict[str, Any]:
    return {
        "success": False,
        "execution_enabled": False,
        "return_code": None,
        "stdout": "",
        "stderr": EXECUTION_DISABLED_MESSAGE,
        "duration_seconds": 0.0,
        "timed_out": False,
        "error": EXECUTION_DISABLED_MESSAGE,
    }


def run_command(
    workspace_root: str,
    command: str,
    timeout_seconds: int = 30,
    max_output_bytes: int = 500000,
) -> Dict[str, Any]:
    """Report that direct command execution is unavailable."""
    return _disabled_result()


def run_tests(workspace_root: str, test_cmd: Optional[str] = None) -> Dict[str, Any]:
    """Report that project test execution requires the Docker sandbox."""
    return _disabled_result()
