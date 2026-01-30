# 📦 VETKA PHASE 7: SPRINT ROADMAP

## OVERVIEW

**Total:** 5 Sprints | **~16 hours** | **~1,500 lines** | **All in container first, then merge to Mac**

---

## SPRINT 1: Elisyа Foundation (2-3 hours)

### 1.1 Create Directory
```bash
mkdir -p src/elisya
touch src/elisya/__init__.py
```

### 1.2 Create `src/elisya/state.py` (50 lines)
```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

class LODLevel(Enum):
    GLOBAL = "global"
    TREE = "tree"
    LEAF = "leaf"
    FULL = "full"

class SemanticTint(Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    GENERAL = "general"

@dataclass
class ElisyaState:
    """Shared memory layer for all agents"""
    workflow_id: str
    speaker: str  # PM|Dev|QA|Architect|EvalAgent
    semantic_path: str  # projects/python/ml/sklearn
    tint: str = "general"
    lod_level: str = "TREE"
    
    context: str = ""
    few_shots: List[Dict] = field(default_factory=list)
    conversation_history: List[Dict] = field(default_factory=list)
    
    timestamp: float = 0.0
    retry_count: int = 0
    score: float = 0.0
```

**Tests:**
- test_state_creation: Create ElisyaState
- test_state_serialization: Convert to/from JSON
- test_state_validation: Validate required fields

### 1.3 Create `src/elisya/middleware.py` (150 lines)
```python
from typing import Dict, List
import time
from .state import ElisyaState

class ElisyaMiddleware:
    """Elisyа middleware: reframe + update"""
    
    def __init__(self, weaviate_client, llm_client):
        self.weaviate = weaviate_client
        self.llm = llm_client
    
    def reframe(self, state: ElisyaState, agent_type: str) -> ElisyaState:
        """
        Reframe context for agent:
        1. Fetch history from Weaviate (same path)
        2. Truncate by LOD
        3. Add few-shots (score > 0.8)
        4. Add semantic tint
        """
        # Fetch history
        history = self.weaviate.get_branch(state.semantic_path)
        
        # Truncate by LOD
        context = self._truncate_by_lod(history, state.lod_level)
        
        # Get few-shots
        few_shots = self.weaviate.search_few_shots(
            agent_type=agent_type,
            task=state.context[:100],
            score_threshold=0.8
        )
        
        # Assemble reframed context
        state.context = f"[HISTORY]\n{context}\n[FEW_SHOTS]\n{few_shots}"
        state.few_shots = few_shots
        
        return state
    
    def update(self, state: ElisyaState, agent_output: str, speaker: str) -> ElisyaState:
        """
        Update state after agent output:
        1. Append to conversation_history
        2. Generate/update semantic_path
        3. Return updated state
        """
        state.conversation_history.append({
            "speaker": speaker,
            "output": agent_output,
            "timestamp": time.time()
        })
        
        state.semantic_path = self._generate_semantic_path(
            state.conversation_history
        )
        
        state.speaker = speaker
        state.timestamp = time.time()
        
        return state
    
    def _truncate_by_lod(self, history: str, lod_level: str) -> str:
        """Truncate history by Level of Detail"""
        lod_limits = {
            "GLOBAL": 500,
            "TREE": 1500,
            "LEAF": 3000,
            "FULL": 10000
        }
        limit = lod_limits.get(lod_level, 1500)
        return history[:limit]
    
    def _generate_semantic_path(self, history: List[Dict]) -> str:
        """Generate semantic path from conversation history"""
        if not history:
            return "projects/unknown"
        
        # Use LLM to generate path
        prompt = f"""
        Based on conversation history, generate a semantic path like: projects/LANG/DOMAIN/TOOL
        Examples:
        - projects/python/ml/sklearn
        - projects/typescript/backend/express
        - projects/rust/system/tokio
        
        History (last 3 messages):
        {history[-3:]}
        
        Path (only format projects/*/*/* ):
        """
        
        path = self.llm.invoke(prompt).strip()
        
        # Validate format
        if not path.startswith("projects/"):
            return "projects/unknown"
        
        return path
```

**Tests:**
- test_reframe_adds_few_shots: Check few-shots added
- test_update_generates_path: Check path generation
- test_truncate_by_lod: Check LOD truncation

### 1.4 Create `src/elisya/semantic_path.py` (80 lines)
```python
class SemanticPathGenerator:
    """Generate semantic paths like projects/python/ml/sklearn"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def generate(self, task: str, history: List[str]) -> str:
        """Generate semantic path from task + history"""
        prompt = f"""
        Task: {task}
        Previous contexts: {history[-3:]}
        
        Generate semantic path in format: projects/LANG/DOMAIN/TOOL
        
        Examples:
        - projects/python/ml/sklearn
        - projects/typescript/backend/express
        - projects/rust/system/tokio
        - projects/go/devops/kubernetes
        
        Path:
        """
        
        path = self.llm.invoke(prompt).strip()
        
        if self._is_valid_path(path):
            return path
        else:
            return "projects/unknown"
    
    def _is_valid_path(self, path: str) -> bool:
        """Validate path format"""
        if not path.startswith("projects/"):
            return False
        
        parts = path.split("/")
        if len(parts) != 4:
            return False
        
        return all(part.replace("-", "").replace("_", "").isalnum() for part in parts)
```

**Tests:**
- test_path_format: projects/python/ml/sklearn
- test_path_consistency: Same task = same path
- test_path_changes: Different context = different path

---

## SPRINT 2: Autogen Integration (3-4 hours)

### 2.1 Create Directory
```bash
mkdir -p src/autogen_integration
touch src/autogen_integration/__init__.py
```

### 2.2 Create `src/autogen_integration/agents_config.py` (100 lines)
```python
from autogen import AssistantAgent

OLLAMA_LLM_CONFIG = {
    "config_list": [{
        "model": "deepseek-coder:6.7b",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
    }],
    "timeout": 120,
}

AGENTS_CONFIG = {
    "PM": {
        "system_message": "You are a PM. Plan tasks clearly. Output: {plan, complexity, risks}",
        "llm_config": OLLAMA_LLM_CONFIG,
    },
    "Dev": {
        "system_message": "You are a Dev. Write code. Output: {code, lang, explanation}",
        "llm_config": OLLAMA_LLM_CONFIG,
    },
    "QA": {
        "system_message": "You are a QA. Write tests. Output: {tests, edge_cases, coverage}",
        "llm_config": OLLAMA_LLM_CONFIG,
    },
    "Architect": {
        "system_message": "You are Architect. Design solution. Output: {design, patterns, trade-offs}",
        "llm_config": OLLAMA_LLM_CONFIG,
    },
    "EvalAgent": {
        "system_message": "You are Evaluator. Score 0-1. Output: {score, reason, suggestions}",
        "llm_config": OLLAMA_LLM_CONFIG,
    },
}

def create_agents() -> Dict[str, AssistantAgent]:
    """Create Autogen AssistantAgents"""
    agents = {}
    for name, config in AGENTS_CONFIG.items():
        agents[name] = AssistantAgent(
            name=name,
            system_message=config["system_message"],
            llm_config=config["llm_config"],
        )
    return agents
```

### 2.3 Create `src/autogen_integration/groupchat_wrapper.py` (200 lines)
```python
from autogen import GroupChat, GroupChatManager, AssistantAgent
from src.elisya.state import ElisyaState
import uuid
import time

class VetkaGroupChat:
    """Autogen GroupChat wrapper for Vetka"""
    
    def __init__(self, agents: Dict[str, AssistantAgent], user_request: str):
        self.agents = agents
        self.user_request = user_request
        self.state = None
        
        self.groupchat = GroupChat(
            agents=list(agents.values()),
            messages=[],
            max_round=10,
            system_message=f"You are a development team. Task: {user_request}",
        )
        self.manager = GroupChatManager(groupchat=self.groupchat)
    
    def create_initial_state(self) -> ElisyaState:
        """Create initial ElisyaState from request"""
        return ElisyaState(
            workflow_id=str(uuid.uuid4()),
            speaker="PM",
            semantic_path="projects/unknown",
            context=self.user_request,
            timestamp=time.time(),
        )
    
    def run(self) -> ElisyaState:
        """Run GroupChat and return ElisyaState"""
        self.state = self.create_initial_state()
        
        # Initiate chat
        result = self.manager.initiate_chat(
            recipient=self.manager,
            message=self.state.context,
            max_consecutive_auto_reply=10,
        )
        
        # Extract messages into state
        for msg in self.groupchat.messages:
            self.state.conversation_history.append({
                "speaker": msg.get("name", "Unknown"),
                "output": msg.get("content", ""),
                "timestamp": time.time(),
            })
        
        return self.state
```

