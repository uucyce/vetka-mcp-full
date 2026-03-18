# CUT NLE — Hotkey Architecture
**Date:** 2026-03-19
**Author:** Opus
**Based on:** 3 parallel recons (Premiere Pro reference, CUT panel inventory, CUT hotkey mapping)
**Status:** Architectural document — defines contract between hotkeys, panels, and functions

---

## 1. Принцип

> Каждый хоткей — это контракт: "нажал клавишу → произошло действие в конкретной панели".
> Если хоткей определён, функция ДОЛЖНА существовать. Если функции нет — хоткей удаляется из определения.

### 1.1 Panel Focus (из Premiere Pro)

В Premiere хоткеи бывают двух видов:
- **Global** — работают всегда (⌘Z undo, ⌘S save, ⌘I import)
- **Panel-scoped** — работают только когда панель в фокусе (JKL в Source vs Program, Delete в Timeline)

**Наша текущая реализация:** ВСЕ хоткеи глобальные (document-level keydown listener). Нет концепции "фокуса панели".

**Решение для MVP:** Ввести `focusedPanel` в store. Панель получает фокус по клику. Хоткеи проверяют `focusedPanel` перед выполнением panel-scoped действий.

---

## 2. Наши панели vs Premiere Pro

| Premiere Panel | Наш аналог | Компонент | Статус |
|----------------|------------|-----------|--------|
| Source Monitor | VideoPreview (center) | `VideoPreview.tsx` | ✅ Mounted |
| Program Monitor | VideoPreview (right) | `VideoPreview.tsx` | ✅ Mounted (но идентичен Source) |
| Timeline | Timeline (bottom) | `TimelineTrackView.tsx` | ✅ Mounted |
| Project Panel | Project Panel (left tab) | `ProjectPanel.tsx` | ✅ Mounted |
| Effects Panel | — | — | ❌ Нет аналога |
| Effect Controls | — | — | ❌ Нет аналога |
| Audio Mixer | AudioLevelMeter | `AudioLevelMeter.tsx` | ⚠️ Только VU meter, нет mixer |
| — | Script Panel | `ScriptPanel.tsx` | ✅ CUT-specific |
| — | DAG Project Panel | `DAGProjectPanel.tsx` | ✅ CUT-specific |
| — | PulseInspector | `PulseInspector.tsx` | ❌ Не подключён |
| — | StorySpace3D | `StorySpace3D.tsx` | ❌ Не подключён |
| — | BPM Track | `BPMTrack.tsx` | ✅ CUT-specific |

---

## 3. Матрица хоткеев: Premiere (эталон) → CUT (наша реализация)

### 3.1 Playback (Panel: Source/Program Monitor)

| Действие | Premiere | FCP7 | CUT key | CUT handler | Status |
|----------|----------|------|---------|-------------|--------|
| Play/Pause | Space | Space | Space | `togglePlay()` | ✅ REAL |
| Stop | K | K | K | `pause()` | ✅ REAL |
| Shuttle Back | J | J | J | `seek(-5s)` | ⚠️ SIMPLIFIED — Premiere: progressive speed, наш: фиксированный -5s |
| Shuttle Forward | L | L | L | `seek(+5s)` | ⚠️ SIMPLIFIED — аналогично |
| Frame Back | ← | ← | ← | `seek(-1/25s)` | ✅ REAL |
| Frame Forward | → | → | → | `seek(+1/25s)` | ✅ REAL |
| 5 Frame Back | ⇧← | ⇧← | — | — | ❌ MISSING |
| 5 Frame Forward | ⇧→ | ⇧→ | — | — | ❌ MISSING |
| Go to Start | Home | Home | Home | `seek(0)` | ✅ REAL |
| Go to End | End | End | End | `seek(duration)` | ✅ REAL |
| Cycle Speed | — | — | — | `cycleRate()` | ✅ CUT-only |
| Match Frame | F | F | — | — | ❌ MISSING |

**Scope:** Panel-scoped в Premiere (JKL привязаны к Source/Program). У нас — global.

### 3.2 Marking (Panel: Source/Program Monitor)

