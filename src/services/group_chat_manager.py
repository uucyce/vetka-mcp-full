# === PHASE 56: GROUP CHAT MANAGER ===
"""
Group chat management for AI agent collaboration.

@status: active
@phase: 96
@depends: asyncio, uuid, pathlib, dataclasses
@used_by: src.api.handlers.group_message_handler, src.api.routes.chat_routes,
          src.initialization.components_init

Features:
- @mentions for agent targeting
- Role-based permissions (admin, worker, reviewer, observer)
- Shared context between agents
- Task assignment via admin agents
- Smart reply with decay for conversation continuity
- Persistence to data/groups.json
"""

import asyncio
import re
import logging
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
from functools import partial
import uuid

logger = logging.getLogger(__name__)


# MARKER_94.6_ROLE_SYSTEM: Group role definitions
class GroupRole(Enum):
    ADMIN = "admin"           # Can assign tasks, manage group
    WORKER = "worker"         # Can execute tasks
    REVIEWER = "reviewer"     # Can review/approve
    OBSERVER = "observer"     # Read-only


@dataclass
class GroupParticipant:
    """Agent in a group."""
    agent_id: str              # "@architect", "@rust_dev"
    model_id: str              # "llama-405b", "deepseek-r1"
    role: GroupRole
    display_name: str
    permissions: List[str] = field(default_factory=lambda: ["read", "write"])

    def to_dict(self) -> dict:
        return {
            'agent_id': self.agent_id,
            'model_id': self.model_id,
            'role': self.role.value,
            'display_name': self.display_name,
            'permissions': self.permissions
        }


@dataclass
class GroupMessage:
    """Message in group chat."""
    id: str
    group_id: str
    sender_id: str             # "@architect" or "user"
    content: str
    mentions: List[str]        # ["@rust_dev", "@qa"]
    message_type: str          # "chat", "task", "artifact", "system"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'group_id': self.group_id,
            'sender_id': self.sender_id,
            'content': self.content,
            'mentions': self.mentions,
            'message_type': self.message_type,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class Group:
    """Group chat."""
    id: str
    name: str
    description: str = ""
    admin_id: str = ""         # Agent ID of admin
    participants: Dict[str, GroupParticipant] = field(default_factory=dict)
    messages: deque = field(default_factory=lambda: deque(maxlen=1000))  # ✅ PHASE 56.2: Bounded memory
    shared_context: Dict[str, Any] = field(default_factory=dict)
    project_id: Optional[str] = None  # Link to VETKA tree
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    # Phase 80.28: Smart reply with decay - track last responder
    last_responder_id: Optional[str] = None  # @dev, @pm, etc - who responded last
    last_responder_decay: int = 0  # Increments on each user message, resets on response

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'admin_id': self.admin_id,
            'participants': {k: v.to_dict() for k, v in self.participants.items()},
            'message_count': len(self.messages),
            'project_id': self.project_id,
            'created_at': self.created_at.isoformat(),
            # Phase 80.28: Smart reply state
            'last_responder_id': self.last_responder_id,
            'last_responder_decay': self.last_responder_decay
        }


