# PHASE 161 P0 — Real Repo DAG Bench Report (2026-03-04)

Status: `VERIFY` (test-first baseline)
Marker: `MARKER_161.TRM.TEST.REAL_REPO_BENCH.V1`

## Commands

```bash
pytest -q tests/mcc
MCC_REAL_REPO_BENCH=1 \
MCC_REAL_REPO_SCOPE=/Users/danilagulin/Documents/VETKA_Project/vetka_live_03 \
MCC_REAL_REPO_MAX_NODES=320 \
pytest -q tests/mcc/test_mcc_real_repo_benchmark.py -q
```

## Artifacts

- JSON: `docs/161_ph_MCC_TRM/TRM_REAL_REPO_BENCH_LATEST.json`
- Test: `tests/mcc/test_mcc_real_repo_benchmark.py`

## Results snapshot

### baseline_no_overlay
- duration: `4.6033s`
- nodes/edges: `57 / 56`
- decision: `pass`
- spectral: `status=ok, lambda2=0.03553, eigengap=0.01488, components=1`
- scorecard: `100.0`

### overlay_on_jepa_path
- duration: `3.6215s`
- nodes/edges: `57 / 56`
- decision: `pass`
- spectral: `status=ok, lambda2=0.03553, eigengap=0.01488, components=1`
- scorecard: `100.0`
- overlay stats observed: `predicted_edges=120`

## Interpretation

1. Baseline DAG builder on real VETKA scope is stable and verifier-pass.
2. With overlay-enabled path, final design backbone quality stayed identical in this run.
3. This report does **not** prove TRM impact yet (TRM is not integrated in runtime path).
4. JEPA-path is exercised as overlay-capable route, but backbone remains deterministic builder output.

## Next gate

Proceed to Phase 161 W1 (contract/config only) with no behavior change.
