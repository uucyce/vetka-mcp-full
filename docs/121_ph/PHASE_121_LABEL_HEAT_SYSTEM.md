# Phase 121: Task Board — Multi-Agent Task Queue (Label Heat System)

**Date:** 2026-02-08
**Agent:** Claude Opus 4.5 (Claude Code)
**Status:** COMPLETE
**Commits:** `ab1216b4`, `734dd39e`, `e765cee5`

---

## Problem Statement

На overview дерева видны только бесполезные chain folders (VETKA → Users → danilagulin → Documents → VETKA_Project), которые не дают представления о содержимом проекта.

**Цель:** Google Maps-style labels — показывать "столицы" (ветвящиеся папки), скрывать "дороги" (chain folders).

---

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           BACKEND                                    │
├─────────────────────────────────────────────────────────────────────┤
│  FileWatcher.heat_scores ──────► tree_routes.py ──────► API         │
│    (per-dir activity)              (inject into nodes)              │
│                                                                      │
│  Node: { id, name, type, heatScore: 0.0-1.0, ... }                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                   │
├─────────────────────────────────────────────────────────────────────┤
│  apiConverter.ts ──────► useStore.ts ──────► labelScoring.ts        │
│    (build children[])      (TreeNode)          (compute scores)     │
│                                                                      │
│  labelScoring formula:                                               │
│    depthScore * 0.42 +     // shallower = better                    │
│    branchFactor * 0.13 +   // more children = landmark              │
│    sizeScore * 0.10 +      // subtree magnitude                     │
│    typeBoost * 0.08 +      // folder vs file                        │
│    searchBoost * 0.12 +    // highlighted                           │
│    heatBoost * 0.15        // ACTIVE DIRECTORY BOOST                │
│                                                                      │
│  HARD GATE: childCount ≤ 1 → return 0.0 (kills chain folders!)      │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           VISUAL                                     │
├─────────────────────────────────────────────────────────────────────┤
│  FileCard.tsx:                                                       │
│    fontSize = BASE(14) + importance(16) + heat(6) * distanceDecay   │
│                                                                      │
│  Hot folders → larger labels, visible from far                      │
│  Cold folders → smaller labels, visible only when zoomed            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Critical Bug Fix

### The Breakthrough

**Problem:** `labelScoring.ts` uses `node.children.length` for branching factor scoring. But `children[]` was NEVER POPULATED!

```typescript
// Before fix: ALL folders had children = undefined/[]
const childCount = node.children?.length ?? 0;  // Always 0!
if (childCount <= 1) return 0.0;  // ALL folders got 0!
```

**Root cause:** `apiConverter.ts` created nodes from API but didn't build parent→children relationships from edges.

**Solution:** After converting nodes, iterate edges to build children arrays:

```typescript
// MARKER_119.2L: Build children from edges
for (const edge of edges) {
  const parentNode = nodes[edge.source];
  if (parentNode) {
    if (!parentNode.children) parentNode.children = [];
    parentNode.children.push(edge.target);
  }
}
```

---

## Files Modified

| File | Marker | Change |
|------|--------|--------|
| `tree_routes.py` | 119.2F | Inject heatScore from FileWatcher |
| `useStore.ts` | 119.2G | Add heatScore to TreeNode type |
| `labelScoring.ts` | 119.2H | Add heatBoost (15%) to formula |
| `FileCard.tsx` | 119.2I/J | Heat-based font size scaling |
| `App.tsx` | — | Pass heatScore prop to FileCard |
| `apiConverter.ts` | 119.2K/L | **FIX:** Build children[], pass heatScore |

---

## Visual Result

### Before
```
Overview shows: VETKA, Users, danilagulin, Documents, VETKA_Project
(useless chain folders that tell nothing about content)
```

### After
```
Overview shows: src, client, docs, tests, data
(actual project structure landmarks, distributed like capitals on a map)
```

---

## Debug Commands

```bash
# Check heat scores
curl -s http://localhost:5001/api/watcher/heat | jq

# Check folder children in API
curl -s http://localhost:5001/api/tree/data | python3 -c "
import sys,json
nodes = json.load(sys.stdin)['tree']['nodes']
branches = [n for n in nodes if n.get('type')=='branch']
for b in sorted(branches, key=lambda x: -len(x.get('children',[])))[:10]:
    print(f\"{b['name']:30} children={len(b.get('children',[]))}\")"

# Frontend console should show:
# [apiConverter] Phase 119.2: Built children for X nodes
```

---

## Future: MGC Integration

Architect review suggests adding `mgcScore` for agent activity tracking:

```typescript
const activityScore =
  (node.heatScore ?? 0) * 0.12 +    // файловая активность (watcher)
  (node.mgcScore ?? 0) * 0.08;      // агентская активность (MGC)
```

This would make files that agents are currently working on "glow" visibly.

**Requirements for MGC integration:**
1. Track per-file read/write counts in MGCCache
2. Add `/api/mgc/activity` endpoint
3. Inject mgcScore into tree nodes
4. Optional: Blue glow effect for actively-worked files

---

## Lessons Learned

1. **Frontend-backend data contracts matter** — API returned edges but frontend didn't build children from them
2. **Simple bugs can block complex features** — The entire label visibility system was "working" but with broken input data
3. **Debug the data flow end-to-end** — The scoring formula was correct, but input (children.length) was always 0

---

**Report by:** Claude Opus 4.5
**Session duration:** ~45 minutes
**Key insight:** Sometimes the fix is not in the algorithm, but in the data pipeline feeding it
