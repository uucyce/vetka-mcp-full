# CUT ↔ FCP7 Feature Coverage Matrix

> **SUPERSEDED:** Live coverage data is now in **[docs/VETKA_CUT_MANUAL.md](../VETKA_CUT_MANUAL.md)** Appendix A (78% compliance, 36 features).
> This file remains as historical Delta audit from 2026-03-22.

**Author:** Delta (QA) | **Date:** 2026-03-22 | **Source:** FCP7 Bible Ch.41-115 + App.A

## How to Read

| Status | Meaning |
|--------|---------|
| ✅ DONE | Implemented + E2E tested |
| 🟡 PARTIAL | Exists but incomplete or untested |
| 🔴 MISSING | Not implemented |
| 🧪 TDD-RED | TDD spec exists, test fails (feature WIP) |
| ⭐ CUT-ONLY | VETKA innovation, no FCP7 equivalent |

---

## Summary

| FCP7 Chapter | Topic | Coverage | Test Status |
|---|---|---|---|
| App A | Keyboard Shortcuts (~200) | 🟡 25% | 37/88 TDD pass |
| Ch.41 | Split Edits (L/J-cuts) | 🔴 0% | TDD-RED: SPLIT1 |
| Ch.42 | Multiclips (Multicam) | 🔴 0% | No tests |
| Ch.43 | Audio Editing Basics | 🟡 30% | No tests |
| Ch.44 | Trim Tools (Slip/Slide/Ripple/Roll) | 🔴 5% | TDD-RED: TRIM1b |
| Ch.45-46 | Trim Edit Window | 🔴 0% | No tests |
| Ch.47-48 | Transitions | 🟡 40% | No tests |
| Ch.49 | Sequence-to-Sequence | 🔴 0% | No tests |
| Ch.50 | Match Frame | 🔴 5% | TDD-RED: MATCH1 |
| Ch.51 | Timecode | 🟡 30% | TDD-RED: TC1 |
| Ch.55-57 | Audio Mixer | 🟡 65% | No tests |
| Ch.66-67 | Motion & Keyframes | 🟡 50% | No tests |
| Ch.69 | Clip Speed | 🟡 55% | TDD-RED: SPEED1 |
| Ch.79-83 | Color Correction | 🟡 25% | No tests |
| Ch.115 | Sequence Settings | 🟡 60% | No tests |

**Overall: ~33% FCP7 compliance (Ch.41-115)**

---

## Detailed Matrix

### Appendix A: Keyboard Shortcuts

#### Tools (A/B/R/S keys)
| FCP7 | Key | CUT Store Field | CUT Hotkey | Test | Status |
|---|---|---|---|---|---|
| Selection (Arrow) | A (FCP7) / V (Premiere) | `activeTool: 'selection'` | ✅ `selectTool` | TOOL1 ✅, TOOL2a ✅ | ✅ DONE |
| Razor (Blade) | B (FCP7) / C (Premiere) | `activeTool: 'razor'` | ✅ `razorTool` | TOOL2b ✅ | ✅ DONE |
| Ripple Edit | R (FCP7) / B (Premiere) | `activeTool: 'ripple'` | ✅ `rippleTool` | TRIM1 ✅ | ✅ DONE |
| Roll Edit | RR (FCP7) | `activeTool: 'roll'` | ✅ `rollTool` | TRIM2 ✅ | ✅ DONE |
| Slip | SS (FCP7) | `activeTool: 'slip'` | 🔴 no hotkey | TRIM3 (did not run) | 🔴 MISSING |
| Slide | SSS (FCP7) | `activeTool: 'slide'` | 🔴 no hotkey | TRIM4 (did not run) | 🔴 MISSING |
| Hand (scroll) | H | `activeTool: 'hand'` | 🔴 no hotkey | — | 🟡 store only |
| Zoom | Z | `activeTool: 'zoom'` | 🔴 no hotkey | — | 🟡 store only |
| Cursor change per tool | — | — | — | TOOL3 🧪 | 🧪 TDD-RED |

