# V-JEPA + Multimedia Import Qdrant Recon
**Created:** 2026-03-02  
**Updated:** 2026-03-02 (Codex re-verify + JEPA role correction)

## CHANGELOG_2026-03-02_Codex
1. Исправлены устаревшие выводы по мультимедиа: OCR/AV-пути уже частично работают в `watcher_routes.py`, `embedding_pipeline.py`, `triple_write_routes.py`.
2. Переклассифицированы гэпы: часть `RED` стала `PARTIAL` (F2/F3/F5/F6), `F1` и `F7` остаются критичными.
3. Добавлен блок внешней верификации по первоисточникам (V-JEPA/I-JEPA/Whisper/ffprobe/FCP XML).
4. Явно зафиксирован research-gap по `PULSE` (неоднозначный термин, не удалось однозначно связать с video ingest стеком по первичным источникам).
5. Исправлена формулировка роли JEPA: это не только "predict overlay", а полноценный representation/scanning слой для multimodal retrieval/ranking/planning.
6. Добавлена локальная верификация `transformers` VJEPA2 интеграции (`modeling_vjepa2.py`, `configuration_vjepa2.py`, `auto/video_processing_auto.py`).
7. Добавлен архитектурный блок anti-freeze: отдельный media MCP + отдельный folder mode для монтажного режима.

## 1. V-JEPA Status (Code + Docs Recheck)

### 1.1 Что подтверждено в коде
1. Hybrid trigger-политика контекст-пакера присутствует: pressure/docs/entropy/modality + hysteresis (`src/orchestration/context_packer.py`).
2. JEPA-путь реально условный и деградирует в fallback без hard-fail (`src/services/mcc_jepa_adapter.py`, `src/services/jepa_runtime.py`).
3. Контракт для architect JEPA context существует и связан с marker-историей 155C (`docs/contracts/JEPA_ARCHITECT_CONTEXT_CONTRACT_V1.md`).

### 1.2 Актуальный вывод
- Для VETKA chat pipeline JEPA уже внедрен как conditional слой, а не mandatory.
- Для мультимедиа ingestion JEPA не заменяет STT/OCR/parsers, но усиливает ingest как слой semantic representation:
  - cross-modal retrieval (video/audio/image/text),
  - scene-level clustering и ranking,
  - candidate dependency edges для DAG (с confidence),
  - planning hints для монтажа и ассистентов.

## 1.3 JEPA Scope Correction (важно)

Предыдущее сужение "JEPA только для предсказаний" некорректно. По первоисточникам и коду:
1. JEPA-family (I-JEPA / V-JEPA2 / VL-JEPA) учит абстрактные представления через prediction-in-latent-space, и эти представления применяются не только для forecast, но и для understanding/retrieval/alignment.
2. V-JEPA2 заявляет motion understanding + anticipation + planning use-cases; это напрямую релевантно VETKA media scanning.
3. Практически для VETKA: JEPA = semantic encoder над таймкодными сегментами, а Whisper/OCR = extractors фактов/текста. Нужны оба слоя одновременно.

## 1.4 Локальная проверка VJEPA2 в окружении проекта

Проверено в `venv_voice`:
1. `transformers/models/vjepa2/modeling_vjepa2.py`:
   - есть `VJEPA2WithMaskedInputPredictorOutput`,
   - 3D patch/tubelet embeddings для видео,
   - full model stack encoder+predictor.
2. `transformers/models/vjepa2/configuration_vjepa2.py`:
   - `VJEPA2Config` с `frames_per_clip`, `tubelet_size`, `pred_*` параметрами.
3. `transformers/models/auto/video_processing_auto.py`:
   - `("vjepa2", "VJEPA2VideoProcessor")` в auto mapping.

Вывод: в текущем окружении VJEPA2 трактуется как полноценный video model + video processor, а не абстрактная "заглушка".

## 2. Multimedia + Qdrant: Re-verified State (важно)

### 2.1 Что уже есть (было недооценено в исходном отчете)
1. `POST /api/watcher/index-file` уже имеет:
- OCR route для `pdf/image`;
- AV transcription route через WhisperSTT для `audio/video`;
- fallback summary при неудаче extraction.
2. `embedding_pipeline._process_single()` уже делает:
- OCR extraction для image/pdf;
- transcript extraction + `media_chunks` для audio/video;
- `modality` и extraction metadata в payload.
3. `POST /api/triple-write/reindex` уже поддерживает multimodal, но только при `req.multimodal=true`.

