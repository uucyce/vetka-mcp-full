# Phase 55.1 Implementation Prompt

**For:** Claude Opus/Sonnet Agents
**Task:** MCP + ARC Integration
**Reference:** PHASE_55.1_MCP_ARC_UNIFIED_MARKERS.md

---

## EXECUTION PLAN

### PHASE A: Core Infrastructure (3 Agents in Parallel)

---

### AGENT A1: MCPStateManager Core

**Task:** Create the core MCP state management system

**Create File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/state/mcp_state_manager.py`

**Reference Markers:** MCP-STATE-008, MCP-STATE-010, MCP-STATE-011, MCP-STATE-012

**Implementation:**

```python
"""
MCP State Manager - Phase 55.1
Manages agent workflow state with Qdrant persistence + LRU cache.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
import time
import asyncio
import hashlib
from collections import OrderedDict

# Qdrant imports
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

@dataclass
class MCPStateEntry:
    """Single state entry for an agent."""
    agent_id: str
    workflow_id: str
    data: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    ttl_seconds: int = 3600  # 1 hour default
    access_count: int = 0

class MCPStateManager:
    """
    MCP State Manager with Qdrant + LRU Cache.

    Features:
    - save_state(agent_id, data, ttl): Persist state
    - get_state(agent_id): Retrieve state (cache first)
    - update_state(agent_id, updates): Merge updates
    - delete_state(agent_id): Remove state
    - get_all_states(prefix): List states by workflow
    - delete_expired_states(): Cleanup TTL expired

    Integration Points:
    - MCP-STATE-008: Reuse Qdrant triple_write pattern
    - MCP-STATE-010: UUID5 collision-free IDs
    - MCP-STATE-011: Audit trail via changelog
    """

    COLLECTION_NAME = "vetka_mcp_states"
    VECTOR_SIZE = 768  # Match existing embeddings
    CACHE_MAX_SIZE = 100

    def __init__(self, collection_name: str = None):
        self.collection_name = collection_name or self.COLLECTION_NAME
        self._cache: OrderedDict[str, MCPStateEntry] = OrderedDict()
        self._qdrant: Optional[QdrantClient] = None
        self._init_qdrant()
        print(f"   • MCPStateManager: initialized (collection={self.collection_name})")

    def _init_qdrant(self):
        """Initialize Qdrant client and collection."""
        if not QDRANT_AVAILABLE:
            print("   ⚠️ Qdrant not available - using cache only")
            return
        try:
            from src.memory.qdrant_client import get_qdrant_client
            self._qdrant = get_qdrant_client()
            # Ensure collection exists
            # Collection creation handled by get_qdrant_client()
        except Exception as e:
            print(f"   ⚠️ Qdrant init failed: {e}")

    def _generate_point_id(self, agent_id: str) -> int:
        """Generate collision-free Qdrant point ID."""
        import uuid
        return uuid.uuid5(uuid.NAMESPACE_DNS, agent_id).int & 0x7FFFFFFFFFFFFFFF

    async def save_state(self, agent_id: str, data: Dict[str, Any],
                         ttl_seconds: int = 3600, workflow_id: str = None) -> bool:
        """Save agent state to cache and Qdrant."""
        entry = MCPStateEntry(
            agent_id=agent_id,
            workflow_id=workflow_id or agent_id.split("_")[0],
            data=data,
            ttl_seconds=ttl_seconds
        )

        # Update cache (LRU)
        if agent_id in self._cache:
            del self._cache[agent_id]
        self._cache[agent_id] = entry

        # Evict oldest if over limit
        while len(self._cache) > self.CACHE_MAX_SIZE:
            self._cache.popitem(last=False)

        # Persist to Qdrant
        if self._qdrant:
            try:
                point_id = self._generate_point_id(agent_id)
                # Use zero vector for state storage (non-semantic)
                vector = [0.0] * self.VECTOR_SIZE
                point = PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "agent_id": agent_id,
                        "workflow_id": entry.workflow_id,
                        "data": data,
                        "created_at": entry.created_at,
                        "updated_at": entry.updated_at,
                        "ttl_seconds": ttl_seconds,
                        "expires_at": entry.created_at + ttl_seconds
                    }
                )
                self._qdrant.upsert(
                    collection_name=self.collection_name,
                    points=[point]
                )
            except Exception as e:
                print(f"   ⚠️ Qdrant save failed: {e}")
                return False

        return True

    async def get_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get state from cache or Qdrant."""
        # Check cache first (O(1))
        if agent_id in self._cache:
            entry = self._cache[agent_id]
            # Check TTL
            if time.time() < entry.created_at + entry.ttl_seconds:
                entry.access_count += 1
                # Move to end (LRU)
                self._cache.move_to_end(agent_id)
                return entry.data
            else:
                # Expired
                del self._cache[agent_id]

        # Fallback to Qdrant
        if self._qdrant:
            try:
                point_id = self._generate_point_id(agent_id)
                results = self._qdrant.retrieve(
                    collection_name=self.collection_name,
                    ids=[point_id]
                )
                if results:
                    payload = results[0].payload
                    # Check TTL
                    if time.time() < payload.get("expires_at", 0):
                        # Warm cache
                        entry = MCPStateEntry(
                            agent_id=agent_id,
                            workflow_id=payload.get("workflow_id", ""),
                            data=payload.get("data", {}),
                            created_at=payload.get("created_at", time.time()),
                            ttl_seconds=payload.get("ttl_seconds", 3600)
                        )
                        self._cache[agent_id] = entry
                        return entry.data
            except Exception as e:
                print(f"   ⚠️ Qdrant get failed: {e}")

        return None

    async def update_state(self, agent_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Merge updates into existing state."""
        current = await self.get_state(agent_id)
        if current is None:
            current = {}

        # Deep merge
        merged = {**current, **updates}

        # Get TTL from cache or default
        ttl = 3600
        workflow_id = None
        if agent_id in self._cache:
            ttl = self._cache[agent_id].ttl_seconds
            workflow_id = self._cache[agent_id].workflow_id

        await self.save_state(agent_id, merged, ttl, workflow_id)
        return merged

    async def delete_state(self, agent_id: str) -> bool:
        """Delete state from cache and Qdrant."""
        # Remove from cache
        if agent_id in self._cache:
            del self._cache[agent_id]

        # Remove from Qdrant
        if self._qdrant:
            try:
                point_id = self._generate_point_id(agent_id)
                self._qdrant.delete(
                    collection_name=self.collection_name,
                    points_selector=[point_id]
                )
            except Exception as e:
                print(f"   ⚠️ Qdrant delete failed: {e}")
                return False

        return True

    async def get_all_states(self, prefix: str = None, limit: int = 100) -> Dict[str, Dict[str, Any]]:
        """Get all states, optionally filtered by prefix."""
        result = {}

        # From cache
        for agent_id, entry in self._cache.items():
            if prefix is None or agent_id.startswith(prefix):
                if time.time() < entry.created_at + entry.ttl_seconds:
                    result[agent_id] = entry.data

        # From Qdrant (if needed)
        if self._qdrant and len(result) < limit:
            try:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                scroll_filter = None
                if prefix:
                    scroll_filter = Filter(
                        must=[FieldCondition(
                            key="workflow_id",
                            match=MatchValue(value=prefix)
                        )]
                    )
                points, _ = self._qdrant.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=scroll_filter,
                    limit=limit
                )
                for point in points:
                    agent_id = point.payload.get("agent_id")
                    if agent_id and agent_id not in result:
                        if time.time() < point.payload.get("expires_at", 0):
                            result[agent_id] = point.payload.get("data", {})
            except Exception as e:
                print(f"   ⚠️ Qdrant scroll failed: {e}")

        return result

    async def delete_expired_states(self) -> int:
        """Delete all expired states. Returns count deleted."""
        deleted = 0
        now = time.time()

        # From cache
        expired_keys = [
            k for k, v in self._cache.items()
            if now >= v.created_at + v.ttl_seconds
        ]
        for k in expired_keys:
            del self._cache[k]
            deleted += 1

        # From Qdrant
        if self._qdrant:
            try:
                from qdrant_client.models import Filter, FieldCondition, Range
                # Find expired
                expired_filter = Filter(
                    must=[FieldCondition(
                        key="expires_at",
                        range=Range(lt=now)
                    )]
                )
                points, _ = self._qdrant.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=expired_filter,
                    limit=1000
                )
                if points:
                    ids = [p.id for p in points]
                    self._qdrant.delete(
                        collection_name=self.collection_name,
                        points_selector=ids
                    )
                    deleted += len(ids)
            except Exception as e:
                print(f"   ⚠️ Qdrant cleanup failed: {e}")

        print(f"   🧹 MCPStateManager: deleted {deleted} expired states")
        return deleted


# Singleton
_mcp_state_manager: Optional[MCPStateManager] = None

def get_mcp_state_manager() -> MCPStateManager:
    """Get singleton MCPStateManager instance."""
    global _mcp_state_manager
    if _mcp_state_manager is None:
        _mcp_state_manager = MCPStateManager()
    return _mcp_state_manager
```

**Also Create:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/state/__init__.py`
```python
"""MCP State Management Module - Phase 55.1"""
from .mcp_state_manager import MCPStateManager, get_mcp_state_manager

__all__ = ["MCPStateManager", "get_mcp_state_manager"]
```

**Test Command:**
```bash
python -c "from src.mcp.state import get_mcp_state_manager; m=get_mcp_state_manager(); import asyncio; asyncio.run(m.save_state('test_pm', {'plan': 'ok'})); print(asyncio.run(m.get_state('test_pm')))"
```

---

### AGENT A2: MCPStateBridge

**Task:** Create bridge between MCPStateManager and MemoryService

**Create File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/services/mcp_state_bridge.py`

**Reference Markers:** MCP-STATE-001, MCP-STATE-002, MCP-STATE-003, MCP-STATE-004

**Implementation:**

```python
"""
MCP State Bridge - Phase 55.1
Extends MemoryService with MCP granular agent state management.
"""

from typing import Dict, Any, Optional, List
import asyncio
from .memory_service import MemoryService


class MCPStateBridge(MemoryService):
    """
    Extends MemoryService with MCP granular state.

    Integration Points:
    - MCP-STATE-001: triple_write() hook
    - MCP-STATE-002: save_agent_output() hook
    - MCP-STATE-003: save_workflow_result() hook
    - MCP-STATE-004: save_performance_metrics() hook
    """

    def __init__(self):
        super().__init__()
        # Lazy import to avoid circular dependency
        self._mcp_state = None
        print("   • MCPStateBridge: initialized")

    @property
    def mcp_state(self):
        """Lazy load MCPStateManager."""
        if self._mcp_state is None:
            from src.mcp.state import get_mcp_state_manager
            self._mcp_state = get_mcp_state_manager()
        return self._mcp_state

    async def save_agent_state(self, workflow_id: str, agent_type: str,
                                output: str, elisya_state: Any = None,
                                ttl: int = 3600) -> bool:
        """
        Save agent state to MCP + triple-write.

        Args:
            workflow_id: Workflow identifier
            agent_type: Agent name (PM, Dev, QA, Architect)
            output: Agent's output text
            elisya_state: Optional ElisyaState for context
            ttl: Time-to-live in seconds
        """
        agent_id = f"{workflow_id}_{agent_type}"

        # Prepare state data
        state_data = {
            "output": output,
            "agent_type": agent_type,
            "workflow_id": workflow_id,
        }

        # Include ElisyaState if provided
        if elisya_state:
            if hasattr(elisya_state, "to_dict"):
                state_data["elisya_state"] = elisya_state.to_dict()
            elif hasattr(elisya_state, "semantic_path"):
                state_data["semantic_path"] = elisya_state.semantic_path
                state_data["conversation_history_len"] = len(
                    getattr(elisya_state, "conversation_history", [])
                )

        # Save to MCP
        await self.mcp_state.save_state(agent_id, state_data, ttl, workflow_id)

        # Also triple-write for persistence
        self.triple_write({
            "type": "mcp_agent_state",
            "agent_id": agent_id,
            "agent_type": agent_type,
            "workflow_id": workflow_id,
            "data": state_data
        })

        return True

    async def get_agent_state(self, workflow_id: str, agent_type: str) -> Optional[Dict[str, Any]]:
        """Get agent state from MCP."""
        agent_id = f"{workflow_id}_{agent_type}"
        return await self.mcp_state.get_state(agent_id)

    async def get_workflow_states(self, workflow_id: str) -> Dict[str, Dict[str, Any]]:
        """Get all agent states for a workflow."""
        return await self.mcp_state.get_all_states(prefix=workflow_id)

    async def merge_parallel_states(self, workflow_id: str,
                                     dev_state: Any, qa_state: Any) -> Dict[str, Any]:
        """
        Merge parallel Dev and QA states.

        Used after parallel execution (WORKFLOW-015).
        """
        merged = {
            "workflow_id": workflow_id,
            "parallel_execution": True,
            "dev": None,
            "qa": None
        }

        if dev_state:
            if hasattr(dev_state, "to_dict"):
                merged["dev"] = dev_state.to_dict()
            else:
                merged["dev"] = {"output": str(dev_state)}

        if qa_state:
            if hasattr(qa_state, "to_dict"):
                merged["qa"] = qa_state.to_dict()
            else:
                merged["qa"] = {"output": str(qa_state)}

        # Save merged state
        await self.mcp_state.save_state(
            f"{workflow_id}_parallel_merge",
            merged,
            ttl_seconds=3600,
            workflow_id=workflow_id
        )

        return merged

    async def publish_workflow_complete(self, workflow_id: str,
                                         result: Dict[str, Any],
                                         elisya_state: Any = None):
        """
        Publish workflow completion notification.

        Used at WORKFLOW-007.
        """
        complete_data = {
            "status": "complete",
            "workflow_id": workflow_id,
            "result_summary": {
                k: v[:200] if isinstance(v, str) else v
                for k, v in result.items()
                if k not in ("full_context", "raw_outputs")
            }
        }

        if elisya_state and hasattr(elisya_state, "semantic_path"):
            complete_data["final_semantic_path"] = elisya_state.semantic_path

        # Save with longer TTL for completed workflows
        await self.mcp_state.save_state(
            f"{workflow_id}_complete",
            complete_data,
            ttl_seconds=86400,  # 24 hours
            workflow_id=workflow_id
        )

        # Also save to persistent storage
        self.save_workflow_result(workflow_id, result)


# Singleton
_mcp_state_bridge: Optional[MCPStateBridge] = None

def get_mcp_state_bridge() -> MCPStateBridge:
    """Get singleton MCPStateBridge instance."""
    global _mcp_state_bridge
    if _mcp_state_bridge is None:
        _mcp_state_bridge = MCPStateBridge()
    return _mcp_state_bridge
```

**Update:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/services/__init__.py`
Add to exports:
```python
from .mcp_state_bridge import MCPStateBridge, get_mcp_state_bridge
```

---

### AGENT A3: ARC Gap Detector

**Task:** Add ARC conceptual gap detection to ElisyaStateService

**Modify File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/services/elisya_state_service.py`

**Reference Markers:** ARC-002, ARC-004, ARC-005

**Add After Line 120 (after reframe_context method):**

```python
    async def get_arc_gaps(self, task: str, workflow_id: str) -> List[Dict[str, Any]]:
        """
        ARC: Query MCP memory for conceptual gaps.

        Finds similar concepts from previous workflow states
        to suggest connections and fill knowledge gaps.

        Integration Points:
        - ARC-002: semantic_path comparison
        - ARC-004: Qdrant similarity search
        - ARC-005: MemoryManager.get_similar_context()

        Args:
            task: Current task description
            workflow_id: Current workflow ID

        Returns:
            List of gap suggestions with scores
        """
        gaps = []

        try:
            # Get MCP state manager
            from src.mcp.state import get_mcp_state_manager
            mcp = get_mcp_state_manager()

            # Get all states from this workflow
            all_states = await mcp.get_all_states(prefix=workflow_id)

            # Also query recent states from other workflows
            recent_states = await mcp.get_all_states(limit=50)

            # Simple similarity: check if task keywords appear in state data
            task_keywords = set(task.lower().split())
            task_keywords.discard("the")
            task_keywords.discard("a")
            task_keywords.discard("an")

            for agent_id, state_data in recent_states.items():
                # Skip same workflow
                if agent_id.startswith(workflow_id):
                    continue

                # Calculate simple keyword overlap
                state_text = str(state_data).lower()
                matches = sum(1 for kw in task_keywords if kw in state_text)
                score = matches / max(len(task_keywords), 1)

                if score > 0.3:  # Threshold for relevance
                    # Get semantic path if available
                    semantic_path = state_data.get("semantic_path", "")
                    if not semantic_path and "elisya_state" in state_data:
                        semantic_path = state_data["elisya_state"].get("semantic_path", "")

                    gaps.append({
                        "concept": semantic_path or agent_id,
                        "from_agent": agent_id,
                        "score": round(score, 2),
                        "suggestion": f"Related context from {agent_id}"
                    })

            # Sort by score
            gaps.sort(key=lambda x: x["score"], reverse=True)

            # Limit to top 5
            return gaps[:5]

        except Exception as e:
            print(f"   ⚠️ ARC gap detection failed: {e}")
            return []

    def inject_arc_gaps_to_prompt(self, prompt: str, arc_gaps: List[Dict[str, Any]]) -> str:
        """
        Inject ARC gaps into agent prompt.

        Args:
            prompt: Original prompt
            arc_gaps: List from get_arc_gaps()

        Returns:
            Enhanced prompt with ARC suggestions
        """
        if not arc_gaps:
            return prompt

        arc_section = "\n\n## Related Concepts (ARC Suggestions):\n"
        for gap in arc_gaps:
            arc_section += f"- {gap['concept']} (relevance: {gap['score']:.0%})\n"

        return prompt + arc_section
```

---

## PHASE B: Tool Registration (3 Agents - After Phase A)

### AGENT B1: Session Tools

**Create File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/session_tools.py`

**Reference Markers:** CHAT-001, CHAT-006, CHAT-009

```python
"""
MCP Session Tools - Phase 55.1
Fat session initialization with ELISION compression.
"""

from typing import Dict, Any, Optional, List


async def vetka_session_init(
    user_id: str = "default",
    group_id: Optional[str] = None,
    include_viewport: bool = True,
    include_pinned: bool = True,
    compress: bool = True,
    max_context_tokens: int = 4000
) -> Dict[str, Any]:
    """
    Initialize MCP session with fat context.

    Gathers:
    - User preferences from Engram
    - Viewport context (if available)
    - Pinned files
    - Recent conversation history
    - CAM activations

    Returns compressed context via ELISION.
    """
    from src.mcp.state import get_mcp_state_manager
    from src.memory.engram_user_memory import EngramUserMemory

    mcp = get_mcp_state_manager()
    session_id = f"session_{user_id}_{group_id or 'solo'}"

    context = {
        "session_id": session_id,
        "user_id": user_id,
        "group_id": group_id,
        "initialized": True,
    }

    # Get user preferences
    try:
        engram = EngramUserMemory()
        prefs = engram.get_all_preferences(user_id)
        if prefs:
            context["user_preferences"] = prefs
    except Exception as e:
        context["user_preferences_error"] = str(e)

    # Get recent MCP states
    try:
        recent = await mcp.get_all_states(limit=10)
        context["recent_states_count"] = len(recent)
    except Exception as e:
        context["recent_states_error"] = str(e)

    # Apply ELISION compression if requested
    if compress:
        try:
            from src.memory.jarvis_prompt_enricher import JarvisPromptEnricher
            enricher = JarvisPromptEnricher()
            compressed = enricher.compress_context(context)
            context["compressed"] = True
            context["compression_ratio"] = len(str(compressed)) / max(len(str(context)), 1)
        except Exception:
            context["compressed"] = False

    # Save session state
    await mcp.save_state(session_id, context, ttl_seconds=3600)

    return context


async def vetka_session_status(session_id: str) -> Dict[str, Any]:
    """Get current session status."""
    from src.mcp.state import get_mcp_state_manager
    mcp = get_mcp_state_manager()

    state = await mcp.get_state(session_id)
    if state:
        return {"exists": True, "session": state}
    return {"exists": False, "session_id": session_id}


def register_session_tools(tool_list: List[Dict[str, Any]]):
    """Register session tools with MCP bridge."""
    tool_list.extend([
        {
            "name": "vetka_session_init",
            "description": "Initialize MCP session with fat context and ELISION compression",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "default": "default"},
                    "group_id": {"type": "string"},
                    "include_viewport": {"type": "boolean", "default": True},
                    "compress": {"type": "boolean", "default": True}
                }
            },
            "handler": vetka_session_init
        },
        {
            "name": "vetka_session_status",
            "description": "Get current MCP session status",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "required": True}
                }
            },
            "handler": vetka_session_status
        }
    ])
```

---

### AGENT B2: Compound Tools

**Create File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/compound_tools.py`

**Reference Markers:** ARC-001, ARC-007

```python
"""
MCP Compound Tools - Phase 55.1
Multi-step tool compositions (search+read+summarize, etc).
"""

from typing import Dict, Any, List


async def vetka_research(topic: str, depth: str = "medium") -> Dict[str, Any]:
    """
    Research a topic: semantic search → read files → summarize.

    Args:
        topic: Research topic
        depth: "quick" (3 files), "medium" (7 files), "deep" (15 files)
    """
    from src.bridge import SemanticSearchTool, ReadFileTool

    limits = {"quick": 3, "medium": 7, "deep": 15}
    limit = limits.get(depth, 7)

    # Step 1: Semantic search
    search_tool = SemanticSearchTool()
    search_result = await search_tool.execute({"query": topic, "limit": limit})

    findings = []
    if "results" in search_result:
        # Step 2: Read top files
        read_tool = ReadFileTool()
        for item in search_result["results"][:limit]:
            file_path = item.get("path") or item.get("file_path")
            if file_path:
                try:
                    content = await read_tool.execute({"file_path": file_path})
                    findings.append({
                        "path": file_path,
                        "score": item.get("score", 0),
                        "content_preview": str(content)[:500]
                    })
                except Exception as e:
                    findings.append({"path": file_path, "error": str(e)})

    return {
        "topic": topic,
        "depth": depth,
        "files_searched": len(search_result.get("results", [])),
        "files_read": len(findings),
        "findings": findings
    }


async def vetka_implement(task: str, dry_run: bool = True) -> Dict[str, Any]:
    """
    Implement a task: plan → code → (optionally) write.

    Args:
        task: Implementation task description
        dry_run: If True, only preview changes
    """
    # This is a placeholder - actual implementation would use LLM
    return {
        "task": task,
        "dry_run": dry_run,
        "status": "requires_agent_execution",
        "suggestion": "Use vetka_execute_workflow for full implementation"
    }


async def vetka_review(file_path: str) -> Dict[str, Any]:
    """
    Review a file: read → analyze → suggest improvements.
    """
    from src.bridge import ReadFileTool

    read_tool = ReadFileTool()
    content = await read_tool.execute({"file_path": file_path})

    return {
        "file_path": file_path,
        "content_length": len(str(content)),
        "status": "requires_agent_analysis",
        "content_preview": str(content)[:1000]
    }


def register_compound_tools(tool_list: List[Dict[str, Any]]):
    """Register compound tools with MCP bridge."""
    tool_list.extend([
        {
            "name": "vetka_research",
            "description": "Research a topic: semantic search → read files → summarize",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "required": True},
                    "depth": {"type": "string", "enum": ["quick", "medium", "deep"], "default": "medium"}
                }
            },
            "handler": vetka_research
        },
        {
            "name": "vetka_implement",
            "description": "Plan implementation for a task (use workflow for execution)",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "required": True},
                    "dry_run": {"type": "boolean", "default": True}
                }
            },
            "handler": vetka_implement
        },
        {
            "name": "vetka_review",
            "description": "Review a file and suggest improvements",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "required": True}
                }
            },
            "handler": vetka_review
        }
    ])
```

---

### AGENT B3: Workflow Tools

**Create File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/workflow_tools.py`

**Reference Markers:** WORKFLOW-001..007

```python
"""
MCP Workflow Tools - Phase 55.1
Full workflow execution: PM → Architect → Dev → QA.
Uses existing Phase 60.1 LangGraph infrastructure.
"""

from typing import Dict, Any, List, Optional
import uuid


async def vetka_execute_workflow(
    request: str,
    workflow_type: str = "pm_to_qa",
    include_eval: bool = True,
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Execute full VETKA workflow.

    Workflow types:
    - "pm_to_qa": PM → Architect → Dev → QA (default)
    - "pm_only": Just PM planning
    - "dev_qa": Dev → QA (skip planning)

    Integration:
    - Uses orchestrator_with_elisya._execute_parallel()
    - Saves state via MCPStateBridge
    """
    workflow_id = f"wf_{uuid.uuid4().hex[:8]}"

    try:
        from src.orchestration.orchestrator_with_elisya import MultiAgentOrchestrator
        from src.orchestration.services import get_mcp_state_bridge

        orchestrator = MultiAgentOrchestrator()
        mcp_bridge = get_mcp_state_bridge()

        # Execute based on workflow type
        if workflow_type == "pm_to_qa":
            result = await orchestrator._execute_parallel(
                feature_request=request,
                execution_mode="orchestrator"
            )
        elif workflow_type == "pm_only":
            result = {"pm_plan": await orchestrator._run_pm_only(request)}
        else:
            result = {"error": f"Unknown workflow type: {workflow_type}"}

        # Save completion state
        await mcp_bridge.publish_workflow_complete(workflow_id, result)

        return {
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "status": "complete",
            "result": result
        }

    except Exception as e:
        return {
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "status": "error",
            "error": str(e)
        }


async def vetka_workflow_status(workflow_id: str) -> Dict[str, Any]:
    """Get status of a workflow."""
    from src.mcp.state import get_mcp_state_manager
    mcp = get_mcp_state_manager()

    # Get all states for this workflow
    states = await mcp.get_all_states(prefix=workflow_id)

    # Check for completion
    complete_state = await mcp.get_state(f"{workflow_id}_complete")

    return {
        "workflow_id": workflow_id,
        "is_complete": complete_state is not None,
        "agent_states": list(states.keys()),
        "completion_data": complete_state
    }


def register_workflow_tools(tool_list: List[Dict[str, Any]]):
    """Register workflow tools with MCP bridge."""
    tool_list.extend([
        {
            "name": "vetka_execute_workflow",
            "description": "Execute full VETKA workflow (PM → Architect → Dev → QA)",
            "parameters": {
                "type": "object",
                "properties": {
                    "request": {"type": "string", "required": True, "description": "Feature request"},
                    "workflow_type": {"type": "string", "enum": ["pm_to_qa", "pm_only", "dev_qa"], "default": "pm_to_qa"},
                    "include_eval": {"type": "boolean", "default": True},
                    "timeout": {"type": "integer", "default": 300}
                }
            },
            "handler": vetka_execute_workflow
        },
        {
            "name": "vetka_workflow_status",
            "description": "Get status of a workflow execution",
            "parameters": {
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "required": True}
                }
            },
            "handler": vetka_workflow_status
        }
    ])
