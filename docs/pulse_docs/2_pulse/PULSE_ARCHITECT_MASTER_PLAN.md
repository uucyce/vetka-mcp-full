# Pulse — Architect Master Plan (Owner: Codex Main)

Date: 2026-02-27  
Owner: Main architect agent (this thread)  
Scope: end-to-end technical coherence, JEPA track, integration, release readiness

## 1) Role and Ownership
This document defines what is owned by the main architect agent.

Owned by Architect:
- JEPA integration strategy and implementation.
- Scale/BPM inference quality pipeline and benchmark methodology.
- Final integration of UI branch + inference branch.
- Release-gate checks and packaging acceptance.
- Cross-system plan for future Pulse -> VETKA memory connectors.

Not owned by Architect (delegated):
- Primary UI decomposition and view-level polishing.
- DevPanel ergonomics and visual composition work.

## 2) Hard Constraints
- Keep audio playability first (no latency regressions).
- Deterministic inference is primary; JEPA is gated fallback.
- No duplicate ownership in active files (avoid edit collisions).
- All major changes must be benchmarked with explicit deltas.

## 3) Active Architect Workstream

### A) JEPA Technical Track
- [ ] A1. Maintain `JepaScaleResolver` as isolated module.
- [ ] A2. Feed resolver with structured inference features:
  - 3 window histograms
  - unique note counts
  - evidence weights
  - bpm context
- [ ] A3. Keep timeout/circuit-breaker strict.
- [ ] A4. Maintain arbitration policy:
  - deterministic wins on strong confidence
  - JEPA rerank only in ambiguous/conflicted states

### B) Calibration + Benchmark Track
- [ ] B1. Maintain synthetic benchmark harness (`ScaleBenchmark`).
- [ ] B2. Add CSV/MD report output for A/B runs.
- [ ] B3. Add deterministic vs deterministic+JEPA benchmark mode.
- [ ] B4. Track metrics:
  - top1 accuracy
  - top3 recall
  - commit-match rate
  - fallback-scale rate
- [ ] B5. Prepare dataset manifest for future real calibration set.

### C) Integration Track
- [ ] C1. Integrate terminal Codex UI branch with zero behavior regressions.
- [ ] C2. Reconcile `App.tsx` merge points safely (if needed).
- [ ] C3. Run full build/test + tauri build acceptance.
- [ ] C4. Produce concise integration report.

## 4) File Ownership Policy (Architect Side)
- `/pulse/src/music/**` -> architect-owned (JEPA/inference/calibration).
- `/pulse/src/audio/**` -> architect-owned for inference/BPM logic only.
- `/pulse/src/__tests__/scale_*` -> architect-owned.
- `/pulse/scripts/**` -> architect-owned benchmark/calibration scripts.
- `/docs/pulse_docs/2_pulse/**` -> architect-owned planning/reporting docs.

Restricted unless explicit sync with terminal Codex:
- `/pulse/src/App.tsx`
- `/pulse/src/views/**`
- `/pulse/src/state/**`

## 5) Delegation Rules
- UI tickets are delegated to terminal Codex by default.
- Architect only consumes stable UI API/contracts from delegated branch.
- If delegated branch modifies shared orchestration points:
  - architect requests checkpoint hash or diff summary,
  - then integrates JEPA hooks with minimal touch.

## 6) Merge and Release Protocol
- [ ] M1. Freeze parallel edits in shared files before merge.
- [ ] M2. Merge delegated UI branch first.
- [ ] M3. Re-run JEPA benchmark and regression tests.
- [ ] M4. Build:
  - `npm run build`
  - `npm test`
  - `npm run tauri build`
- [ ] M5. Publish bundle paths and test checklist.

## 7) Future Pulse -> VETKA Connectors (Architect Responsibilities)
- ENGRAM: preferred scales memory priors.
- CAM: successful instrument/preset context.
- ARC: soft hypotheses for ambiguous transitions.
- HOPE: hierarchy constraints for scale families.
- STM: short-window stability consensus.
- Eval Agent: session feedback + threshold recommendations.

Integration principle:
- connectors are priors, never hard overrides of realtime evidence.

