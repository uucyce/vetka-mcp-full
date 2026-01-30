# 🏗️ UnifiedSearchBar Architecture Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React/TypeScript)                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      ChatPanel.tsx                               │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │                                                                  │   │
│  │  Header Section (lines 786-1185)                                │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ [Chat/Team] [History] [Models] ... [Scanner] [Close]      │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │                                                                  │   │
│  │  NEW: UnifiedSearchBar Section                                  │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ [🔍 Search in code/docs...                    ]   [Filter▼]│ │   │
│  │  │ ┌──────────────────────────────────────────────────────┐   │ │   │
│  │  │ │ Result 1: src/main.py - relevance 0.95             │   │ │   │
│  │  │ │ Result 2: README.md - relevance 0.87               │   │ │   │
│  │  │ │ Result 3: config/api.config.ts - relevance 0.82    │   │ │   │
│  │  │ └──────────────────────────────────────────────────────┘   │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │                                                                  │   │
│  │  Messages Container (lines 1222-1238)                           │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │                  Chat Messages                            │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │                                                                  │   │
│  │  MessageInput Section (lines 1282-1298)                         │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ [🎤] [Text input...        ] [Context] [Send/Mic]        │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │                                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  ┌─────────────────────────┐    ┌──────────────────────────────────┐   │
│  │  useSocket Hook (ts)    │    │  useSearch Hook (NEW)            │   │
│  │  ─────────────────────  │    │  ──────────────────────          │   │
│  │  • sendMessage()        │    │  • handleSearch()                │   │
│  │  • sendGroupMessage()   │    │  • debounce query                │   │
│  │  • joinGroup()          │◄──►│  • cache results                 │   │
│  │  • Socket events        │    │  • mapResults()                  │   │
│  └─────────────────────────┘    │  • Socket listeners              │   │
│                                  └──────────────────────────────────┘   │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Socket.IO Client Connection                                     │   │
│  │ ──────────────────────────────────────────────────────────────  │   │
│  │ • Connected to: ws://localhost:8000/socket.io                  │   │
│  │ • Events:                                                       │   │
│  │   - Emit: 'search_query' { text, limit, filters }             │   │
│  │   - Listen: 'search_results' { results, total }               │   │
│  │   - Listen: 'search_error' { error }                          │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                            │
└────────────────────────────────────────────────────────────────────────▲──┘
                                                                          │
                                                                    WebSocket
                                                                          │
┌─────────────────────────────────────────────────────────────────────────▼──┐
│                      BACKEND (Python/FastAPI)                              │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Socket.IO Server (python-socketio)                                 │  │
│  │  ──────────────────────────────────────────────────────────────────  │  │
│  │  SID → Search Handler (search_handlers.py)                          │  │
│  │                                                                       │  │
│  │  @sio.on('search_query')                                            │  │
│  │  async def handle_search_query(sid, data):                          │  │
│  │    • Extract: { text, limit, filters }                             │  │
│  │    • Call HybridSearchService.async_search()                        │  │
│  │    • Emit 'search_results' back to client                           │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  HybridSearchService (hybrid_search.py)                              │  │
│  │  ──────────────────────────────────────────────────────────────────  │  │
│  │  • async_search(query, limit, filters)                              │  │
│  │    ├─► Semantic Search (Qdrant) - Vector similarity                │  │
│  │    ├─► Keyword Search (Weaviate) - BM25 ranking                    │  │
│  │    └─► RRF Fusion - Combine and rank                               │  │
│  │                                                                       │  │
│  │  Configuration:                                                      │  │
│  │  • SEMANTIC_WEIGHT = 0.5 (env var)                                │  │
│  │  • KEYWORD_WEIGHT = 0.3                                            │  │
│  │  • GRAPH_WEIGHT = 0.2                                              │  │
│  │  • RRF_K = 60                                                       │  │
│  │  • CACHE_TTL = 300s                                                │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │  Qdrant Vector   │  │  Weaviate BM25   │  │  RRF Fusion Algorithm    │ │
│  │  ────────────────│  │  ────────────────│  │  ──────────────────────  │ │
│  │  • Embeddings    │  │  • Text index    │  │  • Rank fusion           │ │
│  │  • Similarity    │  │  • Full-text     │  │  • Weighted scoring      │ │
│  │  • Vector search │  │  • BM25 ranking  │  │  • Final results         │ │
│  │  • Collections   │  │  • Filters       │  │                          │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘ │
│                                                                              │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
User Types Search Query
        │
        ▼
┌─────────────────────────────────┐
│  UnifiedSearchBar Component      │
│  (INPUT: text, debounced)       │
└────────┬────────────────────────┘
         │
         ▼
    useSearch Hook
    (debounce 300ms)
         │
         ▼
┌────────────────────────────────┐
│  Emit 'search_query' Socket    │
│  { text, limit: 10, filters }  │
└────────┬───────────────────────┘
         │
    [WebSocket]
         │
         ▼
┌────────────────────────────────────────────┐
│  Backend: handle_search_query Socket       │
│  (src/api/handlers/search_handlers.py)    │
└────────┬─────────────────────────────────┘
         │
         ▼
    HybridSearchService.async_search(query, limit)
         │
    ┌────┴────┬─────────┐
    │          │         │
    ▼          ▼         ▼
  Qdrant    Weaviate   RRF
 (Semantic) (Keyword) (Fusion)
    │          │         │
    └────┬─────┴────┬────┘
         │          │
         ▼          ▼
    Combine & Rank
         │
         ▼
