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

MARKER_144.12B: Uses call_model_v2 directly (replaced broken MyceliumClient).
Falls back gracefully when LLM provider is unavailable.

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

    MARKER_144.12B: Uses call_model_v2 directly (replaces broken MyceliumClient).
    Provider auto-detected from model prefix (moonshotai/ → POLZA).
    """
    try:
        from src.elisya.provider_registry import call_model_v2

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

        # Determine architect model + provider from preset
        preset = request.context.preset if request.context else "dragon_silver"
        model, provider_source = _get_architect_model_v2(preset)

        logger.info(f"[Architect Chat] Calling {model} via {provider_source} (preset={preset})")

        result = await call_model_v2(
            messages=messages,
            model=model,
            source=provider_source,
            max_tokens=1024,
            temperature=0.7,
        )

        # Extract text from standardized response dict
        # call_model_v2 returns: {"message": {"role": "assistant", "content": "..."}, ...}
        response_text = ""
        if isinstance(result, dict):
            msg = result.get("message", {})
            if isinstance(msg, dict):
                response_text = msg.get("content", "")
            elif isinstance(msg, str):
                response_text = msg
        elif isinstance(result, str):
            response_text = result

        if not response_text:
            logger.warning("[Architect Chat] Empty response from LLM, using fallback")
            return _fallback_response(request)

        return ArchitectChatResponse(
            success=True,
            response=response_text,
        )

    except Exception as e:
        logger.error(f"[Architect Chat] LLM error: {e}")
        return _fallback_response(request)


def _get_architect_model_v2(preset: str) -> tuple:
    """
    Get architect model + provider source from preset.
    MARKER_144.12B: Fully qualified model names for call_model_v2 routing.
    Returns (model_id, provider_source).
    """
    # Load from model_presets.json dynamically (same as workflow_architect.py)
    try:
        from pathlib import Path
        presets_path = Path(__file__).parent.parent.parent.parent / "data" / "templates" / "model_presets.json"
        if presets_path.exists():
            data = json.loads(presets_path.read_text(encoding="utf-8"))
            presets = data.get("presets", {})
            if preset in presets:
                model = presets[preset]["roles"].get("architect", "moonshotai/kimi-k2.5")
                provider = presets[preset].get("provider", "polza")
                return (model, provider)
    except Exception as e:
        logger.warning(f"[Architect Chat] Failed to load preset config: {e}")

    # Fallback hardcoded map
    fallback = {
        "dragon_bronze": ("qwen/qwen3-30b-a3b", "polza"),
        "dragon_silver": ("moonshotai/kimi-k2.5", "polza"),
        "dragon_gold": ("moonshotai/kimi-k2.5", "polza"),
        "dragon_gold_gpt": ("moonshotai/kimi-k2.5", "polza"),
        "titan_lite": ("qwen/qwen3-30b-a3b", "polza"),
        "titan_core": ("google/gemini-3-pro-preview", "polza"),
        "titan_prime": ("anthropic/claude-opus-4.6", "polza"),
        "quality": ("anthropic/claude-opus-4.6", "polza"),
    }
    return fallback.get(preset, ("moonshotai/kimi-k2.5", "polza"))


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
