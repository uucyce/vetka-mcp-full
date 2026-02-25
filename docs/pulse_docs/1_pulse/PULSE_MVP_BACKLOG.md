# Pulse MVP Backlog (Issue-Level)

Status: Draft v1  
Project: VETKA musical branch (`Pulse`)  
Date: 2026-02-22  
Reference: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/PULSE_ARCHITECTURE_AND_ROADMAP.md`

## Planning assumptions

1. Platform target for MVP: macOS (Apple Silicon).
2. Team cadence: 1 issue = 1-2 days.
3. Goal: playable and stable `pulse-v0.1.0`.

## Priority legend

1. P0: required for MVP.
2. P1: strongly recommended for MVP quality.
3. P2: post-MVP or stretch.

## Epic A: Foundations and app shell

## PULSE-001 (P0) - Bootstrap Tauri workspace for Pulse
Estimate: 1 day  
Dependencies: none

Scope:
1. Create `tools/pulse` project with Tauri v2 + React + TypeScript.
2. Add basic scripts for dev, build, lint, typecheck.
3. Add minimal app shell (header, status bar, placeholders for camera/audio).

Acceptance criteria:
1. `tools/pulse` builds and launches in dev mode on macOS.
2. `npm run lint` and `npm run typecheck` pass.
3. README includes startup commands and prerequisites.

## PULSE-002 (P0) - Device permissions and health checks
Estimate: 1 day  
Dependencies: PULSE-001

Scope:
1. Implement mic/camera permission request flow.
2. Device picker for input devices.
3. Health panel: mic active, camera active, audio context state.

Acceptance criteria:
1. User can grant mic/camera access from within app flow.
2. Device picker changes selected input without app restart.
3. Health panel updates correctly on disconnect/reconnect.

## Epic B: Gesture-controlled synth core

## PULSE-003 (P0) - Integrate MediaPipe hand landmarks
Estimate: 1-2 days  
Dependencies: PULSE-002

Scope:
1. Add hand landmark tracking pipeline.
2. Render landmark overlay for debugging.
3. Expose normalized landmark stream to app state.

Acceptance criteria:
1. Single-hand and two-hand detection works in normal indoor light.
2. Overlay renders at interactive rate (target >= 30 FPS camera pipeline).
3. Landmark stream provides stable normalized coordinates.

## PULSE-004 (P0) - Gesture smoothing and mapping engine
Estimate: 1 day  
Dependencies: PULSE-003

Scope:
1. Add smoothing filters (EMA/dead-zone).
2. Map left hand Y to pitch index.
3. Map right-hand pinch/open to volume, X to filter cutoff.
4. Add calibration UI (min/max, invert flags).

Acceptance criteria:
1. Mappings remain stable without jitter spikes at rest.
2. User calibration persists in local settings.
3. Manual test confirms controllable pitch + volume + filter.

## PULSE-005 (P0) - WebAudio synth graph (1-2 osc + ADSR)
Estimate: 1-2 days  
Dependencies: PULSE-001

Scope:
1. Build reusable synth graph with 1-2 oscillators.
2. ADSR envelope and gain staging.
3. Add basic limiter/clip protection.

Acceptance criteria:
1. Synth produces clean tone with no hard clipping at default settings.
2. Parameters update in real time without graph recreation.
3. CPU usage remains acceptable during 10-minute playback.

## PULSE-006 (P0) - Wire gesture control into synth
Estimate: 1 day  
Dependencies: PULSE-004, PULSE-005

Scope:
1. Connect mapped gesture controls to synth params.
2. Add fallback keyboard controls for testing without camera.
3. Add on-screen telemetry (pitch idx, volume, cutoff).

Acceptance criteria:
1. Hand movement audibly controls synth in real time.
2. Keyboard fallback can reproduce same parameter paths.
3. No audible zipper noise at normal control speed.

## Epic C: Rhythm/key analysis and harmony

## PULSE-007 (P0) - Microphone ring buffer and analysis scheduler
Estimate: 1 day  
Dependencies: PULSE-002

Scope:
1. Implement ring buffer for mic audio.
2. Sliding analysis windows (2-4 sec for key, shorter for bpm updates).
3. Scheduler with fixed update cadence and backpressure safeguards.

Acceptance criteria:
1. Buffer handles continuous 20-minute session without overflow.
2. Analysis jobs do not block UI render loop.
3. Analysis cadence remains within configured update interval.

## PULSE-008 (P0) - BPM estimator with smoothing/hysteresis
Estimate: 1-2 days  
Dependencies: PULSE-007

Scope:
1. Implement or integrate BPM detection.
2. Add smoothing and hysteresis to avoid BPM flicker.
3. Expose confidence and current BPM in state.

Acceptance criteria:
1. On steady click track, BPM converges close to expected tempo.
2. BPM display does not jump excessively at stable input.
3. If confidence is low, UI indicates uncertain state.

## PULSE-009 (P0) - Key estimator (windowed + confidence gate)
Estimate: 1-2 days  
Dependencies: PULSE-007

Scope:
1. Implement key detection on 2-4 sec windows.
2. Add confidence threshold and freeze-on-uncertain behavior.
3. UI meter for key + confidence + stale state.

Acceptance criteria:
1. Key updates are readable and not frame-by-frame noisy.
2. Uncertain detection never force-switches active scale instantly.
3. Confidence threshold is configurable.

## PULSE-010 (P0) - Harmony engine (scale quantizer + Camelot manual shift)
Estimate: 1-2 days  
Dependencies: PULSE-006, PULSE-009

Scope:
1. Implement scale quantizer for active key/mode.
2. Implement Camelot map and manual shift actions (+/-1, relative).
3. Add UI controls and hotkeys for shift actions.

Acceptance criteria:
1. Out-of-scale notes are quantized to active scale.
2. Manual shift updates scale immediately and audibly.
3. Hotkeys and UI buttons produce identical shift behavior.

## PULSE-011 (P1) - Simple arp mode synced to tempo
Estimate: 1 day  
Dependencies: PULSE-008, PULSE-010

Scope:
1. Add optional monophonic arpeggio mode.
2. Sync step timing to fixed BPM or detected BPM.
3. Add pattern selector (up/down/ping-pong basic).

Acceptance criteria:
1. Arp timing remains stable for 5+ minutes.
2. Pattern switch does not produce stuck notes.
3. Arp respects current quantized scale.

## Epic D: MIDI, reliability, and release hardening

## PULSE-012 (P0) - Rust MIDI I/O bridge
Estimate: 1-2 days  
Dependencies: PULSE-001

Scope:
1. Implement Rust-side MIDI out and optional MIDI in.
2. IPC commands/events between frontend and Rust.
3. Device list and reconnect logic.

Acceptance criteria:
1. App sends MIDI notes/CC to external synth or DAW.
2. Device reconnect works without app restart.
3. MIDI errors are surfaced in UI, not silent.

## PULSE-013 (P1) - Presets and settings persistence
Estimate: 1 day  
Dependencies: PULSE-006, PULSE-010

Scope:
1. Save/load presets (gesture sensitivity, synth params, harmony mode).
2. Default preset + reset behavior.
3. Basic validation for corrupted settings.

Acceptance criteria:
1. Presets survive app restart.
2. Reset returns to known-good defaults.
3. Corrupt preset file is handled gracefully.

## PULSE-014 (P0) - Stability pass and performance instrumentation
Estimate: 1-2 days  
Dependencies: PULSE-012

Scope:
1. Add performance counters (audio callback load, FPS, event lag).
2. Add watchdog/fallback when camera or mic stream drops.
3. Harden error boundaries around analysis and MIDI paths.

Acceptance criteria:
1. 20-minute jam session passes without crash.
2. Drop/reconnect of camera and mic recovers automatically.
3. Performance panel shows live metrics for diagnostics.

## PULSE-015 (P0) - QA scenario suite and release checklist
Estimate: 1 day  
Dependencies: all P0 issues above

Scope:
1. Write MVP smoke test scenarios (manual + scripted where possible).
2. Document release checklist and known limitations.
3. Tag release candidate criteria for `pulse-v0.1.0`.

Acceptance criteria:
1. Smoke suite covers: startup, permissions, playability, BPM/key, Camelot, MIDI.
2. Known limitations documented in README.
3. Release checklist is executable by another team member.

## Suggested implementation order

1. PULSE-001
2. PULSE-002
3. PULSE-005
4. PULSE-003
5. PULSE-004
6. PULSE-006
7. PULSE-007
8. PULSE-008
9. PULSE-009
10. PULSE-010
11. PULSE-012
12. PULSE-014
13. PULSE-013
14. PULSE-015
15. PULSE-011 (if time allows before freeze)

## MVP release gate (must pass)

1. All P0 issues completed and accepted.
2. End-to-end latency/playability subjectively acceptable on target Mac.
3. 20-minute stability run completed with no crash and no stuck audio.
4. Core docs ready:
   - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/PULSE_ARCHITECTURE_AND_ROADMAP.md`
   - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/PULSE_MVP_BACKLOG.md`
