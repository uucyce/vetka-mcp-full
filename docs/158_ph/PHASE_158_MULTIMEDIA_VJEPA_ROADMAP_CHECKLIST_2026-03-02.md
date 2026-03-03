# PHASE 158 Roadmap + Checklist (Multimedia / V-JEPA / VETKA Final-Cut Track)
**Date:** 2026-03-02
**Updated:** 2026-03-02 (Codex JEPA correction + unified IO matrix)

## CHANGELOG_2026-03-02_Codex
1. Добавлен explicit пункт по `VETKA_UNIFIED_IO_MATRIX_V1.md`.
2. Уточнена роль JEPA: representation/scanning + retrieval/planning, не только prediction.
3. Добавлен anti-freeze контур: `media-mcp` + `media_edit_mode`.
4. Чекбоксы синхронизированы с реально проверенными артефактами в репозитории.
5. Зафиксирован приоритет Premiere XML (без терминологической путаницы).
6. Добавлен R&D трек: `Adobe_Premiere_Pro_MCP` + rhythm/CAM hypothesis.
7. Добавлена детальная спецификация media-mode: `VETKA_MEDIA_MODE_FOLDER_SPEC_V1.md`.
8. Реализован P1 ExtractorRegistry и интеграция в watcher/triple-write/qdrant-updater (+ тесты).
9. Реализован P2: `media_chunks_v1` schema + unified multimodal payload для Qdrant/TripleWrite.
10. Реализован P3 browser-ingest content path + explicit degraded mode (`metadata_only`/fallback reasons).
11. Реализован P4: artifact batch lane wired через `artifact_routes` -> `qdrant_batch_manager.queue_artifact()`.
12. Реализован базовый P5: `POST /api/artifacts/media/preview` + waveform/timeline UI в ArtifactPanel + `Media Edit Mode` пункт в tree context menu.
13. P5 UI-полировка: style-consistent media preview + zoom (`1x/2x/4x`) + playhead + degraded badges в ArtifactPanel.
14. P5.2 partial: `POST /api/artifacts/media/startup` + startup-status banner при входе в `media_edit_mode`.
15. P5.3 partial: guided fallback questions (`missing_inputs` + `fallback_questions`) в `media/startup` + `Ask Jarvis` prefill loop в UI.
16. P5.4 partial: timeline lanes (`video_main`, `audio_sync`, `take_alt_y`) в media chunk contract + lane-aware preview rows в ArtifactPanel.
17. P5.5 partial: semantic links (`hero/action/location/theme`) API + panel in ArtifactPanel on segment click.
18. P5.6 partial: rhythm/music assist API (`/media/rhythm-assist`) + UI panel (cut density, motion volatility, phase markers, bpm hint) + PULSE bridge status.
19. P5.6 update: rhythm overlay track + phase markers visualized directly over timeline lanes in ArtifactPanel.
20. T1 done (tests-first): ingest payload fallback contract (`degraded_mode`/`degraded_reason`) for OCR/STT/meta routes.
21. T2 done (tests-first): canonical `media_chunks_v1` hardening (sorted timeline order, safe numeric coercion, clamped bounds/confidence).
22. T3 done (tests-first): route-level playback metadata contract smoke for preview/semantic-links/rhythm-assist.
23. T4 done (tests-first): optional JEPA/PULSE enrichment hook contract in extractor registry (ok/error/over-budget).
24. T5 done (tests-first, backend): CAM overlay API contract (`/media/cam-overlay`) with uniqueness/memorability tracks + degraded fallback.
25. T5.1 done (real clips): CAM overlay fallback upgraded with `ffmpeg` scene-detect segments + local integration test on Berlin/Kling dataset.
26. T5.2 done (real media matrix): integration tests on Berlin assets across video/photo/script/audio (+ real track preview contract).
27. T6.1 done (tests-first): `POST /api/artifacts/media/transcript-normalized` (Whisper -> normalized JSON) with duration cap + real audio contract test.
28. T7.1 done (tests-first): JSON -> Premiere XML converter service + export endpoint (`/media/export/premiere-xml`) on XMEML v5 lane.
29. T7.2 done (tests-first): JSON -> FCPXML converter service + export endpoint (`/media/export/fcpxml`) as secondary interchange lane.
30. Baseline check done: CinemaFactory `premiere_xml_generator_adobe.py` structural compatibility verified against VETKA Premiere XML lane.

