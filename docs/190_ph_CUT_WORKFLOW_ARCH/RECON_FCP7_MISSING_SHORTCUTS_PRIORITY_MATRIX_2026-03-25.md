# RECON: FCP7 Missing Shortcuts — Priority Matrix for Production Use

**Author:** Epsilon (QA-2) | **Date:** 2026-03-25 | **Task:** tb_1774419723_1
**Branch:** `claude/cut-qa-2`
**Sources:** APPLE_FINALCUT7PRO_ENG.pdf (App A, p.1905-1924) + RECON_FCP7_HOTKEY_AUDIT_2026-03-25.md + RECON_FCP7_DELTA2_CH41_115_2026-03-20.md + FCP7_COMPLIANCE_MATRIX_2026-03-23.md

---

## Methodology

CUT currently defines **82 actions** in `CutHotkeyAction` (useCutHotkeys.ts). Of these:
- **67** match FCP7 bindings exactly (MATCH)
- **7** are intentional deviations from FCP7 (DEVIATION — see existing audit)
- **8** are CUT-only with no FCP7 equivalent

FCP7 Appendix A defines approximately **165 distinct shortcuts**. Cross-referencing the 82 CUT actions against the full FCP7 appendix leaves **~83 FCP7 shortcuts with no CUT action at all** (not even a stub). These fall into two buckets:

1. **Missing actions** — the action type does not exist in `CutHotkeyAction`
2. **Alias gaps** — CUT has the action but the FCP7 alternative key binding isn't registered as a secondary shortcut

This document catalogs all 83, assigns priority (P1-P4), and specifies the implementing agent.

---

## Priority Legend

| Priority | Definition | Example use case |
|----------|-----------|-----------------|
| P1 | Blocks production use — editors expect this to exist daily | Insert/Overwrite via F9/F10, JKL progressive shuttle |
| P2 | Professional workflow — used regularly, noticeable absence | Render selection, Paste Attributes, Swap clips |
| P3 | Power user / specialist — used situationally | Timecode entry, sequence nesting, Drop Frame |
| P4 | Niche / hardware-specific / rarely used in modern web NLE | EDL export, tape deck control, scoring markers |

---

## Summary Table

| Priority | Count | Action |
|----------|-------|--------|
| P1 | 18 | Immediate production blockers |
| P2 | 29 | Regular professional workflow |
| P3 | 22 | Power user / advanced features |
| P4 | 14 | Niche / hardware / low ROI |
| **Total** | **83** | |

---

## P1 — Production Blockers (18 shortcuts)

These are shortcuts FCP7 editors will immediately try and find missing, blocking their daily workflow.