┌─────────────────────────────────┐
│  SearchResult[] (with relevance)│
│  [                              │
│    { id, name, path, type,      │
│      relevance: 0.95, ... },    │
│    { ... }                      │
│  ]                              │
└──────────────┬──────────────────┘
               │
    [WebSocket - emit 'search_results']
               │
               ▼
┌──────────────────────────────────┐
│  useSearch Hook on Frontend      │
│  (Listen: 'search_results')      │
└───────────┬──────────────────────┘
            │
            ▼
┌──────────────────────────────────┐
│  Update state: setSearchResults()│
└───────────┬──────────────────────┘
            │
            ▼
┌──────────────────────────────────┐
│  Render SearchResults Component  │
│  Show ranked results to user     │
└──────────────────────────────────┘
```

---

## Component Integration Flow

```
┌──────────────────────────────────────────────────────────┐
│              ChatPanel State Management                   │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  const [input, setInput] = useState('')                  │
│  const [selectedNode, setSelectedNode] = useState(null)  │
│  const [chatMessages, setChatMessages] = useState([])    │
│                                                            │
│  NEW:                                                     │
│  const [searchQuery, setSearchQuery] = useState('')      │
│  const [searchResults, setSearchResults] = useState([])  │
│  const [selectedSearchResult, setSelectedSearchResult]   │
│                                                            │
└────────────┬─────────────────────────────────────────────┘
             │
      ┌──────┴──────┐
      ▼             ▼
  UnifiedSearchBar  MessageInput
     Component       Component
     │               │
     ├─ Input        ├─ Textarea for message
     ├─ Results      ├─ Voice button
     └─ Select       └─ Send button
        result

When user selects search result:
    1. selectNode(result.id) → Updates 3D visualization
    2. setSelectedNode(node) → Updates context indicator
    3. User can now type message → context auto-included
    4. Click send → message sent with context
```

---

## File Dependencies

```
Component Tree:
───────────────

App.tsx
 └─ ChatPanel.tsx
     ├─ Header Section
     │  ├─ ModelDirectory
     │  └─ ChatSidebar
     │
     ├─ NEW: UnifiedSearchBar.tsx
     │  ├─ useSearch.ts (custom hook)
     │  └─ SearchResults.tsx
     │
     ├─ MessageList.tsx
     │  └─ MessageBubble.tsx
     │
     └─ MessageInput.tsx
        ├─ MentionPopup.tsx
        ├─ useRealtimeVoice.ts
        └─ VoiceButton.tsx


Hooks:
──────

useSocket.ts ◄─── Sends/listens socket events
  ├─ sendMessage()
  ├─ sendGroupMessage()
  ├─ Emits: 'user_message', 'group_message'
  └─ Listens: 'chat_response', 'stream_*'

useSearch.ts (NEW) ◄─── Search-specific logic
  ├─ useSocket for 'search_query'
  ├─ Debounce query
  ├─ Cache results
  └─ Listens: 'search_results'


Backend:
────────

main.py (FastAPI app)
 └─ Socket.IO Server
     ├─ handlers/
     │  ├─ chat_handlers.py
     │  ├─ user_message_handler.py
     │  └─ search_handlers.py (NEW)
     │
     ├─ routes/
     │  ├─ chat_routes.py
     │  ├─ semantic_routes.py
     │  └─ group_routes.py
     │
     └─ search/
        ├─ hybrid_search.py
        ├─ rrf_fusion.py
        └─ [Qdrant + Weaviate clients]
```

---

## API Contract

### Socket.IO Events

#### Client → Server

**Event: `search_query`**
```json
{
  "text": "string",           // Search query text
  "limit": 10,               // Max results (default: 10)
  "filters": {               // Optional filters
    "type": "code|docs|all",
    "recent": true,
    "path_pattern": "src/**"
  }
}
```

#### Server → Client

**Event: `search_results`**
```json
{
  "results": [
    {
      "id": "uuid",
      "name": "filename.ext",
      "path": "/full/path/to/file",
      "type": "file|code|doc",
      "relevance": 0.95,
      "preview": "First 100 chars of content...",
      "metadata": {
        "language": "python",
        "lines": 45,
        "size": 2048
      }
    }
  ],
  "total": 42,
  "query": "search text",
  "took_ms": 145
}
```

**Event: `search_error`**
```json
{
  "error": "Error message",
  "query": "what user searched"
}
```

---

## Performance Considerations

### Caching
- Frontend: Cache last 50 searches (300s TTL)
- Backend: HybridSearchService has built-in cache (300s TTL)
- Qdrant: Vector cache for embeddings
- Weaviate: Inverted index cache

### Optimization
- **Debounce:** 300ms on input (wait for user to finish typing)
- **Limit results:** Default 10, max 50
- **Parallel searches:** Qdrant + Weaviate in parallel
- **RRF fusion:** O(n log n) merging complexity

### Expected Performance
- First search: ~200-500ms (embedding + indexing)
- Subsequent searches: ~50-150ms (cached)
- Real-time updates: <100ms

---

## Testing Points

1. **Frontend Tests**
   - SearchBar renders and accepts input
   - Debounce works (no immediate socket emit)
   - Results display correctly
   - Click result selects node and updates context

2. **Backend Tests**
   - Socket handler receives search_query
   - HybridSearchService returns ranked results
   - Socket emits search_results back

3. **Integration Tests**
   - E2E: Search → Select → Auto-inject context → Send message
   - Error handling: Network failure, search timeout
   - Performance: < 500ms for cold search

---

**Architecture Complete** ✅
**Ready for Implementation** ✅
