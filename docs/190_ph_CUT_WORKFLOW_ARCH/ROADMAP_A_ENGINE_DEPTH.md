# ROADMAP A — Engine Depth
**Author:** Alpha-2 (Engine Architect)
**Date:** 2026-03-23
**Branch:** claude/cut-engine
**Status:** ACTIVE
**Ref:** FCP7 User Manual Ch.10-26, CUT_Interface_Architecture_v1.docx

---

## Context

Core Loop is complete (surface level):
```
Import → Preview → Mark (I/O) → Edit (,/.) → Trim (R drag) → Transition (⌘T) → Export
```

Session stats (Alpha-2):
- 14 commits, 37 Python tests, 0 TS errors introduced
- UNDO-FIX: 9 setLanes bypasses eliminated
- DUAL-VIDEO: Source/Program fully decoupled (4 commits)
- TDD: 7 FCP7 precision tests addressed
- JKL: K+J/K+L frame stepping
- Stereo waveform wired

**Now: DEPTH of each link.** Every feature works at demo level. None works at editor level.

---

## Phase 1 — Trim Depth (FCP7 Ch.19-22)

### Already Done
- [x] Edge handles (7px hit area, cursor per tool)
- [x] Ripple trim (R + drag edge → shift subsequent)
- [x] Roll trim (R×2 + drag → adjust boundary, preserve duration)
- [x] Slip (Y + drag body → change source_in)
- [x] Slide (U + drag → move clip, adjust neighbors)
- [x] Local-first optimistic updates for all modes
- [x] Backend ops: ripple_trim, trim_clip, slip_clip
- [x] Tool cycling: R→ripple→roll, Y→slip→slide

### TODO
| ID | Feature | FCP7 Ref | Owner | Complexity |
|----|---------|----------|-------|------------|
| TD1 | **Trim Edit Window** — dedicated UI for precision trim with two-up display | Ch.20 | Alpha | high |
| TD2 | **Asymmetric trim** — different L/R values on edit point | Ch.21 | Alpha | medium |
| TD3 | **Extend Edit (E key)** — extend nearest edit to playhead | Ch.19 p.285 | Alpha | low |
| TD4 | **Numeric trim entry** — type +5 or -3 to trim by frames | Ch.20 | Alpha | low |
| TD5 | **Trim during playback** — Dynamic Trim (JKL while trimming) | Ch.22 | Alpha | high |
| TD6 | **Multi-track trim** — linked clips trim together | Ch.19 | Alpha | medium |

### Priority: TD3 (Extend Edit) → TD2 (Asymmetric) → TD4 (Numeric) → TD1 (Window)

---

## Phase 2 — Transitions Depth (FCP7 Ch.24-26)

### Already Done
- [x] Cmd+T → cross dissolve at nearest edit point
- [x] Backend: set_transition op (add/remove/replace)
- [x] Visual: gradient overlay with XD/DB/W label
- [x] Click to remove, right-click to cycle type
- [x] Context menu add/remove
- [x] Framerate-aware default duration (30 frames)
- [x] Undo support via applyTimelineOps

### TODO
| ID | Feature | FCP7 Ref | Owner | Complexity |
|----|---------|----------|-------|------------|
| TR1 | **Duration drag** — drag transition edge to resize | Ch.25 p.385 | Alpha | medium |
| TR2 | **Alignment control** — start/center/end on edit point | Ch.24 p.375 | Alpha | low |
| TR3 | **Audio crossfade** — separate from video transition | Ch.26 | Beta | medium |
| TR4 | **Dip to Black/White** — proper render (not just CSS) | Ch.24 | Alpha | low |
| TR5 | **Transition browser** — drag from Effects panel to edit point | Ch.24 | Gamma | medium |
| TR6 | **Duplicate frame detection** — white dots indicator | Ch.25 p.389 | Alpha | low |

### Priority: TR1 (Duration drag) → TR2 (Alignment) → TR6 (Duplicate frames) → TR3 (Audio)

---

## Phase 3 — Timeline Ops (FCP7 Ch.10-12)

### Already Done
- [x] Insert edit (comma → insert_at op, ripple)
- [x] Overwrite edit (period → overwrite_at op)
- [x] Replace edit (F11 → replace_media op)
- [x] Three-point edit resolution (FCP7 Ch.36 rules)
- [x] Local-first fallback when backend unavailable
- [x] Split (Cmd+K → split_at op)
- [x] Delete / Ripple Delete
- [x] Nudge ±1 frame

### TODO
| ID | Feature | FCP7 Ref | Owner | Complexity |
|----|---------|----------|-------|------------|
| TL1 | **Fit to Fill** — speed-adjust source to fit sequence range | Ch.11 p.165 | Alpha | medium |
| TL2 | **Superimpose** — add clip on V2 above current clip | Ch.11 p.167 | Alpha | medium |
| TL3 | **Multi-track editing** — V2/V3/A2/A3 targeting | Ch.12 | Alpha | high |
| TL4 | **Linked selection** — video+audio move together | Ch.10 p.145 | Alpha | medium |
| TL5 | **Through edits** — visual indicator for continuous media | Ch.10 p.152 | Alpha | low |
| TL6 | **Gap detection + close** — find and remove timeline gaps | Ch.10 | Alpha | low |

### Priority: TL4 (Linked selection) → TL3 (Multi-track) → TL1 (Fit to Fill)

---

## Phase 4 — Immediate Bug Fixes

| ID | Task | Priority | Source |
|----|------|----------|--------|
| BF1 | Kill #3b82f6 blue in TimelineTrackView.tsx:162 | P0 | Monochrome rule |
| BF2 | Inspector doesn't react to clip selection (tb_1774229417_11) | P2 | Delta |
| BF3 | Program Monitor error toast (tb_1774229426_12) | P2 | Delta |

---

## Delegation Map

| Agent | Responsibility |
|-------|---------------|
| **Alpha** (Engine) | Trim depth, Timeline ops, Inspector/store wiring |
| **Beta** (Media) | Audio crossfade (TR3), stereo waveform backend |
| **Gamma** (UX) | Transition browser (TR5), Trim Edit Window UI (TD1), MonitorTransport UI |
| **Delta** (QA) | TDD tests for each new feature, regression suite |

---

## Success Metric

**Editor can do a complete 5-minute edit using only CUT:**
1. Import media from folder
2. Preview clips in Source monitor
3. Mark I/O on source clips
4. Insert/overwrite clips into timeline
5. Trim edit points with ripple/roll
6. Add transitions between clips
7. Export to Premiere XML

Each step works at professional speed (sub-200ms response).

---

*"Core Loop gave CUT a skeleton. Depth gives it muscle."*
— Alpha-2, continuing Alpha-1's work
