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
