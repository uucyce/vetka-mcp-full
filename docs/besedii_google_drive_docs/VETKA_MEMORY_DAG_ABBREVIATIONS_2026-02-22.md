# VETKA Memory + DAG Abbreviations (Canonical Glossary)

Status: Canonical glossary for MCC/Mycelium architecture discussions.
Updated: 2026-03-16 (v2: AURA, True ENGRAM, REFLEX/CORTEX/CUT added, cognitive stack clarified)

## Core graph and orchestration

- VETKA: Visual Enhanced Tree Knowledge Architecture.
  - knowledge structure skeleton/tree.
- MYCELIUM: Multi-agent Yielding Cognitive Execution Layer for Intelligent Unified Management.
  - distributed agent network ("brain under the ground"). Execution layer.
- ELISYA: Efficient Language-Independent Synchronization of Yielding Agents.
  - TWO components:
    - A) Python module (`src/elisya/`): Context middleware — "nervous system". ElisyaState (shared agent memory), ElisyaMiddleware (LOD filtering, semantic tint, Qdrant enrichment, few-shots), ModelRouter (task→LLM routing), ProviderRegistry (multi-provider calls + key rotation). The LANGUAGE agents use to think together.
    - B) Qdrant collection `vetka_elisya`: File embeddings for semantic code search. Separate from the module.
- ELISION: Efficient Language-Independent Symbolic Inversion of Names.
  - compression/forgetting/abstraction layer ("memory compressor"). 40-60% token savings.

- MCC: Mycelium Command Center (single-window control interface).
- DAG: Directed Acyclic Graph (approved acyclic architecture view).
- SCC: Strongly Connected Components (cycle condensation unit).
- Sugiyama: Layered DAG layout family (readable hierarchy rendering).
- HNSW: Hierarchical Navigable Small World graph (ANN index/search over embeddings).

## Cognitive stack (memory + processing)

Listed in cognitive processing order (input → output):

### User layer
- AURA: Adaptive User Response Archive (NEW, renamed from "ENGRAM user memory").
  - user behavior profile: communication style, viewport patterns, tool preferences.
  - `src/memory/aura_store.py` (rename from `engram_user_memory.py`).
  - RAM cache (L0) + Qdrant `vetka_user_memories` (L2).
  - Feeds into: REFLEX signal #4 (weight 0.10).

### Working memory
- STM: Short-Term Memory (active working context).
  - last 5-10 interactions, deque with temporal decay.
  - `src/memory/stm_buffer.py`. Phase 99.
  - Decay: `weight *= (1 - 0.1 * age_minutes)`.
  - Feeds into: REFLEX signal #5 (weight 0.10).

### Attention
- CAM: Constructivist Agentic Memory (saliency/surprise-driven relevance signals).
  - surprise detection (0.0-1.0), boosts STM entries.
  - `src/orchestration/cam_engine.py`.
  - Feeds into: REFLEX signal #2 (weight 0.15).

### Knowledge memory (two levels)
- ENGRAM: Deterministic knowledge cache — L1. (CORRECTED: was mislabeled)
  - True Engram = O(1) hash lookup for frequent patterns. Inspired by DeepSeek Engram (N-gram addressing).
  - `src/memory/engram_cache.py` (NEW, not yet implemented). `data/engram_cache.json`.
  - Auto-populated: L2 learning matched ≥3 times → promoted to L1.
  - NOT the same as old "ENGRAM user memory" (that is now AURA).
- Qdrant semantic memory — L2.
  - `VetkaResourceLearnings` (patterns, pitfalls, optimizations from pipeline runs).
  - `vetka_elisya` (file index, code context).
  - `VetkaTree`, `VetkaGroupChat`, `VetkaArtifacts` (other collections).
  - Cosine similarity search, ~200ms. Non-deterministic.

### Cache hierarchy
- MGC: Memory Graph Cache (graph cache + persistence/forgetting controls).
  - 3-tier: Gen0 (RAM) → Gen1 (Qdrant) → Gen2 (JSON files).
  - `src/memory/mgc_cache.py`. Phase 99.
  - Feeds into: REFLEX signal #8 (weight 0.05).

### Tool selection
- REFLEX: Reactive Execution & Function Linking EXchange.
  - 8-signal tool scorer. No LLM calls, pure in-memory scoring, <5ms.
  - `src/reflex/scorer.py`, `src/reflex/registry.py`.
  - Signals: semantic(0.30), CAM(0.15), CORTEX(0.15), AURA(0.10), STM(0.10), phase(0.10), HOPE(0.05), MGC(0.05).

