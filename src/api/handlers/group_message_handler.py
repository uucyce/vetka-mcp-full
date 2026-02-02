"""
Group Message Socket.IO Handler with Streaming Support

@file group_message_handler.py
@status ACTIVE
@phase Phase 80.13 - MCP @mention Routing
@lastUpdate 2026-01-22

Handles:
- Group message routing with @mentions
- Streaming responses from AI agents (via orchestrator)
- Multi-agent conversations in groups
- Full Elisya context integration
- Phase 57.8: Hostess as intelligent router for groups
- Phase 80.13: MCP agent @mention routing (browser_haiku, claude_code)

Phase 57.4: Now uses orchestrator.call_agent() instead of direct HTTP.
This gives us: Elisya context, CAM metrics, semantic search, proper key rotation.

Phase 57.8: Hostess now acts as the group router:
- Without @mention: Hostess analyzes and decides who responds
- Simple questions: Hostess answers directly
- Tasks/projects: Hostess delegates to Architect

Phase 80.13: MCP Agent @mention routing:
- When user @mentions browser_haiku or claude_code
- System notifies MCP agent via dedicated mechanism
- MCP agents can respond through debug API endpoints
"""

import asyncio
import uuid
import time
import logging
import json
import re

logger = logging.getLogger(__name__)

# Global SocketIO reference for tools
_socketio_instance = None


def set_socketio(sio):
    """Set global SocketIO instance for artifact tools."""
    global _socketio_instance
    _socketio_instance = sio


def get_socketio():
    """Get global SocketIO instance."""
    return _socketio_instance


from src.services.group_chat_manager import (
    get_group_chat_manager,
    GroupParticipant,
    GroupRole,
)
from src.initialization.components_init import get_orchestrator
from src.chat.chat_history_manager import get_chat_history_manager
from src.agents.role_prompts import (
    PM_SYSTEM_PROMPT,
    DEV_SYSTEM_PROMPT,
    QA_SYSTEM_PROMPT,
    ARCHITECT_SYSTEM_PROMPT,
    RESEARCHER_SYSTEM_PROMPT,
    get_agent_prompt,
)

# Phase 55.1: MCP session init
from src.mcp.tools.session_tools import vetka_session_init

# ============================================================================
# PHASE 80.13: MCP AGENT @MENTION ROUTING
# ============================================================================
# MCP agents are external (browser_haiku, claude_code) and not group participants.
# When @mentioned, we notify them via dedicated mechanism.

MCP_AGENTS = {
    "browser_haiku": {
        "name": "Browser Haiku",
        "endpoint": "mcp/browser_haiku",
        "icon": "eye",
        "role": "Tester",
        "aliases": ["browserhaiku", "browser", "haiku"],
    },
    "claude_code": {
        "name": "Claude Code",
        "endpoint": "mcp/claude_code",
        "icon": "terminal",
        "role": "Executor",
        "aliases": ["claudecode", "claude", "code"],
    },
}


async def notify_mcp_agents(
    sio,
    group_id: str,
    group_name: str,
    sender_id: str,
    content: str,
    mentions: list,
    message_id: str,
):
    """
    Phase 80.13: Notify MCP agents when they are @mentioned.

    Emits a socket event 'mcp_mention' that browser extensions can listen to.
    Also stores the mention in debug_routes team_messages for API access.

    Args:
        sio: SocketIO instance
        group_id: Group UUID
        group_name: Group name for context
        sender_id: Who sent the message
        content: Full message content
        mentions: List of mention names extracted from content
        message_id: ID of the original message
    """
    # Find which MCP agents are mentioned
    mentioned_mcp_agents = []

    for mention in mentions:
        mention_lower = mention.lower()

        # Check direct match
        if mention_lower in MCP_AGENTS:
            mentioned_mcp_agents.append(mention_lower)
            continue

        # Check aliases
        for agent_id, agent_info in MCP_AGENTS.items():
            if mention_lower in agent_info.get("aliases", []):
                mentioned_mcp_agents.append(agent_id)
                break

    if not mentioned_mcp_agents:
        return

    print(
        f"[MCP_MENTION] Phase 80.13: Detected MCP agent mentions: {mentioned_mcp_agents}"
    )

    # Build notification payload
    notification = {
        "type": "mcp_mention",
        "group_id": group_id,
        "group_name": group_name,
        "sender_id": sender_id,
        "content": content,
        "message_id": message_id,
        "timestamp": time.time(),
        "mentioned_agents": mentioned_mcp_agents,
    }

    # Emit socket event for each mentioned MCP agent
    for agent_id in mentioned_mcp_agents:
        agent_info = MCP_AGENTS[agent_id]

        # Emit targeted event
        await sio.emit(
            "mcp_mention",
            {
                **notification,
                "target_agent": agent_id,
                "agent_name": agent_info["name"],
                "agent_role": agent_info["role"],
            },
            namespace="/",
        )

        print(
            f"[MCP_MENTION] Notified {agent_info['name']} of @mention in {group_name}"
        )

    # Store in team_messages buffer for API access
    try:
        from src.api.routes.debug_routes import team_messages, KNOWN_AGENTS

        for agent_id in mentioned_mcp_agents:
            agent_info = MCP_AGENTS[agent_id]

            msg = {
                "id": f"mcp_{message_id}_{agent_id}",
                "timestamp": time.time(),
                "sender": sender_id,
                "sender_info": {"name": sender_id, "icon": "user", "role": "User"},
                "to": agent_id,
                "to_info": {
                    "name": agent_info["name"],
                    "icon": agent_info["icon"],
                    "role": agent_info["role"],
                },
                "message": content,
                "priority": "normal",
                "context": {
                    "group_id": group_id,
                    "group_name": group_name,
                    "message_id": message_id,
                    "type": "group_mention",
                },
                "pending": True,
                "read": False,
            }

            team_messages.append(msg)

            # Keep buffer limited (max 100)
            if len(team_messages) > 100:
                team_messages[:] = team_messages[-100:]

    except ImportError as e:
        print(f"[MCP_MENTION] Could not import debug_routes: {e}")
    except Exception as e:
        print(f"[MCP_MENTION] Error storing message: {e}")


