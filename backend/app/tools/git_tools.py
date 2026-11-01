"""
Git integration tools for DevPilot AI.
Provides status, diff, and revision checks for projects.
"""

import subprocess
import os
from typing import Dict, Any


def git_status(workspace_root: str) -> Dict[str, Any]:
    """
    Get git status of the project workspace.
    """
    workspace_abs = os.path.abspath(workspace_root)
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=workspace_abs,
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace"
        )
        if proc.returncode != 0:
            return {"success": False, "is_repo": False, "error": proc.stderr.strip()}

        changes = []
        for line in proc.stdout.splitlines():
            if line.strip():
                status_code = line[:2].strip()
                file_name = line[3:].strip()
                changes.append({"status": status_code, "file": file_name})

        return {"success": True, "is_repo": True, "changes": changes, "raw": proc.stdout}
    except Exception as e:
        return {"success": False, "error": str(e)}


def git_diff(workspace_root: str, file_path: str = "") -> Dict[str, Any]:
    """
    Get git diff for uncommitted modifications.
    """
    workspace_abs = os.path.abspath(workspace_root)
    try:
        cmd = ["git", "diff"]
        if file_path:
            cmd.append(file_path)
            
        proc = subprocess.run(
            cmd,
            cwd=workspace_abs,
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="replace"
        )
        return {
            "success": proc.returncode == 0,
            "diff": proc.stdout,
            "has_diff": bool(proc.stdout.strip())
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