```

---

## PHASE C: Hook Integration (3 Agents - After Phase A, B)

### AGENT C1: Orchestrator Hooks

**Modify File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/orchestrator_with_elisya.py`

**Add Import (after line ~50):**
```python
from src.orchestration.services import get_mcp_state_bridge
```

**Add After Line 1500 (after PM save):**
```python
            # Phase 55.1: MCP state hook
            try:
                mcp_bridge = get_mcp_state_bridge()
                await mcp_bridge.save_agent_state(workflow_id, "PM", pm_result, elisya_state)
            except Exception as e:
                print(f"   ⚠️ MCP PM state save failed: {e}")
```

**Add After Line 1533 (after Architect save):**
```python
            # Phase 55.1: MCP state hook
            try:
                mcp_bridge = get_mcp_state_bridge()
                await mcp_bridge.save_agent_state(workflow_id, "Architect", architect_result, elisya_state)
            except Exception as e:
                print(f"   ⚠️ MCP Architect state save failed: {e}")
```

**Add After Line 1652 (after parallel merge):**
```python
            # Phase 55.1: MCP parallel merge hook
            try:
                mcp_bridge = get_mcp_state_bridge()
                await mcp_bridge.merge_parallel_states(workflow_id, dev_state[0], qa_state[0])
            except Exception as e:
                print(f"   ⚠️ MCP parallel merge failed: {e}")
```

