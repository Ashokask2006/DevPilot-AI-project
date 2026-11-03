"""
Secure Filesystem Tools for DevPilot AI.
Provides file and directory operations with strict workspace sandbox containment
and path traversal prevention.
"""

import os
import fnmatch
import stat
import tempfile
from typing import Dict, Any, List, Optional


def _is_within_workspace(workspace_abs: str, target_abs: str) -> bool:
    try:
        return os.path.commonpath([workspace_abs, target_abs]) == workspace_abs
    except ValueError:
        return False


def is_within_workspace(workspace_root: str, path: str) -> bool:
    """Return whether a path resolves inside the workspace root."""
    workspace_abs = os.path.realpath(workspace_root)
    target_abs = os.path.realpath(path)
    return os.path.isdir(workspace_abs) and _is_within_workspace(workspace_abs, target_abs)


def _resolve_safe_path(workspace_root: str, relative_or_abs_path: str) -> str:
    """
    Ensure the resolved path strictly resides within the workspace root.
    Raises PermissionError if a path traversal attempt is detected.
    """
    workspace_abs = os.path.realpath(workspace_root)
    if not os.path.isdir(workspace_abs):
        raise FileNotFoundError(f"Workspace directory not found: {workspace_root}")

    # If path is given relative to workspace
    if os.path.isabs(relative_or_abs_path):
        target_abs = os.path.realpath(relative_or_abs_path)
    else:
        target_abs = os.path.realpath(os.path.join(workspace_abs, relative_or_abs_path))

    # Resolve symlinks before containment checks so an in-workspace symlink
    # cannot be used to reach a file outside the workspace.
    if not _is_within_workspace(workspace_abs, target_abs):
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
            if not is_within_workspace(workspace_root, entry.path):
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
        existed = os.path.exists(target_file)
        if existed and not overwrite:
            return {"success": False, "error": f"File already exists: {file_path}. Set overwrite=True to replace."}

        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        target_file = _resolve_safe_path(workspace_root, target_file)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "success": True,
            "path": os.path.relpath(target_file, workspace_root).replace("\\", "/"),
            "bytes_written": len(content.encode("utf-8")),
            "action": "overwritten" if existed else "created"
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
        workspace_abs = os.path.realpath(workspace_root)
        for root, dirs, files in os.walk(workspace_abs):
            dirs[:] = [
                d for d in dirs
                if d not in (".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build")
                and is_within_workspace(workspace_abs, os.path.join(root, d))
            ]
            for file in files:
                if fnmatch.fnmatch(file, pattern):
                    file_full = os.path.join(root, file)
                    if not is_within_workspace(workspace_abs, file_full):
                        continue
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
        workspace_abs = os.path.realpath(workspace_root)
        lines = [os.path.basename(workspace_abs) + "/"]

        def _traverse(current_dir: str, prefix: str = "", depth: int = 1):
            if depth > max_depth:
                return
            entries = []
            try:
                for entry in os.scandir(current_dir):
                    if entry.name in (".git", "node_modules", "__pycache__", ".venv", "venv", ".pytest_cache", "dist"):
                        continue
                    if not is_within_workspace(workspace_abs, entry.path):
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


