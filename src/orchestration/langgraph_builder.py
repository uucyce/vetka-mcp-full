"""
VETKA LangGraph Graph Builder
Declarative workflow definition

@file langgraph_builder.py
@status ACTIVE
@phase Phase 60.1 - LangGraph Foundation
@calledBy orchestrator_with_elisya.py
@lastAudit 2026-01-10

This module provides the declarative graph definition for VETKA workflows.
It replaces imperative orchestration with LangGraph's declarative approach.

Graph Structure:
    START → Hostess → [Architect → PM → Dev+QA → Eval]
                                          ↓
                                  score >= 0.75?
                                  ↙         ↘
                                YES          NO
                                 ↓            ↓
                             Approval    Learner (retry<3)
                                 ↓            ↓
                                END    Back to Dev+QA
"""

import logging
from typing import TYPE_CHECKING, Optional, Dict, Any, AsyncIterator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.orchestration.langgraph_state import VETKAState, create_initial_state
from src.orchestration.langgraph_nodes import VETKANodes
from src.orchestration.event_types import WorkflowEventEmitter

if TYPE_CHECKING:
    from src.orchestration.orchestrator_with_elisya import OrchestratorWithElisya
    from src.orchestration.vetka_saver import VETKASaver
    from socketio import AsyncServer

logger = logging.getLogger(__name__)