# ============================================================================
# PHASE 57.8: HOSTESS ROUTER
# ============================================================================


async def route_through_hostess(
    sio, manager, orchestrator, group_id: str, group: dict, sender_id: str, content: str
) -> dict:
    """
    Route message through Hostess for intelligent dispatch.
    Phase 57.8: Hostess as the group orchestrator.

    Returns:
        dict with:
        - 'handled': True if Hostess answered directly
        - 'delegate_to': agent name if delegation needed
        - 'response': Hostess's message (if any)
    """
    print(f"[GROUP_HOSTESS] Analyzing message for intelligent routing...")

    # Build context for Hostess
    recent_messages = manager.get_messages(group_id, limit=5)
    participants_list = [
        p.get("display_name") for p in group.get("participants", {}).values()
    ]

    hostess_prompt = f"""You are the Hostess - the orchestrator of a group chat with AI agents.

## GROUP: {group.get("name", "Unknown")}
## PARTICIPANTS: {", ".join(participants_list)}

## RECENT CONVERSATION:
{chr(10).join([f"[{m.get('sender_id')}]: {m.get('content', '')[:150]}" for m in recent_messages[-5:]])}

## USER MESSAGE:
{content}

## YOUR TASK:
Analyze this message and decide:

1. If it's a SIMPLE QUESTION (greeting, clarification, quick answer about the group or project):
   - Answer it yourself briefly and helpfully
   - Return: {{"action": "answer", "response": "your brief answer"}}

2. If it's a TASK/PROJECT (needs planning, coding, implementation, architecture):
   - Delegate to @Architect who will coordinate the team
   - Return: {{"action": "delegate", "to": "Architect", "reason": "brief reason why this needs the team"}}

3. If it's a RESEARCH question (needs investigation, deep analysis, code review):
   - Delegate to @Researcher if available, otherwise @Architect
   - Return: {{"action": "delegate", "to": "Researcher", "reason": "brief reason"}}

4. If it's CODE/IMPLEMENTATION request (write code, fix bug, implement feature):
   - Delegate to @Dev for direct implementation
   - Return: {{"action": "delegate", "to": "Dev", "reason": "brief reason"}}

5. If it's a REVIEW/TEST request:
   - Delegate to @QA
   - Return: {{"action": "delegate", "to": "QA", "reason": "brief reason"}}

Be smart about this. Simple greetings like "Hello" or "What can you do?" should be answered by you.
Complex requests like "Build a calculator" need the Architect.

Respond ONLY with valid JSON. No other text."""

    try:
        # Call Hostess via orchestrator
        result = await asyncio.wait_for(
            orchestrator.call_agent(
                agent_type="Hostess",
                model_id="qwen2:7b",  # Fast local model
                prompt=hostess_prompt,
                context={"group_id": group_id, "is_routing": True},
            ),
            timeout=30.0,  # 30 second timeout for routing
        )

        response_text = ""
        if isinstance(result, dict):
            response_text = result.get("output", "") or result.get("response", "")
        else:
            response_text = str(result)

        print(f"[GROUP_HOSTESS] Raw response: {response_text[:200]}...")

        # Parse JSON response
        json_match = re.search(r"\{[^{}]*\}", response_text, re.DOTALL)
        if json_match:
            try:
                decision = json.loads(json_match.group())
                action = decision.get("action", "answer")

                if action == "answer":
                    # Hostess answers directly
                    answer = decision.get("response", response_text)

                    # Emit Hostess response
                    msg_id = str(uuid.uuid4())
                    await sio.emit(
                        "group_stream_start",
                        {
                            "id": msg_id,
                            "group_id": group_id,
                            "agent_id": "@Hostess",
                            "model": "qwen2:7b",
                        },
                        room=f"group_{group_id}",
                    )

                    await sio.emit(
                        "group_stream_end",
                        {
                            "id": msg_id,
                            "group_id": group_id,
                            "agent_id": "@Hostess",
                            "full_message": answer,
                            "metadata": {"model": "qwen2:7b", "agent_type": "Hostess"},
                        },
                        room=f"group_{group_id}",
                    )

                    # Store message
                    await manager.send_message(
                        group_id=group_id,
                        sender_id="@Hostess",
                        content=answer,
                        message_type="response",
                    )

                    print(f"[GROUP_HOSTESS] Answered directly: {len(answer)} chars")
                    return {"handled": True, "delegate_to": None, "response": answer}

                elif action == "delegate":
                    # Hostess delegates to another agent
                    delegate_to = decision.get("to", "Architect")
                    reason = decision.get("reason", "Task requires specialist")

                    # Emit Hostess delegation message
                    delegation_msg = f"This needs the team's expertise. {reason}\n\nHanding off to @{delegate_to}..."

                    msg_id = str(uuid.uuid4())
                    await sio.emit(
                        "group_stream_end",
                        {
                            "id": msg_id,
                            "group_id": group_id,
                            "agent_id": "@Hostess",
                            "full_message": delegation_msg,
                            "metadata": {"model": "qwen2:7b", "agent_type": "Hostess"},
                        },
                        room=f"group_{group_id}",
                    )

                    await manager.send_message(
                        group_id=group_id,
                        sender_id="@Hostess",
                        content=delegation_msg,
                        message_type="system",
                    )

                    print(f"[GROUP_HOSTESS] Delegating to {delegate_to}: {reason}")
                    return {
                        "handled": False,
                        "delegate_to": delegate_to,
                        "response": delegation_msg,
                    }

            except json.JSONDecodeError as je:
                print(f"[GROUP_HOSTESS] JSON parse error: {je}")

        # Fallback: if parsing fails, delegate to Architect
        print(f"[GROUP_HOSTESS] Parsing failed, defaulting to Architect delegation")
        return {"handled": False, "delegate_to": "Architect", "response": None}

    except asyncio.TimeoutError:
        print(f"[GROUP_HOSTESS] Timeout, defaulting to Architect")
        return {"handled": False, "delegate_to": "Architect", "response": None}
    except Exception as e:
        print(f"[GROUP_HOSTESS] Error: {e}")
        import traceback

        traceback.print_exc()
        return {"handled": False, "delegate_to": "Architect", "response": None}


