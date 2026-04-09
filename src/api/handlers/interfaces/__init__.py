"""
VETKA Interfaces - Base Protocols for Message Handler Refactoring.

Defines core interfaces for the user_message_handler refactoring.
All dependencies are injected via these protocols for testability and decoupling.

Interfaces:
- IContextProvider: Build LLM context from files, viewport, pinned files
- IModelClient: Call Ollama/OpenRouter models
- IAgentExecutor: Execute agent chains (PM/Dev/QA)
- IHostessRouter: Route messages via Hostess agent
- IResponseEmitter: Emit responses to Socket.IO clients
- ISummaryGenerator: Generate summaries for multi-agent responses
- IMentionParser: Parse @mention directives
- ISessionManager: Manage per-session state

@status: active
@phase: 96
@depends: typing, abc
@used_by: context.context_builders, models.model_client, mention.mention_handler, routing.hostess_router
"""

from typing import Protocol, Dict, Any, List, Optional, Tuple
from abc import ABC, abstractmethod


# =============================================================================
# CONTEXT BUILDING INTERFACES
# =============================================================================


class IContextProvider(Protocol):
    """
    Interface for building LLM context from various sources.

    Consolidates context building logic that was repeated 3x in the original code
    (lines 254-291, 399-436, 638-675).
    """

    async def build_context(
        self,
        node_path: str,
        text: str,
        pinned_files: List[Dict[str, Any]],
        viewport_context: Optional[Dict[str, Any]],
        session_id: str,
        model_name: str,
        max_history: int = 10,
    ) -> Dict[str, Any]:
        """
        Build complete context for LLM call.

        Returns:
        {
            'file_context': str,          # File content context
            'pinned_context': str,        # Pinned files context
            'history_context': str,       # Chat history context
            'viewport_summary': str,      # Viewport spatial context
            'json_context': str,          # JSON dependency context
            'model_prompt': str           # Final assembled prompt
        }
        """
        ...


# =============================================================================
# MODEL CLIENT INTERFACES
# =============================================================================


class IModelClient(Protocol):
    """
    Interface for calling LLM models (Ollama, OpenRouter).

    Extracts the MASSIVE 374-line model call block (lines 227-601).
    """

    async def call_model(
        self,
        model_name: str,
        prompt: str,
        session_id: str,
        node_id: str,
        node_path: str,
        streaming: bool = True,
        max_tokens: int = 999999,  # Unlimited responses
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Call a model and return response.

        Returns:
        {
            'success': bool,
            'response_text': str,
            'tokens_input': int,
            'tokens_output': int,
            'model_used': str,
            'error': Optional[str]
        }
        """
        ...

    def is_local_model(self, model_name: str) -> bool:
        """Check if model is local Ollama."""
        ...


# =============================================================================
# AGENT EXECUTION INTERFACES
# =============================================================================


class IAgentExecutor(Protocol):
    """
    Interface for executing agent chains.

    Extracts the 188-line agent loop (lines 1317-1505).
    """

    async def execute_agents(
        self,
        agents_to_call: List[str],
        text: str,
        context: Dict[str, Any],
        single_mode: bool,
        session_id: str,
        node_id: str,
        node_path: str,
    ) -> List[Dict[str, Any]]:
        """
        Execute agent chain and return responses.

        Returns list of:
        {
            'agent': str,
            'model': str,
            'text': str,
            'node_id': str,
            'node_path': str,
            'timestamp': float,
            'artifacts': List[Dict],  # For Dev agent
            'qa_score': Optional[float]  # For QA agent
        }
        """
        ...


# =============================================================================
# ROUTING INTERFACES
# =============================================================================


class IHostessRouter(Protocol):
    """
    Interface for Hostess agent routing logic.

    Extracts the 403-line routing block (lines 912-1315).
    """

    async def route_message(
        self, text: str, node_path: str, client_id: str, session_id: str, node_id: str
    ) -> Dict[str, Any]:
        """
        Route message via Hostess agent.

        Returns:
        {
            'action': str,  # 'quick_answer', 'agent_call', 'chain_call', etc.
            'agents_to_call': List[str],
            'response_text': Optional[str],
            'confidence': float,
            'metadata': Dict[str, Any]
        }
        """
        ...


# =============================================================================
# RESPONSE EMISSION INTERFACES
# =============================================================================


class IResponseEmitter(Protocol):
    """
    Interface for emitting responses to Socket.IO clients.

    Consolidates response emission logic.
    """

    async def emit_agent_response(
        self,
        session_id: str,
        agent_name: str,
        model_name: str,
        text: str,
        node_id: str,
        node_path: str,
        timestamp: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit agent response to client."""
        ...

    async def emit_stream_token(self, session_id: str, msg_id: str, token: str) -> None:
        """Emit streaming token to client."""
        ...

    async def emit_error(self, session_id: str, error: str) -> None:
        """Emit error to client."""
        ...


class ISummaryGenerator(Protocol):
    """
    Interface for generating summaries.

    Extracts summary generation logic (lines 1515-1665).
    """

    async def generate_summary(
        self,
        responses: List[Dict[str, Any]],
        session_id: str,
        node_id: str,
        node_path: str,
    ) -> str:
        """Generate summary from multiple agent responses."""
        ...


# =============================================================================
# PARSING INTERFACES
# =============================================================================


class IMentionParser(Protocol):
    """
    Interface for parsing @mention directives.

    Wraps existing parse_mentions() function.
    """

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse @mentions from text.

        Returns:
        {
            'mentions': List[Dict],
            'agents': List[str],
            'models': List[str],
            'mode': str,  # 'single', 'agents', 'multi'
            'clean_message': str
        }
        """
        ...


# =============================================================================
# SESSION STATE INTERFACES
# =============================================================================


class ISessionManager(Protocol):
    """
    Interface for managing per-session state.

    Replaces global pending_api_keys dict (line 46).
    """

    def set_pending_api_key(self, session_id: str, key: str) -> None:
        """Store pending API key for session."""
        ...

    def get_pending_api_key(self, session_id: str) -> Optional[str]:
        """Get pending API key for session."""
        ...

    def clear_pending_api_key(self, session_id: str) -> None:
        """Clear pending API key for session."""
        ...

    def has_pending_api_key(self, session_id: str) -> bool:
        """Check if session has pending API key."""
        ...


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "IContextProvider",
    "IModelClient",
    "IAgentExecutor",
    "IHostessRouter",
    "IResponseEmitter",
    "ISummaryGenerator",
    "IMentionParser",
    "ISessionManager",
]
