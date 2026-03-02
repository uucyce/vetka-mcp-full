# Pulse — Delegation Pack for Terminal Codex

Date: 2026-02-27  
Delegate: Codex in terminal  
Manager: Architect agent (main thread)

## 1) Mission
Implement and polish the UI track while preserving all existing audio/key/scale behavior.

Primary mission:
- Performance-first UX (`One Circle`) as default.
- DevPanel as full diagnostics + controls workspace.

## 2) Delegated Scope (You own)

### UI decomposition
- [ ] Split to `PerformanceView` and `DevPanelView`.
- [ ] Keep `App.tsx` as orchestration shell.
- [ ] Ensure default view = Performance.
- [ ] Add hotkey `D` and explicit toggle controls.

### DevPanel
- [ ] Migrate all existing controls into DevPanel.
- [ ] Keep calibration actions playable.
- [ ] Keep VST/MIDI/internal rack controls functional.
- [ ] Add 10-line teletype display block.

### Performance view
- [ ] Keep minimal controls only (start/test/smart-audio/toggle).
- [ ] Keep large central Camelot wheel.
- [ ] Hide raw camera feed by default (skeleton overlay acceptable).
- [ ] Keep compact key/scale/genre readability.

### UI quality
- [ ] Make wheel/container responsive for smaller screens.
- [ ] Preserve FPS and avoid heavy visual regressions.
- [ ] No duplicate conflicting panels.

## 3) Out of Scope (Do not own)
- JEPA algorithm design and calibration.
- Scale inference model logic tuning.
- Benchmark/calibration scripts and metrics pipeline.
- Audio detector theory changes outside UI hooks.

These are architect-owned and should not be modified unless explicitly requested.

## 4) Allowed File Areas
- `/pulse/src/views/**`
- `/pulse/src/state/**`
- `/pulse/src/components/**`
- UI-related portions of `/pulse/src/App.tsx`
- `/pulse/src/utils/teletypeLog.ts`

Avoid touching unless coordinated:
- `/pulse/src/music/**`
- `/pulse/src/audio/**`
- `/pulse/scripts/**`
- benchmark tests

## 5) Event Tags Contract
Teletype tags to preserve:
- `BPM_LOCK`
- `KEY_DETECT`
- `SCALE_TOP3`
- `SCALE_COMMIT`
- `JEPA_FALLBACK`
- `AUDIO_LAYER`

If tag names change, report explicitly in handoff.

## 6) Delivery Checklist
- [ ] `npm run build` passes.
- [ ] `npm test` passes.
- [ ] No loss of previously working controls.
- [ ] Performance view remains clean and minimal.
- [ ] DevPanel contains all advanced controls.

## 7) Handoff Format (required)
At completion, provide:
1. File changelog (absolute paths).
2. Functional summary of what changed.
3. Known TODOs.
4. Build/test results.
5. Any merge-risk notes for architect integration.

---

## 8) Next Batch (D2 feedback loop, delegated now)
Goal: close personalization data loop with minimal UI noise.

Task set:
- [ ] Add runtime feedback actions in DevPanel:
  - `Like Scale`, `Dislike Scale`, `Skip Session` (compact buttons).
- [ ] Persist feedback events to durable local file:
  - append JSONL records to `pulse/data/processed/jepa_feedback_events.jsonl`.
- [ ] Wire event payload from live state:
  - `detected_scale`, `committed_scale`, `genre`, `bpm`, `confidence`, `play_sec`, `skip_flag`, `explicit_feedback`.
- [ ] Add command/script to rebuild ENGRAM profile from latest events:
  - reuse existing `build_engram_profile.py` flow; ensure idempotent rerun.
- [ ] Add one integration test:
  - verifies button action writes valid event and profile rebuild reflects it.
- [ ] Keep deterministic-first contract unchanged:
  - no insertion of new scale candidates, only rerank existing top candidates.

Acceptance:
- [ ] `npm test` passes.
- [ ] `npm run build` passes.
- [ ] `npm run jepa:engram:build` reflects newly written runtime events.
