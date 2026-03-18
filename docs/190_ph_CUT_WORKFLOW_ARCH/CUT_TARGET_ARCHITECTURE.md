# CUT Target Architecture
# Целевая архитектура по v1.0 + уточнения

**Date:** 2026-03-17, updated 2026-03-18
**Basis:** VETKA_CUT_Interface_Architecture_v1.docx
**Status:** ALL QUESTIONS RESOLVED ✅

---

## 0. Конституция (из v1.0 без изменений)

> **CUT is not a timeline editor. CUT is a narrative graph navigator.**
> **The editor navigates narrative intent through the DAG of possibilities.**

> CUT не ищет единственно верный монтаж. CUT исследует множество допустимых монтажей
> под разные цели, аудитории и контексты.

- Two-circuit architecture: Circuit A (symbolic/editorial) + Circuit B (learnable/JEPA)
- Bridge layer: bidirectional translation
- 9 principles: no single correct montage, editor sovereign, symbolic=coordinates, learned=perception, bridge bidirectional, favorites=collective memory, versions first-class, formula must evolve, music is in montage

### System Overview Diagram

```
                    CUT SYSTEM OVERVIEW

              ┌──────────────────────────┐
              │      SCRIPT SPINE        │
              │  Scene chunks (SCN_01…)  │
              │  Characters / Locations  │
              │  START → … → END         │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │      DAG PROJECT         │
              │   (Multiverse Graph)     │
              │                          │
              │  Scene nodes             │
              │  ├ video takes           │
              │  ├ audio / music / SFX   │
              │  ├ lore (chars, locs)    │
              │  ├ semantic links        │
              │  └ montage variants      │
              │                          │
              │  All branches coexist    │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │      LOGGER LAYER        │
              │                          │
              │  • shot scale detection  │
              │  • character detection   │
              │  • transcription         │
              │  • semantic similarity   │
              │                          │
              │  → enriched DAG nodes    │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │        PULSE AI          │
              │                          │
              │  Select best takes       │
              │  Evaluate rhythm / BPM   │
              │  Generate cut variants   │
              │                          │
              │  → Rough Cut timeline    │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │   TIMELINE PROJECTIONS   │
              │                          │
              │  cut-00: Logger assembly │
              │  cut-01: PULSE rough cut │
              │  cut-02: Editor cut      │
              │  cut-03: Final cut       │
              │                          │
              │  Timeline = path thru DAG│
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │      HUMAN EDITOR        │
              │                          │
              │  Replace takes           │
              │  Adjust rhythm           │
              │  Refine narrative        │
              │                          │
              │  → Final Film            │
              └──────────────────────────┘
```

---

## 1. Script Panel — хребет всего проекта

### 1.1 Что уже есть
- Y-axis vertical display, click→sync, teleprompter, BPM dots

### 1.2 Что нужно доработать

#### Script как ось Y всего проекта
Script = основа. Каждая строка = точка на оси хрон (Y).
Правило: **1 страница Courier 12pt = 60 секунд экранного времени.**

Script chunks должны быть **видимыми отдельными блоками** в панели:
- Каждый chunk = визуально выделенный блок (border, subtle background)
- Chunk = scene (если определяется scene heading: INT./EXT.)
- Если scene heading не найден = chunk по абзацам (fallback)

#### ✅ РЕШЕНО: Chunking strategy (Q1)

**Выбран: Вариант B (гибридный) + page-timer + manual override.**

> Ответ Данилы (2026-03-17): Гибридный подход. Отдельные чанки текста должны быть видны как кликабельные блоки.
> Время в кино ≠ дата создания. Время = хрон сценария. 1 страница Courier 12pt = 1 минута — это стандарт индустрии.
> Даже если не удаётся красиво разбить по сценам — показываем чанки как есть, каждый кликабелен.

**Реализация (pipeline):**

1. **`pulse_script_analyzer.py`** (уже есть) ищет scene headings (`INT./EXT./ИНТ./НАТ.`)
2. **Если нашёл** → жёсткий split по сценам + расчёт страниц внутри каждой
3. **Если не нашёл** (документалка, кривой текст) → fallback на абзацы + auto-estimate
4. **Правило timing:** `1 страница Courier 12pt = ровно 60 секунд`
   - Реализуется в новом `screenplay_timing.py` (~150 строк)
   - Считаем: 55 строк = 1 страница ИЛИ ~1800-2000 символов = 1 страница
   - `start_sec = cumulative_pages * 60`
   - Каждый chunk → `{chunk_id, start_sec, duration_sec, scene_heading}`
5. **Manual override:**
   - Drag-split в ScriptPanel (как в FCP Timeline — тянешь разделитель)
   - Кнопка «AI → Предложить разбиение» (LLM один раз прогоняет весь текст)

**Форматы импорта:**
- `.fountain` (open format) — готовый парсер: afterwriting-labs или Jouvence (Python)
- `.fdx` (Final Draft XML) — прямой парсинг тегов `<Scene>`
- `.pdf` — OCR уже есть в проекте
- `.docx` — pandoc conversion → plain text
- Plain text — regex detection (уже работает)

