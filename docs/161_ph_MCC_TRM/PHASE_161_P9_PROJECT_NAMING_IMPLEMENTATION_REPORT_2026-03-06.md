# PHASE 161 — P9 Project Naming Implementation Report (2026-03-06)

Protocol: `RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`  
Scope: `P161.9` (project naming contract for multi-project tabs)

## Implemented

1. API contract (`/api/mcc/project/init`):
- request accepts `project_name`.
- response returns `project_name`.

2. Config persistence:
- `ProjectConfig` now persists `display_name`.
- `create_new(...)` supports explicit `project_name` and normalized fallback.

3. Registry/list contract:
- registry stores `display_name` in project rows.
- `/api/mcc/projects/list` returns `display_name` with legacy fallback.

4. UI wiring:
- first-run payload sends `project_name` (derived from workspace basename by default).
- tab label now prioritizes `display_name`.

## Markers

- `MARKER_161.9.MULTIPROJECT.NAMING.API_CONTRACT.V1`
- `MARKER_161.9.MULTIPROJECT.NAMING.CONFIG_PERSIST.V1`
- `MARKER_161.9.MULTIPROJECT.NAMING.UI_TAB_LABEL.V1`

## Verification

Executed:

```bash
pytest -q tests/mcc
```

Result:
- `37 passed, 1 skipped`.

Additional naming contract tests added:
- `tests/mcc/test_mcc_project_naming_contract.py`

## Notes

- Fallback behavior intentionally keeps compatibility for legacy rows without `display_name`.
- Workspace folder basename remains canonical default when explicit name is not provided.
