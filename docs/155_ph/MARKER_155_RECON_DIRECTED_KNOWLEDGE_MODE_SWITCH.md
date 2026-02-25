# MARKER_155 RECON: Directed + Knowledge Mode Switch (Folder-Scoped)

Date: 2026-02-18  
Scope: unify mode architecture, keep Directed stable, define Knowledge switch semantics, map remaining G-gaps.

Sources reviewed:
- `docs/besedii_google_drive_docs/besedii_best_part.txt`
- `docs/136_ph_Knowledge level_from_Phase 72/сердце Knowledge Mode_Grok.txt`
- `docs/136_ph_Knowledge level_from_Phase 72/input_matrix_idea.txt`
- `src/api/routes/tree_routes.py`
- `src/layout/fan_layout.py`
- `src/layout/knowledge_layout.py`
- `src/services/artifact_scanner.py`
- `src/scanners/qdrant_updater.py`

---

## MARKER_155.RECON.MODEL_SPLIT.ACTUAL_STATE

1. Directed tree API path is production-default: `GET /api/tree/data` builds folder/file DAG via `calculate_tree_layout()` in `fan_layout.py`.
2. Knowledge graph path exists separately: `GET/POST /api/tree/knowledge-graph` builds semantic graph via `knowledge_layout.py`.
3. Runtime folder-level switch between these paths is not unified in one user action yet (no single folder-scoped mode pipeline in `tree/data`).

Implication: mode architecture is present but split by endpoint, not by one folder interaction model.

---

## MARKER_155.RECON.DIRECTED_MODE.FINDINGS

From live audits (`TREE_AUDIT`) and code:

1. `x_overlaps=0` in tested scene means global horizontal sibling spacing is not primary failure.
2. Main Directed pain was vertical visual intrusion from tall file stacks and exact centerline chains in many single-child branches.
3. Directed currently remains the most stable base when layout formulas are minimally touched.

Conclusion: keep Directed deterministic and conservative; avoid aggressive global width rewrites.

---

## MARKER_155.RECON.KNOWLEDGE_MODE.FINDINGS

Useful from source docs and code:

1. Knowledge Mode should preserve tree readability principles from Directory/Directed, but hierarchy source changes:
   - Directed hierarchy source: filesystem parent/child.
   - Knowledge hierarchy source: semantic/tag/prerequisite graph.
2. `input_matrix_idea.txt` is directly actionable:
   - explicit relation
   - temporal relation (`created(A) < created(B)` + semantic threshold)
   - reference/citation relation
3. `knowledge_layout.py` already supports typed edges and classification payload, so extraction quality is now the main lever.

Conclusion: for Knowledge, priority is better relation extraction and stable mode switching, not new rendering physics.

---

## MARKER_155.RECON.GAP_MAP (G-series)

### G09 (UI/interaction in graph mode)
- Status: partial.
- Missing: robust folder-level mode switch UX contract (single click select, double-click/toggle mode, root scope behavior).
- Needed: exact interaction spec + persisted mode state.

### G12 (ingestion/search multimodal + graph linkage)
- Status: partial/implemented backend chunks exist.
- Missing: full relation lifecycle consistency from ingestion to visual graph in both modes.
- Needed: one canonical relation schema shared by Directed/Knowledge consumers.

### New split from this recon
- `G09-A`: Folder-scoped mode switch contract + UI action map.
- `G09-B`: Root-folder switch behavior (global rebuild and edge set swap).
- `G12-A`: relation extraction parity across content types.
- `G12-B`: typed-edge compatibility between `/api/tree/data` and `/api/tree/knowledge-graph`.

---

## MARKER_155.RECON.MODE_SWITCH.CONTRACT (Proposed)

Folder interaction:

1. `single click` on folder: select only.
2. `double click` (or context menu action): toggle mode for selected scope:
   - `Directed`
   - `Knowledge`
3. If scope is root folder:
   - full tree rebuild with selected mode dataset
   - edge semantics set switches with mode
   - camera anchor preserved if possible (avoid user disorientation)

Persistence:

- Store mode per scope (folder-id/root-id) in lightweight state store.
- On reload, restore last mode for active scope.

---

