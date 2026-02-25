# CODEX Mycelium MVP Recon (2026-02-25)

Date: 2026-02-25  
Deadline: 2026-02-28 (3 days left)  
Scope: `docs/155_ph` + marker presence in `src/`, `client/`, `main.py`, `run.sh`

## 1) Executive Status

- Progress is real: core Phase 155 DAG architecture track moved from design-only toward runnable backend/UI flow.
- MVP is not fully closed yet: there are still GO/NO-GO gaps in runtime safety, manual UX acceptance, and release gating.
- Current recommended status: **SOFT NO-GO for release, GO for focused stabilization sprint (D-3 to D-0)**.

## 2) Date-Oriented Recon (latest docs first)

## 2026-02-25 (latest)

Primary docs:
- `CODEX_PROTOCOL_IMPL_VERIFY_2026-02-25.md`
- `CODEX_PROTOCOL_RECON_REPORT_2026-02-25.md`
- `CODEX_ALGORITHMIC_OFFLOAD_REPORT_2026-02-25.md`
- `ARCHITECT_BUILD_CONTRACT_V1*.md`

Signal:
- Added/verified: DAG versions API, DAG compare harness, array->DAG endpoint, roadmap DAG version tabs.
- Tests/smokes: backend smokes pass, `pytest -q tests/mcc` reported pass.
- Known release gap remains: global frontend build debt; targeted MCC fixes done.

## 2026-02-24

Primary doc:
- `CODEX_HANDOFF_RECON_2026-02-24.md`

Signal:
- P3/P4 path broadly implemented.
- Explicit open items: P4.2 restore hardening, Diagnostics++ shutdown blockers snapshot/export.

## 2026-02-23

Primary docs:
- `P3_P4_SMOKE_REPORT_2026-02-23.md`
- `P2_2_SMOKE_REPORT_2026-02-23.md`
- `MARKER_155_ARCHITECT_BUILD_IMPLEMENTATION_V1.md`

Signal:
- Many service-level checks: PASS.
- Still recorded at that time: `PENDING MANUAL` / `NO-GO until manual check completed` for some UX/runtime checks.

## 2026-02-22 (baseline gate)

Primary docs:
- `MARKER_155_IMPLEMENTATION_READINESS_REPORT_2026-02-22.md`
- `MARKER_155_IMPLEMENTATION_MAP.md`

Signal:
- Formal readiness verdict was `NO-GO` on all gates (G0..G5).
- Several items were later improved (23-25 Feb), but not all gate criteria were formally re-closed with numeric freeze.

## 3) Marker Inventory Snapshot (docs vs code)

Inventory method:
- Parsed markers from `docs/155_ph/*.md`.
- Checked exact string presence in `src/`, `client/`, `main.py`, `run.sh`.

Totals:
- Total unique markers in docs: **200**
- Markers with code hits: **65** (recheck on 2026-02-26)
- Doc-only markers (design/planning/not yet materialized): **135** (recheck on 2026-02-26)

Important caveat:
- `DOC_ONLY` is not automatically bad; many are architecture/recon/checklist markers by design.
- For MVP risk, only operationally critical doc-only markers matter.

### Confirmed implemented marker families (high confidence)

- DAG versions:
  - `MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.*`
  - Evidence: `src/services/mcc_dag_versions.py`, `src/api/routes/mcc_routes.py`, `client/src/components/mcc/MyceliumCommandCenter.tsx`
- DAG compare harness:
  - `MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.*`
  - Evidence: `src/services/mcc_dag_compare.py`, `src/api/routes/mcc_routes.py`
- Array->DAG offload:
  - `MARKER_155.ARCHITECT_BUILD.ARRAY_CORE.V1`, `...ARRAY_API.V1`
  - Evidence: `src/services/mcc_architect_builder.py`, `src/api/routes/mcc_routes.py`
- Runtime autostart hardening:
  - `MARKER_155.P3_5.JEPA_AUTOSTART`
  - Evidence: `run.sh`, `main.py`
- Focus memory / display wiring:
  - `MARKER_155.P4_2.FOCUS_MEMORY`, `MARKER_155.P4_3.FOCUS_DISPLAY_MODES.V1`
  - Evidence: `client/src/components/mcc/MyceliumCommandCenter.tsx`

### Critical doc-only markers/gates still relevant to MVP