### 2.2 Что реально остается gap
1. `file_watcher.SUPPORTED_EXTENSIONS` уже расширен для media в текущей ветке (раньше был ключевой gap, теперь закрыт regression test'ом).
2. Browser ingest в `add-from-browser` в основном metadata/content_small, без полноценного file-content extraction pipeline.
3. `QdrantIncrementalUpdater.update_file()` для binary path читает текстом и в fallback дает пустой контент (не использует OCR/STT ветки).
4. Artifact batch lane (`qdrant_batch_manager.queue_artifact()`) уже wired через `artifact_routes` bridge в текущей ветке; нужен только regression guard.

## 3. Current Matrix (после перепроверки)

| Type | Watcher index-file | Embedding pipeline | Triple-write reindex | Final state |
|------|---------------------|--------------------|----------------------|-------------|
| text/code | ✅ | ✅ | ✅ | ✅ Stable |
| image/pdf | ✅ OCR (partial) | ✅ OCR | ⚠️ only with `multimodal=true` | ⚠️ Partial |
| audio/video | ✅ STT (partial) | ✅ STT/chunks (partial) | ⚠️ only with `multimodal=true` | ⚠️ Partial |
| browser-import media | ⚠️ metadata/content_small | n/a | n/a | 🔴 Gap |
| artifact batch lane | n/a | n/a | n/a | 🔴 Gap (dead path) |

## 4. Primary Sources Verified (external)

1. V-JEPA base paper (arXiv 2404.08471): feature prediction without text/reconstruction/labels; frozen-backbone transfer.
2. I-JEPA (arXiv 2301.08243): JEPA family baseline and non-generative predictive principle.
3. Official V-JEPA codebase (`facebookresearch/jepa`) и V-JEPA2 (`facebookresearch/vjepa2`) — confirms practical training/eval assumptions.
4. Whisper official code (`openai/whisper`):
- returns `text + segments + language`;
- supports `--word_timestamps`;
- supports output formats `txt/vtt/srt/tsv/json/all`.
5. ffprobe official docs: machine-readable output in JSON/XML; отдельный раздел про timecode.
6. Apple Final Cut Pro XML interchange docs (DTD/import/export reference) как базовый ориентир для XML-интеграции.

### Links
1. https://arxiv.org/abs/2404.08471
2. https://arxiv.org/abs/2506.09985
3. https://arxiv.org/abs/2301.08243
4. https://github.com/facebookresearch/jepa
5. https://github.com/facebookresearch/vjepa2
6. https://raw.githubusercontent.com/openai/whisper/main/README.md
7. https://raw.githubusercontent.com/openai/whisper/main/whisper/transcribe.py
8. https://ffmpeg.org/ffprobe-all.html
9. https://leopard-adc.pepas.com/documentation/AppleApplications/Reference/FinalCutPro_XML/DTD/DTD.html
10. https://swan-swan.ru/services/dialogovie-i-montazhnie-listi/#p00

## 5. PULSE Clarification (research gap)

Термин `PULSE` неоднозначен (есть несколько несвязанных проектов с этим именем).  
По первичным источникам в этой проверке не удалось однозначно идентифицировать именно тот `PULSE`, который должен входить в VETKA multimedia ingest stack.  

**Action:** нужен точный референс от проекта (paper/repo/link на целевой PULSE), иначе риск неверной архитектурной развилки.

Текущий подтвержденный рабочий референс от команды:
- `https://github.com/danilagoleen/pulse` (ваш проект) — можно использовать как "audio ears" для VETKA, но для интеграции нужен отдельный контракт между PULSE-feature-space и VETKA scene/timeline contracts.

## 6. Big Pickle Evaluation (подвопрос)

### Что Big Pickle сделал полезно
1. Правильно зафиксировал исторические pain points (extension gate, browser ingest quality, dead artifact path).
2. Дал практичный narrow V1 фокус на ingest wiring.

### Где ошибся/устарел
1. Несколько статусов уже устарели: OCR/AV пути теперь частично реализованы.
2. Некоторые формулировки слишком “RED”, где по коду уже “PARTIAL”.
3. Line refs/детали местами неточны.

### Вердикт по использованию Big Pickle
- Можно использовать как **черновой recon-ускоритель**.
- Нельзя использовать как финальный source-of-truth без обязательной code re-verify pass.

Practical policy:
1. Big Pickle делает draft report.
2. Codex/ручной проход делает source-check + code-check.
3. Только после этого документ получает `Updated: ... (re-verify)` статус.

## 7. Immediate Next Step (для этой сессии)
1. Закрыть F1 (watcher extension gate) через тесты + код.
2. Стабилизировать multimodal default policy (`triple-write` + incremental updater bridge).
3. Нормализовать единый media contract: `tokens/json/xml` + timecode segments + modality metadata.
4. Ввести `MEDIA_EDIT_MODE` + отдельный `media-mcp` процесс, чтобы тяжелые OCR/STT/preview задачи не блокировали основной orchestrator.
5. Зафиксировать единый `VETKA_UNIFIED_IO_MATRIX_V1.md` как основной канонический язык IO.