**Затраты:** 1-2 дня. Чистый rule-based + существующие компоненты. Никакого GPU.

**Привязка к DAG:** `start_sec` → Y-координата в DAG Project Panel (снизу вверх).
Каждый chunk = кликабельный блок в Script Panel + scene-нода в DAG.

#### Screenplay Import
Нужны парсеры для стандартных форматов:
- `.fountain` (open format, plain text с конвенциями)
- `.fdx` (Final Draft XML)
- `.pdf` (Courier 12pt — уже есть OCR)
- Plain text с scene headings (уже частично в pulse_script_analyzer.py)

#### Documentary Mode (инверсия)
Когда нет сценария:
1. Import media → auto-transcribe (Whisper)
2. Transcript → AI генерирует scene descriptions
3. Descriptions → становятся Script panel content
4. Пользователь редактирует → DAG обновляется

---

## 2. DAG Project — каноническая модель фильма

> **Каноническая формула:**
> Script defines the film spine.
> DAG Project grows media, lore, and semantics around that spine.
> Timeline is a horizontal projection of the DAG.
> PULSE assembles the first rough cut from the DAG.
> The editor refines it into the final film.

### 2.0 Трёхуровневая модель (Three-Level Architecture)

DAG Project — не один монолитный граф, а три уровня абстракции:

```
┌─────────────────────────────────────────────────────────┐
│              LEVEL 1 — SCRIPT SPINE                     │
│                                                         │
│  Позвоночник проекта: порядок сцен, хрон, лор.         │
│  FILM START → [SCN_01] → [SCN_02] → ... → FILM END    │
│                                                         │
│  Это чистая драматургическая структура.                 │
│  Здесь нет медиа — только сценарий и его семантика.    │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│           LEVEL 2 — DAG PROJECT / LOGGER                │
│                                                         │
│  Сцена обрастает плотью:                                │
│  - video takes (camera A, B, C...)                      │
│  - audio (sync, ADR, music, SFX)                        │
│  - lore (characters, locations, items)                   │
│  - PULSE metadata (energy, dramatic_function, Camelot)  │
│  - similarity links                                     │
│                                                         │
│  Это логгер + структурный граф проекта.                 │
│  Материал привязан к сценам, а не висит в project bin.  │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│          LEVEL 3 — TIMELINE PROJECTIONS                 │
│                                                         │
│  Таймлайны = горизонтальные проекции DAG:               │
│  - cut-00: Rough Cut (PULSE Favorites)                  │
│  - cut-01: Script-driven (PULSE)                        │
│  - cut-02: Editor manual                                │
│  - cut-03: Final Cut (locked)                           │
│                                                         │
│  DAG не исчезает — остаётся источником для всех версий. │
│  Каждый timeline = одна из возможных развёрток графа.   │
└─────────────────────────────────────────────────────────┘
```

**Ключевое:** Script Spine — не просто текст. DAG/Logger — не просто project bin. Timeline — не отдельный мир. Это три слоя одной онтологии фильма.

### 2.1 Проблема (текущее состояние кода)
Сейчас: ноды расположены по кластерным колонкам (Character | Location | Take...).
Y-ось = абстрактная позиция, не привязанная ко времени.
**Это фундаментально неверно.** DAG = не project bin. DAG = онтология фильма.

### 2.2 Script Spine — центральная вертикальная ось

**Y-ось = хрон фильма** (bottom=START, top=END).
По центру — **Script Spine**: цепочка scene chunks с постоянными ID `SCN_XX`.

Каждый `SCN_XX` = DAG-узел, от которого расходятся ветви:
- **ВЛЕВО** — Visual: video takes, photos, 3D generated, graphics
- **ВПРАВО** — Audio: dialogue, ADR, music, SFX, ambience, transcription

```
            VIDEO / VISUAL         │      AUDIO / MUSIC / VOICE
            (left side)            │      (right side)
                                   │
  ┌───────────────┐                │           ┌───────────────┐
  │  RAW CLIPS    │◄──────────────┼──────────►│  MUSIC        │
  │  CAMERA A     │               │           │  SCORE        │
  │  CAMERA B     │               │           │  AMBIENCE     │
  └───────▲───────┘               │           └───────▲───────┘
          │                        │                   │
          │           ┌────────────┴──────────┐        │
          └──────────►│    SCN_01 (SCRIPT)    │◄───────┘
                      │  INT. CAFE – DAY      │
                      │  start: 00:00         │
                      └────────────▲──────────┘
                                   │
                      ┌────────────┴──────────┐
                      │   LORE / SEMANTICS    │
                      ├── ANNA (character)    │
                      ├── MARK (character)    │
                      ├── CAFE (location)     │
                      └───────────────────────┘
                                   │
                                   │
  ┌───────────────┐                │           ┌───────────────┐
  │  VIDEO CLIPS  │◄──────────────┼──────────►│  DIALOGUE     │
  │  TAKE 1       │               │           │  ADR          │
  │  TAKE 2       │               │           │  SFX          │
  └───────▲───────┘               │           └───────▲───────┘
          │           ┌────────────┴──────────┐        │
          └──────────►│    SCN_02 (SCRIPT)    │◄───────┘
                      │  EXT. STREET – NIGHT  │
                      │  start: 01:10         │
                      └───────────────────────┘
                                   │
                                   ▼
                              FILM END (top)
```

