# VETKA_UNIFIED_IO_MATRIX_V1
**Created:** 2026-03-02  
**Status:** draft-for-implementation  
**Owner:** VETKA core + PULSE bridge

## CHANGELOG_2026-03-02_Codex
1. Сведены в один контракт идеи `input_matrix_idea.txt` + `MARKER_155_INPUT_MATRIX_SCANNER_CONTRACT.md`.
2. Добавлен bridge: музыкальная матрица (`scale/genre/VST`) <-> сценарная матрица (`scene rhythm/genre/beat`).
3. Зафиксирован JSON-first canonical язык для моделей/ассистентов + export adapters в XML семейства (Premiere XML/FCPXML).
4. Добавлен anti-freeze runtime профиль: отдельный `media-mcp` и отдельный folder mode для монтажа.
5. Зафиксированы implementation markers и test checklist.
6. Зафиксирован приоритет Premiere XML (user-validated import path), без терминологической путаницы.
7. Добавлена гипотеза rhythm-bridge: склейки/внутрикадровое движение как ритм монтажа + CAM метрика уникальности/запоминаемости.

---

## 1) Цель
Унифицировать input/output для любых типов материалов (код, текст, аудио, видео, изображения, сценарии, монтажные листы), чтобы:
1. ingest/scanning были стабильны и воспроизводимы;
2. LLM/JEPA/PULSE работали на одном каноническом языке;
3. VETKA могла строить scene-DAG, timeline и interchange (FCPXML/Premiere XML) без потери таймкодов.

---

## 2) Canonical Language: JSON-first

### 2.1 Почему JSON-first
1. Нативен для LLM пайплайнов и API.
2. Легко валидируется (JSON Schema / pydantic).
3. Подходит как промежуточный слой перед экспортом в XML-диалекты монтажек.

### 2.2 XML роль
1. XML (FCPXML/Premiere XML/другие) не отменяется.
2. XML в VETKA = interchange/export adapters от canonical JSON.
3. Это снижает зависимость ядра от конкретной монтажки.

---

## 3) Unified Entity Model (V1)

```json
{
  "asset_id": "uuid",
  "asset_type": "code|document|script|image|audio|video|timeline|scene_sheet",
  "source_path": "string",
  "mime_type": "string",
  "modality": "text|image|audio|video|mixed",
  "created_at": "iso8601",
  "updated_at": "iso8601",
  "content": {
    "text": "optional extracted text",
    "segments": [
      {
        "segment_id": "uuid",
        "start_sec": 0.0,
        "end_sec": 0.0,
        "text": "segment transcript/ocr caption",
        "confidence": 0.0,
        "speaker": "optional",
        "frame_ref": "optional"
      }
    ]
  },
  "scene_binding": {
    "scene_id": "optional",
    "beat_id": "optional",
    "treatment_node_id": "optional"
  },
  "music_binding": {
    "genre": "optional",
    "rhythm_bpm": "optional",
    "scale": "optional",
    "vst_profile": "optional"
  },
  "links": [
    {
      "source": "asset_or_segment_id",
      "target": "asset_or_segment_id",
      "channel": "structural|semantic|temporal|reference|contextual",
      "weight": 0.0,
      "confidence": 0.0,
      "evidence": ["..."]
    }
  ]
}
```

---

## 4) Input Matrix (универсальная)

### 4.1 Принцип
Любой тип имеет input/output.  
Связь A->B существует, если выполняется хотя бы один путь:
1. structural import/reference;
2. temporal precedence + semantic similarity;
3. explicit citation/link/timecode overlap.

### 4.2 Pair weights (из MARKER_155 логики)
`PAIR_WEIGHTS[(source_type, target_type)]` управляет вкладом каналов:
1. `structural`
2. `semantic`
3. `temporal`
4. `reference`
5. `contextual`

### 4.3 Formula
`score = sigmoid(sum(w_i * channel_i))`  
С циклическими зависимостями: в SCC evidence, а не прямой acyclic edge.

---

## 5) Scene-DAG + Treatment Layer

1. Базовая DAG-сущность в кино-контуре: `scene`.
2. Архитектурный план: `treatment` (уровень выше сцен, задает причинно-смысловую ось).
3. Scene-DAG получает ребра из:
   - script scanner (сцены/персонажи/локации),
   - timeline scanner (таймкоды и переходы),
   - media extractors (Whisper/OCR),
   - JEPA semantic edges.