- `MARKER_155.READINESS.BLOCKER.B2.QUALITY_THRESHOLDS`
- `MARKER_155.READINESS.BLOCKER.B3.RUNTIME_SAFETY`
- `MARKER_155.READINESS.G3.LAYOUT_READABILITY`
- `MARKER_155.READINESS.G4.VERIFIER_EVAL`
- `MARKER_155.READINESS.G5.RUNTIME_OPERATIONS`

Interpretation:
- These are mainly governance/acceptance gates not yet fully frozen as release contracts.

## 4) MVP Gap List (must close by 2026-02-28)

## G1. Manual acceptance not fully re-baselined

What is missing:
- Fresh manual pass for P4 UX scenarios (focus persistence across zoom/drill, architect prefill behavior).

Why it blocks MVP:
- Current status relies on older partial manual notes (`PENDING MANUAL`).

## G2. Runtime blockers observability is incomplete

Status update (2026-02-26):
- CLOSED for MVP baseline (shutdown blockers snapshot/export implemented and validated as separate issue track from Desktop Codex UI bug).

Residual note:
- Keep runtime blockers snapshot in regression smoke pack to avoid silent drift.

## G3. GO/NO-GO numeric gates are not frozen in one executable release gate

What is missing:
- One authoritative threshold set for verifier/readability/runtime safety that fails release if violated.

Why it blocks MVP:
- Without hard gate, regressions can pass by narrative rather than measurable acceptance.

## G4. Frontend release gate remains noisy at repo level

What is missing:
- Clean targeted CI gate for MCC-scope paths (even if global TS debt remains).

Why it blocks MVP:
- MVP hotfix confidence is reduced when signal/noise ratio is low.

## G5. Environment parity for ops tooling

What is missing:
- Single blessed runtime profile for MCP/session tools (venv package parity), documented and enforced.

Why it blocks MVP:
- Mismatch between interpreters causes false negatives during diagnostics/session init.

## 5) D-3 Plan to MVP (26-28 Feb)

## D-3 (2026-02-26): Freeze acceptance + diagnostics contracts

Deliverables:
- Keep shutdown blockers snapshot endpoint + UI diagnostics card/export in regression pack (already implemented).
- Freeze numeric thresholds for verifier/readability/runtime checks in one release-gate doc + code constants.
- Record one fresh manual P4 checklist run.

Done criteria:
- One report file with PASS/FAIL per gate and measured values.

## D-2 (2026-02-27): Harden + run reproducible smoke pack

Deliverables:
- Run reproducible smokes: DAG versions, auto-compare, array API, runtime health route, P4 focus restore.
- Add MCC-scoped CI/test command that is green and stable.

Done criteria:
- Single command pack with all green for MVP-critical scope.

## D-1 / Release day (2026-02-28): Cut MVP decision

Deliverables:
- Final GO/NO-GO sheet with explicit owner sign-off.
- If GO: tag MVP baseline + rollback note.
- If NO-GO: publish short blocker memo with exact next date/time and owner per blocker.

Done criteria:
- Decision is measurable, not narrative.

## 6) Recommended Scope Discipline Until Deadline

- No new Phase 155A/P6 feature expansion until G1..G5 are closed.
- Prioritize reliability, observability, and acceptance closure over new capability.
- Keep marker policy strict: new behavior must have one marker and one verification artifact.

## 7) Recon Sources Used

- `docs/155_ph/MARKER_155_IMPLEMENTATION_READINESS_REPORT_2026-02-22.md`
- `docs/155_ph/MARKER_155_IMPLEMENTATION_MAP.md`
- `docs/155_ph/P3_P4_SMOKE_REPORT_2026-02-23.md`
- `docs/155_ph/CODEX_HANDOFF_RECON_2026-02-24.md`
- `docs/155_ph/CODEX_PROTOCOL_RECON_REPORT_2026-02-25.md`
- `docs/155_ph/CODEX_PROTOCOL_IMPL_VERIFY_2026-02-25.md`
- `docs/155_ph/CODEX_ALGORITHMIC_OFFLOAD_REPORT_2026-02-25.md`
- `docs/155_ph/ARCHITECT_BUILD_CONTRACT_V1.md`
- `docs/155_ph/ARCHITECT_BUILD_CONTRACT_V1_CHECKLIST.md`
- `docs/155_ph/MCC_RELEASE_GATE_V1.md`
- `docs/155_ph/MCC_P4_MANUAL_ACCEPTANCE_2026-02-26.md`
