# MCC Release Gate V1 (G3/G4)

Date: 2026-02-26  
Marker: `MARKER_155.READINESS.G3_G4.RELEASE_GATE.V1`

## Purpose

Single executable GO/NO-GO gate for MVP-critical MCC scope.

Addresses:
- G3: frozen numeric thresholds in one executable contract.
- G4: MCC-scoped gate isolated from global frontend debt noise.

## Command

```bash
./scripts/run_mcc_scope_gate.sh
```

Report output:
- `data/reports/mcc_release_gate.json`

## Frozen thresholds (v1)

- `MIN_SCORE = 70.0` (top auto-compare scorecard)
- `MAX_ORPHAN_RATE = 0.35` (top variant)
- `MIN_VARIANTS = 2` (compare harness run cardinality)
- `REQUIRE_ACYCLIC = true`
- `REQUIRE_MONOTONIC = true`

## Gate checks

1. `layout_verifier_gate`
- Source: `run_dag_auto_compare(...)` (`source_kind=array`, deterministic fixture).
- Pass when all frozen thresholds are satisfied.

2. `runtime_safety_gate`
- Source: `src.services.jepa_runtime.runtime_health(force=True)`.
- Pass policy:
  - runtime disabled -> PASS (explicitly marked disabled),
  - runtime enabled -> must be `ok=true`.

3. `mcc_scope_pytest_gate`
- Command: `pytest -q tests/mcc`.
- Pass when test package is green.

## Decision policy

- Final gate status is `PASS` only when all three checks are `PASS`.
- Any failed check yields final status `FAIL`.

## Notes

- This gate is intentionally MCC-scoped and does not run full repo frontend build.
- Full-repo TS debt remains tracked separately and must not block MCC-focused MVP stabilization checks.
