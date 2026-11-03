"""
Execution and Terminal Tools for DevPilot AI.
Provides controlled command execution, testing, error analysis, and debugging
within project workspaces with timeouts and security restrictions.
"""

import os
import subprocess
import shlex
import time
from typing import Dict, Any, List, Optional

# Risky commands that require explicit caution or denial
BLOCKED_COMMAND_PATTERNS = [
    "format ",
    "del /s /q c:",
    "rmdir /s /q c:",
    "shutdown",
    "reg delete",
    "mkfs",
    ":(){ :|:& };:",
    "curl | sh",
    "wget | sh"
]


def run_command(
    workspace_root: str,
    command: str,
    timeout_seconds: int = 30,
    max_output_bytes: int = 500000
) -> Dict[str, Any]:
    """
    Execute a shell command inside the workspace root with strict timeout and output limits.
    """
    workspace_abs = os.path.abspath(workspace_root)
    if not os.path.isdir(workspace_abs):
        return {"success": False, "error": f"Workspace directory not found: {workspace_root}"}

    # Security check for blatantly destructive host commands
    cmd_lower = command.lower()
    for blocked in BLOCKED_COMMAND_PATTERNS:
        if blocked in cmd_lower:
            return {
                "success": False,
                "error": f"Command rejected: Contains restricted or destructive pattern '{blocked}'."
            }

    start_time = time.perf_counter()
    try:
        # Run inside the project's workspace directory
        process = subprocess.run(
            command,
            cwd=workspace_abs,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            encoding="utf-8",
            errors="replace"
        )
        elapsed_sec = round(time.perf_counter() - start_time, 2)
        stdout = process.stdout[:max_output_bytes]
        stderr = process.stderr[:max_output_bytes]
        
        return {
            "success": process.returncode == 0,
            "return_code": process.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "duration_seconds": elapsed_sec,
            "timed_out": False
        }
    except subprocess.TimeoutExpired:
        elapsed_sec = round(time.perf_counter() - start_time, 2)
        return {
            "success": False,
            "return_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout_seconds} seconds.",
            "duration_seconds": elapsed_sec,
            "timed_out": True
        }
    except Exception as e:
        elapsed_sec = round(time.perf_counter() - start_time, 2)
        return {
            "success": False,
            "return_code": -1,
            "stdout": "",
            "stderr": str(e),
            "duration_seconds": elapsed_sec,
            "timed_out": False
        }


def run_tests(workspace_root: str, test_cmd: Optional[str] = None) -> Dict[str, Any]:
    """
    Run automated tests in the workspace (auto-detects pytest, npm test, etc.).
    """
    workspace_abs = os.path.abspath(workspace_root)
    if not test_cmd:
        # Auto-detect test runner
        if os.path.exists(os.path.join(workspace_abs, "package.json")):
            test_cmd = "npm test"
        elif os.path.exists(os.path.join(workspace_abs, "pytest.ini")) or os.path.exists(os.path.join(workspace_abs, "tests")):
            test_cmd = "python -m pytest"
        else:
            test_cmd = "python -m unittest discover"

    return run_command(workspace_root, test_cmd)


def analyse_errors(workspace_root: str, error_log: str) -> Dict[str, Any]:
    """
    Parse and diagnose compilation, syntax, runtime, or test error logs.
    Identifies root causes, affected files, and offending line numbers.
    """
    import re
    diagnostics = []

    # Detect Python tracebacks: File "...", line X
    py_tracebacks = re.findall(r'File "([^"]+)", line (\d+)(?:, in (\w+))?', error_log)
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
    error_types = re.findall(r'([A-Za-z]+Error|Exception): (.+)', error_log)
    exception_details = [{"type": et, "message": em.strip()} for et, em in error_types]

    # Detect pytest failures
    pytest_failures = re.findall(r'FAILED ([\w/\\.\-]+)::(\w+) - (.+)', error_log)
    test_fails = [{"test_file": tf, "test_name": tn, "reason": tr} for tf, tn, tr in pytest_failures]

    has_errors = bool(diagnostics or exception_details or test_fails or "error" in error_log.lower())

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