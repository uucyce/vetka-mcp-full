# Phase 1 Architecture Diagrams

**Visual Reference for MCP UI & Context Infrastructure**

---

## 1. Current MCP Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      CLAUDE DESKTOP/CODE                     │
│                     (MCP Client)                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                  (MCP stdio protocol)
                  JSON-RPC bidirectional
                         │
┌────────────────────────▼────────────────────────────────────┐
│           /src/mcp/vetka_mcp_bridge.py                      │
│                                                              │
│  ✅ 13 Tools mapped to VETKA endpoints                      │
│  ✅ Request validation (BaseMCPTool)                        │
│  ✅ Response formatting                                      │
│  ✅ Error handling                                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                  (HTTP REST calls)
                  async httpx client
                         │
┌────────────────────────▼────────────────────────────────────┐
│              VETKA FastAPI (localhost:5001)                 │
│                                                              │
│  /api/search/semantic    → Qdrant searches                 │
│  /api/tree/data          → Directory structure             │
│  /api/files/read         → File content                    │
│  /api/health             → System status                   │
│  /api/mcp/requests  [NEW] → Request logging                │
│  /api/mcp/responses [NEW] → Response logging               │
│  /api/mcp/save      [NEW] → Save logs                      │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
│   Qdrant     │ │  File I/O   │ │ Memory Mgr  │
│  (Vector DB) │ │   System    │ │             │
│              │ │             │ │             │
└──────────────┘ └─────────────┘ └─────────────┘
```

---

## 2. Request/Response Logging Flow

```
Claude Code calls: vetka_search_semantic
        │
        ▼
┌─────────────────────────────────┐
│ MCP Bridge receives request     │
│ {                               │
│   tool: "vetka_search_semantic" │
│   args: {query: "auth", ...}    │
│ }                               │
└──────────┬──────────────────────┘
           │
           ├─→ [NEW] Log request
           │         POST /api/mcp/log-request
           │         ↓
           │    _mcp_log.append({type: "request", ...})
           │
           ├─→ Execute tool
           │   (REST call to /api/search/semantic)
           │
           ├─→ [NEW] Log response
           │         duration_ms = (time.time() - start)
           │         POST /api/mcp/log-response
           │         ↓
           │    _mcp_log.append({type: "response", ...})
           │
           ▼
Return formatted result to Claude Code

[Optional] User clicks: Save to /docs/mcp_chat/
    ↓
POST /api/mcp/save
    ↓
Write: /docs/mcp_chat/mcp_chat_SESSION_TIMESTAMP.json
```

---

## 3. Context Retrieval (New)

```
Claude Code: "I need context for @vetka/authentication"
        │
        ▼ (detects @mention or explicit call)
┌────────────────────────────────────┐
│ vetka_get_context                  │
│ branch="authentication"             │
│ depth="medium"                      │
└──────────┬─────────────────────────┘
           │
           ├─→ Step 1: Get embedding
           │   embedding = get_embedding("authentication")
           │
           ├─→ Step 2: Semantic search
           │   results = qdrant.search(
           │     query_vector=embedding,
           │     limit=15,  // medium depth
           │     collection='vetka_elisya'
           │   )
           │
           ├─→ Step 3: Aggregate context
           │   for each result:
           │     - read full file content
           │     - track relevance score
           │     - estimate token count
           │
           ├─→ Step 4: Cache result
           │   cache[authentication] = (context, timestamp)
           │
           ▼
Return context block with:
├─ Branch: "authentication"
├─ Files: 12
├─ Relevance scores
├─ Content preview
└─ Estimated tokens: 5,340
```

---

## 4. Token Efficiency (No Waste)

```
                  Qdrant Vector DB
                  ┌──────────────┐
                  │ 1000+ files  │
                  │ All embedded │
                  │ Always ready │
                  └──────┬───────┘
                         │
                    (STEP 1: EMBED)
                    One-time cost
                    ~500ms, ~100 tokens
                         │
                         ▼
                  Query vector ready
                  ↓
              (STEP 2: SEARCH)
              Qdrant semantic search
              <100ms, 0 tokens!
                  ↓
              (STEP 3: RETURN FILES)
              Full content from disk
              Token cost = content size
              ↓
              (STEP 4: CACHE)
              ↓
          (REPEAT QUERY?)
              ↓
          (CHECK CACHE)
          ↓
          INSTANT RESPONSE
          0 tokens!
          (TTL: 1 hour)

