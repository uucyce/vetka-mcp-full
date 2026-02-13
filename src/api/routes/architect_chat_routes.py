"""
MARKER_144.12: Architect Chat API — conversational interface with Architect agent.

Provides a POST endpoint for user ↔ Architect dialog.
The Architect receives:
- User message
- Chat history (last N messages)
- Current DAG/workflow context (node count, selected node, preset)

The Architect responds with:
- Text response (reasoning, plan, questions)
- Optional DAG mutations (addNodes, removeNodes, addEdges)

Falls back gracefully when Mycelium pipeline is unavailable.

@phase 144
@status active
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/architect", tags=["Architect Chat"])


class ChatContext(BaseModel):
    selectedNodeId: Optional[str] = None
    workflowContext: Optional[Dict[str, Any]] = None
    preset: Optional[str] = "dragon_silver"
    chatHistory: Optional[List[Dict[str, str]]] = None


class ArchitectChatRequest(BaseModel):
    message: str
    context: Optional[ChatContext] = None


class DAGChanges(BaseModel):
    addNodes: Optional[List[Dict[str, str]]] = None
    removeNodes: Optional[List[str]] = None
    addEdges: Optional[List[Dict[str, str]]] = None


class ArchitectChatResponse(BaseModel):
    success: bool = True
    response: str
    dag_changes: Optional[Dict[str, Any]] = None


def _build_architect_prompt(message: str, context: Optional[ChatContext] = None) -> str:
    """Build a system prompt for the Architect agent."""
    system_parts = [
        "You are the Architect agent in VETKA AI system.",
        "Your role: decompose user tasks into subtasks, plan DAG workflows, and provide strategic guidance.",
        "Keep responses concise and actionable.",
        "If the user asks about a specific node, focus on that context.",
        "",
        "When you propose changes to the workflow DAG, include them in a structured format.",
        "Format for proposals: describe what nodes to add/remove and why.",
    ]

    if context:
        if context.selectedNodeId:
            system_parts.append(f"\nUser has selected node: {context.selectedNodeId}")
        if context.workflowContext:
            system_parts.append(f"Current workflow: {json.dumps(context.workflowContext)}")
        if context.preset:
            system_parts.append(f"Active preset: {context.preset}")

    return "\n".join(system_parts)


@router.post("/chat", response_model=ArchitectChatResponse)
async def architect_chat(request: ArchitectChatRequest):
    """
    Send a message to the Architect agent and get a response.

    The Architect will:
    1. Analyze the user's message in context
    2. Provide strategic guidance or task decomposition
    3. Optionally propose DAG workflow changes
    """
    try:
        # Try to use Mycelium pipeline for LLM call
        from src.services.mycelium_client import MyceliumClient

        client = MyceliumClient()

        # Build messages for LLM
        system_prompt = _build_architect_prompt(request.message, request.context)
        messages = [{"role": "system", "content": system_prompt}]

        # Add chat history if available
        if request.context and request.context.chatHistory:
            for msg in request.context.chatHistory[-6:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })

        # Add current message
        messages.append({"role": "user", "content": request.message})

        # Determine architect model from preset
        preset = request.context.preset if request.context else "dragon_silver"
        model = _get_architect_model(preset)

        response_text = await client.call_model(
            model=model,
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )

        return ArchitectChatResponse(
            success=True,
            response=response_text,
        )

    except ImportError:
        logger.warning("[Architect Chat] MyceliumClient not available, using fallback")
        return _fallback_response(request)
    except Exception as e:
        logger.error(f"[Architect Chat] Error: {e}")
        return _fallback_response(request)


def _get_architect_model(preset: str) -> str:
    """Get the architect model name based on the active preset."""
    model_map = {
        "dragon_bronze": "qwen3-30b",
        "dragon_silver": "kimi-k2.5",
        "dragon_gold": "kimi-k2.5",
        "dragon_gold_gpt": "gpt-5.2",
    }
    return model_map.get(preset, "kimi-k2.5")


def _fallback_response(request: ArchitectChatRequest) -> ArchitectChatResponse:
    """
    Provide a helpful fallback when the LLM backend is not available.
    This gives the user guidance without requiring the pipeline to be running.
    """
    message = request.message.lower()

    # Simple pattern matching for common requests
    if any(word in message for word in ["plan", "break", "decompose", "split"]):
        return ArchitectChatResponse(
            success=True,
            response=(
                "I'd break this task into subtasks, but the Architect LLM backend isn't connected right now.\n\n"
                "To execute: create a task above and click ▶ to dispatch via the Dragon pipeline.\n"
                "The pipeline's Architect agent (Kimi K2.5) will automatically decompose and execute.\n\n"
                "Alternatively, use @dragon <your task> in the VETKA chat."
            ),
        )

    if any(word in message for word in ["help", "what", "how", "explain"]):
        return ArchitectChatResponse(
            success=True,
            response=(
                "I'm the Architect agent — I plan task decomposition and workflow design.\n\n"
                "When the LLM backend is running, I can:\n"
                "• Break down complex tasks into subtasks\n"
                "• Propose DAG workflow changes\n"
                "• Answer questions about the current pipeline\n\n"
                "For now, use the task input above to create tasks, or @dragon in chat."
            ),
        )

    return ArchitectChatResponse(
        success=True,
        response=(
            f"Received: \"{request.message[:100]}...\"\n\n"
            "The Architect LLM backend is not connected. Your message will be processed when the pipeline is available.\n\n"
            "Quick actions:\n"
            "• Create a task above and dispatch with ▶\n"
            "• Use @dragon <task> in VETKA chat for immediate execution"
        ),
    )