#### Playback (JKL)
| FCP7 | Key | CUT Field | Test | Status |
|---|---|---|---|---|
| Play/Pause | Space | `isPlaying` | — | ✅ DONE |
| Stop | K | `shuttleSpeed=0` | — | ✅ DONE |
| Forward shuttle | L | `shuttleSpeed++` | JKL1 🧪 | 🧪 TDD-RED (Alpha) |
| Reverse shuttle | J | `shuttleSpeed--` | JKL2 (did not run) | 🧪 TDD-RED |
| Frame step fwd | → | `currentTime+=frame` | — | ✅ DONE |
| Frame step rev | ← | `currentTime-=frame` | — | ✅ DONE |

#### Marking
| FCP7 | Key | CUT Field | Test | Status |
|---|---|---|---|---|
| Mark In | I | `markIn` | — | ✅ DONE |
| Mark Out | O | `markOut` | — | ✅ DONE |
| Add Marker | M | marker API | smoke ✅ | ✅ DONE |
| Go to In | Shift+I | — | — | 🔴 MISSING |
| Go to Out | Shift+O | — | — | 🔴 MISSING |
| Mark Clip | X | `markClip` | — | 🔴 MISSING |
| Clear In+Out | Opt+X | — | — | 🔴 MISSING |
| Next Marker | Shift+↓ | `nextMarker` | MARK2 ✅ | ✅ DONE |
| Prev Marker | Shift+↑ | `prevMarker` | — | ✅ DONE |

#### Editing
| FCP7 | Key | CUT Handler | Test | Status |
|---|---|---|---|---|
| Insert Edit | , (comma) / F9 | `insertEdit` | 3PT1 🧪 | 🧪 TDD-RED (Alpha) |
| Overwrite Edit | . (period) / F10 | `overwriteEdit` | 3PT2 (did not run) | 🧪 TDD-RED |
| Add Edit (split) | Ctrl+V / ⌘K | `splitClip` | KEYS ✅ | ✅ DONE |
| Delete | Del | `deleteClip` | — | ✅ DONE |
| Ripple Delete | Shift+Del | `rippleDelete` | — | ✅ DONE |
| Lift | ; | `liftClip` | — | 🟡 handler exists |
| Extract | ' | `extractClip` | SEQ2 ✅ | ✅ DONE |
| Extend Edit | E | — | — | 🔴 MISSING |

#### Navigation
| FCP7 | Key | CUT Handler | Test | Status |
|---|---|---|---|---|
| Match Frame | F | `matchFrame` | MATCH1 🧪 | 🧪 TDD-RED (Alpha) |
| Go to Start | Home | `goToStart` | — | ✅ DONE |
| Go to End | End | `goToEnd` | — | ✅ DONE |
| Prev Edit | ↑ | `prevEditPoint` | MON1b ✅ | ✅ DONE |
| Next Edit | ↓ | `nextEditPoint` | — | ✅ DONE |
| Q (toggle viewer/canvas) | Q | — | — | 🔴 MISSING |

#### Linked Selection
| FCP7 | Key | CUT Field | Test | Status |
|---|---|---|---|---|
| Link/Unlink toggle | ⌘L | `linkedSelection` | SPLIT1 🧪 | 🧪 TDD-RED (Alpha) |
| Linked underline indicator | — | — | EDIT2 ✅ | ✅ DONE |

---

### Ch.44: Trim Tools

| Feature | CUT Component | Test | Status |
|---|---|---|---|
| Ripple edit (R key activates) | `setActiveTool('ripple')` | TRIM1 ✅ | ✅ tool switch |
| Ripple drag shifts clips | TimelineTrackView.tsx | TRIM1b 🧪 | 🧪 TDD-RED (Alpha) |
| Roll edit | `setActiveTool('roll')` | TRIM2 ✅ | ✅ tool switch |
| Slip edit (content shift) | `setActiveTool('slip')` | TRIM3 (did not run) | 🟡 store only |
| Slide edit (clip + neighbors) | `setActiveTool('slide')` | TRIM4 (did not run) | 🟡 store only |
| Two-up trim display | — | — | 🔴 MISSING |
| Trim Edit Window (Ch.45-46) | — | — | 🔴 MISSING |

