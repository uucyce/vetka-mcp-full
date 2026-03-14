# Stage 1 Recon – CinemaFactory Folder Audit

## Scope
Собрал быструю разведку `/Users/danilagulin/Documents/CinemaFactory`, чтобы выявить готовые модули, документы и экспертизу, которые можно прицепить к нашему монтажному пути (`media_edit_mode`, `MCP_MEDIA`, `media_chunks_v1`, `PremiereAdapter`). Зафиксировал только полезные компоненты, без попыток переписывать код.

## Ключевые находки
### 1. Автоматический анализ → монтажный план
- `pipline/complete_analysis_pipeline.py`: восьмиступенчатая последовательность (FFprobe → аудиоклассификатор → Whisper → Apple Vision → OpenCV scene cuts → unified JSON → Claude decisions → OpenTimelineIO инструкции) структурирует именно тот Unified Analysis, который мы описывали в `media/startup` и `vetka_montage_sheet_v1`. Можно переиспользовать шаблон данного pipeline для построения `media_chunks_v1` и `MCP_MEDIA` startup (quick scan + fallback). Используем как reference flowchart и как пример упаковки затратных шагов в один сервис. 
- `core/auto_xml_generator.py` + вариации `create_premiere_xml*.py`: генераторы Premiere XML (XMEML v5) и FCPXML показывают, как переводить анализ (сценарии, сегменты, VO, AI-подсказки) в XML экспорта. Особенно полезны для `PremiereAdapter` (вместо придумывания формата) – наш backend может вызывать эти модули или инкапсулировать их логику.

### 2. Медиа метаданные, OCR & лица
- `core/apple_vision_bridge.py`: натянута связь к Apple Vision (OCR, face tracking, scene change, memory stats). Структура `AppleVisionResult` (ocr_results, face_results, scene_changes) идеально ложится в `media_chunks_v1` (scene_node_id, rhythm_features, cam_features). Можно адаптировать под VETKA diagnostics – feed эти данные в `media_preview`, `semantic_links` и `cam_overlay`.
- `core/whisper_bridge.py`: robust Whisper wrapper с FFmpeg PATH, Apple Silicon оптимизациями и `TranscriptionSegment`. Можно использовать как подход к `media/transcript-normalized` (timestamps/confidence) и как пример fallback (model lookup, failure logs). Полезно вернуть `language_confidence`, `processing_time`, чтобы заполнить `playback_metadata`.

### 3. Timeline/scene/export инфраструктура
- `core/premiere_xml_generator_adobe.py`: production-ready Adobe XML generator (UUID project IDs, asset references, sequence/clip timeline, metadata injection). Логика создания `media/timeline` clipitem/track пригодится для `media/export/premiere-xml` и `media/export/fcpxml` (можно либо refactor, либо вызывать прямо из VETKA `PremiereAdapter`). Есть place-holder `xmeml` structure and timeline building – можно сравнить с `vetka_montage_sheet_v1.records` и использовать подход `clipitem` + `metadata`.
- `create_premiere_xml_REAL.py`, `_FIXED`, `_SIMPLE`: разные реализации показывают progression (от prototyping до production). Стоит взять как test fixtures и regression data при тестировании экспортных маршрутов. Можно интегрировать `tests/test_phase158_premiere_adapter` style tests referencing this output.

### 4. Asset tooling & APNG prep
- `tools/mp4_to_apng_alpha.py` (mirror in VETKA scripts) + `docs/08_MEDIA_PIPELINE/MP4_TO_APNG_ALPHA_TOOL.md`: готовый toolchain для создания RGBA PNG и APNG с режимами `chroma/luma/depth`. Прямо совпадает с нашей `MARKER_167.MEDIA.APNG.TOOLING.V1` требованием. Можно взять параметры (`fps`, `threshold`, `manifest.json`) и использовать как authoritative config for `scripts/media/mp4_to_apng_alpha.py`.

