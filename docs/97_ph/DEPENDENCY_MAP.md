# VETKA Dependency Map

**Date:** 2026-01-28
**Phase:** 96
**Agent:** Haiku

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│  client/src/                                                     │
│  ├── components/  ← React UI                                     │
│  ├── hooks/       ← State & API hooks                           │
│  ├── store/       ← Zustand state                               │
│  └── utils/       ← Helpers                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND                                  │
│  main.py → FastAPI + Socket.IO                                  │
│  ├── src/api/routes/      ← REST endpoints                      │
│  ├── src/api/handlers/    ← Request processing                  │
│  └── src/bridge/          ← External tool integration           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION                               │
│  src/orchestration/                                              │
│  ├── orchestrator_with_elisya.py  ← Main AI orchestrator        │
│  ├── triple_write_manager.py      ← Dual-store writes           │
│  ├── cam_engine.py                ← Context-Aware Memory        │
│  └── context_fusion.py            ← Context enrichment          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       AI PROVIDERS                               │
│  src/elisya/                                                     │
│  ├── model_router_v2.py    ← Provider selection                 │
│  └── provider_registry.py  ← API key management                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      VECTOR STORES                               │
│  src/memory/                                                     │
│  ├── qdrant_client.py      ← Qdrant (vetka_elisya)             │
│  └── engram_user_memory.py ← User preferences                   │
│                                                                  │
│  src/orchestration/triple_write_manager.py                       │
│  └── Weaviate (VetkaLeaf)  ← BM25 + vectors                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       SCANNERS                                   │
│  src/scanners/                                                   │
│  ├── file_watcher.py       ← Watchdog filesystem monitor        │
│  ├── embedding_pipeline.py ← Text → embeddings                  │
│  └── qdrant_updater.py     ← Index management                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Data Flows

### 1. Chat Message Flow
```
User Input
    ↓
MessageInput.tsx
    ↓ WebSocket emit('user_message')
useSocket.ts
    ↓
chat_routes.py → user_message_handler.py
    ↓
orchestrator_with_elisya.py
    ↓
model_router_v2.py → Provider API (Grok/GPT/Claude/Gemini)
    ↓
response_formatter.py
    ↓ WebSocket emit('assistant_response')
MessageBubble.tsx
```

### 2. Search Flow
```
SearchBar Input
    ↓
UnifiedSearchBar.tsx
    ↓ WebSocket emit('unified_search')
useSearch.ts
    ↓
search_handlers.py
    ↓
┌─── semantic: qdrant_client.py (vetka_elisya)
├─── keyword:  Weaviate BM25 (VetkaLeaf)
└─── hybrid:   RRF fusion of both
    ↓
SearchResults.tsx
```

### 3. File Scan Flow
```
ScanPanel.tsx (folder select)
    ↓ POST /scanner/scan-folder
semantic_routes.py
    ↓
file_watcher.py (watchdog)
    ↓
embedding_pipeline.py
    ↓
qdrant_updater.py
    ↓
triple_write_manager.py
    ↓
┌─── Qdrant (vetka_elisya)
└─── Weaviate (VetkaLeaf)
```

---

## Key Singletons

| Singleton | Location | Purpose |
|-----------|----------|---------|
| `qdrant_client` | singletons.py | Qdrant connection |
| `triple_write` | singletons.py | Dual-store manager |
| `model_router` | singletons.py | AI provider routing |
| `cam_engine` | singletons.py | Context memory |
| `file_watcher` | singletons.py | Filesystem monitor |

---

## Critical Dependencies

### Backend Python
```
fastapi          - API framework
socketio         - WebSocket
qdrant-client    - Vector DB
weaviate-client  - Semantic DB (optional)
watchdog         - File monitoring
sentence-transformers - Embeddings
openai/anthropic/google - AI providers
```

### Frontend TypeScript
```
react            - UI framework
zustand          - State management
socket.io-client - WebSocket
lucide-react     - Icons
tailwindcss      - Styling
```

---

## Cross-File Dependencies (High Coupling)

### Most Imported (Backend)
1. `src/initialization/singletons.py` - 42 imports
2. `src/memory/qdrant_client.py` - 28 imports
3. `src/orchestration/orchestrator_with_elisya.py` - 24 imports
4. `src/api/handlers/handler_utils.py` - 21 imports
5. `src/elisya/model_router_v2.py` - 18 imports

### Most Imported (Frontend)
1. `client/src/store/useStore.ts` - 31 imports
2. `client/src/hooks/useSocket.ts` - 22 imports
3. `client/src/config/api.config.ts` - 18 imports
4. `client/src/utils/formatters.ts` - 15 imports
5. `client/src/hooks/useSearch.ts` - 12 imports

---

## MCP Integration Points

```
src/mcp/
├── vetka_mcp_bridge.py      ← Main MCP server
├── mcp_console_standalone.py ← Debug console
├── state/
│   └── mcp_state.py         ← Session state
└── tools/
    ├── llm_call_tool.py     ← vetka_call_model
    ├── session_tools.py     ← vetka_session_*
    └── workflow_tools.py    ← vetka_execute_workflow
```

MCP tools connect through:
- `singletons.py` → shared instances
- `orchestrator_with_elisya.py` → AI calls
- `triple_write_manager.py` → storage
