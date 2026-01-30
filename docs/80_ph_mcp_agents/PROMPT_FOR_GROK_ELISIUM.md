# Research Request: Elisium - Dynamic Compression Language + CAM + Engram Integration

**To:** Grok / VETKA Council Research Team
**From:** VETKA AI Team (Danila + Opus)
**Subject:** Elisium Architecture - When CAM triggers compression dialects
**Date:** 2026-01-22

---

## Executive Summary

We need to research how to unify three concepts into one coherent memory architecture:

1. **Elisya Language** - Context compression with LOD levels
2. **Elisya Middleware** - Pre-prompting orchestrator
3. **CAM (Constructivist Agentic Memory)** - Surprise metrics & activation
4. **Engram** (DeepSeek) - O(1) lookup hash tables for static patterns

**Core Question:** When a subtree exceeds N nodes AND CAM uniqueness coefficient > threshold, should we dynamically generate a local compression language for that subtree?

---

## Current VETKA Architecture

```
User Query
    ↓
┌─────────────────────────────────────────────────────────────┐
│  ELISYA MIDDLEWARE (Pre-prompting)                          │
│  - LOD levels: GLOBAL(500) → TREE(1500) → LEAF(3000) → FULL │
│  - Semantic tinting (security/performance filters)          │
│  - Qdrant vector search for similar contexts                │
│  - JSON pre-prompting (viewport + pinned files)             │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  CAM ENGINE (Surprise + Activation)                         │
│  - activation_score: 0.0-1.0 per node                       │
│  - surprise metrics via embeddings cosine distance          │
│  - branching (new artifacts)                                │
│  - pruning (low entropy nodes)                              │
│  - merging (similar subtrees)                               │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  TOOLS (Artifact Panel)                                     │
│  - VETKA tools: view_document, search_files, get_viewport   │
│  - Code tools: read_file, write_file, run_tests             │
│  - Weaviate tools (Elysia): search_semantic, camera_focus   │
└─────────────────────────────────────────────────────────────┘
    ↓
LLM (Qwen2 / Grok / Claude) → Response
```

---

## The Research Questions

### Question 1: CAM-Triggered Dialect Generation

**Hypothesis:** When a subtree has:
- `node_count > N` (e.g., 50+)
- `CAM.uniqueness_coefficient > 0.7` (high information density)

Then generate a LOCAL compression dialect for that subtree.

**Example:**
```python
# CAM detects: src/components/chat/ has 11 files, uniqueness=0.82

# Elisium generates dialect:
DIALECT_CHAT_V1 = {
    "_cp": "component",
    "_hk": "hook",
    "_st": "state",
    "_eff": "useEffect",
    "_ctx": "context"
}

# Compressed context (saves ~40% tokens):
"_cp:ChatPanel{_st:45,_hk:20} └_cp:MessageInput{_hk:3}"

# vs uncompressed:
"Component ChatPanel with 45 state variables, 20 hooks..."
```

**Research needed:**
- What threshold for N? (50? 100? dynamic based on total tree size?)
- What CAM uniqueness threshold triggers dialect? (0.7? 0.8?)
- How to version dialects when tree changes?

---

### Question 2: Engram Integration with Elisya

**DeepSeek Engram concept:** Hash table for O(1) lookup of static patterns (n-grams).

**How to integrate with VETKA:**

```
┌─────────────────────────────────────────────────────────────┐
│  ENGRAM LAYER (between Elisya and CAM)                      │
│                                                             │
│  IF CAM.surprise < 0.5 (low surprise = static pattern):     │
│     → Lookup in Engram hash table                           │
│     → Return cached compressed context                      │
│                                                             │
│  ELSE (high surprise = new/changing):                       │
│     → Full Elisya compression                               │
│     → Store result in Engram for future                     │
│                                                             │
│  Hash key: embedding vector of subtree                      │
│  Hash value: compressed dialect + context                   │
└─────────────────────────────────────────────────────────────┘
```

**Research needed:**
- What embedding model for hash keys? (embeddinggemma:300m? larger?)
- How to handle partial matches? (subtree changed 10%?)
- Memory budget for Engram table? (RAM vs Qdrant offload?)

---

### Question 3: Tools in Artifacts via Elisya

**Current state:** Tools defined in Python, injected to LLM as schemas.

**Proposed:** Elisya middleware manages tool availability based on context:

