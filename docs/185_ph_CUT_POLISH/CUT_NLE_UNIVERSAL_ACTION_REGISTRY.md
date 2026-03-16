# CUT NLE — Universal Action Registry

**Goal:** Map all professional NLE operations to a single universal action set.
Three reference NLEs: Premiere Pro, Final Cut Pro 7, Avid Media Composer.
DaVinci Resolve follows Premiere layout — no separate preset needed (same as PPro).

**Architecture:** `Action ID` → handlers in CUT code. Presets map `Key → Action ID`.
Custom presets override any binding. Import from XML (Premiere) / plist (FCP) planned.

---

## 1. PLAYBACK & NAVIGATION

| # | Action ID | Description | Premiere Mac | FCP7 | Avid MC |
|---|-----------|-------------|-------------|------|---------|
| 1 | `play_pause` | Play / Pause toggle | Space | Space | Space |
| 2 | `stop` | Stop (pause + return to mark in) | K | K | K |
| 3 | `shuttle_back` | Play backward / shuttle reverse | J | J | J |
| 4 | `shuttle_forward` | Play forward / shuttle forward | L | L | L |
| 5 | `shuttle_back_fast` | Double-speed reverse | JJ | JJ | Shift+J |
| 6 | `shuttle_forward_fast` | Double-speed forward | LL | LL | Shift+L |
| 7 | `frame_step_back` | Step 1 frame backward | Left | Left | Left |
| 8 | `frame_step_forward` | Step 1 frame forward | Right | Right | Right |
| 9 | `frame_step_back_5` | Step 5 frames backward | Shift+Left | Shift+Left | Shift+Left |
| 10 | `frame_step_forward_5` | Step 5 frames forward | Shift+Right | Shift+Right | Shift+Right |
| 11 | `go_to_start` | Go to sequence start | Home | Home | Home |
| 12 | `go_to_end` | Go to sequence end | End | End | End |
| 13 | `go_to_next_edit` | Go to next edit point | Down | Down / E | A (fast-fwd to) |
| 14 | `go_to_prev_edit` | Go to previous edit point | Up | Up | — |
| 15 | `go_to_next_marker` | Go to next marker | Shift+M | Shift+M | — |
| 16 | `go_to_prev_marker` | Go to previous marker | Cmd+Shift+M | Opt+M | — |
| 17 | `go_to_in` | Go to In point | Shift+I | Shift+I | Q |
| 18 | `go_to_out` | Go to Out point | Shift+O | Shift+O | W |
| 19 | `play_in_to_out` | Play from In to Out | Opt+K | Shift+\ | 6 |
| 20 | `play_around_playhead` | Play around current position | Shift+K | \ | / |
| 21 | `cycle_playback_rate` | Cycle speed (0.5x, 1x, 2x, 4x) | — (CUT-specific) | — | — |
| 22 | `match_frame` | Match frame (source ↔ timeline) | F | F | — |
| 23 | `reverse_match_frame` | Reverse match frame | Shift+R | — | — |

## 2. MARKING & IN/OUT

| # | Action ID | Description | Premiere Mac | FCP7 | Avid MC |
|---|-----------|-------------|-------------|------|---------|
| 24 | `mark_in` | Set In point | I | I | I / E |
| 25 | `mark_out` | Set Out point | O | O | O / R |
| 26 | `clear_in` | Clear In point | Opt+I | Opt+I | D |
| 27 | `clear_out` | Clear Out point | Opt+O | Opt+O | D |
| 28 | `clear_in_out` | Clear both In and Out | Opt+X | Opt+X | G |
| 29 | `mark_clip` | Mark clip under playhead | X | X | T |
| 30 | `mark_selection` | Mark selected range | / | — | — |
| 31 | `add_marker` | Add marker at playhead | M | M | — |
| 32 | `add_marker_dialog` | Add marker + open dialog | MM (double-tap) | Opt+M | — |
| 33 | `add_comment_marker` | Add comment/note marker | Shift+M (CUT) | — | — |