RESULT: No re-embedding, no re-searching
        Just cached response
```

---

## 5. Data Structures

### MCP Request/Response Log

```json
{
  "session_id": "haiku-b-001",
  "requests": [
    {
      "id": "req-001",
      "type": "request",
      "tool": "vetka_search_semantic",
      "arguments": {
        "query": "authentication",
        "limit": 10
      },
      "timestamp": "2026-01-22T22:30:15.123Z"
    },
    {
      "id": "res-001",
      "type": "response",
      "tool": "vetka_search_semantic",
      "result": {
        "count": 8,
        "results": [
          {
            "path": "src/auth/session_manager.py",
            "score": 0.95,
            "snippet": "Session management and..."
          },
          {
            "path": "src/mcp/tools/llm_call_tool.py",
            "score": 0.82,
            "snippet": "LLM call routing..."
          }
        ]
      },
      "duration_ms": 127,
      "timestamp": "2026-01-22T22:30:16.250Z"
    }
  ]
}
```

### Context Retrieval Response

```json
{
  "success": true,
  "result": {
    "branch": "authentication",
    "depth": "medium",
    "files_found": 12,
    "context": [
      {
        "path": "src/auth/session_manager.py",
        "relevance": 0.97,
        "size_bytes": 5234,
        "content": "class SessionManager:\n    def __init__(self, ttl=3600):\n        ..."
      },
      {
        "path": "src/api/middleware/auth.py",
        "relevance": 0.94,
        "size_bytes": 3456,
        "content": "async def authenticate_request(request):\n    token = ..."
      }
    ],
    "total_tokens_estimate": 5340,
    "cached": false,
    "cache_ttl_seconds": 3600
  }
}
```

---

## 6. File Structure (Phase 1)

```
vetka_live_03/
├── src/
│   ├── mcp/
│   │   ├── vetka_mcp_bridge.py
│   │   │   └─ (MODIFY: Add context tool registration)
│   │   │   └─ (MODIFY: Add logging hooks)
│   │   │
│   │   └── tools/
│   │       ├── base_tool.py
│   │       ├── llm_call_tool.py
│   │       ├── search_knowledge_tool.py
│   │       ├── read_file_tool.py
│   │       └── context_tool.py  ◄─ [NEW]
│   │
│   ├── api/
│   │   ├── routes/
│   │   │   ├── tree_routes.py
│   │   │   ├── file_ops_routes.py
│   │   │   └── mcp_routes.py  ◄─ [NEW]
│   │   │
│   │   └── handlers/
│   │       ├── chat_handler.py
│   │       ├── tree_handlers.py
│   │       └── mcp_handlers.py  ◄─ [NEW] (optional for Socket.IO)
│   │
│   └── scanners/
│       └── qdrant_updater.py  (reference only)
│
├── docs/
│   ├── mcp_chat/  ◄─ [WRITE TARGET]
│   │   └── mcp_chat_SESSION_TIMESTAMP.json
│   │
│   └── 80_ph_mcp_agents/
│       ├── PHASE1_HAIKU_B_MCP_UI_CONTEXT.md  ◄─ [THIS]
│       ├── PHASE1_QUICK_START.md
│       └── PHASE1_ARCHITECTURE_DIAGRAMS.md  ◄─ [THIS]
│
└── main.py
    └─ (MODIFY: Register new routes)
```

---

## 7. Implementation Timeline (Phase 1)

```
Day 1 - Morning (1-2h):
  [CREATE] context_tool.py
    ├─ BaseMCPTool implementation
    ├─ Qdrant integration
    ├─ File aggregation logic
    └─ Caching layer

Day 1 - Afternoon (1h):
  [MODIFY] vetka_mcp_bridge.py
    ├─ Register context tool
    ├─ Add logging hooks
    └─ Format context results