**Опция отображения:** по умолчанию START внизу, END вверху. Кнопка `flip Y` меняет направление (как сортировка по дате/имени).

### 2.3 Интерактивный лор — гиперссылки в сценарии

✅ РЕШЕНО (Q2 Storylines, Q4 Metadata, Q5 Scene Click)

> Ответ Данилы (2026-03-18): Слова в сценарии = интерактивные токены.
> Персонажи, локации, предметы — всё кликабельно.
> При клике открывается ветка персонажа/локации из DAG.

В тексте сценария:
```
INT. CAFE – DAY
ANNA sits at the table. She waits for MARK.
```

Слова становятся гиперссылками:
- `ANNA` → character node
- `MARK` → character node
- `CAFE` → location node

**При клике на токен `ANNA`:**
```
CHARACTER DAG: ANNA
├── Biography / notes
├── Relations: Mark, Cafe owner, ...
├── Scenes (appearances):
│   ├── SCN_01 (cafe) — start: 00:00
│   ├── SCN_05 (argument) — start: 04:30
│   └── SCN_12 (resolution) — start: 11:00
└── Media:
    ├── Linked video clips (all takes with Anna)
    └── Linked audio (ADR, VO, character motifs)
```

**При клике на scene-ноду `SCN_03`:**
Живой узел — Inspector показывает:
- Превью сцены (лучший clip по PULSE score или контактный лист всех takes)
- Весь лор: герои, локации, объекты
- Все связанные ассеты (видео + аудио)
- PULSE metadata: Camelot key, energy, pendulum, dramatic_function

**Таким образом: SCRIPT = интерфейс навигации по DAG.**

### 2.4 Метадата нод — полная структура

Каждая нода DAG содержит (при клике → Inspector):

**Scene node (SCN_XX):**
- Script text (chunk content)
- start_sec / duration_sec (из page-timer)
- Linked characters, locations, items
- Linked media (video takes, audio)
- PULSE: dramatic_function, energy, Camelot key, pendulum

**Media node (clip):**
- Технические: codec, resolution, fps, audio channels, duration
- IN/OUT points (если заданы)
- Крупность кадра: CU/MCU/MS/WS/EWS (🎬 уточнить: AI detection или вручную)
- Объекты в кадре (персонажи, предметы — из vision analysis)
- PULSE score (рейтинг качества дубля для данной сцены)
- Семантические связи (similarity links к другим clips)

**Lore node (character/location/item):**
- Name, description, notes
- Relationships (edges к другим lore nodes)
- Scene appearances (список SCN_XX)
- Linked media (все clips где присутствует)

### 2.5 Два представления — одна модель

**Ключевой принцип: DAG Project и Timeline = два представления одного графа.**

DAG (vertical) → поворот 90° → Timeline (horizontal).
`SCN_XX` остаются теми же узлами. Медиа и аудио лежат «вокруг» сценарного трека.

```
DAG Project (vertical):

    START (bottom)
        │
      SCN_01
        │
      SCN_02
        │
      SCN_03
        │
    END (top)

        ↓ transform (rotate 90°)

Timeline (horizontal):

    START ── SCN_01 ── SCN_02 ── SCN_03 ── END
```

**Переключатель:** `VIEW = Vertical DAG / Horizontal Timeline`.
Навигация одна и та же, меняется только проекция.

**DAG Timeline (горизонтальный вид):**
```
VIDEO LAYERS (above script track)
┌──────────────────────────────────────────────────────────────┐
│ V1:  [clip]────[clip]────────────[clip]──────────────────── │
│ V2:        [clip]────[clip]────[clip]                       │
└──────────────────────────────────────────────────────────────┘

SCRIPT TRACK (spine, center)
┌──────────────────────────────────────────────────────────────┐
│      [SCN_01]      [SCN_02] [SCN_03]   [SCN_04]   [SCN_05] │
└──────────────────────────────────────────────────────────────┘
     ↑           ↑         ↑          ↑          ↑
     scene nodes с теми же ID, что и в вертикальном DAG

AUDIO LAYERS (below script track)
┌──────────────────────────────────────────────────────────────┐
│ A1:  [music]────────────[music]───────────────               │
│ A2:       [dialog]────────────[dialog]───────                │
│ A3:  [SFX]────[SFX]────────────[SFX]───────                 │
└──────────────────────────────────────────────────────────────┘
      ▶ time →   start (left)                      end (right)
```

### 2.6 PULSE Assembly Flow — как AI монтирует по DAG

