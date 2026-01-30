# HAIKU RECON 06: CAM (Context-Aware Memory) Architecture

**Agent:** Haiku
**Date:** 2026-01-28
**Task:** Analyze CAM system and its integration with storage

---

## CAM FILES FOUND

| File | Lines | Purpose |
|------|-------|---------|
| `src/orchestration/cam_engine.py` | 1312 | Main CAM engine |
| `src/orchestration/cam_event_handler.py` | 526 | Event-driven integration |
| `src/monitoring/cam_metrics.py` | 376 | Performance monitoring |
| `src/orchestration/services/cam_integration.py` | 154 | Orchestrator integration |

---

## CAM CORE CONCEPTS

### VETKANode Structure
```python
VETKANode {
    id: UUID
    path: filesystem path
    embedding: 768D (Gemma:300m)
    activation_score: [0.0, 1.0]
    children: [node_ids]
    metadata: dict
}
```

### Two Operating Modes

**A) Embedding-Based (Full mode with Qdrant/Weaviate)**
- Uses cosine similarity between embeddings
- Requires EmbeddingService ("embeddinggemma:300m" via Ollama)

**B) Heuristic-Based (Fallback if embeddings unavailable)**
- `calculate_surprise(content)` → float [0.0-1.0]
- Factors: unique_ratio, entropy, code_score, context_diff

---

## FOUR CAM OPERATIONS (per NeurIPS 2025 CAM paper)

### Thresholds (from Grok)
```
SIMILARITY_THRESHOLD_NOVEL = 0.7   (similarity < 0.7)
SIMILARITY_THRESHOLD_MERGE = 0.92  (similarity >= 0.92)
ACTIVATION_THRESHOLD_PRUNE = 0.2   (activation < 0.2)

SURPRISE_THRESHOLDS:
  > 0.65 → BRANCH (create new branch)
  0.30-0.65 → APPEND (add to existing folder)
  < 0.30 → MERGE (duplicate, skip)
```

### Operation 1: BRANCHING
```
handle_new_artifact(artifact_path, metadata)
    ├─ Generate embedding for new artifact
    ├─ Compare with existing nodes (cosine similarity)
    ├─ Find most similar node
    └─ Decision:
        ├─ similarity < 0.7 → BRANCH (new branch)
        ├─ 0.7-0.92 → MERGE_PROPOSAL (suggest to user)
        └─ >= 0.92 → VARIANT (mark as duplicate)
```
**Target:** < 1000ms per artifact

### Operation 2: PRUNING
```
prune_low_entropy(threshold=0.2)
    ├─ Calculate activation_score for each node:
    │   activation = relevance + connectivity_bonus + recency_bonus
    ├─ If score < threshold → mark for deletion
    └─ Requires user confirmation
```
**Target:** > 85% accuracy

### Operation 3: MERGING
```
merge_similar_subtrees(threshold=0.92)
    ├─ For each node pair:
    │   ├─ Collect descendant embeddings
    │   ├─ Calculate mean embedding per branch
    │   └─ Cosine similarity between means
    ├─ If similarity >= 0.92:
    │   ├─ Merge B into A
    │   ├─ Transfer B's metadata to A's merged_variants
    │   └─ Rebind B's children to A
    └─ Update layout
```
**Target:** > 85% accuracy

### Operation 4: ACCOMMODATION (Procrustes interpolation)
```
accommodate_layout(reason)
    ├─ Save old_positions
    ├─ Calculate new_positions (Sugiyama layout)
    ├─ Procrustes alignment: old → new
    └─ Return animation config:
        {duration: 750ms, easing: 'ease-in-out-cubic'}
```
**Target:** 60 FPS smooth animation

---

## CAM ↔ QDRANT/WEAVIATE CONNECTION

### How CAM Uses Qdrant
```
CAM Operations → Qdrant
    ├─ scroll() → get all files for tree building
    ├─ similarity search → find similar branches for merge
    └─ embedding storage → 768D vectors for cosine similarity
```

### Collections Used
- `VetkaTree` - Hierarchical nodes with embeddings
- `VetkaLeaf` - Detailed file information
- `VetkaChangeLog` - History of all changes
- `VetkaTrash` - Nodes marked for deletion

### Triple Write Integration
```
Each new artifact writes to 3 stores:
    1. Qdrant (vetka_elisya collection) - embeddings for similarity search
    2. Weaviate (backup for consistency)
    3. ChangeLog (VetkaChangeLog collection) - audit trail
```

---

## CAM CHECKPOINTS & PERSISTENCE

