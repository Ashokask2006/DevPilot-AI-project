import os
import json
import zipfile
import io
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.models import Project, Conversation, Message, AgentTask, FileChange, ToolExecution
from app.schemas.schemas import (
    ProjectCreate, ProjectResponse,
    ConversationCreate, ConversationResponse,
    PromptRequest
)
from app.core.config import settings
from app.tools import filesystem, terminal
from app.tools.registry import tool_registry
from app.agent.engine import AgentEngine

api_router = APIRouter()


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_isolated_project_workspace(project: Project, db: Session) -> str:
    workspaces_root = os.path.realpath(settings.WORKSPACES_ROOT)
    workspace_path = os.path.realpath(project.workspace_path)
    try:
        contained = os.path.commonpath([workspaces_root, workspace_path]) == workspaces_root
    except ValueError:
        contained = False

    if not contained or workspace_path == workspaces_root:
        raise HTTPException(
            status_code=400,
            detail="Project workspace is outside the configured workspace root",
        )
    if not os.path.isdir(workspace_path):
        raise HTTPException(status_code=404, detail="Project workspace not found")

    other_workspaces = (
        db.query(Project.workspace_path)
        .filter(Project.id != project.id)
        .all()
    )
    if any(os.path.realpath(row[0]) == workspace_path for row in other_workspaces):
        raise HTTPException(
            status_code=409,
            detail="Project workspace is shared with another project",
        )
    return workspace_path


def _serialize_tool_execution(execution: ToolExecution) -> dict:
    status = execution.execution_status or "running"
    payload = {}
    if execution.execution_output:
        try:
            decoded = json.loads(execution.execution_output)
            payload = decoded if isinstance(decoded, dict) else {"output": decoded}
        except (TypeError, json.JSONDecodeError):
            payload = {"output": execution.execution_output}

    return {
        "id": execution.id,
        "tool_name": execution.tool_name,
        "tool_input": payload.get("input", {}),
        "tool_output": payload.get("output", {}),
        "execution_status": status,
        "success": status == "success",
    }


def _mark_task_failed(db: Session, task_id: int) -> None:
    db.rollback()
    task = db.get(AgentTask, task_id)
    if task:
        task.task_status = "failed"
        task.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()


# ----------------- Projects API -----------------

@api_router.get("/projects", response_model=List[ProjectResponse])
def get_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.updated_at.desc()).all()


@api_router.post("/projects", response_model=ProjectResponse)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    # Sanitize project folder name
    clean_name = "".join(c for c in data.project_name if c.isalnum() or c in ("-", "_")).strip()
    if not clean_name:
        clean_name = "devpilot_project"

    workspace_dir = os.path.abspath(
        os.path.join(settings.WORKSPACES_ROOT, f"{clean_name}-{uuid4().hex[:8]}")
    )
    os.makedirs(workspace_dir, exist_ok=True)

    # Scaffolding template files based on project_type
    if data.project_type == "python":
        main_py = os.path.join(workspace_dir, "main.py")
        if not os.path.exists(main_py):
            with open(main_py, "w", encoding="utf-8") as f:
                f.write('def main():\n    print("Hello from DevPilot AI!")\n\nif __name__ == "__main__":\n    main()\n')
        reqs = os.path.join(workspace_dir, "requirements.txt")
        if not os.path.exists(reqs):
            with open(reqs, "w", encoding="utf-8") as f:
                f.write("pytest>=8.0.0\n")

    elif data.project_type == "streamlit":
        app_py = os.path.join(workspace_dir, "app.py")
        if not os.path.exists(app_py):
            with open(app_py, "w", encoding="utf-8") as f:
                f.write('import streamlit as st\n\nst.set_page_config(page_title="DevPilot App")\nst.title("🚀 DevPilot AI Streamlit App")\nst.write("Built with Google Gemini!")\n')
        reqs = os.path.join(workspace_dir, "requirements.txt")
        if not os.path.exists(reqs):
            with open(reqs, "w", encoding="utf-8") as f:
                f.write("streamlit>=1.30.0\n")

    elif data.project_type == "fastapi":
        main_py = os.path.join(workspace_dir, "main.py")
        if not os.path.exists(main_py):
            with open(main_py, "w", encoding="utf-8") as f:
                f.write('from fastapi import FastAPI\n\napp = FastAPI(title="DevPilot API")\n\n@app.get("/")\ndef root():\n    return {"message": "Hello from FastAPI"}\n')

    readme = os.path.join(workspace_dir, "README.md")
    if not os.path.exists(readme):
        with open(readme, "w", encoding="utf-8") as f:
            f.write(f"# {data.project_name}\n\nGenerated by DevPilot AI.\n")

    new_proj = Project(
        project_name=data.project_name,
        project_type=data.project_type,
        workspace_path=workspace_dir
    )
    db.add(new_proj)
    db.commit()
    db.refresh(new_proj)
    return new_proj


