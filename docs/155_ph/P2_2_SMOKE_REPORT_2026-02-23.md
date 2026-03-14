# P2.2 Smoke Report (MCC <-> VETKA ENGRAM Bridge)

Date (UTC): 2026-02-23
Marker: `MARKER_155.MEMORY.ENGRAM_DAG_PREFS.V1`

## Scope
Short smoke for `dag_layout_profiles` bridge:
- Read/write profile for MCC scope
- Read/write profile for VETKA scope
- Confirm shared storage path: `viewport_patterns.dag_layout_profiles`

## Scenario A: Live API smoke (manual path)
Target endpoints:
- `POST /api/mcc/layout/preferences`
- `GET /api/mcc/layout/preferences?user_id=...&scope_key=...`

Result: `FAIL (environment)`
- `curl: (7) Failed to connect to localhost port 5001`
- Port probe: `5001 closed`, `8083 closed`, `8082 closed`, `3001 closed`

Interpretation:
- MCC/Mycelium server was not running during smoke window.
- API-level smoke cannot be confirmed in this run.

## Scenario B: ENGRAM direct bridge smoke (core path)
Method:
- Use `get_engram_user_memory()` directly.
- Write two scoped profiles into `viewport_patterns.dag_layout_profiles`:
  - MCC scope: `dag:/Users/danilagulin/Documents/VETKA_Project/vetka_live_03:architecture`
  - VETKA scope: `dag:/Users/danilagulin/Documents/VETKA_Project/vetka_live_03:workflow`
- Read back and verify both keys exist.

Result: `PASS (core bridge)`

Readback log:
```json
{
  "ok": true,
  "has_mcc": true,
  "has_vetka": true,
  "mcc_profile": {
    "vertical_separation_bias": 0.32,
    "sibling_spacing_bias": -0.11,
    "branch_compactness_bias": 0.21,
    "confidence": 0.78,
    "sample_count": 3,
    "updated_at": "2026-02-23T19:56:42Z",
    "focus_overlay_preference": "focus_only",
    "pin_persistence_preference": "pin_first"
  },
  "vetka_profile": {
    "vertical_separation_bias": 0.12,
    "sibling_spacing_bias": 0.08,
    "branch_compactness_bias": 0.34,
    "confidence": 0.71,
    "sample_count": 2,
    "updated_at": "2026-02-23T19:56:42Z"
  }
}
```

Observed warnings:
- `[EngramUserMemory] Collection init failed: [Errno 1] Operation not permitted`
- `Hot data load failed: [Errno 1] Operation not permitted`
- `Qdrant upsert failed: [Errno 1] Operation not permitted`

Interpretation:
- In current runtime, some ENGRAM persistence paths are permission-restricted,
  but preference read/write contract still executed and returned expected scoped profiles.

## Final verdict
- API manual smoke: `NO-GO` (server unavailable)
- Core ENGRAM bridge logic: `GO` (scoped read/write confirmed)

## Action to close P2.2 fully
1. Start MCC server (`localhost:5001`) and rerun Scenario A.
2. Recheck ENGRAM permission warnings in the runtime environment.
