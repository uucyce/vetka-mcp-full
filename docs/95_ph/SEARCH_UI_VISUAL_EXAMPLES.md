# Search UI Visual Examples - Phase 95

## Before & After Comparison

### 1. Source Badges (NEW)

**Before** (no source indication):
```
📄 component.tsx    250 KB  Jan 24  92% ⭐
📄 utils.ts         125 KB  Jan 23  88% ⭐
📄 config.json      15 KB   Jan 22  95% ⭐
```

**After** (with source badges):
```
📄 [QD] component.tsx    250 KB  Jan 24  92% ⭐
📄 [WV] utils.ts         125 KB  Jan 23  88% ⭐
📄 [HYB] config.json     15 KB   Jan 22  95% ⭐
```

**Legend**:
- `[QD]` = Qdrant (vector/semantic search)
- `[WV]` = Weaviate (BM25/keyword search)
- `[HYB]` = Hybrid (RRF combined result)

---

### 2. Active Mode Indicator (NEW)

**Before** (unclear which mode is active):
```
┌─ Search Controls ────────────────────┐
│ HYB SEM KEY FILE │ 42 │ 125ms │ ↓ ⋮ │
└──────────────────────────────────────┘
```

**After** (clear active mode badge):
```
┌─ Search Controls ────────────────────┐
│ [HYB] │ HYB SEM KEY FILE │ 42 │ 125ms │ ↓ ⋮ │
│  ^active                                    │
└─────────────────────────────────────────────┘
```

---

### 3. Complete Search UI Layout

```
┌─ VETKA Search ───────────────────────────────────────────┐
│ 🔍 vetka/ semantic vector embedding...              [×]  │
├──────────────────────────────────────────────────────────┤
│ [SEM] │ HYB SEM KEY FILE │ 42 results │ 125ms │ ↓ ⋮     │
│   ^      ^mode buttons     ^count      ^time  ^sort      │
├──────────────────────────────────────────────────────────┤
│ 📄 [QD] embedding_pipeline.py  250 KB  Jan 24  92%  ⭐  │
│   src/scanners/embedding_pipeline.py                     │
│                                                           │
│ 📄 [QD] vector_store.ts        125 KB  Jan 23  88%  ⭐  │
│   client/src/lib/vector_store.ts                         │
│                                                           │
│ 📄 [HYB] qdrant_config.json    15 KB   Jan 22  95%  ⭐  │
│   config/qdrant_config.json                              │
│                                                           │
│ 📄 [WV] keyword_search.py      180 KB  Jan 21  85%  ⭐  │
│   src/search/keyword_search.py                           │
└──────────────────────────────────────────────────────────┘
```

---

## Sort Behavior Examples

### Sort by Name (Ascending ↑)
```
📄 [QD] a_config.json
📄 [WV] b_utils.ts
📄 [HYB] c_component.tsx
📄 [QD] d_test.py
```

### Sort by Date (Descending ↓ - newest first)
```
📄 [QD] file_today.ts      Today
📄 [WV] file_yesterday.py  Yesterday
📄 [HYB] file_week.json    Wed
📄 [QD] file_month.md      Jan 15
```

### Sort by Size (Descending ↓ - largest first)
```
📄 [QD] big_file.db       1.2 GB
📄 [WV] medium.json       450 MB
📄 [HYB] small.ts         125 KB
📄 [QD] tiny.txt          2 KB
```

### Sort by Relevance (Default ↓ - highest score first)
```
📄 [QD] exact_match.ts        98%
📄 [HYB] good_match.py        92%
📄 [WV] partial_match.json    85%
📄 [QD] weak_match.md         72%
```

---

## Interactive Elements

### Hover Preview (300ms delay)
```
┌─ component.tsx ─────────────────────┐
│ Type: code  Ext: .tsx  Score: 92%  │
│ Modified: Jan 24, 2026              │
├─────────────────────────────────────┤
│ src/components/search/component.tsx │
├─────────────────────────────────────┤
│ import React from 'react';          │
│ import { useSearch } from '...';    │
│ export function Component() {       │
│   return <div>Search UI</div>;      │
│ }                                    │
└─────────────────────────────────────┘
```

### Context Menu (click "vetka/")
```
┌─ Search Contexts ──────────────────┐
│ 🌳 vetka/         ✓ (active)       │
│    Search in indexed codebase      │
│                                     │
│ 🌐 web/                             │
│    Search the internet (soon)      │
│                                     │
│ 📁 file/                            │
│    Search local files (soon)       │
│                                     │
│ ☁️  cloud/                           │
│    Search cloud storage (soon)     │
│                                     │
│ 👥 social/                          │
│    Search social networks (soon)   │
└─────────────────────────────────────┘
```

### Sort Menu (click ⋮)
```
┌─ Sort By ───────┐
│ Relevance  ✓    │
│ Name            │
│ Type            │
│ Date            │
│ Size            │
└─────────────────┘
```

---

## Edge Cases Handled

### No Source Field
If backend doesn't return `source`:
```
📄 component.tsx    250 KB  Jan 24  92% ⭐
   (no source badge shown)
```

### Unknown Source
If backend returns unexpected source:
```
📄 [ELA] component.tsx    (ElasticSearch → ELA)
```

### No Date/Size
```
📄 [QD] component.tsx    92% ⭐
   (size and date gracefully omitted)
```

---

## Mobile/Compact Mode

In compact mode (`compact={true}`):
```
┌─ Search ─────────────────────────┐
│ 🔍 vetka/ query...          [×] │
├──────────────────────────────────┤
│ [HYB] │ HYB SEM KEY FILE │ 42 │ │
├──────────────────────────────────┤
│ 📄 [QD] file.ts  125KB 92% ⭐   │
│ 📄 [WV] util.py  80KB  88% ⭐   │
└──────────────────────────────────┘
```

---

## Keyboard Shortcuts

- `Enter` - Pin all selected results to context
- `Shift + Click` - Multi-select range
- `Cmd/Ctrl + Click` - Toggle individual selection
- `Escape` - Clear search and close

---

**End of Visual Examples** | Phase 95