class GroupChatManager:
    """
    Manages group chats with AI agents.

    Flow:
    1. User creates group with agents
    2. User sends message with @mentions
    3. Mentioned agents receive and respond
    4. Admin agent can assign tasks
    5. Tasks appear as nodes in VETKA tree
    """

    # ✅ PHASE 56.2: Memory management constants
    MAX_MESSAGES_PER_GROUP = 1000
    MAX_GROUPS_MEMORY = 100
    INACTIVE_GROUP_TIMEOUT = timedelta(hours=24)

    # Persistence configuration
    GROUPS_FILE = Path("data/groups.json")

    def __init__(self, socketio=None, model_registry=None):
        self._groups: Dict[str, Group] = {}
        self._agent_groups: Dict[str, List[str]] = {}  # agent_id -> group_ids
        self._lru_group_ids: List[str] = []  # ✅ Track usage order for LRU cleanup
        self._socketio = socketio
        self._model_registry = model_registry
        self._lock = asyncio.Lock()  # ✅ Prevent concurrent modification
        self._cleanup_task: Optional[asyncio.Task] = None  # ✅ PHASE 56.4: Periodic cleanup

    async def start_cleanup(self, interval: int = 300):
        """Start periodic cleanup task (every 5 min by default)."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop(interval))
            logger.info("[GroupChat] Cleanup task started")

    async def stop_cleanup(self):
        """Stop the periodic cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("[GroupChat] Cleanup task stopped")

    async def _cleanup_loop(self, interval: int):
        """Periodic cleanup loop."""
        while True:
            try:
                await asyncio.sleep(interval)
                await self._cleanup_inactive_groups()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[GroupChat] Cleanup failed: {e}")

    async def select_responding_agents(
        self,
        content: str,
        participants: Dict[str, Any],
        sender_id: str,
        reply_to_agent: str = None,
        group: 'Group' = None  # Phase 80.28: Pass group for smart reply decay
    ) -> List[Any]:
        """
        Phase 57.7: Intelligent agent selection.
        Phase 80.6: MCP agent isolation - no auto-response cascade.
        Phase 80.7: Reply routing to original agent.
        Phase 80.28: Smart reply with decay - last responder continues conversation.

        Priority order:
        1. Reply routing (if replying to specific agent)
        2. @mentions (explicit targeting)
        3. Phase 80.28: Smart reply decay (last responder if no @mention, decay < 1)
        4. /solo, /team, /round commands
        5. SMART keyword-based selection
        6. Default: admin > first worker > hostess

        Args:
            content: Message text with potential commands/@mentions
            participants: Dict of group participants
            sender_id: ID of message sender (to exclude from responses)
            reply_to_agent: Agent ID to route reply to (Phase 80.7)
            group: Group object for smart reply decay tracking (Phase 80.28)

        Returns:
            List of participant dicts to respond
        """
        # MARKER_94.5_AGENT_SELECTION: Intelligent agent selection
        # MARKER_94.6_AGENT_SELECTION: Agent selection with role awareness
        # Phase 80.7: If this is a reply to a specific agent, route to that agent
        if reply_to_agent:
            # MARKER_90.1.3_START: Fix case-sensitive agent matching
            reply_to_normalized = reply_to_agent.lower().lstrip('@') if reply_to_agent else ''
            for pid, p in participants.items():
                agent_id = p.get('agent_id', '')
                agent_id_normalized = agent_id.lower().lstrip('@') if agent_id else ''
                # Match by normalized agent_id (case-insensitive)
                if agent_id_normalized == reply_to_normalized:
                    if p.get('role') != 'observer':
                        logger.info(f"[GroupChat] Phase 80.7: Reply routing to {p.get('display_name')}")
                        return [p]
            # MARKER_90.1.3_END
            # If reply_to_agent not found in participants, fall through to normal selection
            logger.warning(f"[GroupChat] Phase 80.7: Reply target '{reply_to_agent}' not found in participants")

        # Phase 80.6: Check if sender is MCP agent or AI agent (starts with @)
        # MCP agents should NOT trigger auto-response from other agents
        # Only explicit @mentions should work for agent-to-agent communication
        is_agent_sender = sender_id.startswith('@')

        # 1. Check for @mentions
        # Phase 80.31: Use single regex that captures full model IDs (with hyphens, dots, slashes)
        # Old regex r'@(\w+)' would truncate @gpt-5.2-pro to just 'gpt'
        all_mentions_raw = re.findall(r'@([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)', content)
        # Deduplicate and lowercase
        all_mentions = list(set(m.lower() for m in all_mentions_raw))

        if all_mentions:
            selected = []
            for pid, p in participants.items():
                display = p.get('display_name', '').lower()
                agent_id = p.get('agent_id', '').lower().lstrip('@')
                model_id = p.get('model_id', '').lower()

                for mention in all_mentions:
                    # Phase 80.31: Use EXACT match for model IDs (contains hyphen/dot/slash)
                    # Use substring match ONLY for simple agent names (PM, Dev, QA)
                    is_model_mention = '-' in mention or '.' in mention or '/' in mention

                    if is_model_mention:
                        # Exact match for model IDs
                        if mention == agent_id or mention == model_id or mention == display:
                            if p.get('role') != 'observer':
                                selected.append(p)
                                break
                    else:
                        # Substring match for simple names (@PM, @Dev, @Architect)
                        if mention == agent_id or mention in display.split()[0].lower():
                            if p.get('role') != 'observer':
                                selected.append(p)
                                break

            if selected:
                logger.info(f"[GroupChat] Selected by @mention: {[p.get('display_name') for p in selected]}")
                return selected

            # Phase 80.27: If @mention exists but NOT found in participants,
            # it's likely a model/MCP agent - don't fall through to default admin!
            logger.info(f"[GroupChat] Phase 80.27: @mention '{all_mentions}' not in participants - skipping default selection (likely model/MCP)")
            return []  # Let the model/MCP handle it

        # Phase 80.28: Smart reply with decay for MCP agents
        # If sender is MCP agent without @mention BUT there's a last_responder with decay < 2,
        # allow the conversation to continue (enables MCP→Agent chains)
        if is_agent_sender and group and group.last_responder_id and group.last_responder_decay < 2:
            # Find last responder in participants
            for pid, p in participants.items():
                agent_id = p.get('agent_id', '').lower().lstrip('@')
                if agent_id == group.last_responder_id.lower().lstrip('@'):
                    if p.get('role') != 'observer' and p.get('agent_id') != sender_id:
                        logger.info(f"[GroupChat] Phase 80.28: MCP smart reply to {p.get('display_name')} (decay={group.last_responder_decay})")
                        return [p]

        # Phase 80.6: If sender is an agent (MCP or AI) and no explicit @mention,
        # and no smart reply target, DO NOT auto-respond.
        if is_agent_sender:
            logger.info(f"[GroupChat] Phase 80.6: Agent sender '{sender_id}' without @mention - no auto-response")
            return []

        # Phase 80.28: Smart reply with decay for USER messages
        # If user sends message without @mention and there's a recent responder (decay < 1),
        # route to that responder for conversation continuity
        if sender_id == 'user' and group and group.last_responder_id and group.last_responder_decay < 1:
            for pid, p in participants.items():
                agent_id = p.get('agent_id', '').lower().lstrip('@')
                if agent_id == group.last_responder_id.lower().lstrip('@'):
                    if p.get('role') != 'observer':
                        logger.info(f"[GroupChat] Phase 80.28: Smart reply to {p.get('display_name')} (decay={group.last_responder_decay})")
                        return [p]

        content_lower = content.lower()

        # 2. Check for /solo command
        if '/solo' in content_lower or '/single' in content_lower:
            for p in participants.values():
                if p.get('role') != 'observer' and p.get('agent_id') != sender_id:
                    logger.info(f"[GroupChat] /solo: {p.get('display_name')}")
                    return [p]
            return []

        # 3. Check for /team or /all command
        if '/team' in content_lower or '/all' in content_lower:
            all_agents = [
                p for p in participants.values()
                if p.get('role') != 'observer' and p.get('agent_id') != sender_id
            ]
            logger.info(f"[GroupChat] /team: {[p.get('display_name') for p in all_agents]}")
            return all_agents

        # 4. Check for /round command (sequential order)
        if '/round' in content_lower or '/roundtable' in content_lower:
            order = {'PM': 0, 'Architect': 1, 'Dev': 2, 'QA': 3}
            agents = [
                p for p in participants.values()
                if p.get('role') != 'observer' and p.get('agent_id') != sender_id
            ]
            agents_sorted = sorted(agents, key=lambda x: order.get(x.get('display_name', ''), 99))
            logger.info(f"[GroupChat] /round: {[p.get('display_name') for p in agents_sorted]}")
            return agents_sorted

        # 5. SMART: Keyword-based selection
        keywords = {
            'PM': ['plan', 'task', 'scope', 'timeline', 'requirements', 'analyze', 'strategy', 'project', 'manage'],
            'Architect': ['architecture', 'design', 'system', 'pattern', 'structure', 'module', 'interface', 'component'],
            'Dev': ['code', 'implement', 'function', 'class', 'write', 'debug', 'fix', 'api', 'build', 'feature'],
            'QA': ['test', 'bug', 'review', 'verify', 'validate', 'coverage', 'quality', 'check', 'error']
        }

        scores = {}
        for agent_type, kws in keywords.items():
            score = sum(1 for kw in kws if kw in content_lower)
            if score > 0:
                scores[agent_type] = score

        if scores:
            selected = []
            for p in participants.values():
                display = p.get('display_name', '')
                if display in scores and p.get('role') != 'observer':
                    selected.append(p)
            if selected:
                logger.info(f"[GroupChat] SMART selection: {[p.get('display_name') for p in selected]} (scores={scores})")
                return selected

        # 6. Default: first non-observer agent (prefer admin)
        admin = None
        first_worker = None
        for p in participants.values():
            if p.get('role') == 'observer' or p.get('agent_id') == sender_id:
                continue
            if p.get('role') == 'admin' and not admin:
                admin = p
            elif not first_worker:
                first_worker = p

        result = admin or first_worker
        if result:
            logger.info(f"[GroupChat] Default: {result.get('display_name')}")
            return [result]

        return []

    async def create_group(
        self,
        name: str,
        admin_agent: GroupParticipant,
        participants: List[GroupParticipant] = None,
        description: str = "",
        project_id: str = None
    ) -> Group:
        """Create new group chat."""
        group_id = str(uuid.uuid4())

        group = Group(
            id=group_id,
            name=name,
            description=description,
            admin_id=admin_agent.agent_id,
            project_id=project_id
        )

        # Add admin
        group.participants[admin_agent.agent_id] = admin_agent
        self._track_agent_group(admin_agent.agent_id, group_id)

        # Add other participants
        if participants:
            for p in participants:
                group.participants[p.agent_id] = p
                self._track_agent_group(p.agent_id, group_id)

        # ✅ PHASE 56.4: Lock when modifying group storage
        async with self._lock:
            self._groups[group_id] = group
            # ✅ Track LRU for new groups
            self._lru_group_ids.append(group_id)

        # Emit event
        if self._socketio:
            await self._socketio.emit('group_created', group.to_dict())

        # Auto-save after group creation
        await self.save_to_json()

        logger.info(f"[GroupChat] Created group: {name} ({group_id})")
        return group

    def _track_agent_group(self, agent_id: str, group_id: str):
        """Track which groups an agent belongs to."""
        if agent_id not in self._agent_groups:
            self._agent_groups[agent_id] = []
        if group_id not in self._agent_groups[agent_id]:
            self._agent_groups[agent_id].append(group_id)

    async def add_participant(
        self,
        group_id: str,
        participant: GroupParticipant
    ) -> bool:
        """Add participant to group."""
        # ✅ PHASE 56.4: Lock when modifying group participants
        async with self._lock:
            group = self._groups.get(group_id)
            if not group:
                return False

            group.participants[participant.agent_id] = participant
            self._track_agent_group(participant.agent_id, group_id)

        # Emit event
        if self._socketio:
            await self._socketio.emit('group_joined', {
                'group_id': group_id,
                'participant': participant.to_dict()
            })

        # Auto-save after participant added
        await self.save_to_json()

        logger.info(f"[GroupChat] {participant.agent_id} joined {group.name}")
        return True

    async def remove_participant(self, group_id: str, agent_id: str) -> bool:
        """Remove participant from group."""
        # ✅ PHASE 56.4: Lock when modifying group participants
        async with self._lock:
            group = self._groups.get(group_id)
            if not group or agent_id not in group.participants:
                return False

            del group.participants[agent_id]

            if agent_id in self._agent_groups:
                self._agent_groups[agent_id].remove(group_id)

        # Emit event
        if self._socketio:
            await self._socketio.emit('group_left', {
                'group_id': group_id,
                'agent_id': agent_id
            })

        # Auto-save after participant removed
        await self.save_to_json()

        return True

    async def update_participant_model(
        self,
        group_id: str,
        agent_id: str,
        new_model_id: str
    ) -> bool:
        """
        Update participant's model assignment.
        Phase 82: Enable model reassignment after group creation (e.g., Deepseek fallback).
        """
        async with self._lock:
            group = self._groups.get(group_id)
            if not group or agent_id not in group.participants:
                logger.warning(f"[GroupChat] Cannot update model: group or participant not found")
                return False

            # Validate model exists in registry (if registry available)
            if self._model_registry:
                try:
                    model = await self._model_registry.get_model(new_model_id)
                    if not model:
                        logger.error(f"[GroupChat] Model not found in registry: {new_model_id}")
                        return False
                except Exception as e:
                    logger.warning(f"[GroupChat] Could not validate model {new_model_id}: {e}")

            # Update model
            group.participants[agent_id].model_id = new_model_id
            logger.info(f"[GroupChat] Updated {agent_id} model to {new_model_id}")

        # Emit event
        if self._socketio:
            await self._socketio.emit('group_participant_updated', {
                'group_id': group_id,
                'agent_id': agent_id,
                'model_id': new_model_id
            })

        # Auto-save
        await self.save_to_json()
        return True

    async def update_participant_role(
        self,
        group_id: str,
        agent_id: str,
        new_role: str
    ) -> bool:
        """
        Update participant's role.
        Phase 82: Enable role changes after group creation.
        """
        async with self._lock:
            group = self._groups.get(group_id)
            if not group or agent_id not in group.participants:
                logger.warning(f"[GroupChat] Cannot update role: group or participant not found")
                return False

            # Prevent removing last admin
            if group.participants[agent_id].role == GroupRole.ADMIN:
                if new_role != "admin":
                    # Count admins
                    admin_count = sum(1 for p in group.participants.values() if p.role == GroupRole.ADMIN)
                    if admin_count <= 1:
                        logger.error(f"[GroupChat] Cannot demote last admin in group {group_id}")
                        return False

            # Validate role
            try:
                role_enum = GroupRole(new_role)
            except ValueError:
                logger.error(f"[GroupChat] Invalid role: {new_role}")
                return False

            # Update role
            group.participants[agent_id].role = role_enum
            logger.info(f"[GroupChat] Updated {agent_id} role to {new_role}")

        # Emit event
        if self._socketio:
            await self._socketio.emit('group_participant_updated', {
                'group_id': group_id,
                'agent_id': agent_id,
                'role': new_role
            })

        # Auto-save
        await self.save_to_json()
        return True

    async def parse_mentions(self, content: str) -> List[str]:
        """Parse @mentions from message content (non-blocking)."""
        # ✅ PHASE 56.2: Run regex in executor (non-blocking)
        # ✅ PHASE 57.2: Fixed regex to capture full agent/model IDs with dashes, colons, dots, slashes
        # Examples: @nvidia/nemotron-3-nano-30b-a3b:free, @architect, @rust_dev
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            partial(re.findall, r'@([\w\-.:\/]+)', content)
        )

    async def send_message(
        self,
        group_id: str,
        sender_id: str,
        content: str,
        message_type: str = "chat",
        metadata: Dict[str, Any] = None
    ) -> Optional[GroupMessage]:
        """
        Send message to group with activity tracking.
        Parses @mentions and routes to appropriate agents.
        """
        async with self._lock:
            group = self._groups.get(group_id)
            if not group:
                logger.warning(f"[GroupChat] Group not found: {group_id}")
                return None

        # ✅ Parse mentions outside lock (non-blocking)
        mentions = await self.parse_mentions(content)

        async with self._lock:
            group = self._groups.get(group_id)
            if not group:
                return None

            # Create message
            message = GroupMessage(
                id=str(uuid.uuid4()),
                group_id=group_id,
                sender_id=sender_id,
                content=content,
                mentions=mentions,
                message_type=message_type,
                metadata=metadata or {}
            )

            # ✅ Store message (deque auto-removes oldest at maxlen)
            group.messages.append(message)

            # ✅ Update activity timestamp
            group.last_activity = datetime.now()

            # ✅ Track LRU for cleanup
            if group_id in self._lru_group_ids:
                self._lru_group_ids.remove(group_id)
            self._lru_group_ids.append(group_id)

            # ✅ PHASE 56.4: Don't emit here - let handlers broadcast with proper skip_sid
            # Callers (handlers) are responsible for broadcasting to avoid duplicate messages

            logger.info(f"[GroupChat] Message in {group.name}: {sender_id} -> {mentions or 'all'}")

        # Auto-save after message sent
        await self.save_to_json()

        # ✅ PHASE 56.4: Periodic cleanup task handles cleanup, not per-message

        return message

    async def route_to_agents(
        self,
        message: GroupMessage,
        orchestrator=None
    ) -> List[Dict[str, Any]]:
        """
        Route message to mentioned agents for processing.
        Returns list of agent responses.
        Note: Does NOT broadcast messages - callers must handle broadcasting.
        """
        group = self._groups.get(message.group_id)
        if not group:
            return []

        # Determine recipients
        if message.mentions:
            # Route to mentioned agents only
            recipients = [
                group.participants[f"@{m}"]
                for m in message.mentions
                if f"@{m}" in group.participants
            ]
        else:
            # Route to all non-observer agents
            recipients = [
                p for p in group.participants.values()
                if p.role != GroupRole.OBSERVER
            ]

        if not recipients:
            logger.warning(f"[GroupChat] No recipients for message in {group.name}")
            return []

        responses = []

        for participant in recipients:
            try:
                # Build context from group history
                context = self._build_context(group, participant)

                # Get agent response (via orchestrator or direct LLM call)
                if orchestrator:
                    response = await orchestrator.call_agent(
                        agent_type=participant.role.value,
                        model_id=participant.model_id,
                        prompt=message.content,
                        context=context
                    )
                else:
                    # Fallback: Direct response placeholder
                    response = {
                        'agent_id': participant.agent_id,
                        'content': f"[{participant.display_name}] Received: {message.content}",
                        'status': 'pending'
                    }

                responses.append(response)

                # ✅ PHASE 56.4: Store response message internally but don't broadcast
                # Callers handle broadcasting to avoid duplicates
                await self.send_message(
                    group_id=message.group_id,
                    sender_id=participant.agent_id,
                    content=response.get('content', ''),
                    message_type='response',
                    metadata={'original_message_id': message.id}
                )

            except Exception as e:
                logger.error(f"[GroupChat] Agent {participant.agent_id} failed: {e}")
                responses.append({
                    'agent_id': participant.agent_id,
                    'error': str(e)
                })

        return responses

    def _build_context(self, group: Group, participant: GroupParticipant) -> str:
        """Build context for agent from group history."""
        # Last 10 messages
        recent = group.messages[-10:]

        context_parts = [
            f"Group: {group.name}",
            f"Your role: {participant.role.value}",
            f"Your agent ID: {participant.agent_id}",
            "",
            "Recent messages:"
        ]

        for msg in recent:
            context_parts.append(f"[{msg.sender_id}]: {msg.content}")

        # Add shared context if any
        if group.shared_context:
            context_parts.append("")
            context_parts.append("Shared context:")
            for key, value in group.shared_context.items():
                context_parts.append(f"- {key}: {value}")

        return "\n".join(context_parts)

    async def assign_task(
        self,
        group_id: str,
        assigner_id: str,
        assignee_id: str,
        task_description: str,
        dependencies: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Admin assigns task to agent.
        Creates task node in VETKA tree.
        """
        group = self._groups.get(group_id)
        if not group:
            return None

        # Verify assigner is admin
        assigner = group.participants.get(assigner_id)
        if not assigner or assigner.role != GroupRole.ADMIN:
            logger.warning(f"[GroupChat] Non-admin {assigner_id} tried to assign task")
            return None

        # Create task
        task = {
            'id': str(uuid.uuid4()),
            'group_id': group_id,
            'assigned_by': assigner_id,
            'assigned_to': assignee_id,
            'description': task_description,
            'status': 'pending',
            'dependencies': dependencies or [],
            'created_at': datetime.now().isoformat()
        }

        # Send as task message
        await self.send_message(
            group_id=group_id,
            sender_id=assigner_id,
            content=f"@{assignee_id.lstrip('@')} Task: {task_description}",
            message_type='task',
            metadata=task
        )

        # Emit task created
        if self._socketio:
            await self._socketio.emit('task_created', task)

        logger.info(f"[GroupChat] Task assigned: {assigner_id} -> {assignee_id}")
        return task

    def get_group(self, group_id: str) -> Optional[dict]:
        """Get group by ID."""
        group = self._groups.get(group_id)
        return group.to_dict() if group else None

    def get_group_object(self, group_id: str) -> Optional['Group']:
        """Phase 80.28: Get raw Group object for smart reply tracking."""
        return self._groups.get(group_id)

    def get_all_groups(self) -> List[dict]:
        """Get all groups."""
        return [g.to_dict() for g in self._groups.values()]

    def get_agent_groups(self, agent_id: str) -> List[dict]:
        """Get groups for specific agent."""
        group_ids = self._agent_groups.get(agent_id, [])
        return [
            self._groups[gid].to_dict()
            for gid in group_ids
            if gid in self._groups
        ]

    def get_messages(self, group_id: str, limit: int = 50) -> List[dict]:
        """Get recent messages from group."""
        group = self._groups.get(group_id)
        if not group:
            return []

        # ✅ deque supports slicing like list
        messages = list(group.messages)[-limit:]
        return [m.to_dict() for m in messages]

    async def save_to_json(self):
        """
        Save all groups to JSON file for persistence.
        Called after: group creation, message send, participant changes.
        """
        try:
            async with self._lock:
                # Build JSON structure
                groups_data = {}
                for group_id, group in self._groups.items():
                    groups_data[group_id] = {
                        'id': group.id,
                        'name': group.name,
                        'description': group.description,
                        'admin_id': group.admin_id,
                        'participants': {
                            agent_id: p.to_dict()
                            for agent_id, p in group.participants.items()
                        },
                        'messages': [
                            msg.to_dict() for msg in group.messages
                        ],
                        'shared_context': group.shared_context,
                        'project_id': group.project_id,
                        'created_at': group.created_at.isoformat(),
                        'last_activity': group.last_activity.isoformat()
                    }

                data = {
                    'groups': groups_data,
                    'saved_at': datetime.now().isoformat()
                }

                # Ensure data directory exists
                self.GROUPS_FILE.parent.mkdir(parents=True, exist_ok=True)

                # Write atomically (write to temp, then rename)
                temp_file = self.GROUPS_FILE.with_suffix('.tmp')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                # Atomic rename
                temp_file.replace(self.GROUPS_FILE)

                logger.info(f"[GroupChat] Saved {len(groups_data)} groups to {self.GROUPS_FILE}")

        except Exception as e:
            logger.error(f"[GroupChat] Failed to save groups: {e}")

    async def load_from_json(self):
        """
        Load groups from JSON file on startup.
        Reconstructs GroupParticipant, GroupMessage, and Group objects.
        """
        if not self.GROUPS_FILE.exists():
            logger.info(f"[GroupChat] No saved groups file found at {self.GROUPS_FILE}")
            return

        try:
            async with self._lock:
                with open(self.GROUPS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                groups_data = data.get('groups', {})
                loaded_count = 0

                for group_id, group_dict in groups_data.items():
                    # Reconstruct participants
                    participants = {}
                    for agent_id, p_dict in group_dict.get('participants', {}).items():
                        participants[agent_id] = GroupParticipant(
                            agent_id=p_dict['agent_id'],
                            model_id=p_dict['model_id'],
                            role=GroupRole(p_dict['role']),
                            display_name=p_dict['display_name'],
                            permissions=p_dict.get('permissions', ['read', 'write'])
                        )

                    # Reconstruct messages
                    messages = deque(maxlen=self.MAX_MESSAGES_PER_GROUP)
                    for msg_dict in group_dict.get('messages', []):
                        msg = GroupMessage(
                            id=msg_dict['id'],
                            group_id=msg_dict['group_id'],
                            sender_id=msg_dict['sender_id'],
                            content=msg_dict['content'],
                            mentions=msg_dict.get('mentions', []),
                            message_type=msg_dict.get('message_type', 'chat'),
                            metadata=msg_dict.get('metadata', {}),
                            created_at=datetime.fromisoformat(msg_dict['created_at'])
                        )
                        messages.append(msg)

                    # Reconstruct group
                    group = Group(
                        id=group_dict['id'],
                        name=group_dict['name'],
                        description=group_dict.get('description', ''),
                        admin_id=group_dict.get('admin_id', ''),
                        participants=participants,
                        messages=messages,
                        shared_context=group_dict.get('shared_context', {}),
                        project_id=group_dict.get('project_id'),
                        created_at=datetime.fromisoformat(group_dict['created_at']),
                        last_activity=datetime.fromisoformat(group_dict['last_activity'])
                    )

                    # Store group
                    self._groups[group_id] = group

                    # Track agent-group relationships
                    for agent_id in participants.keys():
                        self._track_agent_group(agent_id, group_id)

                    # Track LRU (most recently active groups first)
                    self._lru_group_ids.append(group_id)
                    loaded_count += 1

                # Sort LRU by last_activity (most recent last)
                self._lru_group_ids.sort(
                    key=lambda gid: self._groups[gid].last_activity
                )

                logger.info(f"[GroupChat] Loaded {loaded_count} groups from {self.GROUPS_FILE}")

        except Exception as e:
            logger.error(f"[GroupChat] Failed to load groups: {e}")

    # ✅ PHASE 56.2: Cleanup method for memory management
    async def _cleanup_inactive_groups(self):
        """Remove inactive groups from memory (LRU + timeout)."""
        async with self._lock:
            now = datetime.now()

            # Find inactive groups (no activity for 24 hours)
            inactive_groups = [
                gid for gid, group in self._groups.items()
                if now - group.last_activity > self.INACTIVE_GROUP_TIMEOUT
            ]

            # Remove inactive groups
            for gid in inactive_groups:
                del self._groups[gid]
                if gid in self._lru_group_ids:
                    self._lru_group_ids.remove(gid)
                logger.info(f"[GroupChat] Cleaned up inactive group: {gid}")

            # Remove least-recently-used if over memory limit
            while len(self._groups) > self.MAX_GROUPS_MEMORY:
                if not self._lru_group_ids:
                    break
                oldest_id = self._lru_group_ids.pop(0)
                if oldest_id in self._groups:
                    del self._groups[oldest_id]
                    logger.info(f"[GroupChat] Evicted LRU group: {oldest_id}")


# Singleton
_group_chat_manager: Optional[GroupChatManager] = None


def get_group_chat_manager(socketio=None, model_registry=None) -> GroupChatManager:
    """Get or create singleton GroupChatManager."""
    global _group_chat_manager
    if _group_chat_manager is None:
        _group_chat_manager = GroupChatManager(socketio, model_registry)
    return _group_chat_manager
