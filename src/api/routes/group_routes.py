# === PHASE 56: GROUP API ROUTES ===
"""
FastAPI routes for group chat management.

Provides endpoints for creating groups, adding participants, sending messages.

@status: active
@phase: 96
@depends: fastapi, group_chat_manager
@used_by: main.py router registration
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from src.services.group_chat_manager import (
    get_group_chat_manager,
    GroupParticipant,
    GroupRole
)

router = APIRouter(prefix="/api/groups", tags=["groups"])


class CreateGroupRequest(BaseModel):
    name: str
    description: str = ""
    admin_agent_id: str
    admin_model_id: str
    admin_display_name: str
    project_id: Optional[str] = None


class AddParticipantRequest(BaseModel):
    agent_id: str
    model_id: str
    display_name: str
    role: str = "worker"


class SendMessageRequest(BaseModel):
    sender_id: str
    content: str
    message_type: str = "chat"


class AssignTaskRequest(BaseModel):
    assigner_id: str
    assignee_id: str
    description: str
    dependencies: List[str] = []


# Phase 80.19: Direct model addition request
class AddModelDirectRequest(BaseModel):
    model_id: str  # e.g., "deepseek/deepseek-r1:free"
    role: str = "worker"  # Default role


@router.get("")
async def list_groups():
    """Get all groups."""
    manager = get_group_chat_manager()
    return {
        'groups': manager.get_all_groups()
    }


@router.post("")
async def create_group(body: CreateGroupRequest):
    """Create new group."""
    manager = get_group_chat_manager()

    admin = GroupParticipant(
        agent_id=body.admin_agent_id,
        model_id=body.admin_model_id,
        role=GroupRole.ADMIN,
        display_name=body.admin_display_name
    )

    group = await manager.create_group(
        name=body.name,
        admin_agent=admin,
        description=body.description,
        project_id=body.project_id
    )

    return {'group': group.to_dict()}


@router.get("/{group_id}")
async def get_group(group_id: str):
    """Get group by ID."""
    manager = get_group_chat_manager()
    group = manager.get_group(group_id)

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    return {'group': group}


# MARKER_GROUP_RENAME_API: Phase 108.5 - Rename group endpoint
class UpdateGroupRequest(BaseModel):
    name: str


@router.patch("/{group_id}")
async def update_group(group_id: str, body: UpdateGroupRequest):
    """
    Update group name.
    Phase 108.5: Enable group chat renaming.

    Args:
        group_id: Group UUID
        body: Request body with new name

    Returns:
        Success status with new name
    """
    if not body.name or not body.name.strip():
        raise HTTPException(status_code=400, detail="name is required and cannot be empty")

    manager = get_group_chat_manager()
    success = await manager.update_group_name(group_id, body.name.strip())

    if not success:
        raise HTTPException(status_code=404, detail=f"Group {group_id} not found")

    return {
        "success": True,
        "group_id": group_id,
        "name": body.name.strip()
    }


@router.post("/{group_id}/participants")
async def add_participant(group_id: str, body: AddParticipantRequest):
    """Add participant to group."""
    manager = get_group_chat_manager()

    participant = GroupParticipant(
        agent_id=body.agent_id,
        model_id=body.model_id,
        role=GroupRole(body.role),
        display_name=body.display_name
    )

    if await manager.add_participant(group_id, participant):
        return {'success': True}

    raise HTTPException(status_code=404, detail="Group not found")


@router.delete("/{group_id}/participants/{agent_id}")
async def remove_participant(group_id: str, agent_id: str):
    """Remove participant from group."""
    manager = get_group_chat_manager()

    if await manager.remove_participant(group_id, agent_id):
        return {'success': True}

    raise HTTPException(status_code=404, detail="Group or participant not found")


class UpdateParticipantModelRequest(BaseModel):
    model_id: str


class UpdateParticipantRoleRequest(BaseModel):
    role: str


@router.patch("/{group_id}/participants/{agent_id}/model")
async def update_participant_model(
    group_id: str,
    agent_id: str,
    body: UpdateParticipantModelRequest
):
    """
    Update participant's model assignment.
    Phase 82: Enable model reassignment (e.g., Deepseek fallback to GPT-4).
    """
    manager = get_group_chat_manager()

    if await manager.update_participant_model(group_id, agent_id, body.model_id):
        return {'success': True, 'model_id': body.model_id}

    raise HTTPException(
        status_code=404,
        detail="Group or participant not found, or model validation failed"
    )


@router.patch("/{group_id}/participants/{agent_id}/role")
async def update_participant_role(
    group_id: str,
    agent_id: str,
    body: UpdateParticipantRoleRequest
):
    """
    Update participant's role.
    Phase 82: Enable role changes after group creation.
    """
    manager = get_group_chat_manager()

    if await manager.update_participant_role(group_id, agent_id, body.role):
        return {'success': True, 'role': body.role}

    raise HTTPException(
        status_code=400,
        detail="Invalid role, group/participant not found, or cannot remove last admin"
    )


@router.get("/{group_id}/messages")
async def get_messages(group_id: str, limit: int = 50):
    """Get group messages."""
    manager = get_group_chat_manager()
    return {
        'messages': manager.get_messages(group_id, limit)
    }


@router.post("/{group_id}/messages")
async def send_message(group_id: str, body: SendMessageRequest):
    """Send message to group."""
    manager = get_group_chat_manager()

    message = await manager.send_message(
        group_id=group_id,
        sender_id=body.sender_id,
        content=body.content,
        message_type=body.message_type
    )

    if message:
        return {'message': message.to_dict()}

    raise HTTPException(status_code=404, detail="Group not found")


@router.post("/{group_id}/tasks")
async def assign_task(group_id: str, body: AssignTaskRequest):
    """Assign task to agent."""
    manager = get_group_chat_manager()

    task = await manager.assign_task(
        group_id=group_id,
        assigner_id=body.assigner_id,
        assignee_id=body.assignee_id,
        task_description=body.description,
        dependencies=body.dependencies
    )

    if task:
        return {'task': task}

    raise HTTPException(status_code=400, detail="Failed to assign task")


# Phase 80.19: Direct model addition to group
@router.post("/{group_id}/models/add-direct")
async def add_model_direct(group_id: str, body: AddModelDirectRequest):
    """
    Phase 80.19: Add model directly without role slot.
    Auto-generates agent_id from model name.
    Like solo chat - just pick model and add it.
    """
    manager = get_group_chat_manager()

    # Check if group exists
    group = manager.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Extract name from model_id for agent_id
    # "deepseek/deepseek-r1:free" -> "deepseek-r1"
    # "mcp/claude_code" -> "claude_code"
    # "google/gemma-2-9b-it:free" -> "gemma-2-9b-it"
    model_part = body.model_id.split('/')[-1].split(':')[0]
    agent_id = f"@{model_part}"

    # Check if agent_id already exists in group - make unique if needed
    existing_participants = group.get('participants', {})
    base_agent_id = agent_id
    counter = 1
    while agent_id in existing_participants:
        agent_id = f"{base_agent_id}-{counter}"
        counter += 1

    # Get display name - use model part as fallback
    display_name = model_part.replace('-', ' ').replace('_', ' ').title()

    # Create participant
    participant = GroupParticipant(
        agent_id=agent_id,
        model_id=body.model_id,
        role=GroupRole(body.role),
        display_name=display_name,
        permissions=["read", "write"]
    )

    # Add to group
    success = await manager.add_participant(group_id, participant)
    if success:
        return {
            'success': True,
            'participant': participant.to_dict()
        }

    raise HTTPException(status_code=400, detail="Failed to add participant")
