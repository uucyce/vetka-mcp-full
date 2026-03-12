# MARKER_159_C2_FULLSCREEN_WINDOW_FIX_REPORT_2026-03-06

## Scope
C2 fixes for detached artifact window UX and fullscreen reliability after C1 native open-path rollout.

## Markers
- `MARKER_159.C2.WINDOW_SIZE_DEFAULT`  
  Reduced default detached artifact window size in Tauri `open_artifact_window`.
- `MARKER_159.C2.WINDOW_LABEL_AUTHORITY`  
  Propagated `window_label` from route query into detached `ArtifactPanel` and `VideoArtifactPlayer`.
- `MARKER_159.C2.FULLSCREEN_BUTTON_ROUTING`  
  Fullscreen button now tries a safe label set (`requested`, `artifact-main`, `artifact-media`, `main`) to avoid dead button state.
- `MARKER_159.C2.SETTINGS_ICON_MINIMAL`  
  Replaced text gear with monochrome SVG and larger click target.
- `MARKER_159.C2.FULLSCREEN_LAYOUT_FIXED_INSET`  
  Switched app/standalone top shells from `100vw/100vh` to `position: fixed; inset: 0;` to prevent fullscreen white-gap artifacts.

## Files
- `client/src-tauri/src/commands.rs`
- `client/src/ArtifactStandalone.tsx`
- `client/src/ArtifactMediaStandalone.tsx`
- `client/src/components/artifact/ArtifactPanel.tsx`
- `client/src/components/artifact/viewers/VideoArtifactPlayer.tsx`
- `client/src/App.tsx`

## Tests Added
- `tests/phase159/test_phase159_artifact_window_default_size_contract.py`
- `tests/phase159/test_phase159_artifact_detached_label_routing_contract.py`
- `tests/phase159/test_phase159_video_player_fullscreen_button_contract.py`
- `tests/phase159/test_phase159_fullscreen_layout_fixed_inset_contract.py`

## Expected UAT
1. Detached artifact window opens smaller and does not cover the whole VETKA window.
2. Video fullscreen button in player triggers native fullscreen for current detached window.
3. Green macOS fullscreen and player fullscreen no longer produce white bottom gap.
4. Settings icon is monochrome SVG and visually clearer.

## C2.1 Follow-up (Video Fullscreen UX)
- `MARKER_159.C2.VIDEO_FULLSCREEN_LAYOUT`  
  Detached video viewer removes `maxWidth` cap and extra padding in fullscreen context.
- `MARKER_159.C2.VIDEO_FULLSCREEN_TOOLBAR_HIDE`  
  Artifact bottom toolbar is hidden while video fullscreen is active (detached media mode).
- `MARKER_159.C2.VIDEO_CONTROLS_BOTTOM_ANCHOR`  
  Player controls are hard-anchored to bottom with stronger gradient and smoother fade in fullscreen.
- `MARKER_159.C2.SETTINGS_ICON_RESHAPE`  
  Settings gear SVG redrawn for cleaner center ring geometry.

## C2.2 Fullscreen Stability Patch
- `MARKER_159.C2.WINFS.GET_CURRENT` and `MARKER_159.C2.WINFS.SET_CURRENT`  
  Added current-window fullscreen state/read-set commands in Tauri.
- `MARKER_159.C2.WINFS_ANTI_RACE_LOCK`  
  Added frontend lock and verify-retry cycle in `VideoArtifactPlayer` to prevent intermittent stuck fullscreen toggles after repeated presses.
- `MARKER_159.C2.WINDOW_SIZE_MCC_PARITY`  
  Artifact window default size aligned to MCC baseline: `960x680`.

## C2.3 Micro UX Polish
- `MARKER_159.C2.CONTROL_BAR_DENSITY_TUNE`  
  Reduced bottom control-bar gradient/padding to remove visually stretched dark lower zone.
- `MARKER_159.C2.FULLSCREEN_TRANSITION_BLACK_ROOT`  
  Forced `html/body/#root` black background to reduce short gray flashes during native fullscreen transition animation.

## C2.4 Detached Header/Toolbar Regression Fix
- `MARKER_159.C2.DETACHED_HEADER_ACTIONS_RESTORE`  
  Restored detached-mode top actions in `ArtifactPanel`: `VETKA add` for non-indexed files and `Favorite star` for indexed artifacts/files.
- `MARKER_159.C2.DETACHED_TOOLBAR_COMPACT`  
  Added compact toolbar density for detached media artifacts to reduce oversized lower strip.

## C3 Contract Correction (VETKA/Favorite Logic + Titlebar Placement)
- `MARKER_159.C3.DETACHED_INVETKA_HINT`  
  Added explicit `in_vetka` route contract from main window to detached artifact windows (`open_artifact_window`, `open_artifact_media_window`) to avoid false-negative `isInVetka` when detached store graph is incomplete.
- `MARKER_159.C3.DETACHED_INVETKA_PRIORITY`  
  In detached `ArtifactPanel`, `detachedInitialInVetka` now has priority as source-of-truth; local index writes (`index-file`) still override via `locallyIndexedPath`.
- `MARKER_159.C3.TITLEBAR_ACTIONS_OVERLAY`  
  Removed extra action strip inside artifact content; `VETKA/⭐` controls moved to top overlay aligned with native titlebar row (no dedicated content band).
- `MARKER_159.C3.MEDIA_WINDOW_HINT_PROPAGATION`  
  `openArtifactMediaWindow` now carries `in_vetka` so media detaches preserve the same action logic as non-media artifacts.

### C3 Tests
- `tests/phase159/test_phase159_detached_titlebar_actions_overlay_contract.py`
- `tests/phase159/test_phase159_in_vetka_hint_contract.py`

## C4 Detached Drag/Action Hardening
- `MARKER_159.C4.DETACHED_DRAG_TOPBAR`  
  Added integrated detached topbar in `ArtifactPanel` with `data-tauri-drag-region` to restore reliable mouse-drag window movement.
- `MARKER_159.C4.DETACHED_ACTIONS_RIGHT_DOCK`  
  `⭐/VETKA` actions are now docked to the right inside topbar (near right corner), not rendered as floating fixed strip.
- `MARKER_159.C4.DETACHED_ACTIONS_ENDPOINTS_RECONFIRM`  
  Re-confirmed detached actions still use existing API contracts (`/api/watcher/index-file`, `/api/tree/favorite(s)`, `/api/artifacts/{id}/favorite`) and backend optional CAM sync paths for favorites remain intact.

### C4 Tests
- `tests/phase159/test_phase159_detached_titlebar_actions_overlay_contract.py`
- `tests/phase159/test_phase159_detached_titlebar_actions_fixed_contract.py`
- `tests/phase159/test_phase159_detached_actions_endpoints_contract.py`