## MARKER_155.RECON.DEPENDENCY_SCHEMA.UNIFIED

Canonical edge schema for both modes:

```json
{
  "source": "node_id",
  "target": "node_id",
  "type": "contains|explicit|temporal|reference|semantic|chat|artifact|media_chunk",
  "weight": 0.0,
  "confidence": 0.0,
  "metadata": {
    "evidence": "string",
    "created_at_delta": 0
  }
}
```

Why: Directed and Knowledge can differ in layout logic but must consume one relation contract.

---

## MARKER_155.RECON.APPLICABILITY_FROM_EXTERNAL_RESEARCH

From external/NLP idea (NER/relation extraction):

What is useful now:
1. As optional pre-processor for Knowledge relation extraction (documents, scripts, media transcripts).
2. As confidence scorer, not as source of geometry.

What is not useful now:
1. Using NLP extraction to drive Directed layout geometry directly.

Rule:
- Directed = deterministic structural layout.
- Knowledge = enriched semantic graph with optional NLP extraction.

---

## MARKER_155.RECON.TAO.HDBSCAN_WHITENING_AUDIT

Input reviewed:
- `docs/besedii_google_drive_docs/terens_tao_GROK.txt`

What is confirmed in real code now:

1. HDBSCAN is already present in runtime pipelines:
   - `src/orchestration/semantic_dag_builder.py`
   - `src/layout/knowledge_layout.py`
   - `src/knowledge_graph/position_calculator.py` (via `import hdbscan`)

2. Whitening is NOT present in runtime clustering/projection path:
   - no `PCA(..., whiten=True)` in semantic DAG / knowledge layout paths
   - current preprocessing is mainly L2 normalization before clustering

3. Spectral graph health metrics (e.g., Laplacian spectral gap) are not implemented as operational checks.

Pragmatic value from Tao-summary for VETKA:
- Keep current HDBSCAN foundation.
- Add optional whitening before clustering as controlled enhancement (flagged rollout).
- Treat spectral metrics as diagnostics/monitoring, not as first-line layout replacement.

---

## MARKER_155.RECON.METADATA.KNOWLEDGE_LAYER_READINESS

Question audited: "Do we already collect all metadata needed for robust Knowledge layer?"

Short answer:
- **Collected at scan time: partially yes.**
- **Delivered to Knowledge builder at runtime: no (critical fields are currently dropped).**

### What scanner/updater writes (good base)

`src/scanners/qdrant_updater.py` writes rich payload for scanned files, including:
- `path`, `name`, `extension`, `mime_type`
- `size_bytes`
- `modified_time`
- `content_hash`
- `parent_folder`, `depth`
- `modality`, `source`, `type`

Browser ingest path (`src/api/routes/watcher_routes.py`) also writes:
- `created_time`, `modified_time`
- `parent_folder`, `relative_path`, `mime_type`, `size_bytes`

Artifacts path (`src/services/artifact_scanner.py`) has artifact-level metadata:
- `artifact_type`, `created_at`, `modified_at`, `source_chat_id`, `source_message_id`, etc.

### Where metadata is lost for Knowledge mode (core gap)

Knowledge loaders currently narrow payload too aggressively:
- `src/orchestration/semantic_dag_builder.py` (Qdrant scroll extractor)
- `src/layout/knowledge_layout.py` (Qdrant scroll extractor)

Both currently keep mostly:
- `path`, `name`, `extension`, `type`

and do **not pass through** important fields like:
- `created_time`, `modified_time`
- `parent_folder`, `mime_type`, `modality`
- `size_bytes`, `content_hash`, ingest/source qualifiers

Impact:
- temporal and modality-aware knowledge relations are weakened
- cross-mode parity (Directed vs Knowledge) breaks on richer metadata
- analytics/readability regressions become likely under large mixed datasets

### Mini-checklist: Metadata completion before Knowledge impl

1. Expand Knowledge payload intake (both loaders) to pass-through:
   - `created_time`, `modified_time`, `updated_at`
   - `parent_folder`, `depth`, `mime_type`, `modality`
   - `size_bytes`, `content_hash`, `source`
2. Define one canonical metadata contract shared by:
   - scanner/updater
   - semantic DAG builder
   - knowledge layout
