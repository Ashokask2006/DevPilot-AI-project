from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# AI Status & Gemini
class GeminiStatusResponse(BaseModel):
    success: bool
    configured: bool
    model: str
    latency_ms: Optional[float] = None
    reply: Optional[str] = None
    message: str
    error_code: Optional[int] = None


class AIModelInfo(BaseModel):
    id: str
    name: str
    description: str
    recommended: bool = False


# Chat & Generation
class MessageBase(BaseModel):
    role: str
    content: str


class MessageCreate(MessageBase):
    pass


class MessageResponse(MessageBase):
    id: int
    conversation_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Project Chat"
    project_id: Optional[int] = None


class ConversationResponse(BaseModel):
    id: int
    title: str
    project_id: Optional[int] = None
    created_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


class PromptRequest(BaseModel):
    prompt: str
    conversation_id: Optional[int] = None
    project_id: int = Field(..., gt=0)
    model: Optional[str] = None
    stream: bool = True


# Projects
class ProjectCreate(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=100)
    project_type: str = Field(default="python", description="Template: python, react, nextjs, streamlit, fastapi, etc.")
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    project_name: str
    project_type: str
    workspace_path: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Agent Tasks & Tool Execution
class TaskResponse(BaseModel):
    id: int
    project_id: Optional[int] = None
    task_description: str
    task_status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ToolExecutionResponse(BaseModel):
    id: int
    task_id: int
    tool_name: str
    execution_status: str
    execution_output: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
