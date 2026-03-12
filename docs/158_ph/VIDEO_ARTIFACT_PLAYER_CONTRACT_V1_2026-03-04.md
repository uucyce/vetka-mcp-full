# VIDEO_ARTIFACT_PLAYER_CONTRACT_V1
**Date:** 2026-03-04  
**Status:** Proposed (ready for implementation)  
**Owner:** PHASE 159 media UX

## 1. Architecture Decision
Use **hybrid split**:
1. Keep shared `ArtifactShell` (title, close, pin to chat, save/download/open-in-finder, metadata container).
2. Move media runtime into dedicated `VideoArtifactPlayer` component.
3. Wire via `ArtifactMediaAdapter` contract (no direct route logic in UI component).

Why:
1. Avoid duplicating core artifact actions.
2. Isolate player complexity (controls, quality, fullscreen, hover UX).
3. Keep migration safe with feature flag.

## 2. Design Policy (non-negotiable)
1. Monochrome only: no accent colors in player controls or overlays.
2. Player-first layout: content area is primary; diagnostics hidden by default.
3. Controls appear on hover/focus; idle auto-hide.
4. No autoplay on file open or file switch.
5. Default playback source is direct system decode (no forced transcode).

## 3. Functional Spec (V1)
### A. Core Playback
1. Play/Pause toggle.
2. Seek slider with draggable playhead.
3. Current time / total duration.
4. Mute toggle + volume slider.
5. Playback speed menu: `0.5x, 1x, 1.25x, 1.5x, 2x, 4x`.
6. Fullscreen toggle.
7. Double-click on video: fullscreen toggle.
8. Space key: play/pause.
9. Left/Right arrows: seek `-5s/+5s`.

### B. Quality / Performance
1. Quality menu in player controls, compact like YouTube settings.
2. V1 quality profiles:
   `Auto`, `Original`, `Preview`.
3. `Auto` = choose best direct source by runtime policy.
4. `Original` = always original file source.
5. `Preview` = preview-derived source when available.
6. Future ladder (queued): `1/2, 1/4, 1/8, 1/16, 1/32`.

### C. Preview Assets
1. Static poster preview (smart frame, avoid near-black).
2. Animated preview 300ms.
3. Hover on file-card shows animated preview; fallback to static poster.
4. If assets unavailable: show neutral placeholder (no color highlights).

### D. UI Behavior
1. Top diagnostic rows hidden by default.
2. `i` button toggles info panel (mime, source strategy, degraded reason).
3. Control bar overlays video bottom edge (semi-transparent dark).
4. On mouse leave + idle 1.5s: hide control bar.
5. On mouse move/focus/keyboard input: show control bar.

### E. Artifact Integration (must keep)
1. Pin to chat context.
2. Download.
3. Open in Finder.
4. Close panel.
5. Preserve file identity and context events (`vetka-open-artifact`).

## 4. API Contract Additions (already aligned)
`POST /api/artifacts/media/preview` must return:
1. `playback.source_url`
2. `playback.strategy`
3. `preview_assets.poster_url`
4. `preview_assets.animated_preview_url_300ms`
5. `duration_sec`

## 5. Explicit Exclusions (V1)
1. No subtitle editor UI.
2. No multicam switcher in player overlay.
3. No color-coded badges.
4. No forced proxy transcode by default.

## 6. Tests Required Before Merge
### Contract tests
1. `video_player_no_autoplay_on_open`
2. `video_player_switch_source_resets_and_updates_media`
3. `video_player_hover_controls_show_hide`
4. `video_player_volume_and_mute_work`
5. `video_player_speed_menu_values`
6. `video_player_quality_menu_values`
7. `video_player_fullscreen_toggle`
8. `video_player_info_toggle`

### Integration tests
1. `artifact_shell_actions_preserved_for_video`
2. `video_card_hover_uses_300ms_preview_or_poster`
3. `video_player_direct_decode_default_policy`

## 7. Open Questions (need user decision)
1. Quality menu labels: keep `Auto/Original/Preview` or use pixel labels (`1080p/720p/...`) in V1?
2. Seek step via keyboard: `5s` or `10s`?
3. Control auto-hide timeout: `1.5s` or `2.5s`?
4. Fullscreen hotkey: enable `F` in addition to button/double-click?
5. Keep `4x` speed in primary row or only in settings menu?