@api_router.get("/projects/{project_id}/files")
def get_project_files(project_id: int, subpath: str = ".", db: Session = Depends(get_db)):
    project = _get_project_or_404(project_id, db)
    workspace_path = _get_isolated_project_workspace(project, db)
    return filesystem.list_files(workspace_path, subpath)


@api_router.get("/projects/{project_id}/file")
def read_project_file(project_id: int, file_path: str, db: Session = Depends(get_db)):
    project = _get_project_or_404(project_id, db)
    workspace_path = _get_isolated_project_workspace(project, db)
    res = filesystem.read_file(workspace_path, file_path)
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to read file"))
    return res


@api_router.post("/projects/{project_id}/file")
def save_project_file(project_id: int, payload: dict, db: Session = Depends(get_db)):
    project = _get_project_or_404(project_id, db)
    workspace_path = _get_isolated_project_workspace(project, db)
    file_path = payload.get("file_path")
    content = payload.get("content", "")
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")

    res = filesystem.create_file(workspace_path, file_path, content, overwrite=True)
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res.get("error"))

    # Record file change in database
    fc = FileChange(project_id=project_id, file_path=file_path, change_type="modified")
    db.add(fc)
    db.commit()
    return res


@api_router.post("/projects/{project_id}/terminal")
def execute_terminal(project_id: int, payload: dict, db: Session = Depends(get_db)):
    project = _get_project_or_404(project_id, db)
    workspace_path = _get_isolated_project_workspace(project, db)
    command = payload.get("command", "")
    if command == "run_tests":
        return terminal.run_tests(workspace_path)
    return terminal.run_command(workspace_path, command)


