# RECON: v1.0 Spec vs Codebase
# VETKA CUT Interface Architecture — Gap Analysis

**Date:** 2026-03-17
**Source of truth:** `VETKA_CUT_Interface_Architecture_v1.docx` (2026-03-14)
**Codebase snapshot:** `vetka_live_03` @ 2026-03-17

---

## 1. Seven Panels — Status

### 1.1 Script Panel

| Spec | Code | Status |
|------|------|--------|
| Y=time (vertical, chat-like) | ScriptPanel.tsx (333 строк) | ✅ |
| 1 line ≈ 1 minute (Courier 12pt) | Фиксированный 4 сек/строка | ⚠️ Не привязан к реальному хрон |
| Click line → sync all panels | `usePanelSyncStore.syncFromScript()` | ✅ |
| Teleprompter auto-scroll | Реализован при playback | ✅ |
| BPM display (3 цветных точки) | Отображает audio/visual/script BPM | ✅ |
| Documentary mode (media→transcript→script) | — | ❌ Не реализован |
| Fountain/FDX парсинг | — | ❌ Не реализован |
| DAG mode toggle | — | ❌ Не реализован |
| Script BPM = events per page | Равномерное распределение | ⚠️ Считает линейно, не по событиям |

**Ключевые файлы:** `client/src/components/cut/ScriptPanel.tsx`

---

### 1.2 DAG Project Panel

| Spec | Code | Status |
|------|------|--------|
| Y=time (bottom=00:00, top=end) | Кластерные колонки, НЕ хрон | ❌ КРИТИЧЕСКИЙ |
| Кластеры: Character/Location/Take/Dub/Music/SFX/Graphics | 8 типов реализованы | ✅ |
| Click node → source monitor показывает ассет | `syncFromDAG()` | ✅ |
| Blue glow для linked nodes | Реализовано (MARKER_180.16) | ✅ |
| Bidirectional linking (DAG↔Script) | DAG→Script отсутствует | ❌ |
| Lore clusters (character bio, location history) | — | ❌ |
| Merge из разных источников | — | ❌ |
| ReactFlow визуализация | Да | ✅ |

**КРИТИЧЕСКИЙ ГЭП:** Y-ось сейчас = кластерные колонки. По спеку Y = хрон фильма (снизу вверх). Кластеры должны быть по X.

**Ключевые файлы:** `client/src/components/cut/DAGProjectPanel.tsx`, `src/api/routes/cut_routes.py`

---

### 1.3 Program Monitor

| Spec | Code | Status |
|------|------|--------|
| Правая сторона | Да, right_top в layout | ✅ |
| Timeline playback | HTML5 video | ✅ |
| Story Space mini-panel (120×80px) | StorySpace3D с toggleMini | ✅ |
| Timecode display | HH:MM:SS | ✅ |
| Transport: play/pause/JKL/frame step | Play/pause есть, JKL/frame step нет | ⚠️ |
| Favorite markers на scrubber | — | ❌ |
| НЕ показывает Source material | Нет изоляции, показывает то же что Source | ❌ КРИТИЧЕСКИЙ |

**Ключевые файлы:** `client/src/components/cut/VideoPreview.tsx`, `CutEditorLayoutV2.tsx`

---

### 1.4 Source Monitor

| Spec | Code | Status |
|------|------|--------|
| Ниже Program (или side-by-side) | Left_top в текущем layout | ⚠️ Позиция другая |
| Raw material preview | Через VideoPreview | ⚠️ Общий компонент |
| Inspector ниже видео (PULSE data) | Inspector — отдельная панель | ❌ |
| IN/OUT points для 3-point editing | — | ❌ |
| Favorite-time markers | — | ❌ |
| Изоляция от Program Monitor | Оба показывают одно видео | ❌ КРИТИЧЕСКИЙ |

**Ключевые файлы:** `client/src/components/cut/SourceBrowser.tsx`

---

### 1.5 Timeline Panel