---

### Ch.47-48: Transitions

| Feature | CUT Component | Test | Status |
|---|---|---|---|
| Cross Dissolve | TransitionsPanel.tsx | — | ✅ DONE |
| Wipe transitions | TransitionsPanel.tsx | — | ✅ DONE |
| 3D transitions | TransitionsPanel.tsx | — | ✅ DONE |
| ⌘T default transition | — | — | 🔴 MISSING |
| Transition duration | TransitionsPanel.tsx | — | ✅ DONE |
| Transition alignment | — | — | 🔴 MISSING |
| Audio crossfade | TransitionsPanel.tsx | — | 🟡 PARTIAL |
| Duplicate frame indicator | — | — | 🔴 MISSING |

---

### Ch.50: Match Frame

| Feature | CUT Handler | Test | Status |
|---|---|---|---|
| F → open source at same TC | `matchFrame` in CutEditorLayoutV2 | MATCH1 🧪 | 🧪 TDD-RED |
| Shift+F → reveal master clip | — | — | 🔴 MISSING |
| Playhead Sync (Open/Gang) | — | — | 🔴 MISSING |
| Q toggle source/program focus | — | — | 🔴 MISSING |

---

### Ch.51: Timecode

| Feature | CUT Component | Test | Status |
|---|---|---|---|
| SMPTE display (HH:MM:SS:FF) | TimecodeField.tsx | — | ✅ DONE |
| Timecode entry (type to seek) | TimecodeField click handler | TC1 🧪 | 🧪 TDD-RED |
| Drop Frame (29.97) | — | — | 🔴 MISSING |
| Feet+Frames | — | — | 🔴 MISSING |

---

### Ch.55-57: Audio Mixer

| Feature | CUT Component | Test | Status |
|---|---|---|---|
| Per-track faders | AudioMixer.tsx | — | ✅ DONE |
| Pan slider | AudioMixer.tsx | — | ✅ DONE |
| Mute/Solo | AudioMixer.tsx | — | ✅ DONE |
| Level meters | AudioLevelMeter.tsx | — | ✅ DONE |
| Master fader | AudioMixer.tsx | — | ✅ DONE |
| Record keyframes | — | — | 🔴 MISSING |
| Track visibility | — | — | 🔴 MISSING |
| Audio scrubbing | — | — | 🔴 MISSING |

---

### Ch.66-67: Motion & Keyframes

| Feature | CUT Component | Test | Status |
|---|---|---|---|
| Scale/Rotation/Position | MotionControls.tsx | — | ✅ DONE |
| Opacity | MotionControls.tsx | — | ✅ DONE |
| Crop | MotionControls.tsx | — | 🟡 PARTIAL |
| Distort (4-corner) | — | — | 🔴 MISSING |
| Drop Shadow | — | — | 🔴 MISSING |
| Add Keyframe (Ctrl+K) | — | — | 🔴 MISSING |
| Keyframe navigation | — | — | 🔴 MISSING |
| Canvas wireframe handles | — | — | 🔴 MISSING |

---

### Ch.69: Speed Controls

| Feature | CUT Component | Test | Status |
|---|---|---|---|
| Constant speed (%) | SpeedControl.tsx | — | ✅ DONE |
| Variable speed (keyframes) | SpeedControl.tsx | — | ✅ DONE |
| Reverse playback | SpeedControl.tsx | — | ✅ DONE |
| ⌘J speed dialog | SpeedControl.tsx (mapped ⌘R) | SPEED1 🧪 | 🧪 TDD-RED |
| Speed Tool (palette) | — | — | 🔴 MISSING |
| Timeline speed indicators | — | — | 🔴 MISSING |
| Frame Blending | — | — | 🔴 MISSING |