### Learning loop
- CORTEX: Layer 3 of REFLEX — feedback learning loop.
  - records tool effectiveness: success_rate, usefulness, verifier_pass.
  - `src/reflex/feedback.py`. Append-only JSONL.
  - Score: `success*0.40 + useful*0.35 + verifier*0.25`. Exponential decay.
  - Feeds into: REFLEX signal #3 (weight 0.15).
- Resource Learnings: post-pipeline lesson extraction.
  - `src/orchestration/resource_learnings.py`. Stores in Qdrant `VetkaResourceLearnings`.
  - Auto-promotes to ENGRAM L1 when learning matched ≥3 times.

### Abstraction
- HOPE: Hierarchical Optimized Processing for Enhanced understanding.
  - frequency decomposition: LOW (global) / MID (detail) / HIGH (specifics).
  - `src/agents/hope_enhancer.py`. Phase 8/99.
  - Feeds into: REFLEX signal #7 (weight 0.05), STM truncation.

### Media
- CUT: Cinema Utility Tools.
  - Video editing cognition: scene graph, montage, audio sync.
  - Separate subsystem for media processing.

## Project state (not cognitive, but memory-adjacent)

- project_digest.json: auto-updated project state (phase, achievements, pending, git).
  - Updated by: pre-commit hook, task completion, post-commit.
- TaskBoard: task lifecycle management via MCP.
  - Status history, failure_history, resource_learnings, agent attribution.
  - The "single source of truth" for what agents are doing.

## Predictive and reasoning layers

- JEPA: Joint Embedding Predictive Architecture (predictive embedding layer). Status: dormant.
- ARC: Abstraction/Reasoning cycle (hypothesis-test-refine for architecture decisions). Status: active standalone.
- HOPE: (see Abstraction above).

## Clustering and geometry

- HDBSCAN: Hierarchical Density-Based Spatial Clustering (cluster discovery in embedding space).
- CoM: Concentration of Measure (high-dimensional concentration behavior).
- PCA: Principal Component Analysis (dimensional decorrelation / whitening pre-step).
- SVD: Singular Value Decomposition (spectral factorization).
- GFT: Graph Fourier Transform (signal decomposition on graph laplacian eigenbasis).
- Laplacian: Graph operator L = D - A used for spectral diagnostics.
- Spectral Gap: separation in eigenvalues indicating connectivity/community structure.
- Fiedler value/vector: second laplacian eigenvalue/vector for connectivity partition insight.
- Eigengap heuristic: heuristic for selecting number of communities from spectral gaps.
- JL: Johnson-Lindenstrauss projection principle for distance-preserving dimension reduction.
- Levy's Lemma: concentration result for Lipschitz functions on high-dimensional sphere.
- Gaussian concentration: concentration bounds for functions under Gaussian measure.
- Lipschitz function: function with bounded sensitivity; central in concentration bounds.
- Discrepancy Theory: balance quality of distributions/partitions.
- Equitable Coloring: balanced partition/coloring with near-equal class sizes.
- Graphon: continuous/limit graph representation for large-scale approximation.
- Terence Tao (in this context): Set of geometry/spectral/discrepancy techniques applied to graph and embedding quality.

## Working interpretation in VETKA

- Base architecture truth: deterministic DAG from approved design process.
- Runtime truth: observed graph from scanners/input_matrix.
- Predictive suggestions: JEPA overlay with confidence.
- Human-approved architecture DAG remains canonical.
- Process canonical chain: Research -> Design -> Plan -> Implement -> Verifier/Eval.
- Cognitive processing chain: AURA → STM → CAM → ENGRAM(L1) → Qdrant(L2) → REFLEX → MYCELIUM → CORTEX → (loop).
- Self-learning: CORTEX → Resource Learnings → Qdrant(L2) → promote to ENGRAM(L1) when pattern ≥3 matches.

## Reference documents

- /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/besedii_google_drive_docs/terens_tao_GROK.txt
- /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/besedii_google_drive_docs/Convolutional_neural_network_GROK.txt
- /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/besedii_google_drive_docs/Jepa_GROK-VETKA.txt
- /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/besedii_google_drive_docs/besedii_best_part.txt
- /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/mycelium__bdmitriipro_transcript_youtube.txt
- /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/besedii_google_drive_docs/Opus 46 Discrepancy Theory & Equitable Coloring (Tao гл. 12) .txt
- /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/besedii_google_drive_docs/Opus46# 🌊 Fourier Analysis on Graphs (Tao гл. 13) → Spectral Tools для Архитектора VETKA + JEPA.txt
- /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/186_memory/VETKA_COGNITIVE_STACK_ARCHITECTURE.md (NEW)
- /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/186_memory/VETKA_DYNAMIC_MEMORY_BLUEPRINT.md (NEW)