| Spec | Code | Status |
|------|------|--------|
| X=time (horizontal) | Да | ✅ |
| V1/V2, A1/A2 tracks | V1-V3, A1+, AUX | ✅ |
| BPM track (4 ряда цветных точек) | BPMTrack.tsx | ✅ |
| Standard markers (top ruler) | — | ❌ |
| Multi-timeline tabs | TimelineTabBar.tsx | ✅ |
| Параллельный показ 2 таймлайнов | Только табы, НЕ одновременно | ❌ КРИТИЧЕСКИЙ |
| Detachable (FCP7 style) | Layout поддерживает detach | ⚠️ Drag UI нет |
| DAG mode toggle (scene graph) | — | ❌ |
| Versioning: {project}_cut-{NN} | Частично | ⚠️ |
| Timeline diff view | — | ❌ |

**Ключевые файлы:** `client/src/components/cut/TimelineTrackView.tsx`, `BPMTrack.tsx`, `TimelineTabBar.tsx`

---

### 1.6 Story Space 3D

| Spec | Code | Status |
|------|------|--------|
| Camelot wheel (12 keys, horizontal plane) | Three.js + R3F | ✅ |
| McKee triangle (vertical axis) | Barycentric coordinates | ✅ |
| Scene dots (pendulum color, energy size) | Реализовано | ✅ |
| Trajectory line | Реализовано | ✅ |
| Floating mini-panel (120×80px) | toggleMini() | ✅ |
| Click dot → sync all panels | usePanelSyncStore | ✅ |
| BPM pulse at center | — | ❌ Minor |

**Статус:** ✅ Полностью реализовано

**Ключевые файлы:** `client/src/components/cut/StorySpace3D.tsx`, `src/services/pulse_story_space.py`

---

### 1.7 Effects / Node Graph Panel

| Spec | Code | Status |
|------|------|--------|
| DaVinci Fusion-style nodes | — | ❌ |
| Color correction, transitions | — | ❌ |
| PULSE-driven effects | — | ❌ |

**Статус:** ❌ Не реализовано. Placeholder в layout store (`visible: false`).
**Приоритет:** Низкий (Phase 5 в build order по спеку §14).

---

## 2. Backend Systems — Status

| Система | Файлы | Строк | Тесты | Статус |
|---------|-------|-------|-------|--------|
| PULSE Conductor | pulse_conductor.py | 458 | ✅ 152+ | ✅ Полностью |
| Energy Critics (5) | pulse_energy_critics.py | 400 | ✅ | ✅ Полностью |
| Camelot Engine | pulse_camelot_engine.py | ~300 | ✅ | ✅ Полностью |
| Cinema Matrix (26 scales) | pulse_cinema_matrix.py | 705 | ✅ | ✅ Полностью |
| Story Space | pulse_story_space.py | ~200 | ✅ | ✅ Полностью |
| Script Analyzer | pulse_script_analyzer.py | ~300 | ✅ | ✅ Работает |
| Auto-Montage (3 modes) | pulse_auto_montage.py | ~400 | ✅ | ✅ Backend ready |
| SRT Bridge | pulse_srt_bridge.py | ~150 | ✅ | ✅ |
| Scene Detector (video) | cut_scene_detector.py | ~200 | ✅ | ✅ FFmpeg |
| Text Chunker | text_chunker.py | ~150 | ✅ | ✅ |
| Project Schema | project_vetka_cut_schema.py | ~100 | ✅ | ✅ |

**Вывод:** Backend PULSE = ~3500 строк, 152+ тестов, полностью готов. Frontend Auto-Montage UI = 0.

---

## 3. Frontend Systems — Status

| Система | Файлы | Статус |
|---------|-------|--------|
| Panel Sync | usePanelSyncStore.ts (176 строк) | ✅ Полная матрица 7×5 |
| Layout (dock/tab/float) | usePanelLayoutStore.ts + PanelGrid + PanelShell | ✅ Основа работает |
| BPM Track | BPMTrack.tsx | ✅ 4 ряда точек |
| Waveform | WaveformCanvas.tsx | ✅ |
| Transport | TransportBar.tsx | ⚠️ Базовый (нет JKL) |
| SVG Icons | 80+ иконок | ✅ По спеку |
| Dark Theme | По спеку §11 | ✅ |

---

## 4. Критические гэпы — RED LEVEL

### GAP-1: DAG Project — Y-ось ≠ хрон
**Spec §2.2:** Y = time in MCC/VETKA style (bottom=start, top=latest)
**Code:** Y = кластерные колонки (Character/Location/Take...)
**Impact:** Фундаментально меняет визуализацию проекта. Сценарий должен быть осью Y, медиа — привязано к точкам на оси Y.

