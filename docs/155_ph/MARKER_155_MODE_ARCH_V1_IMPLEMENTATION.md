# MARKER_155 Mode Architecture v1 - Implementation Plan

Date: 2026-02-21  
Status: Active  
Scope: Phase A execution plan from `MODE_ARCHITECTURE_V1.md`

## References (Lineage)

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/155_ph/MODE_ARCHITECTURE_V1.md`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/155_ph/MARKER_155_RECON_DIRECTED_KNOWLEDGE_MODE_SWITCH.md`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/136_ph_Knowledge level_from_Phase 72/input_matrix_idea.txt`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/136_ph_Knowledge level_from_Phase 72/сердце Knowledge Mode_Grok.txt`

---

## MARKER_155.IMPL.V1.PHASE_A_ORDER

Execution order for Phase A:

1. **A.1 Metadata pass-through + completeness audit** (now)
2. A.2 Scoped knowledge build with semantic expansion budget
3. A.3 Topological layering + default edge thinning
4. A.4 File-level `Top Links` interaction

Rationale:
- UI behavior depends on relation quality.
- Relation quality depends on metadata completeness.

---

## MARKER_155.IMPL.V1.A1.GOAL

Guarantee that knowledge builders consume and preserve minimum canonical metadata contract:

- `path`, `name`, `type`, `parent_folder`, `depth`
- `created_time`, `modified_time`, `updated_at`
- `mime_type`, `modality`
- `size_bytes`, `content_hash`, `source`

and expose machine-readable completeness audit to API consumers.

---

## MARKER_155.IMPL.V1.A1.CODE_TARGETS

1. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/layout/knowledge_layout.py`
2. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/semantic_dag_builder.py`
3. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/tree_routes.py`

---

## MARKER_155.IMPL.V1.A1.CHANGES

### A1-1. Completeness metrics expansion

Track at least:
- with_created_time
- with_modified_time
- with_updated_at
- with_parent_folder
- with_modality
- with_mime_type
- with_size_bytes
- with_content_hash
- with_source
- with_depth

### A1-2. Time fallback audit

Track fallback path usage:
- created_from_created
- created_from_modified
- created_from_updated
- created_missing

and keep fallback policy:
- `created_time -> modified_time -> updated_at -> 0`

### A1-3. API visibility

Return metadata audit block from knowledge builder into `/api/tree/knowledge-graph` response.
Purpose: debug correctness without parsing long backend logs.

---

## MARKER_155.IMPL.V1.A1.ACCEPTANCE

1. `POST /api/tree/knowledge-graph` response contains `metadata_completeness`.
2. Audit contains percentages and fallback counters.
3. Completeness stats are logged once per build in compact form.
4. No regression in current Knowledge graph payload shape (`tags`, `edges`, `positions`, `knowledge_levels` still present).

---

## MARKER_155.IMPL.V1.A1.NOTES

- This phase does **not** change graph geometry policy.
- This phase does **not** alter relation thresholds.
- This phase is data-quality + observability only.

---

## MARKER_155.IMPL.V1.A2.GOAL

Implement scoped Knowledge expansion:

- Keep strict folder/file scope as seed.
- Add external semantic neighbors with fixed budget and threshold.
- Keep deterministic behavior and no global fallback contamination.

## MARKER_155.IMPL.V1.A2.CHANGES

1. Backend (`knowledge_layout.py`):
- Add `semantic_expansion_budget` and `semantic_expansion_threshold`.
- Compute scope seed from strict path matching.
- Expand via cosine similarity to scope centroid, top-N by budget.

2. API (`tree_routes.py`):
- Accept request fields:
  - `semantic_expansion_budget`
  - `semantic_expansion_threshold`
- Include these fields in KG cache signature to prevent stale cross-scope cache reuse.

3. Frontend (`useTreeData.ts` + `utils/api.ts`):
- Pass expansion controls to `/api/tree/knowledge-graph`.
- Use default budget policy:
  - file scope: 8
  - folder scope: 20
  - root-like scope: 80
- Default threshold: `0.72`.

## MARKER_155.IMPL.V1.A2.ACCEPTANCE

1. Scoped switch no longer leaks to full-global KG.
2. External neighbors appear but stay within budget.
3. Same scope + same snapshot gives deterministic expansion set.
4. Cache does not reuse KG from another scope/threshold/budget combination.