class VETKAGraphBuilder:
    """
    Builds the LangGraph workflow for VETKA.

    This is the DECLARATIVE definition that replaces imperative orchestration.
    The graph is compiled once and can be invoked multiple times with different
    initial states.

    Usage:
        builder = VETKAGraphBuilder(nodes)
        app = builder.compile()
        result = await app.ainvoke(initial_state, config)
    """

    # Score threshold for passing evaluation
    EVAL_THRESHOLD = 0.75

    def __init__(
        self,
        nodes: VETKANodes,
        checkpointer=None
    ):
        """
        Initialize graph builder.

        Args:
            nodes: VETKANodes instance with node implementations
            checkpointer: Optional checkpointer (VETKASaver or MemorySaver)
        """
        self.nodes = nodes
        self.checkpointer = checkpointer or MemorySaver()
        self.graph = None
        self.app = None

        logger.info("[LangGraph] VETKAGraphBuilder initialized")

    def build(self) -> StateGraph:
        """
        Build the LangGraph workflow.

        Flow:
            START → hostess → [architect → pm → dev_qa → eval]
                                                    ↓
                                            score >= 0.75?
                                            ↙         ↘
                                          YES          NO
                                           ↓            ↓
                                       approval    learner (retry<3)
                                           ↓            ↓
                                          END    Back to dev_qa

        Returns:
            StateGraph: Built (but not compiled) graph
        """
        logger.info("[LangGraph] Building workflow graph...")

        # Create graph with state type
        builder = StateGraph(VETKAState)

        # ===========================
        # ADD NODES
        # ===========================

        builder.add_node("hostess", self.nodes.hostess_node)
        builder.add_node("architect", self.nodes.architect_node)
        builder.add_node("pm", self.nodes.pm_node)
        builder.add_node("hope_enhancement", self.nodes.hope_enhancement_node)  # Phase 76.2
        builder.add_node("dev_qa_parallel", self.nodes.dev_qa_parallel_node)
        builder.add_node("eval", self.nodes.eval_node)
        builder.add_node("learner", self.nodes.learner_node)
        builder.add_node("approval", self.nodes.approval_node)

        logger.info("[LangGraph] Added 8 nodes: hostess, architect, pm, hope_enhancement, dev_qa_parallel, eval, learner, approval")

        # ===========================
        # SET ENTRY POINT
        # ===========================

        builder.set_entry_point("hostess")

        # ===========================
        # ADD EDGES
        # ===========================

        # Hostess → routing decision (conditional)
        builder.add_conditional_edges(
            "hostess",
            self._route_from_hostess,
            {
                "architect": "architect",
                "pm": "pm",
                "dev_qa_parallel": "dev_qa_parallel",
                "end": END
            }
        )

        # Architect → PM
        builder.add_edge("architect", "pm")

        # PM → HOPE Enhancement → Dev+QA parallel (Phase 76.2)
        builder.add_edge("pm", "hope_enhancement")
        builder.add_edge("hope_enhancement", "dev_qa_parallel")

        # Dev+QA → Eval
        builder.add_edge("dev_qa_parallel", "eval")

        # Eval → conditional (approval or learner)
        builder.add_conditional_edges(
            "eval",
            self._route_from_eval,
            {
                "approval": "approval",
                "learner": "learner"
            }
        )

        # Learner → back to Dev+QA (RETRY CYCLE!)
        builder.add_edge("learner", "dev_qa_parallel")

        # Approval → END
        builder.add_edge("approval", END)

        logger.info("[LangGraph] Graph edges configured")

        self.graph = builder
        return builder

    def compile(self):
        """
        Compile the graph with checkpointer.

        Returns:
            Compiled LangGraph app ready for invocation
        """
        if self.graph is None:
            self.build()

        self.app = self.graph.compile(checkpointer=self.checkpointer)
        logger.info("[LangGraph] Graph compiled with checkpointer")

        return self.app

    # ===========================
    # ROUTING FUNCTIONS
    # ===========================

    def _route_from_hostess(self, state: VETKAState) -> str:
        """
        Route based on Hostess decision.

        The 'next' field is set by hostess_node based on:
        - @mentions → specific agent
        - Simple question → end
        - Complex task → architect
        """
        next_node = state.get('next', 'architect')

        # Map any unexpected values to safe defaults
        valid_nodes = {'architect', 'pm', 'dev_qa_parallel', 'end'}
        if next_node not in valid_nodes:
            logger.warning(f"[LangGraph] Invalid hostess route: {next_node}, defaulting to architect")
            return "architect"

        return next_node

    def _route_from_eval(self, state: VETKAState) -> str:
        """
        Route based on EvalAgent score.

        Threshold: 0.75 (optimal from Grok research)

        Decision logic:
        - score >= 0.75 → approval (success!)
        - score < 0.75 AND retries < max → learner (retry)
        - score < 0.75 AND retries >= max → approval (with warning)
        """
        score = state.get('eval_score', 0)
        retry_count = state.get('retry_count', 0)
        max_retries = state.get('max_retries', 3)

        if score >= self.EVAL_THRESHOLD:
            return "approval"
        elif retry_count < max_retries:
            return "learner"
        else:
            # Max retries reached, proceed anyway
            return "approval"

    # ===========================
    # EXECUTION METHODS
    # ===========================

    async def invoke(
        self,
        initial_state: VETKAState,
        config: Optional[Dict] = None
    ) -> VETKAState:
        """
        Execute the workflow.

        Args:
            initial_state: Starting state
            config: LangGraph config (thread_id for persistence)

        Returns:
            Final state after workflow completion
        """
        if self.app is None:
            self.compile()

        config = config or {"configurable": {"thread_id": initial_state['workflow_id']}}

        logger.info(f"[LangGraph] Starting workflow: {initial_state['workflow_id']}")

        result = await self.app.ainvoke(initial_state, config)

        logger.info(f"[LangGraph] Workflow complete: score={result.get('eval_score', 0):.2f}, retries={result.get('retry_count', 0)}")

        return result

    async def stream(
        self,
        initial_state: VETKAState,
        config: Optional[Dict] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream workflow execution (for real-time updates).

        Yields (node_name, state) tuples as workflow progresses.
        Useful for Socket.IO streaming to frontend.

        Args:
            initial_state: Starting state
            config: LangGraph config

        Yields:
            Dict with {node_name: state} as each node completes
        """
        if self.app is None:
            self.compile()

        config = config or {"configurable": {"thread_id": initial_state['workflow_id']}}

        logger.info(f"[LangGraph] Starting streaming workflow: {initial_state['workflow_id']}")

        async for event in self.app.astream(initial_state, config):
            yield event

    def get_graph_visualization(self) -> str:
        """
        Get ASCII visualization of the graph.

        Returns:
            ASCII art representation of the graph
        """
        if self.app is None:
            self.compile()

        try:
            return self.app.get_graph().draw_ascii()
        except Exception as e:
            logger.warning(f"[LangGraph] Could not draw graph: {e}")
            return """
            VETKA LangGraph Workflow
            ========================

            START
              │
              ▼
            [hostess] ─────┬──────────────────┐
              │            │                  │
              ▼            ▼                  ▼
            [architect] [pm] ───────► [dev_qa] ◄─┐
              │                          │       │
              └──────────────────────────┤       │
                                         ▼       │
                                       [eval]    │
                                         │       │
                                   ┌─────┴─────┐ │
                                   ▼           ▼ │
                              [approval]  [learner]
                                   │           │
                                   ▼           └──┘
                                  END
            """


# ===========================
# FACTORY FUNCTION
# ===========================

def create_vetka_graph(
    orchestrator: "OrchestratorWithElisya",
    use_persistent_checkpointer: bool = True,
    sio: "AsyncServer" = None
):
    """
    Factory function to create VETKA LangGraph workflow.

    Args:
        orchestrator: OrchestratorWithElisya instance with services
        use_persistent_checkpointer: Use VETKASaver (True) or MemorySaver (False)
        sio: python-socketio AsyncServer for event streaming (Phase 60.2)

    Returns:
        Compiled LangGraph app ready for invocation

    Usage:
        app = create_vetka_graph(orchestrator, sio=sio)
        result = await app.ainvoke(initial_state, config)
    """
    logger.info("[LangGraph] Creating VETKA graph...")

    # Create event emitter for Socket.IO streaming (Phase 60.2)
    event_emitter = WorkflowEventEmitter(sio=sio, namespace='/workflow')

    # Create nodes with orchestrator dependencies and event emitter
    nodes = VETKANodes(orchestrator=orchestrator, event_emitter=event_emitter)

    # Create checkpointer
    if use_persistent_checkpointer:
        try:
            from src.orchestration.vetka_saver import VETKASaver
            checkpointer = VETKASaver(
                memory_manager=orchestrator.memory_service.memory
            )
            logger.info("[LangGraph] Using VETKASaver checkpointer")
        except Exception as e:
            logger.warning(f"[LangGraph] VETKASaver not available: {e}, using MemorySaver")
            checkpointer = MemorySaver()
    else:
        checkpointer = MemorySaver()
        logger.info("[LangGraph] Using MemorySaver checkpointer")

    # Build and compile
    builder = VETKAGraphBuilder(nodes, checkpointer)
    app = builder.compile()

    logger.info(f"[LangGraph] VETKA graph created and compiled (event_emitter={'enabled' if sio else 'disabled'})")

    return app


def create_vetka_graph_builder(
    orchestrator: "OrchestratorWithElisya",
    use_persistent_checkpointer: bool = True,
    sio: "AsyncServer" = None
) -> VETKAGraphBuilder:
    """
    Factory function that returns the builder (not just compiled app).

    Useful when you need access to builder methods like stream().

    Args:
        orchestrator: OrchestratorWithElisya instance
        use_persistent_checkpointer: Use VETKASaver (True) or MemorySaver (False)
        sio: python-socketio AsyncServer for event streaming (Phase 60.2)

    Returns:
        VETKAGraphBuilder instance (compiled)
    """
    # Create event emitter for Socket.IO streaming (Phase 60.2)
    event_emitter = WorkflowEventEmitter(sio=sio, namespace='/workflow')

    # Create nodes with event emitter
    nodes = VETKANodes(orchestrator=orchestrator, event_emitter=event_emitter)

    if use_persistent_checkpointer:
        try:
            from src.orchestration.vetka_saver import VETKASaver
            checkpointer = VETKASaver(
                memory_manager=orchestrator.memory_service.memory
            )
        except Exception:
            checkpointer = MemorySaver()
    else:
        checkpointer = MemorySaver()

    builder = VETKAGraphBuilder(nodes, checkpointer)
    builder.compile()

    return builder
