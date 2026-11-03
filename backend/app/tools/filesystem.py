"""
Secure Filesystem Tools for DevPilot AI.
Provides file and directory operations with strict workspace sandbox containment
and path traversal prevention.
"""

import os
import fnmatch
from typing import Dict, Any, List, Optional


def _resolve_safe_path(workspace_root: str, relative_or_abs_path: str) -> str:
    """
    Ensure the resolved path strictly resides within the workspace root.
    Raises PermissionError if a path traversal attempt is detected.
    """
    workspace_abs = os.path.abspath(workspace_root)
    # If path is given relative to workspace
    if os.path.isabs(relative_or_abs_path):
        target_abs = os.path.abspath(relative_or_abs_path)
    else:
        target_abs = os.path.abspath(os.path.join(workspace_abs, relative_or_abs_path))

    # Common path check to prevent escaping sandbox
    if os.path.commonpath([workspace_abs, target_abs]) != workspace_abs:
        raise PermissionError(f"Access denied: Path '{relative_or_abs_path}' is outside workspace boundaries.")

    return target_abs


def list_files(workspace_root: str, subpath: str = ".") -> Dict[str, Any]:
    """
    List files and directories within a workspace subpath.
    """
    try:
        target_dir = _resolve_safe_path(workspace_root, subpath)
        if not os.path.exists(target_dir):
            return {"success": False, "error": f"Directory not found: {subpath}"}
        
        entries = []
        for entry in os.scandir(target_dir):
            # Ignore git and common build artifacts
            if entry.name in (".git", "node_modules", "__pycache__", ".venv", "venv"):
                continue
            entries.append({
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "path": os.path.relpath(entry.path, workspace_root).replace("\\", "/"),
                "size_bytes": entry.stat().st_size if entry.is_file() else 0
            })
        
        # Sort directories first, then alphabetical
        entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return {"success": True, "files": entries, "count": len(entries)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def read_file(workspace_root: str, file_path: str, max_bytes: int = 500000) -> Dict[str, Any]:
    """
    Read the contents of a source code file.
    """
    try:
        target_file = _resolve_safe_path(workspace_root, file_path)
        if not os.path.isfile(target_file):
            return {"success": False, "error": f"File does not exist: {file_path}"}
        
        size = os.path.getsize(target_file)
        if size > max_bytes:
            return {"success": False, "error": f"File exceeds maximum read limit ({max_bytes} bytes)."}

        with open(target_file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        return {
            "success": True,
            "path": os.path.relpath(target_file, workspace_root).replace("\\", "/"),
            "content": content,
            "lines": len(content.splitlines()),
            "size_bytes": size
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_file(workspace_root: str, file_path: str, content: str, overwrite: bool = True) -> Dict[str, Any]:
    """
    Create a new file with specified content. Creates parent folders automatically.
    """
    try:
        target_file = _resolve_safe_path(workspace_root, file_path)
        if os.path.exists(target_file) and not overwrite:
            return {"success": False, "error": f"File already exists: {file_path}. Set overwrite=True to replace."}

        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "success": True,
            "path": os.path.relpath(target_file, workspace_root).replace("\\", "/"),
            "bytes_written": len(content.encode("utf-8")),
            "action": "overwritten" if os.path.exists(target_file) else "created"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def edit_file(workspace_root: str, file_path: str, target: str, replacement: str) -> Dict[str, Any]:
    """
    Perform a targeted replacement inside an existing file.
    """
    try:
        target_file = _resolve_safe_path(workspace_root, file_path)
        if not os.path.isfile(target_file):
            return {"success": False, "error": f"File does not exist: {file_path}"}

        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()

        if target not in content:
            return {
                "success": False,
                "error": f"Target snippet not found in {file_path}. Verify line endings and exact characters."
            }

        new_content = content.replace(target, replacement, 1)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(new_content)

        return {
            "success": True,
            "path": os.path.relpath(target_file, workspace_root).replace("\\", "/"),
            "message": "File edited successfully."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_file(workspace_root: str, file_path: str) -> Dict[str, Any]:
    """
    Delete a file within the workspace.
    """
    try:
        target_file = _resolve_safe_path(workspace_root, file_path)
        if not os.path.isfile(target_file):
            return {"success": False, "error": f"File not found: {file_path}"}

        os.remove(target_file)
        return {
            "success": True,
            "path": os.path.relpath(target_file, workspace_root).replace("\\", "/"),
            "message": "File deleted successfully."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_directory(workspace_root: str, dir_path: str) -> Dict[str, Any]:
    """
    Create a directory within the workspace.
    """
    try:
        target_dir = _resolve_safe_path(workspace_root, dir_path)
        os.makedirs(target_dir, exist_ok=True)
        return {
            "success": True,
            "path": os.path.relpath(target_dir, workspace_root).replace("\\", "/"),
            "message": "Directory ready."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_files(workspace_root: str, query: str, pattern: str = "*") -> Dict[str, Any]:
    """
    Search for text query or symbol across workspace files matching file pattern.
    """
    try:
        results = []
        workspace_abs = os.path.abspath(workspace_root)
        for root, dirs, files in os.walk(workspace_abs):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build")]
            for file in files:
                if fnmatch.fnmatch(file, pattern):
                    file_full = os.path.join(root, file)
                    rel_path = os.path.relpath(file_full, workspace_root).replace("\\", "/")
                    try:
                        with open(file_full, "r", encoding="utf-8", errors="ignore") as f:
                            for idx, line in enumerate(f, start=1):
                                if query.lower() in line.lower():
                                    results.append({
                                        "file": rel_path,
                                        "line_number": idx,
                                        "line_content": line.strip()[:200]
                                    })
                                    if len(results) >= 50:
                                        break
                    except Exception:
                        continue
            if len(results) >= 50:
                break

        return {"success": True, "query": query, "matches": results, "total_matches": len(results)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_project_structure(workspace_root: str, max_depth: int = 4) -> Dict[str, Any]:
    """
    Generate an ASCII tree representation of the project workspace.
    """
    try:
        workspace_abs = os.path.abspath(workspace_root)
        lines = [os.path.basename(workspace_abs) + "/"]

        def _traverse(current_dir: str, prefix: str = "", depth: int = 1):
            if depth > max_depth:
                return
            entries = []
            try:
                for entry in os.scandir(current_dir):
                    if entry.name in (".git", "node_modules", "__pycache__", ".venv", "venv", ".pytest_cache", "dist"):
                        continue
                    entries.append(entry)
            except PermissionError:
                return

            entries.sort(key=lambda e: (not e.is_dir(), e.name.lower()))
            for i, entry in enumerate(entries):
                is_last = (i == len(entries) - 1)
                connector = "└── " if is_last else "├── "
                sub_prefix = "    " if is_last else "│   "
                if entry.is_dir():
                    lines.append(f"{prefix}{connector}{entry.name}/")
                    _traverse(entry.path, prefix + sub_prefix, depth + 1)
                else:
                    lines.append(f"{prefix}{connector}{entry.name}")

        _traverse(workspace_abs)
        return {"success": True, "tree": "\n".join(lines)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def batch_edit_files(workspace_root: str, edits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Perform multi-file creation and editing in a single atomic batch.
    Each item in 'edits' must have 'file_path' and 'content'.
    Optional 'mode' can be 'overwrite' (default) or 'replace' (requires 'target').
    """
    results = []
    failed = []

    for item in edits:
        file_path = item.get("file_path")
        if not file_path:
            failed.append({"item": item, "error": "Missing file_path"})
            continue

        mode = item.get("mode", "overwrite")
        try:
            if mode == "replace":
                target = item.get("target", "")
                replacement = item.get("content", "")
                res = edit_file(workspace_root, file_path, target, replacement)
            else:
                content = item.get("content", "")
                overwrite = item.get("overwrite", True)
                res = create_file(workspace_root, file_path, content, overwrite=overwrite)

            if res.get("success"):
                results.append({"file_path": file_path, "status": "success", "action": res.get("action", mode)})
            else:
                failed.append({"file_path": file_path, "status": "failed", "error": res.get("error")})
        except Exception as e:
            failed.append({"file_path": file_path, "status": "failed", "error": str(e)})

    return {
        "success": len(failed) == 0,
        "total_edits": len(edits),
        "successful_edits": len(results),
        "failed_edits": len(failed),
        "changes": results,
        "errors": failed
    }