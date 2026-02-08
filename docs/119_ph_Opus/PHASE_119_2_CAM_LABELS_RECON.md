# Phase 119.2: CAM/Engram → Label Visibility — Recon Report

**Date:** 2026-02-08
**Agent:** Opus 4.5
**Status:** RECON COMPLETE
**Task:** Интеграция "горячести" файлов/папок с видимостью ярлыков

---

## Problem Statement

Сейчас ярлыки папок показываются по статическим факторам:
- Глубина (depth)
- Количество детей (children)
- Тип (folder/file)
- Pinned/highlighted

**Цель:** Добавить динамическую "горячесть" из CAM/Engram — активные, важные, часто используемые папки видны издалека.

---

## Discovered Systems

### 1. Heat Scores (File Watcher)

**Файл:** `src/scanners/file_watcher.py`

```python
# MARKER_119.2A — Heat Score System
class AdaptiveScanner:
    heat_scores: Dict[str, float] = {}  # path → 0.0-1.0

    def update_heat(dir_path, event_type):
        # created=+0.3, modified=+0.1, deleted=+0.2
        current = heat_scores.get(dir_path, 0.0)
        heat_scores[dir_path] = min(1.0, current + delta)

    def decay_all():  # hourly, factor=0.95
        for path in heat_scores:
            heat_scores[path] *= 0.95
```

**API:** `GET /api/watcher/heat` → `{scores: {path: score}, intervals: {...}}`

**Статус:** ✅ Работает, данные есть!

---

### 2. CAM (Context Awareness Module)

**Файл:** `src/memory/surprise_detector.py`

```python
# MARKER_119.2B — CAM Surprise Detection
class CAMMemory:
    THRESHOLD_LOW = 0.3   # compress aggressively
    THRESHOLD_HIGH = 0.7  # preserve fully

    def compute_surprise(block1, block2) -> float:
        # Cosine distance between context blocks
        # Used for ELISION compression, NOT for file scoring
```

**Статус:** ⚠️ CAM работает на уровне текста, не файлов. Не подходит напрямую.

---

### 3. Engram (User Memory)

**Файл:** `src/memory/engram_user_memory.py`

```python
# MARKER_119.2C — Engram User Preferences
class EngramUserMemory:
    # Hot preferences in RAM (usage_count > 5)
    # Cold preferences in Qdrant

    def get_preference(user_id, category, key):
        # O(1) lookup for hot prefs
```

**Статус:** ⚠️ Хранит user preferences, не file activity. Не подходит напрямую.

---

### 4. Label Scoring (Frontend)

**Файл:** `client/src/utils/labelScoring.ts`

```typescript
// MARKER_119.2D — Current Scoring Formula
export function computeLabelScore(node, isPinned, isHighlighted): number {
  if (isPinned) return 1.0;
  if (childCount <= 1) return 0.0;  // chain folders = 0

  return (
    depthScore * 0.50 +      // shallower = better
    branchFactor * 0.15 +    // more children = tiebreaker
    sizeScore * 0.10 +
    typeBoost * 0.10 +
    searchBoost * 0.15
  );
}
```

**Gap:** Нет `heatScore` в формуле!

---

### 5. Frontend Data Flow

**ScanPanel.tsx** уже получает heat scores:
```typescript
// MARKER_119.2E — Heat data exists but unused for labels
fetch(`${API_BASE}/watcher/status`)
  .then(res => res.json())
  .then(data => {
    // data.heat_scores available here
    // But NOT passed to labelScoring!
  });
```

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND                                  │
├─────────────────────────────────────────────────────────────┤
│  FileWatcher.heat_scores ─────────────────┐                 │
│      (per-directory activity)              │                 │
│                                            ▼                 │
│  GET /api/watcher/heat ──────────────► {path: score}        │
│                                            │                 │
│  GET /api/tree/data ─────────────────────┼────► {nodes}     │
│      (current: no heat data)              │                 │
└───────────────────────────────────────────┼─────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND                                 │
├─────────────────────────────────────────────────────────────┤
│  useSocket/useTreeData ───────► nodes: TreeNode[]           │
│      (current: no heat field)                                │
│                                            │                 │
│  labelScoring.ts ◄────────────────────────┘                 │
│      computeLabelScore(node, pinned, highlighted)            │
│      └── MISSING: node.heatScore                            │
│                                            │                 │
│  FileCard.tsx ◄────────────────────────────┘                │
│      showLabel = selectedLabelIds.has(id)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Option A: Inject Heat into Tree API (Recommended)