def _write_bytes_atomically(target_file: str, content: bytes, mode: int | None) -> None:
    """Replace one file without exposing a partially written result."""
    parent = os.path.dirname(target_file)
    descriptor, temp_path = tempfile.mkstemp(prefix=".devpilot-", dir=parent)
    try:
        with os.fdopen(descriptor, "wb") as temp_file:
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.chmod(temp_path, mode if mode is not None else 0o644)
        os.replace(temp_path, target_file)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def batch_edit_files(workspace_root: str, edits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply a validated batch and roll back every applied file if one write fails."""
    if not isinstance(edits, list) or not edits:
        return {
            "success": False,
            "total_edits": len(edits) if isinstance(edits, list) else 0,
            "successful_edits": 0,
            "failed_edits": 1,
            "changes": [],
            "errors": [{"error": "edits must be a non-empty list"}],
            "rolled_back": False,
        }

    workspace_abs = os.path.realpath(workspace_root)
    if not os.path.isdir(workspace_abs):
        return {
            "success": False,
            "total_edits": len(edits),
            "successful_edits": 0,
            "failed_edits": len(edits),
            "changes": [],
            "errors": [{"error": f"Workspace directory not found: {workspace_root}"}],
            "rolled_back": False,
        }

    plans = []
    validation_errors = []
    seen_targets = set()

    for index, item in enumerate(edits):
        if not isinstance(item, dict):
            validation_errors.append({"index": index, "error": "Each edit must be an object"})
            continue

        file_path = item.get("file_path")
        content = item.get("content")
        mode = item.get("mode", "overwrite")

        if not isinstance(file_path, str) or not file_path.strip():
            validation_errors.append({"index": index, "error": "file_path must be a non-empty string"})
            continue
        if not isinstance(content, str):
            validation_errors.append({"index": index, "file_path": file_path, "error": "content must be a string"})
            continue
        if mode not in {"overwrite", "replace"}:
            validation_errors.append({"index": index, "file_path": file_path, "error": "mode must be 'overwrite' or 'replace'"})
            continue

        try:
            target_file = _resolve_safe_path(workspace_abs, file_path)
            if target_file in seen_targets:
                raise ValueError("Duplicate file_path entries are not allowed")
            seen_targets.add(target_file)

            existed = os.path.exists(target_file)
            if existed and not os.path.isfile(target_file):
                raise ValueError("Target path is not a regular file")

            if existed:
                with open(target_file, "rb") as existing_file:
                    original_bytes = existing_file.read()
            else:
                original_bytes = None
            original_mode = stat.S_IMODE(os.stat(target_file).st_mode) if existed else None

            if mode == "replace":
                target = item.get("target")
                if not isinstance(target, str) or not target:
                    raise ValueError("replace mode requires a non-empty target")
                if not existed:
                    raise ValueError("replace mode requires an existing file")
                try:
                    original_text = original_bytes.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise ValueError("replace mode requires a UTF-8 text file") from exc
                if target not in original_text:
                    raise ValueError("Target snippet was not found")
                new_content = original_text.replace(target, content, 1)
                action = "replaced"
            else:
                overwrite = item.get("overwrite", True)
                if not isinstance(overwrite, bool):
                    raise ValueError("overwrite must be a boolean")
                if existed and not overwrite:
                    raise ValueError("File already exists and overwrite is false")
                new_content = content
                action = "overwritten" if existed else "created"

            plans.append(
                {
                    "file_path": file_path,
                    "target_file": target_file,
                    "content": new_content.encode("utf-8"),
                    "existed": existed,
                    "original_bytes": original_bytes,
                    "original_mode": original_mode,
                    "action": action,
                }
            )
        except Exception as exc:
            validation_errors.append({"index": index, "file_path": file_path, "error": str(exc)})

    if validation_errors:
        return {
            "success": False,
            "total_edits": len(edits),
            "successful_edits": 0,
            "failed_edits": len(validation_errors),
            "changes": [],
            "errors": validation_errors,
            "rolled_back": False,
        }

    applied = []
    created_directories = []
    try:
        for plan in plans:
            parent = os.path.dirname(plan["target_file"])
            missing_directories = []
            cursor = parent
            while cursor != workspace_abs and not os.path.exists(cursor):
                missing_directories.append(cursor)
                next_cursor = os.path.dirname(cursor)
                if next_cursor == cursor:
                    raise PermissionError("Unable to create a directory outside the workspace")
                cursor = next_cursor

            if not _is_within_workspace(workspace_abs, parent):
                raise PermissionError("Target parent is outside workspace boundaries")

            os.makedirs(parent, exist_ok=True)
            created_directories.extend(missing_directories)

            resolved_again = _resolve_safe_path(workspace_abs, plan["file_path"])
            if resolved_again != plan["target_file"]:
                raise PermissionError("Target path changed during batch validation")

            exists_now = os.path.exists(plan["target_file"])
            if exists_now != plan["existed"]:
                raise RuntimeError("Target file changed during batch validation")
            if plan["existed"]:
                with open(plan["target_file"], "rb") as current_file:
                    current_bytes = current_file.read()
                if current_bytes != plan["original_bytes"]:
                    raise RuntimeError("Target file contents changed during batch validation")

            _write_bytes_atomically(
                plan["target_file"],
                plan["content"],
                plan["original_mode"],
            )
            applied.append(plan)
    except Exception as exc:
        rollback_errors = []
        for plan in reversed(applied):
            try:
                resolved_again = _resolve_safe_path(workspace_abs, plan["file_path"])
                if resolved_again != plan["target_file"]:
                    raise PermissionError("Target path changed before rollback")
                if plan["existed"]:
                    _write_bytes_atomically(
                        plan["target_file"],
                        plan["original_bytes"],
                        plan["original_mode"],
                    )
                elif os.path.lexists(plan["target_file"]):
                    os.remove(plan["target_file"])
            except Exception as rollback_exc:
                rollback_errors.append(
                    {"file_path": plan["file_path"], "error": str(rollback_exc)}
                )

        for directory in sorted(set(created_directories), key=len, reverse=True):
            try:
                if _is_within_workspace(workspace_abs, directory):
                    os.rmdir(directory)
            except OSError:
                pass

        errors = [{"error": f"Batch write failed: {exc}"}]
        errors.extend(rollback_errors)
        return {
            "success": False,
            "total_edits": len(edits),
            "successful_edits": 0,
            "failed_edits": len(edits),
            "changes": [],
            "errors": errors,
            "rolled_back": len(rollback_errors) == 0,
        }

    changes = [
        {
            "file_path": plan["file_path"],
            "status": "success",
            "action": plan["action"],
        }
        for plan in plans
    ]
    return {
        "success": True,
        "total_edits": len(edits),
        "successful_edits": len(changes),
        "failed_edits": 0,
        "changes": changes,
        "errors": [],
        "rolled_back": False,
    }
