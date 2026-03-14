# Pulse — Scale Inference Windowed Spec (Reproducible)

Date: 2026-02-27
Owner: Pulse audio intelligence
Status: In progress (Phase A partially implemented in real codebase)

## Implementation Snapshot (Codebase Reality Check)
- Implemented:
- `src/music/ScaleInferenceWindowed.ts` exists and is wired in `src/App.tsx`.
- `scaleMode` (`auto/manual`) exists with manual dropdown from `SCALES_DB`.
- Auto-mode top-3 candidates are shown in UI.
- Mic sensitivity control exists and is propagated to SmartAudio/Key detector.
- Key mode (`auto/manual`) exists in UI.
- ARP/ADSR debug HUD exists.
- Gaps found during audit and addressed now:
- Output note quantization was key-only (`quantizeToScale` by Camelot key), not `selectedScaleName`-aware.
- Scale commit had hard key-compatibility gate, causing valid minor/exotic scales to never commit.
- SmartAudio key callback emitted only when key changed, starving scale inference updates and causing scale "freeze".
- BPM had weak anti-jitter logic (high jump probability under noisy onset stream).

## Immediate Fixes Applied (this iteration)
- Rewired note quantization path to `selectedScaleName + selectedCamelotKey` (`quantizeToNamedScale` and `getMidiScaleNotesForKeyAndScale`).
- Removed forced auto remap to Camelot default scale on mode/key transitions (prevents repeated fallback to Ionian).
- Switched scale commit from hard key-family gate to confidence-gated commit from windowed inference.
- Increased key auto-commit responsiveness (lower hit/hold requirements).
- SmartAudio now emits `onKey` on interval (not only on key change), so scale inference receives continuous note evidence.
- Added BPM stabilizer in SmartAudio (`median/jump guard + confidence-weighted smoothing`).

## Known Remaining Risks
- Camelot root mapping currently uses simplified `CAMELOT_TO_KEY`; enharmonic handling still coarse.
- BPM is stabilized but still onset-based; for very percussive/noisy rooms, beat lock can drift.
- Scale inference currently consumes active-note snapshots, not full chroma histograms; accuracy ceiling remains.

## Goal
Stabilize and improve realtime scale detection using beat-synchronized rolling windows, confidence gating, and deterministic rules first; optional JEPA fallback second.

## Design Principles
- Deterministic first: fast, explainable scoring before ML fallback.
- Beat-aware timing: inference aligned to musical grid, not arbitrary frame timing.
- Hysteresis over flicker: commit only with evidence + margin + persistence.
- Reproducible tuning: all thresholds and weights in config, all decisions logged.

## MARKER_PULSE_SCALE_V2_001 — Time Model
- Input: BPM + beat phase from SmartAudioEngine.
- At `120 BPM, 4/4`: beat=0.5s, bar=2s.
- Inference window size: `2 bars = 4s`.
- Rolling crawler stride: `1 bar = 2s`.
- Active windows: `W0, W1, W2` (oldest→newest), each 4s, overlapping.

This yields asynchronous comparison while remaining musically meaningful.

## MARKER_PULSE_SCALE_V2_002 — Note Cache with Decay
For each incoming note event (pitch class 0..11):
- Store `(pitchClass, ts, velocityProxy)` in a ring buffer.
- Build weighted histogram per window using exponential decay:

`weight = velocityProxy * exp(-(now - ts)/tau_ms)`

Default:
- `tau_ms = 2600`
- `velocityProxy = 1.0` if unavailable

Purpose:
- recent notes dominate,
- stale notes fade naturally,
- no hard resets between windows.

## MARKER_PULSE_SCALE_V2_003 — Per-Window Scale Score
For each candidate scale `S`:
- `coverage(S) = matched_weight / total_weight`
- `purity(S) = matched_unique_notes / max(unique_notes,1)`
- `intervalFit(S)` from existing interval logic (ScaleLearner compatible)
- `sizeBias(S)` small preference for minimal scales only under low evidence

Per-window score:

`score_w(S) = 0.46*coverage + 0.28*intervalFit + 0.18*purity + 0.08*sizeBias`

Constraints:
- keep `sizeBias` capped to avoid forced 5-note collapse.
- apply penalties for broad defaults under low evidence:
  - Chromatic, Ionian, Spanish penalties configurable.

## MARKER_PULSE_SCALE_V2_004 — 3-Window Fusion
Aggregate with recency weighting:

`score_fused(S) = 0.20*score_W0 + 0.30*score_W1 + 0.50*score_W2 + consistency_bonus`