### 5. Knowledge base / orchestration notes
- `docs/02_BACKEND_DEVELOPMENT/grok_research_02_multi_agent_coordination.md` and `/docs/05_RESEARCH_ARCHIVE/grok_research_01…05*`: detailed multi-agent coordination patterns (Orchestrator-Worker, sequential/concurrent/handoff) that можно переупаковать как research для `MCP_MEDIA` orchestration + Jarvis fallback. Документ содержит anti-patterns, monitor tips и circuits (use Claude Sonnet orchestrator, Circuit breakers) – пригодится для построения `media_mcp_job_store`/`media_mcp_job_v1` job orchestration.
- `docs/03_TECHNICAL_RESEARCH/01_ai_ecosystem_map.md` + `cinema_factory_complete_knowledge.md`: roadmap систем (ComfyUI + MCP Bridge + multi-layer providers). Транслируется в VETKA `media_edit_mode` multi-agent pipeline (LLM orchestrator, fallback loops) и может послужить reference для `media-startup` prompts/`fallback_questions`.
- `docs/03_TECHNICAL_RESEARCH/PREMIERE_AUTOMATION_SUMMARY.md`: показывает как настроить ExtendScript/UXP и automation workflows. Можно взять идею Phase roadmap (UXP foundation → core automation → advanced features) для нашего `UAT-FIX` pack + release-runbook (Premiere connectors + pipeline). 

## Что стоит взять в VETKA
1. **Pipeline structure**: Use `CompleteAnalysisPipeline.run_complete_analysis` as blueprint when designing MCP_MEDIA quick scan + fallback (FFprobe → Whisper → Vision → Timeline → AI decision). Expose each step's outputs inside `media_chunks_v1` and `media/startup` response (stats/signals). 
2. **Metadata sources**: Flatten `AppleVisionResult`/`WhisperBridge` dataclasses into `media_chunks_v1` records (ocr text, face boxes, scene types, transcripts). Feed them to `semantic_links`, `cam_overlay`, `rhythm_assist`, and export adapters so they align with the montage sheet schema. 
3. **Export generator**: Adapt `PremiereXMLGenerator` to `PremiereAdapter`, reuse sequences/tracks structure, and keep the `xmeml` builder for timeline-level tests (`tests/phase158` etc). Use the varying `create_premiere_xml_*` outputs as goldens for verifying `PremiereAdapter.export_from_transcript`. 
4. **Tooling**: Incorporate MP4→APNG parameters and manifest into `scripts/media/mp4_to_apng_alpha.py` (already mirrored) to ensure same behavior and telemetry. Document `chroma/luma/depth` modes and dependencies. 
5. **Research guidance**: Map Grok multi-agent patterns to our `MCP_JOB` orchestration (Orchestrator-Worker, fault detectors, fallback). Keep the AI ecosystem map (ComfyUI + providers) as background for `media_mcp_job` job definitions and fallback question scripting. 
6. **Automation playbook**: Use `PREMIERE_AUTOMATION_SUMMARY.md` as a reference for bridging `PremiereAdapter` to Adobe UXP/ExtendScript when we eventually support direct Premiere interactions (embedding ramp-ups).

## Рекомендуемые next steps
1. Добавить `core/premiere_xml_generator_adobe.py` logic к `src/services/premiere_adapter.py` (или использовать как external library) и написать контрактные тесты на экспорт (в документации `docs/158_ph` + `create_premiere_xml_*` outputs). 
2. Переписать `pipline/complete_analysis_pipeline` шаги в новый VETKA service (внутри `media_mcp_job_store`) и возвращать JSON-объекты на каждый этап для frontend banners (`mediaStartup.phases`). 
3. Использовать dataclasses из AppleVision & Whisper bridge как canonical schema для `media_chunks_v1` records (OCR/scene/facial metadata). 
4. Настроить `tools/mp4_to_apng_alpha.py` параметры и документацию в docs (`docs/08_MEDIA_PIPELINE/MP4_TO_APNG_ALPHA_TOOL.md`) как runtime reference for asset pipeline. 
5. Синхронизировать Grok multi-agent patterns и AI ecosystem map с `docs/158_ph/PHASE_159...` orchestration sections — использовать их для training prompts `fallback_questions` + `media_mcp` job steps. 

Отчёт с примечаниями и ссылками помещён сюда: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/169_ph_editmode_recon/Stage1_GPT-5.1-Codex-CinemaFactoryAudit.md`.
