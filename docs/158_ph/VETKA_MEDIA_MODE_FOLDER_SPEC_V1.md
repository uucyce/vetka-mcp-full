# VETKA_MEDIA_MODE_FOLDER_SPEC_V1
**Created:** 2026-03-02  
**Status:** draft-for-implementation  
**Mode:** `media_edit_mode` (right-click activation from Directed Mode)

## CHANGELOG_2026-03-02_Codex
1. Зафиксировано пользовательское видение media-mode папки как отдельного монтажного режима.
2. Описан dual-mode UX: Directed (быстрый обзор) -> Media Edit (монтаж и анализ).
3. Добавлен runtime контракт `MCP_MEDIA` с авто/полуавто сценарием запуска.
4. Добавлены правила scene graph, timeline, multicam и semantic links.
5. Зафиксирован музыкально-ритмический контур (PULSE + JEPA + optional SUNO API).

---

## 1) Product Intent
Цель режима: из "папки с хаотичным материалом" автоматически получить монтажно-готовую структуру сцен, синхронизированные дорожки и быстрый путь к черновому фильму.

Уровни автоматизации:
1. 70-90% действий выполняются автоматически.
2. Оставшаяся часть закрывается через наводящие вопросы Jarvis и выбор дублей человеком.

---

## 2) UX: Directed vs Media Edit

### 2.1 Directed Mode (default)
1. Данные лежат в обычных директориях.
2. Видео показывается карточкой `16:9` с play-иконкой.
3. Превью:
   - ultra-fast short preview (`~300ms`), 
   - fallback static thumbnail,
   - optional animated preview (gif/webp-like approach).
4. Аудио:
   - waveform-strip,
   - отображение первых ~60 секунд,
   - справа длительность (`+mm:ss`).

### 2.2 Переход в Media Edit Mode
1. Активация: right-click -> `Open in Media Mode`.
2. Стартует `MCP_MEDIA` и анализ проекта.
3. Запуск может быть не мгновенным (допускается warm-up/analyze phase).
4. Пользователь видит этапы анализа и прогресс (не "зависание", а managed startup).

---

## 3) MCP_MEDIA Runtime Contract

### 3.1 Обязанности
1. Индексация media (video/audio/image/doc/script).
2. Синхронизация видео-аудио.
3. Автогруппировка по сценам (metadata/script/treatment/time).
4. Построение scene graph + montage timeline.
5. Подготовка playback artifacts (preview/full).

### 3.2 Auto -> Semi-auto fallback
Если данных не хватает (нет монтажного листа, нет сценария, слабый нейминг файлов):
1. Jarvis задает наводящие вопросы в чат/scan panel/unified search.
2. Пользователь может догрузить файлы и ответы.
3. MCP_MEDIA делает incremental rebuild, а не full reset.

---

## 4) Scene/Timeline Model

### 4.1 Core Abstraction
1. Один узел = одна сцена = одна рабочая папка сцены.
2. Ветка сцены = универсальный timeline слева направо.
3. Базовый слой:
   - video track сверху,
   - synced audio track снизу.

### 4.2 Duplicates / Takes
1. По Y: новые дубли выше базового слоя (приоритет воспроизведения сверху).
2. По Z: optional experimental "drum" navigation для realtime multicam переключения.
3. Default V1: Y-first для очевидности и привычной монтажной логики.

### 4.3 Scene Order
1. Если есть сценарий/тритмент: порядок по ним.
2. Если нет: fallback по времени съемки + semantic clustering.

---

## 5) Semantic Links Inside Media Mode

При выборе кадра/фрагмента система показывает связанные материалы:
1. по герою (same character),
2. по действию (similar action),
3. по локации (same location),
4. по сцене/теме (same narrative cluster).

Связи отображаются как:
1. inline подсветка на таймлайне,
2. related panel,
3. graph edges в scene knowledge view.

---

## 6) Jarvis + JEPA + LLM Team

1. Jarvis в этом режиме действует как media architect.
2. JEPA помогает выделять смысловые структуры и представления по материалу.
3. LLM-команда на этой базе может:
   - собрать treatment постфактум (документалистика case),
   - предложить сценную структуру,
   - подготовить черновой сценарий/монтажный план.

---

## 7) Music-Driven Editing Layer

1. PULSE = аудио-слой и ритм-сигналы.
2. Optional connector: SUNO API (для музыкальных треков/вариантов).
3. JEPA используется как смысловой валидатор соответствия кадр <-> музыка/настроение.
4. Приоритет ритмического монтажа:
   - не только длина склеек,
   - а внутрикадровое движение и фазы кадра.

Гипотеза из практики:
1. Музыка присутствует всегда (даже без явного саундтрека).
2. Ритм видео/сценария/монтажа должен моделироваться как единая система.

---

## 8) Playback + Artifact

1. Artifact должен воспроизводить любые media-отрезки в этом режиме.
2. Поддержка multicam playback (V1 basic switch, V2 realtime advanced).
3. Поддержка playback из scene-node контекста и из full timeline.

---

## 9) Data Contract Additions (V1)

Добавить в unified contracts:
1. `scene_node_id`
2. `take_id`
3. `sync_group_id`
4. `timeline_lane` (`video_main`, `audio_sync`, `take_alt_y`, `take_alt_z`)
5. `rhythm_features`:
   - `cut_density`,
   - `motion_volatility`,
   - `phase_markers`
6. `cam_features`:
   - `frame_uniqueness`,
   - `memorability_score_est`

---

## 10) Implementation Phases (for roadmap sync)

1. P5.1: Directed preview cards (video/audio) polish and performance budget.
2. P5.2: `media_edit_mode` activation + MCP_MEDIA startup orchestration.
3. P5.3: auto scene assembly + Jarvis guided fallback loop.
4. P5.4: timeline lanes (Y-first takes) + multicam basic.
5. P5.5: semantic links panel and graph overlays.
6. P5.6: music-driven edit assists (PULSE + rhythm features).

---

## 11) Open Items

1. Принять точный формат short-preview (`300ms mp4/webp/gif`) после профилирования.
2. Утвердить метрики и пороги для CAM-гипотезы.
3. Утвердить UX поведения Z-mode (оставить экспериментальным до A/B).

---

## 12) Media Asset Tooling (MP4 -> Alpha PNG -> APNG)

MARKER_167.MEDIA.APNG.TOOLING.V1

Цель: стандартный pipeline для подготовки анимационных MYCO/media-mode иконок из `.mp4` с прозрачностью.

Основной tool в VETKA:
- `scripts/media/mp4_to_apng_alpha.py`

README:
- `scripts/media/README.md`

Поддерживаемые режимы альфы:
1. `chroma` — хромакей по цвету (быстрый дефолт)
2. `luma` — alpha из яркости
3. `depth` — alpha из монокулярной depth map (через `transformers`)

Контракт запуска (Codex/Claude/VETKA):
1. вход: `input.mp4`
2. выход: `frames_rgba/*.png` + `manifest.json` + `output.apng`
3. runtime: через `ffmpeg` + python deps (`pillow`, `numpy`), optional (`torch`, `transformers`) для depth

Принцип внедрения:
1. подготовка анимаций — отдельный asset-pipeline шаг
2. не делать inline UI hack для конвертации на лету
3. хранить reproducible параметры (`fps`, threshold/softness) в `manifest.json`