| Действие | Premiere | FCP7 | CUT key | CUT handler | Status |
|----------|----------|------|---------|-------------|--------|
| Mark In | I | I | I | `setMarkIn()` | ✅ REAL |
| Mark Out | O | O | O | `setMarkOut()` | ✅ REAL |
| Clear In | ⌥I | ⌥I | — | — | ❌ MISSING |
| Clear Out | ⌥O | ⌥O | — | — | ❌ MISSING |
| Clear In/Out | ⌘⇧X | ⌥X | ⌘⇧X / ⌥X | — | ❌ DEFINED but MISSING handler |
| Go to In | ⇧I | ⇧I | — | — | ❌ MISSING |
| Go to Out | ⇧O | ⇧O | — | — | ❌ MISSING |

**Scope:** Panel-scoped в Premiere (I/O на Source ставят source-marks, на Program — sequence-marks). У нас — global, всегда один markIn/markOut.

### 3.3 Editing (Panel: Timeline)

| Действие | Premiere | FCP7 | CUT key | CUT handler | Status |
|----------|----------|------|---------|-------------|--------|
| Split/Add Edit | ⌘K | B | ⌘K / B | — | ❌ DEFINED but MISSING handler |
| Split All Tracks | ⌘⇧K | — | — | — | ❌ MISSING |
| Delete (gap) | Delete | Delete | Delete | `removeSelectedClip()` | ✅ REAL |
| Ripple Delete | ⌥Delete | ⇧Delete | ⇧Delete | — | ❌ DEFINED but MISSING handler |
| Ripple Trim Prev→Playhead | Q | — | — | — | ❌ MISSING (Premiere Tier 1) |
| Ripple Trim Next→Playhead | W | — | — | — | ❌ MISSING (Premiere Tier 1) |
| Insert from Source | , | F9 | , / F9 | — | ❌ DEFINED but MISSING handler |
| Overwrite from Source | . | F10 | . / F10 | — | ❌ DEFINED but MISSING handler |
| Lift | ; | — | — | — | ❌ MISSING |
| Extract | ' | — | — | — | ❌ MISSING |

**Scope:** Timeline-only в Premiere. У нас — global.

### 3.4 Tools (Panel: Timeline)

| Действие | Premiere | FCP7 | CUT key | CUT handler | Status |
|----------|----------|------|---------|-------------|--------|
| Selection Tool | V | A | V / A | — | ❌ DEFINED but MISSING handler |
| Razor Tool | C | B | C / B | — | ❌ DEFINED but MISSING handler |
| Ripple Edit Tool | B | — | — | — | ❌ MISSING |
| Rolling Edit Tool | N | — | — | — | ❌ MISSING |
| Slip Tool | Y | — | — | — | ❌ MISSING |
| Slide Tool | U | — | — | — | ❌ MISSING |
| Snap Toggle | S | — | S | `toggleSnap()` | ✅ REAL (in TimelineToolbar) |

### 3.5 Navigation (Panel: Timeline)

| Действие | Premiere | FCP7 | CUT key | CUT handler | Status |
|----------|----------|------|---------|-------------|--------|
| Prev Edit Point | ↑ | ↑ | — | — | ❌ MISSING (Premiere Tier 1) |
| Next Edit Point | ↓ | ↓ | — | — | ❌ MISSING (Premiere Tier 1) |
| Zoom In | = | ⌘= | = / ⌘= | `setZoom(×1.3)` | ✅ REAL |
| Zoom Out | - | ⌘- | - / ⌘- | `setZoom(÷1.3)` | ✅ REAL |
| Zoom to Fit | \ | ⇧Z | — | — | ❌ MISSING |
| Nudge Left 1fr | ⌥← | — | ⌥← | — | ❌ DEFINED but MISSING handler |
| Nudge Right 1fr | ⌥→ | — | ⌥→ | — | ❌ DEFINED but MISSING handler |
| Nudge Left 5fr | ⌥⇧← | — | — | — | ❌ MISSING |
| Nudge Right 5fr | ⌥⇧→ | — | — | — | ❌ MISSING |

