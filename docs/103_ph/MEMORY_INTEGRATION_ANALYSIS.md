# MEMORY INTEGRATION ANALYSIS - Phase 103
## Comprehensive Audit: ARC, HOPE, Elisya, CAM, STM

**Date:** 2026-01-31
**Task:** Trace memory flow between agents (Dev, QA, Spawn, Pipeline)
**Status:** ✅ COMPLETE

---

## 📋 EXECUTIVE SUMMARY

VETKA uses **5 memory subsystems** working in concert:

| Component | Purpose | Phase | Pipeline Ready? | Spawn Ready? |
|-----------|---------|-------|----------------|--------------|
| **ARC** | Gap detection, pattern learning | 99.3 | ✅ YES | ⚠️ PARTIAL |
| **HOPE** | Hierarchical analysis (LOW/MID/HIGH) | 99 | ✅ YES | ✅ YES |
| **Elisya** | Agent context reframing | 96 | ✅ YES | ❌ NO |
| **CAM** | Tree restructuring, surprise detection | 99 | ✅ YES | ❌ NO |
| **STM** | Short-term buffer (5-10 items, decay) | 99 | ✅ YES | ⚠️ PARTIAL |

**Key Finding:** Memory flows through **LangGraph state** in pipeline but **not** in spawn tasks.

---

## 1️⃣ ARC - Automatic Reasoning & Creativity

### 📍 Definition Location
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/arc_gap_detector.py`

**Core Classes:**
```python
class ARCGapDetector:
    """
    Detects conceptual gaps before agent execution.

    FIX_99.3: Implements TODO_ARC_GAP
    """
    SIMILARITY_THRESHOLD_NOVEL = 0.7    # Below this = new branch
    CONCEPT_PATTERNS = [
        r'\b(api|endpoint|route|handler)\b',
        r'\b(database|db|qdrant|weaviate|storage)\b',
        r'\b(cache|memory|buffer|stm|mgc)\b',
        r'\b(cam|hope|arc|elisya)\b',  # VETKA-specific
    ]
```

**Key Methods:**
- `extract_concepts(text)` - O(n) pattern matching, no LLM
- `find_related_concepts()` - Semantic search via MemoryManager
- `detect_gaps()` - Compare extracted vs related concepts
- `_get_arc_solver_suggestions()` - Deep analysis via ARCSolverAgent

### 🔌 Integration Points

**1. Orchestrator Integration**
```python
# src/orchestration/orchestrator_with_elisya.py
from src.orchestration.arc_gap_detector import detect_conceptual_gaps, get_gap_detector

async def _run_agent_with_elisya_async(...):
    # FIX_99.3: ARC gap detection before agent execution
    gap_suggestions = await detect_conceptual_gaps(
        prompt=prompt,
        context=state.context,
        memory_manager=self.memory,
        arc_solver=self.arc_solver
    )
    if gap_suggestions:
        prompt = f"{prompt}\n\n{gap_suggestions}"
```

**2. ARCSolverAgent Dependency**
```python
# src/agents/arc_solver_agent.py
class ARCSolverAgent:
    """
    Suggests connections between graph nodes for transformations.
    """
    few_shot_examples: List[FewShotExample]  # ARC learning cache

    def suggest_connections(self, workflow_id, graph_data, task_context):
        # Returns top suggestions with type, explanation, score
```

### ⚙️ Pipeline Usage

**WHERE:**
- `src/orchestration/orchestrator_with_elisya.py` - Before each agent call
- `src/orchestration/langgraph_nodes.py` - Dev/QA parallel node (via orchestrator)

**HOW:**
```python
# Pipeline flow:
1. User prompt arrives
2. ARCGapDetector.extract_concepts(prompt) → ['api', 'endpoint', 'handler']
3. MemoryManager.search(concepts) → Related code examples from Qdrant
4. detect_gaps() → Find missing patterns
5. Inject suggestions into prompt:
   "[ARC Gap Analysis - Consider these related concepts:]
    1. auth middleware integration (★★★★☆)
    2. error handling patterns (★★★☆☆)"