## 3. EDITING OPERATIONS

| # | Action ID | Description | Premiere Mac | FCP7 | Avid MC |
|---|-----------|-------------|-------------|------|---------|
| 34 | `undo` | Undo last action | Cmd+Z | Cmd+Z | Cmd+Z |
| 35 | `redo` | Redo last undone action | Cmd+Shift+Z | Cmd+Shift+Z | Cmd+Shift+Z |
| 36 | `cut` | Cut selection to clipboard | Cmd+X | Cmd+X | Cmd+X |
| 37 | `copy` | Copy selection | Cmd+C | Cmd+C | Cmd+C |
| 38 | `paste` | Paste from clipboard | Cmd+V | Cmd+V | Cmd+V |
| 39 | `paste_attributes` | Paste attributes only | Cmd+Opt+V | Opt+V | — |
| 40 | `delete_clip` | Delete / Clear selected | Delete | Delete | Delete |
| 41 | `ripple_delete` | Ripple delete (close gap) | Opt+Delete | Shift+Delete | — |
| 42 | `select_all` | Select all clips | Cmd+A | Cmd+A | Cmd+A |
| 43 | `deselect_all` | Deselect all | Cmd+Shift+A | Cmd+Shift+A | — |
| 44 | `duplicate` | Duplicate selection | Cmd+Shift+/ | — | — |
| 45 | `find` | Find in project/timeline | Cmd+F | Cmd+F | Cmd+F |

## 4. TRIM & EDIT TYPES

| # | Action ID | Description | Premiere Mac | FCP7 | Avid MC |
|---|-----------|-------------|-------------|------|---------|
| 46 | `insert_edit` | Insert edit from source | , (comma) | F9 | V |
| 47 | `overwrite_edit` | Overwrite edit from source | . (period) | F10 | B |
| 48 | `split_clip` | Add edit / razor at playhead | Cmd+K | Cmd+B / B (razor) | — |
| 49 | `split_all_tracks` | Add edit to all tracks | Cmd+Shift+K | Cmd+Shift+B | — |
| 50 | `lift` | Lift (remove, leave gap) | ; | — | Z |
| 51 | `extract` | Extract (remove, close gap) | ' | — | X |
| 52 | `trim_edit` | Enter trim mode | Shift+T / Cmd+T | — | — |
| 53 | `extend_edit` | Extend edit to playhead | E | E | — |
| 54 | `apply_video_transition` | Apply default video transition | Cmd+D | Cmd+T | — |
| 55 | `apply_audio_transition` | Apply default audio transition | Cmd+Shift+D | Opt+Cmd+T | — |
| 56 | `apply_default_transitions` | Apply transitions to selection | Shift+D | — | — |

## 5. CLIP MANIPULATION

| # | Action ID | Description | Premiere Mac | FCP7 | Avid MC |
|---|-----------|-------------|-------------|------|---------|
| 57 | `nudge_left_1f` | Nudge clip left 1 frame | Opt+, / Cmd+Left | — | , |
| 58 | `nudge_right_1f` | Nudge clip right 1 frame | Opt+. / Cmd+Right | — | . |
| 59 | `nudge_left_5f` | Nudge clip left 5 frames | Shift+Cmd+Left | — | Shift+, |
| 60 | `nudge_right_5f` | Nudge clip right 5 frames | Shift+Cmd+Right | — | Shift+. |
| 61 | `nudge_up_track` | Move clip up 1 track | Opt+Up | — | — |
| 62 | `nudge_down_track` | Move clip down 1 track | Opt+Down | — | — |
| 63 | `slide_left_1f` | Slide clip left 1 frame | Opt+, | Opt+, | — |
| 64 | `slide_right_1f` | Slide clip right 1 frame | Opt+. | Opt+. | — |
| 65 | `slip_left_1f` | Slip clip content left 1 frame | Cmd+Opt+Left | — | — |
| 66 | `slip_right_1f` | Slip clip content right 1 frame | Cmd+Opt+Right | — | — |
| 67 | `speed_duration` | Open speed/duration dialog | Cmd+R | Cmd+J | — |
| 68 | `link_unlink` | Link/Unlink A/V | Cmd+L | Cmd+L | — |
| 69 | `group` | Group clips | Cmd+G | Cmd+G | — |
| 70 | `ungroup` | Ungroup clips | Cmd+Shift+G | Cmd+Shift+G | — |
| 71 | `enable_disable` | Enable/Disable clip | Cmd+Shift+E | — | — |
| 72 | `make_subclip` | Make subclip | Cmd+U | Cmd+U | — |