Day 2 - Morning (1h):
  [CREATE] mcp_routes.py
    ├─ GET /api/mcp/requests
    ├─ GET /api/mcp/responses
    └─ POST /api/mcp/save

Day 2 - Afternoon (1h):
  [INTEGRATE] main.py
    ├─ Register routes
    ├─ Test endpoints
    └─ Verify logging

Day 2 - Evening (30m):
  [TEST] Full workflow
    ├─ Claude Code → vetka_get_context
    ├─ Check logging
    ├─ Save to /docs/mcp_chat/
    └─ Performance check

TOTAL: ~4.5 hours
Ready for Phase 2: UI
```

---

## 8. Depth Levels (Context Retrieval)

```
SHALLOW Depth
  └─ 5 files
  └─ Snippets only (first 200 chars)
  └─ ~500-1000 tokens
  └─ Use: Quick overviews

MEDIUM Depth (DEFAULT)
  └─ 15 files
  └─ First 500 chars content
  └─ ~3000-5000 tokens
  └─ Use: General understanding

DEEP Depth
  └─ 30+ files
  └─ Full file content
  └─ ~15000-20000 tokens
  └─ Use: Comprehensive context
```

---

## 9. Error Handling Flow

```
User calls: vetka_get_context branch="invalid"
        │
        ▼
┌──────────────────────────┐
│ Validation               │
│ ✅ branch length > 0     │
│ ✅ depth in [S, M, D]    │
└────────┬─────────────────┘
         │
         ├─ FAIL: Return validation error
         │
         ▼
┌──────────────────────────┐
│ Qdrant connection        │
│ ✅ Client available      │
│ ✅ Collection exists     │
└────────┬─────────────────┘
         │
         ├─ FAIL: Return error + fallback
         │
         ▼
┌──────────────────────────┐
│ Search execution         │
│ ✅ Query processed       │
│ ✅ Results retrieved     │
└────────┬─────────────────┘
         │
         ├─ FAIL: Return partial results
         │
         ▼
┌──────────────────────────┐
│ File aggregation         │
│ ✅ File readable         │
│ ✅ Content extracted     │
└────────┬─────────────────┘
         │
         ├─ FAIL: Skip, continue
         │
         ▼
Return context with error count and warnings
```

---

## 10. Integration Points (Summary)

```
VETKA Main System
│
├── Qdrant (Vector DB)
│   └─ Already populated with file embeddings
│   └─ Used by: context_tool.py
│
├── File System
│   └─ Read files on disk
│   └─ Used by: context_tool.py
│
├── FastAPI (Main server)
│   ├─ /api/mcp/* routes  [NEW]
│   └─ Socket.IO for real-time updates  [optional]
│
├── MCP Bridge (vetka_mcp_bridge.py)
│   ├─ 13 existing tools
│   ├─ +1 context tool  [NEW]
│   └─ Logging hooks  [NEW]
│
└── Claude Code (Client)
    └─ Calls MCP tools
    └─ Gets context + logging
```

---

## 11. Performance Metrics (Expected)

```
Context Retrieval Performance:

First call (not cached):
├─ Embedding query: ~100ms
├─ Qdrant search: ~50ms
├─ File reads (15 files): ~300ms
├─ Content aggregation: ~50ms
└─ Total: ~500ms

Subsequent calls (cached):
└─ Instant (<10ms)

Logging overhead per tool call:
├─ Request log POST: ~5ms
├─ Response log POST: ~5ms
└─ Total: ~10ms (1% overhead on typical calls)

Cache hit rate expected: 80-90% (1-hour TTL)
Token waste from repeated context: 0 (cached)
```

---

## 12. Success Indicators

```
✅ Claude Code can specify: vetka_get_context branch="X"
✅ Returns 10-30 files with relevance scores
✅ API endpoints respond: /api/mcp/requests, /api/mcp/responses
✅ Responses saved to: /docs/mcp_chat/mcp_chat_*.json
✅ Performance: <500ms first call, <10ms cached
✅ Logging adds <10ms overhead
✅ Zero token waste from caching
✅ No regression in existing tools
✅ All tests pass
```

---

**End of Architecture Reference**

Generated by Haiku Agent B
Phase 80.41 - 2026-01-22 23:02 UTC
