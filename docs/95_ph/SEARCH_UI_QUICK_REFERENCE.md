# Search UI Quick Reference - Phase 95

**One-page guide for developers working with the Search UI**

---

## 🎯 What Changed

### 3 New Features Added

1. **Source Badges** - Show which search backend returned each result
2. **Active Mode Indicator** - Badge showing current search mode
3. **Sort Direction** - Already working, now documented

---

## 📍 Code Locations

### UnifiedSearchBar.tsx

**Source Badge Display** (line ~1043):
```typescript
{result.source && (
  <span style={{ fontSize: '8px', ... }}>
    {result.source === 'qdrant' && 'QD'}
    {result.source === 'weaviate' && 'WV'}
    {result.source === 'hybrid' && 'HYB'}
  </span>
)}
```

**Active Mode Badge** (line ~817):
```typescript
<span style={{ fontSize: '9px', background: '#444', ... }}>
  {searchMode === 'hybrid' && 'HYB'}
  {searchMode === 'semantic' && 'SEM'}
  {searchMode === 'keyword' && 'KEY'}
  {searchMode === 'filename' && 'FILE'}
</span>
```

**Sort Logic** (line ~293):
```typescript
const sortedResults = React.useMemo(() => {
  const sorted = [...results];
  const dir = sortAscending ? 1 : -1;
  // Sort by name, type, date, size, relevance
}, [results, sortMode, sortAscending, displayLimit]);
```

---

## 🔌 API Integration

### SearchResult Type
```typescript
interface SearchResult {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'code' | 'doc';
  relevance: number;
  preview?: string;
  source?: string;        // NEW: 'qdrant' | 'weaviate' | 'hybrid'
  created_time?: number;
  modified_time?: number;
  size?: number;
}
```

### Backend Response
```json
{
  "results": [...],
  "total": 42,
  "took_ms": 125,
  "mode": "hybrid",
  "sources": ["qdrant", "weaviate"]
}
```

---

## 🎨 UI Components

### Search Mode Buttons
```typescript
type SearchModeType = 'hybrid' | 'semantic' | 'keyword' | 'filename';

const SEARCH_MODE_LABELS: Record<SearchModeType, string> = {
  hybrid: 'Hybrid',
  semantic: 'Semantic',
  keyword: 'Keyword',
  filename: 'Filename',
};
```

### Sort Options
```typescript
type SortMode = 'relevance' | 'name' | 'type' | 'date' | 'size';
```

---

## 🧪 Testing Checklist

### Manual Testing
- [ ] Search returns results with source badges
- [ ] Source badges show correct values: QD, WV, HYB
- [ ] Active mode badge updates when switching modes
- [ ] Sort dropdown works: name, relevance, type, date, size
- [ ] Sort direction toggle: ↑ ascending, ↓ descending
- [ ] Results sort correctly in both directions
- [ ] Hover preview shows file metadata
- [ ] Multi-select works (Shift+Click, Cmd+Click)

### Edge Cases
- [ ] No source field → no badge shown
- [ ] Unknown source → show first 3 letters uppercase
- [ ] Empty results → no errors
- [ ] Missing date/size → gracefully omitted
- [ ] Very long file names → ellipsis truncation

---

## 🐛 Debugging

### Check Source Field
```typescript
console.log('Result source:', result.source);
// Expected: 'qdrant' | 'weaviate' | 'hybrid' | undefined
```

### Check Sort State
```typescript
console.log('Sort mode:', sortMode, 'Ascending:', sortAscending);
// Expected: sortMode = 'relevance' | 'name' | ..., sortAscending = true/false
```

### Check Search Mode
```typescript
console.log('Active mode:', searchMode);
// Expected: 'hybrid' | 'semantic' | 'keyword' | 'filename'
```

---

## 🎯 Common Issues

### "Source badge not showing"
- Check if backend returns `source` field in SearchResult
- Verify result.source is one of: 'qdrant', 'weaviate', 'hybrid'
- Check conditional render: `{result.source && <span>...}`

### "Sort not working"
- Verify sortMode state is updating: `setSortMode(mode)`
- Check sortedResults memo dependencies include sortMode
- Ensure direction toggle updates: `setSortAscending(!sortAscending)`

### "Mode indicator wrong"
- Check searchMode state matches actual mode used
- Verify backend returns mode in response
- Check useSearch hook updates searchMode from response

---

## 📚 Related Files

```
client/src/
├── components/search/
│   └── UnifiedSearchBar.tsx     (main component)
├── hooks/
│   └── useSearch.ts             (search logic)
└── types/
    └── chat.ts                  (SearchResult type)
```

---

## 🚀 Future Enhancements

Not in current scope, but documented for future:

- **Backend sort params** - Pass sort to server instead of client-side
- **CAM suggestions** - Display contextual file suggestions
- **Context switching** - Enable /web/, /file/, /cloud/ backends
- **Advanced filters** - File type, size range, date range
- **Search history** - Recent searches dropdown

---

## 📞 Need Help?

1. Read **SONNET_SEARCH_UI_FIXES.md** for full implementation details
2. Check **SEARCH_UI_VISUAL_EXAMPLES.md** for visual examples
3. Reference **HAIKU_MARKERS_2_SEARCH_UI.md** for original requirements

---

**Quick Reference** | Phase 95 | Sonnet 4.5 | 2026-01-26
