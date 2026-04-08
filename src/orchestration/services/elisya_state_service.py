"""
Elisya State Management Service

Handles:
- ElisyaState creation and management
- State updates via middleware
- Semantic path generation
- Conversation history management

@status: active
@phase: 96
@depends: src.elisya.state, src.elisya.middleware, src.elisya.semantic_path, src.mcp.state
@used_by: src.orchestration.orchestrator_with_elisya, src.api.handlers.chat_handler
"""

from typing import Dict, Any, Optional, List
from src.elisya.state import ElisyaState
from src.elisya.middleware import ElisyaMiddleware, MiddlewareConfig
from src.elisya.semantic_path import get_path_generator


class ElisyaStateService:
    """Manages ElisyaState instances for workflows."""

    def __init__(self, memory_manager=None):
        """
        Initialize Elisya state service.

        Args:
            memory_manager: MemoryManager instance for Qdrant integration
        """
        # State storage (per workflow)
        self.elisya_states: Dict[str, ElisyaState] = {}

        # Initialize middleware
        self.middleware = ElisyaMiddleware(
            config=MiddlewareConfig(
                enable_few_shots=True,
                enable_semantic_tint=True,
                enable_qdrant_search=True,
                truncate_by_lod=True,
                max_history_tokens=1500,
                few_shot_threshold=0.8,
                qdrant_search_limit=5
            ),
            memory_manager=memory_manager
        )
        print(f"   • Elisya Middleware: initialized with Qdrant integration")

        # Initialize semantic path generator
        self.path_generator = get_path_generator()
        print(f"   • Semantic Path Generator: initialized")

    def get_or_create_state(self, workflow_id: str, feature: str) -> ElisyaState:
        """
        Get or create ElisyaState for workflow.

        Args:
            workflow_id: Workflow identifier
            feature: Feature request text

        Returns:
            ElisyaState instance
        """
        if workflow_id not in self.elisya_states:
            # Generate semantic path from feature
            semantic_path = self.path_generator.generate(
                task=feature,
                context="workflow initialization"
            )

            # Create state
            state = ElisyaState(
                workflow_id=workflow_id,
                semantic_path=semantic_path,
                raw_context=feature,
                original_request={'feature': feature}
            )

            self.elisya_states[workflow_id] = state
            print(f"   📝 ElisyaState created for {workflow_id}")
            print(f"      Path: {semantic_path}")

        return self.elisya_states[workflow_id]

    def update_state(self, state: ElisyaState, speaker: str, output: str) -> ElisyaState:
        """
        Update ElisyaState after agent execution.

        Args:
            state: Current ElisyaState
            speaker: Agent name
            output: Agent's output text

        Returns:
            Updated ElisyaState
        """
        # Use middleware to update state
        state = self.middleware.update(state, output, speaker)

        # Update semantic path if needed
        state.semantic_path = self.path_generator.generate(
            task=state.original_request.get('feature', ''),
            history=[msg.content for msg in state.conversation_history[-3:]]
        )

        return state

    def reframe_context(self, state: ElisyaState, agent_type: str) -> ElisyaState:
        """
        Reframe context for specific agent.

        Args:
            state: Current ElisyaState
            agent_type: Agent name

        Returns:
            ElisyaState with reframed context
        """
        return self.middleware.reframe(state, agent_type)

    def get_state(self, workflow_id: str) -> Optional[Dict]:
        """
        Get ElisyaState for workflow as dict.

        Args:
            workflow_id: Workflow identifier

        Returns:
            State dict or None if not found
        """
        if workflow_id not in self.elisya_states:
            return None

        state = self.elisya_states[workflow_id]
        return state.to_dict()

    def get_operation_stats(self) -> Dict[str, Any]:
        """
        Get middleware operation statistics.

        Returns:
            Dict with operation stats
        """
        return self.middleware.get_operation_stats()

    async def get_arc_gaps(self, task: str, workflow_id: str) -> List[Dict[str, Any]]:
        """
        ARC: Query MCP memory for conceptual gaps.

        Finds similar concepts from previous workflow states
        to suggest connections and fill knowledge gaps.

        Integration Points:
        - ARC-002: semantic_path comparison
        - ARC-004: Qdrant similarity search
        - ARC-005: MemoryManager.get_similar_context()
        """
        gaps = []

        try:
            from src.mcp.state import get_mcp_state_manager
            mcp = get_mcp_state_manager()

            all_states = await mcp.get_all_states(prefix=workflow_id)
            recent_states = await mcp.get_all_states(limit=50)

            task_keywords = set(task.lower().split())
            task_keywords.discard("the")
            task_keywords.discard("a")
            task_keywords.discard("an")

            for agent_id, state_data in recent_states.items():
                if agent_id.startswith(workflow_id):
                    continue

                state_text = str(state_data).lower()
                matches = sum(1 for kw in task_keywords if kw in state_text)
                score = matches / max(len(task_keywords), 1)

                if score > 0.3:
                    semantic_path = state_data.get("semantic_path", "")
                    if not semantic_path and "elisya_state" in state_data:
                        semantic_path = state_data["elisya_state"].get("semantic_path", "")

                    gaps.append({
                        "concept": semantic_path or agent_id,
                        "from_agent": agent_id,
                        "score": round(score, 2),
                        "suggestion": f"Related context from {agent_id}"
                    })

            gaps.sort(key=lambda x: x["score"], reverse=True)
            return gaps[:5]

        except Exception as e:
            print(f"   ⚠️ ARC gap detection failed: {e}")
            return []

    def inject_arc_gaps_to_prompt(self, prompt: str, arc_gaps: List[Dict[str, Any]]) -> str:
        """
        Inject ARC gaps into agent prompt.
        """
        if not arc_gaps:
            return prompt

        arc_section = "\n\n## Related Concepts (ARC Suggestions):\n"
        for gap in arc_gaps:
            arc_section += f"- {gap['concept']} (relevance: {gap['score']:.0%})\n"

        return prompt + arc_section
