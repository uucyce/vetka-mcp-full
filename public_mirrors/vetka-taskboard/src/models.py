"""
Pydantic models for Agent Gateway API.

Shared request/response schemas used by gateway_routes.py and gateway_admin_routes.py.
Provides OpenAPI schema generation and request validation.

@phase 196.7
@task tb_1774957713_28508_1
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Agent Registration
# ---------------------------------------------------------------------------


class AgentRegisterRequest(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=128, description="Agent display name"
    )
    provider: str = Field(
        "", max_length=64, description="Provider: gemini, claude, gpt, local"
    )
    agent_type: str = Field("external", description="Agent type identifier")
    capabilities: List[str] = Field(
        default_factory=lambda: ["read", "claim", "submit"],
        description="Capabilities: read, claim, submit, create, search",
    )


class AgentRegisterResponse(BaseModel):
    success: bool
    agent_id: str
    api_key: str
    message: str = "Store this key securely — it won't be shown again."


class AgentInfo(BaseModel):
    agent_id: str
    name: str
    agent_type: str
    provider: str = ""
    capabilities: List[str] = Field(default_factory=list)
    status: str = "active"
    registered_at: str
    last_seen: str = ""
    max_concurrent: int = 3


# ---------------------------------------------------------------------------
# Task Models
# ---------------------------------------------------------------------------


class TaskSummary(BaseModel):
    id: str
    title: str
    description: str = ""
    priority: int = 3
    phase_type: str = "build"
    complexity: str = "medium"
    project_id: str = ""
    tags: List[str] = Field(default_factory=list)
    status: str = "pending"
    created_at: str = ""
    assigned_to: str = ""


class TaskDetail(BaseModel):
    id: str
    title: str
    status: str
    assigned_to: str = ""
    priority: int = 3
    phase_type: str = "build"
    created_at: str = ""
    completed_at: str = ""
    commit_hash: str = ""
    commit_message: str = ""
    description: str = ""


class TasksListResponse(BaseModel):
    success: bool = True
    tasks: List[TaskSummary] = Field(default_factory=list)
    count: int = 0
    agent_id: str = ""


class MyTasksResponse(BaseModel):
    success: bool = True
    agent_id: str = ""
    tasks: List[TaskSummary] = Field(default_factory=list)
    count: int = 0


# ---------------------------------------------------------------------------
# Claim / Submit
# ---------------------------------------------------------------------------


class TaskClaimRequest(BaseModel):
    pass


class TaskSubmitRequest(BaseModel):
    commit_hash: str = Field(
        ..., min_length=7, max_length=64, description="Git commit SHA"
    )
    commit_message: str = Field("", max_length=2048)
    branch: str = Field("", max_length=256, description="Agent's work branch")
    pr_url: str = Field("", max_length=512, description="GitHub PR URL (optional)")
    summary: str = Field("", max_length=4096, description="Description of changes")


class TaskClaimResponse(BaseModel):
    success: bool
    task_id: str
    agent_id: str
    status: str = "claimed"
    message: str


class TaskSubmitResponse(BaseModel):
    success: bool
    task_id: str
    agent_id: str
    status: str
    commit_hash: str
    pr_url: str = ""
    summary: str = ""
    message: str = ""


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "agent-gateway"
    active_agents: int = 0


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


class AdminAgentListResponse(BaseModel):
    success: bool = True
    agents: List[AgentInfo] = Field(default_factory=list)
    count: int = 0


class AdminActionResponse(BaseModel):
    success: bool
    agent_id: str
    action: str
    message: str = ""


class AuditLogEntry(BaseModel):
    id: int
    agent_id: str
    action: str
    task_id: str = ""
    ip_address: str = ""
    response_status: int = 0
    created_at: str = ""


class AuditLogResponse(BaseModel):
    success: bool = True
    entries: List[AuditLogEntry] = Field(default_factory=list)
    count: int = 0
    offset: int = 0
    limit: int = 50


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    success: bool = False
    detail: str
    status_code: int = 400