## 6. TOOLS (mode switches)

| # | Action ID | Description | Premiere Mac | FCP7 | Avid MC |
|---|-----------|-------------|-------------|------|---------|
| 73 | `tool_selection` | Selection / Arrow tool | V | A | — |
| 74 | `tool_track_select_fwd` | Track Select Forward | A | T | — |
| 75 | `tool_track_select_back` | Track Select Backward | Shift+A | TT | — |
| 76 | `tool_ripple` | Ripple Edit tool | B | RR | — |
| 77 | `tool_rolling` | Rolling Edit tool | N | R | — |
| 78 | `tool_rate_stretch` | Rate Stretch tool | R | — | — |
| 79 | `tool_razor` | Razor / Blade tool | C | B | — |
| 80 | `tool_slip` | Slip tool | Y | S | — |
| 81 | `tool_slide` | Slide tool | U | SS | — |
| 82 | `tool_hand` | Hand / scroll tool | H | H | — |
| 83 | `tool_zoom` | Zoom tool | Z | Z | — |
| 84 | `tool_type` | Text / Type tool | T | — | — |

## 7. VIEW & ZOOM

| # | Action ID | Description | Premiere Mac | FCP7 | Avid MC |
|---|-----------|-------------|-------------|------|---------|
| 85 | `zoom_in` | Zoom in timeline | = (plus) | Cmd+= | — |
| 86 | `zoom_out` | Zoom out timeline | - (minus) | Cmd+- | — |
| 87 | `zoom_to_fit` | Zoom to fit sequence | \ (backslash) | Shift+Z | — |
| 88 | `snap_toggle` | Toggle snapping | S | N | — |
| 89 | `maximize_panel` | Maximize/restore panel | ~ (tilde) | — | — |
| 90 | `increase_video_height` | Increase video track height | Cmd+= | Shift+T | — |
| 91 | `decrease_video_height` | Decrease video track height | Cmd+- | Shift+T | — |
| 92 | `increase_audio_height` | Increase audio track height | Opt+= | — | — |
| 93 | `decrease_audio_height` | Decrease audio track height | Opt+- | — | — |

## 8. PANELS & WORKSPACE

| # | Action ID | Description | Premiere Mac | FCP7 | Avid MC |
|---|-----------|-------------|-------------|------|---------|
| 94 | `panel_project` | Focus Project panel | Shift+1 | — | — |
| 95 | `panel_source` | Focus Source monitor | Shift+2 | — | — |
| 96 | `panel_timeline` | Focus Timeline panel | Shift+3 | — | — |
| 97 | `panel_program` | Focus Program monitor | Shift+4 | — | — |
| 98 | `panel_effect_controls` | Focus Effect Controls | Shift+5 | — | — |
| 99 | `panel_effects` | Focus Effects panel | Shift+7 | — | — |

## 9. PROJECT & FILE

| # | Action ID | Description | Premiere Mac | FCP7 | Avid MC |
|---|-----------|-------------|-------------|------|---------|
| 100 | `save` | Save project | Cmd+S | Cmd+S | Cmd+S |
| 101 | `save_as` | Save as... | Cmd+Shift+S | Cmd+Shift+S | — |
| 102 | `import` | Import media | Cmd+I | Cmd+I | — |
| 103 | `export_media` | Export media | Cmd+M | Cmd+E | — |
| 104 | `new_project` | New project | Cmd+Opt+N | — | — |
| 105 | `new_sequence` | New sequence/timeline | Cmd+N | Cmd+N | — |
| 106 | `new_bin` | New bin/folder | Cmd+B | — | — |