3. Add strict fallback policy for missing time:
   - `created_time -> modified_time -> updated_at -> 0`
4. Add audit log line for metadata completeness ratio in Knowledge build:
   - e.g. `% nodes with created_time`, `% with modality`, `% with parent_folder`
5. Only after (1)-(4): enable whitening experiment flag for controlled rollout.

---

## MARKER_155.RECON.PRACTICAL_LAYOUT_GUIDE

Operational guidance to avoid repeated layout regressions:

1. Prepare clean graph primitives first:
   - reliable node set
   - reliable edge set
   - typed edges with confidence
   This is often harder than rendering itself.

2. Use the correct engine for hierarchy:
   - hierarchical DAG path should use layered/Sugiyama-style layout logic
   - in external libs this maps to `dot`, `sugiyama`, `hierarchical`, `layered` families.

3. Tune parameters explicitly (not implicit defaults):
   - inter-layer spacing
   - sibling spacing
   - edge routing/shape
   - collision/overlap guards
   Parameter set must be treated as part of API contract for mode stability.

---

## MARKER_155.RECON.EXTERNAL_DAG_TOOLS (Reference)

From external comparison (DAGitty / ggdag / Graphviz):

1. DAGitty
   - good for fast causal DAG prototyping
   - useful for reasoning/validation, not as VETKA runtime layout engine.

2. ggdag (R + ggplot2)
   - good for presentation-quality static visuals
   - useful for reporting snapshots, not for interactive VETKA scene runtime.

3. Graphviz (`dot`, Python wrapper)
   - strong hierarchical DAG layout baseline
   - best candidate for offline regression oracle:
     compare VETKA layout metrics against `dot` output on sampled subgraphs.

VETKA recommendation:
- Keep runtime engine internal (Directed: `fan_layout.py`, Knowledge: `knowledge_layout.py`).
- Use Graphviz offline for audit/testing:
  - crossing count comparison
  - layer-depth consistency
  - node order sanity checks
- Do not replace runtime renderer with external static toolchain.

### Mini-checklist: Offline Graphviz Comparison (Oracle)

1. Export sampled subgraph from VETKA response:
   - take one problematic root scope (e.g. `tests`, `docs/108_ph`, etc.)
   - save `nodes` + `edges` JSON from `/api/tree/data` or `/api/tree/knowledge-graph`.

2. Convert to DOT:
   - include only directed edges relevant to mode:
     - Directed: `contains` (+ optional strict dependency edges)
     - Knowledge: `explicit|temporal|reference|semantic`
   - preserve node ids and depth metadata if available.

3. Run Graphviz layered layout:
   - command baseline: `dot -Tplain subgraph.dot > subgraph.plain`
   - `dot` is the Sugiyama-like hierarchical engine reference.

4. Compute comparison metrics:
   - edge crossings (approx)
   - layer monotonicity violations (child below parent in chosen axis)
   - node order instability across repeated runs
   - span width ratio (`max_x - min_x`) runtime vs oracle.

5. Pass/Fail gate (pragmatic):
   - no new crossing regressions vs previous baseline
   - no increase in layer monotonicity violations
   - width ratio not exploding unexpectedly (set tolerance window).

6. Decision:
   - if runtime diverges strongly from oracle on same subgraph:
     - inspect spacing/order formulas before changing core hierarchy rules.

---

## MARKER_155.RECON.PLAN_A_B

Plan A (preferred):
1. Keep Directed stable.
2. Implement folder-scoped mode switch contract.
3. Reuse current Knowledge endpoint data with unified edge schema adapter.

Plan B (already agreed):
1. Manual node position correction workflow.
2. Persist user layout positions.
3. Optional local model/tool for overlap-fix suggestions with user approval.

---

## MARKER_155.RECON.READY_FOR_IMPL

Ready to implement next in narrow steps:

1. `G09-A`: mode switch interaction contract in UI (folder scope).
2. `G09-B`: root scope rebuild switching between `/api/tree/data` and `/api/tree/knowledge-graph`.
3. `G12-B`: adapter to unified edge schema in response payloads.
4. `Plan B foundation`: persisted node positions.
