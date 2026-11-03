"""Terminal tools for DevPilot AI.

Project commands are intentionally disabled until they can run inside a
purpose-built, restricted Docker sandbox. The application must never execute
agent-provided commands on the backend host.
"""

import os
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


def analyse_errors(workspace_root: str, error_output: str) -> Dict[str, Any]:
    """
    Parse and diagnose compilation, syntax, runtime, or test error logs.
    Identifies root causes, affected files, and offending line numbers.
    """
    import re
    diagnostics = []

    # Detect Python tracebacks: File "...", line X
    py_tracebacks = re.findall(r'File "([^"]+)", line (\d+)(?:, in (\w+))?', error_output)
    for tb_file, tb_line, tb_func in py_tracebacks:
        # Check if file belongs to workspace
        rel_path = os.path.relpath(tb_file, workspace_root).replace("\\", "/") if os.path.isabs(tb_file) else tb_file
        diagnostics.append({
            "language": "python",
            "file": rel_path,
            "line": int(tb_line),
            "function": tb_func or "unknown",
            "type": "traceback"
        })

    # Detect common Python exceptions
    error_types = re.findall(r'([A-Za-z]+Error|Exception): (.+)', error_output)
    exception_details = [{"type": et, "message": em.strip()} for et, em in error_types]

    # Detect pytest failures
    pytest_failures = re.findall(r'FAILED ([\w/\\.\-]+)::(\w+) - (.+)', error_output)
    test_fails = [{"test_file": tf, "test_name": tn, "reason": tr} for tf, tn, tr in pytest_failures]

    has_errors = bool(diagnostics or exception_details or test_fails or "error" in error_output.lower())

    return {
        "success": True,
        "has_errors": has_errors,
        "tracebacks": diagnostics,
        "exceptions": exception_details,
        "test_failures": test_fails,
        "summary": f"Detected {len(exception_details)} exception(s) and {len(test_fails)} test failure(s)."
    }


def fix_errors(workspace_root: str, file_path: str, target: str, replacement: str) -> Dict[str, Any]:
    """
    Apply a targeted fix to resolve an identified bug in a source file.
    """
    from app.tools.filesystem import edit_file
    return edit_file(workspace_root, file_path, target, replacement)
