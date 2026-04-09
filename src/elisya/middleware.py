"""
ElisyaMiddleware: reframe() + update() operations for context filtering.

Phase 15-3: Added Qdrant integration via MemoryManager for semantic search.

@status: active
@phase: 96
@depends: typing, dataclasses, time, enum
@used_by: orchestrator_with_elisya, agents
"""

from typing import Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass
import time
from enum import Enum

# Lazy import to avoid circular dependencies
if TYPE_CHECKING:
    from src.orchestration.memory_manager import MemoryManager


class ContextAction(Enum):
    """Actions middleware can perform"""
    REFRAME = "reframe"
    UPDATE = "update"
    TRUNCATE = "truncate"
    ENRICH = "enrich"


class LODLevel(Enum):
    """Level of Detail for context filtering"""
    GLOBAL = "global"      # Minimal context (500 tokens)
    TREE = "tree"          # Branch-level (1500 tokens)
    LEAF = "leaf"          # Full agent context (3000 tokens)
    FULL = "full"          # Complete history (10000 tokens)


@dataclass
class MiddlewareConfig:
    """Configuration for middleware behavior"""
    enable_few_shots: bool = True
    enable_semantic_tint: bool = True  # ✅ Built-in via _apply_tint_filter()
    enable_qdrant_search: bool = True  # ✅ Phase 15-3: Enable semantic search via Qdrant
    truncate_by_lod: bool = True
    max_history_tokens: int = 1500
    few_shot_threshold: float = 0.8
    qdrant_search_limit: int = 5  # ✅ Phase 15-3: Number of similar results to fetch
    # NOTE: SemanticTint is not a separate class - it's implemented in _apply_tint_filter()