### 2.4 Create `src/autogen_integration/message_handler.py` (100 lines)
```python
from src.elisya.middleware import ElisyaMiddleware
from src.elisya.state import ElisyaState

class Autogen2ElisyaHandler:
    """Convert Autogen messages to Elisyа updates"""
    
    def __init__(self, elisya_middleware: ElisyaMiddleware):
        self.middleware = elisya_middleware
    
    def process_message(self, msg: Dict, state: ElisyaState) -> ElisyaState:
        """
        Convert Autogen message to Elisyа update
        """
        speaker = msg.get("name", "Unknown")
        content = msg.get("content", "")
        
        # Reframe for agent
        state = self.middleware.reframe(state, speaker)
        
        # Update after agent output
        state = self.middleware.update(state, content, speaker)
        
        return state
```

**Tests:**
- test_agents_creation: All agents created
- test_groupchat_initialization: GroupChat starts
- test_groupchat_runs: Messages flow

---

## SPRINT 3: LangGraph + Elisyа (4-5 hours)

### 3.1 Create `src/workflows/langgraph_with_elisya.py` (250 lines)
```python
from langgraph.graph import StateGraph, START, END
from src.elisya.state import ElisyaState
from src.elisya.middleware import ElisyaMiddleware
from src.workflows.langgraph_nodes import VetkaLangGraphNodes

def build_vetka_graph(
    nodes: VetkaLangGraphNodes,
    middleware: ElisyaMiddleware
):
    """Build complete workflow with Elisyа"""
    
    graph = StateGraph(ElisyaState)
    
    # ===== NODE: PM Planning =====
    def pm_node(state: ElisyaState) -> ElisyaState:
        state = middleware.reframe(state, "PM")
        output = nodes.pm_plan_node(state)
        state = middleware.update(state, output, "PM")
        return state
    
    # ===== NODE: Architect =====
    def architect_node(state: ElisyaState) -> ElisyaState:
        state = middleware.reframe(state, "Architect")
        output = nodes.architect_node(state)
        state = middleware.update(state, output, "Architect")
        return state
    
    # ===== NODE: Dev || QA Parallel =====
    def dev_qa_parallel_node(state: ElisyaState) -> ElisyaState:
        # Dev
        state_dev = middleware.reframe(state, "Dev")
        output_dev = nodes.dev_implement_node(state_dev)
        
        # QA
        state_qa = middleware.reframe(state, "QA")
        output_qa = nodes.qa_test_node(state_qa)
        
        # Merge
        state = middleware.update(state, output_dev, "Dev")
        state = middleware.update(state, output_qa, "QA")
        return state
    
    # ===== NODE: Eval =====
    def eval_node(state: ElisyaState) -> ElisyaState:
        state = middleware.reframe(state, "EvalAgent")
        # Score
        score = 0.85  # placeholder
        state.score = score
        
        if score < 0.7:
            return {"retry": True, "state": state}
        else:
            return {"retry": False, "state": state}
    
    # Add nodes
    graph.add_node("pm", pm_node)
    graph.add_node("architect", architect_node)
    graph.add_node("dev_qa", dev_qa_parallel_node)
    graph.add_node("eval", eval_node)
    
    # Add edges
    graph.add_edge(START, "pm")
    graph.add_edge("pm", "architect")
    graph.add_edge("architect", "dev_qa")
    graph.add_edge("dev_qa", "eval")
    graph.add_edge("eval", END)
    
    return graph.compile()
```

### 3.2 Create `src/workflows/state_manager.py` (150 lines)
```python
from src.elisya.state import ElisyaState
import uuid
import time

class StateManager:
    """Manage ElisyaState lifecycle"""
    
    def __init__(self, weaviate_client, qdrant_client):
        self.weaviate = weaviate_client
        self.qdrant = qdrant_client
    
    def create_from_request(self, request: Dict) -> ElisyaState:
        """Create initial state from request"""
        return ElisyaState(
            workflow_id=str(uuid.uuid4()),
            speaker="PM",
            semantic_path="projects/unknown",
            context=request.get("feature", ""),
            lod_level=request.get("lod_level", "TREE"),
            timestamp=time.time(),
        )
    
    def persist_to_weaviate(self, state: ElisyaState):
        """Save state to Weaviate"""
        # Implementation in sprint 4
        pass
    
    def load_from_weaviate(self, workflow_id: str) -> ElisyaState:
        """Resume workflow from Weaviate"""
        # Implementation in sprint 4
        pass
```

