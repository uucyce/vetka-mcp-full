# VETKA API Endpoints Reference - Phase 93

**Last Updated:** 2026-01-25
**Total Endpoints:** 66+ FastAPI routes + Socket.IO events + OpenCode Bridge routes
**Architecture:** FastAPI + python-socketio + Qdrant + Weaviate

## Table of Contents
1. [REST API Endpoints (FastAPI)](#rest-api-endpoints-fastapi)
2. [Socket.IO Events](#socketio-events)
3. [OpenCode Bridge Endpoints](#opencode-bridge-endpoints)
4. [MCP Tool Endpoints](#mcp-tool-endpoints)

---

## REST API ENDPOINTS (FastAPI)

All REST endpoints follow FastAPI/Pydantic patterns. Base URL: `http://localhost:8000/api/`

### 1. CHAT ENDPOINTS (`/api/chat/*`)

**Router:** `src/api/routes/chat_routes.py`

#### GET `/api/chat/history`
- **Purpose:** Retrieve chat history for a specific node
- **Parameters:**
  - `path` (Query, required): Node path identifier
- **Response:**
  ```json
  {
    "success": true,
    "history": [{message}, ...],
    "node_path": "string",
    "count": number
  }
  ```
- **Services Called:** Memory manager (triple write), chat history loader

#### POST `/api/chat/clear-history`
- **Purpose:** Clear all chat history for a node
- **Body:** `{"path": "string"}`
- **Response:** `{"success": true, "message": "History cleared"}`
- **Services Called:** Memory manager, file system

#### POST `/api/chat` (THE BIG ONE!)
- **Purpose:** Universal chat API - routes to agents or direct LLM
- **Body:**
  ```json
  {
    "message": "string (required)",
    "conversation_id": "string (optional)",
    "model_override": "string (optional)",
    "system_prompt": "string (optional)",
    "temperature": number (0.0-2.0),
    "max_tokens": number,
    "node_id": "string (optional)",
    "node_path": "string (optional)",
    "file_path": "string (optional)"
  }
  ```
- **Response:**
  ```json
  {
    "conversation_id": "uuid",
    "response": "string",
    "model": "string",
    "provider": "string",
    "processing_time_ms": number,
    "eval_score": number,
    "eval_feedback": "string",
    "metrics": {
      "input_tokens": number,
      "output_tokens": number,
      "agent_scores": {}
    },
    "timestamp": number
  }
  ```
- **Flow:**
  1. Check if MCP agent (mcp/claude_code, mcp/browser_haiku) → forward to team messages
  2. Run Hostess decision engine (optional) → quick_answer, clarify, search, show_file
  3. Run orchestrator with PM/Dev/QA agents (parallel if PARALLEL_MODE enabled)
  4. Fallback: API Gateway v2 → Ollama (qwen2:7b)
  5. Triple-write to memory (Weaviate + Qdrant)
  6. EvalAgent scoring
  7. Return complete response

- **Services Called:**
  - Hostess agent (routing decision)
  - Orchestrator (PM, Dev, QA agents)
  - Memory manager (Weaviate, Qdrant)
  - EvalAgent (scoring)
  - API Gateway v2
  - Model Router v2
  - Ollama (fallback)

**Feature Flags:**
- `ELISYA_ENABLED`: Enable Elisya orchestrator
- `PARALLEL_MODE`: Run PM/Dev/QA in parallel
- `HOSTESS_AVAILABLE`: Enable Hostess routing
- `API_GATEWAY_AVAILABLE`: Use API Gateway v2
- `MODEL_ROUTER_V2_AVAILABLE`: Use model router
- `QDRANT_AUTO_RETRY_AVAILABLE`: Save to Qdrant

---

### 2. CONFIGURATION ENDPOINTS (`/api/config/*`)

**Router:** `src/api/routes/config_routes.py`

#### GET `/api/config`
- **Purpose:** Get current agentic configuration
- **Response:**
  ```json
  {
    "success": true,
    "config": {
      "models": {},
      "routing": {},
      ...
    }
  }
  ```
- **Note:** API keys redacted for security

#### POST `/api/config`
- **Purpose:** Update configuration (partial updates supported)
- **Body:** Any JSON object (API keys prevented)
- **Response:** `{"success": true, "message": "Config updated"}`

#### GET `/api/mentions`
- **Purpose:** Get available @mentions for autocomplete
- **Response:**
  ```json
  {
    "success": true,
    "mentions": ["@PM", "@Dev", "@QA", ...],
    "count": number
  }
  ```

#### GET `/api/models/available`
- **Purpose:** Get available models by tier
- **Response:**
  ```json
  {
    "success": true,
    "available": {},
    "defaults": {},
    "aliases": {}
  }
  ```

#### GET `/api/tools/available`
- **Purpose:** Get list of available agent tools
- **Response:**
  ```json
  {
    "success": true,
    "tools": ["tool_name"],
    "definitions": {}
  }
  ```

#### GET `/api/reactions`
- **Purpose:** Get all saved reactions for UI state restoration
- **Response:**
  ```json
  {
    "success": true,
    "reactions": {},
    "count": number
  }
  ```

#### POST `/api/tools/execute`
- **Purpose:** Execute a single tool (testing/debugging)
- **Body:** `{"tool": "string", "params": {}}`
- **Response:**
  ```json
  {
    "success": boolean,
    "tool": "string",
    "params": {},
    "result": {}
  }
  ```

#### GET `/api/keys/status`
- **Purpose:** Get API keys status without exposing actual keys
- **Response:**
  ```json
  {
    "success": true,
    "stats": {
      "openrouter_keys": number,
      ...
    }
  }
  ```

#### POST `/api/keys/add`
- **Purpose:** Add new API key
- **Body:** `{"key": "string", "provider": "openrouter", "is_paid": boolean}`
- **Response:** `{"success": boolean, ...}`

#### POST `/api/keys/detect`
- **Purpose:** Auto-detect API key type/provider
- **Body:** `{"key": "string"}`
- **Response:**
  ```json
  {
    "success": true,
    "detected": true,
    "provider": "string",
    "confidence": number
  }
  ```

#### POST `/api/keys/add-smart`
- **Purpose:** Smart key addition with auto-detection
- **Body:** `{"key": "string"}`
- **Response:** `{"success": boolean, "provider": "string", ...}`

#### GET `/api/keys/validate`
- **Purpose:** Validate all stored API keys
- **Response:**
  ```json
  {
    "success": true,
    "validation": {
      "provider": "status"
    }
  }
  ```

#### GET `/api/keys`
- **Purpose:** Get all saved keys by provider (masked for UI)
- **Response:**
  ```json
  {
    "success": true,
    "providers": [{
      "provider": "string",
      "keys": [{
        "id": "string",
        "provider": "string",
        "key": "masked",
        "key_full": "string",
        "status": "active"
      }],
      "count": number
    }]
  }
  ```

#### GET `/api/agents/status`
- **Purpose:** Get status of initialized agents
- **Response:**
  ```json
  {
    "success": true,
    "agents_available": boolean,
    "agents": ["PM", "Dev", "QA"],
    "count": number
  }
  ```

#### GET `/api/models`
- **Purpose:** Get all available models with pricing (Phase 48)
- **Query:** `refresh=boolean`
- **Response:**
  ```json
  {
    "success": true,
    "count": number,
    "summary": {
      "free": number,
      "cheap": number,
      "premium": number,
      "voice": number,
      "providers": ["list"]
    },
    "models": [{
      "id": "string",
      "name": "string",
      "provider": "string",
      "context_length": number,
      "pricing": {"prompt": "string", "completion": "string"},
      "type": "string",
      "capabilities": ["list"]
    }]
  }
  ```

#### GET `/api/models/categories`
- **Purpose:** Get models organized by category
- **Response:**
  ```json
  {
    "success": true,
    "categories": {
      "free": [{...}],
      "cheap": [{...}],
      "premium": [{...}],
      "providers": {}
    }
  }
  ```

---

### 3. TREE/KNOWLEDGE GRAPH ENDPOINTS (`/api/tree/*`)

**Router:** `src/api/routes/tree_routes.py`

#### GET `/api/tree/data`
- **Purpose:** Get multi-tree layout with directory/semantic blend (Phase 17.2)
- **Query:** `mode=directory|semantic|both`
- **Response:**
  ```json
  {
    "format": "vetka-v1.4",
    "source": "qdrant",
    "mode": "string",
    "tree": {
      "id": "main_tree_root",
      "name": "VETKA",
      "nodes": [{
        "id": "string",
        "type": "root|branch|leaf",
        "name": "string",
        "parent_id": "string",
        "metadata": {},
        "visual_hints": {
          "layout_hint": {"expected_x": number, "expected_y": number, "expected_z": number},
          "color": "string",
          "opacity": number
        },
        "cam": {"surprise_metric": number, "operation": "string"}
      }],
      "edges": [{
        "from": "string",
        "to": "string",
        "semantics": "contains"
      }],
      "metadata": {
        "total_nodes": number,
        "total_edges": number,
        "total_files": number,
        "total_folders": number
      }
    }
  }
  ```
- **Services Called:** Qdrant (scroll), CAM engine (surprise metrics), layout engine

#### POST `/api/tree/clear-semantic-cache`
- **Purpose:** Clear semantic DAG cache
- **Response:** `{"status": "ok", "message": "Semantic cache cleared"}`

#### GET `/api/tree/export/blender`
- **Purpose:** Export tree to Blender-compatible format
- **Query:** `format=json|glb|obj`, `mode=directory|semantic`
- **Response:** File download (JSON/GLB/OBJ)
- **Services Called:** Blender exporter, Qdrant

#### GET|POST `/api/tree/knowledge-graph`
- **Purpose:** Get Knowledge Graph structure for tag-based layout (Phase 17.1)
- **Query/Body:**
  - `force_refresh`: boolean
  - `min_cluster_size`: number (default 3)
  - `similarity_threshold`: number (default 0.7)
  - `file_positions`: object
- **Response:**
  ```json
  {
    "status": "ok|error",
    "source": "cache|computed",
    "tags": {
      "tag_id": {
        "id": "string",
        "name": "string",
        "files": ["array"],
        "color": "string",
        "position": {}
      }
    },
    "edges": [{
      "source": "string",
      "target": "string",
      "type": "string",
      "weight": number
    }],
    "chain_edges": [{...}],
    "positions": {
      "node_id": {"x": number, "y": number, "z": number, ...}
    },
    "knowledge_levels": {
      "file_id": number
    },
    "nodes": number,
    "rrf_stats": {},
    "statistics": {}
  }
  ```
- **Services Called:** Qdrant, Knowledge layout builder, RRF fusion engine

#### POST `/api/tree/clear-knowledge-cache`
- **Purpose:** Clear Knowledge Graph cache
- **Response:** `{"status": "ok", "message": "Knowledge Graph cache cleared"}`

---

### 4. SEMANTIC SEARCH ENDPOINTS (`/api/search/*`, `/api/semantic-tags/*`)

**Router:** `src/api/routes/semantic_routes.py`

#### GET `/api/semantic-tags/search`
- **Purpose:** Search files by semantic tag using embeddings
- **Query:**
  - `tag`: string (required)
  - `limit`: number (default 100)
  - `min_score`: number (default 0.35)
- **Response:**
  ```json
  {
    "success": true,
    "tag": "string",
    "count": number,
    "files": [{
      "id": "string",
      "name": "string",
      "path": "string",
      "score": number,
      "extension": "string"
    }]
  }
  ```
- **Services Called:** SemanticTagger, Qdrant

#### GET `/api/semantic-tags/available`
- **Purpose:** Get list of predefined semantic tags
- **Response:**
  ```json
  {
    "tags": ["string"],
    "tag_details": [{...}],
    "description": "string"
  }
  ```

#### GET `/api/file/{file_id}/auto-tags`
- **Purpose:** Get auto-assigned semantic tags for a file
- **Response:**
  ```json
  {
    "file_id": "string",
    "name": "string",
    "path": "string",
    "tags": [{
      "tag": "string",
      "score": number
    }]
  }
  ```
- **Services Called:** SemanticTagger, Qdrant

#### GET `/api/search/semantic`
- **Purpose:** Universal semantic search with caching (Phase 17, Phase 19)
- **Query:**
  - `q`: string (required, min 2 chars)
  - `limit`: number (default 100)
- **Response:**
  ```json
  {
    "success": true,
    "query": "string",
    "count": number,
    "cache_hit": boolean,
    "files": [{
      "id": "string",
      "name": "string",
      "path": "string",
      "score": number,
      "extension": "string",
      "created_time": number,
      "modified_time": number
    }]
  }
  ```
- **Cache:** 5-minute TTL, max 100 entries
- **Services Called:** SemanticTagger, Qdrant

#### POST `/api/search/weaviate`
- **Purpose:** Hybrid search via Weaviate with Qdrant fallback
- **Body:**
  ```json
  {
    "query": "string (required)",
    "limit": number (default 100),
    "filters": {}
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "results": [{
      "id": "string",
      "path": "string",
      "name": "string",
      "type": "string",
      "depth": number,
      "distance": number,
      "certainty": number,
      "snippet": "string",
      "source": "weaviate|qdrant"
    }],
    "total": number,
    "query": "string",
    "source": "weaviate|qdrant"
  }
  ```
- **Services Called:** Weaviate (GraphQL), Qdrant (fallback), SemanticTagger

#### GET `/api/search/hybrid`
- **Purpose:** Hybrid search with RRF (Reciprocal Rank Fusion) - Phase 68
- **Query:**
  - `q`: string (required)
  - `limit`: number (1-1000, default 100)
  - `mode`: semantic|keyword|hybrid (default hybrid)
  - `file_types`: comma-separated filter (optional)
  - `collection`: tree|leaf|shared (default tree)
  - `skip_cache`: boolean
- **Response:**
  ```json
  {
    "success": true,
    "results": [{
      "id": "string",
      "score": number,
      "rrf_score": number,
      "explanation": "string",
      ...
    }],
    "count": number,
    "mode": "string",
    "timing_ms": number,
    "sources": ["qdrant", "weaviate"],
    "config": {
      "semantic_weight": number,
      "keyword_weight": number,
      "rrf_k": number
    }
  }
  ```
- **RRF Configuration:**
  - `VETKA_SEMANTIC_WEIGHT`: 0.5 (default)
  - `VETKA_KEYWORD_WEIGHT`: 0.3 (default)
  - `VETKA_RRF_K`: 60 (default)
  - `VETKA_HYBRID_CACHE_TTL`: 300s (default)

#### GET `/api/search/hybrid/stats`
- **Purpose:** Get hybrid search service statistics
- **Response:**
  ```json
  {
    "success": true,
    "stats": {
      "backend_status": {},
      "cache_stats": {},
      "configuration": {}
    }
  }
  ```

#### POST `/api/scanner/rescan`
- **Purpose:** Trigger full reindex with cleanup (Phase 69, Phase 83)
- **Query:**
  - `path`: string (optional, defaults to cwd)
- **Response:**
  ```json
  {
    "success": true,
    "status": "completed|stopped",
    "indexed": number,
    "skipped": number,
    "deleted": number,
    "total_scanned": number,
    "errors": number,
    "path": "string",
    "stopped": boolean,
    "scanner_stats": {}
  }
  ```
- **Services Called:** QdrantIncrementalUpdater, LocalScanner
- **Socket.IO Events:** scan_started, scan_progress, scan_complete/scan_stopped

#### POST `/api/scanner/stop`
- **Purpose:** Stop running scan gracefully (Phase 83)
- **Response:**
  ```json
  {
    "success": true,
    "status": "stop_requested",
    "message": "string",
    "current_stats": {}
  }
  ```

#### GET `/api/scanner/status`
- **Purpose:** Get current scanner status (Phase 83)
- **Response:**
  ```json
  {
    "success": true,
    "stop_requested": boolean,
    "stats": {}
  }
  ```

#### DELETE `/api/scanner/clear-all`
- **Purpose:** Delete all points from vetka_elisya collection (Phase 84)
- **Response:**
  ```json
  {
    "success": true,
    "message": "string",
    "deleted_count": number,
    "collection": "string"
  }
  ```
- **Services Called:** Qdrant

---

### 5. FILES ENDPOINTS (`/api/files/*`)

**Router:** `src/api/routes/files_routes.py`

#### POST `/api/files/read`
- **Purpose:** Read file content with artifact/binary support
- **Body:** `{"path": "string (required)"}`
- **Response:**
  ```json
  {
    "success": true,
    "path": "string",
    "content": "string",
    "encoding": "utf-8|binary",
    "size": number,
    "hash": "string"
  }
  ```
- **Note:** Handles artifacts (/artifact/xxx.md → data/artifacts/xxx.md)

#### POST `/api/files/save`
- **Purpose:** Save file content
- **Body:**
  ```json
  {
    "path": "string (required)",
    "content": "string (required)"
  }
  ```
- **Response:** `{"success": true, "path": "string", "size": number}`

#### GET `/api/files/raw`
- **Purpose:** Raw file serving
- **Query:** `path=string (required)`
- **Response:** File content with appropriate MIME type

#### POST `/api/files/resolve-path`
- **Purpose:** Smart file path resolution for drag & drop
- **Body:**
  ```json
  {
    "filename": "string",
    "relativePath": "string (optional)",
    "contentHash": "string (optional)",
    "fileSize": number (optional)
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "path": "string",
    "resolved": boolean
  }
  ```

#### GET `/api/file/show-in-finder`
- **Purpose:** Open file location in system file explorer
- **Query:** `path=string`
- **Response:** `{"success": true}`
- **Platform:** macOS (open), Windows (explorer), Linux (xdg-open)

---

### 6. GROUP CHAT ENDPOINTS (`/api/groups/*`)

**Router:** `src/api/routes/group_routes.py`

#### GET `/api/groups`
- **Purpose:** Get all groups
- **Response:**
  ```json
  {
    "groups": [{
      "id": "string",
      "name": "string",
      "admin_agent_id": "string",
      "participants": [],
      "created_at": number
    }]
  }
  ```

#### POST `/api/groups`
- **Purpose:** Create new group
- **Body:**
  ```json
  {
    "name": "string",
    "description": "string",
    "admin_agent_id": "string",
    "admin_model_id": "string",
    "admin_display_name": "string",
    "project_id": "string (optional)"
  }
  ```
- **Response:** `{"group": {...}}`

#### GET `/api/groups/{group_id}`
- **Purpose:** Get group by ID
- **Response:** `{"group": {...}}`

#### POST `/api/groups/{group_id}/participants`
- **Purpose:** Add participant to group
- **Body:**
  ```json
  {
    "agent_id": "string",
    "model_id": "string",
    "display_name": "string",
    "role": "worker|admin"
  }
  ```
- **Response:** `{"success": true}`

#### POST `/api/groups/{group_id}/messages`
- **Purpose:** Send message in group
- **Body:**
  ```json
  {
    "sender_id": "string",
    "content": "string",
    "message_type": "chat|system"
  }
  ```
- **Response:** `{"message": {...}}`

#### POST `/api/groups/{group_id}/tasks`
- **Purpose:** Assign task to agent in group
- **Body:**
  ```json
  {
    "assigner_id": "string",
    "assignee_id": "string",
    "description": "string",
    "dependencies": ["string"]
  }
  ```
- **Response:** `{"task": {...}}`

#### POST `/api/groups/{group_id}/models/add` (Phase 80.19)
- **Purpose:** Add model to group directly
- **Body:**
  ```json
  {
    "model_id": "string",
    "role": "worker"
  }
  ```
- **Response:** `{"success": true}`

---

### 7. MODEL REGISTRY ENDPOINTS (`/api/models/*`)

**Router:** `src/api/routes/model_routes.py`

#### GET `/api/models`
- **Purpose:** List all models in phonebook
- **Response:**
  ```json
  {
    "models": [{...}],
    "count": number
  }
  ```

#### GET `/api/models/available`
- **Purpose:** List available models only
- **Response:** `{"models": [{...}]}`

#### GET `/api/models/local`
- **Purpose:** List local (Ollama) models
- **Response:** `{"models": [{...}]}`

#### GET `/api/models/free`
- **Purpose:** List free models (local + cloud free tier)
- **Response:** `{"models": [{...}]}`

#### GET `/api/models/favorites`
- **Purpose:** List favorite models
- **Response:** `{"models": [{...}]}`

#### GET `/api/models/recent`
- **Purpose:** List recently used models
- **Response:** `{"models": [{...}]}`

#### POST `/api/models/favorites/{model_id}`
- **Purpose:** Add model to favorites
- **Response:** `{"success": true}`

#### DELETE `/api/models/favorites/{model_id}`
- **Purpose:** Remove model from favorites
- **Response:** `{"success": true}`

#### POST `/api/models/keys`
- **Purpose:** Add API key for provider
- **Body:** `{"provider": "string", "key": "string"}`
- **Response:** `{"success": true, "provider": "string"}`

#### DELETE `/api/models/keys/{provider}`
- **Purpose:** Delete API key for provider
- **Response:** `{"success": true}`

---

### 8. WATCHER ENDPOINTS (`/api/watcher/*`)

**Router:** `src/api/routes/watcher_routes.py`

#### POST `/api/watcher/add`
- **Purpose:** Add directory to watch list
- **Body:**
  ```json
  {
    "path": "string (required)",
    "recursive": boolean (default true)
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "path": "string",
    "watching": boolean
  }
  ```

#### POST `/api/watcher/add-from-browser`
- **Purpose:** Add files scanned from browser FileSystem API
- **Body:**
  ```json
  {
    "rootName": "string",
    "files": [{
      "name": "string",
      "relativePath": "string",
      "size": number,
      "type": "string",
      "lastModified": number
    }],
    "timestamp": number (optional)
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "indexed": number,
    "skipped": number,
    "root_name": "string"
  }
  ```

#### POST `/api/watcher/remove`
- **Purpose:** Remove directory from watch list
- **Body:** `{"path": "string"}`
- **Response:** `{"success": true}`

#### GET `/api/watcher/status`
- **Purpose:** Get current watcher status
- **Response:**
  ```json
  {
    "success": true,
    "watching_paths": ["string"],
    "file_count": number,
    "last_update": number
  }
  ```

#### GET `/api/watcher/heat`
- **Purpose:** Get adaptive scanner heat scores
- **Response:**
  ```json
  {
    "success": true,
    "heat_scores": {
      "path": number
    }
  }
  ```

---

### 9. HEALTH ENDPOINTS (`/api/health/*`)

**Router:** `src/api/routes/health_routes.py`

#### GET `/api/health/deep`
- **Purpose:** Deep health check - tests all components
- **Response:**
  ```json
  {
    "status": "healthy|degraded|unhealthy",
    "checks": {
      "component_name": {
        "name": "display name",
        "status": "healthy|degraded|unavailable",
        "available": boolean,
        "latency_ms": number
      }
    },
    "timestamp": number
  }
  ```

#### GET `/api/health/ready` (K8s readiness probe)
- **Purpose:** Quick readiness check
- **Response:** `{"status": "ready"}`

#### GET `/api/health/live` (K8s liveness probe)
- **Purpose:** Quick liveness check
- **Response:** `{"status": "alive"}`

#### GET `/api/health/metrics`
- **Purpose:** Current metrics for monitoring
- **Response:**
  ```json
  {
    "uptime_seconds": number,
    "requests": number,
    "errors": number,
    "components": {}
  }
  ```

---

### 10. METRICS ENDPOINTS (`/api/metrics/*`)

**Router:** `src/api/routes/metrics_routes.py`

#### GET `/api/metrics/dashboard`
- **Purpose:** Get dashboard metrics summary
- **Response:**
  ```json
  {
    "requests_per_second": number,
    "avg_response_time_ms": number,
    "error_rate": number,
    "uptime": "string"
  }
  ```

#### GET `/api/metrics/agents`
- **Purpose:** Get agent performance metrics
- **Response:**
  ```json
  {
    "PM": {"calls": number, "avg_time": number, "quality": number},
    "Dev": {...},
    "QA": {...}
  }
  ```

---

### 11. DEBUG ENDPOINTS (`/api/debug/*`)

**Router:** `src/api/routes/debug_routes.py`

#### GET `/api/debug/inspect`
- **Purpose:** Full tree state inspection
- **Response:** Complete tree structure with positions, metadata

#### GET `/api/debug/formulas`
- **Purpose:** Current layout formulas and constants
- **Response:**
  ```json
  {
    "Y_PER_DEPTH": number,
    "BRANCH_LENGTH": number,
    "FAN_ANGLE": number,
    "FILE_SPACING": number
  }
  ```

#### GET `/api/debug/tree-state`
- **Purpose:** Quick tree health check
- **Response:**
  ```json
  {
    "files_count": number,
    "folders_count": number,
    "total_nodes": number
  }
  ```

#### GET `/api/debug/recent-errors`
- **Purpose:** Last N errors from logs
- **Query:** `limit=number`
- **Response:**
  ```json
  {
    "errors": [{
      "timestamp": number,
      "error": "string",
      "source": "string"
    }]
  }
  ```

#### GET `/api/debug/modes`
- **Purpose:** Current mode states (blend values, etc)
- **Response:** Blend values, layout modes, active features

#### GET `/api/debug/chat-context`
- **Purpose:** Get current chat context (like internal agents)
- **Response:** Current chat state, agents, memory

#### GET `/api/debug/team-messages`
- **Purpose:** Get team messages buffer for MCP agents
- **Response:**
  ```json
  {
    "messages": [{
      "id": "string",
      "from": "string",
      "to": "string",
      "message": "string",
      "conversation_id": "string",
      "timestamp": number,
      "pending": boolean
    }],
    "count": number
  }
  ```

#### POST `/api/debug/camera-focus`
- **Purpose:** Control 3D camera position
- **Body:**
  ```json
  {
    "target": "string",
    "zoom": "fit|close|medium|far",
    "highlight": boolean
  }
  ```
- **Response:** `{"success": true}`

---

## SOCKET.IO EVENTS

**Server Implementation:** `src/api/handlers/connection_handlers.py`, various socket handlers

### Connection Events

#### connect
- **Emitter:** Client connects to WebSocket
- **Handler:** Confirms connection
- **Response:** `{"data": "Connected to VETKA Phase 53", "timestamp": number}`

#### disconnect
- **Emitter:** Client disconnects from WebSocket
- **Handler:** Cleans up per-session chat manager
- **Cleanup:** Removes ChatRegistry entry for session

### Chat Events

#### user_message
- **Purpose:** User sends message (usually emitted by `/api/chat` REST endpoint)
- **Data:**
  ```json
  {
    "message": "string",
    "model": "string (optional)",
    "conversation_id": "string"
  }
  ```

#### chat_response
- **Purpose:** Server sends response to user message
- **Data:**
  ```json
  {
    "content": "string",
    "conversation_id": "string",
    "model": "string",
    "processing_time": number
  }
  ```

#### chat_error
- **Purpose:** Error occurred during chat processing
- **Data:**
  ```json
  {
    "error": "string",
    "conversation_id": "string"
  }
  ```

### Scanner Events

#### scan_started
- **Purpose:** File scan started
- **Data:** `{"path": "string", "status": "scanning"}`

#### scan_progress
- **Purpose:** Progress update during scan (every 10 files)
- **Data:**
  ```json
  {
    "current": number,
    "indexed": number,
    "file": "string",
    "path": "string"
  }
  ```

#### scan_complete
- **Purpose:** Scan completed successfully
- **Data:**
  ```json
  {
    "indexed": number,
    "skipped": number,
    "total": number,
    "deleted": number,
    "path": "string",
    "stopped": false
  }
  ```

#### scan_stopped
- **Purpose:** Scan was stopped by user
- **Data:**
  ```json
  {
    "indexed": number,
    "skipped": number,
    "total": number,
    "path": "string",
    "stopped": true
  }
  ```

#### scan_stop_requested
- **Purpose:** Stop signal sent to running scan
- **Data:**
  ```json
  {
    "status": "stop_requested",
    "message": "Stop signal sent - scan will halt at next checkpoint"
  }
  ```

#### scan_cleared
- **Purpose:** All scans cleared from collection
- **Data:**
  ```json
  {
    "collection": "string",
    "deleted_count": number,
    "status": "cleared"
  }
  ```

### Tree/Layout Events

#### tree_updated
- **Purpose:** Tree structure or layout changed
- **Data:** Updated tree structure

#### knowledge_graph_updated
- **Purpose:** Knowledge graph was recalculated
- **Data:** Updated graph structure

#### camera_moved
- **Purpose:** 3D camera position changed
- **Data:**
  ```json
  {
    "position": {"x": number, "y": number, "z": number},
    "target": "string"
  }
  ```

### File Watcher Events

#### file_created
- **Purpose:** New file detected in watched directory
- **Data:**
  ```json
  {
    "path": "string",
    "size": number,
    "timestamp": number
  }
  ```

#### file_modified
- **Purpose:** File in watched directory was modified
- **Data:**
  ```json
  {
    "path": "string",
    "timestamp": number
  }
  ```

#### file_deleted
- **Purpose:** File in watched directory was deleted
- **Data:**
  ```json
  {
    "path": "string",
    "timestamp": number
  }
  ```

---

## OPENCODE BRIDGE ENDPOINTS

**Router:** `src/opencode_bridge/routes.py`
**Prefix:** `/api/bridge/`
**Status:** Optional (enabled via `OPENCODE_BRIDGE_ENABLED=true`)
**Purpose:** Local-only bridge for OpenRouter key rotation

### GET `/api/bridge/openrouter/keys`
- **Purpose:** Get available OpenRouter keys (masked) for UI
- **Response:**
  ```json
  {
    "enabled": true,
    "provider": "openrouter",
    "keys": ["masked_key_1", "masked_key_2"],
    "total": number
  }
  ```

### POST `/api/bridge/openrouter/invoke`
- **Purpose:** Invoke OpenRouter model with automatic key rotation
- **Body:**
  ```json
  {
    "model_id": "string (required)",
    "messages": [{...}] (required),
    "temperature": number (optional),
    "max_tokens": number (optional),
    ...other OpenRouter params
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "model": "string",
    "content": "string",
    "tokens": {"prompt": number, "completion": number},
    "key_rotated": boolean
  }
  ```
- **Key Rotation:** Automatic rotation on rate-limit errors

### GET `/api/bridge/openrouter/stats`
- **Purpose:** Get rotation statistics for UI
- **Response:**
  ```json
  {
    "enabled": true,
    "provider": "openrouter",
    "stats": {
      "total_keys": number,
      "active_keys": number,
      "rate_limited_keys": number,
      "current_key_index": number,
      "last_rotation": "ISO timestamp"
    }
  }
  ```

### GET `/api/bridge/openrouter/health`
- **Purpose:** Health check for bridge
- **Response:**
  ```json
  {
    "status": "healthy",
    "bridge_enabled": true,
    "provider": "openrouter"
  }
  ```

---

## MCP TOOL ENDPOINTS

**Purpose:** Integration with Claude Code (MCP - Model Context Protocol)

These endpoints are not traditional REST endpoints but represent MCP tools exposed through `/api/mcp/*` namespace.

### MCP Tool Categories

#### File Operations
- `read_file(path)`: Read file content
- `write_file(path, content)`: Write file content
- `search_files(pattern)`: Search files by pattern
- `list_files(path)`: List directory contents

#### Semantic Search
- `semantic_search(query, limit)`: Find files by semantic similarity
- `search_hybrid(query, limit, mode)`: Hybrid search with RRF

#### Tree Operations
- `get_tree_data(mode)`: Fetch tree structure
- `get_knowledge_graph()`: Fetch knowledge graph
- `export_tree(format)`: Export to Blender/GLB/OBJ

#### Chat & Agents
- `call_agent(agent_name, message)`: Route to specific agent
- `send_to_group(group_id, message)`: Send to group chat
- `get_model_for_task(task, complexity)`: Get best model

#### Scanning & Indexing
- `trigger_rescan(path)`: Start full reindex
- `stop_scanner()`: Stop running scan
- `add_watcher(path)`: Start watching directory
- `clear_all_scans()`: Clear all indexed files

#### Configuration
- `get_config()`: Get current config
- `update_config(updates)`: Update config
- `add_api_key(provider, key)`: Add/update API key
- `detect_api_key(key)`: Auto-detect key type

### MCP Integration Flow

1. Claude Code (MCP) → Uses defined tools
2. Tool call → Forwarded to `/api/mcp/{tool_name}`
3. VETKA processes → Returns structured response
4. Response → Back to Claude Code
5. Claude Code → Uses response to continue reasoning

---

## ARCHITECTURAL PATTERNS

### Request Flow Examples

#### 1. Simple Chat Flow
```
User Input
  ↓
POST /api/chat
  ├→ Message validation
  ├→ Model selection (MODEL_ROUTER_V2)
  ├→ API Gateway call
  ├→ Memory save (Qdrant + Weaviate)
  └→ EvalAgent scoring
  ↓
Response returned
```

#### 2. Intelligent Chat Flow (with Hostess)
```
User Input
  ↓
POST /api/chat
  ├→ Message validation
  ├→ Hostess Decision Engine
  │   ├→ quick_answer → Return immediately
  │   ├→ search → Query Qdrant, return results
  │   ├→ show_file → Read file, return content
  │   └→ chain_call → Continue to orchestrator
  ├→ Orchestrator (if chain_call)
  │   ├→ PM Agent (Planning)
  │   ├→ Dev Agent (Implementation)
  │   └→ QA Agent (Testing)
  ├→ Memory save (Weaviate + Qdrant)
  └→ EvalAgent scoring
  ↓
Response returned
```

#### 3. Search Flow
```
GET /api/search/hybrid?q=...&mode=hybrid
  ├→ Query validation
  ├→ Cache check
  ├→ Semantic search (Qdrant) [50% weight]
  ├→ Keyword search (Weaviate) [30% weight]
  ├→ RRF fusion [merge scores]
  ├→ Cache result (5 min TTL)
  └→ Return merged results
```

#### 4. Scanner Flow
```
POST /api/scanner/rescan?path=/path
  ├→ Reset stop flag
  ├→ Delete old entries from Qdrant
  ├→ Scan directory (LocalScanner)
  │   ├→ Emit scan_started event
  │   ├→ Process each file
  │   ├→ Emit scan_progress (every 10 files)
  │   ├→ Check stop flag at each iteration
  │   └→ Update Qdrant vectors
  ├→ Emit scan_complete/stopped event
  └→ Return statistics
```

### Service Dependencies

```
ChatRoute (/api/chat)
  ├→ Hostess Agent
  ├→ Orchestrator
  │   ├→ PM Agent
  │   ├→ Dev Agent
  │   ├→ QA Agent
  │   └→ EvalAgent
  ├→ Memory Manager
  │   ├→ Weaviate
  │   └→ Qdrant
  ├→ Model Router v2
  │   └→ API Gateway v2
  ├→ Ollama (fallback)
  └→ KeyManager (API keys)

SearchRoute (/api/search/hybrid)
  ├→ HybridSearch
  │   ├→ Qdrant (semantic)
  │   ├→ Weaviate (keyword)
  │   └→ RRF Fusion
  ├→ Cache (in-memory)
  └→ SemanticTagger

TreeRoute (/api/tree/data)
  ├→ Qdrant (fetch scanned files)
  ├→ CAM Engine (surprise metrics)
  ├→ Layout Engine (FAN layout)
  └→ Position Calculator

ScannerRoute (/api/scanner/rescan)
  ├→ QdrantIncrementalUpdater
  ├→ LocalScanner
  ├→ File Watcher
  └→ SocketIO (progress events)
```

### Configuration Hierarchy

1. **Environment Variables** (highest priority)
   - `VETKA_SEMANTIC_WEIGHT`: 0.5
   - `VETKA_KEYWORD_WEIGHT`: 0.3
   - `VETKA_RRF_K`: 60
   - `VETKA_HYBRID_CACHE_TTL`: 300
   - `OPENCODE_BRIDGE_ENABLED`: false
   - `ELISYA_ENABLED`: true
   - `PARALLEL_MODE`: false

2. **Config File** (data/config.json)
   - API keys
   - Model preferences
   - Routing rules
   - Tool definitions

3. **Runtime Settings** (app.state)
   - Feature flags
   - Component references
   - DI container

---

## ERROR HANDLING

All endpoints follow consistent error patterns:

```json
{
  "success": false,
  "error": "Human-readable error message",
  "status_code": 400|500|503,
  "timestamp": number
}
```

**Common Status Codes:**
- `400`: Bad request (validation error)
- `404`: Not found (resource doesn't exist)
- `500`: Server error (unexpected exception)
- `503`: Service unavailable (component not initialized)

---

## CACHING STRATEGY

| Endpoint | Cache Type | TTL | Max Size |
|----------|-----------|-----|----------|
| `/api/search/semantic` | In-memory | 5 min | 100 entries |
| `/api/search/hybrid` | In-memory | Configurable | 100 entries |
| `/api/tree/data` | Memory | Session | Per-client |
| `/api/tree/knowledge-graph` | Memory | Session | Per-client |
| `/api/models` | Memory | Session | Single |

---

## RATE LIMITING

- **Connection events:** Rate-limited logging (5s minimum between logs)
- **Scanner events:** Progress emitted every 10 files
- **No hard rate limits** - suitable for local/single-user app

---

## Authentication & Authorization

- **No authentication required** (local-only application)
- **All endpoints accessible** to connected clients
- **Socket.IO events** require active connection
- **OpenCode Bridge** local-only, no external access

---

## Future Endpoints (Roadmap)

- `/api/eval/*` - Evaluation scoring endpoints
- `/api/knowledge/*` - Knowledge graph management
- `/api/triple-write/*` - Memory persistence stats
- `/api/ocr/*` - Optical character recognition
- `/api/workflow/*` - Workflow execution
- `/api/embeddings/*` - Embedding management

---

**Generated:** 2026-01-25
**VETKA Phase:** 93
**Total API Endpoints Documented:** 66+
