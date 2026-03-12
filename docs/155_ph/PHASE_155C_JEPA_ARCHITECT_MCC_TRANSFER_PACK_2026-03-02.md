# PHASE 155C — JEPA Architect MCC Transfer Pack (2026-03-02)

Status: `IMPLEMENTATION READY` (for MCC standalone repo).

## 0) Why this pack
MCC must run standalone (separate MCP), while VETKA must also run standalone.
Current workspace contains VETKA monorepo only, so this pack is the exact implementation map for MCC repo without mutating VETKA runtime.

## 1) Source baseline to copy from VETKA
Commit baseline: `c15c26fa`

Take as reference logic:
1. `src/orchestration/context_packer.py`
2. `src/services/jepa_runtime.py`
3. `tests/test_phase157_context_packer.py`
4. `tests/test_phase157_context_packer_real_docs_debug.py`
5. `scripts/context_packer_probe.py`

## 2) 155C slices (execute in MCC repo)

### 155C-P0 — Shared contract only
Markers:
- `MARKER_155C.JEPA_ARCH_SHARED_CONTRACT.V1`
- `MARKER_155C.JEPA_ARCH_MCC_STANDALONE_GUARD.V1`
- `MARKER_155C.JEPA_ARCH_VETKA_STANDALONE_GUARD.V1`

Implement:
1. Add `docs/contracts/JEPA_ARCHITECT_CONTEXT_CONTRACT_V1.md`.
2. Define strict payload schema:
   - `jepa_context`
   - trace fields (`jepa_forced`, `jepa_trigger`, `provider_mode`, `latency_ms`, `fallback_reason`).
3. Define env contract:
   - provider selection (`auto|runtime|embedding|deterministic`)
   - runtime module path
   - strict runtime mode.

DoD:
- contract doc approved
- no runtime imports from VETKA-specific handler modules.

### 155C-P1 — Architect first-call JEPA policy
Markers:
- `MARKER_155C.JEPA_ARCH_BOOTSTRAP_POLICY.V1`
- `MARKER_155C.JEPA_ARCH_FIRST_CALL_FORCE.V1`
- `MARKER_155C.JEPA_ARCH_EMPTY_PROJECT_SKIP.V1`

Implement in MCC architect route/service:
1. `is_first_architect_turn(context)`
2. `has_non_empty_codebase(scope_root)`
3. `collect_bootstrap_pinned_files(scope_root, limit)`
4. Call packer with `force_jepa=true` iff:
   - first turn
   - codebase non-empty
5. Skip JEPA when project empty/new.

DoD:
- first call on real codebase injects JEPA semantic core
- first call on empty repo bypasses JEPA path.

### 155C-P2 — Runtime fallback resilience
Marker:
- `MARKER_155C.JEPA_ARCH_RUNTIME_FALLBACK_CHAIN.V1`

Implement:
1. Adapter chain: runtime -> embedding -> deterministic.
2. Timeout budget for bootstrap stage.
3. Non-blocking fallback semantics.

DoD:
- architect call never hard-fails due to JEPA runtime unavailable.

### 155C-P3 — Verify + probes
Markers:
- `MARKER_155C.JEPA_ARCH_TEST_FIRST_CALL_FORCE.V1`
- `MARKER_155C.JEPA_ARCH_TEST_EMPTY_PROJECT_SKIP.V1`
- `MARKER_155C.JEPA_ARCH_TEST_FALLBACK.V1`

Tests to add in MCC:
1. first-call force on non-empty codebase
2. empty-project skip
3. runtime unavailable -> deterministic fallback
4. hysteresis behavior after first call

Probe:
- add/update `scripts/context_packer_probe.py` equivalent in MCC.

## 3) Reference patch map (MCC repo)

1. `mcc/orchestration/context_packer.py`
   - add `force_jepa` optional parameter in `pack(...)`
   - trace includes `jepa_forced`
2. `mcc/api/routes/architect_chat_routes.py` (or equivalent)
   - add JEPA bootstrap builder
   - inject semantic digest into architect system context
3. `mcc/services/jepa_runtime.py`
   - keep runtime health + fallback compatible with contract
4. `mcc/tests/test_phase155c_jepa_architect_bootstrap.py`
5. `mcc/scripts/context_packer_probe.py`

## 4) Non-goals (to avoid confusion)
1. Do not modify VETKA route handlers as part of MCC 155C.
2. Do not create hard runtime coupling between MCC and VETKA code paths.
3. Do not merge full shared py runtime; share contract, not handlers.

## 5) Gate to return to main 155
When MCC-side 155C P0..P3 are green:
1. publish MCC report `PHASE_155C_MCC_REPORT_YYYY-MM-DD.md`
2. update VETKA tracking doc with link only
3. return to main `155` execution queue.