Consistency bonus:
- +`k_consistency` if candidate is top-1 in >=2 windows.

Output each cycle:
- top-3 scales with normalized confidence,
- `margin = top1 - top2`.

## MARKER_PULSE_SCALE_V2_005 — Commit Gate (Anti-Flicker)
Commit `activeScale = top1` only if all are true:
1. `confidence(top1) >= min_conf`
2. `margin >= min_margin`
3. `top1` persists for `N` fusion cycles
4. key compatibility check passes (unless disabled)

Recommended defaults:
- `min_conf = 0.58`
- `min_margin = 0.09`
- `N = 2`

Strong override:
- allow immediate commit if `confidence>=0.78` and `margin>=0.16`.

## MARKER_PULSE_SCALE_V2_006 — Auto vs Manual
`scaleMode`:
- `auto`: pipeline commits by gate rules.
- `manual`: selected scale fixed; pipeline still computes top-3 and confidence in background for telemetry.

UI requirements:
- toggle `Auto/Manual`
- manual dropdown from `SCALES_DB`
- show top-3 in auto with percentages

## MARKER_PULSE_SCALE_V2_007 — JEPA Fallback (Optional)
Use only when deterministic confidence is weak.

Trigger:
- low confidence for `M` consecutive fusion cycles (default `M=3`).

Input payload to JEPA:
- BPM summary,
- beat stability,
- 3 window histograms (12-d vectors),
- current key,
- deterministic top-5 scores,
- recent committed scale history.

Expected JEPA output:
- `top3 scales`, `confidence`, optional explanation tags.

Arbitration:
- if deterministic gate passes -> deterministic wins.
- else if JEPA confidence high and margin strong -> JEPA proposal accepted.

## MARKER_PULSE_SCALE_V2_008 — Config (single source of truth)
Create config object/file (`scale_inference_config`):
- `window_ms`, `stride_ms`, `num_windows`
- `tau_ms`
- score weights
- penalties and bonuses
- gate thresholds (`min_conf`, `min_margin`, `persist_cycles`)
- JEPA fallback thresholds

No magic numbers in app logic.

## MARKER_PULSE_SCALE_V2_009 — Telemetry & Reproducibility
Log structured events (JSONL):
- timestamp
- bpm, beatPhase
- active key
- window histograms (compressed)
- top3 candidates + scores
- commit/no-commit reason
- mode (auto/manual)
- fallback used (none/jepa)

Required for tuning and regressions.

## MARKER_PULSE_SCALE_V2_010 — Acceptance Criteria
- Scale flip rate reduced by >=40% on same test sessions.
- Manual mode never overwritten by auto commit.
- In auto mode, top-3 always visible and confidence monotonic under stable phrase.
- No additional audible latency in note output path.

## Test Protocol
1. Fixed reference clips: ionian, aeolian, mixolydian, phrygian, chromatic noise.
2. Live mic tests at 90/120/160 BPM, 4/4.
3. Evaluate:
- time to first correct commit
- wrong commits per minute
- stability duration of active scale
- top1/top2 margin behavior

## Implementation Plan
Phase A (deterministic core) — `DONE (baseline)`:
1. Add windowed cache + decay histogram.
2. Add fused scorer + commit gate.
3. Wire to existing `scaleMode` UI and top-3 display.

Phase A.1 (stability patch) — `DONE (current iteration)`:
1. Bind output quantization to committed scale (not key-only quantization).
2. Remove hard key-family gate for scale commit.
3. Feed inference continuously (periodic onKey emits).
4. Add BPM jump guard + smoothing.

Phase B (tuning + verification) — `NEXT`:
1. Add structured telemetry logging (decision reasons, top3, commit/no-commit, bpm confidence).
2. Tune thresholds from recorded sessions (at least 3 reference scenarios: minor phrase, modal phrase, noisy room).
3. Publish benchmark table:
- wrong commits/min
- median commit latency
- BPM MAE vs reference click.

Phase C (optional JEPA) — `DEFERRED`:
1. Add fallback interface only for low-confidence streaks.
2. Run A/B deterministic vs deterministic+JEPA.
3. Keep JEPA only if measurable gain over deterministic baseline.

## Open Questions
- Should downbeat boundaries hard-reset window stride or remain wall-clock aligned?
- Should key compatibility be hard gate or soft penalty for exotic scales?
- How aggressive should generic-scale penalties be when unique notes < 6?

## Next Action
Implement Phase A in codebase (`App.tsx` + `ScaleLearner` + config module), then run benchmark protocol and attach results to this document.