**Add After Line 1862 (at workflow complete):**
```python
            # Phase 55.1: MCP workflow complete hook
            try:
                mcp_bridge = get_mcp_state_bridge()
                await mcp_bridge.publish_workflow_complete(workflow_id, result, elisya_state)
            except Exception as e:
                print(f"   ⚠️ MCP workflow complete failed: {e}")
```

---

### AGENT C2: Chat Entry Hooks

**Modify File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py`

**Add Import (after line ~60):**
```python
from src.mcp.tools.session_tools import vetka_session_init
```

**Add After Line 245 (MARKER_94.5_SOLO_ENTRY):**
```python
        # Phase 55.1: MCP session init
        try:
            import asyncio
            session = await vetka_session_init(
                user_id=sid,
                group_id=None,
                compress=True
            )
            print(f"   [MCP] Solo session initialized: {session.get('session_id')}")
        except Exception as e:
            print(f"   ⚠️ MCP session init failed: {e}")
```

**Modify File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`

**Add Import (after imports):**
```python
from src.mcp.tools.session_tools import vetka_session_init
```

**Add After Line 541 (MARKER_94.5_GROUP_ENTRY):**
```python
    # Phase 55.1: MCP group session init
    try:
        session = await vetka_session_init(
            user_id=sender_id,
            group_id=group_id,
            compress=True
        )
        print(f"   [MCP] Group session initialized: {session.get('session_id')}")
    except Exception as e:
        print(f"   ⚠️ MCP group session init failed: {e}")
```

---

### AGENT C3: MCP Bridge Tool Registration

**Modify File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py`

**Add Imports (after line ~50):**
```python
# Phase 55.1: MCP tools registration
from src.mcp.tools.session_tools import register_session_tools
from src.mcp.tools.compound_tools import register_compound_tools
from src.mcp.tools.workflow_tools import register_workflow_tools
```

**Add to @server.list_tools() (after line ~584, before return):**
```python
    # Phase 55.1: Register new MCP tools
    mcp_tools = []
    register_session_tools(mcp_tools)
    register_compound_tools(mcp_tools)
    register_workflow_tools(mcp_tools)

    # Convert to MCP format
    for tool in mcp_tools:
        tools.append(Tool(
            name=tool["name"],
            description=tool["description"],
            inputSchema=tool["parameters"]
        ))
```

---

## PHASE D: Maintenance (1 Agent - After All)

### AGENT D1: CAM + Cleanup Scheduler

**Modify File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/initialization/components_init.py`

**Add Import (after imports):**
```python
import threading
```

**Add After Line 245 (after Qdrant init):**
```python
    # Phase 55.1: Initialize MCP maintenance scheduler
    try:
        from src.mcp.state import get_mcp_state_manager
        mcp_state = get_mcp_state_manager()

        async def maintenance_cycle():
            """Run maintenance tasks every 24 hours."""
            import asyncio
            while True:
                await asyncio.sleep(86400)  # 24 hours
                try:
                    deleted = await mcp_state.delete_expired_states()
                    print(f"   🧹 Maintenance: deleted {deleted} expired MCP states")
                except Exception as e:
                    print(f"   ⚠️ Maintenance failed: {e}")

        # Start maintenance in background
        def run_maintenance():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(maintenance_cycle())

        maintenance_thread = threading.Thread(target=run_maintenance, daemon=True)
        maintenance_thread.start()
        print("   • MCP Maintenance: scheduler started (24h cycle)")

    except Exception as e:
        print(f"   ⚠️ MCP maintenance init failed: {e}")
```

---

## SUMMARY

| Phase | Agents | Files Created | Files Modified | Parallel |
|-------|--------|---------------|----------------|----------|
| A | 3 | 3 | 1 | YES |
| B | 3 | 3 | 0 | YES |
| C | 3 | 0 | 4 | YES |
| D | 1 | 0 | 1 | NO |

**Total New Code:** ~1200 lines
**Total Modified Lines:** ~150

**Execution Order:**
1. Phase A (all 3 in parallel)
2. Phase B (all 3 in parallel, after A complete)
3. Phase C (all 3 in parallel, after B complete)
4. Phase D (single agent, after all complete)

---

**Document Complete**
**Ready for Agent Execution**