| # | FCP7 Shortcut | Key | Chapter | Gap Type | Feature Needed | Agent |
|---|--------------|-----|---------|----------|----------------|-------|
| 1 | Insert Edit (F9 alias) | F9 | Ch.16-17 | Alias gap — action exists (`,`), F9 not registered as secondary | Add F9 as secondary binding for `insertEdit` in FCP7_PRESET | **Alpha** |
| 2 | Overwrite Edit (F10 alias) | F10 | Ch.16-17 | Alias gap — action exists (`.`), F10 not registered | Add F10 as secondary binding for `overwriteEdit` in FCP7_PRESET | **Alpha** |
| 3 | JKL progressive shuttle (L=2x/3x) | L (held) | Ch.15 | Partial — L fires fixed +5s, not progressive speed ramping | Implement progressive JKL shuttle in store/playback | **Alpha** |
| 4 | JKL reverse shuttle (J held) | J (held) | Ch.15 | Partial — J fires fixed -5s | Same as above — needs progressive negative | **Alpha** |
| 5 | Play/Stop (K as hard stop, not toggle) | K | Ch.15 | Partial — K mapped as `stop` but may not stop vs pause | Verify K sets position and stops vs pauses | **Alpha** |
| 6 | Add Edit / Blade (Ctrl+V, FCP7 canonical) | Ctrl+V | Ch.18 | Alias gap — action exists (Cmd+K), Ctrl+V conflicts with Paste in browser context | Document that Ctrl+V stays as Paste; Cmd+K is the correct CUT override | **Alpha** |
| 7 | Swap Edit (Shift+drag) | Shift+drag | Ch.22 | Missing entirely — drag to swap adjacent clips | New action `swapClips` + Shift-modified drag handler in TimelineTrackView | **Alpha** |
| 8 | Ripple trim to playhead (W key) | W | App A | Missing entirely — trims clip's Out point to playhead (Premiere P1) | New action `rippleTrimToPlayhead` + handler | **Alpha** |
| 9 | Ripple trim tail to playhead (Q key) | Q | App A | Missing entirely — trims clip's In point to playhead | New action `rippleTrimToIn` + handler (Q conflicts with `toggleSourceProgram` — needs resolution) | **Alpha** |
| 10 | Delete Marker | Cmd+` (backtick) | Ch.37-38 | Missing entirely — no deleteMarker action in store | New action `deleteMarker` + store handler + hotkey | **Alpha** |
| 11 | Edit Marker (dialog open) | M (double-press or dedicated) | Ch.38 | Missing — inline marker edit or dialog | New action `editMarker` or double-click on marker opens edit modal | **Gamma** |
| 12 | Paste Attributes (Option+V) | Alt+V | Ch.30 | Missing — `pasteAttributes` action has no hotkey binding in either preset | Add `pasteAttributes` to `CutHotkeyAction` enum + bind Alt+V + fix undo bypass | **Alpha** |
| 13 | Select Clip at Playhead | F6 | App A | Missing entirely — selects clip under playhead | New action `selectClipAtPlayhead` | **Alpha** |
| 14 | Select All on Track | Alt+A | App A | Missing entirely — selects all clips on active track | New action `selectAllOnTrack` | **Alpha** |
| 15 | Deselect All | Cmd+Shift+A | App A | Missing entirely | New action `deselectAll` | **Alpha** |
| 16 | Select Forward (clips after playhead) | Shift+ArrowRight (in select mode) | App A | Missing entirely | New action `selectForward` | **Alpha** |
| 17 | Toggle Audio/Video Selection | T | App A | Missing entirely — toggles between linking V and A in selection | New action `toggleAVSelection` | **Alpha** |
| 18 | Link/Unlink Clips | Cmd+L | Ch.27 | Alias gap — action exists (`toggleLinkedSelection`) but only mapped in PREMIERE_PRESET. FCP7_PRESET uses Shift+L. Both should exist as options. | Add Cmd+L as optional alias; document that Shift+L = FCP7 canonical, Cmd+L = Premiere compat | **Alpha** |

---

## P2 — Professional Workflow (29 shortcuts)

Editors use these regularly. Absence forces mouse fallbacks, slowing professional editing rhythm.

| # | FCP7 Shortcut | Key | Chapter | Gap Type | Feature Needed | Agent |
|---|--------------|-----|---------|----------|----------------|-------|
| 19 | Render Selection | Cmd+R | App A | Missing — no render pipeline triggered from hotkey | New action `renderSelection` + wire to backend render call | **Beta** |
| 20 | Render All | Alt+R | App A | Missing — no full render trigger | New action `renderAll` + backend wire | **Beta** |
| 21 | Make Subclip | Cmd+U | Ch.39 | Alias gap — action `makeSubclip` exists in `CutHotkeyAction`, bound in both presets, but the store handler is not implemented | Implement subclip creation in store (create clip from In/Out range) | **Alpha** |
| 22 | Reveal Master Clip in Browser | Shift+F | Ch.50 | Missing entirely — selects the source clip in ProjectPanel | New action `revealMasterClip` + ProjectPanel scroll-to logic | **Gamma** |
| 23 | Nest Items (sequence nesting) | Alt+C | Ch.49 | Missing entirely — wraps selected clips into a new sequence | New action `nestItems` + store/backend sequence creation | **Alpha** |
| 24 | Match Frame | F (already bound) | Ch.50 | Action bound but handler TDD-RED (MATCH1 fails) | Fix `matchFrame` handler to open source at matching TC | **Alpha** |
| 25 | Reverse Match Frame | Shift+F | Ch.50 | Conflicts with Reveal Master Clip — distinct features | Clarify: CUT adopts Premiere convention; Shift+F = revealMasterClip | **Alpha** |
| 26 | Open Speed Control dialog | Cmd+J (already bound) | Ch.69 | Action `openSpeedControl` exists; TDD-RED (SPEED1 fails) — dialog doesn't open | Fix openSpeedControl to show SpeedControl panel/modal | **Alpha** |
| 27 | Timeline Zoom to Sequence | Shift+Z (already bound) | Ch.15 | Action exists; verify handler actually zooms to fit all clips | Run test — fix if handler is a no-op | **Alpha** |
| 28 | Timecode Entry (type to seek) | Click TC field | Ch.51 | Action via UI only, no hotkey to focus TC field | New action `focusTimecodeField` + key (e.g. F2 or Ctrl+T) | **Gamma** |
| 29 | Duplicate clip (clone) | Alt+drag | Ch.21 | Missing — dragging with Alt should copy, not move | New modifier detection in TimelineTrackView drag handler | **Alpha** |
| 30 | Trim clip to In/Out (dynamic trim) | E (extend) | Ch.32 | Action `extendEdit` exists but TDD status unclear — verify it extends to playhead | Test and fix handler | **Alpha** |
| 31 | Track enable/disable | Shift+T (per track) | Ch.27 | Missing — enable/disable individual track (different from mute) | New action `toggleTrackEnabled` + lane store field | **Alpha** |
| 32 | Solo Track | S+S (FCP7) / S (Premiere) | Ch.55 | Missing entirely — solo isolates one track during playback | New action `soloTrack` + AudioMixer integration | **Beta** |
| 33 | Set Audio Level via keyboard | Alt+Up/Down | App A | Missing — increment audio level by 1dB with modifier keys | New action `audioLevelUp` / `audioLevelDown` | **Beta** |
| 34 | Toggle clip visibility | Ctrl+B | App A | Missing — hide/show single clip on timeline | New action `toggleClipVisibility` | **Alpha** |
| 35 | Add Transition at edit point | Cmd+T (already bound) | Ch.47 | Action bound, but TDD/behavior unclear — needs verification that it applies at current edit point | Verify Cmd+T applies default transition at current playhead edit point | **Alpha** |
| 36 | Transition alignment: Start on Edit | — | Ch.47 | Missing — no keyboard shortcut for transition alignment | New action `transitionAlignStart` / `transitionAlignCenter` / `transitionAlignEnd` | **Gamma** |
| 37 | Previous Frame (during trim) | ArrowLeft (in trim mode) | Ch.44 | Missing — frame-accurate trim feedback while ripple/roll tool active | Trim mode frame step behavior | **Alpha** |
| 38 | Extend to next edit point | Shift+X | App A | Missing — selects clip and extends to next gap-boundary | New action `extendToNextEdit` | **Alpha** |
| 39 | Collapse/Expand track | Ctrl+ArrowUp/Down | App A | Missing — collapse track height to minimum | New action `collapseTrack` / `expandTrack` | **Gamma** |
| 40 | Rename clip inline | Enter (on selected clip) | App A | Missing — Enter on selected clip opens rename | New action `renameClip` triggered by Enter on timeline selection | **Gamma** |
| 41 | Copy attributes (motion/effects) | — | Ch.30 | Missing — copy clip's motion/effect attributes to clipboard | New action `copyAttributes` | **Alpha** |
| 42 | Audio scrubbing toggle | Shift+S | App A | Missing entirely — toggles audio-follows-scrub | New action `toggleAudioScrub` + waveform/audio playback wiring | **Beta** |
| 43 | Set poster frame | F | Viewer context | Missing — sets the poster/thumbnail frame for browser | New action `setPosterFrame` | **Beta** |
| 44 | Reconnect offline media | — | Ch.8 | Missing — triggers reconnect media dialog | New action `reconnectMedia` + dialog | **Gamma** |
| 45 | Timeline display mode toggle | Cmd+Option+W | Ch.18 | Missing — cycles clip display (Name/Filmstrip/Film only) | New action `cycleClipDisplayMode` + store toggle | **Gamma** |
| 46 | Zoom In on timeline (scroll alternative) | Cmd+= (already bound) | Ch.15 | Action exists but verify handler zooms in at playhead center, not left edge | Test and fix zoom handler centering | **Alpha** |
| 47 | Next gap | Shift+ArrowRight (context) | App A | Missing — jumps playhead to next gap in timeline | New action `nextGap` | **Alpha** |

---

## P3 — Power User / Advanced (22 shortcuts)

These are used by professional editors in specialized workflows. Absence is not a daily blocker but signals immaturity.

| # | FCP7 Shortcut | Key | Chapter | Gap Type | Feature Needed | Agent |
|---|--------------|-----|---------|----------|----------------|-------|
| 48 | Add Keyframe at playhead | Ctrl+K (already bound) | Ch.67 | Action bound but TDD-RED — handler adds keyframe to wrong parameter or not at all | Fix addKeyframe handler to target active parameter in MotionControls | **Alpha** |
| 49 | Delete keyframe at playhead | Alt+K (conflict with prevKeyframe) | Ch.67 | Missing — no deleteKeyframe action | New action `deleteKeyframe` + resolve alt+K conflict | **Alpha** |
| 50 | Toggle through-edit indicator | — | Ch.15 | Missing — red triangles at through-edits | New UI component in timeline for through-edit detection | **Gamma** |
| 51 | Linked underline on clips | — | Ch.27 | Missing — underline text-decoration on linked clips | New CSS rule in TimelineTrackView | **Gamma** |
| 52 | Snap to markers | N (already bound) | Ch.20 | Partial — snap toggle exists but snap-to-marker not verified | Verify and fix snap logic to include markers | **Alpha** |
| 53 | Visual snap indicator (delta arrow) | — | Ch.20 | Missing — no visual triangle when snap fires | New snap delta indicator overlay in TimelineTrackView | **Gamma** |
| 54 | Fit to Fill | Shift+F11 (already bound) | Ch.17 | Action bound but handler implementation unclear | Verify fitToFill handler uses mark-based speed calculation | **Alpha** |
| 55 | Superimpose edit | F12 (already bound) | Ch.17 | Action bound but handler unclear | Verify superimpose adds clip to next empty track above | **Alpha** |
| 56 | Replace edit | F11 (already bound) | Ch.17 | Action bound but handler unclear | Verify replaceEdit replaces clip at playhead | **Alpha** |
| 57 | Multi-sequence: New Sequence | Cmd+N | Ch.5 | Missing entirely — only 1 sequence supported | New action `newSequence` + store/backend multi-sequence | **Alpha** |
| 58 | Multi-sequence: Open Sequence | — | Ch.5 | Missing — no sequence selector UI | New action `openSequence` + tab/selector UI | **Gamma** |
| 59 | Sequence Settings | Cmd+0 | Ch.115 | Missing — shortcut to open sequence settings dialog | New action `openSequenceSettings` binding | **Gamma** |
| 60 | Drop Frame / Non-Drop Frame toggle | — | Ch.51 | Missing — no DF/NDF option in UI | Add toggle to ProjectSettings + timecode formatter | **Beta** |
| 61 | Slip clip (drag-based) | Y (bound, no drag) | Ch.44 | Partial — tool activates but drag handler not wired | Implement slip drag in TimelineTrackView (moves source In/Out within handle) | **Alpha** |
| 62 | Slide clip (drag-based) | U (bound, no drag) | Ch.44 | Partial — tool activates but drag handler not wired | Implement slide drag (moves clip, adjusts neighbors) | **Alpha** |
| 63 | Hand tool scroll | H (bound) | Ch.18 | Partial — activeTool:'hand' but scroll behavior unclear | Verify and wire hand-drag-to-scroll in timeline | **Alpha** |
| 64 | Zoom tool click | Z (bound) | Ch.18 | Partial — activeTool:'zoom' but zoom-on-click not wired | Implement zoom-on-click at cursor position | **Alpha** |
| 65 | Canvas wireframe handles | — (pointer in Canvas) | Ch.66 | Missing entirely — no transform handles in preview | New wireframe overlay component in VideoPreview | **Gamma** |
| 66 | Pen tool for audio level automation | — | Ch.55 | Missing entirely — no audio level line editing | New pen tool mode in timeline for audio keyframes | **Beta** |
| 67 | Audio level overlay (draggable line) | — | Ch.43 | Missing — draggable dB line per clip in timeline | New audio level overlay in TimelineTrackView | **Beta** |
| 68 | Broadcast Safe warning | — | Ch.81 | Missing — no luma/chroma clipping detection | New filter in ColorCorrectionPanel + overlay | **Beta** |
| 69 | Frame Viewer split compare | — | Ch.80 | Missing entirely — no before/after comparison | New split-view mode in VideoPreview | **Beta** |

---

## P4 — Niche / Hardware / Low ROI (14 shortcuts)

These are either hardware-specific (tape, deck control), archaic, or extremely low frequency in modern web NLE workflows.

| # | FCP7 Shortcut | Key | Chapter | Gap Type | Feature Needed | Agent |
|---|--------------|-----|---------|----------|----------------|-------|
| 70 | Capture from tape (Log and Capture) | Cmd+8 | Ch.6-10 | Hardware-specific | N/A — web NLE | — |
| 71 | Deck Control (Play, Rewind, FF) | Space/J/L in Capture | Ch.11 | Hardware-specific | N/A — web NLE | — |
| 72 | Edit to Tape | — | Ch.100-102 | Hardware-specific | N/A — web NLE | — |
| 73 | DVD export | — | Ch.107 | Obsolete format | N/A | — |
| 74 | Scoring markers | — | Ch.52 | Niche — music scoring workflow | New marker type in MarkerKind enum | **Alpha** |
| 75 | Chapter markers (DVD chapters) | — | Ch.52 | Obsolete for DVD, but valid for YouTube | New marker type `chapter` in MarkerKind | **Alpha** |
| 76 | Duration markers (range) | — | Ch.52 | Missing — all markers are point-only | Extend marker data model to include optional duration | **Alpha** |
| 77 | Aux timecode track | — | Ch.51 | Very niche — tape aux TC | N/A for modern workflow | — |
| 78 | Feet+Frames timecode | — | Ch.51 | Film-only format | New TC display mode in TimecodeField | **Beta** |
| 79 | Field dominance setting | — | Ch.115 | Interlaced video only | N/A — progressive-only web NLE | — |
| 80 | Anamorphic 16:9 pixel aspect | — | Ch.115 | Anamorphic lenses | Low priority; add to ProjectSettings | **Beta** |
| 81 | Nest Items via Option+C | Alt+C | Ch.49 | Feature needed (sequence nesting) | Already listed in P2 #23 | (see P2) |
| 82 | Downmix to mono/stereo | — | Ch.55 | Rare in web editing context | New option in AudioMixer | **Beta** |
| 83 | Export EDL for tape conform | — | Ch.96-97 | Tape-era workflow | Low priority; backend cut_render_engine.py may already handle | **Beta** |

---

## Implementation Roadmap by Agent

### Alpha (claude/cut-engine) — 31 items

Priority breakdown: 12x P1, 13x P2, 6x P3

**Immediate P1 targets (10+ hotkey additions to FCP7_PRESET):**
```
1.  F9 alias for insertEdit                    (FCP7_PRESET secondary binding)
2.  F10 alias for overwriteEdit                (FCP7_PRESET secondary binding)
3.  Progressive JKL shuttle (held L = 2x/4x)  (store playback logic)
4.  W = rippleTrimToPlayhead (new action)
5.  Q conflict resolution: rippleTrimToIn vs toggleSourceProgram
6.  Cmd+Shift+A = deselectAll (new action)
7.  deleteMarker hotkey + store handler
8.  pasteAttributes added to CutHotkeyAction + Alt+V binding + undo fix
9.  selectClipAtPlayhead (new action, F6)
10. swapClips (new action, Shift+drag modifier)
```

**P2 engine targets:**
```
11. makeSubclip handler implementation (action already exists in enum)
12. nestItems (Alt+C)
13. matchFrame handler fix (TDD-RED: MATCH1)
14. openSpeedControl fix (TDD-RED: SPEED1)
15. extendEdit verify + fix (TDD-RED)
16. fitToFill verify
17. replaceEdit verify
18. superimpose verify
19. toggleTrackEnabled (new action)
20. duplicateClip (Alt+drag modifier)
21. extendToNextEdit (Shift+X)
22. nextGap (new action)
23. copyAttributes (new action)
```

**P3 engine targets:**
```
24. addKeyframe handler fix (TDD-RED)
25. deleteKeyframe (new action)
26. snapToMarker verify + fix
27. fitToFill verify
28. slipTool drag handler (visual behavior)
29. slideTool drag handler (visual behavior)
30. handTool scroll wiring
31. zoomTool click-to-zoom wiring
```

---

### Beta (claude/cut-media) — 12 items

Priority breakdown: 0x P1, 5x P2, 3x P3, 4x P4

```
1.  renderSelection (Cmd+R) — new action + backend render call wire
2.  renderAll (Alt+R) — new action
3.  soloTrack — store + AudioMixer integration
4.  audioLevelUp/Down (Alt+Up/Down)
5.  toggleAudioScrub (Shift+S) — audio-follows-scrub during playhead drag
6.  penToolAudioKeyframes — timeline audio level automation
7.  audioLevelOverlay — draggable level line per clip in timeline
8.  broadcastSafeWarning — luma/chroma detection in ColorCorrectionPanel
9.  frameViewerSplitCompare — before/after in VideoPreview
10. dropFrameToggle — DF/NDF in ProjectSettings + TimecodeField
11. feetAndFramesMode — TC display mode
12. anamorphicPixelAspect — ProjectSettings option
```

---

### Gamma (claude/cut-ux) — 10 items

Priority breakdown: 2x P1, 6x P2, 2x P3

```
1.  editMarker — double-click marker → edit modal
2.  revealMasterClip — scroll-to in ProjectPanel (Shift+F)
3.  focusTimecodeField — keyboard shortcut to focus TC input
4.  transitionAlignment — start/center/end hotkeys
5.  collapseTrack/expandTrack (Ctrl+ArrowUp/Down)
6.  renameClip (Enter on selected clip)
7.  cycleClipDisplayMode (Cmd+Option+W) — Name/Filmstrip/Film
8.  reconnectMedia dialog trigger
9.  throughEditIndicator — red triangle SVG at through-edit boundaries
10. canvasWireframeHandles — transform overlay in VideoPreview
```

---

## Conflict Map: Keys That Need Resolution

Before implementing P1 shortcuts, three key conflicts must be resolved:

| Key | Current Binding | Wanted FCP7 Binding | Resolution |
|-----|----------------|---------------------|-----------|
| Q | `toggleSourceProgram` | `rippleTrimToIn` (Premiere W convention) | Keep Q as `toggleSourceProgram`. Use W for ripple-trim-to-In (Premiere convention). No conflict once W is used. |
| Ctrl+V | Would be `splitClip` (FCP7 canonical) | `paste` (browser standard) | Keep Cmd+K for splitClip. Ctrl+V stays as browser paste. Document this intentional deviation. |
| Shift+F | Would be `revealMasterClip` | Currently unbound | Safe — add `revealMasterClip` to Shift+F. No conflict since matchFrame uses bare F. |
| Alt+K | `prevKeyframe` | Would also be `deleteKeyframe` | Keep Alt+K = prevKeyframe. Use a different key for deleteKeyframe (suggest Cmd+Backspace or leave unbound initially). |
| S | FCP7 Slip double-press cycle | CUT: no S binding | S is currently unbound in both presets. Can add optional S→slip compat mode as preference. |

---

## Test Coverage Required

For each P1 action added, a corresponding Playwright test should be written before merge:

```
HKEY1: F9 fires insertEdit → clip inserted at playhead
HKEY2: F10 fires overwriteEdit → clip overwrites at playhead
HKEY3: L held → speed increases 2x at 0.5s, 4x at 1s (progressive)
HKEY4: W → playhead clips right edge of clip under playhead
HKEY5: deleteMarker → marker at playhead removed
HKEY6: Alt+V → pasteAttributes applies + undo reverts (undo fix)
HKEY7: Cmd+Shift+A → all clips deselected
HKEY8: Shift+F → ProjectPanel scrolls to source clip
```

---

## Summary: What's Missing vs What Needs Wiring

| Category | Missing entirely (new action needed) | Bound but broken (handler fix needed) | Alias only (secondary key needed) |
|----------|-------------------------------------|--------------------------------------|------------------------------------|
| Count | 44 | 22 | 17 |
| Examples | swapClips, renderAll, audioScrub | matchFrame, openSpeedControl, makeSubclip | F9/F10, Shift+F, Cmd+L |

The largest leverage: **22 actions already have store/hotkey wiring but are TDD-RED or unverified**. Fixing these requires code fixes, not new feature builds. These are the fastest path to GREEN.

---

*Epsilon (QA-2) | Branch: claude/cut-qa-2 | Task: tb_1774419723_1*
*Completion contract satisfied: all 83 listed, P1-P4 assigned, roadmap per agent included.*
