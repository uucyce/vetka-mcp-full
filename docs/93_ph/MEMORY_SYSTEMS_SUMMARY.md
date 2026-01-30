# VETKA Memory Systems Summary
**Phase 93 - Complete Memory Architecture Documentation**

**Date:** January 25, 2026
**Status:** COMPREHENSIVE DOCUMENTATION
**Last Updated:** Phase 90.8 (Scanner and Watcher fully working)

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Memory Components Overview](#memory-components-overview)
3. [Elisium - Compression System](#elisium---compression-system)
4. [CAM - Context-Aware Memory](#cam---context-aware-memory)
5. [Engram - User Memory System](#engram---user-memory-system)
6. [Triple Memory - Combined Architecture](#triple-memory---combined-architecture)
7. [API Endpoints](#api-endpoints)
8. [Configuration & Integration](#configuration--integration)
9. [Key Files and Implementation Details](#key-files-and-implementation-details)

---

## Executive Summary

VETKA implements a sophisticated **three-layer memory architecture** that combines:

1. **Elisium** - Age-based embedding compression (768D → 384D → 256D → 64D)
2. **CAM (Constructivist Agentic Memory)** - Dynamic tree restructuring with branching, pruning, and merging
3. **Engram** - User preference memory with RAM cache + Qdrant persistence

These systems work together to create a **"living knowledge system"** that evolves with usage patterns, compresses old data intelligently, and personalizes user interactions across model changes.

---

## Memory Components Overview

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│           External Reality (Filesystem, Web, Media)         │
└─────────────────────────────────────────────────────────────┘
                            ↓
    ┌──────────────────────────────────────────────────────┐
    │      Memory Sync Engine + Orchestrator              │
    │  ├─ Snapshot & Diff (Track changes)                 │
    │  ├─ CAM Operations (Branch/Prune/Merge)             │
    │  ├─ Compression (Age-based)                         │
    │  └─ User Preferences (Engram)                       │
    └──────────────────────────────────────────────────────┘
                    ↓           ↓           ↓
        ┌───────────────────────────────────────┐
        │    Unified Memory Layers              │
        ├───────────────────────────────────────┤
        │ Active Memory:    768D full embeddings│
        │ Archived Memory:  256-384D compressed │
        │ Trash Memory:     Soft delete + TTL   │
        └───────────────────────────────────────┘
                    ↓           ↓           ↓
    ┌──────────┬────────────┬──────────────┐
    ↓          ↓            ↓
Qdrant DB   Weaviate DB   User Preferences
Vectors     Metadata       (JSON + Qdrant)
```

---

## Elisium - Compression System

### Purpose
Progressive memory compression following human cognition's "forgetting curve." Older, less-used memories compress to save storage while maintaining semantic meaning.

### Location
- **Primary:** `/src/memory/compression.py` (Phase 77.4)
- **DEP Graph:** `/src/memory/dep_compression.py` (Phase 77.5)
- **Integration:** `/src/memory/jarvis_prompt_enricher.py` (Phase 92 ELISION)

### How It Works

#### Embedding Compression Schedule

```python
Age              Dimension   Quality    Layer       Confidence
─────────────────────────────────────────────────────────────
0-1 days         768D        100%       active      1.0
1-7 days         768D        99%        active      0.95-0.99
7-30 days        384D        90%        active      0.85
30-90 days       256D        80%        archived    0.70
90-180 days      64D         60%        archived    0.50
180+ days        lazy        varies     archived    0.30
```

#### Dependency Graph Compression

```python
Age              Mode        Dependencies    Recompute on Access
────────────────────────────────────────────────────────────────
0-30 days        full        all edges       N/A
30-90 days       top_3       3 strongest     if needed
90-180 days      top_1       1 primary       if needed
180+ days        none        none            on demand (fast)
```

### Key Classes

#### `MemoryCompression`
```python
class MemoryCompression:
    """Age-based embedding compression."""

    async def compress_by_age(node: NodeState, age_days: int = None) -> CompressedNodeState:
        """Compress single node - returns CompressedNodeState with reduced embedding"""

    async def compress_batch(nodes: List[NodeState]) -> List[CompressedNodeState]:
        """Batch compress multiple nodes efficiently"""

    def get_quality_degradation_report() -> Dict[str, Any]:
        """Returns: {nodes_tracked, avg_quality, degraded_count, quality_distribution}"""
```

#### `CompressedNodeState` (Dataclass)
```python
@dataclass
class CompressedNodeState:
    path: str                           # Node path
    embedding: List[float]              # Compressed embedding (768/384/256/64D)
    embedding_dim: int                  # Actual dimension after compression
    original_dim: int = 768             # For tracking compression ratio
    dep_mode: Literal["full", "top_3", "top_1", "none"]  # Dependency mode
    confidence: float = 1.0             # Decays with age
    memory_layer: Literal["active", "archived"] = "active"
    compression_ratio: float = 1.0      # original_dim / embedding_dim
    age_days: int = 0
    quality_score: float = 1.0          # Search quality (1.0 = full, decreases with compression)
```

### Quality Metrics
- **compression_ratio**: How many times smaller (e.g., 768/384 = 2.0 = 50% reduction)
- **quality_score**: Expected search quality (1.0 = full, 0.6 = 64D)
- **confidence**: Trustworthiness (1.0 = fresh, decays with age)
- **memory_layer**: Location indicator (active vs archived)

### Integration Points
1. **JARVIS Enricher** - Applies ELISION compression to JSON context before LLM calls
2. **Memory Sync Engine** - Called during periodic compression cycles
3. **CAM Operations** - Triggered when nodes age past thresholds
4. **Orchestrator** - Before API responses, compress old data

### Configuration

```python
# In MemoryCompression class
COMPRESSION_SCHEDULE = [
    (0, 768, "active", 1.0),     # Fresh: full quality
    (7, 768, "active", 0.99),    # Week: still full
    (30, 384, "active", 0.90),   # Month: reduce to 384D
    (90, 256, "archived", 0.80), # Quarter: reduce to 256D
    (180, 64, "archived", 0.60), # Half year: summary only
]

CONFIDENCE_DECAY = {
    0: 1.0,    1: 0.99,   7: 0.95,  30: 0.85,
    90: 0.70,  180: 0.50, 365: 0.30
}
```

---

## CAM - Context-Aware Memory

### Purpose
Implements **Constructivist Agentic Memory** (NeurIPS 2025 CAM paper, arXiv:2510.05520).

Dynamic tree restructuring that:
- **Branches**: Creates new subtrees for novel content
- **Prunes**: Marks low-activation branches for removal
- **Merges**: Combines similar subtrees to reduce redundancy
- **Accommodates**: Smooth layout transitions with Procrustes interpolation

### Location
- **Core Engine:** `/src/orchestration/cam_engine.py` (Phase 35)
- **Event Handler:** `/src/orchestration/cam_event_handler.py` (Phase 51.3)
- **Integration Service:** `/src/orchestration/services/cam_integration.py` (Phase 54.1)
- **Metrics:** `/src/monitoring/cam_metrics.py` (Phase 16)

### How It Works

#### Core Operations

**1. Branching (handle_new_artifact)**
```python
async def handle_new_artifact(artifact_path: str, metadata: Dict) -> CAMOperation:
    """
    Decision tree:
    - similarity < 0.7 → BRANCH (create new branch)
    - 0.7 ≤ similarity < 0.92 → MERGE_PROPOSAL (suggest merge)
    - similarity ≥ 0.92 → VARIANT (mark as duplicate)
    """
```

**2. Pruning (prune_low_entropy)**
```python
async def prune_low_entropy(threshold: float = 0.2) -> List[str]:
    """
    Marks low-activation branches for deletion (requires user confirmation).
    Returns list of node IDs marked for pruning.
    """
    activation_score = calculate_activation_score(node_id)
    if activation_score < threshold:
        node.is_marked_for_deletion = True
```

**3. Merging (merge_similar_subtrees)**
```python
async def merge_similar_subtrees(threshold: float = 0.92) -> List[Tuple[str, str]]:
    """
    Finds similar branches (>92% similarity) and merges them.
    Preserves metadata using merged_variants tracking.
    Returns: [(old_id, merged_into_id), ...]
    """
```

**4. Accommodation (accommodate_layout)**
```python
async def accommodate_layout(reason: str = "structure_changed") -> Dict:
    """
    Smooth tree restructuring using Procrustes interpolation.
    Returns: {old_positions, new_positions, duration=0.75s, easing='ease-in-out-cubic'}
    """
```

#### Surprise Metric (Novelty Detection)

```python
def calculate_surprise(content: str, context: Optional[str] = None) -> float:
    """
    Determines how novel/surprising content is (0.0-1.0).

    Heuristics:
    - unique_words / total_words (25% weight)
    - Character entropy (Shannon, 25% weight)
    - Structural complexity (code indicators, 15% weight)
    - Context difference (35% weight)

    Returns: 0.0 (predictable) to 1.0 (completely novel)
    """
```

#### CAM Operation Decisions

```python
def decide_cam_operation_for_file(surprise: float) -> str:
    """
    Thresholds from NeurIPS 2025 CAM paper:
    - surprise > 0.65  → 'branch'   (create new subtree)
    - 0.30 < surprise ≤ 0.65  → 'append'  (add to existing)
    - surprise ≤ 0.30  → 'merge'   (duplicate, compress)
    """
```

### Key Classes

#### `VETKANode` (Dataclass)
```python
@dataclass
class VETKANode:
    id: str
    path: str
    name: str
    depth: int
    embedding: Optional[np.ndarray]  # 768D Gemma embedding
    children: List[str]
    parent: Optional[str]
    activation_score: float = 0.5     # Relevance score (0-1)
    is_marked_for_deletion: bool = False
    duplicate_of: Optional[str] = None
    created_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any]
```

#### `CAMOperation` (Result)
```python
@dataclass
class CAMOperation:
    operation_type: str      # "branch", "merge", "prune", "accommodate", etc.
    node_ids: List[str]      # Affected node IDs
    duration_ms: float       # Operation timing
    success: bool
    details: Dict[str, Any]  # Additional metadata
```

#### `VETKACAMEngine` (Main Class)
```python
class VETKACAMEngine:
    """Constructivist Agentic Memory Engine."""

    # Thresholds
    SIMILARITY_THRESHOLD_NOVEL = 0.7    # Below = new branch
    SIMILARITY_THRESHOLD_MERGE = 0.92   # Above = merge candidates
    ACTIVATION_THRESHOLD_PRUNE = 0.2    # Below = prune candidates

    # Methods
    calculate_activation_score(branch_id) → float
    compute_branch_similarity(branch_a_id, branch_b_id) → float
    handle_new_artifact(artifact_path, metadata) → CAMOperation
    prune_low_entropy(threshold) → List[str]
    merge_similar_subtrees(threshold) → List[Tuple[str, str]]
    accommodate_layout(reason) → Dict
```

### Activation Score Calculation

```python
activation_score = (
    avg_relevance_to_queries +        # Cosine similarity to query embeddings
    connectivity_bonus +              # min(0.2, num_children * 0.02)
    recency_bonus                     # max(0, 0.1 * (1 - time_since_access / 86400))
)
# Bounded to [0.0, 1.0]
```

### CAM Tool Memory

```python
class CAMToolMemory:
    """Remembers VETKA tool usage patterns for JARVIS-like suggestions."""

    VETKA_TOOLS = [
        'view_document',    # View file in 3D viewport
        'search_files',     # Search in tree
        'get_viewport',     # Get current viewport state
        'pin_files',        # Pin files for context
        'focus_node',       # 3D camera focus
        'expand_folder',    # Tree expansion
    ]

    def record_tool_use(tool_name: str, context: Dict, success: bool) → None
    def suggest_tool(context: Dict, top_n: int = 3) → List[Tuple[str, float]]
    def get_jarvis_hint(context: Dict) → Optional[str]
```

### Configuration

```python
# From cam_engine.py
SIMILARITY_THRESHOLD_NOVEL = 0.7      # New branch threshold
SIMILARITY_THRESHOLD_MERGE = 0.92     # Merge candidate threshold
ACTIVATION_THRESHOLD_PRUNE = 0.2      # Pruning threshold
EMBEDDING_MODEL = "embeddinggemma:300m"
EMBEDDING_DIM = 768
```

### Integration Points
1. **Orchestrator** - CAM operations triggered on artifact events
2. **Tree Routes** - Calculate surprise metrics for visualization
3. **CAM Integration Service** - Periodic maintenance cycle (prune, merge)
4. **Event Handler** - Process CAM_EVENT types

---

## Engram - User Memory System

### Purpose
**Hybrid RAM + Qdrant architecture** for fast user preference lookups with automatic offloading and temporal decay.

Features:
- **O(1) RAM lookups** for hot preferences (usage > 5)
- **Qdrant cold storage** for infrequently accessed preferences
- **Temporal decay** - confidence decreases over time
- **Automatic pruning** - low-confidence preferences removed
- **23-43% token savings** in prompt enrichment

### Location
- **Main Class:** `/src/memory/engram_user_memory.py` (Phase 76.3)
- **User Preferences Schema:** `/src/memory/user_memory.py`
- **JARVIS Enricher Integration:** `/src/memory/jarvis_prompt_enricher.py` (Phase 76.3 + 92)

### How It Works

#### Five-Level Architecture

**Level 1: Static RAM Hash Table (O(1) Lookup)**
```python
async def engram_lookup(query: str) -> Optional[List[Dict]]:
    """
    Basic pattern matching on RAM cache.
    Returns: List of matching patterns sorted by confidence.
    """
    memory = get_engram_user_memory()
    for user_id, preferences in memory.ram_cache.items():
        # Search through cached preferences
```

**Level 2: CAM + ELISION Integration**
```python
async def enhanced_engram_lookup(query: str, level: int = 2) -> Optional[List[Dict]]:
    """
    Level 2: CAM surprise integration + ELISION compression.
    - Calculates surprise score on content
    - Triggers ELISION compression if surprise > 0.7
    - Returns: results with compression_triggered flag
    """
```

**Level 3: Temporal Weighting**
```python
async def enhanced_engram_lookup(query: str, level: int = 3) -> Optional[List[Dict]]:
    """
    Level 3: Temporal decay weighting.
    - Boosts recent accesses (10% decay per day)
    - final_score = surprise * 0.6 + temporal_weight * 0.4
    """
```

**Level 4: Cross-Session Persistence**
```python
async def enhanced_engram_lookup(query: str, level: int = 4) -> Optional[List[Dict]]:
    """
    Level 4: Qdrant-based cross-session persistence.
    - Combines RAM results with Qdrant search
    - Survives application restarts
    """
```

**Level 5: Advanced Features (Framework)**
```python
async def enhanced_engram_lookup(query: str, level: int = 5) -> Optional[List[Dict]]:
    """
    Level 5: Advanced API integration and predictions.
    (Currently: placeholder structure with mock values)
    - contextual_relevance: 0.8
    - predictive_confidence: 0.7
    - cross_domain_links: []
    """
```

### Key Classes

#### `UserPreferences` (Dataclass)
```python
@dataclass
class UserPreferences:
    user_id: str
    viewport_patterns: ViewportPatterns        # zoom, focus areas, style
    tree_structure: TreeStructure              # depth, grouping, layout
    project_highlights: ProjectHighlights      # current project, priorities
    communication_style: CommunicationStyle    # formality, detail, language
    temporal_patterns: TemporalPatterns        # time of day, seasonality
    tool_usage_patterns: ToolUsagePatterns     # frequent tools, shortcuts

    # Each category has:
    # - confidence: float (0-1)
    # - last_updated: str (ISO timestamp)
```

#### `EngramUserMemory` (Main Class)
```python
class EngramUserMemory:
    """Hybrid RAM + Qdrant user memory."""

    COLLECTION_NAME = "vetka_user_memories"
    VECTOR_SIZE = 768  # Gemma embeddings
    OFFLOAD_THRESHOLD = 5  # Promote to RAM after 5 accesses
    DECAY_RATE = 0.05  # Per week
    MIN_CONFIDENCE = 0.1  # Prune below this

    def __init__(self, qdrant_client: Optional[QdrantClient] = None)
    def get_preference(user_id: str, category: str, key: str) → Optional[Any]
    def set_preference(user_id: str, category: str, key: str, value: Any, confidence: float = 0.5)
    def get_user_preferences(user_id: str) → Optional[UserPreferences]
    def decay_preferences(user_id: str)  # Exponential decay: confidence *= e^(-0.05 * weeks)
    def clear_user(user_id: str)
    def get_stats() → Dict[str, Any]
```

### Usage Example

```python
# Initialize
memory = get_engram_user_memory(qdrant_client)

# Get preference (O(1) from RAM if cached)
zoom_levels = memory.get_preference('danila', 'viewport_patterns', 'zoom_levels')
# Returns: [1.0, 1.5, 2.0]

# Set preference
memory.set_preference('danila', 'communication_style', 'formality', 0.2, confidence=0.8)

# Decay old preferences (exponential)
memory.decay_preferences('danila')

# Get statistics
stats = memory.get_stats()
# Returns: {ram_cache_size, users_in_ram, qdrant_available, offload_threshold, ...}
```

### Temporal Decay Formula

```python
# Exponential decay
new_confidence = current_confidence * math.exp(-DECAY_RATE * weeks_old)

# DECAY_RATE = 0.05 per week
# Example: 50% confidence after ~13.9 weeks (3.2 months)
```

### Offload Logic

```
1. User accesses preference in Qdrant
2. usage_count incremented
3. If usage_count >= 5:
   - Load full preferences from Qdrant
   - Add to RAM cache
   - Future accesses are O(1)
```

### Persistence

```python
# Serialization
json_str = preferences.to_json()  # Converts to JSON

# Storage
qdrant.upsert(
    collection="vetka_user_memories",
    points=[PointStruct(
        id=user_id,
        vector=[0.0] * 768,  # Dummy vector
        payload=preferences.to_dict()
    )]
)

# Cross-session loading
preferences = UserPreferences.from_dict(qdrant.retrieve(...).payload)
```

### Integration with JARVIS Prompt Enricher

```python
class JARVISPromptEnricher:
    """Model-agnostic prompt enrichment with user preferences."""

    def enrich_prompt(
        self,
        base_prompt: str,
        user_id: str,
        model: str = "claude"
    ) -> str:
        """
        Adds user preferences to prompt.
        - Works with any model (DeepSeek, Claude, Qwen, Gemma, etc.)
        - Applies ELISION compression to JSON context
        - 23-43% token savings
        """
```

---

## Triple Memory - Combined Architecture

### How the Three Systems Work Together

```
┌────────────────────────────────────────────────────────────┐
│           User Request / Query / Artifact Event            │
└────────────────────────────────────────────────────────────┘
                            ↓
            ┌───────────────────────────────┐
            │   Engram Level 1: O(1) Lookup │ (Fastest)
            │   (User Preferences)          │
            └───────────────────────────────┘
                   Hit? ↓ Miss? ↓
            ┌───────────────────────────────┐
            │  CAM Surprise Detection       │
            │  (Is this novel content?)     │
            └───────────────────────────────┘
                            ↓
            ┌───────────────────────────────┐
            │  Branching / Merging Decision │
            │  (Tree restructuring)         │
            └───────────────────────────────┘
                            ↓
            ┌───────────────────────────────┐
            │  Age-based Compression        │
            │  (Elisium: 768D → 64D)        │
            └───────────────────────────────┘
                            ↓
            ┌───────────────────────────────┐
            │  Response with Enrichment     │
            │  (JARVIS context injection)   │
            └───────────────────────────────┘
```

### Data Flow Example

**Scenario: New file added to codebase**

1. **Scanner detects change** → New file created
2. **CAM engine triggered** → `handle_new_artifact()`
3. **Surprise calculated** → 0.75 (novel content)
4. **Decision made** → BRANCH (create new subtree)
5. **Tree restructures** → Accommodation animation
6. **Engram updated** → User interest patterns recorded
7. **Age timer starts** → Future compression scheduling
8. **Compression applied** → When age > threshold

**Timeline:**
- Day 1: 768D, confidence=1.0, active layer, all dependencies
- Week 2: 768D, confidence=0.95, active layer, all dependencies
- Month 1: 384D, confidence=0.85, active layer, all dependencies
- Day 30: 256D, confidence=0.70, archived layer, top_3 dependencies
- Day 90: 64D, confidence=0.50, archived layer, lazy recompute

### Unified Query Processing

```python
async def dynamic_semantic_search(query: str, scope: str = "all") -> List[Dict]:
    """
    Three-stage hybrid search:

    Stage 1: Engram O(1) (engram_o1)
    - Check RAM cache for preferences
    - If hit, return immediately

    Stage 2: Qdrant Vector Search (qdrant_cam_hybrid)
    - Search vector DB
    - Apply CAM surprise scoring
    - Enhance with user preferences

    Stage 3: Fallback (qdrant_fallback)
    - Simple vector search without CAM

    Stage 4: Empty Result Handling (failed_fallback)
    - Graceful degradation
    """

    if scope in ["all", "engram"]:
        engram_results = await engram_lookup(query)
        if engram_results:
            return engram_results

    if scope in ["all", "qdrant", "memory"]:
        qdrant_results = await qdrant_search(query)
        # Apply CAM enhancement
        if self._cam_engine:
            for result in qdrant_results:
                result['surprise_score'] = calculate_surprise(result['content'])
                result['source'] = 'qdrant_cam_hybrid'
        return qdrant_results

    # Fallback paths...
```

---

## API Endpoints

### Memory Routes

#### Search Endpoints

```
GET /api/search
├─ query: str (search term)
├─ scope: str = "all" (all|engram|qdrant|memory)
├─ limit: int = 10 (max results)
└─ Returns: {source, results: [{path, relevance, surprise_score, ...}]}

GET /api/search/semantic
├─ query: str
├─ embedding_model: str = "embeddinggemma:300m"
└─ Returns: {results with vector similarity scores}

GET /api/search/cam
├─ query: str
├─ include_surprise: bool = true
└─ Returns: {results with CAM surprise metrics}
```

#### Engram Endpoints

```
GET /api/engram/preferences/{user_id}
└─ Returns: UserPreferences (all categories with confidence)

GET /api/engram/preference/{user_id}/{category}/{key}
└─ Returns: {value, confidence, last_updated}

POST /api/engram/preference/{user_id}/{category}/{key}
├─ value: Any
├─ confidence: float = 0.5
└─ Returns: {success, updated}

GET /api/engram/stats/{user_id}
└─ Returns: {ram_cache_size, usage_counts, ...}

DELETE /api/engram/user/{user_id}
└─ Clears all preferences for user
```

#### CAM Endpoints

```
GET /api/cam/metrics
└─ Returns: {branching, pruning, merging, accommodation stats}

GET /api/cam/surprise/{artifact_id}
├─ artifact_path: str
├─ sibling_ids: List[str] (optional)
└─ Returns: {surprise_score: float, operation: str}

POST /api/cam/branch
├─ artifact_path: str
├─ metadata: Dict
└─ Returns: {operation_result}

POST /api/cam/merge
├─ branch_a_id: str
├─ branch_b_id: str
└─ Returns: {merged_id, old_metadata}

GET /api/cam/activation-scores
└─ Returns: {branch_id: activation_score, ...}
```

#### Compression Endpoints

```
GET /api/compression/quality-report
└─ Returns: {avg_quality, degraded_count, quality_distribution}

POST /api/compression/compress-by-age
├─ node_id: str
├─ age_days: int (optional)
└─ Returns: {compression_ratio, new_dim, quality_score}

GET /api/compression/schedule
└─ Returns: compression schedule thresholds
```

#### Tree Visualization Endpoints

```
GET /api/tree
└─ Returns: tree structure with surprise metrics for all files

GET /api/tree/node/{node_id}
├─ include_embeddings: bool = false
├─ include_stats: bool = true
└─ Returns: VETKANode with metadata

GET /api/tree/metrics
└─ Returns: {total_nodes, branching_ops, merge_candidates, ...}
```

### Implementation Notes

- All endpoints use **singleton memory instances** (LazyLoader pattern)
- Endpoints apply **permission filtering** based on agent type
- CAM operations are **async** with event emission
- Compression operations **gracefully degrade** if libraries unavailable (e.g., sklearn)

---

## Configuration & Integration

### Environment Variables

```bash
# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=optional

# Weaviate Configuration
WEAVIATE_HOST=http://localhost:8080

# Memory Layers
ACTIVE_MEMORY_THRESHOLD_DAYS=7
ARCHIVE_MEMORY_THRESHOLD_DAYS=30
TRASH_TTL_DAYS=90

# Compression
COMPRESSION_ENABLE_ELISION=true
COMPRESSION_PCA_AVAILABLE=true  # sklearn

# CAM
CAM_SIMILARITY_NOVEL=0.7
CAM_SIMILARITY_MERGE=0.92
CAM_ACTIVATION_PRUNE=0.2

# Engram
ENGRAM_OFFLOAD_THRESHOLD=5
ENGRAM_DECAY_RATE=0.05
ENGRAM_MIN_CONFIDENCE=0.1
```

### Initialization

```python
# Memory Initialization (in main.py or orchestrator)

# 1. Initialize Qdrant client
from src.memory.qdrant_client import get_qdrant_client
qdrant = get_qdrant_client()

# 2. Initialize Engram memory
from src.memory.engram_user_memory import get_engram_user_memory
engram = get_engram_user_memory(qdrant_client=qdrant.client)

# 3. Initialize CAM engine
from src.orchestration.cam_engine import get_cam_engine
cam_engine = get_cam_engine()

# 4. Initialize JARVIS enricher
from src.memory.jarvis_prompt_enricher import JARVISPromptEnricher
enricher = JARVISPromptEnricher(
    engram_memory=engram,
    elision_config=ElisionConfig(enabled=True, level=2)
)

# 5. Start CAM maintenance cycle
from src.orchestration.services.cam_integration import CAMIntegrationService
cam_service = CAMIntegrationService(cam_engine)
asyncio.create_task(cam_service.maintenance_cycle())
```

### Integration with Orchestrator

```python
# From orchestrator_with_elisya.py

async def execute_workflow(self, task: str, context: Dict):
    """Memory-aware workflow execution."""

    # Step 1: Check sync status (Phase 77)
    fs_snapshot = await self.scanner.create_snapshot()
    memory_snapshot = await self.memory.get_current_snapshot()
    diff = await self.diff_engine.diff(memory_snapshot, fs_snapshot)

    # Step 2: Ask Hostess curator if significant changes
    if len(diff.added) + len(diff.deleted) > 10:
        decisions = await self.hostess.sync_with_user(diff)
        # Apply user decisions to memory

    # Step 3: Compress old data by age
    await self.compression.compress_all_by_age()

    # Step 4: Enrich prompt with user preferences
    enriched_prompt = await self.enricher.enrich_prompt(
        base_prompt=task,
        user_id=context.get('user_id', 'default'),
        model=context.get('model', 'claude')
    )

    # Step 5: Execute workflow with CAM enhancement
    cam_results = await self._cam_engine.handle_new_artifact(
        artifact_path=context.get('artifact_path'),
        metadata=context.get('metadata', {})
    )

    # Step 6: Standard execution
    return await super().execute_workflow(enriched_prompt, context)
```

---

## Key Files and Implementation Details

### File Structure

```
src/memory/
├── compression.py              # Elisium: Age-based embedding compression
├── dep_compression.py          # Dependency graph compression (Phase 77.5)
├── engram_user_memory.py       # Engram: User preferences (Phase 76.3)
├── jarvis_prompt_enricher.py   # JARVIS: Prompt enrichment with ELISION (Phase 76.3 + 92)
├── user_memory.py              # UserPreferences dataclass and schema
├── elision.py                  # ELISION compression core (Phase 92)
├── snapshot.py                 # Memory snapshots for sync (Phase 77.1)
├── diff.py                     # Diff algorithm for memory sync (Phase 77.2)
├── trash.py                    # Trash memory management (Phase 77.6)
├── qdrant_client.py            # Qdrant connection management
├── hostess_memory.py           # Hostess agent memory interface
└── user_memory_updater.py      # Background preference updater

src/orchestration/
├── cam_engine.py               # CAM: Dynamic tree restructuring (Phase 35)
├── cam_event_handler.py        # Event-driven CAM processing (Phase 51.3)
├── orchestrator_with_elisya.py # Main orchestrator with memory integration
└── services/
    ├── cam_integration.py      # CAM service wrapper (Phase 54.1)
    └── api_key_service.py      # API key management

src/agents/
├── tools.py                    # Tool registry (CAM, Engram, Compression tools)
├── base_agent.py               # Base agent with memory support
└── hostess_agent.py            # Hostess agent (memory curator, Phase 76)

src/api/routes/
├── semantic_routes.py          # Search and Engram routes
├── tree_routes.py              # Tree visualization with CAM metrics
├── debug_routes.py             # Debug/monitoring endpoints
└── [other routes]

docs/
├── 77_78_ph/vetka_memory_sync_complete.md  # Memory sync protocol
├── PHASE_14-15/17_CAM_memory.txt           # CAM research
└── 91_ph_Big_Picle/HAIKU_REPORT_*.md       # Audit reports
```

### Phase History

```
Phase 14-15: CAM Research (NeurIPS 2025 paper)
Phase 16:    CAM Metrics Tracking
Phase 17:    CAM Surprise Metric Implementation
Phase 35:    CAM Engine Core Implementation
Phase 51.3:  Event-Driven CAM Operations
Phase 54.1:  CAM Integration Service
Phase 66:    Elisium Research & Design
Phase 67.2:  CAM Engine Singleton
Phase 75.1:  CAM Tool Memory (JARVIS hints)
Phase 76.3:  Engram User Memory + JARVIS Enricher
Phase 77-78: Memory Sync Protocol (Compression, Backup, Diff)
Phase 80+:   Scanner & Watcher Integration
Phase 90.8:  Scanner and Watcher fully working
Phase 91:    Architecture Audit Reports
Phase 92:    ELISION Compression Integration
Phase 93:    MEMORY_SYSTEMS_SUMMARY (this document)
```

### Quality Metrics & Monitoring

#### Tracked Metrics

```python
# From cam_metrics.py
metrics = {
    'branching': {'count': 45, 'avg': 150.5, 'min': 50, 'max': 2000},  # ms
    'pruning': {'count': 12, 'avg': 80.2, 'min': 20, 'max': 300},
    'merging': {'count': 8, 'avg': 200.5, 'min': 100, 'max': 500},
    'accommodation': {'count': 25, 'avg': 120.3, 'min': 50, 'max': 400},
    'total_nodes': 1250,
    'total_edges': 3420
}

# Compression quality report
quality = {
    'nodes_tracked': 1250,
    'avg_quality': 0.87,
    'degradation_rate': 0.32,
    'quality_distribution': {
        'full_quality': 450,
        'high_quality': 380,
        'medium_quality': 320,
        'low_quality': 100
    }
}
```

#### Monitoring Endpoints

```
GET /api/memory/health
└─ Returns: {qdrant_status, weaviate_status, memory_stats}

GET /api/memory/compression-status
└─ Returns: quality report, compression ratios

GET /api/memory/cam-metrics
└─ Returns: operation timings, total nodes/edges

GET /api/memory/engram-stats/{user_id}
└─ Returns: preferences count, cache size, decay status
```

---

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Typical Time |
|-----------|-----------|---|
| Engram Level 1 (RAM lookup) | O(1) | <1ms |
| Engram Level 4 (Qdrant lookup) | O(1) by user_id | 5-50ms |
| CAM branching | O(n) where n=nodes | 50-2000ms |
| CAM merging (pair similarity) | O(n²) pairs | 100-500ms |
| Compression by age | O(n) nodes | ~100ms for 1000 nodes |
| Surprise calculation | O(m) content size | 1-50ms |
| Decay (per user) | O(k) categories | 10-100ms |

### Space Complexity

| Component | Space (per entity) | Example |
|-----------|---|---|
| VETKANode (minimal) | ~5KB | 1000 nodes = 5MB |
| 768D embedding | 3KB | 1000 embeddings = 3MB |
| 64D embedding | 256B | 1000 archived = 256KB |
| UserPreferences | 1-2KB | 100 users = 100-200KB |
| Qdrant index | varies | Depends on collection size |

### Memory Compression Savings

```
Original State (all 768D):
- 1000 nodes × 3KB = 3MB

Compressed State (mixed):
- 450 active @ 768D = 1.35MB
- 380 recent @ 384D = 570KB
- 320 old @ 256D = 320KB
- 100 ancient @ 64D = 25KB
─────────────────────────
Total: 2.2MB (27% reduction)

After 6 months:
- Most nodes compressed to 256D or 64D
- ~50-70% total space savings
```

---

## Future Enhancements (Planned)

### Phase 94+

1. **Real ELISION Algorithm**
   - Implement actual semantic-aware path compression
   - Replace mock truncation
   - Target: 40-60% additional compression on JSON context

2. **Procrustes Animation**
   - Full layout interpolation for tree restructuring
   - Smooth 3D transitions in frontend
   - Collision detection

3. **Level 5 Engram Implementation**
   - API integration for contextual analysis
   - Cross-domain correlation engine
   - Predictive suggestions

4. **Memory Persistence**
   - CAM tool memory to JSON
   - Compression state versioning
   - Rollback capability

5. **Advanced Security**
   - HMAC signing for compressed embeddings
   - AES encryption for archived data
   - Audit logging for all operations

6. **Visualization**
   - Real-time memory layer display
   - Compression ratio tracking UI
   - Quality metrics dashboard

---

## References

### Research Papers
- **CAM (NeurIPS 2025):** arXiv:2510.05520 - "Constructivist Agentic Memory"
- **GitHub Prototype:** https://github.com/rui9812/CAM
- **Procrustes Interpolation:** Standard linear algebra technique for smooth transitions

### Related Documentation
- `/docs/77_78_ph/vetka_memory_sync_complete.md` - Memory Sync Protocol
- `/docs/91_ph_Big_Picle/HAIKU_REPORT_04_CAM_TOOLS.md` - CAM Tools Analysis
- `/docs/91_ph_Big_Picle/HAIKU_REPORT_05_ENGRAM_LEVELS.md` - Engram Levels
- `/docs/91_ph_Big_Picle/HAIKU_REPORT_09_ELISION.md` - ELISION Analysis
- `/docs/PHASE_14-15/17_CAM_memory.txt` - Original CAM Research

### Key Implementation Files
1. `/src/memory/compression.py` - 504 lines, age-based compression
2. `/src/memory/engram_user_memory.py` - 678 lines, user preferences
3. `/src/orchestration/cam_engine.py` - 1312 lines, core CAM engine
4. `/src/memory/jarvis_prompt_enricher.py` - JARVIS enrichment
5. `/src/api/routes/semantic_routes.py` - API endpoints

---

## Conclusion

VETKA's memory systems create a **cognitive architecture** for AI assistance that:

✓ **Learns from usage** (Engram tracks user preferences)
✓ **Evolves dynamically** (CAM restructures tree actively)
✓ **Compresses intelligently** (Elisium follows forgetting curves)
✓ **Personalizes automatically** (JARVIS enriches all interactions)
✓ **Survives model changes** (Eternal memory via Qdrant persistence)

The three systems work together to transform VETKA from a static knowledge graph into a **living, learning, personalizable knowledge system** that adapts to user behavior and project dynamics in real time.

---

**Document Generated:** 2026-01-25
**Status:** COMPREHENSIVE REFERENCE
**Next Update:** Post Phase 93 implementation
**Maintained By:** VETKA Architecture Team