### GAP-2: Source vs Program Monitor — нет изоляции
**Spec §2.3, §2.4:** Source = raw clip из Project Bin. Program = timeline playback. "Source and Program NEVER show the same feed."
**Code:** Оба используют один VideoPreview, нет routing logic.
**Bug:** tb_1773714867_26

### GAP-3: Параллельный показ 2 таймлайнов
**Spec §2.5:** "View 2+ timelines at once (FCP 7 style)". Simultaneous view для сравнения cut_1 vs cut_2.
**Code:** Только табы. Одновременно виден только 1 таймлайн.

### GAP-4: Script как корень DAG
**Spec §0.3, §14:** "Script is the spine. Material links to script."
**Code:** Script panel и DAG project — параллельные табы. Нет иерархии: script chunks → scene nodes → media assets.

### GAP-5: Auto-Montage Frontend
**Spec §7:** 3 режима (Favorites/Script/Music), safety rules, agent visualization.
**Code:** Backend 100% ready. Frontend = 0. Нет кнопок, нет UI, нет визуализации процесса.

---

## 5. Средние гэпы — YELLOW LEVEL

| # | Гэп | Spec | Code |
|---|-----|------|------|
| Y-1 | Screenplay import (Fountain/FDX) | §2.1 | Только raw text |
| Y-2 | Documentary mode (media→script) | §2.1, §12.1 | Не реализован |
| Y-3 | Three-point editing (IN/OUT) | §2.4 | Нет UI |
| Y-4 | Favorite markers UI | §6 | Backend dataclass, нет frontend |
| Y-5 | Standard markers on timeline ruler | §6 | Нет UI |
| Y-6 | Layout drag-to-dock UI | §1 | Инфраструктура есть, нет drag |
| Y-7 | Timeline DAG mode | §8 | Нет toggle |
| Y-8 | Script DAG mode | §8 | Нет toggle |
| Y-9 | JKL shuttle + frame step | §2.3 | Нет в transport |
| Y-10 | Layout persist to disk | §3 | save/load не привязаны к файлу |
| Y-11 | Bridge layer (Symbolic↔JEPA) | §0.2 | Частично, не как единая система |
| Y-12 | Script BPM по событиям (не линейный) | §5.3 | Линейный расчёт |

---

## 6. Что хорошо работает — GREEN LEVEL

1. **PULSE backend** — conductor, critics, camelot, cinema matrix, story space (~3500 строк, 152+ тестов)
2. **Panel sync matrix** — click на любой панели каскадит обновления ко всем
3. **BPM track** — 4 ряда цветных точек с orange sync markers
4. **StorySpace 3D** — Camelot × McKee × trajectory, floating mini-panel
5. **Layout system** — dock/tab/float инфраструктура, 6 dock positions
6. **Timeline** — tracks, ruler, playhead, clips, waveforms, snap-to-grid, zoom
7. **SVG icons + dark theme** — 80+ иконок, все по спеку §11
8. **Project schema** — Pydantic validation, timeline versions, PULSE config
9. **Text chunker** — hierarchical splitting, overlap-aware (для script chunks)
10. **Scene detector** — FFmpeg-based video scene boundaries

---

## 7. Script Chunking & Import — Detailed Status

| Возможность | Статус | Где |
|-------------|--------|-----|
| Text chunking (general) | ✅ | text_chunker.py (max_chars=3000, overlap) |
| Scene heading detection (INT./EXT./ИНТ./НАТ.) | ✅ | pulse_script_analyzer.py (regex) |
| Bilingual (EN+RU) | ✅ | Ключевые слова обоих языков |
| Fountain format (.fountain) | ❌ | Не реализован |
| FDX format (.fdx) | ❌ | Не реализован |
| DOCX import | ❌ | Не реализован |
| PDF import | ✅ | ocr_processor.py (text + OCR) |
| Courier 12pt → page timing (1 page = 60 sec) | ❌ | Нет |
| Scene-aware chunking (split by scene headings) | ❌ | chunker не знает о сценах |
| Script chunks → DAG nodes | ❌ | Нет связи |