## 10. CUT-SPECIFIC (our extensions)

| # | Action ID | Description | Default Key | Category |
|---|-----------|-------------|-------------|----------|
| 107 | `scene_detect` | Run scene detection | Cmd+D | AI Assembly |
| 108 | `montage_suggest` | Show montage suggestions | Cmd+Shift+M (TBD) | AI Assembly |
| 109 | `auto_montage_favorites` | Auto-montage: favorites cut | — | AI Assembly |
| 110 | `auto_montage_script` | Auto-montage: script cut | — | AI Assembly |
| 111 | `auto_montage_music` | Auto-montage: music cut | — | AI Assembly |
| 112 | `toggle_proxy` | Toggle proxy mode | — | Media Pipeline |
| 113 | `toggle_view_mode` | Toggle NLE / Debug view | Cmd+\ | CUT UI |
| 114 | `escape_context` | Cancel / Close popup | Escape | CUT UI |
| 115 | `cycle_playback_rate` | Cycle playback speed | — | CUT Playback |

---

## Architecture Summary

### Total actions: 115

| Category | Count | CUT Status |
|----------|-------|------------|
| Playback & Navigation | 23 | 12 implemented |
| Marking & In/Out | 10 | 5 implemented |
| Editing Operations | 12 | 7 implemented |
| Trim & Edit Types | 11 | 2 implemented (split, transition TBD) |
| Clip Manipulation | 16 | 0 (nudge basics only) |
| Tools (mode switches) | 12 | 0 (no tool mode system yet) |
| View & Zoom | 9 | 3 implemented |
| Panels & Workspace | 6 | 0 (panel system TBD) |
| Project & File | 7 | 2 (import, export) |
| CUT-Specific (AI) | 9 | 3 implemented |

### Implementation priority (what makes a NLE feel professional):

**Tier 1 — Must have (users will leave without these):**
- All Playback (1-20) ← mostly done
- Marking (24-33) ← mostly done
- Core editing: undo/redo, cut/copy/paste, delete, ripple delete
- Split clip (razor at playhead)
- Insert/Overwrite edits
- Snap toggle

**Tier 2 — Expected by pros:**
- Trim (ripple, rolling, extend)
- Nudge (1f, 5f)
- Tool switching (selection, razor, slip, slide)
- Match frame
- Lift / Extract

**Tier 3 — Power user:**
- Slip/Slide
- Track height controls
- Panel focus hotkeys
- Speed/Duration dialog
- Multi-cam switching

**Tier 4 — CUT differentiator (AI layer on top):**
- Scene detect, montage suggestions, auto-montage modes
- Proxy toggle, sync status
- ComfyUI generation pipeline integration (future)
- 3D StorySpace navigation

### Preset import plan:
- **Premiere:** Parse XML keyboard layout (`*.kys` file)
- **FCP7:** Parse plist (`~/Library/Preferences/com.apple.FinalCutPro.plist`)
- **Avid:** Parse `*.avs` settings file
- **DaVinci:** Same as Premiere layout (no separate preset)
- **Custom:** JSON export/import

---

## Source references
- `docs/185_ph_CUT_POLISH/hotcuts/premiere.md` — Adobe helpx full list
- `docs/185_ph_CUT_POLISH/hotcuts/Premiere Pro Keyboard Shortcuts Mac.txt` — Noble Desktop cheat sheet
- `docs/185_ph_CUT_POLISH/hotcuts/finalcut_7_shortcuts.pdf` — FCP7 reference
- `docs/185_ph_CUT_POLISH/hotcuts/avid.pdf` — Avid MC reference