async def post_hostess_summary(
    sio,
    manager,
    orchestrator,
    group_id: str,
    group: dict,
    original_content: str,
    previous_outputs: dict,
) -> None:
    """
    Post a summary from Hostess after all agents have responded.
    Phase 57.8: Hostess closes the loop with a helpful summary.
    """
    if len(previous_outputs) < 2:
        # Only summarize when multiple agents responded
        return

    try:
        # Build summary context
        outputs_summary = "\n\n".join(
            [
                f"**{agent_name}**: {output[:300]}..."
                for agent_name, output in previous_outputs.items()
            ]
        )

        summary_prompt = f"""The team has completed their work on the user's request. Provide a brief, helpful summary.

## ORIGINAL REQUEST:
{original_content}

## TEAM RESPONSES:
{outputs_summary}

## YOUR TASK:
1. Summarize what was accomplished (2-3 sentences max)
2. Highlight any key deliverables or artifacts
3. Mention next steps if relevant
4. Keep it SHORT and actionable

Respond naturally as the helpful Hostess. No JSON needed."""

        result = await asyncio.wait_for(
            orchestrator.call_agent(
                agent_type="Hostess",
                model_id="qwen2:7b",
                prompt=summary_prompt,
                context={"group_id": group_id, "is_summary": True},
            ),
            timeout=30.0,
        )

        summary_text = ""
        if isinstance(result, dict):
            summary_text = result.get("output", "") or result.get("response", "")
        else:
            summary_text = str(result)

        if summary_text and len(summary_text) > 20:
            # Clean up any JSON artifacts
            summary_text = re.sub(r"\{[^}]+\}", "", summary_text).strip()

            if summary_text:
                final_msg = f"**Summary**\n\n{summary_text}"

                msg_id = str(uuid.uuid4())
                await sio.emit(
                    "group_stream_end",
                    {
                        "id": msg_id,
                        "group_id": group_id,
                        "agent_id": "@Hostess",
                        "full_message": final_msg,
                        "metadata": {
                            "model": "qwen2:7b",
                            "agent_type": "Hostess",
                            "is_summary": True,
                        },
                    },
                    room=f"group_{group_id}",
                )

                await manager.send_message(
                    group_id=group_id,
                    sender_id="@Hostess",
                    content=final_msg,
                    message_type="system",
                )

                print(f"[GROUP_HOSTESS] Posted summary: {len(summary_text)} chars")

    except Exception as e:
        print(f"[GROUP_HOSTESS] Summary failed: {e}")