1. **Modify `tree_routes.py`:**
   ```python
   # Add heat_scores to tree response
   watcher = get_watcher()
   heat_scores = watcher.adaptive_scanner.get_all_heat_scores()

   for node in nodes:
       dir_path = os.path.dirname(node['path'])
       node['heatScore'] = heat_scores.get(dir_path, 0.0)
   ```

2. **Update TreeNode type:**
   ```typescript
   interface TreeNode {
     // existing fields...
     heatScore?: number;  // 0.0-1.0
   }
   ```

3. **Update labelScoring.ts:**
   ```typescript
   export function computeLabelScore(
     node: TreeNode,
     isPinned: boolean,
     isHighlighted: boolean,
   ): number {
     // NEW: Heat boost for active directories
     const heatBoost = (node.heatScore ?? 0) * 0.20;  // up to 20% boost

     return Math.min(1.0,
       depthScore * 0.40 +     // reduced from 0.50
       branchFactor * 0.15 +
       sizeScore * 0.10 +
       typeBoost * 0.10 +
       searchBoost * 0.10 +    // reduced from 0.15
       heatBoost              // NEW
     );
   }
   ```

### Option B: Separate Heat Socket Event

1. Backend emits `heat_update` event via SocketIO
2. Frontend maintains `heatScores` Map in store
3. labelScoring reads from store

**Pros:** Real-time updates without polling
**Cons:** More complex, separate data flow

---

## Markers Added

| Marker | File | Line | Description |
|--------|------|------|-------------|
| `MARKER_119.2A` | file_watcher.py | 190 | Heat score system |
| `MARKER_119.2B` | surprise_detector.py | 80 | CAM (text-level, not file) |
| `MARKER_119.2C` | engram_user_memory.py | 79 | User prefs (not file activity) |
| `MARKER_119.2D` | labelScoring.ts | 63 | Current scoring formula |
| `MARKER_119.2E` | ScanPanel.tsx | 273 | Heat data fetched but unused |

---

## Complexity Assessment

| Aspect | Level | Notes |
|--------|-------|-------|
| Backend changes | LOW | Just add heat to tree response |
| Frontend changes | LOW | Add field to type + scoring formula |
| Risk | LOW | Additive, doesn't break existing |
| Performance | WATCH | Heat map lookup is O(1) |

---

## Files to Modify

1. **`src/api/routes/tree_routes.py`** — Inject heat_scores into nodes
2. **`client/src/store/useStore.ts`** — Add heatScore to TreeNode type
3. **`client/src/utils/labelScoring.ts`** — Add heatBoost to formula
4. **Optional: `client/src/hooks/useSocket.ts`** — Listen for heat_update

---

## Visual Result

```
Overview (zoom out):
┌─────────────────────────────────────┐
│                                     │
│     [src] ← HOT, visible!           │
│       │                             │
│     [components] ← WARM             │
│                                     │
│     [docs] ← COLD, hidden           │
│                                     │
└─────────────────────────────────────┘

Close-up (zoom in):
All labels visible as normal
```

---

## Next Steps

1. User approval of Option A vs B
2. Add MARKER comments to files
3. Implement heat injection
4. Test with real activity data
5. Tune weight coefficients

---

**Report by:** Opus 4.5
**Scout method:** Direct file analysis (no Haiku needed for this scope)
**Duration:** ~5 minutes

---

## UPDATE: Review by Claude Opus (Claude Code session, 2026-02-08)

**Reviewer context:** Я реализовал Phase 119.1-119.8 включая MGC Dedup, STM Bridge, Scout role, Tavily, Context7, и только что Phase 120 (pipeline quality fixes). Знаю архитектуру памяти изнутри.

### Verdict: Option A — правильный выбор, но нужны расширения

