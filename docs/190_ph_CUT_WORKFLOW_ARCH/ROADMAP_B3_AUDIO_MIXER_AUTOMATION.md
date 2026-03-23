# ROADMAP B3: Audio Mixer Automation
**Task:** tb_1773996025_9 — CUT-FCP7-55
**Agent:** Beta (Media Pipeline)
**Branch:** claude/cut-media
**FCP7 Ref:** Ch.55-57 (p.881-932)
**Date:** 2026-03-23

---

## Status: RECON COMPLETE

### What Exists
- `AudioMixer.tsx` (365 lines, Gamma-built): channel strips, faders, pan, mute/solo, VU sim, master bus
- `cut_audio_engine.py`: mixer state → FFmpeg filters, LUFS analysis
- Store: `laneVolumes`, `mutedLanes`, `soloLanes`, `addKeyframe(clipId, property, time, value)`
- `AudioRubberBand.tsx` (B30): per-clip volume automation overlay

### What's Missing (FCP7 Ch.55-57 gaps)

| # | Feature | FCP7 Ref | Complexity | Owner |
|---|---------|----------|------------|-------|
| B3.1 | **ClippingIndicator** — persistent red clip light per strip | p.889 | Low | Beta |
| B3.2 | **RecordKeyframes** — button + state machine for real-time keyframe recording | p.891 | Medium | Beta (component) + Alpha (hotkey) |
| B3.3 | **MixerViewPresets** — 4 view buttons for track bank visibility | p.885 | Low | Beta (component) + Gamma (wire) |
| B3.4 | **Fader dB entry** — click on % label → type exact dB value | p.888 | Low | Beta |

### Sub-task Plan

#### B3.1: ClippingIndicator.tsx (Low, Beta-only)
- Red dot next to VU meter, lights when level > 0.95
- Stays lit ("latched") until user clicks it or playback stops
- Monochrome: grey dot at rest, #ef4444 when clipped (exception like broadcast ILLEGAL)
- No backend needed — pure frontend state

#### B3.2: RecordKeyframes toggle (Medium)
- Toggle button "REC KF" on mixer panel
- When enabled + playback running: fader changes → `addKeyframe(clipId, 'volume', currentTime, value)`
- Needs: `isRecordingKeyframes` state, lookup which clip is under playhead
- Backend: no new endpoint, uses existing keyframe store
- Hotkey: Cmd+Shift+K (Alpha wires in useCutHotkeys)

#### B3.3: MixerViewPresets (Low)
- 4 small buttons [1][2][3][4] above channel strips
- Each stores which lanes are visible in mixer
- Local state (not persisted — FCP7 loses views on project close too)
- No backend needed

#### B3.4: Fader dB entry (Low)
- Click on "100%" label → editable input field
- Parse dB or % input → set volume
- No backend needed

### Execution Order
1. B3.1 ClippingIndicator (quick win, visible improvement)
2. B3.4 Fader dB entry (quick win)
3. B3.3 MixerViewPresets (quick win)
4. B3.2 RecordKeyframes (medium, needs playhead + clip lookup)

### Files to Create (Beta domain)
- `client/src/components/cut/ClippingIndicator.tsx` — latched clip light
- `client/src/components/cut/MixerViewPresets.tsx` — 4-bank view buttons
- `client/src/components/cut/FaderDbInput.tsx` — inline dB/% editor

### Files to Wire (Alpha/Gamma)
- `AudioMixer.tsx` — import and render Beta's sub-components
- `useCutHotkeys.ts` — Cmd+Shift+K for record keyframes toggle
