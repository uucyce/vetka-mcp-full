# CODEX Protocol Recon Report (2026-02-25)
Protocol: `RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`

## 1) RECON + Markers (current state)

Confirmed active marker families:
- Architect build baseline:
  - `MARKER_155.ARCHITECT_BUILD.CONTRACT.V1`
  - `MARKER_155.ARCHITECT_BUILD.VERIFIER.V1`
  - `MARKER_155.ARCHITECT_BUILD.JEPA_OVERLAY.V1`
- Algorithmic offload array core:
  - `MARKER_155.ARCHITECT_BUILD.ARRAY_CORE.V1`
  - `MARKER_155.ARCHITECT_BUILD.ARRAY_RUNTIME_BRIDGE.V1`
  - `MARKER_155.ARCHITECT_BUILD.ARRAY_INFER_EDGES.V1`
  - `MARKER_155.ARCHITECT_BUILD.ARRAY_API.V1`
  - planned: `MARKER_155.ARCHITECT_BUILD.ARRAY_CORE.V2_POLICY`
- MCC hardening / runtime:
  - `MARKER_155.P4_2.FOCUS_MEMORY`
  - `MARKER_155.P3_5.JEPA_AUTOSTART`

Primary implementation files:
- `src/services/mcc_architect_builder.py`
- `src/api/routes/mcc_routes.py`
- `client/src/components/mcc/MyceliumCommandCenter.tsx`
- `main.py`
- `run.sh`

Primary docs:
- `docs/155_ph/ARCHITECT_BUILD_CONTRACT_V1.md`
- `docs/155_ph/ARCHITECT_BUILD_CONTRACT_V1_CHECKLIST.md`
- `docs/155_ph/CODEX_ALGORITHMIC_OFFLOAD_REPORT_2026-02-25.md`
- `docs/155_ph/CODEX_HANDOFF_RECON_2026-02-24.md`

## 2) REPORT (gaps for next narrow implementation)

G1. DAG versioning is not yet first-class.
- Need persisted `dag_version` entities and compare flow.

G2. Architect context is not yet version-bound.
- Chat/actions should be tied to explicit `dag_version_id`.

G3. Debug experiment flow is not yet complete.
- Need tabbed DAG variants with visible build metadata (weights/tools/proportions).

G4. Automated comparison harness is missing.
- Need golden runs and scorecards across multiple input types.

G5. UI simplification cleanup still pending.
- Known extra/no-op controls remain in MCC action surfaces.

## 3) Narrow Implementation Candidates (for GO)

N1. Backend DAG Version API (minimal):
- `POST /api/mcc/dag-versions/create`
- `GET /api/mcc/dag-versions/list`
- `GET /api/mcc/dag-versions/{id}`
- `POST /api/mcc/dag-versions/{id}/set-primary`

N2. Metadata contract for each DAG version:
- `builder_profile`, `weights`, `budget`, `verifier`, `spectral`, `overlay_stats`, `markers`.

N3. MCC tabs for DAG variants (debug mode first):
- lightweight tabs + switch active version + compare summary.

N4. Smoke tests:
- array input set A/B/C
- baseline vs variant scorecard snapshot
- verifier decision gate.

## 4) Verify Plan (post-GO)

- API contract tests for DAG version endpoints.
- Build/rebuild reproducibility check (same input -> stable decision class).
- UI switch test across DAG tabs.
- Verifier/spectral panel sync with active DAG version.

## 5) Status

Current step reached: `REPORT`.

Next protocol step: `WAIT GO`.
