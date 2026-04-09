"""
VETKA Dependency Injection Container.

Wires all extracted modules together for clean dependency injection.

Architecture:
- ContextBuilder: Build LLM context from files, viewport, pinned files
- ModelClient: Call Ollama/OpenRouter models
- MentionHandler: Parse @mentions and route to models
- HostessRouter: Route via Hostess agent
- AgentOrchestrator: Execute agent chains (PM/Dev/QA)
- ResponseManager: Emit responses to Socket.IO clients

All dependencies are explicitly injected, making testing and refactoring trivial.

@status: active
@phase: 96
@depends: context.context_builders, models.model_client, mention.mention_handler, routing.hostess_router, orchestration.agent_orchestrator, orchestration.response_manager
@used_by: user_message_handler_v2
"""

from typing import Dict, Any
from src.chat.chat_registry import ChatRegistry, Message
from src.chat.chat_history_manager import get_chat_history_manager
from src.api.handlers.handler_utils import (
    save_chat_message,
    get_agents,
    ROLE_PROMPTS_AVAILABLE,
)
from src.api.handlers.message_utils import build_pinned_context
from src.api.handlers.streaming_handler import stream_response
from src.utils.artifact_extractor import extract_artifacts, extract_qa_score, extract_qa_verdict
from src.orchestration.cam_event_handler import emit_cam_event
from src.elisya.api_aggregator_v3 import HOST_HAS_OLLAMA
from src.agents.role_prompts import build_full_prompt

# Import all extracted modules
from .context.context_builders import ContextBuilder
from .models.model_client import ModelClient
from .mention.mention_handler import MentionHandler
from .routing.hostess_router import HostessRouter
from .orchestration.agent_orchestrator import AgentOrchestrator
from .orchestration.response_manager import ResponseManager


class HandlerContainer:
    """
    Dependency injection container for user_message_handler.

    Wires all extracted modules together with proper dependencies.
    This eliminates the 1694-line God Object antipattern.
    """

    def __init__(self, sio, app=None):
        """
        Initialize container with Socket.IO server.

        Args:
            sio: Socket.IO AsyncServer instance
            app: Optional Flask/Sanic app reference
        """
        self.sio = sio
        self.app = app

        # Initialize all components
        self._init_components()

    def _init_components(self):
        """Initialize all components with dependency injection."""

        # 1. Context Builder (no dependencies)
        self.context_builder = ContextBuilder()

        # 2. Model Client (depends on: sio, context_builder)
        self.model_client = ModelClient(
            sio=self.sio,
            context_builder=self.context_builder
        )

        # 3. Mention Handler (depends on: sio)
        self.mention_handler = MentionHandler(sio=self.sio)

        # 4. Hostess Router (depends on: sio)
        self.hostess_router = HostessRouter(sio_emitter=self.sio)

    def create_orchestrator(self, sid: str) -> AgentOrchestrator:
        """
        Create AgentOrchestrator for a specific session.

        Args:
            sid: Socket.IO session ID

        Returns:
            Configured AgentOrchestrator instance
        """
        return AgentOrchestrator(
            sio=self.sio,
            sid=sid,
            build_full_prompt_func=build_full_prompt,
            build_pinned_context_func=build_pinned_context,
            stream_response_func=stream_response,
            extract_artifacts_func=extract_artifacts,
            extract_qa_score_func=extract_qa_score,
            extract_qa_verdict_func=extract_qa_verdict,
            ROLE_PROMPTS_AVAILABLE=ROLE_PROMPTS_AVAILABLE,
            HOST_HAS_OLLAMA=HOST_HAS_OLLAMA
        )

    def create_response_manager(self, sid: str) -> ResponseManager:
        """
        Create ResponseManager for a specific session.

        Args:
            sid: Socket.IO session ID

        Returns:
            Configured ResponseManager instance
        """
        chat_manager = ChatRegistry.get_manager(sid)

        return ResponseManager(
            sio=self.sio,
            sid=sid,
            chat_manager=chat_manager,
            Message=Message,
            save_chat_message_func=save_chat_message,
            get_chat_history_manager_func=get_chat_history_manager,
            emit_cam_event_func=emit_cam_event,
            get_agents_func=get_agents
        )


# =============================================================================
# SINGLETON CONTAINER INSTANCE
# =============================================================================

_container_instance = None


def get_container(sio=None, app=None) -> HandlerContainer:
    """
    Get singleton HandlerContainer instance.

    Args:
        sio: Socket.IO server (required on first call)
        app: Optional Flask/Sanic app

    Returns:
        HandlerContainer singleton instance
    """
    global _container_instance

    if _container_instance is None:
        if sio is None:
            raise ValueError("sio is required to initialize container")
        _container_instance = HandlerContainer(sio, app)

    return _container_instance


def reset_container():
    """Reset container singleton (for testing)."""
    global _container_instance
    _container_instance = None