# ============================================================================
# MAIN HANDLER REGISTRATION
# ============================================================================


def register_group_message_handler(sio, app=None):
    """Register group chat Socket.IO handlers.

    Phase 57.4: Uses orchestrator for LLM calls instead of direct HTTP.
    Phase 57.8: Hostess as intelligent router + summary provider.
    """
    # Store SocketIO reference for artifact tools
    set_socketio(sio)

    @sio.on("join_group")
    async def handle_join_group(sid, data):
        """Handle client joining a group room."""
        group_id = data.get("group_id")
        if group_id:
            # Join Socket.IO room for this group
            await sio.enter_room(sid, f"group_{group_id}")
            print(f"[GROUP] Client {sid[:8]} joined group room: {group_id}")
            await sio.emit("group_joined_ack", {"group_id": group_id}, to=sid)

    @sio.on("leave_group")
    async def handle_leave_group(sid, data):
        """Handle client leaving a group room."""
        group_id = data.get("group_id")
        if group_id:
            await sio.leave_room(sid, f"group_{group_id}")
            print(f"[GROUP] Client {sid[:8]} left group room: {group_id}")

    @sio.on("group_message")
    async def handle_group_message(sid, data):
        """
        # MARKER_94.6_MESSAGE_BROADCAST: Group message broadcasting
        Handle group message with streaming response.
        Phase 57: Smart key rotation with 24h cooldown markers.

        Expected data:
        - group_id: Group UUID
        - sender_id: "user" or agent_id
        - content: Message text (may contain @mentions)
        """
        # MARKER_94.5_GROUP_ENTRY: Group chat entry point
        print(f"\n{'=' * 50}")
        print(f"[GROUP_MESSAGE] Received from {sid}")
        print(f"[GROUP_MESSAGE] Data: {data}")
        print(f"{'=' * 50}\n")

        group_id = data.get("group_id")
        sender_id = data.get("sender_id", "user")
        content = data.get("content", "").strip()
        reply_to_id = data.get("reply_to")  # Phase 80.7: Message ID being replied to
        pinned_files = data.get(
            "pinned_files", []
        )  # Phase 80.11: Pinned files for context

        # Phase 55.1: MCP group session init (fire-and-forget, non-blocking)
        async def _bg_session_init():
            try:
                session = await asyncio.wait_for(
                    vetka_session_init(user_id=sender_id, group_id=group_id, compress=False),
                    timeout=1.0
                )
                print(f"   [MCP] Group session initialized: {session.get('session_id')}")
            except asyncio.TimeoutError:
                print(f"   ⚠️ MCP session init timeout (1s)")
            except Exception as e:
                print(f"   ⚠️ MCP group session init failed: {e}")
        asyncio.create_task(_bg_session_init())

        if not group_id or not content:
            await sio.emit(
                "group_error", {"error": "Missing group_id or content"}, to=sid
            )
            return

        manager = get_group_chat_manager()
        group = manager.get_group(group_id)
        # Phase 80.28: Get Group object for smart reply decay
        group_object = manager.get_group_object(group_id)

        if not group:
            await sio.emit(
                "group_error", {"error": f"Group not found: {group_id}"}, to=sid
            )
            return

        # Store user message in group (Phase 80.11: Include pinned_files in metadata)
        user_message = await manager.send_message(
            group_id=group_id,
            sender_id=sender_id,
            content=content,
            message_type="chat",
            metadata={"pinned_files": pinned_files} if pinned_files else {},
        )

        if not user_message:
            await sio.emit("group_error", {"error": "Failed to store message"}, to=sid)
            return

        # Broadcast user message to group room
        await sio.emit(
            "group_message", user_message.to_dict(), room=f"group_{group_id}"
        )

        # MARKER_108_3_SOCKETIO_UPDATE: Phase 108.3 - Real-time chat node updates
        # Emit chat_node_update for opacity animation when user sends message
        from datetime import datetime
        await sio.emit(
            "chat_node_update",
            {
                "chat_id": group_id,
                "decay_factor": 1.0,  # Just updated = fully opaque
                "last_activity": datetime.now().isoformat(),
                "message_count": len(manager.get_messages(group_id, limit=1000)),
            },
            room=f"group_{group_id}",
        )

        # Phase 80.28: Increment decay counter on user messages (for smart reply)
        if sender_id == "user" and group_object:
            group_object.last_responder_decay += 1
            print(
                f"[GROUP_DEBUG] Phase 80.28: User message, decay now {group_object.last_responder_decay}"
            )

        # Phase 80.13: Check for MCP agent @mentions and notify them
        # MCP agents (browser_haiku, claude_code) are not in participants
        # but can be @mentioned and notified via socket events
        mentions = (
            user_message.mentions
            if hasattr(user_message, "mentions")
            # MARKER_108_ROUTING_FIX_4: Support hyphenated model names
            else re.findall(r"@([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)", content)
        )
        if mentions:
            await notify_mcp_agents(
                sio=sio,
                group_id=group_id,
                group_name=group.get("name", "Unknown Group"),
                sender_id=sender_id,
                content=content,
                mentions=mentions,
                message_id=user_message.id,
            )

        # Phase 74.8: Save user message to chat_history
        try:
            chat_history = get_chat_history_manager()
            group_name = group.get("name", f"Group {group_id[:8]}")
            # Find or create chat by group name (Phase 74.10: strip handles trailing spaces)
            chat_id = chat_history.get_or_create_chat(
                file_path="unknown", context_type="group", display_name=group_name
            )
            chat_history.add_message(
                chat_id,
                {
                    "role": "user",
                    "content": content,
                    "agent": sender_id,
                    "metadata": {"group_id": group_id},
                },
            )
        except Exception as chat_err:
            print(f"[GROUP_CHAT] Error saving to chat_history: {chat_err}")

        # Phase 57.4: Get orchestrator for proper LLM routing
        orchestrator = get_orchestrator()
        if not orchestrator:
            print(f"[GROUP_ERROR] Orchestrator is None! Cannot call agents.")
            await sio.emit(
                "group_error", {"error": "Orchestrator not initialized"}, to=sid
            )
            return
        print(f"[GROUP_DEBUG] Orchestrator loaded: {type(orchestrator).__name__}")

        # Phase 80.7: Find original agent if this is a reply
        # MARKER_108_ROUTING_FIX_2: Handle MCP agent replies
        reply_to_agent = None
        reply_to_mcp_agent = False
        if reply_to_id:
            # Look up the original message to find its sender
            messages = manager.get_messages(group_id, limit=100)
            for msg in messages:
                if msg.get("id") == reply_to_id:
                    original_sender = msg.get("sender_id", "")
                    # Only route to agent replies (not user replies)
                    if original_sender.startswith("@"):
                        reply_to_agent = original_sender
                        # Phase 108: Check if this is MCP agent (claude_code, browser_haiku, etc.)
                        # MCP agents are NOT in participants list
                        mcp_agent_names = ["claude_code", "browser_haiku", "lmstudio", "cursor", "opencode"]
                        agent_name_lower = original_sender.lower().lstrip("@")
                        if any(mcp_name in agent_name_lower for mcp_name in mcp_agent_names):
                            reply_to_mcp_agent = True
                            print(
                                f"[GROUP_DEBUG] Phase 108: Reply to MCP agent {reply_to_agent} - skipping group routing"
                            )
                        else:
                            print(
                                f"[GROUP_DEBUG] Phase 80.7: Reply to message {reply_to_id[:8]}... from {reply_to_agent}"
                            )
                    break

        # MARKER_108_ROUTING_FIX_2: If replying to MCP agent, don't route to group agents
        if reply_to_mcp_agent:
            print(f"[GROUP_DEBUG] Phase 108: Reply to MCP agent - no group agents invoked")
            return

        # Phase 57.7: Use smart agent selection
        # Phase 80.7: Pass reply_to_agent for proper routing
        # Phase 80.28: Pass group_object for smart reply decay
        participants_to_respond = await manager.select_responding_agents(
            content=content,
            participants=group.get("participants", {}),
            sender_id=sender_id,
            reply_to_agent=reply_to_agent,
            group=group_object,  # Phase 80.28
        )

        # Phase 57.8.2: REMOVED Hostess routing - она слишком медленная для роутинга
        # Hostess теперь только для: камера, навигация, context awareness
        # Вместо этого полагаемся на select_responding_agents + agent-to-agent @mentions

        if not participants_to_respond:
            # Enhanced debug: show why no one responds
            all_participants = [
                (pid, pdata.get("role", "unknown"))
                for pid, pdata in group.get("participants", {}).items()
            ]
            print(f"[GROUP_DEBUG] No agents to respond!")
            print(f"[GROUP_DEBUG] All participants: {all_participants}")
            print(f"[GROUP_DEBUG] Sender ID: {sender_id}")
            return

        print(
            f"[GROUP_DEBUG] Participants to respond: {[p['agent_id'] for p in participants_to_respond]}"
        )

        # Phase 57.7: Track previous outputs for chain context
        previous_outputs = {}

        # Phase 57.8.2: Use while loop to allow dynamic addition of agents via @mentions
        # for loop doesn't see items added during iteration
        processed_idx = 0
        max_agents = 10  # Safety limit to prevent infinite loops

        while (
            processed_idx < len(participants_to_respond) and processed_idx < max_agents
        ):
            participant = participants_to_respond[processed_idx]
            processed_idx += 1

            agent_id = participant["agent_id"]
            model_id = participant["model_id"]

            # Detect provider for model attribution
            from src.elisya.provider_registry import ProviderRegistry
            detected_provider = ProviderRegistry.detect_provider(model_id)
            provider_name = detected_provider.value if detected_provider else "unknown"

            # MARKER_93.7_REMOVED_OPENROUTER_PREFIX: Phase 93.7 Fix
            # Previously this code added "openrouter/" prefix which broke routing:
            # - "openai/gpt-5.2" -> "openrouter/openai/gpt-5.2" -> Provider.OPENROUTER -> 402
            # Now we let detect_provider work correctly:
            # - "openai/gpt-5.2" -> Provider.OPENAI -> uses OpenAI API directly -> works!
            # The old "fix" was counterproductive because it forced OpenRouter
            # instead of letting the system use the appropriate provider.
            display_name = participant["display_name"]
            role = participant.get("role", "worker")

            # MARKER_94.6_ROLE_ROUTING: Role-based agent routing
            # Map group role to orchestrator agent type
            agent_type_map = {
                "PM": "PM",
                "pm": "PM",
                "Dev": "Dev",
                "dev": "Dev",
                "QA": "QA",
                "qa": "QA",
                "Architect": "Architect",
                "architect": "Architect",
                "Researcher": "Researcher",  # Phase 57.8
                "researcher": "Researcher",
                "admin": "PM",  # Default admin to PM
                "worker": "Dev",  # Default worker to Dev
            }
            agent_type = agent_type_map.get(
                display_name, agent_type_map.get(role, "Dev")
            )

            print(
                f"[GROUP] Calling agent {agent_id} ({model_id}) via orchestrator as {agent_type}..."
            )

            # Emit typing indicator
            await sio.emit(
                "group_typing",
                {"group_id": group_id, "agent_id": agent_id},
                room=f"group_{group_id}",
            )

            # Emit stream start
            msg_id = str(uuid.uuid4())
            await sio.emit(
                "group_stream_start",
                {
                    "id": msg_id,
                    "group_id": group_id,
                    "agent_id": agent_id,
                    "model": model_id,
                },
                room=f"group_{group_id}",
            )

            try:
                # Phase 57.7: Build role-specific prompt with chain context
                system_prompt = get_agent_prompt(agent_type)

                # Build recent messages context
                recent_messages = manager.get_messages(group_id, limit=5)
                context_parts = [
                    f"## ROLE\n{system_prompt}\n",
                    f"## GROUP: {group.get('name', 'Team Chat')}\n",
                ]

                # Add chain context if other agents have responded
                if previous_outputs:
                    context_parts.append("## PREVIOUS AGENT OUTPUTS")
                    for agent_name, output in previous_outputs.items():
                        context_parts.append(f"[{agent_name}]: {output[:400]}...")
                    context_parts.append("")

                # Add recent conversation
                context_parts.append("## RECENT CONVERSATION")
                for msg in recent_messages:
                    msg_content = msg.get("content", "")[:200]
                    context_parts.append(f"[{msg.get('sender_id')}]: {msg_content}")

                # Current request
                context_parts.append(f"\n## CURRENT REQUEST\n{content}")

                # Phase 95: ARC Integration - Group Chat Suggestions
                try:
                    from src.agents.arc_solver_agent import ARCSolverAgent

                    # Create ARC solver instance
                    arc_solver = ARCSolverAgent(use_api=False, learner=None)

                    # Build minimal graph data from group context
                    graph_data = {
                        "nodes": [{"id": agent_id, "type": "agent"} for agent_id in group.get("participants", {}).keys()],
                        "edges": []
                    }

                    # Get ARC suggestions
                    arc_result = arc_solver.suggest_connections(
                        workflow_id=group_id,
                        graph_data=graph_data,
                        task_context=content,
                        num_candidates=5,
                        min_score=0.5
                    )

                    # Add top suggestions to context
                    top_suggestions = arc_result.get("top_suggestions", [])
                    if top_suggestions:
                        context_parts.append("\n## ARC SUGGESTED IMPROVEMENTS")
                        for idx, suggestion in enumerate(top_suggestions[:3], 1):
                            score = suggestion.get("score", 0.0)
                            explanation = suggestion.get("explanation", "No explanation")
                            context_parts.append(f"{idx}. {explanation} (confidence: {score:.2f})")
                        print(f"[ARC_GROUP] Added {len(top_suggestions[:3])} suggestions to group context")
                except Exception as arc_err:
                    # Non-critical: continue even if ARC fails
                    print(f"[ARC_GROUP] ARC integration failed: {arc_err}")

                prompt = "\n".join(context_parts)

                # Phase 57.4: Use orchestrator.call_agent() for proper Elisya integration
                print(
                    f"[GROUP_DEBUG] Calling orchestrator.call_agent('{agent_type}', model='{model_id}')"
                )
                call_start = time.time()

                try:
                    result = await asyncio.wait_for(
                        orchestrator.call_agent(
                            agent_type=agent_type,
                            model_id=model_id,
                            prompt=prompt,
                            context={
                                "group_id": group_id,
                                "group_name": group["name"],
                                "agent_id": agent_id,
                                "display_name": display_name,
                            },
                        ),
                        timeout=120.0,  # 2 minute timeout
                    )
                except asyncio.TimeoutError:
                    print(f"[GROUP_ERROR] Timeout after 120s calling {agent_type}")
                    result = {"status": "error", "error": "Timeout after 120 seconds"}

                call_elapsed = time.time() - call_start
                print(
                    f"[GROUP_DEBUG] call_agent returned in {call_elapsed:.2f}s, status={result.get('status')}"
                )

                if result.get("status") == "done":
                    response_text = result.get("output", "")
                else:
                    response_text = f"[Error: {result.get('error', 'Unknown error')}]"

                print(f"[GROUP_DEBUG] Response length: {len(response_text)} chars")

                # Phase 57.7: Store for chain context (next agents see this output)
                previous_outputs[display_name] = response_text[:500]

                # Store agent response in group
                agent_message = await manager.send_message(
                    group_id=group_id,
                    sender_id=agent_id,
                    content=response_text,
                    message_type="response",
                    metadata={"in_reply_to": user_message.id},
                )

                # Emit stream end with full response
                await sio.emit(
                    "group_stream_end",
                    {
                        "id": msg_id,
                        "group_id": group_id,
                        "agent_id": agent_id,
                        "full_message": response_text,
                        "metadata": {"model": model_id, "agent_type": agent_type},
                    },
                    room=f"group_{group_id}",
                )

                # Broadcast agent response
                if agent_message:
                    await sio.emit(
                        "group_message",
                        agent_message.to_dict(),
                        room=f"group_{group_id}",
                    )

                    # MARKER_108_3_SOCKETIO_UPDATE: Phase 108.3 - Real-time chat node updates
                    # Emit chat_node_update when agent responds (activity update)
                    from datetime import datetime
                    await sio.emit(
                        "chat_node_update",
                        {
                            "chat_id": group_id,
                            "decay_factor": 1.0,  # Agent response = activity
                            "last_activity": datetime.now().isoformat(),
                            "message_count": len(manager.get_messages(group_id, limit=1000)),
                        },
                        room=f"group_{group_id}",
                    )

                # Phase 80.28: Track last responder for smart reply decay
                if group_object and result.get("status") == "done":
                    group_object.last_responder_id = agent_id
                    group_object.last_responder_decay = (
                        0  # Reset decay after successful response
                    )
                    print(
                        f"[GROUP_DEBUG] Phase 80.28: last_responder={agent_id}, decay reset to 0"
                    )

                # Phase 74.8: Save agent response to chat_history
                # MARKER_CHAT_HISTORY_ATTRIBUTION: Model attribution fix - IMPLEMENTED
                try:
                    chat_history = get_chat_history_manager()
                    group_name = group.get("name", f"Group {group_id[:8]}")
                    chat_id = chat_history.get_or_create_chat(
                        file_path="unknown",
                        context_type="group",
                        display_name=group_name,
                    )
                    chat_history.add_message(
                        chat_id,
                        {
                            "role": "assistant",
                            "content": response_text,
                            "agent": display_name,
                            "model": model_id,
                            "model_provider": provider_name,  # Provider attribution for model disambiguation
                            "metadata": {"group_id": group_id},
                        },
                    )
                except Exception as chat_err:
                    print(
                        f"[GROUP_CHAT] Error saving agent response to chat_history: {chat_err}"
                    )

                # MARKER_103.6_START: Auto-stage artifacts from Dev/Architect
                # Staging pattern: Dev generates code → stage in JSON → QA review → apply to disk
                # MARKER_103_ARTIFACT_LINK: Added source_message_id for traceability
                try:
                    # Only stage for code-generating agents
                    if display_name in ["Dev", "Architect", "Coder"]:
                        from src.utils.artifact_extractor import extract_artifacts, extract_qa_score
                        from src.utils.staging_utils import stage_artifacts_batch

                        artifacts = extract_artifacts(response_text, display_name)
                        if artifacts:
                            qa_score = extract_qa_score(response_text) or 0.5  # Default moderate

                            staged_ids = stage_artifacts_batch(
                                artifacts=artifacts,
                                qa_score=qa_score,
                                agent=display_name,
                                group_id=group_id,
                                source_message_id=user_message.id  # Link to source message
                            )

                            if staged_ids:
                                print(f"[STAGING] {len(staged_ids)} artifacts staged from {display_name}")

                                # Emit socket event for UI notification
                                await sio.emit(
                                    "artifacts_staged",
                                    {
                                        "group_id": group_id,
                                        "agent": display_name,
                                        "count": len(staged_ids),
                                        "task_ids": staged_ids,
                                        "qa_score": qa_score,
                                    },
                                    room=f"group_{group_id}",
                                )
                except Exception as staging_err:
                    # Graceful degradation - don't block message flow
                    print(f"[STAGING] Error (non-blocking): {staging_err}")
                # MARKER_103.6_END

                # MARKER_103.7_START: Persist agent response to Qdrant for long-term memory
                # MARKER_103_GC7: FIXED - wrapped in background task to avoid blocking
                import uuid as uuid_module
                msg_id = str(uuid_module.uuid4())

                async def _persist_to_qdrant_background():
                    """Background task for Qdrant persistence - non-blocking."""
                    try:
                        from src.memory.qdrant_client import upsert_chat_message
                        upsert_chat_message(
                            group_id=group_id,
                            message_id=msg_id,
                            sender_id=agent_id,
                            content=response_text,
                            role="assistant",
                            agent=display_name,
                            model=model_id,
                            metadata={"in_reply_to": user_message.id if user_message else None}
                        )
                        # Emit socket event for UI sync
                        await sio.emit(
                            "message_saved",
                            {"group_id": group_id, "message_id": msg_id, "success": True},
                            room=f"group_{group_id}",
                        )
                    except Exception as qdrant_err:
                        print(f"[QDRANT] Chat upsert failed (non-blocking): {qdrant_err}")

                # Fire-and-forget: don't await, let it run in background
                asyncio.create_task(_persist_to_qdrant_background())
                # MARKER_103.7_END

                print(f"[GROUP] Agent {agent_id} responded: {len(response_text)} chars")

                # Phase 57.8: Check for @mentions in agent response to trigger other agents
                # MARKER_108_ROUTING_FIX_4: Support hyphenated model names
                agent_mentions = re.findall(r"@([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)", response_text)
                if agent_mentions:
                    print(
                        f"[GROUP_DEBUG] Agent {display_name} mentioned: {agent_mentions}"
                    )

                    for mentioned_name in agent_mentions:
                        # Skip self-mentions and already-responded agents
                        if mentioned_name.lower() == display_name.lower():
                            continue
                        if mentioned_name in previous_outputs:
                            continue

                        # Find mentioned agent in participants
                        mentioned_participant = None
                        for pid, pdata in group.get("participants", {}).items():
                            pname = pdata.get("display_name", "").lower()
                            agent_id = pdata.get("agent_id", "").lstrip("@").lower()
                            mentioned_lower = mentioned_name.lower()

                            # Strategy 1: Exact display_name match
                            if pname == mentioned_lower:
                                mentioned_participant = pdata
                                break
                            # Strategy 2: Match agent_id
                            if agent_id == mentioned_lower:
                                mentioned_participant = pdata
                                break
                            # Strategy 3: Match display_name prefix (before parentheses)
                            if (
                                "(" in pname
                                and pname.split("(")[0].strip() == mentioned_lower
                            ):
                                mentioned_participant = pdata
                                break

                        if not mentioned_participant:
                            print(
                                f"[GROUP_DEBUG] ⚠️ Agent '{mentioned_name}' NOT FOUND in group participants"
                            )

                        if (
                            mentioned_participant
                            and mentioned_participant.get("role") != "observer"
                        ):
                            # Check if agent is already in queue (by agent_id)
                            already_queued = any(
                                p.get("agent_id")
                                == mentioned_participant.get("agent_id")
                                for p in participants_to_respond
                            )
                            if not already_queued:
                                participants_to_respond.append(mentioned_participant)
                                print(
                                    f"[GROUP_DEBUG] Added {mentioned_name} to responders from agent @mention (queue size: {len(participants_to_respond)})"
                                )

            except Exception as e:
                print(f"[GROUP] Error calling agent {agent_id}: {e}")
                # Emit stream end with error
                await sio.emit(
                    "group_stream_end",
                    {
                        "id": msg_id,
                        "group_id": group_id,
                        "agent_id": agent_id,
                        "full_message": "",
                        "error": str(e)[:100],
                    },
                    room=f"group_{group_id}",
                )

                error_msg = await manager.send_message(
                    group_id=group_id,
                    sender_id=agent_id,
                    content=f"[Error: {str(e)[:100]}]",
                    message_type="error",
                )
                if error_msg:
                    await sio.emit(
                        "group_message", error_msg.to_dict(), room=f"group_{group_id}"
                    )

        # Phase 57.8.2: REMOVED Hostess summary - она слишком медленная
        # Hostess теперь получает весь контекст пассивно для:
        # - Наведения камеры (camera_focus)
        # - Навигации по дереву
        # - Future: контекст ветки
        # Но НЕ участвует в активной координации

    @sio.on("group_typing")
    async def handle_group_typing(sid, data):
        """Broadcast typing indicator to group."""
        group_id = data.get("group_id")
        agent_id = data.get("agent_id")
        if group_id and agent_id:
            await sio.emit(
                "group_typing",
                {"group_id": group_id, "agent_id": agent_id},
                room=f"group_{group_id}",
                skip_sid=sid,
            )