### State Saved In:

**A) MCPStateBridge (Phase 55)**
- MCP server state snapshots
- Persisted in `data/mcp_state.json`

**B) EliSyaStateService (Phase 50)**
- Elisya state (shared memory for agents)
- Includes CAM state

**C) ChatHistoryManager**
- Messages (including surprise scores)
- `data/chat_history.json`

**D) CAMToolMemory (Phase 75.1)**
```python
{
    tool_activations: Dict[tool_name][context_key] = score,
    usage_history: List[ToolUsageRecord]
}
# to_dict() / from_dict() for persistence
```

---

## CAM ↔ SEARCH INTEGRATION

```
Search Pipeline:
    UnifiedSearchBar → useSearch() → /api/search → QueryDispatcher
                                                        │
CAM Integration Points:                                 ▼
    ├─ add_query_to_history(query, embedding)
    ├─ Query-based activation scoring
    ├─ Influences prune/merge decisions
    └─ Search results affect node scores
```

---

## KNOWLEDGE MODE (Separate Tree View)

### Two Visualization Modes

**A) Directory Mode (default)**
```
Root
├─ Folders (dir nodes)
└─ Files (leaf nodes)
```
Endpoint: `GET /api/tree/data?mode=directory`

**B) Knowledge Mode (semantic)**
```
Tags (from file clustering)
├─ Chain edges (semantic similarity)
├─ Knowledge levels (concept hierarchy)
└─ RRF scoring (hybrid search)
```
Endpoint: `GET /api/tree/data?mode=semantic`

### Knowledge Graph Structure
```python
{
    tags: [{id, name, files, position}],
    edges: [(tag1, tag2, similarity)],
    chain_edges: [(file1, file2, relevance)],
    positions: {node_id: {x, y, z}},
    knowledge_levels: {level: [nodes]},
    rrf_stats: {mean_score, distribution}
}
```

---

## CAM TOOL MEMORY (Phase 75.1 - JARVIS Effect)

### Tracked VETKA Tools
- `view_document(path)`
- `search_files(query)`
- `get_viewport()`
- `pin_files(paths)`
- `focus_node()`
- `expand_folder()`

### Context Keys
- `folder_path`: "folder:src/orchestration"
- `file_extension`: "ext:py"
- `query_type`: "query:where_is"
- `viewport_zoom`: "zoom:close|medium|overview"

### Activation Scoring
```
success_bonus: +0.15 for successful use
recency_weight: +0.1 for freshness
exponential_decay: * 0.95 per hour
Range: [0.0, 1.0]
```

### JARVIS Suggestion
```
If top score >= 0.6:
    "CAM suggests: search_files (activation: 0.85)"
```

---

## GLOBAL SINGLETONS

```python
_cam_engine_instance     # get_cam_engine(memory_manager)
_cam_event_handler       # get_cam_event_handler()
_cam_tool_memory_instance # get_cam_tool_memory()
_metrics_instance        # get_cam_metrics()
```

---

## PHASE MARKERS IN CAM CODE

| Phase | Feature |
|-------|---------|
| 16 | CAM Engine & Dynamic Restructuring |
| 17 | Surprise Metric for file-level novelty |
| 35 | EvalAgent + CAM integrated |
| 36.1 | Unified EmbeddingService |
| 51.2-51.4 | Enhanced logging, Event-driven Handler |
| 54.1 | CAM Integration Service refactored |
| 75.1 | CAM Tool Memory with JARVIS suggestions |
| 92 | Standalone surprise calculation |

---

## ANSWERS TO KEY QUESTIONS

### 1. How is CAM connected to Weaviate/Qdrant?
- **Qdrant**: Primary storage for embeddings, similarity search
- **Weaviate**: Backup via Triple Write, BM25 text search
- CAM scrolls through VetkaTree for all files, uses similarity for merge decisions

### 2. Where are CAM checkpoints stored?
- MCPStateBridge: `data/mcp_state.json`
- EliSyaStateService: Embedded in Elisya State
- ChatHistoryManager: `data/chat_history.json`
- CAMToolMemory: to_dict() → can be saved to JSON

### 3. How does CAM integrate with search?
- `add_query_to_history()` tracks queries
- Query embeddings affect node activation scores
- Search results influence prune/merge decisions

### 4. Is there a separate tree for Knowledge mode?
- **Same data layer** (Qdrant) but **two visualization modes**
- Directory Mode: filesystem hierarchy
- Knowledge Mode: semantic clustering with tags and chain edges