6. Dev/QA agents receive enriched prompt
```

### 🔄 Spawn Usage

**STATUS:** ⚠️ **PARTIAL** - No direct integration

**Opportunity:**
```python
# Future: src/utils/staging_utils.py
async def run_subtask_spawn(subtask):
    # Add ARC gap detection here:
    gap_suggestions = await detect_conceptual_gaps(
        prompt=subtask['description'],
        memory_manager=get_memory_manager()
    )
    if gap_suggestions:
        subtask['description'] = f"{subtask['description']}\n\n{gap_suggestions}"
```

**Gap:** Spawn tasks don't benefit from ARC's pattern learning yet.

---

## 2️⃣ HOPE - Hierarchical Optimized Processing Engine

### 📍 Definition Location
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/agents/hope_enhancer.py`

**Core Architecture:**
```python
class HOPEEnhancer:
    """
    Hierarchical analysis with frequency-based decomposition.

    - LOW: High-level summary, main concepts (~200 words)
    - MID: Detailed analysis, relationships (~400 words)
    - HIGH: Specifics, edge cases, implementation (~600 words)
    """

    LAYER_PROMPTS = {
        FrequencyLayer.LOW: "GLOBAL ANALYSIS (Low Frequency - Big Picture)",
        FrequencyLayer.MID: "DETAILED ANALYSIS (Mid Frequency - Relationships)",
        FrequencyLayer.HIGH: "FINE-GRAINED ANALYSIS (High Frequency - Specifics)"
    }

    def analyze(self, content, layers, complexity, stm_context):
        # FIX_99.1: STM Buffer integration
        if stm_context:
            recent_context = "\n".join(e.content for e in stm_context[:3])
            content = f"Recent context:\n{recent_context}\n\n{content}"
```

### 🔌 Integration Points

**1. LangGraph Node - hope_enhancement_node**
```python
# src/orchestration/langgraph_nodes.py (line 443-577)
async def hope_enhancement_node(self, state: VETKAState) -> VETKAState:
    """
    HOPE enhancement node.

    Marker: [M-10] - Insert between pm_node and dev_qa_parallel_node

    Analyzes PM output with multi-frequency approach.
    """
    lod_level = state.get('lod_level', 'MEDIUM')
    complexity_map = {
        'MICRO': 'LOW',
        'SMALL': 'LOW',
        'MEDIUM': 'MID',
        'LARGE': 'HIGH',
        'EPIC': 'HIGH'
    }

    hope = HOPEEnhancer(use_api_fallback=False)
    analysis = hope.analyze(
        content=content_to_analyze[:4000],
        layers=[FrequencyLayer.LOW, FrequencyLayer.MID, ...],
        complexity=lod_level
    )

    state['hope_summary'] = analysis.get('combined', '')

    # FIX_99.1: Add HOPE summary to STM buffer
    stm.add_from_hope(hope_summary[:500], workflow_id=workflow_id)
```

**2. Dev/QA Context Injection**
```python
# src/orchestration/langgraph_nodes.py (line 631-633)
async def dev_qa_parallel_node(self, state: VETKAState) -> VETKAState:
    hope_summary = state.get('hope_summary', '')
    if hope_summary:
        combined_context = f"## 🧠 HOPE Analysis (Hierarchical Overview)\n{hope_summary}\n\n{combined_context}"
```

### ⚙️ Pipeline Usage

**FLOW:**
```
1. PM creates plan
2. hope_enhancement_node() analyzes with matryoshka layers
3. HOPE summary stored in state['hope_summary']
4. Dev/QA receive enriched context with HOPE hierarchical view
```

**Example:**
```markdown
## 🧠 HOPE Analysis (Hierarchical Overview)

### Global Overview
Create REST API endpoint for user authentication with JWT tokens.

### Detailed Analysis
- Route: POST /api/auth/login
- Middleware: validateCredentials → generateToken → setCookie
- Error handling: 401 Unauthorized, 500 Internal Server Error

### Specifics & Details
- JWT expiry: 7 days
- Bcrypt rounds: 12
- Token refresh: sliding window pattern
```

