# PHASE 159 Sub-Roadmap: Artifact Native Fullscreen + Multi-Window Media
**Date:** 2026-03-04  
**Status:** Draft for execution (marker-recon ready)  
**Parent:** `docs/158_ph/PHASE_159_MEDIA_ARCHITECTURE_FIRST_ROADMAP_2026-03-03.md`
**Clean-Cut Successor (2026-03-06):** `docs/158_ph/PHASE_159_ARTIFACT_NATIVE_WINDOW_CLEAN_CUT_PLAN_2026-03-06.md`

## Purpose
Не тонуть в точечных UI-фиксах и дебаге fullscreen.  
Идем по рельсам: сначала recon и контракты окна, потом нативный fullscreen, затем отдельное media-window и синхронизация с таймлайном.

## Scope
1. Artifact panel video/audio fullscreen behavior.
2. Native fullscreen in Tauri window layer (не DOM-подмена).
3. Optional detached Artifact Media Window (вынесение за пределы основного окна VETKA).
4. State sync: main window <-> artifact media window.
5. Test gates на каждый шаг.

## Non-Goals (for this sub-roadmap)
1. Монтажный timeline editor.
2. Multicam UX.
3. Subtitle/caption editing UI.
4. Premiere export changes.

---

## Recon Markers Report (current baseline)
### MARKER_159.WINFS.RECON_1 (frontend player runtime)
**File:** `client/src/components/artifact/viewers/VideoArtifactPlayer.tsx`  
Findings:
1. Есть fallback fullscreen overlay (fixed 100vw/100vh), но это не system fullscreen.
2. Кнопка fullscreen зависит от WebView API пути, без гарантии native-переключения окна.
3. Quality UI есть, но нужен hard verification что stream реально сменился (не только label).

### MARKER_159.WINFS.RECON_2 (artifact shell integration)
**File:** `client/src/components/artifact/ArtifactPanel.tsx`  
Findings:
1. Artifact shell уже содержит нужные действия (pin/download/open/close) и должен остаться единым.
2. Плеер можно выделить в отдельный режим окна без потери shell-функций.

### MARKER_159.WINFS.RECON_3 (backend preview/playback contract)
**File:** `src/api/routes/artifact_routes.py`  
Findings:
1. `media/preview` уже возвращает `playback.sources_scale`.
2. Есть база для реального quality ladder (full/half/quarter/eighth/sixteenth).
3. Нужна явная проверка доступности профилей + telemetry на выбор профиля.

### MARKER_159.WINFS.RECON_4 (platform risk)
**Layer:** Tauri/WebView (macOS)  
Findings:
1. DOM fullscreen внутри embedded WebView может давать нестабильный UX.
2. Для production нужно окно-level fullscreen через Tauri window API.

---

## Architecture Decision (target)
1. **Primary fullscreen path:** native window fullscreen (`Tauri window.setFullscreen(true/false)`).
2. **Secondary path:** detached media window (отдельное окно для artifact media).
3. **Last resort fallback:** in-panel overlay fullscreen (только аварийный режим).
4. **Single source of truth:** `ArtifactMediaSessionState` с IPC-синхронизацией.

---

## Execution Rails (step-by-step)
### R0. Contract Freeze (must pass first)
- [x] Freeze `ArtifactMediaWindowContractV1`:
  1. `open_media_window`
  2. `close_media_window`
  3. `toggle_fullscreen`
  4. `set_quality_scale`
  5. `sync_playback_state`
- [x] Freeze `ArtifactMediaSessionStateV1` fields:
  1. `path`
  2. `current_time`
  3. `is_playing`
  4. `volume`
  5. `is_muted`
  6. `quality_scale`
  7. `playback_rate`

**Gate R0 tests**
1. [x] `test_phase159_media_window_contract_schema.py`
2. [x] `test_phase159_media_session_state_schema.py`

### R1. Native Fullscreen (same window, no detach yet)
- [x] Implement window-level fullscreen command in Tauri backend.
- [x] Wire fullscreen button in player to Tauri command first.
- [x] Keep DOM fullscreen only as fallback and mark it degraded.
- [ ] Add visible mode flag in diagnostics (`native_window` | `dom_fallback`).

**Gate R1 tests**
1. [x] `test_phase159_fullscreen_command_contract.py`
2. [x] `test_phase159_video_player_fullscreen_mode_priority.py`

### R2. Detached Artifact Media Window
- [x] Add command to open dedicated media window with artifact payload.
- [x] Ensure window can move outside VETKA root window and across monitors.
- [x] Preserve artifact actions in detached mode (pin/download/open/close).

**Gate R2 tests**
1. [x] `test_phase159_media_window_open_close_contract.py`
2. [x] `test_phase159_artifact_actions_preserved_detached_window.py`

### R3. Playback State Sync (main <-> detached)
- [x] Bidirectional IPC sync for play/pause/seek/volume/quality/rate.
- [x] Leader election policy: active-focused window is authoritative.
- [x] Recover on window close (state back to main panel).

**Gate R3 tests**
1. [x] `test_phase159_media_window_state_sync_contract.py`
2. [x] `test_phase159_media_window_authority_focus_policy.py`

### R4. Real Quality Ladder Verification
- [ ] Add runtime assertion: selected quality maps to real source URL from `sources_scale`.
- [ ] Add telemetry event on quality switch (`from`, `to`, `source_url`).
- [ ] Add optional debug indicator (`FULL/1-2/1-4/...`) in info mode only.

**Gate R4 tests**
1. `test_phase159_quality_scale_uses_real_source.py`
2. `test_phase159_quality_scale_telemetry_contract.py`

### R5. Release Gate (UAT-focused)
- [ ] Scenario S1: fullscreen button always reacts (native preferred).
- [ ] Scenario S2: detached media window stable > 10 open/close cycles.
- [ ] Scenario S3: quality switch visibly changes decode profile on real clips.
- [ ] Scenario S4: no loss of artifact actions and no UI deadlocks.

**Gate R5 tests**
1. `test_phase159_uat_fullscreen_stability_matrix.py`
2. `test_phase159_uat_detached_window_regression.py`

---

## Risk Register
1. **Tauri platform variance:** fullscreen API behavior differs by OS/window manager.
2. **State divergence:** two windows controlling one media session without strict authority policy.
3. **Performance pressure:** quality variant generation latency on first open.
4. **UX regressions:** losing artifact shell actions in detached mode.

## Mitigations
1. Native-first fullscreen + explicit fallback status.
2. Single `ArtifactMediaSessionState` contract + focus-authority rule.
3. Prebuild/cached `sources_scale` variants with timeout and degraded mode.
4. Contract tests for shell actions in both modes.

---

## Definition of Done (for this sub-roadmap)
1. Fullscreen button produces predictable fullscreen behavior (native path first).
2. Detached artifact media window works as first-class mode.
3. Quality ladder confirmed as real stream switch, not label-only.
4. User can keep watching media outside main VETKA window without losing artifact workflow.

## Change Log
1. 2026-03-04: Initial marker-recon sub-roadmap created.