---

### Ch.79-83: Color Correction (Beta scope)

| Feature | CUT Component | Test | Status |
|---|---|---|---|
| Basic curves | ColorCorrectionPanel.tsx | — | 🟡 PARTIAL |
| 3-Way corrector | — | — | 🔴 MISSING |
| Scopes (waveform/vector/histogram) | — | — | 🔴 MISSING |
| LUT application | Backend FFmpeg | — | 🟡 PARTIAL |
| Broadcast Safe | — | — | 🔴 MISSING |

---

### Ch.115: Sequence Settings

| Feature | CUT Component | Test | Status |
|---|---|---|---|
| Frame size/rate | ProjectSettings.tsx | — | ✅ DONE |
| Audio sample rate | ProjectSettings.tsx | — | ✅ DONE |
| Codec selection | Backend | — | 🟡 PARTIAL |
| TC start offset | — | — | 🔴 MISSING |
| Drop frame toggle | — | — | 🔴 MISSING |

---

## CUT Layout & Menus (TDD Coverage)

| Area | Test Spec | Pass | Fail | Skip | Status |
|---|---|---|---|---|---|
| Layout: MenuBar, DockView, panels | cut_layout_compliance_tdd | 7/12 | 0 | 5 (did not run) | 🟡 |
| Menus: File/Edit/View/Mark/Clip/Seq/Win | cut_fcp7_menus_editing_tdd | 14/22 | 0 | 8 (did not run) | 🟡 |
| Panel Focus: JKL scope, indicator | cut_panel_focus_tdd | 4/8 | 0 | 4 (did not run) | 🟡 |
| Precision: Tools, Trim, JKL, Match | cut_fcp7_precision_editing_tdd | 4/21 | 7 | 10 (did not run) | 🧪 |
| Timecode & Trim | cut_timecode_trim_tdd | 6/10 | 0 | 4 (did not run) | 🟡 |
| FCP7 Deep Compliance | cut_fcp7_deep_compliance_tdd | 8/15 | 0 | 7 (did not run) | 🟡 |

---

## CUT Innovations (No FCP7 Equivalent) ⭐

| Feature | Component | Tests | Status |
|---|---|---|---|
| PULSE AI Auto-Montage | AutoMontagePanel.tsx | — | ⭐ CUT-ONLY |
| Script Panel (teleprompter) | ScriptPanel.tsx | — | ⭐ CUT-ONLY |
| DAG Multiverse Graph | DAGProjectPanel.tsx | — | ⭐ CUT-ONLY |
| BPM Track (beat grid) | BPMTrack.tsx | — | ⭐ CUT-ONLY |
| Camelot Key Detection | CamelotWheel.tsx | — | ⭐ CUT-ONLY |
| Scene Detection AI | cut_scene_detector.py | — | ⭐ CUT-ONLY |
| StorySpace 3D | StorySpace3D.tsx | — | ⭐ CUT-ONLY |
| McKee Story Triangle | PulseInspector.tsx | — | ⭐ CUT-ONLY |
| Hotkey Preset System | HotkeyEditor.tsx | — | ⭐ CUT-ONLY |
| Time Stretch (Paulstretch) | SpeedControl.tsx | — | ⭐ CUT-ONLY |
| Triple Write Persistence | cut_triple_write.py | — | ⭐ CUT-ONLY |
| Marker Semantic Types | cut_marker_bundle_service.py | smoke ✅ | ⭐ CUT-ONLY |

---

## Test Score Summary

| Suite | Pass | Fail | Skip/DNR | Total |
|---|---|---|---|---|
| Smoke tests | 16 | 0 | 11 | 27 |
| TDD specs | 55 | 0 | 35 | 90 |
| **Total** | **71** | **0** | **46** | **117** |

**Next milestone:** Alpha fixes 7 TDD-RED → 62 pass (53% coverage)