**PULSE не монтирует из пустоты. Он работает поверх уже логированного DAG.**

```
SCRIPT SPINE (input)
  Scene 1 → Scene 2 → Scene 3 → Scene 4 → Scene 5
                         │
                         ▼
DAG PROJECT / LOGGER LAYER
  Для каждой сцены доступны:
  - video takes (camera A, B, C...)
  - audio/sync
  - generated shots
  - lore / characters / locations
  - pulse metadata
  - similarity links
                         │
                         ▼
PULSE SELECTION STAGE
  Scene 1: выбрать лучший take → критерии:
    dramatic_function, continuity, rhythm/bpm,
    semantic fit, visual/audio harmony
  Scene 2: выбрать лучший take
  Scene 3: ...
                         │
                         ▼
PULSE ASSEMBLY → ROUGH CUT TIMELINE (cut-NN)
  [best S1] [best S2] [best S3] [best S4] [best S5]
  + альтернативы: Scene 1: take_1 / take_3 / generated_v2
                         │
                         ▼
EDITOR REFINEMENT → FINAL CUT
  - заменяет дубли
  - меняет ритм
  - перестраивает переходы
  - блокирует финальный монтаж
```

**Full pipeline:**
```
Raw media
  → sync / transcription / scene matching
  → DAG Project / Logger
  → PULSE Rough Cut (auto)
  → Human Editor Cut (manual)
  → Final Cut
```

**RULE: Auto-montage ALWAYS creates new `cut-NN`. NEVER overwrites.**

### 2.7 Почему это не «ещё одна монтажка»

В обычном NLE (Premiere, DaVinci, FCP):
```
script        ← отдельный файл
project bin   ← отдельная папка
timeline      ← НЕ связан ни с чем
```
Три несвязанных сущности. Монтажёр вручную держит связи в голове.

В CUT:
```
script  = spine (ось DAG)
DAG     = структура (онтология фильма)
timeline = проекция DAG (горизонтальный разворот)
```

Это даёт:
- Монтаж от сценария (script-driven)
- Монтаж от материала (media-driven)
- Монтаж от AI (PULSE-driven)
- Единый граф фильма — любой вход ведёт к полной картине

### 2.8 Storylines — параллельные сюжетные линии (партитура)

✅ РЕШЕНО (Q2.1)

> Ответ Данилы + GPT synthesis (2026-03-18):
> Не отдельные деревья (развалится единый хрон).
> Не просто цветовые тэги (слишком слабо для драматургии).
> **Script spine в центре + storyline branches по X.**
> Как партитура / монтажная карта / драматургическая схема.

**Принцип:**
- **Y** = хрон фильма (постоянный для всех линий)
- **X** = сюжетные линии / персонажи / темы
- Общие сцены = точки пересечения линий (все ветки входят в одну scene-node)

```
       X1: Anna arc    X2: Script Spine    X3: Mark arc
Y ↑
│
│      [emotion]         [Scene 10]          [decision]
│      [close-up]        [Scene 9]           [phone call]
│      [memory ref]      [Scene 8]           [arrival]
│                          ...
│      [conflict]        [Scene 6]           ← shared scene (both)
│                          ...
│      [intro]           [Scene 2]           [intro]
│                        [Scene 1]
│
└──────────────────────────────────────────────────────────→ X
```

**Каждая storyline column содержит:**
- Арку персонажа (ключевые моменты, эмоциональные точки)
- Связанные clips (все takes с этим персонажем)
- Lore nodes (backstory, relationships)
- Character motifs (музыкальные темы)

**Общая сцена** (например Scene 6 — конфликт Anna и Mark):
- Нода `SCN_06` находится на центральной оси
- От неё идут edges к обеим storyline columns
- При клике — показывает ОБА персонажа и все их takes для этой сцены

**Это масштабируется:**
- 2 линии (герой/антагонист) → 2 X-колонки
- 5 линий (ансамбль) → 5 X-колонок
- Музыкальная линия → отдельная X-колонка
- Тематическая линия (flashbacks) → отдельная X-колонка

### 2.9 Multiverse DAG — драфты сценария и альтернативные монтажи

✅ РЕШЕНО (Q2.2)

> Ответ Данилы (2026-03-18):
> DAG Project = мультивселенная фильма. Все сценарии, все варианты сцен, все монтажи
> существуют одновременно. Timeline — это выбор одной траектории через этот граф.
> Конструирование (script → film) и реконструирование (footage → script) = симметричные
> процессы. Баланс между документальным и постановочным кино настраиваем.

**Принцип:** Script drafts НЕ хранятся как отдельные DAG. Все варианты живут в одном графе.

> **DAG Project stores the multiverse of the film.**
> **Timeline is the currently chosen universe.**
> **A scene on the timeline is never final; it is always a projection of a richer graph node.**

#### Три типа расхождений в Multiverse DAG

