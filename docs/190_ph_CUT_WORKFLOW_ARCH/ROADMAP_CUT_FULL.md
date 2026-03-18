# CUT Full Roadmap
# От текущего состояния до рабочего продукта

**Date:** 2026-03-18
**Basis:** CUT_TARGET_ARCHITECTURE.md, CUT_DATA_MODEL.md, RECON_v1_vs_CODE.md, RECON_UI_CLEANUP.md
**Audience:** Любой агент (включая Ollama 8B). Каждый таск самодостаточный.
**Status:** DRAFT v2 — UI cleanup integrated

### Обязательные ссылки для КАЖДОГО таска

Любой таск, связанный с CUT, ДОЛЖЕН ссылаться на эти документы:

| Документ | Зачем |
|----------|-------|
| `docs/190_ph_CUT_WORKFLOW_ARCH/CUT_TARGET_ARCHITECTURE.md` | Архитектура: Source/Program, DAG spine, layout, phases |
| `docs/185_ph_CUT_POLISH/CUT_NLE_UNIVERSAL_ACTION_REGISTRY.md` | 115 NLE actions, hotkeys, tool modes (Premiere/FCP7/Avid) |
| `docs/190_ph_CUT_WORKFLOW_ARCH/RECON_UI_CLEANUP.md` | Что удалить, что перестроить, mapping code→actions |
| `docs/190_ph_CUT_WORKFLOW_ARCH/CUT_DATA_MODEL.md` | Node/Edge types для DAG |
| `docs/190_ph_CUT_WORKFLOW_ARCH/ROADMAP_CUT_FULL.md` | Этот файл — общий план |

---

## 0. ТЕКУЩЕЕ СОСТОЯНИЕ КОДОВОЙ БАЗЫ

### Frontend (client/src/components/cut/) — 22 файла, ~8500 строк

| Файл | Строк | Что делает | Статус |
|------|-------|-----------|--------|
| TimelineTrackView.tsx | 1687 | Timeline: треки, клипы, drag, trim, ruler, playhead | Работает |
| CutEditorLayout.tsx | 799 | Старый layout (legacy, до V2) | МУСОР? |
| CutEditorLayoutV2.tsx | 276 | Текущий layout: 6 dock positions | Работает |
| TransportBar.tsx | 671 | Play/pause, export кнопки | Работает |
| ProjectPanel.tsx | 585 | Media bin: список файлов проекта, импорт | Работает |
| SourceBrowser.tsx | 540 | Legacy media browser | МУСОР? |
| StorySpace3D.tsx | 482 | Camelot + McKee 3D визуализация | Работает |
| PanelShell.tsx | 376 | Dock/float/mini framework для панелей | Работает |
| VideoPreview.tsx | 343 | HTML5 video player + timecode | Работает |
| ScriptPanel.tsx | 332 | Script Y-time display + teleprompter | Работает |
| PulseInspector.tsx | 329 | PULSE metadata display (Camelot+McKee) | Работает |
| DAGProjectPanel.tsx | 320 | ReactFlow DAG (кластерные колонки) | Работает, но Y-ось неверная |
| BPMTrack.tsx | 320 | Canvas: 4 ряда BPM точек | Работает |
| CamelotWheel.tsx | ~300 | SVG 2D Camelot wheel для Inspector | Работает |
| ClipInspector.tsx | ~270 | Per-clip metadata display | Работает |
| WaveformCanvas.tsx | ~200 | Waveform отрисовка для треков | Работает |
| AudioLevelMeter.tsx | ~150 | VU meter полоска на video | Работает |
| TranscriptOverlay.tsx | ~100 | Субтитры поверх видео | Работает |
| TimelineTabBar.tsx | ~100 | Табы таймлайнов: [cut-00][cut-01][+] | Работает |
| icons/CutIcons.tsx | ~800 | 80+ SVG иконок | Работает |
| nodes/MarkerNode.tsx | ~80 | ReactFlow кастомная нода для маркеров | Работает |

### Zustand Stores — 3 файла для CUT

| Store | Строк | Что делает |
|-------|-------|-----------|
| useCutEditorStore.ts | 353 | Master state: playback, timeline, clips, markers, zoom |
| usePanelSyncStore.ts | 176 | Матрица синхронизации 7 панелей |
| usePanelLayoutStore.ts | ~200 | Layout dock/tab/float state |

### Backend Python — 22 файла, ~16000 строк