### 3.6 Markers (Panel: Global / любая)

| Действие | Premiere | FCP7 | CUT key | CUT handler | Status |
|----------|----------|------|---------|-------------|--------|
| Add Marker | M | M | M | `createMarker('favorite')` | ⚠️ REAL but type differs |
| Add Comment | — | — | ⇧M | `createMarker('comment', text)` | ✅ CUT-only |
| Next Marker | ⇧M | — | — | — | ❌ MISSING |
| Prev Marker | ⌘⇧M | — | — | — | ❌ MISSING |
| Negative Marker | — | — | N | — | ❌ DEFINED in arch doc but MISSING |

### 3.7 Clipboard (Panel: Global)

| Действие | Premiere | FCP7 | CUT key | CUT handler | Status |
|----------|----------|------|---------|-------------|--------|
| Undo | ⌘Z | ⌘Z | ⌘Z | `runUndoAction('undo')` | ✅ REAL (API) |
| Redo | ⌘⇧Z | ⌘⇧Z | ⌘⇧Z | `runUndoAction('redo')` | ✅ REAL (API) |
| Copy | ⌘C | ⌘C | ⌘C | — | ❌ DEFINED but MISSING handler |
| Paste | ⌘V | ⌘V | ⌘V | — | ❌ DEFINED but MISSING handler |
| Select All | ⌘A | ⌘A | ⌘A | — | ❌ DEFINED but MISSING handler |

### 3.8 Project (Panel: Global)

| Действие | Premiere | FCP7 | CUT key | CUT handler | Status |
|----------|----------|------|---------|-------------|--------|
| Import | ⌘I | ⌘I | ⌘I | `dispatchEvent('cut:trigger-import')` | ⚠️ STUB (event, no direct handler) |

### 3.9 CUT-Only (не в Premiere)

| Действие | CUT key | CUT handler | Status |
|----------|---------|-------------|--------|
| Scene Detect | ⌘D | `handleSceneDetect()` | ✅ REAL (API) |
| Toggle View (NLE/debug) | ⌘\ | `setViewMode()` | ✅ REAL |
| Escape Context | Esc | — | ❌ DEFINED but MISSING handler |

### 3.10 Panel Switching (НЕТ у нас)

| Действие | Premiere | CUT | Status |
|----------|----------|-----|--------|
| Focus Project Panel | ⇧1 | — | ❌ MISSING |
| Focus Source Monitor | ⇧2 | — | ❌ MISSING |
| Focus Timeline | ⇧3 | — | ❌ MISSING |
| Focus Program Monitor | ⇧4 | — | ❌ MISSING |
| Focus Inspector | ⇧5 | — | ❌ MISSING |
| Maximize Panel | ` | — | ❌ MISSING |

---

## 4. Статистика

### По статусу handler:
| Status | Count |
|--------|-------|
| ✅ REAL (функция работает) | 15 |
| ⚠️ SIMPLIFIED/STUB | 4 |
| ❌ DEFINED key, MISSING handler | 12 |
| ❌ MISSING entirely | 24+ |

### По приоритету (Premiere Tier 1 = "cannot ship without"):

| Tier 1 Action | Status |
|---------------|--------|
| JKL shuttle | ⚠️ Simplified (±5s, не progressive) |
| Space play/stop | ✅ |
| I/O mark in/out | ✅ |
| ←/→ frame step | ✅ |
| , insert / . overwrite | ❌ MISSING handler |
| ⌘K split/add edit | ❌ MISSING handler |
| Q/W ripple trim to playhead | ❌ MISSING entirely |
| Delete / ripple delete | ⚠️ Delete works, ripple missing |
| ⌘Z/⌘⇧Z undo/redo | ✅ |
| V selection tool | ❌ MISSING handler |
| S snap | ✅ |
| ↑/↓ navigate edits | ❌ MISSING entirely |

**Tier 1 score: 6/12 работают (50%)**

---

## 5. Архитектурные решения

### 5.1 Panel Focus System

```
useCutEditorStore → focusedPanel: 'source' | 'program' | 'timeline' | 'project' | 'script' | 'dag' | null

