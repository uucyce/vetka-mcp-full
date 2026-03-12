# PHASE 165 — P165.A Implementation Report (2026-03-07)

Protocol step: `IMPL NARROW -> VERIFY TEST`
Status: `DONE / WAIT GO`

## Implemented

1. New MCC-scoped backend route:
- `POST /api/mcc/search/file`
- file: `src/api/routes/mcc_routes.py`

2. Route behavior:
- resolves active project scope from `sandbox_path` first (fallback `source_path`),
- validates requested `scope_path` stays inside active project scope,
- executes file search with explicit `scope_roots=[resolved_scope]`,
- applies final path-filter to ensure no out-of-scope results leak to client.

3. Search engine extension:
- `search_files(...)` accepts optional `scope_roots`.
- file: `src/search/file_search_service.py`

## Markers

- `MARKER_165.MCC.CONTEXT_SEARCH.API_SCOPED_FILE_ROUTE.V1`
- `MARKER_165.MCC.CONTEXT_SEARCH.SCOPE_GUARD.V1`
- `MARKER_165.MCC.CONTEXT_SEARCH.PATH_FILTER.V1`

## Tests Added

- `tests/mcc/test_mcc_context_search_api_scope.py`
  - default scope uses active sandbox,
  - out-of-scope results are filtered,
  - external `scope_path` is rejected.

## Verification

- `pytest -q tests/mcc/test_mcc_context_search_api_scope.py` → `2 passed`
- `pytest -q tests/mcc` → `46 passed, 1 skipped`

## Notes

- This step intentionally does not modify MCC UI yet.
- Next step (P165.B) can safely consume `/api/mcc/search/file` from Context window.