**Tests:**
- test_graph_compiles: StateGraph builds
- test_state_flows: State moves through nodes
- test_parallel_execution: Dev || QA timing

---

## SPRINT 4: Triple Write Integration (2-3 hours)

### 4.1 Create `src/memory/triple_write_integration.py` (100 lines)
```python
from src.elisya.state import ElisyaState

def persist_elisya_state(
    state: ElisyaState,
    qdrant_client,
    weaviate_client,
):
    """Write ElisyaState to all 3 stores atomically"""
    
    results = qdrant_client.triple_write(
        workflow_id=state.workflow_id,
        node_id=f"{state.speaker}_{state.timestamp}",
        path=state.semantic_path,
        content=state.context,
        metadata={
            "tint": state.tint,
            "lod": state.lod_level,
            "retry_count": state.retry_count,
            "score": state.score,
        },
        vector=embed(state.context),
        weaviate_write_func=weaviate_client.save,
    )
    
    assert results["atomic"], f"Triple write failed: {results}"
    
    return results
```

**Tests:**
- test_triple_write: All stores written
- test_changelog_records: ChangeLog updated
- test_atomicity_verified: Flag = true

---

## SPRINT 5: Full Integration Tests (3-4 hours)

### 5.1 Create `tests/test_complete_workflow.py` (100 lines)
```python
def test_complete_workflow():
    """End-to-end workflow test"""
    from src.workflows.langgraph_with_elisya import build_vetka_graph
    from src.workflows.state_manager import StateManager
    
    request = {"feature": "Create ML model", "complexity": "LARGE"}
    
    # Create components
    graph = build_vetka_graph(create_nodes(), middleware)
    state_mgr = StateManager(weaviate, qdrant)
    
    # Create initial state
    state = state_mgr.create_from_request(request)
    
    # Run workflow
    final_state = graph.invoke(state)
    
    # Verify
    assert final_state.score > 0.7, f"Score too low: {final_state.score}"
    assert len(final_state.conversation_history) > 2
    assert final_state.semantic_path.startswith("projects/")
    assert final_state.workflow_id
```

---

## 📋 ALL SPRINT FILES SUMMARY

| Sprint | Files | Lines | Time |
|--------|-------|-------|------|
| 1 | state.py, middleware.py, semantic_path.py | 280 | 2-3h |
| 2 | agents_config.py, groupchat_wrapper.py, message_handler.py | 400 | 3-4h |
| 3 | langgraph_with_elisya.py, state_manager.py | 400 | 4-5h |
| 4 | triple_write_integration.py | 100 | 2-3h |
| 5 | test_complete_workflow.py + benchmarks | 100 | 3-4h |
| **TOTAL** | **~10+ files** | **~1,500** | **~16h** |

---

## 🧪 SUCCESS CRITERIA (Sprint-by-Sprint)

### Sprint 1: ✓
- [ ] ElisyaState creates without errors
- [ ] reframe() adds few-shots
- [ ] update() generates semantic_path
- [ ] All 3 tests PASS

### Sprint 2: ✓
- [ ] GroupChat starts and runs
- [ ] Agents communicate
- [ ] Messages flow to Elisyа
- [ ] All 3 tests PASS

### Sprint 3: ✓
- [ ] Graph compiles
- [ ] State flows through all nodes
- [ ] Middleware applied at each step
- [ ] Dev || QA parallel verified
- [ ] All tests PASS

### Sprint 4: ✓
- [ ] All 3 stores written
- [ ] ChangeLog complete
- [ ] Atomicity = true
- [ ] All tests PASS

### Sprint 5: ✓
- [ ] User request → final output in < 160s
- [ ] Score > 0.7
- [ ] Conversation history complete
- [ ] All tests PASS

---

## 🚀 EXECUTION ORDER

1. ✅ Sprint 1 → test locally → GREEN
2. ✅ Sprint 2 → test locally → GREEN
3. ✅ Sprint 3 → test locally → GREEN
4. ✅ Sprint 4 → test locally → GREEN
5. ✅ Sprint 5 → test locally → GREEN
6. → All tests GREEN
7. → Merge to Mac project
8. → Run on Mac
9. → Demo complete

---

**Total Time: ~16 hours in container, then ~2 hours on Mac for merge + testing**

All code written in container first, fully tested with pytest, then integrated on Mac.