Y-ось knowledge mode:
`Y = f(time_created, knowledge_level, treatment_depth)`.

---

## 6) Music <-> Scene Bridge (PULSE)

Цель: свести музыкальную матрицу и сценарную матрицу через ритм/жанр сцены.

V1 поля маппинга:
1. `scene.genre`
2. `scene.rhythm_bpm_range`
3. `scene.energy_curve`
4. `music.scale`
5. `music.vst_profile`

Правило:
1. PULSE дает audio/texture признаки и музыкальные кандидаты.
2. VETKA проверяет совместимость с scene/treatment constraints.
3. Результат фиксируется как `music_binding` на scene или segment.

### 6.1 Rhythm Hypothesis (R&D)
1. Ритм склеек и внутрикадрового движения = монтажный ритм сцены.
2. Монтажный ритм сцены связывается с музыкальным ритмом даже при отсутствии явной музыки.
3. Метрики кандидаты:
   - cut density (склейки/сек),
   - motion vector volatility (резкая смена внутрикадрового движения),
   - shot duration variance.
4. CAM добавляется как дополнительный сигнал:
   - frame uniqueness,
   - memorability proxy.
5. Статус: гипотеза, требуются эксперименты и тесты.

---

## 7) Extractor Registry (единый)

Единый реестр экстракторов для всех точек входа:
1. watcher `/index-file`
2. triple-write `/reindex`
3. incremental updater
4. browser ingest

Базовый контракт:
1. `extract(path, mime, options) -> ExtractionResult`
2. `ExtractionResult` содержит `text`, `segments`, `metadata`, `errors`, `extractor_id`, `latency_ms`.

Extractors V1:
1. `text_reader`
2. `ocr_processor` (pdf/image)
3. `whisper_stt` (audio/video transcript)
4. `jepa_encoder` (semantic embeddings/segment descriptors)
5. `pulse_audio_encoder` (music/audio features)

---

## 8) Anti-Freeze Architecture (обязательно)

### 8.1 Проблема
OCR/STT/video-preview тяжелые операции могут подвешивать основной цикл.

### 8.2 Решение V1
1. Отдельный `media-mcp` процесс (или worker pool) для тяжелых media задач.
2. Новый folder mode: `media_edit_mode` (дополнительно к `directed` и `knowledge`).
3. Очереди:
   - `ingest_queue` (high throughput),
   - `preview_queue` (interactive low latency),
   - `export_queue` (batch).
4. Budgets:
   - hard timeout per extractor,
   - backpressure limits,
   - graceful degradation на metadata-only summary.

### 8.3 UI/Data Contract For Visualization (не откладываем)
1. Audio waveform:
   - `waveform_bins`: массив нормализованных амплитуд,
   - `sample_rate`,
   - `duration_sec`.
2. Video timeline preview:
   - `video_segments`: `start_sec`, `end_sec`, `thumb_ref`, `shot_id`,
   - `preview_aspect`: `16:9`.
3. Rhythm overlays:
   - `cut_density_track`,
   - `motion_volatility_track`,
   - `cam_uniqueness_track` (R&D).
4. Montage UX:
   - zoomable scale,
   - scrub playback,
   - selectable segment->scene binding.

---

## 9) Interchange Targets

Primary canonical: JSON.  
Export adapters:
1. `json -> FCPXML` (Final Cut)
2. `json -> Premiere XML` (Adobe Premiere Pro import lane; user-validated on real samples)
3. `json -> internal timeline sheet` (VETKA montage sheet)

CinemaFactory reference confirms practical generators exist (`create_premiere_xml*.py`, `core/premiere_xml_generator_adobe.py`, `core/auto_xml_generator.py`) and can be reused as adapter prototypes, but VETKA core should remain JSON-first.

---

## 10) Implementation Markers (V1)