### 🔄 Spawn Usage

**STATUS:** ✅ **YES** - Can be used

**How:**
```python
# Subtask decomposition with HOPE:
from src.agents.hope_enhancer import quick_hope_analysis

for subtask in subtasks:
    # Analyze subtask description with HOPE LOW layer
    summary = quick_hope_analysis(subtask['description'])
    subtask['hope_summary'] = summary
```

**Benefit:** Each spawn task gets hierarchical context breakdown.

---

## 3️⃣ ELISYA - Context Reframing Middleware

### 📍 Definition Location

**Core State:**
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/state.py`

```python
@dataclass
class ElisyaState:
    """
    Shared memory state for all agents.

    This is the LANGUAGE that agents use to communicate.
    """
    workflow_id: str
    speaker: str = "PM"
    semantic_path: str = "projects/unknown"

    context: str = ""                 # Reframed context (for current agent)
    lod_level: str = "tree"           # GLOBAL|TREE|LEAF|FULL
    tint: str = "general"             # Security|Performance|...

    conversation_history: List[ConversationMessage]
    few_shots: List[FewShotExample]
```

**Middleware:**
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/middleware.py`

```python
class ElisyaMiddleware:
    """
    Context reframing for each agent type.

    PM:   "Create a plan"
    Dev:  "Implement the following architecture"
    QA:   "Test this implementation"
    """

    def reframe_context(self, state: ElisyaState, agent_type: str) -> ElisyaState:
        # Filter context based on:
        # - agent_type (PM/Dev/QA/Architect)
        # - lod_level (GLOBAL/TREE/LEAF/FULL)
        # - tint (security/performance/reliability)
```

### 🔌 Integration Points

**1. Orchestrator Integration**
```python
# src/orchestration/orchestrator_with_elisya.py (line 155-227)
class OrchestratorWithElisya:
    def __init__(self):
        self.elisya_service = ElisyaStateService(memory_manager=self.memory)
        self.middleware = self.elisya_service.middleware

    def _get_or_create_state(self, workflow_id, feature) -> ElisyaState:
        return self.elisya_service.get_or_create_state(workflow_id, feature)
```

**2. LangGraph Conversion**
```python
# src/orchestration/langgraph_nodes.py (line 1102-1119)
def _create_elisya_state(self, state: VETKAState) -> ElisyaState:
    """Convert VETKAState → ElisyaState for backwards compatibility."""
    return ElisyaState(
        workflow_id=state["workflow_id"],
        speaker=state.get("current_agent", "PM"),
        context=state.get("context", ""),
        semantic_path=state.get("semantic_path", ""),
        lod_level=state.get("lod_level", "tree").lower()
    )
```

### ⚙️ Pipeline Usage

**FLOW:**
```
1. VETKAState (LangGraph) arrives at node
2. Convert to ElisyaState via _create_elisya_state()
3. ElisyaMiddleware.reframe_context(elisya_state, "Dev")
4. Agent receives reframed context
5. Agent output stored back in VETKAState
```

**Example:**
```python
# PM receives:
"Create a REST API for authentication"

# After reframing for Dev:
"Implement the following REST API:
- Endpoint: POST /api/auth/login
- Input: {username, password}
- Output: {token, expires_at}
- Security: bcrypt + JWT
Existing context: [related code from semantic_path]"
```

### 🔄 Spawn Usage

**STATUS:** ❌ **NO** - Not integrated

**Why:**
- Spawn uses `asyncio.create_subprocess_exec()` - direct process spawn
- No ElisyaState passed to subprocess
- No middleware reframing

**Opportunity:**
```python
# Future: Create ElisyaState for spawn subtasks
from src.elisya.state import ElisyaState

async def run_subtask_with_elisya(subtask):
    state = ElisyaState(
        workflow_id=subtask['id'],
        speaker='Dev',
        context=subtask['description']
    )
    state = middleware.reframe_context(state, 'Dev')
    # Pass state.context to spawn subprocess
```