class ElisyaMiddleware:
    """
    Middleware for context reframing and state updates.

    Two main operations:
    1. reframe(state, agent_type) - Prepare context for agent
    2. update(state, output, speaker) - Update state after agent execution

    Phase 15-3: Added Qdrant integration via MemoryManager for semantic search
    - fetch_similar_context() queries Qdrant for relevant history
    - Enriches agent context with semantically similar past outputs
    """

    def __init__(self, config: Optional[MiddlewareConfig] = None, memory_manager=None):
        self.config = config or MiddlewareConfig()
        self.operation_log: List[Dict] = []
        self._memory_manager = memory_manager  # ✅ Phase 15-3: Optional MemoryManager for Qdrant

    def set_memory_manager(self, memory_manager):
        """
        Phase 15-3: Set MemoryManager for Qdrant semantic search.
        Can be called after initialization to avoid circular imports.
        """
        self._memory_manager = memory_manager
        print(f"[ElisyaMiddleware] ✅ MemoryManager connected for Qdrant search")
    
    def reframe(self, state, agent_type: str):
        """
        Reframe context for specific agent.

        Steps:
        1. Fetch history from state's semantic_path
        2. Truncate by LOD (Level of Detail)
        3. Add few-shots if available (score > threshold)
        4. Apply semantic tint filter
        5. ✅ Phase 15-3: Fetch similar context from Qdrant
        6. Return reframed state
        """
        self._log_operation("reframe", {"agent_type": agent_type})

        # Step 1: Get base context (Phase 57.6: ensure not None)
        base_context = state.raw_context or state.context or ''

        # Step 2: Truncate by LOD
        if self.config.truncate_by_lod:
            base_context = self._truncate_by_lod(base_context, state.lod_level)

        # Step 3: Add few-shots
        few_shots_text = ""
        if self.config.enable_few_shots and state.few_shots:
            few_shots_text = self._format_few_shots(state.few_shots, agent_type)

        # Step 4: Apply semantic tint filter
        tint_context = ""
        if self.config.enable_semantic_tint:
            tint_context = self._apply_tint_filter(base_context, state.tint)
        else:
            tint_context = base_context

        # ✅ Step 5 (Phase 15-3): Fetch similar context from Qdrant
        qdrant_context = ""
        if self.config.enable_qdrant_search:
            qdrant_context = self._fetch_qdrant_context(
                query=base_context[:500],  # Use first 500 chars as query
                agent_type=agent_type,
                limit=self.config.qdrant_search_limit
            )

        # Step 6: Assemble reframed context
        state.context = f"""[HISTORY]
{tint_context}

[FEW_SHOTS]
{few_shots_text}

[SIMILAR_CONTEXT]
{qdrant_context}

[AGENT_FOCUS]
You are {agent_type}. Use history, examples, and similar context above.
"""

        return state
    
    def update(self, state, agent_output: str, speaker: str):
        """
        Update state after agent execution.
        
        Steps:
        1. Append message to conversation_history
        2. Generate/update semantic_path
        3. Update speaker and timestamp
        4. Return updated state
        """
        self._log_operation("update", {"speaker": speaker, "output_len": len(agent_output)})
        
        # Step 1: Add to history
        state.add_message(speaker, agent_output)
        
        # Step 2: Update semantic_path (will be done by semantic_path generator)
        # For now, keep existing path and mark it as evolved
        state.semantic_path = state.semantic_path or "projects/unknown"
        
        # Step 3: Update metadata
        state.speaker = speaker
        state.timestamp = time.time()
        
        return state
    
    def _truncate_by_lod(self, text: str, lod_level: str) -> str:
        """Truncate text by Level of Detail"""
        lod_limits = {
            "global": 500,
            "tree": 1500,
            "leaf": 3000,
            "full": 10000,
        }
        
        limit = lod_limits.get(lod_level.lower(), 1500)
        
        # Rough token count: 1 token ≈ 4 characters
        char_limit = limit * 4
        
        if len(text) <= char_limit:
            return text
        
        # Truncate and try to preserve sentence boundary
        truncated = text[:char_limit]
        last_period = truncated.rfind('.')
        
        if last_period > char_limit * 0.8:
            return truncated[:last_period + 1]
        
        return truncated + "..."
    
    def _format_few_shots(self, few_shots: List, agent_type: str) -> str:
        """Format few-shot examples for agent"""
        relevant_shots = [fs for fs in few_shots if hasattr(fs, 'agent_type') and fs.agent_type == agent_type]
        
        if not relevant_shots:
            return "[No few-shots available]"
        
        formatted = ""
        for i, shot in enumerate(relevant_shots[:3], 1):  # Top 3 examples
            formatted += f"""
Example {i} (score: {shot.score:.2f}):
Task: {shot.task[:200]}
Output: {shot.output[:300]}
---
"""
        
        return formatted
    
    def _apply_tint_filter(self, text: str, tint: str) -> str:
        """Apply semantic tint filter to text"""
        tint_keywords = {
            "security": ["security", "auth", "encrypt", "token", "password", "permission"],
            "performance": ["performance", "latency", "cache", "optimize", "benchmark", "throughput"],
            "reliability": ["reliability", "retry", "failover", "error", "recovery", "monitoring"],
            "scalability": ["scalability", "distributed", "horizontal", "vertical", "cluster", "load"],
            "general": [],  # No filtering
        }
        
        if tint == "general":
            return text
        
        keywords = tint_keywords.get(tint.lower(), [])
        if not keywords:
            return text
        
        # Simple filtering: keep lines with tint keywords
        lines = text.split('\n')
        filtered = [line for line in lines if any(kw in line.lower() for kw in keywords)]
        
        return '\n'.join(filtered) if filtered else text
    
    def _fetch_qdrant_context(self, query: str, agent_type: str, limit: int = 5) -> str:
        """
        Phase 15-3: Fetch semantically similar context from Qdrant via MemoryManager.

        Args:
            query: Search query (usually first 500 chars of base context)
            agent_type: Current agent type (PM, Dev, QA, Architect)
            limit: Number of similar results to fetch

        Returns:
            str: Formatted similar context or "[No similar context found]"
        """
        if not self._memory_manager:
            return "[No Qdrant connection - MemoryManager not set]"

        try:
            # Call MemoryManager's semantic search
            results = self._memory_manager.get_similar_context(
                query=query,
                limit=limit
            )

            if not results:
                return "[No similar context found in Qdrant]"

            # Format results for agent context
            formatted = []
            for i, result in enumerate(results, 1):
                speaker = result.get('speaker', 'unknown')
                content = result.get('content', '')[:300]  # Limit content length
                score = result.get('score', 0)
                workflow_id = result.get('workflow_id', 'unknown')

                formatted.append(
                    f"({i}) [{speaker}] (workflow: {workflow_id[:8]}): {content}..."
                )

            self._log_operation("qdrant_search", {
                "agent_type": agent_type,
                "results_count": len(results),
                "query_preview": query[:50]
            })

            print(f"[ElisyaMiddleware] ✅ Qdrant returned {len(results)} similar contexts for {agent_type}")

            return "\n".join(formatted)

        except Exception as e:
            print(f"[ElisyaMiddleware] ⚠️ Qdrant search failed: {e}")
            return f"[Qdrant search error: {str(e)[:50]}]"

    def _log_operation(self, operation: str, details: Dict):
        """Log middleware operation"""
        self.operation_log.append({
            "operation": operation,
            "details": details,
            "timestamp": time.time(),
        })
    
    def get_operation_stats(self) -> Dict:
        """Get statistics of middleware operations"""
        return {
            "total_operations": len(self.operation_log),
            "reframes": len([op for op in self.operation_log if op["operation"] == "reframe"]),
            "updates": len([op for op in self.operation_log if op["operation"] == "update"]),
        }
