# PHASE 159 Test Matrix (Function-by-Function)
**Date:** 2026-03-04  
**Goal:** точечные проверки функциональности без ручного UI-шумового тестирования.

## UAT-FIX-1 Playback + Waveform
1. `playback_contract_mime_m4a`  
   Test: `tests/phase159/test_media_playback_contract.py::test_phase159_normalize_media_mime_for_m4a`
2. `playback_contract_raw_serves_audio`  
   Test: `tests/phase159/test_media_playback_contract.py::test_phase159_get_raw_file_uses_normalized_media_type`
3. `preview_waveform_non_wav`  
   Test: `tests/test_artifact_api_approve_reject.py::test_media_preview_uses_ffmpeg_waveform_for_non_wav_audio`
4. `preview_waveform_wav`  
   Test: `tests/test_artifact_api_approve_reject.py::test_media_preview_returns_waveform_for_wav`
5. `raw_audio_stream_decodable_e2e`  
   Test: `tests/phase159/test_media_stream_playback_e2e.py::test_phase159_raw_audio_stream_is_decodable`
6. `raw_video_stream_decodable_e2e`  
   Test: `tests/phase159/test_media_stream_playback_e2e.py::test_phase159_raw_video_stream_is_decodable`
7. `media_toolbar_contract_hide_text_actions`  
   Test: `tests/phase159/test_artifact_media_toolbar_contract.py::test_phase159_media_toolbar_hides_text_edit_actions`
8. `media_src_contract_raw_stream_priority`  
   Test: `tests/phase159/test_artifact_media_toolbar_contract.py::test_phase159_media_artifact_uses_raw_stream_not_base64`
9. `video_fastplay_generation_budget`  
   Test: `tests/phase159/test_media_video_fastplay_contract.py::test_phase159_fastplay_asset_generation_budget`
10. `video_preview_fastplay_payload_contract`  
   Test: `tests/phase159/test_media_video_fastplay_contract.py::test_phase159_media_preview_returns_video_fastplay_payload`
11. `video_panel_timeupdate_throttle_contract`  
   Test: `tests/phase159/test_artifact_video_performance_contract.py::test_phase159_artifact_video_timeupdate_is_throttled`
12. `video_panel_fullscreen_and_poster_contract`  
   Test: `tests/phase159/test_artifact_video_performance_contract.py::test_phase159_artifact_video_has_fullscreen_and_poster`
13. `media_info_toggle_noise_gate_contract`
   Test: `tests/phase159/test_artifact_media_info_toggle_contract.py::test_phase159_media_info_toggle_exists_and_controls_noise`
14. `media_ui_monochrome_key_surfaces_contract`
   Test: `tests/phase159/test_media_monochrome_contract.py::test_phase159_artifact_media_css_is_monochrome_on_key_surfaces`

## UAT-FIX-2 Media Search/Discovery
1. `search_mdfind_fallback`  
   Test: `tests/phase159/test_file_search_media_discovery.py::test_phase159_file_search_falls_back_when_mdfind_misses`
2. `search_media_filename_hit`  
   Test: `tests/phase159/test_file_search_media_discovery.py::test_phase159_file_search_supports_media_extension_hits`

## UAT-FIX-4 Copy Policy (VETKA naming)
1. `startup_prefill_copy_no_jarvis`  
   Test: `tests/test_artifact_api_approve_reject.py::test_media_startup_collects_scope_stats`
   Assert: fallback prefill strings contain `VETKA` and do not contain `Jarvis`.

## UAT-FIX-3 Media Card Rendering
1. `filecard_media_category_16_9_contract`
   Test: `tests/phase159/test_filecard_media_contract.py::test_phase159_filecard_supports_media_category_and_16_9_shape`
2. `filecard_media_audio_m4a_binary_gate`
   Test: `tests/phase159/test_filecard_media_contract.py::test_phase159_filecard_treats_m4a_as_binary_non_previewable`
3. `filecard_media_play_triangle_overlay`
   Test: `tests/phase159/test_filecard_media_contract.py::test_phase159_filecard_media_draws_play_triangle`

## L0 Contract Freeze
1. `media_mcp_job_schema_valid_done`  
   Test: `tests/phase159/test_media_mcp_job_schema.py::test_phase159_media_mcp_job_schema_accepts_valid_done_payload`
2. `media_mcp_job_schema_state_guard`  
   Test: `tests/phase159/test_media_mcp_job_schema.py::test_phase159_media_mcp_job_schema_rejects_invalid_state`
3. `media_mcp_job_schema_error_requires_error_obj`  
   Test: `tests/phase159/test_media_mcp_job_schema.py::test_phase159_media_mcp_job_schema_requires_error_for_error_state`

## L2 Sub-MCP Orchestration
1. `media_startup_async_job_lifecycle`
   Test: `tests/phase159/test_media_mcp_async_startup.py::test_phase159_media_startup_async_job_lifecycle`
2. `media_startup_async_unknown_job_404`
   Test: `tests/phase159/test_media_mcp_async_startup.py::test_phase159_media_startup_async_unknown_job_returns_404`

## Browser DOM Probe
1. `browser_dom_current_time_advances`  
   Test: `tests/phase159/test_media_dom_playback_probe.py::test_phase159_dom_playback_probe_advances_current_time`  
   Script: `scripts/media_dom_playback_probe.sh`  
   Run mode: opt-in (`VETKA_E2E_BROWSER=1`) to keep default smoke fast/stable.

## Planned: VideoArtifactPlayer V1
1. `video_player_no_autoplay_on_open`  
   Test: `tests/phase159/test_video_artifact_player_contract.py::test_phase159_video_player_has_core_controls_and_no_autoplay`
2. `video_player_switch_source_resets_and_updates_media`  
   Test: `tests/phase159/test_video_artifact_player_contract.py::test_phase159_video_player_resets_on_source_switch`
3. `video_player_speed_menu_values + quality_menu_values`  
   Test: `tests/phase159/test_video_artifact_player_contract.py::test_phase159_video_player_has_quality_menu_and_speed_menu`
4. `video_player_quality_menu_switches_real_source`  
   Test: `tests/phase159/test_artifact_media_toolbar_contract.py::test_phase159_media_artifact_uses_raw_stream_not_base64`
5. `video_player_hover_controls_show_hide`
6. `video_player_volume_and_mute_work`
7. `video_player_fullscreen_toggle`
8. `video_player_info_toggle`
9. `artifact_shell_actions_preserved_for_video`
10. `video_card_hover_uses_300ms_preview_or_poster`

## One-command smoke pack
```bash
pytest -q \
  tests/phase159/test_media_stream_playback_e2e.py \
  tests/phase159/test_artifact_media_toolbar_contract.py \
  tests/phase159/test_artifact_video_performance_contract.py \
  tests/phase159/test_artifact_media_info_toggle_contract.py \
  tests/phase159/test_media_monochrome_contract.py \
  tests/phase159/test_media_video_fastplay_contract.py \
  tests/phase159/test_filecard_media_contract.py \
  tests/phase159/test_media_playback_contract.py \
  tests/phase159/test_file_search_media_discovery.py \
  tests/phase159/test_media_mcp_async_startup.py \
  tests/phase159/test_media_mcp_job_schema.py \
  tests/phase159/test_media_dom_playback_probe.py \
  tests/test_artifact_api_approve_reject.py
```
