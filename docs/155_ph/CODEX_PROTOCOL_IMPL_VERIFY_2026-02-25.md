# CODEX Protocol Impl+Verify Report (2026-02-25)
Protocol step: `IMPL NARROW -> VERIFY`
Based on recon: `CODEX_PROTOCOL_RECON_REPORT_2026-02-25.md`

## Scope executed (narrow)
Implemented:
- N1: Backend DAG Version API (create/list/get/set-primary)
- N2: DAG version metadata contract persistence
- N3: MCC DAG version tabs + active graph binding
- N4: DAG auto-compare harness (multi-variant scorecard + optional persist/primary)
- N5: MCC UI auto-compare action in roadmap DAG tabs
- N7: MCC compare matrix panel for ranked DAG variants

Not implemented in this wave:
- N4 auto compare harness

## Code changes

### 1) New persistence service
File:
- `src/services/mcc_dag_versions.py`

Markers:
- `MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.V1`
- `MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.CREATE.V1`
- `MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.LIST.V1`
- `MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.GET.V1`
- `MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.PRIMARY.V1`

Behavior:
- Stores versions in `data/mcc_dag_versions.json`.
- Project bucket layout:
  - `primary_version_id`
  - `versions[]`
- Version record includes:
  - identity: `version_id`, `name`, `created_at`, `author`, `source`, `is_primary`
  - counters: `node_count`, `edge_count`
  - metadata: `build_meta`, `markers`
  - payload: `dag_payload`

### 2) New MCC API endpoints
File:
- `src/api/routes/mcc_routes.py`

Marker:
- `MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.API.V1`

Endpoints:
- `POST /api/mcc/dag-versions/create`
- `GET /api/mcc/dag-versions/list`
- `GET /api/mcc/dag-versions/{version_id}`
- `POST /api/mcc/dag-versions/{version_id}/set-primary`
- `POST /api/mcc/dag-versions/auto-compare`

Project resolution:
- uses current `ProjectConfig.project_id` when available,
- fallback: `default_project`.

### 3) MCC UI DAG version tabs and active source binding
File:
- `client/src/components/mcc/MyceliumCommandCenter.tsx`

Marker:
- `MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.UI_TABS.V1`

Behavior:
- roadmap-level tab strip shows:
  - `baseline` (live roadmap source),
  - saved DAG versions,
  - `+ snapshot` action.
- active version fetches payload from backend and becomes graph source for roadmap view.
- star button sets selected version as primary.
- verifier and cross-edge source switch with active DAG version payload.

### 4) DAG auto-compare harness (algorithmic offload)
File:
- `src/services/mcc_dag_compare.py`

Markers:
- `MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.V1`
- `MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.SCORECARD.V1`
- `MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.AUTORUN.V1`
- `MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.PERSIST.V1`
- `MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.API.V1` (route/model)

Behavior:
- Runs multiple DAG build variants in one call (`source_kind=scope|array`).
- Computes a deterministic scorecard per variant from verifier/spectral metrics.
- Returns ranked variants + `best`.
- Optionally persists each run as DAG version snapshot (`source=auto_compare`).
- Optionally sets best persisted version as primary (`set_primary_best=true`).

### 5) MCC UI auto-compare action (roadmap tabs)
File:
- `client/src/components/mcc/MyceliumCommandCenter.tsx`

Marker:
- `MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.UI_TABS.V1`

Behavior:
- Added `auto-compare` button in roadmap DAG versions strip.
- Runs `POST /api/mcc/dag-versions/auto-compare` with 3 preset variants:
  - `clean_topology`
  - `balanced`
  - `overlay_try`
- Persists compare runs as DAG versions and auto-selects best version tab when returned.
- Shows compact compare status in tabs row:
  - `best: <name> (<score>)`
  - `<N> variants` (with row tooltip details).

### 6) MCC compare matrix panel (roadmap tabs)
File:
- `client/src/components/mcc/MyceliumCommandCenter.tsx`

Behavior:
- Added `matrix` toggle button in DAG version strip.
- Shows ranked rows from auto-compare payload with columns:
  - `variant`
  - `score`
  - `decision`
  - `nodes`
  - `edges`
  - `orph`
  - `dens`
  - `version`
  - `action`
- Per-row actions:
  - activate DAG version tab,
  - set row version as primary (`★`).
- Added quick action:
  - `promote best` (set best compare result as primary).
- Added selected-row params line:
  - `max_nodes`, `min_conf`, `overlay`, `max_pred`.

## VERIFY results

### Syntax
- `python -m py_compile src/services/mcc_dag_versions.py src/api/routes/mcc_routes.py src/services/mcc_architect_builder.py`
- Result: `PASS`

### Functional smoke
Executed local smoke script:
- create version v1 (set primary)
- create version v2
- list versions
- get v2 by id
- set v2 as primary
- list again and verify primary changed

Result:
- `PASS`
- output: `OK dagv_8b008ba00e11 dagv_7cd675462ef7 dagv_7cd675462ef7`

### Auto-compare smoke
Executed local smoke for new harness:
- `run_dag_auto_compare(...)` with `source_kind=array`, 2 variants, `persist_versions=true`, `set_primary_best=true`.

Result:
- `PASS`
- output:
  - `OK 2 dense_overlay dagv_e14119465b40 True`
  - rows include scores + version ids for both variants.

### Tests: MCC package
Executed:
- `pytest -q tests/mcc`

Result:
- `PASS`
- `10 passed`

### Frontend sanity (targeted)
Executed:
- `npm --prefix client run build`

Result:
- `FAIL` (pre-existing global TypeScript debt across many files in repo)
- N3-specific regressions fixed during this wave:
  - moved `useToast()` initialization above callbacks that use `addToast` in dependency arrays (runtime TDZ prevention).
  - normalized `relationKind` mapping in DAG version edge adapter to strict `DAGEdge['relationKind']` union (removed introduced TS2322 mismatch).
- Spot check:
  - `npm --prefix client run build 2>&1 | rg "MyceliumCommandCenter.tsx\\("`
  - no remaining TS2322 on `adaptVersionEdge`; remaining MCC errors are existing strictness warnings (`TS6133`/`TS7006`) from broader file baseline.

## Notes / constraints
- This wave includes backend + UI tabs (N1+N2+N3).
- Smoke test wrote test records into `data/mcc_dag_versions.json` under `default_project`.
- Auto-compare smoke also wrote compare variants into `data/mcc_dag_versions.json` (`source=auto_compare`).

## Next step candidates
- N5: UI controls for `auto-compare` runs (variant presets + compare matrix in DAG tabs row).
- N6: golden datasets + threshold gate in CI (GO/NO-GO before release).
