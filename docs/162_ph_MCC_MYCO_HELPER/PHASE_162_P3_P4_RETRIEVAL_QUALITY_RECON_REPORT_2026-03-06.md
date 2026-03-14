# PHASE 162 — P3.P4 Retrieval Quality Recon Report (2026-03-06)

Status: `RECON + MARKERS`
Protocol: `RECON -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`

## Scope
Next slice after `P3.P3`:
1. Connect MYCO hidden index to real retrieval path (not just manifest counters).
2. Add glossary alias normalization based on canonical memory glossary.
3. Add quality gates + coverage tests for hidden retrieval relevance.

## Recon Findings
1. Hidden index ingestion is implemented:
- `src/services/myco_memory_bridge.py::reindex_hidden_instruction_memory()`
- Stores chunks via triple-write with metadata `hidden_index=true`, `index_scope=myco_instructions`.

2. Runtime MYCO fastpath currently does **not** retrieve hidden chunks:
- `src/api/routes/chat_routes.py::_build_myco_quick_reply()` uses only payload summary (`hidden_index.source_count`) and orchestration snapshot.
- No semantic retrieval query over hidden corpus is called on quick MYCO path.

3. API surfaces exist and are stable:
- `POST /api/mcc/myco/hidden-index/reindex`
- `POST /api/mcc/myco/context`

4. Canonical alias source exists:
- `docs/besedii_google_drive_docs/VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md`
- Contains terms for DAG/STM/ENGRAM/MGC/CAM/JEPA/etc.

5. Current test coverage for phase-162 validates contracts and payload shape, but not retrieval relevance or alias normalization quality.

## Gaps (to close in P3.P4)
1. Missing retrieval bridge from quick MYCO path to hidden corpus chunks.
2. Missing query alias expansion for memory glossary terms.
3. Missing retrieval quality gate (minimum relevance/top-k policy/fallback behavior).
4. Missing regression tests for retrieval + alias behavior.

## Markers (P3.P4)
1. `MARKER_162.P3.P4.MYCO.RETRIEVAL_BRIDGE.V1`
2. `MARKER_162.P3.P4.MYCO.GLOSSARY_ALIAS_EXPANSION.V1`
3. `MARKER_162.P3.P4.MYCO.RETRIEVAL_QUALITY_GATE.V1`
4. `MARKER_162.P3.P4.MYCO.RETRIEVAL_COVERAGE_TESTS.V1`

## Narrow Implementation Plan (for GO)
1. Add hidden retrieval helper in `myco_memory_bridge.py`:
- input: `query`, `focus`, `active_project_id`
- output: compact top-k snippets with source path + score
- filter: `metadata.hidden_index=true`, `index_scope=myco_instructions`

2. Add alias normalization helper:
- load canonical glossary terms and synonyms from `VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md`
- expand query with safe alias map (bounded expansion)

3. Wire retrieval into `chat_routes.py` quick MYCO branch:
- include retrieval snippets in prompt assembly before `_build_myco_quick_reply`
- keep fallback deterministic if retrieval unavailable

4. Add tests:
- retrieval bridge contract
- alias expansion contract
- quality gate/fallback contract
- phase-162 aggregate run

## Verify Plan
Run:
- `pytest -q tests/test_phase162_p1_myco_helper_contract.py tests/test_phase162_p2_myco_topbar_title_contract.py tests/test_phase162_p3_p1_hidden_memory_contract.py tests/test_phase162_p3_p2_orchestration_memory_contract.py <new P3.P4 tests>`

Pass criteria:
1. Existing phase-162 tests remain green.
2. New retrieval tests assert deterministic fallback when retrieval is empty.
3. Alias-expanded query path is covered by unit contract tests.

## GO Gate
Ready for narrow implementation command:
`GO 162-P3.P4`
