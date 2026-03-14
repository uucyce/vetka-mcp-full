# PHASE 155C — JEPA Architect Implementation Plan for MCC (2026-03-02)

Status: `PLAN` (next after recon). Scope is MCC-side implementation; VETKA runtime remains untouched.

## 1) Objective
Implement JEPA-assisted architect bootstrap in MCC so that:
1. first architect call on non-empty codebase gets forced semantic core,
2. empty/new project skips JEPA bootstrap,
3. MCC and VETKA remain independently runnable.

## 2) Source baseline
Use commit baseline from VETKA for logic reference only:
- `c15c26fa` (`context_packer.py`, `jepa_runtime.py`, tests, probe)

## 3) Implementation slices (MCC repo)

### Slice 155C-P0: Contract freeze
Markers:
- `MARKER_155C.JEPA_ARCH_SHARED_CONTRACT.V1`
- `MARKER_155C.JEPA_ARCH_MCC_STANDALONE_GUARD.V1`
- `MARKER_155C.JEPA_ARCH_VETKA_STANDALONE_GUARD.V1`

Deliverables:
1. JEPA digest format contract.
2. Trigger/trace schema contract.
3. Env contract table (provider/runtime/fallback flags).

DoD:
- Contract doc committed in MCC repo.
- No imports from VETKA route handlers.

### Slice 155C-P1: Architect bootstrap trigger policy
Markers:
- `MARKER_155C.JEPA_ARCH_BOOTSTRAP_POLICY.V1`
- `MARKER_155C.JEPA_ARCH_FIRST_CALL_FORCE.V1`
- `MARKER_155C.JEPA_ARCH_EMPTY_PROJECT_SKIP.V1`

Deliverables:
1. `is_first_architect_turn` detection.
2. non-empty codebase guard.
3. forced JEPA path on first turn only.
4. empty project short-circuit path.

DoD:
- First turn + non-empty project yields JEPA semantic core.
- First turn + empty project does not call JEPA path.

### Slice 155C-P2: Runtime resilience + fallback
Deliverables:
1. runtime adapter path: `runtime -> embedding -> deterministic`.
2. timeout budget for bootstrap stage.
3. trace fields: `forced`, `provider_mode`, `latency_ms`, `fallback_reason`.

DoD:
- Strict runtime mode optional.
- Deterministic fallback always available.

### Slice 155C-P3: Verification suite
Deliverables:
1. tests: first-call-force, empty-project-skip, hysteresis-after-first, fallback-unavailable-runtime.
2. probe script for real-doc scenarios.

DoD:
- green test pack for all JEPA architect scenarios.
- reproducible debug artifacts from probe.

## 4) Rollout and safety
1. Implement only in MCC repo.
2. Keep VETKA code unchanged unless separate explicit GO.
3. Validate standalone startup for MCC and for VETKA independently.

## 5) Return gate to main Phase 155
After 155C plan is accepted and transferred to MCC repo, return to main `155` stream with protocol gate:
- `WAIT GO` before next main 155 implementation block.