## Goal (Session Success Definition)
1. Импортировать и сканировать мультимедиа в VETKA.
2. Нормализовать media в machine format: `text/tokens/json/xml` (с таймкодами).
3. Отобразить media в UI: waveform audio + video preview/timeline-friendly segments.
4. Воспроизводить media в VETKA artifact flow.

## Step 1. Recheck Big Pickle Reports (docs/158_ph)
- [x] Перепроверить утверждения по коду.
- [x] Исправить устаревшие/неточные статусы.
- [x] Добавить changelog с пометками изменений.
- [x] Добавить external primary-source verification section.

## Step 2. Roadmap + Checklist
- [x] Сформировать этапы P0..P6.
- [x] Определить acceptance criteria для каждого этапа.
- [x] Выделить блок рисков и зависимостей.
- [x] Зафиксировать unified IO contract: `docs/158_ph/VETKA_UNIFIED_IO_MATRIX_V1.md`.

## Step 3. Additional Research Intake (from user)
Подтверждено пользователем:
- [x] `PULSE` reference: `https://github.com/danilagoleen/pulse`.
- [x] Premiere priority: `Premiere XML` (в первую очередь), плюс FCPXML lane.
- [x] Монтажный лист: обязательный export profile VETKA.
- [ ] Ограничения production pipeline: max file size, target codecs, target fps.
- [ ] Зафиксировать финальный schema-файл обязательных полей монтажного листа (`vetka_montage_sheet_v1`).

## Step 4. Recon Codebase with Markers
- [x] Зафиксировать текущие marker-based gaps в docs.
- [~] Добавить новые `MARKER_158.*` в код на реальных точках интеграции (`registry`, `media_edit_mode`, `media-mcp`).  
  `registry` внедрен, `media_edit_mode`/`media-mcp` pending.
- [x] Согласовать единый media contract для ingest/extract/retrieve/render (док-уровень V1).

## Step 5. Tests in `/tests`
- [x] Добавить тесты на watcher multimedia extension-gate.
- [x] Добавить тесты на multimodal ingest payload (OCR/STT/meta fallback).
- [x] Добавить тесты на canonical media chunk schema (`start/end/text/confidence`).
- [x] Добавить smoke-тест на route-level playback metadata contract.

## Step 6. Implementation (TDD, step-by-step)
### P0 (Now)
- [x] Расширить `file_watcher.SUPPORTED_EXTENSIONS` для media.
- [x] Прогнать точечные тесты (`tests/test_phase158_watcher_multimedia_extensions.py`).

### P1
- [x] Вынести extractor registry (`OCR`, `STT`, `summary fallback`) в единый сервис.
- [x] Подключить registry в `watcher/index-file`, `triple-write/reindex`, `qdrant_updater.update_file`.
- [~] Добавить JEPA/PULSE encoder hooks в registry как optional enrichment слой.  
  Внедрен безопасный optional hook framework + latency/error statuses; concrete JEPA/PULSE encoders pending.

### P2
- [x] Ввести canonical media timeline schema (`media_chunks_v1`).
- [x] Обеспечить единый payload в Qdrant/TripleWrite.

### P3
- [x] Добавить browser-ingest content path (где возможно) + ясный degraded mode.

### P4
- [x] Починить или удалить dead path `queue_artifact`.