---

## 4️⃣ CAM - Constructivist Agentic Memory

### 📍 Definition Location
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/cam_engine.py`

**Core Architecture:**
```python
class VETKACAMEngine:
    """
    Implements 4 core operations from NeurIPS 2025 CAM paper:
    1. Branching - create new branches for novel artifacts
    2. Pruning - mark low-activation branches for deletion
    3. Merging - combine similar subtrees
    4. Accommodation - smooth layout transitions with Procrustes
    """

    SIMILARITY_THRESHOLD_NOVEL = 0.7    # Below this = new branch
    SIMILARITY_THRESHOLD_MERGE = 0.92   # Above this = merge candidates
    ACTIVATION_THRESHOLD_PRUNE = 0.2    # Below this = prune candidates

    # FIX_99.1: STM Buffer Integration
    def notify_stm_surprise(self, content, surprise_score, stm_buffer):
        """Notify STM buffer about a surprise event."""
        if surprise_score >= 0.3:
            stm_buffer.add_from_cam(content[:500], surprise_score)
```

### 🔌 Integration Points

**1. Handle New Artifact**
```python
async def handle_new_artifact(self, artifact_path, metadata) -> CAMOperation:
    """
    Decision tree:
    - similarity < 0.7: create new branch
    - 0.7 <= similarity < 0.92: propose merge
    - similarity >= 0.92: mark as variant
    """
    embedding = self._get_embedding(content)
    max_similarity = max(cosine_similarity(embedding, existing_node.embedding))

    if max_similarity < SIMILARITY_THRESHOLD_NOVEL:
        operation_type = "branch"
    elif max_similarity >= SIMILARITY_THRESHOLD_MERGE:
        operation_type = "variant"
    else:
        operation_type = "merge_proposal"
```

**2. Surprise Metric**
```python
def calculate_surprise_for_file(self, file_embedding, sibling_embeddings) -> float:
    """
    surprise = 1 - cosine_similarity(file_embedding, avg_sibling_embeddings)

    Returns:
        Surprise score from 0.0 (identical) to 1.0 (completely novel)
    """
    avg_sibling = np.mean(sibling_embeddings, axis=0)
    similarity = np.dot(file_embedding, avg_sibling) / (norm_file * norm_sibling)
    surprise = max(0.0, min(1.0, 1.0 - similarity))
    return surprise
```

### ⚙️ Pipeline Usage

**WHERE:**
- `src/api/routes/tree_routes.py` - Surprise calculation for file tree
- `src/orchestration/langgraph_nodes.py` - Artifact processing in approval_node

**FLOW:**
```
1. File scan detects new artifact
2. CAM.handle_new_artifact() calculates surprise
3. High surprise (>0.3) → notify_stm_surprise()
4. STM buffer stores surprise event with boosted weight
5. Layout accommodation triggered
```

**Example:**
```python
# Artifact: new auth middleware
artifact_path = "src/middleware/auth.ts"
metadata = {
    'type': 'typescript',
    'size': 1234,
    'embedding': [0.123, 0.456, ...]
}

cam_operation = await cam.handle_new_artifact(artifact_path, metadata)
# cam_operation.operation_type = "branch"
# cam_operation.details = {'similarity': 0.65, 'similar_to': 'src/middleware/logger.ts'}

# STM notification
if cam_operation.details['similarity'] < 0.7:
    cam.notify_stm_surprise(
        content=artifact_path,
        surprise_score=1.0 - 0.65,  # 0.35
        stm_buffer=stm
    )
```

### 🔄 Spawn Usage

**STATUS:** ❌ **NO** - Not integrated

**Why:**
- CAM operates on file tree structure
- Spawn tasks are ephemeral (no persistent tree)
- No embedding generation for spawn outputs

**Opportunity:**
```python
# Future: Track spawn task novelty
async def track_spawn_novelty(subtask_output):
    embedding = get_embedding(subtask_output)
    siblings = get_sibling_subtask_embeddings()
    surprise = cam.calculate_surprise_for_file(embedding, siblings)

    if surprise > 0.5:
        # High novelty subtask - worth storing
        await store_in_replay_buffer(subtask_output)
