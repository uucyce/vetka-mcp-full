# ⚡ UnifiedSearchBar - Quick Integration Reference

## Frontend Integration Points

### 1. ChatPanel (`client/src/components/chat/ChatPanel.tsx`)
```typescript
// Line 30: Function signature
export function ChatPanel({ isOpen, onClose, leftPanel, setLeftPanel }: Props)

// Line 52: Input state
const [input, setInput] = useState('');

// Line 50: useSocket hook
const { sendMessage, isConnected, joinGroup, leaveGroup, sendGroupMessage } = useSocket();

// Line 381-449: handleSend function
// → integrate search here for context auto-injection
```

**Integration point:** Add SearchBar between header (line 1185) and messages container (line 1221)

### 2. MessageInput (`client/src/components/chat/MessageInput.tsx`)
```typescript
// Line 139: Main component signature
export function MessageInput({
  value,        // Current input text
  onChange,     // Update input
  onSend,       // Send message
  // ... more props
})

// Line 626: Main input textarea
<textarea ref={inputRef} value={value} onChange={...} />

// Line 660-702: Smart button (Send/Mic)
```

**Integration point:** Could add search toolbar above textarea, but ChatPanel header is better

### 3. useSocket Hook (`client/src/hooks/useSocket.ts`)
```typescript
// Line 957: Main send function
const sendMessage = useCallback((message: string, nodePath?: string, modelId?: string) => {
  socketRef.current.emit('user_message', {
    text: message,
    node_path: nodePath,
    node_id: 'root',
    model: modelId,
    pinned_files: pinnedFiles
  });
})

// Add new socket event:
const searchQuery = useCallback((query: string, limit: number) => {
  socketRef.current?.emit('search_query', {
    text: query,
    limit,
    filters: {}
  });
})
```

**New events to add:**
- Client→Server: `search_query` (request search)
- Server→Client: `search_results` (receive results)

### 4. Types (`client/src/types/chat.ts`)
```typescript
// ADD:
export interface SearchResult {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'code' | 'doc';
  relevance: number;
  preview?: string;
}

export interface SearchQuery {
  text: string;
  limit?: number;
  filters?: { type?: string };
}
```

### 5. Styling
- **Theme:** Dark Nolan style (dark grays/whites)
- **Colors:**
  - Text: `#fff`, `#aaa`, `#555`
  - Background: `#1a1a1a`, `#222`
  - Accent: `#4a9eff` (blue)
  - Border: `#333`
- **Fonts:** Inherit (no special fonts, monospace for code)

---

## Backend Integration Points

### 1. Chat Handler (`src/api/handlers/chat_handler.py`)
```python
# Line 48-96: detect_provider() - already handles model routing
# Line 287-303: get_agent_short_name() - extracts short name

# Can be reused for search results
```

### 2. Search Service (`src/search/hybrid_search.py`)
```python
# Line 50+: class HybridSearchService
# Already implements:
# - Semantic search (Qdrant)
# - Keyword search (Weaviate)
# - RRF fusion

# Methods to use:
# - async_search(query, limit, filters)
# - Results: List[SearchResult] with relevance scores
```

### 3. Semantic Routes (`src/api/routes/semantic_routes.py`)
```python
# Line 36+: router = APIRouter(prefix="/api")

# Existing endpoint:
# GET /api/search/hybrid?query=...&limit=15

# Can be enhanced for real-time via WebSocket
```

### 4. Socket.IO Handler (NEW FILE: `src/api/handlers/search_handlers.py`)
```python
# Create new handler:
@sio.on('search_query')
async def handle_search_query(sid, data):
    query = data.get('text', '')
    limit = data.get('limit', 10)

    service = HybridSearchService()
    results = await service.async_search(query, limit)

    await sio.emit('search_results', {
        'results': results,
        'total': len(results)
    }, to=sid)
```

---

## Socket.IO Events Summary

### Existing events (don't modify)
- `user_message` - user text input (MAIN)
- `group_message` - group chat
- `stream_start/token/end` - streaming responses
- `approval_required/decided` - approval flow

### New events to add
```typescript
// CLIENT → SERVER
'search_query' {
  text: string
  limit: number
  filters?: object
}

// SERVER → CLIENT
'search_results' {
  results: SearchResult[]
  total: number
  took_ms: number
}

'search_error' {
  error: string
}
```

---

## File Structure for New Component

```
client/src/components/search/
├── UnifiedSearchBar.tsx       (NEW - main component)
├── SearchResults.tsx          (NEW - results display)
└── useSearch.ts               (NEW - custom hook)

src/api/handlers/
└── search_handlers.py         (NEW - socket handlers)
```

---

## Key Functions to Reuse

### Frontend
- `useSocket()` - hook for socket events (LINE 265)
- `useStore()` - state management (LINE 30+)
- `selectNode()` - select file in 3D (LINE 44)

### Backend
- `HybridSearchService.async_search()` - hybrid search
- `detect_provider()` - model detection
- `build_model_prompt()` - prompt formatting

---

## Integration Checklist

- [ ] Create `UnifiedSearchBar.tsx` component
- [ ] Create `useSearch.ts` hook
- [ ] Create `search_handlers.py` socket handler
- [ ] Add socket event types in `useSocket.ts`
- [ ] Add `SearchResult` type in `types/chat.ts`
- [ ] Add SearchBar section in ChatPanel (between header and messages)
- [ ] Connect SearchBar to socket.io `search_query` event
- [ ] Listen to `search_results` event and display
- [ ] Add debounce for live search
- [ ] Test integration end-to-end

---

## Code Snippets Ready to Use

### Add to ChatPanel.tsx (after line 80)
```typescript
const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
const [selectedSearchResult, setSelectedSearchResult] = useState<SearchResult | null>(null);

useEffect(() => {
  const handleSearchResults = (e: CustomEvent) => {
    setSearchResults(e.detail.results);
  };
  window.addEventListener('search-results', handleSearchResults);
  return () => window.removeEventListener('search-results', handleSearchResults);
}, []);
```

### Add SearchBar JSX (after line 1185, before line 1221)
```typescript
{/* Search Bar - Phase 68 */}
<div style={{ padding: 12, borderBottom: '1px solid #222' }}>
  <UnifiedSearchBar
    onSearch={(query) => handleSearch(query)}
    results={searchResults}
    onSelectResult={handleSelectSearchResult}
  />
</div>
```

---

**Status:** Ready for implementation
**Estimated effort:** 3-4 hours (frontend + backend)
**Risk level:** LOW (using existing components and services)