**A. Script branch** — меняется сценарный ход:
```
Scene 2
├─ Draft 1: герой входит в кафе
├─ Draft 2: герой звонит с улицы
└─ Improvised: сцена из документального материала (transcript + vision)
```

**B. Montage branch** — сценарий тот же, монтаж разный:
```
Scene 4
├─ V1: длинные планы (emotional emphasis)
├─ V2: быстрый ритм (rhythmic emphasis)
└─ V3: music-driven cut
```

**C. Material branch** — разные источники для одного сценарного узла:
```
Scene 3
├─ camera take A
├─ camera take B
├─ archive insert
└─ generated shot
```

#### Каноническая схема Multiverse DAG

```
                            MULTIVERSE DAG PROJECT

                               FILM START
                                   │
                                   ▼
                          [S1] Opening Scene
                          anchor, start: 00:00
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              [S2-A] Draft 1  [S2-B] Draft 2  [S2-C] Improvised
              classic version  alt dialogue    reconstructed
                    │              │              │
                    └──────┬───────┴──────────────┘
                           │
                           ▼
                    [S3] Common scene (merge back)
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              [S4-V1] slow   [S4-V2] fast
              emotional       rhythmic
                    │             │
                    └──────┬──────┘
                           │
                           ▼
                    [S5] Final confrontation
                           │
                           ▼
                        FILM END
```

#### Merge logic для драфтов сценария

Скрипты **мерджатся по чанкам**: если scene heading совпадает — это один узел с вариантами.
Если не совпадает — расхождение по X.

```
Draft 1:  Scene1 → Scene2 → Scene3 → Scene4
Draft 2:  Scene1 → Scene2 → Scene2b → Scene3 → Scene4

DAG:
  Scene1
    │
  Scene2
    ├── Scene2a (draft 1)
    └── Scene2b (draft 2)
    │
  Scene3
    │
  Scene4
```

Алгоритм определения "та же сцена": scene heading match + semantic similarity (embedding distance).

#### Timeline = экстракт из Multiverse

```
MULTIVERSE DAG:    S1 → S2[A|B|C] → S3 → S4[V1|V2] → S5

Timeline 1 (PULSE):     S1 → S2-B → S3 → S4-V2 → S5
Timeline 2 (Editor):    S1 → S2-A → S3 → S4-V1 → S5
Timeline 3 (Doc):       S1 → S2-C → S3 → S4-V1 → S5
```

**Каждый timeline = путь через граф. DAG не исчезает.**

#### Обратная зависимость (Reverse Dependency)

При клике на сцену в таймлайне — показать альтернативы из DAG:

```
Scene 2B selected in timeline →
├── show sibling script variants: [S2-A] [S2-C]
├── show montage variants (if exist)
├── show available takes
├── show music alternatives
└── show lore links (characters, locations)
```

**Timeline — не тупой линейный рендер, а живой указатель на граф.**

#### Construction / Reconstruction Symmetry

```
Fiction mode:       Script → Scene chunks → Shoot footage → DAG → Timeline
Documentary mode:   Raw footage → Transcript → Scene reconstruction → DAG → Timeline
Hybrid mode:        Both directions coexist in one DAG Project
```

> **In CUT, construction and reconstruction are symmetric operations inside one project graph.**

Примеры гибрида: Нанук на Севере (Flaherty, 1922), Вернер Херцог, mockumentary.
Система не делает искусственного разделения — любой проект может двигаться в обе стороны.

### 2.10 ✅ РЕШЕНО: Shot Scale, Lore Editing, Flip Y

#### Q2.3 — Крупность кадра: automatic-first

> Решение (2026-03-18): AI detection by default. Manual correction as override.

Shot scale (CU/MCU/MS/WS/EWS) определяется автоматически vision/JEPA/multimodal моделью
как часть Logger layer. Ручная правка = override, а не основной способ.

**Формат данных clip node:**
```
shot_scale_auto: CU | MCU | MS | WS | EWS    (vision model)
shot_scale_manual: optional override           (editor)
shot_scale_final = manual if exists, else auto
shot_scale_confidence: 0..1
```

**Дополнительно AI определяет:**
- Состав кадра (композиция)
- Персонажей в кадре (face detection + character matching)
- Объекты (object detection)
- Направление движения
- Тип кадра / coverage
- Эмоциональную интенсивность

**Принцип: крупность — часть автоматического logger layer, не отдельная ручная задача.**

#### Q2.4 — Lore Editing: DAG = canonical, Timeline = fast linking

> Решение (2026-03-18): Canonical editing в DAG Project. Fast contextual linking из Timeline/Inspector.

**В DAG Project** (основное):
Пользователь кликает на character/scene/location/object node и видит/редактирует:
- Biography / notes
- Relations (edges к другим lore nodes)
- Visual references (для генерации)
- Linked scenes (appearances)
- Linked clips
- Motifs / tags

**В Timeline/Inspector** (быстрый доступ):
- Привязать clips к lore node
- Связать clip с участком script spine
- Создать manual semantic bundle