```

---

## 5️⃣ STM - Short-Term Memory Buffer

### 📍 Definition Location
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/stm_buffer.py`

**Core Architecture:**
```python
class STMBuffer:
    """
    Short-Term Memory Buffer with automatic decay.

    Maintains the most recent N interactions with time-based weight decay.
    High-surprise items from CAM get boosted initial weights.

    MARKER-99-01: Decay formula applies on each add() call
    """

    def __init__(self, max_size=10, decay_rate=0.1, min_weight=0.1):
        self._buffer: deque[STMEntry] = deque(maxlen=max_size)
        self.decay_rate = decay_rate  # 10% per minute

    def _apply_decay(self):
        """
        FIX_99.2: Adaptive surprise preservation (soft coefficient 0.3)

        base_decay = weight * (1 - decay_rate * (age_seconds / 60))

        High-surprise items decay 30% slower:
        - surprise_score=0 → full decay (preservation=1.0)
        - surprise_score=1 → 30% slower decay (preservation=1.3)
        """
        for entry in self._buffer:
            age_seconds = (now - entry.timestamp).total_seconds()
            base_decay = self.decay_rate * (age_seconds / 60)

            surprise_preservation = 1.0 + (entry.surprise_score * 0.3)
            adjusted_decay = decay_factor + (1 - decay_factor) * (entry.surprise_score * 0.3)

            entry.weight = max(self.min_weight, entry.weight * adjusted_decay)
```

### 🔌 Integration Points

**1. HOPE → STM**
```python
# src/orchestration/langgraph_nodes.py (line 524-534)
async def hope_enhancement_node(self, state: VETKAState) -> VETKAState:
    # FIX_99.1: Add HOPE summary to STM buffer
    stm = STMBuffer.from_dict(state.get('stm_buffer', {}))
    stm.add_from_hope(hope_summary[:500], workflow_id=workflow_id)
    state['stm_buffer'] = stm.to_dict()
```

**2. CAM → STM**
```python
# src/orchestration/cam_engine.py (line 749-786)
def notify_stm_surprise(self, content, surprise_score, stm_buffer):
    """
    FIX_99.1: High-surprise events are added to STM for quick context access.
    """
    entry = STMEntry(
        content=content,
        source="cam_surprise",
        weight=1.0 + surprise_score,  # Surprise boosts initial weight
        surprise_score=surprise_score
    )
    stm_buffer.add(entry)
```

**3. VETKAState Storage**
```python
# src/orchestration/langgraph_state.py (line 108)
class VETKAState(TypedDict):
    stm_buffer: Optional[Dict[str, Any]]  # FIX_99.1
```

### ⚙️ Pipeline Usage

**FLOW:**
```
1. HOPE analyzes PM output
2. HOPE summary added to STM: stm.add_from_hope(summary)
3. CAM detects surprise artifact
4. CAM adds to STM: stm.add_from_cam(artifact, surprise_score)
5. Dev/QA read STM context: stm.get_context(max_items=5)
6. STM entries decay over time (10% per minute)
```

**Example:**
```python
# STM state after 3 interactions:
[
    STMEntry(
        content="HOPE: Global architecture - REST API with JWT auth",
        source="hope",
        weight=1.1,  # Slight boost for HOPE
        surprise_score=0.0
    ),
    STMEntry(
        content="CAM: New file src/middleware/auth.ts",
        source="cam_surprise",
        weight=1.35,  # 1.0 + 0.35 surprise
        surprise_score=0.35
    ),
    STMEntry(
        content="User: implement login endpoint",
        source="user",
        weight=0.9,  # Decayed (2 minutes old)
        surprise_score=0.0
    )
]

# Get context for Dev agent:
context = stm.get_context(max_items=3)
# Returns sorted by weight: [CAM entry, HOPE entry, User entry]
```