Ресёрч Cursor Opus **качественный** — правильно нашёл heat scores, CAM, Engram, labelScoring.ts, и data flow gap. Но есть несколько важных дополнений:

### 1. MGC Cache — неиспользованный козырь

Cursor Opus **не нашёл** `src/memory/mgc_cache.py` (MGC = Multi-Granularity Cache). Это ключевая система:

```python
# MGCCache — canonical cache with get_sync/set_sync (Phase 119.1)
# Stores per-file access patterns:
# - read_count, write_count, last_accessed
# - Can compute "importance" = reads + writes * 2
```

**Рекомендация:** Помимо `heatScore` (файловая активность на диске), добавить `mgcScore` (активность агентов в памяти). Файл который часто ищут через Qdrant или читают через pipeline — важнее чем просто модифицированный.

Формула должна учитывать ОБА сигнала:
```typescript
const activityScore =
  (node.heatScore ?? 0) * 0.12 +    // файловая активность (watcher)
  (node.mgcScore ?? 0) * 0.08;      // агентская активность (MGC)
// Итого до 20% буст, как в оригинале
```

### 2. Экстраполяция на чаты и favorite

Cursor Opus описал только файлы/папки. Но та же механика нужна для:

| Сущность | Heat Source | Visibility Effect |
|----------|-----------|-------------------|
| **Файлы/папки** | FileWatcher heat + MGC access | Label видимость + размер |
| **Чаты** | Частота сообщений + pipeline использование | Позиция в истории + яркость |
| **Favorite ★** | Ручной pin пользователем | Всегда видно, score = 1.0 |

Для favorite нужен `isFavorite: boolean` в TreeNode и ChatHistory — это просто Boolean в store, без backend. При `isFavorite=true` → `computeLabelScore()` сразу возвращает 1.0 (как `isPinned`).

### 3. Реализация MGC score injection

Добавить в `tree_routes.py` рядом с heat injection:

```python
# After heat injection
try:
    from src.memory.mgc_cache import MGCCache
    mgc = MGCCache()
    for node in nodes:
        path = node.get('path', '')
        stats = mgc.get_sync(path)
        if stats:
            reads = stats.get('read_count', 0)
            writes = stats.get('write_count', 0)
            # Normalize to 0-1 range (cap at 50 interactions)
            node['mgcScore'] = min(1.0, (reads + writes * 2) / 50)
except Exception:
    pass  # MGC unavailable — skip gracefully
```

### 4. Приоритеты имплементации

| Step | Что | Сложность | Зависимости |
|------|-----|-----------|-------------|
| A1 | Heat injection в tree API + labelScoring | LOW | Как описал Cursor |
| A2 | isFavorite Boolean для файлов + чатов | LOW | useStore.ts + ChatPanel |
| A3 | MGC score injection | MEDIUM | Нужен MGC endpoint |
| A4 | Chat heat (частота сообщений) | MEDIUM | ChatHistoryManager |
| A5 | SocketIO real-time heat updates | LOW | Option B от Cursor, после A1 |

**Рекомендация:** Делать A1+A2 как один PR (Dragon Silver), A3-A5 отдельно.

### 5. О CAM и Engram

Cursor Opus правильно отметил что CAM (surprise_detector.py) и Engram работают на другом уровне:
- **CAM** — текстовый surprise detection для ELISION compression. НЕ подходит для file scoring.
- **Engram** — user preferences (hot RAM + cold Qdrant). Может хранить `favorite_files` как preference, но это overkill для Boolean.

Для file/chat favorites лучше простой JSON в `data/favorites.json` или field в `useStore.ts`.

### 6. Визуальный эффект (расширение)

Помимо label visibility, предлагаю:
- **Glow effect:** Горячие папки/файлы слегка светятся (CSS/Three.js emissive)
- **Size scaling:** Label font-size масштабируется с score (12px → 16px для hot)
- **Color gradient:** Cold=серый → Warm=голубой → Hot=оранжевый

Это даёт "тепловую карту" проекта с одного взгляда.

---

**Reviewed by:** Claude Opus 4.6 (Claude Code)
**Context:** Built Phase 119.1-120, knows MGC/STM/Pipeline internals