```
Scene 5 (after manual enrichment)
├ linked character lore: Anna
├ linked location lore: Cafe
├ linked object lore: red cup
└ linked selected frames for generation/reference
```

**Feedback loop:** Ручные правки пользователя сохраняются как correction memory →
PULSE/Logger учитывает это как preference при следующих запусках.

#### Q2.5 — Flip Y: START at bottom (confirmed)

> Решение (2026-03-18): Default = START внизу, END вверху. Flip Y = view option, DAG-only.

- **DAG Project:** vertical chronology, START bottom → END top (default)
- **Timeline:** horizontal chronology, standard left-to-right (не меняется)
- **Flip Y:** чистая настройка отображения графа, не влияет на онтологию

---

## 3. Source vs Program Monitor — routing

### 3.1 Целевое состояние (из v1.0 §2.3, §2.4)

```
┌───────────────────┐    ┌───────────────────┐
│  SOURCE MONITOR   │    │  PROGRAM MONITOR  │
│                   │    │                   │
│  Shows: raw clip  │    │  Shows: timeline  │
│  from Project Bin │    │  playback result  │
│  or DAG click     │    │                   │
│                   │    │  Feed: active     │
│  Feed: selected   │    │  timeline output  │
│  individual asset │    │                   │
│                   │    │  Controls:        │
│  Controls:        │    │  transport        │
│  IN/OUT points    │    │  (play/JKL/step)  │
│  favorite markers │    │                   │
│                   │    │  Overlay:         │
│  Below:           │    │  StorySpace mini  │
│  Inspector (PULSE)│    │                   │
└───────────────────┘    └───────────────────┘

SOURCE = LEFT (рядом с DAG/Script)
PROGRAM = RIGHT (результат монтажа)
Стандарт NLE: Premiere Pro, FCP, DaVinci

RULE: Source and Program NEVER show the same feed
```

### 3.2 Routing Logic

| Action | Program Monitor | Source Monitor |
|--------|----------------|---------------|
| Timeline playback | ✅ Shows | — |
| Click clip in Project/DAG | — | ✅ Shows |
| Double-click clip | — | ✅ Loads for IN/OUT |
| Playhead moves on timeline | ✅ Updates | — |
| Click script line | ✅ Jumps to time | ✅ Shows linked raw material |

### 3.3 Inspector под Source Monitor

Spec §2.4: Inspector показывает PULSE analysis для selected clip:
- Camelot key, scale, pendulum
- dramatic_function
- energy_profile
- BPM (audio/visual/script)

Сейчас Inspector = отдельная панель. Нужно: встроить в Source Monitor area (или под ним как tab).

---

## 4. Timeline — параллельный показ

### 4.1 Целевое состояние

**2 таймлайна видны одновременно** (не табы, а stacked):

```
┌─────────────────────────────────────────────────────┐
│ TIMELINE 2 (reference): project_cut-01 (PULSE)       │
│ ░░░░░│░░░░░░░░░│░░░░░│░░░░░│░░░░░░░░                │
├─────────────────────────────────────────────────────┤
│ TIMELINE 1 (active ★): project_cut-02 (Manual)      │
│ ▓▓▓▓▓│▓▓▓▓▓▓▓│▓▓▓│▓▓▓▓▓▓▓▓▓│▓▓▓▓│▓▓▓▓▓▓           │
└─────────────────────────────────────────────────────┘
Tab bar: [cut-00] [cut-01 ★] [cut-02 ★] [cut-03] [+]
         (★ = visible in parallel view)

Default: active (user) timeline ВНИЗУ, reference timeline СВЕРХУ.
Пользователь может менять расположение.
```

**Rules:**
- Active timeline (★) → Program Monitor
- Both timelines scroll together (synced playhead)
- Click on Timeline 2 → it becomes active
- Each timeline = cut_N version in Project DAG
- Drag from Tab bar → swap into parallel view

### 4.2 Версионирование

Каждая версия = нода в DAG Project (верхний уровень):
- `cut-00`: First assembly (Logger output)
- `cut-01`: PULSE auto-montage (Favorites mode)
- `cut-02`: Manual editor adjustments
- `cut-03`: PULSE Script-driven variant
- ...

**RULE: Auto-montage ALWAYS creates new cut-NN. NEVER overwrites.**

### ✅ РЕШЕНО: Timeline diff view (Q6)

> Решение (2026-03-18): Вариант C. Параллельный показ = и есть diff.

Два таймлайна stacked — уже достаточный визуальный diff.
Отдельный цветовой overlay (зелёный/красный/жёлтый) НЕ нужен в core architecture.

**Почему:** В монтаже сравнение = ритм, плотность, порядок сцен, длительность.
Это лучше читается глазом по самим таймлайнам, чем по code-diff оверлеям.

Experimental overlay можно добавить позже, но не в MVP.

---

## 5. BPM System — уточнения

### 5.1 Что работает
- Audio BPM (green) — librosa
- Visual BPM (blue) — FFmpeg scene detection
- Script BPM (white) — event density
- Orange sync (2-3 sources align ±2 frames)

