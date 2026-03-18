# RECON: CUT UI Cleanup
# Что удалить, что переместить, что переименовать

**Date:** 2026-03-18
**Basis:** Скриншоты Данилы + Premiere Pro / Avid reference + CUT_NLE_UNIVERSAL_ACTION_REGISTRY.md
**Принцип:** Монтажёр хочет видеть ВИДЕО и АУДИО на таймлайне. Всё остальное — мешает.

---

## 1. ПРОБЛЕМЫ (по скриншотам)

### P1: Два Program Monitor вместо Source + Program
- **Что видим:** center + right_top оба говорят "Program Monitor", оба "Select a clip to preview"
- **Как должно быть (Premiere/Avid):**
  - СЛЕВА = Source Monitor (raw clip из bin/DAG, со своим мини-скраббером)
  - СПРАВА = Program Monitor (таймлайн playback, со своим мини-скраббером)
- **Каждый монитор имеет:**
  - Свой video player
  - Свой scrubber (мини-таймлайн) ПОД видео
  - Свой transport (Play/JKL) ПОД скраббером
  - Свой timecode display
  - IN/OUT buttons (Source) или timeline position (Program)
- **Файл:** `CutEditorLayoutV2.tsx` строки 89-104 — right_top рендерит дублирующий Program Monitor

### P2: Transport Bar привязан к Timeline, а не к мониторам
- **Что видим:** Play/Stop/Skip + timecode + IN/OUT + "1x" + кнопки — все живут НАД таймлайном
- **Как должно быть:** Transport controls = часть КАЖДОГО монитора (под video)
- **Timeline toolbar** = минимальный: snap toggle (S), zoom slider, track height — и ВСЁ
- **Файл:** `TransportBar.tsx` (671 строк) — нужно разделить на MonitorTransport + TimelineToolbar

