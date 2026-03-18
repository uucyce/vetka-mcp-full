# RECON 192: Architecture vs Code Audit
**Date:** 2026-03-18
**Auditor:** Opus (3 parallel agents)
**Scope:** CUT_TARGET_ARCHITECTURE.md + CUT_DATA_MODEL.md vs codebase
**Method:** File-by-file code read, grep for wiring, UI screenshot verification

---

## TL;DR

Phases 0-8 закрыты по тасками, но **integration-level broken**. Код каждого компонента существует, но pipeline не собран. Ключевые разрывы:

1. **usePanelSyncStore — остров** — Script/DAG/StorySpace пишут в него, но никто в NLE не читает
2. **Hotkeys мертвы** — useCutHotkeys + TransportBar существуют, но TransportBar не подключён к layout
3. **Source = Program** — оба монитора на одном activeMediaPath, feed prop не передаётся
4. **DAG клик → ничего** — пишет в PanelSyncStore, но не доходит до VideoPreview
5. **Inspector убран** — renderRightBottom возвращает null

---

## 1. CRITICAL (блокирует использование)

### 1.1 usePanelSyncStore — изолированный остров
- **Проблема:** ScriptPanel, DAGProjectPanel, StorySpace3D пишут в `usePanelSyncStore` (syncFromScript, syncFromDAG, syncFromPlayhead). Но ни один компонент в NLE layout не читает эти значения для управления видео/таймлайном.
- **Файлы:** `usePanelSyncStore.ts`, `CutEditorLayoutV2.tsx`, `VideoPreview.tsx`
- **Fix:** Создать bridge-эффект в CutStandalone: `usePanelSyncStore.selectedAssetPath → useCutEditorStore.setActiveMedia()`

### 1.2 Hotkeys мертвы в NLE
- **Проблема:** `useCutHotkeys.ts` полностью реализован (Premiere/FCP7 presets, 40+ bindings). Подключен к `TransportBar.tsx`. Но TransportBar **не монтируется** в NLE layout — нигде нет `<TransportBar />`.
- **Файлы:** `useCutHotkeys.ts`, `TransportBar.tsx`, `CutEditorLayoutV2.tsx`
- **Fix:** Вызвать `useCutHotkeys()` в CutStandalone или CutEditorLayoutV2 напрямую (без TransportBar)

### 1.3 Source vs Program — одно и то же видео
- **Проблема:** Оба монитора рендерят `<VideoPreview />` без feed prop. Оба читают `activeMediaPath`. Store не имеет `sourceMediaPath`/`programMediaPath` split.
- **Файлы:** `CutEditorLayoutV2.tsx:121,136`, `VideoPreview.tsx`, `useCutEditorStore.ts`
- **Комментарий в коде:** line 114: "Phase 3 (CUT-3.2) will add feed='source' prop"
- **Fix:** Добавить `sourceMediaPath` в store, VideoPreview принимает `feed` prop

### 1.4 DAG клик не грузит Source Monitor
- **Проблема:** `DAGProjectPanel.handleNodeClick` → `syncFromDAG(nodeId, sourcePath)` → пишет в PanelSyncStore. Но PanelSyncStore не bridged к EditorStore, поэтому VideoPreview не реагирует.
- **Файлы:** `DAGProjectPanel.tsx:290-296`, `usePanelSyncStore.ts`
- **Fix:** Часть fix 1.1 (bridge)

---

## 2. HIGH (ломает архитектуру)

### 2.1 DAG Y-ось перевёрнута
- **Проблема:** START вверху (Y=0), END внизу. Архитектура: "bottom=START, top=END". Нет кнопки Flip Y.
- **Файл:** `DAGProjectPanel.tsx:145` — `y = start_sec * PX_PER_SEC` (вниз)
- **Fix:** `y = -start_sec * PX_PER_SEC` или добавить `flipY` toggle

### 2.2 Layout не соответствует архитектуре
- **Проблема:** Арх.док: Source LEFT, Program RIGHT. Код: Source CENTER, Project/Script/DAG LEFT. CutEditorLayoutV2 hardcoded, игнорирует usePanelLayoutStore.
- **Файлы:** `CutEditorLayoutV2.tsx`, `usePanelLayoutStore.ts`
- **Note:** Текущий layout может быть сознательным решением. Обсудить с Данилой.

### 2.3 Inspector убран из layout
- **Проблема:** `PulseInspector.tsx` существует и работает. Но `renderRightBottom` возвращает null. Inspector нигде не рендерится.
- **Файл:** `CutEditorLayoutV2.tsx:145`
- **Fix:** Добавить Inspector как таб или вернуть в right_bottom

