# PHASE 162 — P3.P0 Hidden Memory Recon Report (2026-03-06)

Status: `RECON COMPLETE`
Protocol: `RECON -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`

## 1) Scope
Recon for Phase `162-P3.P0` (no behavioral code change):
1. Hidden instruction indexing for MYCO/agents.
2. ENGRAM payload for user + recent tasks across projects.
3. JEPA + local Gemma fast retrieval path.
4. Strict no-UI memory surface contract.

## 2) Markers (locked)
1. `MARKER_162.P3.MYCO.HIDDEN_TRIPLE_MEMORY_INDEX.V1`
2. `MARKER_162.P3.MYCO.README_SCAN_PIPELINE.V1`
3. `MARKER_162.P3.MYCO.ENGRAM_USER_TASK_MEMORY.V1`
4. `MARKER_162.P3.MYCO.JEPA_GEMMA_LOCAL_FASTPATH.V1`
5. `MARKER_162.P3.MYCO.NO_UI_MEMORY_SURFACE.V1`

## 3) Existing integration points (confirmed)
1. Triple-write backend and reindex flow already exist:
- `src/api/routes/triple_write_routes.py`
- `src/orchestration/triple_write_manager.py`
- `src/orchestration/services/memory_service.py`

2. Chat path already writes to memory and can host MYCO retrieval hook:
- `src/api/routes/chat_routes.py`
- `src/api/handlers/user_message_handler.py`

3. ENGRAM user memory exists and is reusable:
- `src/memory/engram_user_memory.py`

4. Context packing + JEPA overflow fallback already exist:
- `src/orchestration/context_packer.py`
- `src/services/jepa_runtime.py`

5. Multi-project session/project metadata store exists (for recent tasks by project):
- `src/services/mcc_project_registry.py`

6. Project runtime task history source exists:
- `src/orchestration/agent_pipeline.py` (`get_recent_tasks`)

## 4) Hidden indexing source set (P3 baseline)
Initial index sources for internal retrieval (no new UI):
1. `README.md`
2. `src/memory/README.md`
3. `src/orchestration/README.md`
4. `client/src/components/mcc/README.md`
5. `docs/162_ph_MCC_MYCO_HELPER/*.md`
6. `docs/161_ph_MCC_TRM/MYCO_AGENT_INSTRUCTIONS_GUIDE_V1_2026-03-06.md`
7. `docs/besedii_google_drive_docs/VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md`

Notes:
- This source set is hidden runtime input, not user-facing content rendering.
- Retrieval stays inside MYCO/agent path only.

## 5) P3.P1 narrow implementation plan (ready)
1. Add hidden ingest routine that chunks + tags docs and writes into triple-memory.
2. Add MYCO retrieval bridge in chat/controller path:
- inputs: focus context + project id + selected node/task
- outputs: short guidance snippets + confidence
3. Add ENGRAM payload merge for MYCO context:
- `user_name`
- `recent_tasks_by_project`
4. Add JEPA/Gemma fastpath order:
- JEPA/context pack summary first
- local Gemma answer second
- API escalation only on low confidence/coverage
5. Keep UI invariant:
- no new memory panel/button/chip
- no memory diagnostics leak into grandma UI

## 6) Verification contract (for P3.P1)
1. Hidden index test:
- index is written/readable by backend runtime
- no new UI element appears

2. ENGRAM payload test:
- MYCO context includes user and cross-project recent tasks

3. Fastpath routing test:
- JEPA/local-first route is used before API escalation

4. Regression guard:
- existing MCC chat + DAG behavior unchanged when memory index unavailable

## 7) Gaps and risks
1. Risk: token/noise growth from broad instruction corpus.
- Control: small chunk size + alias tags from memory glossary + recency weighting.

2. Risk: stale guidance from old docs.
- Control: reindex trigger + source timestamp metadata.

3. Risk: accidental UI leak of memory internals.
- Control: explicit test for `NO_UI_MEMORY_SURFACE` marker.

## 8) Result
`162-P3.P0` recon is complete and implementation-ready.

Next gate command:
`GO 162-P3.P1`
