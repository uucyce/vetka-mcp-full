# MARKER_137.RECON_S1_6_TESTS
# Recon Report: tb_1770809279_6 (S1.6 tests)

Date: 2026-02-11
Workspace: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

## Task scope
- Add tests for:
1. heartbeat daemon starts/stops/processes tasks
2. unified search integration across providers
3. auto-close on commit flow

## Existing coverage found
1. Heartbeat:
- Existing heavy phase tests already cover parsing + dispatch ticks (`tests/test_phase117_2c_heartbeat.py`, `tests/test_phase119_3_heartbeat_e2e.py`).
- Gap for Sprint-1 framing: no focused test file named `tests/test_heartbeat_daemon.py` for start/stop config semantics + pipeline wakeup + compact process-flow assertions.

2. Unified search:
- Existing `tests/test_unified_search_api.py` covers basic aggregator behavior.
- Gap: no dedicated E2E-style route/provider integration file `tests/test_unified_search_e2e.py`.

3. Auto-close by commit:
- Existing `tests/test_phase136_auto_close_commit.py` validates pending/queued completion.
- This can be re-used in validation run (no duplicate file needed).

## Planned isolated implementation
1. Add `tests/test_heartbeat_daemon.py` with marker:
- start/stop via heartbeat config API (`/api/heartbeat/config` handlers)
- processing flow via `heartbeat_tick()` with mocked board dispatch
- wakeup flow via `on_pipeline_complete()`

2. Add `tests/test_unified_search_e2e.py` with marker:
- route-level integration for `/api/search/unified` handler call
- provider fan-in and source filtering checks

3. Validate with targeted pytest run including existing auto-close tests:
- `tests/test_heartbeat_daemon.py`
- `tests/test_unified_search_e2e.py`
- `tests/test_phase136_auto_close_commit.py`

## Duplication control
- No backend logic changes planned for S1.6; tests only.
- Reuse existing auto-close suite instead of cloning scenarios.