### 2.4 DAG timelineId hardcoded
- **Проблема:** `<DAGProjectPanel />` рендерится без `timelineId` prop → всегда запрашивает `main`. При переключении табов таймлайна DAG не обновляется.
- **Файл:** `CutEditorLayoutV2.tsx:104`
- **Fix:** Передать `timelineId={activeTimelineId}` из store

---

## 3. MEDIUM (недореализовано)

### 3.1 Parallel Timelines не реализованы
- **Проблема:** Один TimelineTrackView в layout. Нет stacked dual-timeline view.
- **Файл:** `CutEditorLayoutV2.tsx:154`

### 3.2 Auto-Montage UI отсутствует
- **Проблема:** Бэкенд (3 режима) работает. Фронтенд — ноль. Нет кнопок, прогресса, ничего.
- **Бэкенд:** `POST /api/cut/pulse/auto-montage`, `pulse_auto_montage.py`

### 3.3 Favorite markers — неполная реализация
- **Проблема:** M = marker работает. N = negative отсутствует. MM (double-tap) = comment не реализован. MarkerKind taxonomy не совпадает с архитектурой.
- **Файл:** `useCutHotkeys.ts:112-113`, `useCutEditorStore.ts:63-65`

### 3.4 Screenplay import форматы
- **Проблема:** Только plain text. Fountain, FDX, PDF, DOCX — не реализованы.
- **Файл:** `screenplay_timing.py`

---

## 4. LOW (будущие фазы)

### 4.1 LoreNode — полностью отсутствуют
- Нет character/location/item нод в taxonomy или code.

### 4.2 Documentary mode (footage → transcript → script)
- Нет reverse pipeline.

### 4.3 Multiverse DAG / Storylines
- Нет branch visualization, нет X-columns для storylines.

### 4.4 Script BPM Layer B (JEPA/embeddings)
- Только symbolic rule-based BPM.

### 4.5 Layout drag-to-dock
- PanelShell инфраструктура есть, drag UI нет.

---

## 5. DATA MODEL GAPS

### Node Types: 10 в доке → 2 реально в графе
| Type | Status |
|------|--------|
| ScriptChunkNode | PARTIAL — существует как `scene_chunk`, 7 полей из 15 |
| MediaNode | PARTIAL — flat JSON bundles, не граф-ноды |
| MarkerNode | PARTIAL — MarkerKind taxonomy расходится с доком |
| TimelineNode | PARTIAL — runtime JSON, не граф |
| ProjectNode | PARTIAL — JSON schema, не нода |
| LoreNode | MISSING |
| SourceFileNode | MISSING |
| AnalysisNode | MISSING |
| ClipUsageNode | PARTIAL — как TimelineClip, упрощённый |
| FeedbackEvent | MISSING |

### Edge Types: 9+ в доке → 2 работают
| Edge | Status |
|------|--------|
| `next_scene` | MATCH |
| `contains` | MATCH |
| `has_media` | PARTIAL — в taxonomy, не создаётся |
| Остальные 7 | MISSING |

### Taxonomy naming mismatch
Код: `scene`, `take`, `asset`, `note`, `follows`, `semantic_match`, `alt_take`, `references`
Док: `ScriptChunkNode`, `MediaNode`, `MarkerNode`, `next_scene`, `mentions`, `similar_to`
Полное рассогласование имён.

---

## 6. РЕКОМЕНДУЕМЫЙ ПОРЯДОК ТАСКОВ

```
WAVE 1 — WIRING (убрать разрывы, ничего нового не писать)
  W1.1  PanelSyncStore → EditorStore bridge
  W1.2  Hotkeys — подключить useCutHotkeys к NLE layout
  W1.3  Source/Program feed split (store + VideoPreview prop)
  W1.4  DAG timelineId prop wiring
  W1.5  Inspector — вернуть в layout

WAVE 2 — DIRECTION FIXES
  W2.1  DAG Y-axis flip (START bottom)
  W2.2  Source Monitor label fix ("Program" → "Source")

WAVE 3 — MISSING UI
  W3.1  Auto-Montage UI (3 кнопки + progress)
  W3.2  Parallel Timelines (stacked dual view)
  W3.3  Favorite markers: N key + MM double-tap

WAVE 4 — DATA MODEL ALIGNMENT
  W4.1  Taxonomy naming reconciliation
  W4.2  has_media edge creation
  W4.3  LoreNode implementation
```

---

## Ссылки
- `CUT_TARGET_ARCHITECTURE.md` — архитектурный план
- `CUT_DATA_MODEL.md` — модель данных
- `ROADMAP_CUT_FULL.md` — роадмап фаз 0-9
