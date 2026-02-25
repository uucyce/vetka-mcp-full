# Mode Architecture v1 (Core + Extensible Workflows)

Date: 2026-02-21  
Status: Draft v1 (Product + Data + Runtime Contract)

## Purpose

This document fixes one core direction for VETKA:

1. Keep `Directed Mode` as stable causal/time baseline.  
2. Build `Knowledge Mode` as controlled semantic restructuring (not random graph).  
3. Add specialized workflow modes as modular extensions (MCP-heavy where needed), without polluting Core.

---

## Lineage (Evolution of Thought)

This v1 is explicitly based on:

- `docs/136_ph_Knowledge level_from_Phase 72/input_matrix_idea.txt`
- `docs/136_ph_Knowledge level_from_Phase 72/сердце Knowledge Mode_Grok.txt`
- `docs/besedii_google_drive_docs/besedii_best_part.txt`
- `docs/155_ph/MARKER_155_RECON_DIRECTED_KNOWLEDGE_MODE_SWITCH.md`

Evolution summary:

1. `input_matrix_idea.txt` defines universal relations:
   - explicit/import
   - temporal (`created(A) < created(B)` + similarity threshold)
   - referential/citation
2. Knowledge-level docs define Y as semantic hierarchy signal (not just filesystem depth).
3. Recon 155 showed runtime split and failure modes:
   - mode switch exists but needs stricter scoped behavior and DAG constraints
   - metadata pass-through is incomplete for robust knowledge building

---

## MARKER_155.MODE_ARCH.V1.CORE_SPLIT

### Directed Mode (Core)

Goal:
- Maximum readability of provenance/sequence.

Primary structure:
- filesystem hierarchy + temporal order inside branches.

Rules:
- deterministic layout
- conservative geometry changes only
- no aggressive semantic rewiring

### Knowledge Mode (Core)

Goal:
- reveal new, useful relations across folders and sources.

Primary structure:
- scoped seed set + controlled semantic expansion + typed edges.

Rules:
- must remain explainable (every edge has "why")
- must remain acyclic in visual causal layer
- must stay within node/edge budgets

---

## MARKER_155.MODE_ARCH.V1.USER_SCENARIOS

### Scenario 1: Right-click folder -> Knowledge

Behavior:
1. Selected folder = scope seed.
2. Build knowledge graph from scoped files.
3. Add semantic neighbors from outside scope (budgeted).
4. Show resulting graph with typed edges and reason labels.

User value:
- finds non-obvious dependencies and related artifacts.

### Scenario 1A: Right-click file -> Top links

Behavior:
1. Selected file = scope seed.
2. Show top related files by relation type and confidence.
3. Optional expand action to full folder-level Knowledge view.

User value:
- fast local intelligence without graph overload.

### Scenario 2: Root folder -> Project Knowledge view

Behavior:
1. Root selected.
2. Full project knowledge synthesis with stricter thinning.
3. All non-selected worlds hidden (or high fade).

User value:
- cross-domain map of project causality and semantics.

---

## MARKER_155.MODE_ARCH.V1.DATA_CONTRACT

Canonical edge schema (shared across Directed/Knowledge consumers):

```json
{
  "source": "node_id",
  "target": "node_id",
  "type": "contains|explicit|temporal|reference|semantic|chat|artifact|media_chunk",
  "weight": 0.0,
  "confidence": 0.0,
  "metadata": {
    "evidence": "string",
    "created_at_delta": 0,
    "sim_score": 0.0
  }
}
```

Canonical node metadata (minimum for Knowledge correctness):

- `path`, `name`, `type`, `parent_folder`, `depth`
- `created_time`, `modified_time`, `updated_at`
- `mime_type`, `modality`
- `size_bytes`, `content_hash`

Fallback policy for time:
- `created_time -> modified_time -> updated_at -> 0`

---

## MARKER_155.MODE_ARCH.V1.KNOWLEDGE_RUNTIME

Knowledge build pipeline (v1):

1. `scope seed`: collect files of selected folder/file/root.
2. `semantic expansion`: add external neighbors by similarity.
3. `relation typing`: explicit + temporal + reference + semantic.
4. `edge thinning`: top-k per node by typed priority.
5. `DAG projection`: keep causal orientation (older -> newer) and remove/redirect cycle-causing links for layered view.
6. `topological layering`: assign levels by longest-path/Kahn order.
7. `render`: scoped graph in focus, non-scoped hidden or strongly faded.

Default guardrails:

- semantic expansion budget: 20 (folder), 8 (file), 80 (root)
- semantic threshold: 0.72
- top-k outgoing: 2
- top-k incoming: 2

---

## MARKER_155.MODE_ARCH.V1.WHY_EDGE_EXPLAINABILITY

Every rendered edge in Knowledge mode must expose:

- relation type
- confidence
- evidence snippet (`import line`, `cite path`, `time+sim`)

This is mandatory for trust and for debugging failed layouts.

---

## MARKER_155.MODE_ARCH.V1.WORKFLOW_EXTENSIONS

Core keeps only lightweight mode logic. Heavy workflows are modular:

- `workflow/code_context` (Core-ready)
- `workflow/video_context` (MCP-heavy)
- `workflow/audio_context` (MCP-heavy)
- `workflow/3d_context` (MCP-heavy)
- `workflow/market_context` (specialized plugin/MCP)

Rule:
- Core provides selection, scoping, and typed graph contract.
- Workflow module provides domain-specific extraction and actions.

---

## MARKER_155.MODE_ARCH.V1.UI_CONTROL_MODEL

Minimal control set (v1):

1. `Mode`: Directed / Knowledge
2. `Scope`: File / Folder / Root
3. `Expansion`: Low / Medium / High
4. `Relations`: [explicit, temporal, ref, semantic] toggles
5. `Why`: edge explanation on hover/click

Optional next:
- include/exclude folder chips for project-level Knowledge views.

---

## MARKER_155.MODE_ARCH.V1.PHASE_PLAN

### Phase A (now)

1. Metadata pass-through completion (scanner -> knowledge builder).
2. Knowledge scoped build with semantic expansion budget.
3. Topological layering + edge thinning default.
4. File-level "Top links" mode action.

### Phase B

1. Per-scope mode persistence.
2. Relation explainability panel.
3. Root-level include/exclude controls.

### Phase C

1. Workflow modules per domain (video/audio/3d/market).
2. MCP integrations on top of the same graph contract.

---

## MARKER_155.MODE_ARCH.V1.ACCEPTANCE_CRITERIA

1. Switching folder to Knowledge never collapses into non-readable spaghetti.  
2. Graph remains causally layered for temporal/causal edges.  
3. External semantic neighbors appear, but within budget.  
4. Every non-contains edge is explainable.  
5. Same scope gives deterministic structure under same data snapshot.

---

## MARKER_155.MODE_ARCH.V1.RISKS

1. Over-expansion causes visual overload.
2. Missing metadata weakens temporal logic.
3. Mixed relation priorities can break readability if unthinned.
4. Different datasets may require adaptive thresholds.

Mitigation:
- enforce budgets,
- completeness audit logs,
- typed priority weights,
- deterministic tie-breakers.

---

## MARKER_155.MODE_ARCH.V1.NOTES

This document is a base architecture contract, not a final layout formula.
Formula tuning remains iterative, but must stay inside this contract:

- scoped,
- explainable,
- budgeted,
- DAG-readable.