### 🔄 Spawn Usage

**STATUS:** ⚠️ **PARTIAL** - No automatic integration

**Why:**
- STM stored in VETKAState (LangGraph state)
- Spawn doesn't use VETKAState
- No shared memory between spawn tasks

**Opportunity:**
```python
# Future: Shared STM across spawn tasks
from src.memory.stm_buffer import get_stm_buffer

async def run_subtask_spawn(subtask):
    stm = get_stm_buffer()  # Global singleton

    # Add subtask to STM
    stm.add_message(subtask['description'], source='spawn')

    # Get recent context
    context = stm.get_context_string(max_items=5)
    subtask['enriched_context'] = f"{context}\n\n{subtask['description']}"
```

---

## 📊 INTEGRATION MATRIX

### Pipeline (LangGraph) Integration

| Memory | Where Defined | Used By | How Passed | Storage |
|--------|--------------|---------|-----------|---------|
| ARC | `arc_gap_detector.py` | `orchestrator_with_elisya.py` | Function call | MemoryManager |
| HOPE | `hope_enhancer.py` | `langgraph_nodes.py:hope_enhancement_node` | VETKAState['hope_summary'] | In-state dict |
| Elisya | `elisya/state.py` | All agents via `_create_elisya_state()` | Converted from VETKAState | Orchestrator |
| CAM | `cam_engine.py` | `langgraph_nodes.py:approval_node` | CAMIntegration service | Singleton |
| STM | `stm_buffer.py` | `langgraph_nodes.py` (HOPE, CAM) | VETKAState['stm_buffer'] | In-state dict |

### Spawn Integration

| Memory | Integrated? | Reason | Fix Strategy |
|--------|-------------|--------|--------------|
| ARC | ⚠️ PARTIAL | No gap detection before spawn | Add `detect_conceptual_gaps()` in staging_utils |
| HOPE | ✅ YES | Can call `quick_hope_analysis()` | Already works - just need to call it |
| Elisya | ❌ NO | No ElisyaState in spawn | Create ElisyaState wrapper for spawn tasks |
| CAM | ❌ NO | No file tree for spawn | Track spawn task novelty separately |
| STM | ⚠️ PARTIAL | No shared STM | Use global `get_stm_buffer()` singleton |

---

## 🔍 MEMORY FLOW DIAGRAMS

### Pipeline Flow (LangGraph)

```
┌─────────────────────────────────────────────────────────────┐
│ VETKAState (LangGraph Unified State)                        │
├─────────────────────────────────────────────────────────────┤
│ - context: str                                              │
│ - hope_summary: str                                         │
│ - stm_buffer: Dict[str, Any]                                │
│ - semantic_path: str (from Elisya)                          │
│ - surprise_scores: Dict[str, float] (from CAM)              │
└─────────────────────────────────────────────────────────────┘
           │
           ├──> ARC Gap Detection (before agent call)
           │    └─> Inject suggestions into prompt
           │
           ├──> HOPE Enhancement Node
           │    ├─> Analyze PM output (LOW/MID/HIGH)
           │    └─> Add summary to state['hope_summary']
           │         └─> STM.add_from_hope()
           │
           ├──> Elisya Middleware
           │    ├─> Convert VETKAState → ElisyaState
           │    ├─> Reframe context for agent type
           │    └─> Agent receives reframed context
           │
           ├──> CAM Artifact Processing
           │    ├─> Calculate surprise for new files
           │    ├─> Decide: branch/merge/variant
           │    └─> STM.add_from_cam() if surprise > 0.3
           │
           └──> STM Buffer
                ├─> Receives from HOPE, CAM, User
                ├─> Apply decay (10% per minute)
                └─> Provide top 5 by weight to agents
```

### Spawn Flow (Current - No Memory Integration)

