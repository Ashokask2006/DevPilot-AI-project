"""Disabled Git tools for DevPilot AI.

Git commands must not run on the backend host. Even read-only Git operations can
invoke repository-configured helpers, so these tools remain unavailable until
they can execute inside the restricted Docker sandbox.
"""

from typing import Any, Dict


GIT_EXECUTION_DISABLED_MESSAGE = (
    "Git command execution is disabled until the Docker sandbox is implemented."
)


def _disabled_result() -> Dict[str, Any]:
    return {
        "success": False,
        "execution_enabled": False,
        "error": GIT_EXECUTION_DISABLED_MESSAGE,
    }


def git_status(workspace_root: str) -> Dict[str, Any]:
    """Report that Git status requires the Docker sandbox."""
    return _disabled_result()


def git_diff(workspace_root: str, file_path: str = "") -> Dict[str, Any]:
    """Report that Git diff requires the Docker sandbox."""
    return _disabled_result()