**Вывод:** Есть generic chunker и scene heading detector, но они не связаны. Нужен screenplay-aware chunker, который разбивает по сценам и привязывает чанки к хрону (через правило Courier 12pt = 1 page/60 sec).

---

## 8. Workflow Pipeline — Status

v1 spec подразумевает 5-стадийный pipeline: `IMPORT → LOGGER → PULSE → MONTAGE → EXPORT`

| Стадия | Статус | Детали |
|--------|--------|--------|
| IMPORT | ✅ Реализовано | Bootstrap pipeline, folder import, proxy generation |
| LOGGER | ❌ **Отсутствует** | Нет script-to-scene assignment, нет clip-to-scene matching |
| PULSE | ⚠️ Backend ready, UI partial | Backend compute ready; нет scene-scoped UI display |
| MONTAGE | ⚠️ Backend ready, UI = 0 | Auto-montage engine есть; multi-timeline display нет |
| EXPORT | ✅ Реализовано | Premiere XML (XMEML v5), FCPXML v1.10, EDL, SRT |

**Главная дыра = LOGGER** — стадия где clips привязываются к scene nodes из script.

---

## 9. Детальные метрики кодовой базы

### Frontend CUT Components
| Файл | Строк | Комментарий |
|-------|-------|-------------|
| TimelineTrackView.tsx | ~60K | Монолит — drag, trim, render, tracks |
| TransportBar.tsx | ~23K | Play/pause/export |
| SourceBrowser.tsx | ~18K | Legacy, заменяется ProjectPanel |
| CamelotWheel.tsx | ~9.5K | SVG 2D для Inspector |
| StorySpace3D.tsx | ~482 | Three.js полная визуализация |
| PanelShell.tsx | ~377 | Dock/float/mini framework |
| ScriptPanel.tsx | ~332 | Y-time display + teleprompter |
| DAGProjectPanel.tsx | ~321 | ReactFlow + cluster layout |
| PulseInspector.tsx | ~330 | Camelot + McKee + pendulum |
| BPMTrack.tsx | ~320 | Canvas 4-row dots |
| ClipInspector.tsx | ~269 | Per-clip metadata display |
| CutEditorLayoutV2.tsx | ~276 | Grid layout master |
| PanelGrid.tsx | ~255 | CSS Grid + resize borders |

### Backend PULSE Services
| Файл | Строк | Тесты |
|-------|-------|-------|
| pulse_conductor.py | ~458 | ✅ 152+ |
| pulse_cinema_matrix.py | ~705 | ✅ |
| pulse_auto_montage.py | ~400 | ✅ |
| pulse_energy_critics.py | ~400 | ✅ |
| pulse_camelot_engine.py | ~300 | ✅ |
| pulse_script_analyzer.py | ~300 | ✅ |
| pulse_story_space.py | ~200 | ✅ |
| pulse_srt_bridge.py | ~150 | ✅ |
| pulse_timeline_bridge.py | — | ✅ |

### Zustand Stores
| Store | Назначение |
|-------|-----------|
| useCutEditorStore.ts | Master state: clips, tracks, playhead |
| usePanelSyncStore.ts (176 строк) | Полная матрица 7×5 синхронизации |
| usePanelLayoutStore.ts | Dock/tab/float state, panel visibility |

---

## 10. Source vs Program Monitor — BUG CONFIRMED

**В `CutEditorLayoutV2.tsx` (lines 69-103):** оба монитора рендерят один и тот же `<VideoPreview />` с одним и тем же `activeMediaPath`. Нет routing logic для разделения source feed vs timeline feed.

**Bug ID:** tb_1773714867_26
**Impact:** Критический — нарушает базовый NLE workflow (source = raw, program = assembled).

---

## 11. Q1 РЕШЁН — Chunking Strategy

**Дата:** 2026-03-17
**Решение:** Гибридный (Вариант B) + page-timer + manual override.
**Детали:** См. CUT_TARGET_ARCHITECTURE.md §1.2

Ключевые моменты от Данилы:
- Время = хрон сценария, НЕ дата создания
- 1 страница Courier 12pt = 1 минута (стандарт)
- Чанки должны быть видны и кликабельны даже если разбиение неидеальное
- Fountain/FDX поддержка через open-source парсеры (afterwriting-labs, Jouvence)
- Затраты: 1-2 дня, ~150 строк `screenplay_timing.py`