### P3: Кнопка "Scenes" (ножницы) — непонятная
- **Что видим:** Фиолетовая обводка на кнопку "✂ Scenes" в toolbar Timeline
- **Проблема:** Это scene detection? Razor tool? Непонятно даже монтажёру
- **Решение:**
  - Если scene detection → убрать из toolbar, это AI операция (меню или Cmd+D)
  - Razor = hotkey **C** (по Action Registry #79 `tool_razor`), НЕ кнопка
  - Все tool switches = hotkeys, НЕ кнопки (V/A/B/N/C/Y/U/H/Z — по Registry §6)

### P4: StorySpace 3D мешает видеть треки
- **Что видим:** Зелёная обводка — StorySpace висит поверх правой части таймлайна
- **Решение:** Mini-panel в углу Program Monitor (как сейчас задумано, но не работает) ИЛИ отдельный tab в Inspector area

### P5: Лишние кнопки в toolbar загрязняют интерфейс
- **Что видим:** Жёлтые X — ряд кнопок справа (zoom buttons, grid icon, ещё что-то)
- **Принцип Данилы:** "Удалить вообще все кнопки. Убирал всё что мешает видеть отрезки"
- **Решение:** Timeline toolbar = ТОЛЬКО:
  - Snap toggle (иконка магнита, hotkey S)
  - Zoom slider (горизонтальный, как в Premiere)
  - Linked selection toggle (иконка цепочки)
  - Ничего больше. Всё остальное = hotkeys.

### P6: Layout не соответствует Premiere standard
- **Как должно быть (из скриншотов Premiere):**
```
┌──────────────┬──────────────┐
│   SOURCE     │   PROGRAM    │
│  [video]     │  [video]     │
│  [scrubber]  │  [scrubber]  │
│  [transport] │  [transport] │
├──────────────┼──────────────┤
│   PROJECT    │  INSPECTOR   │
│   (media     │  (Script/    │
│    bin)      │   DAG/PULSE) │
├──────────────┴──────────────┤
│   TIMELINE (full width)     │
│   [tab bar: cut-00 cut-01]  │
│   [tracks]                  │
│   [BPM track]               │
└─────────────────────────────┘
```

---

## 2. ЧТО УДАЛИТЬ

### 2.1 Файлы-кандидаты на удаление

| Файл | Строк | Причина | Решение |
|------|-------|---------|---------|
| `CutEditorLayout.tsx` | 799 | Legacy layout, заменён CutEditorLayoutV2 | **УДАЛИТЬ** если нигде не импортируется |
| `SourceBrowser.tsx` | 540 | Legacy media browser, заменён ProjectPanel | **УДАЛИТЬ** если нигде не импортируется |

### 2.2 UI элементы для удаления из TransportBar

Текущий `TransportBar.tsx` (671 строк) содержит:
- Play/Pause/Stop/Skip → **ПЕРЕНЕСТИ** в MonitorTransport (под каждый монитор)
- Timecode display → **ПЕРЕНЕСТИ** в MonitorTransport
- IN / OUT textfields → **ПЕРЕНЕСТИ** в Source Monitor transport
- "1x" speed display → **ПЕРЕНЕСТИ** в MonitorTransport
- Кнопка "Scenes" (ножницы) → **УДАЛИТЬ** (scene detection = меню/Cmd+D, razor = hotkey C)
- Export кнопки → **ПЕРЕНЕСТИ** в меню File > Export
- Все остальные кнопки → **УДАЛИТЬ или перенести в hotkeys**

### 2.3 Кнопки Timeline toolbar — удалить/оставить

| Элемент | Решение | Почему |
|---------|---------|--------|
| Snap toggle (S) | ОСТАВИТЬ (иконка магнита) | Единственная визуально нужная кнопка |
| Zoom slider | ОСТАВИТЬ (горизонтальный) | Нужен для мыши, но можно и +/- hotkeys |
| Linked selection | ОСТАВИТЬ (иконка цепи) | Premiere стандарт |
| Все остальные кнопки | УДАЛИТЬ | Hotkeys: V, C, B, N, Y, U, H, Z |
| Grid icon | УДАЛИТЬ | Зачем? |
| Scene detection button | УДАЛИТЬ | Cmd+D или меню |

---

## 3. ЧТО СОЗДАТЬ / ПЕРЕСТРОИТЬ

### 3.1 MonitorTransport — новый компонент
- **Файл:** `MonitorTransport.tsx` (~150 строк)
- **Рендерится:** ПОД video в каждом мониторе (Source и Program)
- **Содержит:**
```
┌─────────────────────────────────────────────┐
│ [scrubber bar — мини-таймлайн всего клипа]  │
│ TC: 00:01:23:15  DUR: 00:04:10:00   Fit ▼  │
│ ◄◄  ◄  ▶  ►  ►►    [IN] [OUT]    1/2  ▼   │
└─────────────────────────────────────────────┘
```
- **Source Monitor:** IN/OUT кнопки видны, Mark Clip кнопка
- **Program Monitor:** IN/OUT скрыты, показывает timeline position
- **Размер:** Компактный, ~60px высота максимум

### 3.2 TimelineToolbar — минимальный
- **Файл:** Упрощённый `TransportBar.tsx` → переименовать в `TimelineToolbar.tsx` (~100 строк)
- **Содержит ТОЛЬКО:**
```
┌───────────────────────────────────────────┐
│ 🔗  🧲(S)  ────────[zoom slider]──────── │
└───────────────────────────────────────────┘
```
- Linked selection toggle
- Snap toggle (S)
- Zoom slider (horizontal)
- Ничего больше. Может вообще быть частью tab bar.

### 3.3 Layout refactor: 4 зоны вместо 6
- **Текущий:** 6 dock positions (left_top, left_bottom, center, right_top, right_bottom, bottom)
- **Целевой:** 4 зоны (как Premiere):
```
source_monitor  |  program_monitor     ← верхняя половина
project_panel   |  inspector_tabs      ← средняя (ИЛИ tabs с Source/Program)
timeline                               ← нижняя (full width)
```
- **Или оставить 6, но правильно назначить:**
  - left_top = Source Monitor (с MonitorTransport)
  - right_top = Program Monitor (с MonitorTransport)
  - left_bottom = Project Panel
  - right_bottom = Inspector (tabs: Inspector / Script / DAG)
  - bottom = Timeline (TimelineToolbar + TabBar + Tracks + BPM)
  - center = НЕ НУЖЕН (убрать дублирующий Program Monitor)

---

## 4. ACTION REGISTRY → CUT HOTKEY MAP

На основе `CUT_NLE_UNIVERSAL_ACTION_REGISTRY.md` (115 actions).
Выделяю то, что нужно для MVP (Tier 1 + частично Tier 2).

### 4.1 Tier 1 — Must have (без них не NLE)

**Playback (привязаны к АКТИВНОМУ монитору, не к timeline):**

| Hotkey | Action ID | Что делает | Статус в коде |
|--------|-----------|-----------|---------------|
| Space | `play_pause` | Play/Pause | Есть (TransportBar) |
| J | `shuttle_back` | Reverse playback | НЕТ |
| K | `stop` | Stop | НЕТ |
| L | `shuttle_forward` | Forward playback | НЕТ |
| JJ | `shuttle_back_fast` | 2x reverse | НЕТ |
| LL | `shuttle_forward_fast` | 2x forward | НЕТ |
| Left | `frame_step_back` | -1 frame | НЕТ |
| Right | `frame_step_forward` | +1 frame | НЕТ |
| Shift+Left | `frame_step_back_5` | -5 frames | НЕТ |
| Shift+Right | `frame_step_forward_5` | +5 frames | НЕТ |
| Home | `go_to_start` | Go to start | НЕТ |
| End | `go_to_end` | Go to end | НЕТ |
| Up | `go_to_prev_edit` | Previous edit point | НЕТ |
| Down | `go_to_next_edit` | Next edit point | НЕТ |

**Marking (работают в Source Monitor):**

| Hotkey | Action ID | Что делает | Статус |
|--------|-----------|-----------|--------|
| I | `mark_in` | Set IN point | Поле есть, hotkey НЕТ |
| O | `mark_out` | Set OUT point | Поле есть, hotkey НЕТ |
| Opt+I | `clear_in` | Clear IN | НЕТ |
| Opt+O | `clear_out` | Clear OUT | НЕТ |
| Opt+X | `clear_in_out` | Clear both | НЕТ |
| X | `mark_clip` | Mark clip under playhead | НЕТ |
| M | `add_marker` | Add marker | НЕТ |

**Editing (работают когда focus = Timeline):**

| Hotkey | Action ID | Что делает | Статус |
|--------|-----------|-----------|--------|
| Cmd+Z | `undo` | Undo | Backend есть (cut_undo_redo.py), UI нет |
| Cmd+Shift+Z | `redo` | Redo | Backend есть, UI нет |
| Delete | `delete_clip` | Delete selected | НЕТ |
| Opt+Delete | `ripple_delete` | Ripple delete | НЕТ |
| , (comma) | `insert_edit` | Insert from source | НЕТ |
| . (period) | `overwrite_edit` | Overwrite from source | НЕТ |
| Cmd+K | `split_clip` | Razor at playhead | НЕТ (кнопка "Scenes" ≠ это) |
| S | `snap_toggle` | Toggle snapping | Кнопка есть, hotkey НЕТ |

**Tools:**

| Hotkey | Action ID | Что делает | Статус |
|--------|-----------|-----------|--------|
| V | `tool_selection` | Arrow/selection tool | НЕТ |
| C | `tool_razor` | Razor/blade tool | НЕТ |

### 4.2 CUT-Specific extensions (наши)

| Hotkey | Action ID | Что делает | Приоритет |
|--------|-----------|-----------|-----------|
| M | `fav_marker_positive` | Positive marker (favorite) | Phase 6 |
| N | `fav_marker_negative` | Negative marker (reject) | Phase 6 |
| MM | `fav_marker_comment` | Marker + comment dialog | Phase 6 |
| Cmd+D | `scene_detect` | Run AI scene detection | Phase 5 |
| ~ | `maximize_panel` | Maximize/restore panel | Phase 7 |
| F | `match_frame` | Match source ↔ timeline | Phase 3 |

**Конфликт M:** В Premiere M = add_marker. В CUT архитектуре M = favorite positive.
**Решение:** M = favorite positive (наш приоритет). Shift+M = standard marker. Совместимо с Registry #31-32.

---

## 5. REFERENCE: CURRENT CODE → ACTION ID MAPPING

Что УЖЕ реализовано в коде и как это маппится на Registry:

| Код | Где | Action ID | Работает? |
|-----|-----|-----------|-----------|
| `play()` / `pause()` | useCutEditorStore | `play_pause` | Да, через кнопку |
| `seek()` | useCutEditorStore | Используется playhead sync | Да |
| `setMarkIn()` / `setMarkOut()` | useCutEditorStore | `mark_in` / `mark_out` | Store есть, UI поля есть, hotkey нет |
| `setPlaybackRate()` | useCutEditorStore | `cycle_playback_rate` | Store есть, "1x" кнопка |
| `toggleSnap()` | useCutEditorStore | `snap_toggle` | Store есть, кнопка где-то |
| `setZoom()` | useCutEditorStore | `zoom_in` / `zoom_out` | Store есть, slider? |
| `createVersionedTimeline()` | useCutEditorStore | `new_sequence` | Работает |
| Undo/Redo | cut_undo_redo.py | `undo` / `redo` | Backend есть, UI/hotkey нет |
| Scene detect | cut_scene_detector.py | `scene_detect` | Backend есть, кнопка "Scenes" непонятная |
| Export Premiere XML | premiere_xml_converter.py | `export_media` | Работает |
| Export FCPXML | fcpxml_converter.py | `export_media` | Работает |

**ИТОГО:** Из 115 actions реализовано ~12 (store + backend), из них hotkeys подключено: ~2 (Space, может ещё что-то).

---

## 6. ПЛАН ДЕЙСТВИЙ (для обновления ROADMAP)

### Очерёдность UI cleanup:

**Cleanup Wave 1 (можно делать сейчас, параллельно с Phase 1):**
- [ ] Удалить CutEditorLayout.tsx (если не используется)
- [ ] Удалить SourceBrowser.tsx (если не используется)
- [ ] Layout: убрать дублирующий Program Monitor из right_top → заменить на Inspector tabs
- [ ] Переименовать: left_top = "Source: NO CLIP" (уже верно), center = Program Monitor (один!)

**Cleanup Wave 2 (Phase 3, вместе с routing):**
- [ ] Создать MonitorTransport.tsx — transport controls ПОД каждым монитором
- [ ] TransportBar.tsx → разрезать на MonitorTransport + TimelineToolbar
- [ ] Timeline toolbar = только Snap + Zoom slider + Linked selection
- [ ] Удалить кнопку "Scenes" из toolbar

**Cleanup Wave 3 (Phase 6-7, hotkeys):**
- [ ] Создать useHotkeys.ts — центральный регистр всех hotkeys
- [ ] Подключить Tier 1 hotkeys (JKL, I/O, Space, arrows, Cmd+Z, V/C)
- [ ] Action → Handler mapping (из Registry action IDs)

---

## 7. КЛЮЧЕВОЙ ДОКУМЕНТ ДЛЯ ВСЕХ ТАСКОВ

Каждый таск, касающийся UI/UX/hotkeys, ДОЛЖЕН ссылаться на:

1. **`docs/190_ph_CUT_WORKFLOW_ARCH/CUT_TARGET_ARCHITECTURE.md`** — архитектура (Source/Program, DAG spine, layout)
2. **`docs/185_ph_CUT_POLISH/CUT_NLE_UNIVERSAL_ACTION_REGISTRY.md`** — 115 actions, hotkeys, tool modes
3. **`docs/190_ph_CUT_WORKFLOW_ARCH/RECON_UI_CLEANUP.md`** — этот документ (что удалить, что перестроить)

Тройка документов покрывает: ЧТО строим (Architecture) + КАК управляется (Registry) + ЧТО чистим (этот Recon).