@api_router.get("/projects/{project_id}/download")
def download_project_zip(project_id: int, db: Session = Depends(get_db)):
    project = _get_project_or_404(project_id, db)
    workspace_root = _get_isolated_project_workspace(project, db)
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(workspace_root):
            dirs[:] = [
                d for d in dirs
                if d not in (".git", "__pycache__", "venv", ".venv", "node_modules")
                and filesystem.is_within_workspace(workspace_root, os.path.join(root, d))
            ]
            for file in files:
                full_path = os.path.join(root, file)
                if not filesystem.is_within_workspace(workspace_root, full_path):
                    continue
                arcname = os.path.relpath(full_path, workspace_root)
                zf.write(full_path, arcname)

    mem_zip.seek(0)
    filename = f"{project.project_name}.zip"
    return StreamingResponse(
        mem_zip,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ----------------- Conversations API -----------------

@api_router.get("/conversations", response_model=List[ConversationResponse])
def get_conversations(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Conversation)
    if project_id is not None:
        _get_project_or_404(project_id, db)
        query = query.filter(Conversation.project_id == project_id)
    return query.order_by(Conversation.created_at.desc()).all()


@api_router.post("/conversations", response_model=ConversationResponse)
def create_conversation(data: ConversationCreate, db: Session = Depends(get_db)):
    if data.project_id is not None:
        _get_project_or_404(data.project_id, db)
    conv = Conversation(title=data.title or "New Chat", project_id=data.project_id)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


# ----------------- AI Agent Prompt API -----------------

@api_router.post("/agent/prompt")
async def execute_agent_prompt(data: PromptRequest, db: Session = Depends(get_db)):
    """
    Executes the DevPilot AI Autonomous Agent Loop using Gemini function calling:
    1. Understands user prompt
    2. Calls Gemini with all registered tools
    3. Executes tool calls in sandboxed workspace
    4. Loops until task is complete or max_iterations reached
    5. Returns reply, tool_calls_log, logs, and files_changed
    """
    if data.project_id is None:
        raise HTTPException(status_code=400, detail="project_id is required for agent file access")

    project = _get_project_or_404(data.project_id, db)
    workspace_path = _get_isolated_project_workspace(project, db)

    if data.conversation_id is not None:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == data.conversation_id)
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation.project_id != project.id:
            raise HTTPException(
                status_code=400,
                detail="Conversation does not belong to the requested project",
            )

    # Save user message to database if conversation exists
    if data.conversation_id is not None:
        user_msg = Message(conversation_id=data.conversation_id, role="user", content=data.prompt)
        db.add(user_msg)

    # Create Agent Task Record
    task = AgentTask(
        project_id=data.project_id,
        task_description=data.prompt,
        task_status="running"
    )
    db.add(task)
    try:
        db.commit()
        db.refresh(task)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create agent task") from exc

    try:
        # Run the advanced agentic loop
        engine = AgentEngine(
            workspace_root=workspace_path,
            tool_registry=tool_registry,
            db=db,
            model=data.model,
        )

        result = await engine.run(
            prompt=data.prompt,
            conversation_id=data.conversation_id,
            project_id=data.project_id,
            task_id=task.id,
        )

        reply = result["reply"]
        tool_calls_log = result["tool_calls_log"]
        logs = result["logs"]
        files_changed = result["files_changed"]

        if not result.get("success", False):
            _mark_task_failed(db, task.id)
            raise HTTPException(
                status_code=502,
                detail={
                    "message": result.get("error") or "Agent execution failed",
                    "task_id": task.id,
                },
            )

        task.task_status = "completed"
        task.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()

        # Save assistant message to database
        if data.conversation_id is not None:
            assistant_msg = Message(
                conversation_id=data.conversation_id,
                role="assistant",
                content=reply
            )
            db.add(assistant_msg)
            db.commit()

        return {
            "success": True,
            "reply": reply,
            "tool_calls": tool_calls_log,
            "logs": logs,
            "files_changed": files_changed,
            "task_id": task.id,
        }

    except HTTPException:
        raise
    except Exception as exc:
        _mark_task_failed(db, task.id)
        raise HTTPException(
            status_code=500,
            detail={"message": "Agent execution failed", "task_id": task.id},
        ) from exc


# ----------------- Batch Edit API -----------------

@api_router.post("/projects/{project_id}/batch-edit")
def batch_edit_project_files(project_id: int, payload: dict, db: Session = Depends(get_db)):
    """
    Apply multiple file creates/edits atomically in one request.
    Body: { "edits": [ { "file_path": str, "content": str, "mode": "overwrite"|"replace", "target": str }, ... ] }
    """
    project = _get_project_or_404(project_id, db)
    workspace_path = _get_isolated_project_workspace(project, db)

    edits = payload.get("edits", [])
    if not edits:
        raise HTTPException(status_code=400, detail="No edits provided")

    result = filesystem.batch_edit_files(workspace_path, edits)
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result)
    return result


# ----------------- Tasks API -----------------

@api_router.get("/projects/{project_id}/tasks")
def get_project_tasks(project_id: int, db: Session = Depends(get_db)):
    """List all agent tasks for a project, with their tool executions."""
    _get_project_or_404(project_id, db)

    tasks = (
        db.query(AgentTask)
        .filter(AgentTask.project_id == project_id)
        .order_by(AgentTask.created_at.desc())
        .all()
    )

    result = []
    for t in tasks:
        executions = (
            db.query(ToolExecution)
            .filter(ToolExecution.task_id == t.id)
            .order_by(ToolExecution.id)
            .all()
        )
        result.append({
            "id": t.id,
            "project_id": t.project_id,
            "task_description": t.task_description,
            "task_status": t.task_status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "tool_executions": [
                _serialize_tool_execution(ex)
                for ex in executions
            ],
        })
    return result


@api_router.get("/tasks/{task_id}")
def get_task_detail(task_id: int, db: Session = Depends(get_db)):
    """Get a single agent task with full tool execution log."""
    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    executions = (
        db.query(ToolExecution)
        .filter(ToolExecution.task_id == task_id)
        .order_by(ToolExecution.id)
        .all()
    )

    return {
        "id": task.id,
        "project_id": task.project_id,
        "task_description": task.task_description,
        "task_status": task.task_status,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "tool_executions": [
            _serialize_tool_execution(ex)
            for ex in executions
        ],
    }
