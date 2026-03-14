# IMPLEMENTATION READINESS CHECKLIST (GO/NO-GO)

Date: 2026-02-22  
Project: VETKA / MCC Unified DAG  
Flow: Research -> Design -> Plan -> Implement -> Verifier/Eval

How to use:
- Mark each item `[x]` or `[ ]`.
- A gate is `GO` only if all items in that gate are checked.
- Final implementation start is allowed only when all mandatory gates are `GO`.

---

## G0. Problem & Scope Freeze (Mandatory)
- [x] Single-window UX is fixed (no scene/window swap for architecture/task/workflow drill).
- [x] LOD behavior is fixed (L0 overview, L1 architecture, L2 workflow detail).
- [x] "No more than 3 context actions" rule is fixed for each depth/state.
- [ ] Success criteria are written in testable form (not descriptive only).

Gate G0: `NO-GO`

## G1. Design DAG Artifact Approved (Mandatory)
- [ ] Explicit Design DAG artifact exists (nodes, edges, node types, edge types).
- [ ] Root semantics are fixed (what is "base/source" in this project).
- [x] Node color/state semantics are fixed (implemented=white, planned=gray, etc.).
- [x] Folder/file policy is fixed (folders included as first-class nodes: yes/no + rules).
- [x] Workflow-team relation policy is fixed (task assigns team/workflow, not replaces DAG).

Gate G1: `NO-GO`

## G2. Graph Construction Contract (Mandatory)
- [x] Input channels are fixed (structural/import, temporal, reference, semantic, multimodal).
- [x] SCC policy is fixed (condense cycles, keep drill evidence, never silently drop).
- [ ] Edge confidence policy is fixed (thresholds per channel + evidence bundle).
- [ ] Knowledge Level formula is fixed and documented (no hidden hardcode behavior).
- [ ] Root/level ranking policy is fixed (why a node is lower/higher is explainable).

Gate G2: `NO-GO`

## G3. Layout & Readability Contract (Mandatory)
- [x] Layering policy is fixed (Sugiyama base + spectral/discrepancy balancing strategy).
- [x] Edge policy is fixed for overview vs focus (minimal set vs expanded on click).
- [ ] Crossing budget and density budget are fixed (numeric limits for acceptance).
- [ ] Viewport fit policy is fixed (must fit default project overview without manual rescue).
- [ ] Minimap and camera behavior are deterministic and documented.

Gate G3: `NO-GO`

## G4. Verifier/Eval Contract (Mandatory)
- [x] Verifier metrics are fixed: acyclicity, crossing count, layer spread, orphan rate.
- [ ] Eval thresholds are fixed (pass/fail numbers, not relative wording).
- [ ] Regression suite is fixed (snapshot JSON + screenshot baseline for MCC DAG states).
- [x] Explainability check is fixed (node can show "why this level/edge").
- [ ] GO decision is blocked automatically when verifier fails.

Gate G4: `NO-GO`

## G5. Runtime & Operations Readiness (Mandatory)
- [ ] Trigger model is fixed (event-driven sync, no uncontrolled polling loops).
- [ ] Scanner/indexer boundaries are fixed (no accidental full rescan storms).
- [ ] Feature flags are fixed for staged rollout (safe fallback to stable mode).
- [ ] Cache invalidation policy is fixed (when to rebuild L0/L1/L2, SCC, layout).
- [ ] Rollback path is documented and tested.

Gate G5: `NO-GO`

---

## Final GO/NO-GO
Mandatory gates: G0, G1, G2, G3, G4, G5

- [ ] `FINAL GO` (all mandatory gates are GO)
- [x] `NO-GO` (at least one mandatory gate is NO-GO)

Decision owner(s): Danila + Architect + Codex  
Date: 2026-02-22

---

## Immediate Next Action (if NO-GO)
- Write top-3 blockers with owner and deadline:
1. Freeze canonical Design DAG artifact and root semantics / owner: Architect / due: next session
2. Freeze numeric DAG quality thresholds (crossings, density, viewport-fit, spectral) / owner: Architect + Verifier / due: next session
3. Freeze runtime safety contract (trigger model, scan bounds, cache invalidation, rollback) / owner: Backend / due: next session