```
┌─────────────────────────────────────────────────────────────┐
│ Subtask Dictionary                                          │
├─────────────────────────────────────────────────────────────┤
│ - id: str                                                   │
│ - description: str                                          │
│ - status: str                                               │
│ - agent_type: str                                           │
└─────────────────────────────────────────────────────────────┘
           │
           └──> asyncio.create_subprocess_exec()
                ├─> No ARC gap detection
                ├─> No HOPE analysis
                ├─> No Elisya reframing
                ├─> No CAM surprise tracking
                └─> No STM buffer

                → Spawn task runs in isolation
```

---

## 🛠️ RECOMMENDED FIXES

### 1. ARC Integration in Spawn

**File:** `src/utils/staging_utils.py`

```python
from src.orchestration.arc_gap_detector import detect_conceptual_gaps
from src.orchestration.memory_manager import MemoryManager

async def run_subtask_spawn(subtask):
    # MARKER-SPAWN-ARC-001: Add gap detection
    memory = MemoryManager()

    gap_suggestions = await detect_conceptual_gaps(
        prompt=subtask['description'],
        context="",
        memory_manager=memory
    )

    if gap_suggestions:
        subtask['description'] = f"{subtask['description']}\n\n{gap_suggestions}"
```

### 2. STM Global Singleton for Spawn

**File:** `src/memory/stm_buffer.py` (already has global singleton)

**File:** `src/utils/staging_utils.py`

```python
from src.memory.stm_buffer import get_stm_buffer

async def run_subtask_spawn(subtask):
    # MARKER-SPAWN-STM-001: Share STM across tasks
    stm = get_stm_buffer()

    # Get recent context
    recent_context = stm.get_context_string(max_items=3)
    if recent_context:
        subtask['description'] = f"Recent context:\n{recent_context}\n\n{subtask['description']}"

    # After execution, add result to STM
    result = await execute_subtask(subtask)
    stm.add_message(result[:500], source='spawn', metadata={'subtask_id': subtask['id']})
```

### 3. HOPE for Subtask Decomposition

**File:** `src/utils/staging_utils.py`

```python
from src.agents.hope_enhancer import quick_hope_analysis

async def decompose_task_with_hope(task_description):
    # MARKER-SPAWN-HOPE-001: Add hierarchical analysis
    hope_summary = quick_hope_analysis(task_description)

    return {
        'original': task_description,
        'hope_summary': hope_summary,
        'subtasks': [...]
    }
```

---

## ✅ VERIFICATION MARKERS

**MARKER-MEM-001:** ARC defined in `src/orchestration/arc_gap_detector.py`
**MARKER-MEM-002:** HOPE defined in `src/agents/hope_enhancer.py`
**MARKER-MEM-003:** Elisya defined in `src/elisya/state.py`
**MARKER-MEM-004:** CAM defined in `src/orchestration/cam_engine.py`
**MARKER-MEM-005:** STM defined in `src/memory/stm_buffer.py`

**MARKER-MEM-006:** ARC used in pipeline via `orchestrator_with_elisya.py`
**MARKER-MEM-007:** HOPE used in pipeline via `langgraph_nodes.py:hope_enhancement_node`
**MARKER-MEM-008:** Elisya used in pipeline via `_create_elisya_state()`
**MARKER-MEM-009:** CAM used in pipeline via `approval_node` and `tree_routes`
**MARKER-MEM-010:** STM used in pipeline via VETKAState storage

**MARKER-MEM-011:** ARC NOT used in spawn (opportunity: staging_utils)
**MARKER-MEM-012:** HOPE CAN be used in spawn (just call it)
**MARKER-MEM-013:** Elisya NOT used in spawn (no state conversion)
**MARKER-MEM-014:** CAM NOT used in spawn (no file tree)
**MARKER-MEM-015:** STM PARTIAL in spawn (global singleton available but not used)

---

## 📖 DATA FLOW EXAMPLES

### Example 1: Pipeline with Full Memory Integration

```python
# 1. User request arrives
user_prompt = "Create REST API for user authentication"

# 2. ARC Gap Detection
arc_gaps = await detect_conceptual_gaps(user_prompt, memory_manager=memory)
# Result: "Consider: JWT token generation, password hashing, session management"

# 3. HOPE Analysis (in hope_enhancement_node)
hope_analysis = hope.analyze(user_prompt)
# Result:
# - LOW: "REST API with auth endpoints"
# - MID: "POST /login, POST /register, GET /me, middleware chain"
# - HIGH: "bcrypt hashing, JWT expiry 7 days, refresh token pattern"

# 4. STM Update
stm.add_from_hope(hope_analysis['combined'][:500])

# 5. Elisya Reframing for Dev
elisya_state = ElisyaState(context=user_prompt, speaker='PM')
elisya_state = middleware.reframe_context(elisya_state, 'Dev')
# Result: "Implement REST API with: [architecture details], existing code: [semantic_path search results]"

# 6. Dev Agent Execution
dev_output = await dev_agent.execute(elisya_state.context)

# 7. CAM Artifact Processing (if Dev created files)
for artifact in created_files:
    cam_op = await cam.handle_new_artifact(artifact.path, artifact.metadata)
    if cam_op.details['similarity'] < 0.7:
        stm.add_from_cam(artifact.path, surprise_score=0.35)

# 8. QA receives enriched context
qa_context = f"{hope_analysis['combined']}\n\n{dev_output}\n\n{stm.get_context_string()}"
```

### Example 2: Spawn Without Memory (Current)

```python
# 1. User request
user_prompt = "Create authentication system"

# 2. Decompose into subtasks
subtasks = [
    {'id': '1', 'description': 'Implement JWT token generation'},
    {'id': '2', 'description': 'Implement password hashing'},
    {'id': '3', 'description': 'Create login endpoint'}
]

# 3. Spawn tasks in parallel
for subtask in subtasks:
    asyncio.create_subprocess_exec(
        'python', '-c', f"execute_task('{subtask['description']}')"
    )
    # ❌ No ARC gap detection
    # ❌ No HOPE analysis
    # ❌ No Elisya reframing
    # ❌ No CAM surprise tracking
    # ❌ No STM context
```

### Example 3: Spawn WITH Memory (Proposed)

```python
# 1. User request
user_prompt = "Create authentication system"

# 2. HOPE analysis for task decomposition
hope_summary = quick_hope_analysis(user_prompt)

# 3. Decompose with context
subtasks = [
    {'id': '1', 'description': 'Implement JWT token generation', 'hope_summary': hope_summary},
    {'id': '2', 'description': 'Implement password hashing', 'hope_summary': hope_summary},
    {'id': '3', 'description': 'Create login endpoint', 'hope_summary': hope_summary}
]

# 4. ARC + STM enrichment
stm = get_stm_buffer()
for subtask in subtasks:
    # ARC gap detection
    gaps = await detect_conceptual_gaps(subtask['description'])

    # STM context
    recent = stm.get_context_string(max_items=3)

    # Enrich description
    subtask['enriched'] = f"{recent}\n{gaps}\n{hope_summary}\n\n{subtask['description']}"

    # Execute with enriched context
    result = await execute_spawn(subtask['enriched'])

    # Update STM
    stm.add_message(result[:500], source='spawn')
```

---

## 🎯 CONCLUSION

**Pipeline Memory:** ✅ **EXCELLENT** - All 5 systems integrated
**Spawn Memory:** ⚠️ **NEEDS WORK** - Only HOPE easily usable

**Priority Fixes:**
1. **HIGH:** Add STM global singleton usage in spawn tasks
2. **MEDIUM:** Add ARC gap detection before spawn execution
3. **LOW:** Add HOPE quick analysis for subtask decomposition

**Implementation Estimate:**
- STM integration: 30 minutes
- ARC integration: 1 hour
- HOPE integration: 15 minutes

**Total:** ~2 hours for full spawn memory integration

---

**Report by:** Claude Sonnet 4.5
**Date:** 2026-01-31
**Next Steps:** Implement spawn memory integration (see recommended fixes)