### 5.2 ✅ Script BPM — Hybrid Model (Symbolic + JEPA)

> Решение (2026-03-18): Script BPM = не только rule-based.
> Два слоя: symbolic event density + semantic energy spikes.
> BPM = точка встречи Circuit A (symbolic) и Circuit B (learned).

**Layer A — Symbolic Script BPM (rule-based, дешёвый baseline):**
```
script_bpm = (event_count_in_page / 1.0) * 60
// event = scene heading, new character speaks, stage direction, CUT TO
```
- Густой диалог (короткие реплики) = высокий script BPM
- Длинное описание = низкий script BPM
- Считается по сценарию без GPU

**Layer B — Learned Event Energy (JEPA / embeddings):**
- Резкая смена состояния в тексте/видео → energy spike
- Неожиданное действие → semantic vector shift
- Пример: спокойный диалог → внезапно въехал грузовик = не просто "новая строка",
  а реальный energy spike, который rule-based не поймает

**Итоговая формула:**
```
script_bpm_final = combine(
  symbolic_event_density,       // Layer A
  semantic_vector_shift,        // Layer B
  optional_jepa_energy_spike    // Layer B (multimodal)
)
```

**Архитектурная связь:** Это прямая реализация принципа двухконтурности из конституции v1.0:
Circuit A (symbolic/editorial) + Circuit B (learned/perceptual) → BPM = место их встречи.

---

## 6. Marker System — целевое

4 типа маркеров одновременно:

| Тип | Позиция | Цвет | Export | Статус |
|-----|---------|------|--------|--------|
| Standard | Top ruler | User picks | Premiere XML, EDL | ❌ UI нет |
| BPM | Bottom BPM track | Green/Blue/White/Orange | pulse_markers.json | ✅ |
| Favorite-time | На clip в Source Monitor | Dedicated color | SRT | ❌ UI нет |
| PULSE scene | Script + timeline | Amber | pulse_scenes.json | ⚠️ Backend only |

### ✅ РЕШЕНО: Favorite markers UX (Q7)

> Решение (2026-03-18): Hotkey-first. M = positive, N = negative, MM = comment.

**Базовые hotkeys:**
- **M** = positive / favorite marker ("оставить / нравится / важный момент")
- **N** = negative marker / reject ("нежелательно / убрать / плохой дубль")
- **MM** (double-tap) = marker + открыть текстовый комментарий

**Почему M, а не F:** F культурно ассоциирован с fullscreen/find/fit. M = marker — естественно.

**Формат данных:**
```
marker_type: favorite_positive | favorite_negative | note | standard
marker_time: timecode
marker_text: optional comment
marker_source: user | pulse_auto
```

**Семантика для агентов:** Favorite markers = collective memory (из конституции v1.0).
PULSE использует positive markers для взвешивания при auto-montage (Favorites mode).

---

## 7. Auto-Montage — UI для backend

### 7.1 Backend готов
- `pulse_auto_montage.py`: 3 режима (Favorites/Script/Music)
- Safety: always creates new timeline
- PULSE conductor + critics evaluate result

### 7.2 Нужен Frontend

**Минимум:**
- Кнопка/меню: "PULSE → Assemble Favorites / Script-driven / Music-driven"
- Progress indicator на DAG (пульсирующие ноды)
- Результат = новый tab в Timeline

### 7.3 Agent visualization

Spec §7.3: "DAG project panel shows agent activity: pulsing nodes, edges lighting up, nodes turn green."

Визуализация PULSE assembly на DAG — важна, но не в MVP.
Минимум для начала: progress bar + результат = новый tab в Timeline.
Пульсирующие ноды / lighting edges — Phase 4+.

---

## 8. Layout — default + persistence

### 8.1 Default Layout

✅ РЕШЕНО (Q9)

> Ответ Данилы (2026-03-18):
> - Program Monitor — СПРАВА (timeline playback result)
> - Source Monitor — СЛЕВА (рядом с DAG Project / Script panel)
> - Timeline — ВНИЗУ (пользовательский таймлайн всегда внизу по умолчанию)
> - Всё перемещаемо: "где и как хочет пользователь, но по умолчанию так"

```
┌──────────┬──────────┬─────────────────────┐
│ Script   │ Source   │                     │
│  (tab)   │ Monitor  │  Program Monitor    │
│──────────│──────────│                     │
│ DAG      │Inspector │  [StorySpace mini]  │
│ project  │ (PULSE)  │                     │
│  (tab)   │          │                     │
├──────────┴──────────┴─────────────────────┤
│ Timeline (full width, user timeline)       │
│ [cut-00] [cut-01 ★] [cut-02 ★] [+]       │
│ ▓▓▓▓│▓▓▓▓▓│▓▓▓│▓▓▓▓▓│▓▓▓▓▓│▓▓▓          │
│ ░░░░│░░░░░│░░░│░░░░░│░░░░░│░░░           │
└────────────────────────────────────────────┘
```