### P5 (UI montage readiness)
- [x] Backend API: waveform bins + timeline segments + preview ranges (v1: `POST /api/artifacts/media/preview`).
- [~] Frontend: waveform strip, 16:9 preview, zoomable timeline segments.  
  Внедрен waveform/timeline preview + zoom/playhead/degraded badges в ArtifactPanel; advanced timeline UX (multicam lanes/overlays) pending.
- [x] Ввести `media_edit_mode` UI/route policy (без блокировки directed/knowledge mode) — добавлен режим в tree context menu.
- [x] Визуализация ритма: cut-density + motion-volatility overlay на timeline.  
  Добавлен `rhythm-assist` endpoint + UI метрики/phase markers + overlay track на lane timeline.
- [~] CAM-overlay: frame uniqueness/memorability heat track (R&D flag).  
  Backend contract and tests added (`POST /api/artifacts/media/cam-overlay`), including real-video scene-detect fallback (`ffmpeg`) and local dataset integration test; frontend lane overlay integration pending.
- [~] Реализовать `MCP_MEDIA` startup orchestration (analyze phase + progress UI).  
  Добавлен backend startup contract + frontend status banner; full async job/progress streaming pending.
- [~] Реализовать Jarvis guided fallback loop при нехватке metadata/script/sheet.  
  Добавлен `missing_inputs`/`fallback_questions` контракт + UI->chat prefill loop; conversational multi-step assistant loop pending.
- [~] Реализовать scene-node timeline lanes (`video_main`, `audio_sync`, `take_alt_y`).  
  Lane assignment добавлен в `media_chunks_v1`/artifact chunk graph/preview API + lane rows в UI; full scene-node editing lanes + multicam switching pending.
- [~] Подключить semantic links panel (hero/action/location/theme).  
  Добавлен endpoint `POST /api/artifacts/media/semantic-links` + UI panel с `Ask/Seek/Open` поведением; graph-edge overlays и richer entity linking pending.
- [~] Реализовать music-driven edit assists (PULSE + rhythm features).  
  Добавлен `POST /api/artifacts/media/rhythm-assist` + ArtifactPanel rhythm widget + heuristic PULSE bridge status; native PULSE feature extractor integration pending.

### P6 (Export/interchange)
- [x] Whisper transcript to normalized JSON.
- [x] JSON -> Premiere XML converter (production priority).
- [x] JSON -> FCPXML converter (secondary lane).
- [ ] Доисследовать `Adobe_Premiere_Pro_MCP` как reference интеграционного слоя: https://github.com/hetpatel-11/Adobe_Premiere_Pro_MCP
- [x] Проверить как baseline рабочий референс: `/Users/danilagulin/Documents/CinemaFactory/core/premiere_xml_generator_adobe.py` (исторически успешный импорт в Premiere).  
  Проверена структурная совместимость (xmeml v5, project/sequence/clipitem/clipitem-markers); прямой manual import smoke в Premiere GUI остается отдельным ручным шагом.

## Acceptance Criteria
1. Любой media файл проходит ingest и получает semantic payload без silent-drop.
2. Для audio/video сохраняются segment-level timestamps.
3. UI умеет показать waveform + playable preview + duration-aligned segments.
4. Есть regression tests в `/tests`, зеленые на целевых сценариях.

## Risk Log
1. Неконсистентная терминология Premiere XML может ломать импорт при неверном профиле экспорта.
2. STT/OCR latency может блокировать online ingest без async queue policy.
3. FCPXML compatibility зависит от точной версии схемы и требований NLE pipeline.
4. Без отдельного media worker/MCP тяжелые AV задачи могут деградировать весь orchestrator.
5. Неверный UX startup (без видимого прогресса) будет восприниматься как "зависание" при анализе проекта.

## Related Docs
- `docs/158_ph/VETKA_UNIFIED_IO_MATRIX_V1.md`
- `docs/158_ph/VETKA_MEDIA_MODE_FOLDER_SPEC_V1.md`