1. `MARKER_158.UNIFIED_IO.CANONICAL_JSON_V1`
2. `MARKER_158.UNIFIED_IO.EXTRACTOR_REGISTRY_V1`
3. `MARKER_158.UNIFIED_IO.SCENE_DAG_BRIDGE_V1`
4. `MARKER_158.UNIFIED_IO.MUSIC_SCENE_BIND_V1`
5. `MARKER_158.UNIFIED_IO.MEDIA_EDIT_MODE_V1`
6. `MARKER_158.UNIFIED_IO.MEDIA_MCP_V1`
7. `MARKER_158.UNIFIED_IO.XML_ADAPTERS_V1`

Implementation status (current branch):
1. `MARKER_158.INGEST.MEDIA_EXTRACTOR_REGISTRY` implemented in `src/scanners/extractor_registry.py`.
2. `MARKER_158.QDRANT.SCHEMA_MEDIA_CHUNKS_V1` implemented via `normalize_media_chunks()` + unified payload builders in `src/scanners/multimodal_contracts.py`.

---

## 11) Test Checklist (to /tests)

1. `test_unified_io_registry_routes.py`  
   Проверка одинакового extractor поведения для watcher/reindex/updater.
2. `test_unified_io_media_chunk_schema.py`  
   Валидация `segments` и таймкодов.
3. `test_unified_io_scene_dag_bridge.py`  
   Проверка edge generation (temporal+semantic+reference).
4. `test_unified_io_music_scene_binding.py`  
   Проверка маппинга rhythm/genre/scale/vst.
5. `test_unified_io_media_mode_backpressure.py`  
   Проверка очередей и graceful degradation.
6. `test_unified_io_xml_adapters_smoke.py`  
   Smoke export JSON->FCPXML/Premiere XML.
7. `test_unified_io_rhythm_bridge_cam_hypothesis.py`  
   Проверка `cut_density`, `motion_volatility`, `frame_uniqueness` и их связи со сценой.

---

## 12) Locked Decisions (from user)

1. `PULSE` source-of-truth: `https://github.com/danilagoleen/pulse` (audio/music ear layer for VETKA).
2. Premiere interchange priority: `Premiere XML` (практически проверяемый импортный путь), плюс FCPXML lane.
3. Монтажный лист = обязательный VETKA export profile.

---

## 13) Primary Sources Re-verified

External:
1. V-JEPA paper: https://arxiv.org/abs/2404.08471
2. V-JEPA2 paper (improved video understanding): https://arxiv.org/abs/2506.09985
3. I-JEPA paper: https://arxiv.org/abs/2301.08243
4. Whisper README/CLI outputs: https://raw.githubusercontent.com/openai/whisper/main/README.md
5. ffprobe machine-readable metadata/timecode docs: https://ffmpeg.org/ffprobe-all.html
6. Монтажные/диалоговые листы (формат полей в отраслевой практике): https://swan-swan.ru/services/dialogovie-i-montazhnie-listi/#p00

Local:
1. `src/scanners/multimodal_contracts.py`
2. `src/scanners/mime_policy.py`
3. `src/scanners/file_watcher.py`
4. `src/api/routes/watcher_routes.py`
5. `src/api/routes/triple_write_routes.py`
6. `src/scanners/embedding_pipeline.py`
7. `src/scanners/qdrant_updater.py`
8. `venv_voice/lib/python3.11/site-packages/transformers/models/vjepa2/modeling_vjepa2.py`
9. `venv_voice/lib/python3.11/site-packages/transformers/models/vjepa2/configuration_vjepa2.py`
10. `venv_voice/lib/python3.11/site-packages/transformers/models/auto/video_processing_auto.py`
11. `/Users/danilagulin/Documents/CinemaFactory/core/premiere_xml_generator_adobe.py`
12. `/Users/danilagulin/Documents/CinemaFactory/core/auto_xml_generator.py`

Note:
Локальный PDF `Монтажный лист для Госфильмофонда (образец).pdf` не был автоматически распознан в текст в текущем окружении (нет системного PDF text extractor), поэтому его точные поля нужно подтвердить отдельным парсером/ручной сверкой.
XML reference note from user:
`/Users/danilagulin/Documents/CinemaFactory/core/premiere_xml_generator_adobe.py` считается рабочим референсом с успешными импортами в Premiere; при возвращении к этапу P6 его нужно прогнать повторно как baseline.

---

## 14) Related Spec

Детальная UX/runtime спецификация media режима вынесена в:
`docs/158_ph/VETKA_MEDIA_MODE_FOLDER_SPEC_V1.md`
