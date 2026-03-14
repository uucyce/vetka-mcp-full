# MARKER_162D_HEARTBEAT_DUAL_LOG_RECON_2026-03-06

## Scope
Investigate why logs show both:
- `[Startup] Heartbeat daemon started (60s interval)`
- `[Heartbeat] Daemon started (enabled=False, interval=86400s)`

## Evidence
- Startup log is emitted when task is created: `main.py:356-364`.
- Runtime heartbeat log is emitted inside daemon after warmup sleep: `main.py:198-202`.
- The daemon explicitly sleeps 10s before announcing runtime config: `main.py:199`.
- Runtime config is loaded from disk (`debug_routes` config file): `main.py:192`, `src/api/routes/debug_routes.py:2777-2786`.
- Current config file value is `interval: 86400`, `enabled: false` in `data/heartbeat_config.json`.

## Diagnosis
1. These are two logs from the **same daemon lifecycle**, not proof of two separate heartbeat daemons.
2. “60s interval” in startup message reflects default/startup intent label.
3. “86400s” reflects persisted runtime config loaded from `data/heartbeat_config.json`.
4. Apparent contradiction is observability/wording mismatch, not necessarily runtime duplication.

## Related parallel scheduler (non-heartbeat)
- Separate 24h MCP maintenance loop exists in `src/initialization/components_init.py:258-276`.
- This is not the same as mycelium heartbeat daemon, but contributes to operator confusion.

## Recommended Agent Task (separate)
- Unify heartbeat startup messaging to report effective loaded config immediately.
- Rename/label MCP maintenance logs to avoid “heartbeat-like” interpretation.
- Add endpoint/health field that explicitly reports single heartbeat task identity + config source.

## Acceptance Criteria
- Operators can distinguish task-creation log vs effective-runtime-config log.
- No ambiguity about whether one or multiple heartbeat loops are active.
- `enabled/interval` in logs always matches source-of-truth config file.