```python
# Elisya decides which tools are relevant based on:
# 1. Current LOD level
# 2. File types in viewport
# 3. User's recent actions (CAM memory)

class ElisyaToolManager:
    def get_tools_for_context(self, elisya_state) -> List[Tool]:
        if elisya_state.lod_level == LODLevel.GLOBAL:
            return [search_files, get_tree_context]  # High-level only

        elif elisya_state.lod_level == LODLevel.LEAF:
            # Full toolset for deep work
            return [read_file, write_file, run_tests, camera_focus]

        elif "chat" in elisya_state.semantic_path:
            # Context-specific tools
            return [view_component, edit_tsx, search_hooks]
```

**Research needed:**
- Should tools be artifacts (visible in UI artifact panel)?
- How to show "available tools" based on camera zoom?
- Tool suggestions via CAM (remember which tools user prefers)?

---

### Question 4: LangGraph / BMAD Integration Path

**Current:** Custom orchestrator with Elisya middleware.

**Future:** LangGraph for agent orchestration, BMAD for memory.

**Question:** How does Elisium fit?

```
LangGraph Router (PM → Architect → Dev → QA)
    ↓
┌─────────────────────────────────────────────────────────────┐
│  ELISIUM (Dynamic Dialect Layer)                            │
│  - Intercepts context before each agent                     │
│  - Checks CAM for subtree uniqueness                        │
│  - Generates/retrieves dialect from Engram                  │
│  - Compresses context with dialect                          │
│  - Passes to agent with dialect header                      │
└─────────────────────────────────────────────────────────────┘
    ↓
Agent (LLM with tools)
    ↓
BMAD Memory (long-term storage)
```

**Research needed:**
- Can Elisium be a LangGraph "middleware node"?
- How to share dialects across agents in same session?
- Where does BMAD fit vs Engram vs Qdrant?

---

## Existing Code Context

### Key Files to Reference:

1. **`src/elisya/middleware.py`** - ElisyaMiddleware class
   - `reframe(state, agent_type)` - Prepare context
   - `update(state, output, speaker)` - Update after execution
   - LODLevel enum (GLOBAL, TREE, LEAF, FULL)

2. **`src/orchestration/cam_engine.py`** - CAM Engine
   - `VETKANode` dataclass with `activation_score`
   - `handle_new_artifact()` - Branching
   - `prune_low_entropy()` - Pruning
   - Surprise calculation via embeddings

3. **`src/memory/engram_user_memory.py`** - Engram concept
   - Hybrid RAM + Qdrant storage
   - O(1) lookup for hot preferences
   - Temporal decay (confidence -= 0.05/week)

4. **`src/orchestration/orchestrator_with_elisya.py`** - Main orchestrator
   - Shows how Elisya integrates with agent calls
   - Tool injection patterns

---

## Deliverables Requested

### From Research Team:

1. **Feasibility Analysis**
   - Is CAM-triggered dialect generation worth complexity?
   - Token economics: when does dialect header cost < savings?

2. **Algorithm Sketch**
   ```
   Input: subtree, cam_metrics
   Output: dialect OR null (if not worth it)

   1. Check node_count > N
   2. Check cam.uniqueness > threshold
   3. Analyze common patterns (prefixes, types, structures)
   4. Generate abbreviation map
   5. Calculate break-even point
   6. Return dialect if savings > 20%
   ```

3. **Integration Path**
   - How to add Elisium layer to existing middleware
   - Engram table structure for dialect caching
   - CAM hooks for triggering dialect generation

4. **Prototype Code Sketch**
   - Python class `ElisiumDialectGenerator`
   - Integration with `ElisyaMiddleware.reframe()`

---

## Related Research

- **JSON ELISION** - 23-43% token savings (our baseline)
- **DeepSeek Engram** - Hash tables for static patterns
- **CAM Paper** (NeurIPS 2025) - Constructivist memory operations
- **Matryoshka Embeddings** - Hierarchical representations
- **HOPE/ARC** - Agent evaluation frameworks

---

## Success Criteria

Elisium is successful if:
1. **30%+ token reduction** on large subtrees (>50 nodes)
2. **<100ms overhead** for dialect lookup/generation
3. **Seamless integration** with existing Elisya middleware
4. **CAM-driven** - only activates when truly beneficial

---

**Priority:** Research/Exploration (Phase 89)
**Timeline:** Async - first report within 24-48h
**Format:** Markdown report with code sketches

---

*"Ветка как память для агентов, а агенты как двигатели"*
*- VETKA Philosophy*