| Файл | Строк | Что делает | Тесты |
|------|-------|-----------|-------|
| cut_routes.py | 7818 | ВСЕ CUT API эндпоинты (монолит) | — |
| cut_project_store.py | 1231 | Project state: JSON store, scene graph | — |
| pulse_cinema_matrix.py | 704 | 26 cinema scales (Camelot-кино связь) | Есть |
| pulse_auto_montage.py | 669 | 3 режима авто-монтажа | Есть |
| pulse_story_space.py | 615 | McKee triangle + Camelot + trajectory | Есть |
| pulse_energy_critics.py | 481 | 5 критиков энергии | Есть |
| pulse_conductor.py | 457 | Оркестратор PULSE анализа | Есть |
| pulse_timeline_bridge.py | 387 | PULSE → Timeline конвертация | Есть |
| cut_triple_write.py | 344 | Тройная запись (JSON+digest+event) | Есть |
| cut_montage_ranker.py | 326 | Ранжирование клипов для авто-монтажа | — |
| pulse_camelot_engine.py | 320 | Camelot wheel engine (12 ключей) | Есть |
| cut_proxy_worker.py | 318 | FFmpeg proxy generation | — |
| cut_undo_redo.py | 304 | Undo/redo command stack | — |
| pulse_script_analyzer.py | 286 | Scene heading detection (INT./EXT.) | Есть |
| cut_scene_detector.py | 281 | FFmpeg scene boundary detection | Есть |
| pulse_srt_bridge.py | 271 | SRT ↔ PULSE conversion | Есть |
| cut_audio_intel_eval.py | 230 | Audio sync detection | — |
| cut_timeline_events.py | 206 | WebSocket timeline events | — |
| cut_marker_bundle_service.py | 193 | Marker bundles / slices | — |
| cut_ffmpeg_audio_sync.py | 191 | FFmpeg audio sync offset | — |
| cut_ffmpeg_waveform.py | ~150 | FFmpeg waveform extraction | — |
| cut_scene_graph_taxonomy.py | ~100 | Scene graph node/edge types | — |
| cut_mcp_job_store.py | ~100 | Async job queue for MCP | — |

### Export — работает

| Формат | Файл | Статус |
|--------|------|--------|
| Premiere XML (XMEML v5) | converters/premiere_xml_converter.py | Работает |
| FCPXML v1.10 | converters/fcpxml_converter.py | Работает |
| EDL | В cut_routes.py | Работает |
| SRT | pulse_srt_bridge.py | Работает |

---

## PHASE 0: UI CLEANUP — расчистка площадки
**Цель:** Удалить мусор, убрать дублирование, подготовить layout под правильную архитектуру.
**Можно делать ПАРАЛЛЕЛЬНО с Phase 1** (не зависят друг от друга).
**Ссылка:** `RECON_UI_CLEANUP.md` §2, §3

### 0.1 Удалить legacy файлы
- **CutEditorLayout.tsx** (799 строк) — legacy layout, заменён CutEditorLayoutV2
  - Проверить: `grep -r "CutEditorLayout" client/src/` (НЕ CutEditorLayoutV2)
  - Если не импортируется нигде → удалить файл
- **SourceBrowser.tsx** (540 строк) — legacy media browser, заменён ProjectPanel
  - Проверить: `grep -r "SourceBrowser" client/src/`
  - Если не импортируется → удалить файл

### 0.2 Убрать дублирующий Program Monitor
- **Где:** `CutEditorLayoutV2.tsx` строки 97-104
- **Сейчас:** `renderRightTop()` рендерит ещё один Program Monitor
- **Нужно:** right_top НЕ нужен как отдельная зона. Убрать center, оставить:
  - left_top = Source Monitor
  - right_top = Program Monitor (ОДИН)
  - left_bottom = Project Panel
  - right_bottom = Inspector tabs (Inspector / Script / DAG)
  - bottom = Timeline
- **Или:** right_top → Program Monitor, center → убрать из layout

### 0.3 TransportBar → разделить на MonitorTransport + TimelineToolbar
- **Сейчас:** TransportBar.tsx (671 строк) — монолит с Play/IN/OUT/Scenes/Export/Speed
- **Нужно:**
  1. **MonitorTransport.tsx** (~150 строк) — рендерится ПОД video в каждом мониторе:
     - Scrubber bar (мини-таймлайн клипа)
     - Timecode display
     - Transport кнопки: |◄ ◄ ▶ ► ►| (маленькие, компактные)
     - Source Monitor: + IN/OUT кнопки
     - Program Monitor: + timeline position
  2. **TimelineToolbar.tsx** (~50 строк) — МИНИМАЛЬНЫЙ, над треками:
     - Snap toggle (🧲, hotkey S)
     - Zoom slider (горизонтальный)
     - Linked selection toggle (🔗)
     - Ничего больше. Можно встроить в TimelineTabBar.