Каждая панель:
  onMouseDown → setFocusedPanel('timeline')
  CSS: панель в фокусе получает highlight border (1px solid #4A9EFF)

useCutHotkeys → проверяет focusedPanel перед panel-scoped действиями:
  if action.scope === 'panel' && action.panel !== focusedPanel → skip
```

### 5.2 Hotkey Registry (правило)

```
ПРАВИЛО: Хоткей существует в useCutHotkeys.ts ↔ handler существует и работает.

Нет handler → удалить хоткей из определения.
Новый handler → добавить хоткей в определение.
Никогда: хоткей без handler (текущее состояние с 12 "defined but missing").
```

### 5.3 JKL Progressive Shuttle

```
Текущее: J = seek(-5s), L = seek(+5s) — фиксированный скачок.
Premiere: J/L = прогрессивный shuttle (1x → 2x → 4x → 8x). K = стоп. JK/KL = медленно.

MVP решение:
  shuttleSpeed: number (0, -1, -2, -4, -8, 1, 2, 4, 8)
  J нажат → shuttleSpeed = shuttleSpeed > 0 ? -1 : shuttleSpeed * 2
  L нажат → shuttleSpeed = shuttleSpeed < 0 ? 1 : shuttleSpeed * 2
  K нажат → shuttleSpeed = 0, pause()
  requestAnimationFrame loop: seek(currentTime + shuttleSpeed * dt)
```

### 5.4 Tool State Machine

```
activeTool: 'select' | 'razor' | 'hand' | 'zoom'

V → activeTool = 'select' (default)
C → activeTool = 'razor'
H → activeTool = 'hand'
Z → activeTool = 'zoom'

Timeline cursor меняется по activeTool.
Click behavior зависит от activeTool:
  select → select/drag clip
  razor → split at click position
  hand → pan timeline
  zoom → zoom in at click position
```

---

## 6. Рекомендуемый порядок реализации

### Phase A — Foundation (перед любыми хоткеями)
1. **Panel Focus system** — `focusedPanel` в store + onMouseDown на панелях
2. **Cleanup:** удалить 12 хоткеев с missing handlers из определения
3. **Wire useCutHotkeys** в CutStandalone (не через TransportBar)

### Phase B — Tier 1 Editing (минимум для монтажа)
4. **Split at playhead** (⌘K) — API call `/cut/timeline/apply` op=`split_clip`
5. **Insert/Overwrite** (,/.) — Source mark in/out → insert/overwrite в Timeline
6. **Navigate edits** (↑/↓) — найти prev/next edit point, seek()
7. **Ripple Delete** (⌥Delete) — API call с op=`ripple_delete`

### Phase C — Tier 1 Polish
8. **JKL Progressive Shuttle** — заменить ±5s на progressive speed
9. **Q/W Ripple Trim to Playhead** — API call
10. **5-frame step** (⇧←/⇧→)
11. **Clear In/Out** (⌥I/⌥O/⌘⇧X)

### Phase D — Tool System
12. **Tool state machine** (V/C/H/Z) + cursor change
13. **Razor click** — split at mouse position (не playhead)

### Phase E — Panel Switching & UX
14. **⇧1-5 panel switching** — setFocusedPanel + scroll into view
15. **Backtick maximize** — toggle panel fullscreen
16. **Escape** — deselect / exit tool / close modal

---

## 7. Связь с другими задачами

| Задача | Зависимость |
|--------|------------|
| W1.1 PanelSyncStore bridge | Phase B.5 (insert/overwrite) нуждается в Source→Timeline pipeline |
| W1.3 Source/Program split | Phase A.1 (panel focus) нужен для panel-scoped I/O marks |
| W1.2 Wire hotkeys | = Phase A.3 (это один и тот же таск) |

---

## Ссылки
- `useCutHotkeys.ts` — текущие определения хоткеев
- `TransportBar.tsx` — текущие handlers (deprecated, не подключён)
- `CUT_TARGET_ARCHITECTURE.md` — общая архитектура
- `RECON_192_ARCH_VS_CODE_2026-03-18.md` — аудит код vs арх
