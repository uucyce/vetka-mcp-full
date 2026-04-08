"""
VETKA LangGraph State Definition
Unified state for all LangGraph workflows

@file langgraph_state.py
@status ACTIVE
@phase Phase 99 - STM Buffer Integration (prev: 75.5 Spatial Context)
@calledBy langgraph_builder.py, langgraph_nodes.py, orchestrator_with_elisya.py
@lastAudit 2026-01-28

This module defines VETKAState - the unified state object that flows through
all LangGraph nodes. It combines:
- ElisyaState fields (context, semantic_path, LOD)
- Workflow tracking (current_agent, agent_outputs)
- Phase 29 Self-Learning (eval_score, retry_count, lessons_learned)
- Group Chat (participants, mentions)
- CAM Memory (surprise_scores, cam_operations)
"""

from typing import TypedDict, Annotated, Sequence, List, Dict, Optional, Any
from operator import add
from dataclasses import dataclass, field
from datetime import datetime

# Graceful import for langchain_core (allows tests without full langgraph install)
try:
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    # Fallback: create mock message classes for testing
    LANGCHAIN_AVAILABLE = False

    class BaseMessage:
        """Mock BaseMessage for testing without langchain_core."""
        def __init__(self, content: str, name: str = None):
            self.content = content
            self.name = name

    class HumanMessage(BaseMessage):
        """Mock HumanMessage for testing without langchain_core."""
        pass

    class AIMessage(BaseMessage):
        """Mock AIMessage for testing without langchain_core."""
        pass


class VETKAState(TypedDict):
    """
    Unified state for LangGraph workflow.

    Combines ElisyaState + workflow data + Phase 29 learning.
    This is the SINGLE SOURCE OF TRUTH during workflow execution.

    Key Design Decisions:
    - Uses TypedDict for LangGraph compatibility
    - Messages accumulate via Annotated[..., add]
    - eval_score threshold is 0.75 (from Grok research)
    - max_retries defaults to 3
    """

    # === Core Identity ===
    workflow_id: str
    group_id: Optional[str]  # For group chat sessions

    # === Messages (accumulating via reducer) ===
    messages: Annotated[Sequence[BaseMessage], add]

    # === Elisya Context ===
    context: str                    # Reframed context for current agent
    raw_context: str                # Original unfiltered user request
    semantic_path: str              # Evolves during conversation (e.g., "projects/vetka/auth")
    lod_level: str                  # MICRO/SMALL/MEDIUM/LARGE/EPIC (Level of Detail)
    few_shots: List[Dict]           # Learning examples from memory

    # === Agent Tracking ===
    current_agent: str              # PM/Dev/QA/Architect/Hostess/Learner/EvalAgent
    agent_outputs: Dict[str, str]   # {agent_name: output_text}
    artifacts: List[Dict]           # Created artifacts [{type, path, content}]

    # === Task Management ===
    tasks: List[Dict]               # Decomposed tasks from Architect [{description, status}]
    current_task_index: int

    # === Evaluation (Phase 29) ===
    eval_score: float               # 0.0 - 1.0, threshold is 0.75
    eval_feedback: str              # Detailed feedback from EvalAgent
    retry_count: int                # Current retry attempt (0-based)
    max_retries: int                # Maximum retry attempts (default: 3)

    # === Learning (Phase 29 Self-Learning) ===
    failure_analysis: Optional[Dict]  # LearnerAgent output
    enhanced_prompt: Optional[str]    # Improved prompt for retry
    lessons_learned: List[Dict]       # Extracted lessons [{task, failure_reason, suggestion}]

    # === Routing ===
    next: str                       # Next node to execute (set by current node)

    # === Group Chat ===
    participants: List[str]         # Group members (agent types)
    mentions: List[str]             # @mentions parsed from message

    # === Memory (CAM) ===
    surprise_scores: Dict[str, float]  # {artifact_id: surprise_score}
    cam_operations: List[Dict]         # CAM actions taken [{action, target, timestamp}]

    # === Phase 99: Short-Term Memory Buffer ===
    stm_buffer: Optional[Dict[str, Any]]  # STM state {entries, max_size, decay_rate} - FIX_99.1

    # === Phase 75.5: Spatial Context (viewport + pinned files) ===
    viewport_context: Optional[Dict[str, Any]]      # 3D viewport state {focus_node, zoom, visible_files}
    pinned_files: Optional[List[Dict[str, Any]]]    # User-pinned files [{path, reason, timestamp}]
    code_context: Optional[Dict[str, Any]]          # Code operation context {last_file, operation, result}

    # === Phase 76.2: HOPE Analysis ===
    hope_analysis: Optional[Dict[str, Any]]         # Full HOPE analysis {low, mid, high, combined}
    hope_summary: Optional[str]                     # Combined summary for Dev context injection

    # === Metadata ===
    created_at: str                 # ISO format timestamp
    updated_at: str                 # ISO format timestamp
    vetka_checkpoint_id: Optional[str]    # For checkpoint recovery (renamed from checkpoint_id - reserved by LangGraph)


