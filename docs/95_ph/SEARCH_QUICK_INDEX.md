# VETKA Search System - Quick Reference

## Fast Navigation

### Search Types Status
| Type | Status | File | Time |
|------|--------|------|------|
| Semantic | ✅ WORKING | `src/search/hybrid_search.py` | 50-150ms |
| Keyword | ✅ WORKING | `src/memory/weaviate_helper.py` | 80-200ms |
| Hybrid (RRF) | ✅ WORKING | `src/search/hybrid_search.py` | 150-300ms |
| Filename | ✅ WORKING | `src/search/hybrid_search.py` | 20-80ms |
| CAM Tools | ✅ WORKING* | `src/orchestration/cam_engine.py` | - |

*UI not integrated

### API Endpoints
```
GET  /api/search/hybrid?q=...&mode=hybrid
POST /api/search/weaviate {query, limit, filters}
GET  /api/search/semantic?q=...
GET  /api/semantic-tags/search?tag=...
POST /api/scanner/rescan?path=...
```

### Frontend Components
```
UnifiedSearchBar.tsx       → Main search UI
useSearch.ts               → Search hook (debounce, state)
useSocket.ts               → WebSocket communication
```

### Socket.IO Events
```
Client → Server:  'search_query' {text, limit, mode, filters, min_score}
Server → Client:  'search_results' {results[], total, took_ms, sources}
Server → Client:  'search_error' {error, query}
```

### MCP Tools (Claude Code)
```
vetka_search              → Semantic search via embeddings
vetka_search_knowledge    → Advanced search with filtering
vetka_list_files          → File browsing with glob patterns
```

---

## Core Configuration

```bash
# Weights (sum = 1.0)
VETKA_SEMANTIC_WEIGHT=0.5    # Qdrant
VETKA_KEYWORD_WEIGHT=0.3     # Weaviate
VETKA_GRAPH_WEIGHT=0.2       # Future

# RRF
VETKA_RRF_K=60               # Smoothing constant

# Cache
VETKA_HYBRID_CACHE_TTL=300   # Seconds

# Context Fusion
VETKA_FUSION_MAX_TOKENS=2000
```

---

## CAM (Context-Aware Memory)

### Status
- ✅ Backend: Fully implemented
- ❌ Frontend: Not integrated

### Core Operations
1. **Branching** - Novel content detection (similarity < 0.7)
2. **Pruning** - Low-entropy removal (score < 0.2)
3. **Merging** - Similar subtree combination (similarity > 0.92)
4. **Accommodation** - Layout transitions (Procrustes)

### Tool Memory (Phase 75.1)
Tracks: `view_document`, `search_files`, `get_viewport`, `pin_files`, `focus_node`, `expand_folder`

### JARVIS Hints (NOT IN UI)
```python
suggestions = cam_tool_memory.suggest_tool(context)
hint = cam_tool_memory.get_jarvis_hint(context)
# Returns: "CAM suggests: search_files (activation: 0.85)"
```

---

## Issues at a Glance

| Issue | Impact | Fix Time | File |
|-------|--------|----------|------|
| CAM UI Missing | Medium | 4-6h | `UnifiedSearchBar.tsx` |
| Sort Incomplete | Low | 2h | `UnifiedSearchBar.tsx` |
| No Source Display | Low | 1h | `UnifiedSearchBar.tsx` |
| Context Prefixes Untested | Low | 2h | Backend routes |

---

## Debug Commands

```bash
# Test search endpoint
curl "http://localhost:8000/api/search/hybrid?q=authentication&mode=hybrid"

# Test semantic search
curl "http://localhost:8000/api/search/semantic?q=authentication"

# Check hybrid stats
curl "http://localhost:8000/api/search/hybrid/stats"

# Check CAM metrics
# (Add to tree_routes.py if not present)
curl "http://localhost:8000/api/cam/metrics"
```

---

## File Locations

### Backend
```
src/search/                  → Core search service
src/api/routes/              → API endpoints
src/api/handlers/            → Socket.IO handlers
src/orchestration/           → CAM & context fusion
src/memory/                  → Qdrant, Weaviate, compression
src/knowledge_graph/         → SemanticTagger
src/mcp/tools/               → Claude Code tools
```

### Frontend
```
client/src/components/search/     → UnifiedSearchBar
client/src/hooks/                 → useSearch, useSocket
client/src/types/chat.ts          → SearchResult types
```

---

## Performance Notes

### Caching
- Hit ratio: ~40-60%
- Hit latency: 1-2ms
- Miss latency: 150-500ms
- Max cache: 200 entries

### Parallel Execution
- Qdrant + Weaviate run concurrently
- RRF fusion: O(n log n) in practice
- Typical query: <300ms for 100 results

### Fallbacks
1. Weaviate down → Pure Qdrant (semantic)
2. Qdrant down → Pure Weaviate (keyword)
3. Both down → Empty results + error

---

## Integration Points

```
UI Search Bar
    ↓
Socket.IO: search_query
    ↓
search_handlers.py
    ↓
HybridSearchService
    ├→ Qdrant (semantic)
    ├→ Weaviate (keyword)
    └→ RRF fusion
    ↓
Context Fusion (includes CAM)
    ↓
LLM receives unified context
```

---

## Next Steps (If Needed)

### Phase 1: CAM UI Integration (Quick)
1. Add CAM activation display to search results
2. Show JARVIS hints in search bar
3. Add "suggested tools" section

### Phase 2: UI Polish (Medium)
1. Complete sort options
2. Add source indicators
3. Improve artifact view

### Phase 3: Advanced (Future)
1. Graph relations search (VETKA_GRAPH_WEIGHT)
2. Multi-language support
3. Custom weight configuration UI

---

## Emergency Info

**All search works** → System is healthy ✅

**Need CAM suggestions in UI?** → Missing integration, not broken
- File: `UnifiedSearchBar.tsx`
- Hook into: `cam_tool_memory.suggest_tool(context)`
- Effort: 4-6 hours

**Search slow?** → Check cache/backends
```bash
curl "http://localhost:8000/api/search/hybrid/stats"
```

**Qdrant down?** → Keyword-only fallback active
**Weaviate down?** → Semantic-only fallback active
**Both down?** → Empty results, error message

---

*Last Updated: 2026-01-26 | HAIKU-RECON-3*