- **Удалить из toolbar:** кнопка "Scenes" (ножницы), export кнопки, speed display, IN/OUT поля

### 0.4 StorySpace 3D — убрать с таймлайна
- **Сейчас:** Floating поверх правой части таймлайна, мешает видеть треки
- **Нужно:** Mini-panel в углу Program Monitor (как задумано в архитектуре)
- **Или:** Tab в Inspector area (Inspector / Script / DAG / StorySpace)
- **Файлы:** `CutEditorLayoutV2.tsx` (storySpacePanel), `StorySpace3D.tsx`

### 0.5 Чистка кнопок Timeline area
- **Удалить:**
  - Кнопка "Scenes" (✂) — scene detection = Cmd+D (Registry #107), НЕ кнопка
  - Grid icon — непонятное назначение
  - Лишние zoom кнопки — zoom = slider + hotkeys +/-
  - Export кнопки — перенести в меню
- **Оставить:**
  - Tab bar: [Main] [cut-01] [cut-02] [+]
  - Snap toggle (магнит)
  - Zoom slider

---

## 1. КРИТИЧЕСКИЕ ДЕФЕКТЫ (исправить до новых фич)

### BUG-1: Source и Program Monitor показывают одно и то же видео
- **Где:** `CutEditorLayoutV2.tsx` строки 70-103
- **Проблема:** Оба рендерят `<VideoPreview />` без props. VideoPreview берёт `activeMediaPath` из useCutEditorStore. Нет разделения source feed vs program feed.
- **Спек:** "Source and Program NEVER show the same feed" (§3.1)
- **Как чинить:**
  1. Добавить в useCutEditorStore поле `sourceMediaPath` (отдельно от `activeMediaPath`)
  2. VideoPreview принимает prop `feed: 'source' | 'program'`
  3. `feed='source'` → читает `sourceMediaPath` (raw clip из DAG/bin)
  4. `feed='program'` → читает `activeMediaPath` (timeline playback)
  5. В CutEditorLayoutV2: Source Monitor передаёт `feed="source"`, Program Monitor — `feed="program"`
- **Файлы:** `VideoPreview.tsx`, `useCutEditorStore.ts`, `CutEditorLayoutV2.tsx`

### BUG-2: DAG Y-ось = кластерные колонки, а не хрон фильма
- **Где:** `DAGProjectPanel.tsx`
- **Проблема:** Ноды раскладываются по кластерам (Character | Location | Take | Music...). Y-ось абстрактная.
- **Спек:** "Y = film chronology, bottom=START, top=END. Script Spine = center." (§2.2)
- **Как чинить:** см. Phase 2 ниже (требует Scene Chunks → DAG nodes)

---

## PHASE 1: SCRIPT SPINE — фундамент всего
**Цель:** Script text → структурированные scene chunks с хрон-привязкой.
**Без этого:** Ничего дальше не работает. DAG, routing, auto-montage — всё зависит от scene chunks.

### 1.1 screenplay_timing.py — Screenplay-aware chunker + page-timer
- **Что:** Новый файл `src/services/screenplay_timing.py` (~150-200 строк)
- **Вход:** plain text (или результат Fountain/FDX парсинга)
- **Выход:** список `SceneChunk` объектов
- **Алгоритм:**
  1. Взять `pulse_script_analyzer.py` — он уже ищет scene headings (INT./EXT./ИНТ./НАТ.)
  2. Если нашёл scene headings → split по ним (hard scene boundaries)
  3. Если не нашёл → fallback: split по пустым строкам (абзацы)
  4. Для каждого chunk считаем timing:
     - 55 строк = 1 страница ИЛИ ~1800 символов = 1 страница
     - 1 страница = 60 секунд
     - `start_sec = cumulative_pages * 60`
  5. Каждый chunk → `{chunk_id: "SCN_01", scene_heading, start_sec, duration_sec, text}`
- **Dataclass:**
```python
@dataclass
class SceneChunk:
    chunk_id: str           # "SCN_01", "SCN_02", ...
    scene_heading: str | None  # "INT. CAFE - DAY" или None
    chunk_type: str         # "scene" | "paragraph"
    text: str
    start_sec: float
    duration_sec: float
    line_start: int         # первая строка в исходном тексте
    line_end: int           # последняя строка
    page_count: float       # сколько страниц занимает (для timing)
```
- **Зависимости:** `pulse_script_analyzer.py` (scene heading regex — уже работает)
- **Тесты:**
  - Тест с screenplay (INT. CAFE - DAY → scene chunks)
  - Тест с документалкой (без scene headings → paragraph chunks)
  - Тест timing: 55 строк = 60 сек

### 1.2 API endpoint: POST /api/cut/script/parse
- **Что:** Эндпоинт в `cut_routes.py`
- **Вход:** `{text: string}` или `{file_path: string}` или file upload (.fountain, .fdx, .txt, .pdf, .docx)
- **Выход:** `{chunks: SceneChunk[], total_duration_sec, page_count}`
- **Для каждого формата:**
  - `.txt`, plain text → прямой парсинг screenplay_timing.py
  - `.fountain` → парсер fountain → plain text → screenplay_timing.py
  - `.fdx` → парсер XML (Final Draft теги `<Scene>`) → plain text → screenplay_timing.py
  - `.pdf` → OCR (уже есть ocr_processor.py) → text → screenplay_timing.py
  - `.docx` → pandoc → text → screenplay_timing.py
- **Файлы:** `cut_routes.py` (новый endpoint), `screenplay_timing.py`
- **MVP:** только plain text. Fountain/FDX/PDF/DOCX = Phase 2.

### 1.3 ScriptPanel: отображение scene chunks как кликабельных блоков
- **Что:** Обновить `ScriptPanel.tsx`
- **Сейчас:** Строки с timecodes, линейный расчёт 4 сек/строку
- **Нужно:**
  1. Вместо строк — блоки (каждый chunk = визуальный блок с border/background)
  2. Scene heading = жирный заголовок блока
  3. Timecode = из chunk.start_sec (не линейный расчёт)
  4. Click на блок → `usePanelSyncStore.syncFromScript(chunk.line_start, chunk.chunk_id, chunk.start_sec)`
  5. Автоскролл по playhead (teleprompter — уже работает, нужно привязать к chunk boundaries)
- **Файлы:** `ScriptPanel.tsx`
- **Данные:** GET /api/cut/script/chunks/{project_id} → возвращает SceneChunk[]

---

## PHASE 2: DAG SPINE — сценарий как ось графа
**Цель:** Scene chunks становятся нодами DAG. Y-ось = хрон фильма.
**Зависит от:** Phase 1 (chunks существуют)

### 2.1 Backend: scene chunks → project DAG nodes
- **Что:** При парсинге скрипта — создать scene nodes в project_store
- **Где:** `cut_project_store.py`
- **Алгоритм:**
  1. При вызове POST /api/cut/script/parse → каждый SceneChunk → нода в DAG проекта
  2. Node type = "scene_chunk" (добавить в `cut_scene_graph_taxonomy.py`)
  3. Edges: `SCN_01 → SCN_02 → SCN_03` (edge type = "next_scene")
  4. Каждая scene node хранит: chunk_id, scene_heading, start_sec, duration_sec, text
- **Файлы:** `cut_project_store.py`, `cut_scene_graph_taxonomy.py`, `cut_routes.py`

### 2.2 Frontend: DAG Y-ось = хрон, Script Spine = центр
- **Что:** Переписать layout алгоритм в `DAGProjectPanel.tsx`
- **Сейчас:** Кластерные колонки по X, Y абстрактная
- **Нужно:**
  1. Y-ось = film chronology. Bottom = START (SCN_01), top = END (SCN_XX)
  2. Script Spine = центральная вертикальная цепочка SCN_XX нод
  3. Медиа ноды: ВИДЕО слева от SCN, АУДИО справа от SCN
  4. Lore ноды: ниже каждого SCN (персонажи, локации)
  5. ReactFlow layout: `dagre` или custom с фиксированной X-позицией для spine
- **Layout формула:**
```
SCN node X = viewport_width / 2  (центр)
SCN node Y = chunk.start_sec * pixels_per_sec  (хрон)
Video node X = center - offset  (левее)
Audio node X = center + offset  (правее)
```
- **Файлы:** `DAGProjectPanel.tsx`
- **Кнопка Flip Y:** меняет направление (START top ↔ START bottom). Чистый view option.

### 2.3 Bidirectional sync: Script ↔ DAG
- **Что:** Click на script chunk → DAG подсвечивает SCN node + linked media. Click на SCN node в DAG → ScriptPanel скроллит к этому chunk.
- **Где:** `usePanelSyncStore.ts`
- **Сейчас:** `syncFromScript` обновляет `activeSceneId`, `syncFromDAG` обновляет `selectedAssetPath`
- **Нужно:**
  1. ScriptPanel подписывается на `activeSceneId` от DAG → автоскролл
  2. DAGProjectPanel подписывается на `activeSceneId` от Script → highlight node + connected
  3. Blue glow для linked nodes уже работает (MARKER_180.16) — нужно связать с scene_id
- **Файлы:** `ScriptPanel.tsx`, `DAGProjectPanel.tsx`, `usePanelSyncStore.ts`

---

## PHASE 3: SOURCE/PROGRAM ROUTING
**Цель:** Source Monitor ≠ Program Monitor. Полная изоляция feeds.
**Зависит от:** Phase 2 (DAG nodes существуют, клики на них → routing)

### 3.1 Store: sourceMediaPath + programMediaPath
- **Что:** Разделить один `activeMediaPath` на два
- **Где:** `useCutEditorStore.ts`
- **Добавить:**
```typescript
sourceMediaPath: string | null;    // raw clip из DAG/bin клика
programMediaPath: string | null;   // timeline playback
setSourceMedia: (path: string | null) => void;
setProgramMedia: (path: string | null) => void;
```
- **Routing table (из §3.2):**
  - Timeline playback → `programMediaPath` обновляется
  - Click clip в DAG/Project → `sourceMediaPath` обновляется
  - Double-click clip → `sourceMediaPath` + load for IN/OUT
  - Playhead moves on timeline → `programMediaPath` обновляется
  - Click script line → `programMediaPath` jumps + `sourceMediaPath` shows linked raw

### 3.2 VideoPreview: prop feed
- **Что:** VideoPreview принимает `feed: 'source' | 'program'`
- **Где:** `VideoPreview.tsx`
- **Логика:**
  - `feed='source'` → подписка на `sourceMediaPath`
  - `feed='program'` → подписка на `programMediaPath`
  - Остальное без изменений (play/pause, timecode, error overlay)

### 3.3 Layout: правильное подключение
- **Что:** CutEditorLayoutV2 передаёт `feed` prop
- **Где:** `CutEditorLayoutV2.tsx`
- **Source Monitor (left_top):** `<VideoPreview feed="source" />`
- **Program Monitor (center + right_top):** `<VideoPreview feed="program" />`

### 3.4 MonitorTransport: transport controls под каждым монитором
- **Что:** Каждый монитор (Source и Program) получает свой transport
- **Компонент:** `MonitorTransport.tsx` (создан в Phase 0.3)
- **Source Monitor transport:**
```
[scrubber]
TC: 00:01:23:15   DUR: 00:04:10   Fit▼
|◄  ◄  ▶  ►  ►|   [I] [O]   1/2▼
```
- **Program Monitor transport:**
```
[scrubber — привязан к timeline playhead]
TC: 00:02:37:21   DUR: 00:04:10   Fit▼
|◄  ◄  ▶  ►  ►|
```
- **JKL shuttle:** Работает на АКТИВНОМ мониторе (последний кликнутый)
- **Файлы:** `MonitorTransport.tsx`, `CutEditorLayoutV2.tsx`

### 3.5 DAG/Project click → Source Monitor
- **Что:** При клике на ноду в DAG или клипе в ProjectPanel — Source Monitor показывает этот ассет
- **Где:** `DAGProjectPanel.tsx`, `ProjectPanel.tsx`
- **syncFromDAG:** вызывает `setSourceMedia(assetPath)` (не program!)

---

## PHASE 4: PARALLEL TIMELINES
**Цель:** 2 таймлайна видны одновременно (stacked, не табы)
**Зависит от:** Phase 3 (routing работает)

### 4.1 Timeline stacked view
- **Что:** Два TimelineTrackView рендерятся одновременно (один над другим)
- **Где:** `CutEditorLayoutV2.tsx` (секция bottom)
- **Сейчас:** TimelineTabBar + один TimelineTrackView
- **Нужно:**
  1. Состояние: `parallelTimelineId: string | null` в useCutEditorStore
  2. Если `parallelTimelineId !== null` → рендерить 2 TimelineTrackView
  3. Верхний = reference (read-only, dimmed). Нижний = active (full controls)
  4. Playhead синхронизирован между обоими
  5. Click на верхний timeline → он становится active (swap)
- **UI:**
```
┌────────────────────────────────┐
│ TIMELINE 2 (reference): cut-01 │  ← dimmed, read-only
│ ░░░░│░░░░░│░░░│░░░░░│░░░░│░░░ │
├────────────────────────────────┤
│ TIMELINE 1 (active ★): cut-02  │  ← full controls
│ ▓▓▓│▓▓▓▓▓│▓▓│▓▓▓▓▓│▓▓▓▓│▓▓  │
└────────────────────────────────┘
```

### 4.2 Timeline versioning
- **Что:** Связать timeline tabs с DAG versioning
- **Сейчас:** `createVersionedTimeline()` в useCutEditorStore создаёт новые табы
- **Нужно:**
  1. Каждый tab = `{project}_cut-{NN}` (уже реализовано)
  2. RULE: Auto-montage ALWAYS creates new cut-NN, NEVER overwrites (уже в store)
  3. Drag tab в parallel slot → виден одновременно с active
- **Файлы:** `TimelineTabBar.tsx`, `useCutEditorStore.ts`

---

## PHASE 5: AUTO-MONTAGE UI
**Цель:** Frontend для 3 режимов auto-montage (backend 100% готов)
**Зависит от:** Phase 4 (результат = новый tab в Timeline)

### 5.1 Montage menu / кнопки
- **Что:** UI для запуска auto-montage
- **Где:** Новый компонент `AutoMontagePanel.tsx` или кнопки в TransportBar
- **3 режима:**
  1. **Favorites Cut** — монтаж из clips с positive markers
  2. **Script Cut** — монтаж по сценарию (script chunks → best takes per scene)
  3. **Music Cut** — монтаж по BPM музыкального трека
- **Для каждого:** POST /api/cut/montage/assemble → новый timeline → новый tab
- **Backend:** `pulse_auto_montage.py` (669 строк, уже работает)

### 5.2 Progress indicator
- **Что:** Показать прогресс auto-montage
- **MVP:** Progress bar в TransportBar area
- **Future:** Пульсирующие ноды в DAG (Phase 7+)

### 5.3 Reverse dependency: click scene → show alternatives
- **Что:** При клике на сцену в timeline — показать альтернативные takes из DAG
- **Где:** Inspector area или popup
- **Данные:** Scene node → все linked MediaNodes → ranked by PULSE score
- **Backend:** `cut_montage_ranker.py` (326 строк, уже работает)

---

## PHASE 6: MARKERS & IN/OUT
**Цель:** Полная система маркеров + three-point editing

### 6.0 useHotkeys.ts — центральный регистр ВСЕХ горячих клавиш
- **Что:** Единственный файл, где определены ВСЕ hotkey bindings
- **Файл:** `client/src/hooks/useHotkeys.ts` (~300 строк)
- **Архитектура:**
  1. Map: `Action ID → handler function`
  2. Map: `Key combo → Action ID` (из Registry, preset = "premiere_mac")
  3. Context-aware: фокус на Source Monitor → playback управляет source. Фокус на Timeline → editing commands.
  4. Presets: Premiere (default), FCP7, Avid, Custom
- **Tier 1 hotkeys (MVP):**
  - Playback: Space, J/K/L, JJ/LL, Left/Right, Shift+Left/Right, Home/End, Up/Down
  - Marking: I, O, Opt+I, Opt+O, Opt+X, X, M
  - Editing: Cmd+Z, Cmd+Shift+Z, Delete, Opt+Delete, Cmd+K, comma, period
  - Tools: V (selection), C (razor), S (snap)
- **Ссылка:** `CUT_NLE_UNIVERSAL_ACTION_REGISTRY.md` — полный список 115 actions
- **Зависимости:** Phase 3 (MonitorTransport — JKL привязаны к активному монитору)

### 6.1 Favorite markers: hotkeys M / N / MM
- **Что:** При просмотре в Source Monitor:
  - **M** = positive marker (favorite / keep)
  - **N** = negative marker (reject / discard)
  - **MM** (double-tap) = marker + text comment popup
- **Где:** Новый `useHotkeys.ts` hook (или расширить существующий)
- **Данные:** MarkerNode с типом `favorite_positive | favorite_negative | note`
- **Backend:** Markers уже в `useCutEditorStore.ts` (type TimeMarker)

### 6.2 Standard markers на ruler
- **Что:** Маркеры на верхней линейке Timeline
- **Где:** `TimelineTrackView.tsx` (ruler area)
- **UI:** Цветные треугольники / флажки на ruler. Click → edit text.

### 6.3 Three-point editing (IN/OUT в Source Monitor)
- **Что:** Set IN point, set OUT point, insert to timeline
- **Где:** `VideoPreview.tsx` (когда feed='source')
- **UI:**
  - Hotkey **I** = set IN, **O** = set OUT
  - Visual overlay на video: IN/OUT markers на scrubber
  - Кнопка "Insert to Timeline" (или hotkey **,** / **.**)
- **Store:** `markIn` / `markOut` уже есть в useCutEditorStore

---

## PHASE 7: BPM & POLISH
**Цель:** Финальная полировка

### 7.1 Script BPM — hybrid model
- **Что:** Script BPM = не линейный, а по событиям
- **Сейчас:** Линейное распределение
- **Нужно:**
  - Layer A (symbolic): event density per page (scene heading, new speaker, CUT TO = event)
  - Layer B (semantic): embedding distance shift = energy spike (future, requires JEPA)
- **MVP:** Layer A only (rule-based, ~50 строк в screenplay_timing.py)

### 7.2 JKL shuttle + frame step
- **Что:** Professional transport controls
- **Где:** `TransportBar.tsx` + hotkey handler
- **J** = reverse playback, **K** = pause, **L** = forward playback
- **J+J** = 2x reverse, **L+L** = 2x forward
- **Arrow Left/Right** = 1 frame step

### 7.3 Layout persist
- **Что:** Save/load layout to project file
- **Где:** `usePanelLayoutStore.ts`
- **Сейчас:** Store есть, save/load нет
- **Нужно:** При смене layout → save to `{sandbox_root}/.vetka_cut/layout_state.json`

### 7.4 Drag-to-dock
- **Что:** Drag панель за title bar → dock в другую позицию
- **Где:** `PanelShell.tsx`, `PanelGrid.tsx`
- **Сейчас:** Инфраструктура PanelMode + DockPosition есть, drag UI нет

---

## PHASE 8: LOGGER ENRICHMENT (DAG grows flesh)
**Цель:** DAG обрастает реальными данными о медиа
**Зависит от:** Phase 2 (scene nodes существуют)

### 8.1 Scene-material linking
- **Что:** Привязка clips → SCN_XX nodes
- **Алгоритм:**
  1. Clip → transcript (Whisper, уже есть)
  2. Transcript → semantic match с scene text (embedding similarity)
  3. Или manual: drag clip на scene node в DAG
- **Backend:** `cut_project_store.py` (add edges: has_media)

### 8.2 Shot scale auto-detection
- **Что:** CU/MCU/MS/WS/EWS определяется vision моделью
- **Формат:** `shot_scale_auto: "MS"`, `shot_scale_manual: null`, `shot_scale_confidence: 0.82`
- **Manual override:** Inspector позволяет поправить

### 8.3 Lore nodes: characters, locations, items
- **Что:** Создание LoreNode в DAG
- **Алгоритм:**
  1. Из script: имена персонажей (CAPS before dialogue), локации (INT./EXT.)
  2. Manual: пользователь создаёт/редактирует lore nodes
  3. Edges: `mentions` (SceneChunk → LoreNode)
- **UI:** В Inspector показывать lore при клике на scene node

### 8.4 Screenplay import: Fountain, FDX
- **Что:** Парсеры для профессиональных форматов
- **Fountain (.fountain):** Open format, plain text с конвенциями. Парсер: afterwriting-labs или Jouvence (Python)
- **FDX (.fdx):** Final Draft XML. Парсер: прямое чтение тегов `<Scene>`
- **DOCX:** pandoc → plain text → screenplay_timing.py
- **Каждый парсер:** ~100-200 строк, выход = plain text для screenplay_timing.py

---

## PHASE 9: FUTURE / GENERATIVE (не MVP)

### 9.1 Documentary mode (инверсия)
- Import media → auto-transcribe → AI generates scene descriptions → Script panel

### 9.2 Interactive lore tokens
- Слова в сценарии = гиперссылки. ANNA → character node. CAFE → location node.

### 9.3 Storylines (партитура)
- Script spine в центре + storyline branches по X (арки персонажей)

### 9.4 Multiverse DAG advanced UI
- Branch visualization, merge logic, draft comparison

### 9.5 Bridge layer (Circuit A ↔ Circuit B)
- Bidirectional translation: symbolic ↔ learned/JEPA

### 9.6 Effects node graph
- DaVinci Fusion-style nodes для color correction + transitions

---

## ПОРЯДОК ИСПОЛНЕНИЯ (summary)

```
Phase 0: UI CLEANUP              ← расчистка (параллельно с Phase 1)
  0.1 Удалить legacy файлы (CutEditorLayout.tsx, SourceBrowser.tsx)
  0.2 Убрать дублирующий Program Monitor
  0.3 TransportBar → MonitorTransport + TimelineToolbar
  0.4 StorySpace 3D: убрать с таймлайна → mini в Program Monitor
  0.5 Чистка лишних кнопок Timeline

Phase 1: SCRIPT SPINE            ← фундамент, без него ничего не работает
  1.1 screenplay_timing.py
  1.2 API: POST /cut/script/parse
  1.3 ScriptPanel: chunk blocks

Phase 2: DAG SPINE               ← script chunks → DAG nodes
  2.1 Backend: chunks → project DAG
  2.2 Frontend: DAG Y=хрон
  2.3 Bidirectional sync

Phase 3: SOURCE/PROGRAM ROUTING  ← критический баг + routing
  3.1 Store: два media path
  3.2 VideoPreview: prop feed
  3.3 Layout wiring
  3.4 MonitorTransport: controls под каждым монитором
  3.5 DAG click → Source

Phase 4: PARALLEL TIMELINES      ← 2 timeline stacked view
  4.1 Stacked view
  4.2 Versioning wiring

Phase 5: AUTO-MONTAGE UI         ← frontend для готового backend
  5.1 3 mode buttons
  5.2 Progress
  5.3 Reverse dependency

Phase 6: HOTKEYS & MARKERS       ← профессиональный editing workflow
  6.0 useHotkeys.ts — центральный регистр (115 actions из Registry)
  6.1 Favorite markers (M/N/MM)
  6.2 Standard markers
  6.3 Three-point editing (I/O/comma/period)

Phase 7: BPM & POLISH
  7.1 Script BPM hybrid
  7.2 JKL shuttle (подключено через useHotkeys)
  7.3 Layout persist
  7.4 Drag-to-dock

Phase 8: LOGGER ENRICHMENT       ← DAG grows flesh
  8.1 Scene-material linking
  8.2 Shot scale detection
  8.3 Lore nodes
  8.4 Screenplay import formats

Phase 9: FUTURE / GENERATIVE     ← не MVP
  9.1-9.6 Documentary, lore tokens, storylines, multiverse, bridge, effects
```

### Граф зависимостей

```
Phase 0 (cleanup) ──────────────────────────────────────────────┐
     │ параллельно                                               │
Phase 1 (script spine) ──→ Phase 2 (DAG spine) ──┐              │
                                                  ├──→ Phase 5   │
Phase 3 (routing) ───────────────────────────────┤  (montage)   │
     │                                            │              │
     └──→ Phase 4 (parallel timelines) ──────────┘              │
                                                                 │
Phase 6 (hotkeys) ←── Phase 0.3 (MonitorTransport) ←────────────┘
     │
     └──→ Phase 7 (polish)

Phase 8 (logger) ←── Phase 2 (DAG nodes exist)
```

---

## РЕВЬЮ UI ВМЕСТЕ С ДАНИЛОЙ

**TODO:** Пройтись по UI вживую и решить:
1. `CutEditorLayout.tsx` (799 строк) — это legacy? Удалить?
2. `SourceBrowser.tsx` (540 строк) — заменён ProjectPanel? Удалить?
3. Нет ли мёртвого кода в TimelineTrackView.tsx (1687 строк)?
4. DAGProjectPanel: кластерный layout — выкинуть или оставить как альтернативный view?
5. Общая визуальная ревизия: что выглядит как мусор от доноров?

---

## ЗАМЕТКИ ДЛЯ OLLAMA / МАЛЕНЬКИХ МОДЕЛЕЙ

Каждый таск в этом roadmap написан так, чтобы маленькая модель могла его выполнить:
- **Файлы** указаны конкретно (не "somewhere in the project")
- **Dataclass/interface** прописан прямо в таске
- **Алгоритм** пошаговый
- **Тесты** описаны (что проверять)
- **Зависимости** указаны (что должно быть сделано ДО)

При нарезке в таски на TaskBoard — каждый таск из этого roadmap = 1 таск на доске.
Таски Phase 1 и Phase 3.1-3.2 можно делать параллельно (независимы).