def create_initial_state(
    workflow_id: str,
    context: str,
    group_id: Optional[str] = None,
    participants: Optional[List[str]] = None,
    lod_level: str = "MEDIUM",
    max_retries: int = 3,
    # Phase 75.5: Spatial context parameters
    viewport_context: Optional[Dict[str, Any]] = None,
    pinned_files: Optional[List[Dict[str, Any]]] = None,
    code_context: Optional[Dict[str, Any]] = None,
) -> VETKAState:
    """
    Create initial state for LangGraph workflow.

    Args:
        workflow_id: Unique identifier for workflow
        context: User's request/query
        group_id: Optional group chat ID
        participants: Optional list of agent types in group
        lod_level: Level of Detail (MICRO/SMALL/MEDIUM/LARGE/EPIC)
        max_retries: Maximum retry attempts on low scores
        viewport_context: Phase 75.5 - 3D viewport state from frontend
        pinned_files: Phase 75.5 - User-pinned files for context
        code_context: Phase 75.5 - Code operation context

    Returns:
        VETKAState: Initialized state ready for graph execution

    Example:
        state = create_initial_state(
            workflow_id="calc-001",
            context="Create a calculator in Python",
            lod_level="MEDIUM",
            viewport_context={"focus_node": "src/main.py", "zoom": 2.0}
        )
    """
    now = datetime.now().isoformat()

    return VETKAState(
        # Core Identity
        workflow_id=workflow_id,
        group_id=group_id,

        # Messages
        messages=[HumanMessage(content=context)],

        # Elisya Context
        context=context,
        raw_context=context,
        semantic_path="",
        lod_level=lod_level,
        few_shots=[],

        # Agent Tracking
        current_agent="",
        agent_outputs={},
        artifacts=[],

        # Task Management
        tasks=[],
        current_task_index=0,

        # Evaluation (Phase 29)
        eval_score=0.0,
        eval_feedback="",
        retry_count=0,
        max_retries=max_retries,

        # Learning (Phase 29)
        failure_analysis=None,
        enhanced_prompt=None,
        lessons_learned=[],

        # Routing
        next="hostess",  # Default entry point

        # Group Chat
        participants=participants or [],
        mentions=[],

        # Memory (CAM)
        surprise_scores={},
        cam_operations=[],

        # Phase 99: STM Buffer (initialized as None, created on first use)
        stm_buffer=None,

        # Phase 75.5: Spatial Context
        viewport_context=viewport_context,
        pinned_files=pinned_files,
        code_context=code_context,

        # Phase 76.2: HOPE Analysis
        hope_analysis=None,
        hope_summary=None,

        # Metadata
        created_at=now,
        updated_at=now,
        vetka_checkpoint_id=None
    )


def state_to_elisya_dict(state: VETKAState) -> Dict[str, Any]:
    """
    Convert VETKAState to ElisyaState-compatible dict.

    Used for backwards compatibility with existing agent code
    that expects ElisyaState.to_dict() format.

    Args:
        state: VETKAState from graph execution

    Returns:
        Dict compatible with ElisyaState.from_dict()
    """
    return {
        "workflow_id": state["workflow_id"],
        "speaker": state["current_agent"] or "PM",
        "semantic_path": state["semantic_path"],
        "context": state["context"],
        "lod_level": state["lod_level"].lower() if state["lod_level"] else "tree",
        "tint": "general",  # Default tint
        "conversation_history": [
            {
                "speaker": msg.name if hasattr(msg, 'name') and msg.name else ("user" if isinstance(msg, HumanMessage) else "assistant"),
                "content": msg.content,
                "timestamp": datetime.now().timestamp(),
                "metadata": {}
            }
            for msg in state.get("messages", [])
        ],
        "few_shots": state.get("few_shots", []),
        "timestamp": datetime.now().timestamp(),
        "retry_count": state.get("retry_count", 0),
        "score": state.get("eval_score", 0.0),
    }


def update_state_timestamp(state: VETKAState) -> VETKAState:
    """
    Update the updated_at timestamp in state.

    Should be called after any state modification.

    Args:
        state: Current state

    Returns:
        Updated state with new timestamp
    """
    state["updated_at"] = datetime.now().isoformat()
    return state


# ============ STATE HELPERS ============

def get_last_message_content(state: VETKAState) -> str:
    """Get content of the last message in state."""
    messages = state.get("messages", [])
    if messages:
        return messages[-1].content
    return state.get("context", "")


def add_agent_message(state: VETKAState, agent_name: str, content: str) -> List[BaseMessage]:
    """
    Add an agent's message to the message list.

    Note: Returns new list due to TypedDict immutability pattern.
    Use: state["messages"] = add_agent_message(state, "Dev", output)

    Args:
        state: Current state
        agent_name: Name of the agent (PM, Dev, QA, etc.)
        content: Agent's output

    Returns:
        New messages list with added message
    """
    return list(state.get("messages", [])) + [AIMessage(content=content, name=agent_name)]


def should_retry(state: VETKAState, threshold: float = 0.75) -> bool:
    """
    Check if workflow should retry based on eval score.

    Threshold is 0.75 based on Grok research for optimal quality/cost balance.

    Args:
        state: Current state
        threshold: Score threshold (default 0.75)

    Returns:
        True if retry should happen
    """
    score = state.get("eval_score", 0)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    return score < threshold and retry_count < max_retries


def get_workflow_summary(state: VETKAState) -> Dict[str, Any]:
    """
    Get a summary of workflow state for logging/debugging.

    Args:
        state: Current state

    Returns:
        Summary dict with key metrics
    """
    return {
        "workflow_id": state.get("workflow_id"),
        "current_agent": state.get("current_agent"),
        "eval_score": state.get("eval_score"),
        "retry_count": state.get("retry_count"),
        "agents_completed": list(state.get("agent_outputs", {}).keys()),
        "tasks_count": len(state.get("tasks", [])),
        "artifacts_count": len(state.get("artifacts", [])),
        "lessons_count": len(state.get("lessons_learned", [])),
        "next": state.get("next"),
    }
