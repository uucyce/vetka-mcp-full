# VETKA Performance Audit (2026-03-01)

## Scope
- Goal: identify concrete slowdown sources before broad refactors.
- Method: static hot-path audit + runtime behavior correlation from current logs.

## Top Findings (ordered by impact)

1. **Watcher hot path is heavily synchronous and log-heavy**
- File: `src/scanners/file_watcher.py`
- Evidence:
  - Per-event prints in hot callback: line 704
  - Repeated success/error prints on index + retry: lines 729-749, 813-866
  - Queue worker prints each emitted event: lines 891-895
- Risk:
  - I/O-heavy stdout spam on every filesystem event.
  - Threading.Timer retries multiply event pressure during Qdrant hiccups.
  - High chance of UI lag when many file events happen.

2. **`/api/tree/data` is expensive and still called frequently from frontend**
- Backend file: `src/api/routes/tree_routes.py`
- Evidence:
  - Full layout + enrichment flow inside request path: lines 895-979
  - Numerous per-request prints (`[API]`, `[CAM]`, `[TREE_PERF]`): lines 918-950
  - Soft TTL is only 1.5s: line 98 (`_TREE_DATA_TTL_SOFT_SEC = 1.5`)
- Frontend files:
  - `client/src/hooks/useSocket.ts`: extra fetches on `browser_folder_added` and `directory_scanned` (lines 1002, 1047)
  - `client/src/hooks/useTreeData.ts`: initial fetch path and heavy console logs (lines 86, 111-113, 121, 145, 158)
- Risk:
  - Repeated full graph rebuilds + frequent network calls => visible lag/freezes in UI.

3. **Too many watched directories, including external heavy folders**
- File: `data/watcher_state.json`
- Evidence:
  - Current watched dirs include:
    - `/Users/danilagulin/Documents/CinemaFactory/workflows`
    - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03`
    - `/Users/danilagulin/Documents/adult-doc`
- Risk:
  - VETKA watcher load is affected by unrelated external filesystem activity.
  - Large trees can flood watcher callbacks even when VETKA UI is idle.

4. **Time-based background tasks are always active**
- File: `main.py`
- Evidence:
  - Heartbeat daemon loop: lines 184-238 (polling every `interval`, and every 5s when disabled)
  - Periodic cleanup task: lines 166-180 (hourly)
  - Model health checks (every 300s): line 385
  - Group cleanup task (every 300s): line 411
- Risk:
  - Aggregate baseline CPU/network churn, especially with many models/groups.
  - Adds jitter during already heavy tree rebuilds.

5. **Hardcoded `localhost` remains in multiple frontend paths**
- Evidence:
  - `client/src/hooks/useTreeData.ts:61`
  - `client/src/hooks/useCaptain.ts:15`
  - `client/src/hooks/useMCCDiagnostics.ts:3`
  - `client/src/hooks/useDAGEditor.ts:22`
  - `client/src/utils/browserAgentBridge.ts:58`
  - `client/src/utils/dagLayoutPreferences.ts:12`
- Risk:
  - In VPN/proxy scenarios `localhost`/`::1` can flap separately from `127.0.0.1`.
  - Causes intermittent ECONNREFUSED and retry storms.

## Quick Wins (safe, low-risk)
1. Add `VETKA_WATCHER_VERBOSE=0` default and silence most watcher `print` in hot path.
2. Debounce frontend tree reloads (single fetch window 1-2s) for `directory_scanned` + `browser_folder_added`.
3. Raise `_TREE_DATA_TTL_SOFT_SEC` from `1.5` to `5-10` seconds; keep singleflight.
4. Reduce watched dirs to VETKA project root during stabilization.
5. Normalize frontend API base to `127.0.0.1` via one shared config constant.

## Medium-Risk / High-Gain Follow-ups
1. Move expensive knowledge/layout stages to incremental/background computation.
2. Replace per-event watcher retries with bounded queue + coalescing by path.
3. Add endpoint-level timing metrics (`tree_data`, `watcher_event`, `socket_emit`) with percentile output.

## Acceptance Metrics for perf phase
1. `/api/tree/data` p95 under 350ms on warm cache.
2. No UI freeze > 300ms during bulk scan.
3. Watcher logs reduced by >= 80% in normal mode.
4. Stable node rendering with no repeated full reload storm.