**Логика расположения:**
- Source Monitor рядом с DAG/Script — кликнул на ноду/строку → сразу видишь материал рядом
- Program Monitor справа — как результат работы, как Premiere-style
- Inspector под Source Monitor — PULSE данные для выбранного clip
- Timeline внизу — full width, stacked parallel view

---

## 9. ✅ Приоритеты реализации (Q10 — утверждено)

> Решение (2026-03-18): Общий порядок правильный.
> Ключевое уточнение: Logger enrichment = часть раннего core, не polish.
> Без хорошего logger layer PULSE будет монтировать "из мусора".

```
Phase 1: ROUTING + SCRIPT SPINE (foundation)
  → Source vs Program isolation (GAP-2) — critical bug fix
  → Screenplay-aware chunker (scene-based + page-timer)
  → Script chunks = scene nodes in DAG
  → DAG Y-axis = film chronology (GAP-1, GAP-4)
  → Click any node → Source Monitor shows it

Phase 2: LOGGER ENRICHMENT (DAG grows flesh)
  → Scene-material linking (clips → SCN_XX)
  → Shot scale auto-detection (vision model)
  → Characters/objects detection
  → Lore nodes: characters, locations, items
  → Screenplay import: Fountain, FDX, PDF, DOCX

Phase 3: PARALLEL TIMELINES
  → 2 timelines visible simultaneously (GAP-3)
  → cut_N versioning linked to DAG
  → Tab ↔ parallel swap
  → Active timeline BOTTOM, reference TOP

Phase 4: AUTO-MONTAGE UI
  → Frontend for 3 modes (GAP-5)
  → Agent visualization on DAG (pulsing nodes)
  → New timeline creation flow
  → Reverse dependency: click scene → show alternatives

Phase 5: MARKERS & IN/OUT
  → Favorite markers: M (positive), N (negative), MM (comment)
  → Standard markers on ruler
  → Three-point editing in Source Monitor
  → SRT export

Phase 6: BPM & POLISH
  → Script BPM hybrid (symbolic + JEPA energy spikes)
  → JKL shuttle + frame step
  → Drag-to-dock
  → Layout persist to project file

Phase 7: FUTURE / GENERATIVE
  → Effects node graph
  → Documentary mode (footage → reconstructed script)
  → Bridge layer (Circuit A ↔ Circuit B full bidirectional)
  → Multiverse DAG advanced UI (branch visualization)
  → Interactive lore tokens in script text
```

---

## 10. Summary: ВСЕ ВОПРОСЫ ЗАКРЫТЫ ✅

**Дата завершения:** 2026-03-18
**Все 10 вопросов + 5 подвопросов = решено.**

| # | Тема | Решение |
|---|------|---------|
| Q1 | Chunking | Гибридный (scene headings → fallback абзацы) + page-timer (1 page = 60 sec) + manual drag-split |
| Q2 | DAG canonical model | Three-Level Architecture: Script Spine → DAG/Logger → Timeline Projections |
| Q2.1 | Storylines | Script spine в центре + storyline branches по X (партитура). Не деревья, не тэги |
| Q2.2 | Script drafts | Multiverse DAG: все варианты в одном графе. Мердж по чанкам. Timeline = выбранный путь |
| Q2.3 | Shot scale | Automatic-first (vision/JEPA). Manual = override. Оба значения сохраняются |
| Q2.4 | Lore editing | Canonical в DAG Project. Fast contextual linking из Timeline/Inspector. Feedback loop |
| Q2.5 | Flip Y | START bottom, END top (default). Flip Y = view option, DAG-only |
| Q4 | Node metadata | Полная структура: scene/media/lore nodes. Лор = кликабельные токены в сценарии |
| Q5 | Scene click | Живой узел: лучший clip + все takes + лор + PULSE metadata |
| Q6 | Timeline diff | Вариант C: параллельный показ = и есть diff. Без цветового overlay |
| Q7 | Favorite UX | Hotkey-first: M = positive, N = negative, MM = comment |
| Q8 | PULSE Assembly | Logger → Selection → Assembly → Editor. PULSE поверх DAG, не из пустоты |
| Q9 | Layout | Source LEFT (рядом с DAG), Program RIGHT, Timeline BOTTOM |
| Q10 | Priorities | Logger enrichment = ранний core. 7 фаз утверждены |
| BPM | Script BPM | Hybrid: symbolic event density + JEPA semantic energy spikes |

---

## 11. Каноническая формула CUT (финальная)

> **Script defines the film spine.**
> **DAG Project grows media, lore, and semantics around that spine.**
> **Timeline is a horizontal projection of the DAG.**
> **PULSE assembles the first rough cut from the DAG.**
> **The editor refines it into the final film.**

> **DAG Project stores the multiverse of the film.**
> **Timeline is the currently chosen universe.**
> **A scene on the timeline is never final; it is always a projection of a richer graph node.**

> **Construction (script → film) and reconstruction (footage → script) are symmetric operations inside one project graph.**
