# Pulse UI v2 — One Circle + Dev Panel

Date: 2026-02-27  
Owner: Pulse product/design track  
Status: Planned (execution checklist)

## 1) Product Intent
Pulse UI must feel like a single musical instrument, not a software dashboard.

Core direction:
- Main window = performance object (`One Circle Edition`).
- Old complex UI = separate `Dev Panel` for diagnostics and experimentation.
- Default user experience must be minimal, expressive, and stage-friendly.

## 2) Information Architecture

### Window A — Performance (default)
Goals:
- one central visual object,
- no clutter,
- clear current harmonic state.

Mandatory elements:
- [ ] A1. Full-screen Camelot-Itten circle (12 sectors).
- [ ] A2. Scale polygon in center, animated smoothly.
- [ ] A3. Active key + mode shown minimally in center.
- [ ] A4. Background hue follows active key.
- [ ] A5. Active note pulse as short color flash.

Elements to remove from performance view:
- [ ] A6. No large text logs.
- [ ] A7. No debug metrics panels.
- [ ] A8. No direct VST/MIDI management controls.
- [ ] A9. No duplicated BPM/key blocks.

### Window B — Dev Panel (advanced mode)
Goals:
- full observability,
- tuning controls,
- research workflows.

Mandatory elements:
- [ ] B1. Existing controls migrated here (scale mode, key mode, VST, MIDI, thresholds).
- [ ] B2. Ten-line rolling teletype log (latest events only).
- [ ] B3. Structured event tags in teletype:
  - `BPM_LOCK`, `KEY_DETECT`, `SCALE_TOP3`, `SCALE_COMMIT`, `JEPA_FALLBACK`, `AUDIO_LAYER`.
- [ ] B4. Expandable full log export (JSONL).
- [ ] B5. Visual status badges for pipeline health:
  - audio input, BPM, key detector, scale inference, JEPA, VST rack.

## 3) Visual System (Itten + Camelot)
- [ ] C1. Define fixed hue map for 12 tones (C anchored as pure red).
- [ ] C2. Define saturation rules:
  - low saturation = background state,
  - high saturation = active note/commit pulse.
- [ ] C3. Define contrast rules:
  - warm/cool opposition for harmonic relation visibility.
- [ ] C4. Remove decorative gradients by default (flat/clean color planes first).
- [ ] C5. Add motion grammar:
  - slow morph for scale,
  - short pulse for note,
  - medium transition for key change.

## 4) Camera/Tracking Presentation
- [ ] D1. Performance window hides full camera feed by default.
- [ ] D2. Keep only minimal hand skeleton/landmark overlay (optional toggle).
- [ ] D3. Camera raw feed visible only in Dev Panel.
- [ ] D4. Add fallback state when camera off (instrument still readable).

## 5) Interaction Model
- [ ] E1. Single obvious start action in performance mode (`Start`).
- [ ] E2. Gesture-based reveal for temporary controls (if needed).
- [ ] E3. Auto/Lock/Manual shown as visual ring state, not button clutter.
- [ ] E4. Preserve manual override priority and prevent accidental mode flips.

## 6) Technical Plan
- [ ] F1. Split UI into two route-level shells:
  - `PerformanceView`,
  - `DevPanelView`.
- [ ] F2. Move current `App.tsx` panels into `DevPanelView`.
- [ ] F3. Create shared state store for both windows/views.
- [ ] F4. Add event bus for teletype (bounded ring buffer of 10).
- [ ] F5. Keep render path GPU-light for realtime responsiveness.

## 7) Definition of Done
- [ ] G1. User can perform from default window without reading diagnostics.
- [ ] G2. Dev Panel provides full control and fast debugging.
- [ ] G3. No loss of current functionality after split.
- [ ] G4. Performance view remains stable at target framerate on test machine.

## 8) Immediate Build Order
- [ ] S1. Add view split scaffold (Performance/Dev).
- [ ] S2. Implement ten-line teletype in Dev Panel.
- [ ] S3. Migrate existing controls to Dev Panel.
- [ ] S4. Build minimal One Circle performance screen.
- [ ] S5. Connect event/status indicators and validate live session flow.
