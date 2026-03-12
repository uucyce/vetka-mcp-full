# PHASE 159 Clean-Cut Plan: Artifact as Native Tauri Window
**Date:** 2026-03-06  
**Status:** Execution-ready plan (recon-based)  
**Scope:** Remove mixed/legacy fullscreen paths and make Artifact a true native window path.

## Intent
Сделать артефакт отдельным окном Tauri (как MCC), чтобы:
1. окно можно было увести за пределы главного окна VETKA;
2. fullscreen работал нативно и независимо;
3. не было ложного fullscreen внутри embedded `react-rnd` слоя.

## Decision Freeze (architecture)
### D1. Primary model
1. `ArtifactWindow` becomes **native Tauri window first-class path**.
2. Embedded floating artifact remains only as temporary compatibility mode during migration.

### D2. Fullscreen model
1. Fullscreen only at **native window layer** (`set_fullscreen` on artifact window label).
2. DOM fullscreen inside embedded artifact is removed from production path.

### D3. Window strategy
1. **Phase A (safe):** media-first native window mandatory; text/code optional.
2. **Phase B (final):** all artifact types open in native window by default.

---

## Recon Snapshot (why clean-cut needed)
### MARKER_159.CLEAN.RECON_1
`ArtifactWindow` is still embedded via `FloatingWindow` (`react-rnd`) in main app tree.  
Ref: `client/src/App.tsx`, `client/src/components/artifact/FloatingWindow.tsx`.

### MARKER_159.CLEAN.RECON_2
Detached media window code exists, but it is a side path (`onDetach`) not the default artifact open path.  
Ref: `client/src/components/artifact/ArtifactPanel.tsx`, `client/src/components/artifact/Toolbar.tsx`.

### MARKER_159.CLEAN.RECON_3
Fullscreen behavior is still ambiguous for users because embedded path remains visible and active.

---

## Clean-Cut Execution Rails
## C0 Contract Freeze (must pass first)
- [x] Freeze `ArtifactWindowRoutingV1`:
  1. `open_artifact_window(payload)`
  2. `close_artifact_window(label)`
  3. `focus_artifact_window(label)`
  4. `set_artifact_fullscreen(label, enabled)`
- [x] Freeze label policy:
  1. `artifact-main` (generic)
  2. `artifact-media` (media-specific during transition)
- [x] Freeze window payload schema:
  1. `path`
  2. `name`
  3. `extension`
  4. `artifact_id`
  5. `initial_seek_sec`
  6. `content_mode` (`file|raw|web`)

Gate tests:
1. [x] `tests/phase159/test_phase159_artifact_window_routing_contract.py`
2. [x] `tests/phase159/test_phase159_artifact_window_payload_schema.py`

## C1 Open-Path Refactor (no fullscreen changes yet)
- [ ] Replace default `setIsArtifactOpen(true)` flows with `open_artifact_window` invoke path in Tauri runtime.
- [ ] Keep embedded `ArtifactWindow` only as browser-mode fallback and guarded dev fallback.
- [ ] Add clear runtime telemetry marker on open path:
  1. `opened_via=native_window|embedded_fallback`.

Remove/cleanup:
1. Stop treating embedded as default for Tauri.
2. Keep compatibility wrapper only under explicit fallback condition.

Gate tests:
1. `tests/phase159/test_phase159_artifact_open_path_prefers_native_tauri.py`
2. `tests/phase159/test_phase159_embedded_artifact_fallback_guard.py`

## C2 Media Window Consolidation
- [ ] Merge `artifact-media` side path into unified artifact window controller (no duplicate open logic).
- [ ] Keep media viewer contract intact (playback, quality, waveform, preview assets).
- [ ] Preserve existing artifact actions: pin/download/open-in-finder/close.

Transfer-in-place (must not break):
1. `ArtifactPanel` media logic.
2. `VideoArtifactPlayer` controls and state sync contracts.
3. Toolbar actions and semantics.

Gate tests:
1. `tests/phase159/test_phase159_media_actions_preserved_after_open_path_refactor.py`
2. `tests/phase159/test_phase159_media_payload_roundtrip_native_window.py`

## C3 Fullscreen Clean Cut
- [ ] Route fullscreen button exclusively to native artifact window label.
- [ ] Remove production dependency on DOM fullscreen for Tauri path.
- [ ] Keep DOM fullscreen only for browser fallback mode.

