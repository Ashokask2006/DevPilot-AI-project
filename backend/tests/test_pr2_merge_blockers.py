import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent import engine as engine_module
from app.agent.engine import AgentEngine
from app.api import router as router_module
from app.database.session import Base
from app.models.models import AgentTask, Conversation, Project, ToolExecution
from app.schemas.schemas import ConversationCreate, ProjectCreate, PromptRequest
from app.tools import filesystem, git_tools
from app.tools.registry import ToolRegistry


@pytest.fixture
def db_session():
    database_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(database_engine)
    session = sessionmaker(bind=database_engine)()
    try:
        yield session
    finally:
        session.close()
        database_engine.dispose()


def _create_project(db_session, workspace: Path, name: str = "project") -> Project:
    project = Project(
        project_name=name,
        project_type="python",
        workspace_path=str(workspace),
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def test_tool_execution_history_uses_existing_database_model(
    db_session,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspaces" / "project"
    workspace.mkdir(parents=True)
    project = _create_project(db_session, workspace)
    task = AgentTask(
        project_id=project.id,
        task_description="Read a file",
        task_status="running",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    agent = object.__new__(AgentEngine)
    agent.db = db_session
    agent._persist_tool_execution(
        task_id=task.id,
        tool_name="read_file",
        tool_input={"file_path": "example.py"},
        tool_output={"success": True, "content": "print('ok')"},
    )

    execution = db_session.query(ToolExecution).one()
    payload = json.loads(execution.execution_output)
    assert execution.execution_status == "success"
    assert payload["input"] == {"file_path": "example.py"}
    assert payload["output"]["success"] is True

    task_detail = router_module.get_task_detail(task.id, db_session)
    assert task_detail["tool_executions"] == [
        {
            "id": execution.id,
            "tool_name": "read_file",
            "tool_input": {"file_path": "example.py"},
            "tool_output": {"success": True, "content": "print('ok')"},
            "execution_status": "success",
            "success": True,
        }
    ]


@pytest.mark.asyncio
async def test_agent_endpoint_requires_an_existing_isolated_project(
    db_session,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "workspaces"
    root.mkdir()
    monkeypatch.setattr(router_module.settings, "WORKSPACES_ROOT", str(root))

    with pytest.raises(ValidationError):
        PromptRequest(prompt="hello")

    with pytest.raises(HTTPException) as unknown:
        await router_module.execute_agent_prompt(
            PromptRequest(prompt="hello", project_id=999),
            db_session,
        )
    assert unknown.value.status_code == 404

    outside = tmp_path / "outside"
    outside.mkdir()
    outside_project = _create_project(db_session, outside, "outside")
    with pytest.raises(HTTPException) as escaped:
        await router_module.execute_agent_prompt(
            PromptRequest(prompt="hello", project_id=outside_project.id),
            db_session,
        )
    assert escaped.value.status_code == 400


@pytest.mark.asyncio
async def test_agent_endpoint_rejects_cross_project_conversation(
    db_session,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "workspaces"
    first_workspace = root / "first"
    second_workspace = root / "second"
    first_workspace.mkdir(parents=True)
    second_workspace.mkdir()
    monkeypatch.setattr(router_module.settings, "WORKSPACES_ROOT", str(root))
    first_project = _create_project(db_session, first_workspace, "first")
    second_project = _create_project(db_session, second_workspace, "second")
    conversation = Conversation(title="Second", project_id=second_project.id)
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    with pytest.raises(HTTPException) as mismatch:
        await router_module.execute_agent_prompt(
            PromptRequest(
                prompt="hello",
                project_id=first_project.id,
                conversation_id=conversation.id,
            ),
            db_session,
        )
    assert mismatch.value.status_code == 400


def test_shared_project_workspace_is_rejected(
    db_session,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "workspaces"
    shared = root / "shared"
    shared.mkdir(parents=True)
    monkeypatch.setattr(router_module.settings, "WORKSPACES_ROOT", str(root))
    first = _create_project(db_session, shared, "first")
    _create_project(db_session, shared, "second")

    with pytest.raises(HTTPException) as duplicate:
        router_module._get_isolated_project_workspace(first, db_session)
    assert duplicate.value.status_code == 409


def test_new_projects_receive_unique_workspaces(
    db_session,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "workspaces"
    monkeypatch.setattr(router_module.settings, "WORKSPACES_ROOT", str(root))

    first = router_module.create_project(
        ProjectCreate(project_name="same name", project_type="python"),
        db_session,
    )
    second = router_module.create_project(
        ProjectCreate(project_name="same name", project_type="python"),
        db_session,
    )

    assert first.workspace_path != second.workspace_path
    assert Path(first.workspace_path).parent == root
    assert Path(second.workspace_path).parent == root


def test_conversation_routes_reject_unknown_project_ids(db_session) -> None:
    with pytest.raises(HTTPException) as listing:
        router_module.get_conversations(project_id=999, db=db_session)
    assert listing.value.status_code == 404

    with pytest.raises(HTTPException) as creation:
        router_module.create_conversation(
            ConversationCreate(title="orphan", project_id=999),
            db_session,
        )
    assert creation.value.status_code == 404


def test_git_tools_cannot_execute_or_inject_options(tmp_path: Path) -> None:
    output_path = tmp_path / "must-not-exist"
    option = f"--output={output_path}"

    direct_result = git_tools.git_diff(str(tmp_path), option)
    registry_result = ToolRegistry().execute_tool(
        "git_diff",
        str(tmp_path),
        {"file_path": option},
    )

    assert direct_result["success"] is False
    assert direct_result["execution_enabled"] is False
    assert registry_result["success"] is False
    assert registry_result["execution_enabled"] is False
    assert output_path.exists() is False


def test_batch_edit_prevalidation_prevents_partial_writes(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    existing = workspace / "existing.txt"
    existing.write_text("original", encoding="utf-8")

    result = filesystem.batch_edit_files(
        str(workspace),
        [
            {"file_path": "created.txt", "content": "created"},
            {
                "file_path": "existing.txt",
                "mode": "replace",
                "target": "",
                "content": "unsafe",
            },
        ],
    )

    assert result["success"] is False
    assert result["successful_edits"] == 0
    assert (workspace / "created.txt").exists() is False
    assert existing.read_text(encoding="utf-8") == "original"


def test_batch_edit_rolls_back_after_a_runtime_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    first = workspace / "first.txt"
    first.write_text("before", encoding="utf-8")
    original_writer = filesystem._write_bytes_atomically
    calls = 0

    def fail_second_write(target_file: str, content: bytes, mode: int | None) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated write failure")
        original_writer(target_file, content, mode)

    monkeypatch.setattr(filesystem, "_write_bytes_atomically", fail_second_write)

    result = filesystem.batch_edit_files(
        str(workspace),
        [
            {"file_path": "first.txt", "content": "after"},
            {"file_path": "second.txt", "content": "new"},
        ],
    )

    assert result["success"] is False
    assert result["rolled_back"] is True
    assert first.read_text(encoding="utf-8") == "before"
    assert (workspace / "second.txt").exists() is False


def test_batch_edit_rejects_symlink_escape(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    protected = outside / "protected.txt"
    protected.write_text("unchanged", encoding="utf-8")
    (workspace / "escape").symlink_to(outside, target_is_directory=True)

    result = filesystem.batch_edit_files(
        str(workspace),
        [{"file_path": "escape/protected.txt", "content": "changed"}],
    )

    assert result["success"] is False
    assert result["successful_edits"] == 0
    assert protected.read_text(encoding="utf-8") == "unchanged"


@pytest.mark.asyncio
async def test_agent_endpoint_marks_agent_failures_and_respects_model(
    db_session,
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "workspaces"
    workspace = root / "project"
    workspace.mkdir(parents=True)
    monkeypatch.setattr(router_module.settings, "WORKSPACES_ROOT", str(root))
    project = _create_project(db_session, workspace)

    class FailingAgent:
        requested_model = None

        def __init__(self, workspace_root, tool_registry, db, model=None):
            self.__class__.requested_model = model

        async def run(self, **kwargs):
            return {
                "success": False,
                "error": "Provider unavailable",
                "reply": "Provider unavailable",
                "tool_calls_log": [],
                "logs": ["provider unavailable"],
                "files_changed": [],
            }

    monkeypatch.setattr(router_module, "AgentEngine", FailingAgent)

    with pytest.raises(HTTPException) as failure:
        await router_module.execute_agent_prompt(
            PromptRequest(
                prompt="hello",
                project_id=project.id,
                model="requested-model",
            ),
            db_session,
        )

    assert failure.value.status_code == 502
    assert FailingAgent.requested_model == "requested-model"
    task = db_session.query(AgentTask).one()
    assert task.task_status == "failed"
    assert task.completed_at is not None


@pytest.mark.asyncio
async def test_agent_loop_uses_async_client_and_reports_success(
    tmp_path: Path,
    monkeypatch,
) -> None:
    class FakeChat:
        def __init__(self):
            self.calls = 0

        async def send_message(self, message):
            self.calls += 1
            if self.calls == 1:
                function_call = SimpleNamespace(
                    name="create_file",
                    args={"file_path": "created.txt", "content": "safe"},
                )
                return SimpleNamespace(function_calls=[function_call])
            return SimpleNamespace(function_calls=[], text="complete")

    class FakeAsyncChats:
        def __init__(self, chat):
            self.chat = chat

        def create(self, model, config):
            return self.chat

    chat = FakeChat()
    fake_client = SimpleNamespace(
        aio=SimpleNamespace(chats=FakeAsyncChats(chat)),
    )
    monkeypatch.setattr(
        engine_module.genai,
        "Client",
        lambda api_key: fake_client,
    )

    agent = AgentEngine(
        workspace_root=str(tmp_path),
        tool_registry=ToolRegistry(),
        model="requested-model",
    )
    result = await agent.run("create a file", max_iterations=3)

    assert agent.model == "requested-model"
    assert result["success"] is True
    assert result["error"] is None
    assert result["reply"] == "complete"
    assert result["files_changed"] == ["created.txt"]
    assert (tmp_path / "created.txt").read_text(encoding="utf-8") == "safe"


@pytest.mark.asyncio
async def test_agent_loop_reports_async_provider_failure(monkeypatch) -> None:
    class FailingAsyncChats:
        def create(self, model, config):
            raise RuntimeError("provider unavailable")

    fake_client = SimpleNamespace(
        aio=SimpleNamespace(chats=FailingAsyncChats()),
    )
    monkeypatch.setattr(
        engine_module.genai,
        "Client",
        lambda api_key: fake_client,
    )

    agent = AgentEngine(
        workspace_root=".",
        tool_registry=ToolRegistry(),
    )
    result = await agent.run("hello")

    assert result["success"] is False
    assert result["error"] == "Failed to initialise the AI session."
    assert result["reply"] == result["error"]


def test_execution_tool_descriptions_match_disabled_state() -> None:
    registry = ToolRegistry()
    definitions = {
        definition["name"]: definition
        for definition in registry.get_tool_definitions()
    }

    for name in ("run_command", "run_tests", "git_status", "git_diff"):
        assert "Unavailable" in definitions[name]["description"]

    agent = object.__new__(AgentEngine)
    agent.workspace_root = "/workspace/project"
    instruction = agent._build_system_instruction()
    assert "execution tools are disabled" in instruction
    assert "Use run_command" not in instruction
