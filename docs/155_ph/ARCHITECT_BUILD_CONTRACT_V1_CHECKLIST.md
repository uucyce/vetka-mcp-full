# ARCHITECT_BUILD_CONTRACT_V1_CHECKLIST
Status: Active release gate  
Date: 2026-02-25  
Source contract: `ARCHITECT_BUILD_CONTRACT_V1.md`

Use this checklist as GO/NO-GO before merge/release of MCC/VETKA DAG pipeline changes.

---

## 1) Pipeline Integrity (GO/NO-GO)
- [ ] `build_condensed_graph(...)` runs first and returns runtime basis.
- [ ] `_embed_texts(...)` has working primary path and deterministic fallback.
- [ ] `_whiten_vectors(...)` is executed with safe fallback on numeric failure.
- [ ] `_cluster_vectors(...)` keeps HDBSCAN -> DBSCAN -> quantile fallback chain.
- [ ] `_build_design_graph(...)` runs with budget guards.
- [ ] `build_predictive_overlay(...)` is optional and does not block baseline DAG.
- [ ] `_verifier_report(...)` and `_spectral_metrics(...)` are always present in response.

GO rule:
- All items checked.

NO-GO rule:
- Any missing step or broken fallback chain.

---

## 2) Parameter Guards (GO/NO-GO)
- [ ] `max_nodes` is clamped to `50..5000`.
- [ ] `max_predicted_edges` is clamped to `0..2000`.
- [ ] `min_confidence` is clamped to `0.0..0.99`.
- [ ] Whitening keep policy remains ~95% variance with bounded components.
- [ ] Design budget formulas are unchanged or explicitly versioned.

GO rule:
- All clamps and guards enforced.

NO-GO rule:
- Unbounded params or silent behavior drift.

---

## 3) DAG Invariants (GO/NO-GO)
- [ ] Structural backbone remains acyclic.
- [ ] Layer monotonicity holds on base edges.
- [ ] Orphan-rate is computed and reported.
- [ ] Spectral block returns `lambda2`, `eigengap`, `component_count`, `status`.
- [ ] Verifier decision is always `pass|warn|fail`.

GO rule:
- No invariant violations in baseline scenarios.

NO-GO rule:
- Any acyclic/monotonic break in baseline output.

---

## 4) Verifier Policy Gate (GO/NO-GO)
- [ ] `fail` emitted when required by policy (acyclic/monotonic/spectral fail).
- [ ] `warn` emitted when orphan-rate threshold or spectral warn triggers.
- [ ] `pass` emitted otherwise.
- [ ] UI receives verifier payload and surfaces it in diagnostics.

GO rule:
- Decision policy is deterministic and visible.

NO-GO rule:
- Missing/ambiguous decision output.

---

## 5) JEPA Policy Gate (v1) (GO/NO-GO)
- [ ] JEPA remains overlay-only in v1.
- [ ] Base architecture topology is not mutated by JEPA outputs.
- [ ] If JEPA runtime unavailable, baseline builder still completes.
- [ ] Runtime-health endpoint is reachable and returns structured payload.

GO rule:
- Overlay helps, baseline always survives.

NO-GO rule:
- JEPA failure breaks DAG build or mutates backbone without policy approval.

---

## 6) Runtime and Stability Checks (GO/NO-GO)
- [ ] MCC startup path works with current launcher (`run.sh` and `python main.py`).
- [ ] JEPA autostart/health path is validated (when enabled).
- [ ] Shutdown does not hang under normal stop sequence.
- [ ] Diagnostics tab loads verifier/runtime sections without errors.
- [ ] Array API path `POST /api/mcc/graph/build-design/from-array` returns contract-compatible payload.

GO rule:
- All core runtime checks pass.

NO-GO rule:
- Startup/shutdown regressions or diagnostics dead path.

---

## 7) UI Contract Checks (GO/NO-GO)
- [ ] `runtime_graph`, `design_graph`, `predictive_overlay` are visually/contractually separated.
- [ ] Focus behavior remains deterministic across zoom/drill transitions.
- [ ] Overlay links do not flood base topology by default.
- [ ] Manual pin/layout behavior is preserved after refresh.

GO rule:
- Readable architecture-first view preserved.

NO-GO rule:
- Reintroduced spaghetti view or unstable focus/overlay behavior.

---

## 8) Rollback Readiness (GO/NO-GO)
- [ ] Predictive overlay can be disabled without breaking baseline DAG.
- [ ] Deterministic fallback path is tested and documented.
- [ ] Release note includes rollback trigger conditions.
- [ ] No destructive migration required for user layout state.

GO rule:
- Rollback can be executed quickly and safely.

NO-GO rule:
- No clear fallback path under degradation.

---

## 9) Release Decision
Mark one:
- [ ] GO
- [ ] NO-GO

Required notes:
- Build/commit:
- Evaluated scope(s):
- Known warnings accepted (if GO):
- Owner sign-off:
