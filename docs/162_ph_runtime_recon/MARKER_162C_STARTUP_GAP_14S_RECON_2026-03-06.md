# MARKER_162C_STARTUP_GAP_14S_RECON_2026-03-06

## Scope
Investigate observed startup delay (~14s between early startup logs and final Socket.IO registration log).

## Evidence from startup flow
- Sequential startup pipeline in `main.py:329-503`.
- `register_all_handlers` is awaited at `main.py:491-492`.
- Many pre-handler async init steps occur before it (registry, pinned files, group manager, watcher).

## Direct timing probe (local repro)
- Isolated `register_all_handlers(...)` call completed in ~0.105s in this environment.
- Individual handler module imports were mostly sub-second; highest observed around:
  - `connection_handlers` ~1.0s
  - `jarvis_handler` ~0.77s

## Likely contributors
1. Startup is a chain of serial awaits; small costs accumulate before final “handlers registered” marker.
2. Import side effects in API stack (notably Ollama health probe in `src/elisya/api_aggregator_v3.py:44-51` with network timeout behavior) can inflate cold-start when loopback/network is unstable.
3. Mixed `print` and timestamped logger output can make delay look larger/less localized in terminal timeline.

## What this is NOT
- No evidence of crash or deadlock in provided logs.
- No evidence that MCP socket registration itself is the 14s bottleneck (isolated call is fast).

## Recommended Agent Task (separate)
- Add startup stage timing markers around each await block in lifespan (`main.py`).
- Isolate and cache expensive import-time probes (especially provider health checks).
- Convert critical startup `print` traces to structured logger timestamps for precise attribution.

## Acceptance Criteria
- Measured per-stage startup breakdown is available.
- p95 startup latency target is defined and tracked.
- Delay source is attributable to a concrete stage, not inferred from mixed logs.