Remove/cleanup:
1. Remove mixed fullscreen branching that silently stays in embedded path for Tauri.
2. Remove stale fallback flags from Tauri-only branches.

Gate tests:
1. `tests/phase159/test_phase159_fullscreen_tauri_window_only_for_native_path.py`
2. `tests/phase159/test_phase159_no_dom_fullscreen_on_tauri_native_path.py`

## C4 Window Lifecycle and Multi-Monitor
- [ ] Ensure artifact window can:
  1. open on secondary monitor,
  2. keep independent z-order/focus,
  3. survive main window movement.
- [ ] Add explicit focus/fly-back command for user recall.

Gate tests:
1. `tests/phase159/test_phase159_artifact_window_lifecycle_contract.py`
2. `tests/phase159/test_phase159_artifact_window_focus_recall_contract.py`

## C5 State Sync Stabilization
- [ ] Keep R3 sync model (`play/pause/seek/volume/quality/rate`) with focus authority.
- [ ] Add deterministic close handoff:
  1. on native artifact close, commit latest session state to main store.

Gate tests:
1. `tests/phase159/test_phase159_native_close_state_handoff.py`
2. `tests/phase159/test_phase159_focus_authority_no_state_echo_loops.py`

## C6 Expand to Text/Code (optional toggle -> default)
- [ ] Add feature flag:
  1. `ARTIFACT_NATIVE_WINDOW_ALL_TYPES` (initially off)
- [ ] Enable text/code native window mode under flag.
- [ ] Validate performance and open latency.

Gate tests:
1. `tests/phase159/test_phase159_text_code_native_window_flag_contract.py`
2. `tests/phase159/test_phase159_text_code_open_latency_budget.py`

## C7 Legacy Cleanup (final cut)
- [ ] Remove deprecated embedded-default branches.
- [ ] Remove dead commands/unused UI controls created during transitional debugging.
- [ ] Keep one explicit fallback path for browser mode only.

Remove candidates (after migration verified):
1. embedded artifact open toggles in Tauri path,
2. duplicated detach-only controls no longer needed,
3. stale fullscreen fallback code in Tauri branch.

Gate tests:
1. `tests/phase159/test_phase159_no_legacy_embedded_default_for_tauri.py`
2. `tests/phase159/test_phase159_cleanup_no_orphan_window_commands.py`

## C8 UAT Release Gate
- [ ] Scenario U1: open artifact, drag window outside VETKA main window.
- [ ] Scenario U2: fullscreen works and occupies native screen space.
- [ ] Scenario U3: second monitor behavior stable.
- [ ] Scenario U4: close/reopen keeps state and actions intact.
- [ ] Scenario U5: no regressions in pin/download/open-in-finder.

Gate tests:
1. `tests/phase159/test_phase159_uat_native_artifact_window_matrix.py`
2. `tests/phase159/test_phase159_uat_fullscreen_multi_monitor_regression.py`

---

## Code Map (what to remove / write / move)
### Remove or downgrade to fallback-only
1. Embedded-first open flow in app-level artifact toggles (Tauri runtime path).
2. Tauri fullscreen branches that target `main` for media playback UX.
3. Duplicate detach UI logic once native-open is default.

### Write
1. Unified artifact window controller in Tauri commands + typed frontend gateway.
2. Artifact open dispatcher in app layer (single source of truth).
3. Runtime diagnostics panel field: `artifact_window_mode`.

### Move/keep intact
1. `ArtifactPanel` rendering and toolbar behavior.
2. `VideoArtifactPlayer` media controls and quality ladder UI.
3. Session sync contracts from R3.

---

## Risk Register
1. Window orchestration race (open/focus/fullscreen order).
2. State divergence if both embedded and native paths run simultaneously.
3. User confusion during transition if both buttons remain visible.

Mitigations:
1. Single dispatcher and strict mode flag.
2. Force one active artifact presentation mode in Tauri.
3. Short transition window + visible mode indicator.

---

## Definition of Done
1. В Tauri artifact opens as native window by default (media first, then all types by flag plan).
2. Fullscreen is native-window fullscreen only.
3. User can move artifact window independently (including other monitor).
4. Legacy embedded-default path removed from Tauri runtime.
5. Phase159 test gates green for C0..C8 relevant steps.

## Change Log
1. 2026-03-06: Initial clean-cut migration plan created from Phase159 recon and user UAT feedback.
