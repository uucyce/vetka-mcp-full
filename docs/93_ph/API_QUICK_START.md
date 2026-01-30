# VETKA API Quick Start - Phase 93

## One-Liner Summary
VETKA exposes **66+ REST endpoints** (FastAPI), **10+ Socket.IO events**, and **optional OpenCode Bridge** for a unified AI workspace with semantic search, intelligent routing, and real-time file scanning.

## Base URL
```
http://localhost:8000/api/
```

## Quick Endpoint Categories

### Most Important (Daily Use)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| **POST /chat** | POST | Universal chat - routes to agents/LLM |
| **GET /search/hybrid** | GET | Search files with RRF fusion |
| **GET /tree/data** | GET | Get 3D tree visualization |
| **POST /scanner/rescan** | POST | Reindex directory |
| **GET /tree/knowledge-graph** | GET | Get knowledge graph structure |

### Configuration & Setup

| Endpoint | Method | Purpose |
|----------|--------|---------|
| POST /keys/add | POST | Add API key |
| POST /keys/add-smart | POST | Auto-detect and add key |
| GET /models | GET | List all available models |
| GET /config | GET | Get current config |
| POST /config | POST | Update config |

### File Operations

| Endpoint | Method | Purpose |
|----------|--------|---------|
| POST /files/read | POST | Read file content |
| POST /files/save | POST | Save file content |
| POST /watcher/add | POST | Watch directory for changes |
| GET /watcher/status | GET | Get watcher status |

### Debugging & Monitoring

| Endpoint | Method | Purpose |
|----------|--------|---------|
| GET /health/deep | GET | Deep component health check |
| GET /debug/tree-state | GET | Quick tree status |
| GET /metrics/dashboard | GET | System metrics |
| POST /scanner/stop | POST | Stop running scan |

---

## Authentication

**None required** - VETKA is local-only. All endpoints are accessible to connected clients.

---

## Common Request Patterns

### 1. Simple Chat
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is this project about?",
    "model_override": "qwen2:7b"
  }'
```

**Response includes:**
- `response`: AI's reply
- `model`: Model used
- `processing_time_ms`: Latency
- `eval_score`: Quality score (0-10)

### 2. Semantic Search
```bash
curl -X GET "http://localhost:8000/api/search/hybrid?q=authentication&mode=hybrid&limit=20"
```

**Response includes:**
- `results`: Array of matching files
- `count`: Number of results
- `sources`: Which backends (qdrant, weaviate)
- `timing_ms`: Search latency

### 3. Get Tree Visualization
```bash
curl -X GET "http://localhost:8000/api/tree/data?mode=directory"
```

**Response includes:**
- `tree.nodes`: All files/folders with positions
- `tree.edges`: Folder→file relationships
- `tree.metadata`: Statistics

### 4. Trigger Rescan
```bash
curl -X POST "http://localhost:8000/api/scanner/rescan?path=/home/user/project"
```

**Response includes:**
- `indexed`: Files added to index
- `skipped`: Files skipped
- `deleted`: Old entries removed
- `status`: completed or stopped

---

## Socket.IO Events (Real-Time)

### Connect
```javascript
const socket = io('http://localhost:8000');
socket.on('connect_response', (data) => {
  console.log(data.data); // "Connected to VETKA Phase 53"
});
```

### Scan Progress
```javascript
socket.on('scan_progress', (data) => {
  console.log(`Scanning: ${data.file} (${data.current}/${data.total})`);
});

socket.on('scan_complete', (data) => {
  console.log(`Indexed: ${data.indexed} files`);
});
```

---

## Key Concepts

### Hostess Agent
Routes user queries intelligently:
- **quick_answer**: Return immediately
- **search**: Query knowledge base
- **show_file**: Display file content
- **clarify**: Ask for clarification
- **agent_call**: Route to specific agent
- **chain_call**: Full agent pipeline

### Orchestrator Workflow
For complex tasks:
1. PM Agent: Planning
2. Dev Agent: Implementation
3. QA Agent: Testing/Quality check
4. EvalAgent: Scoring

### Hybrid Search (Phase 68)
Combines multiple backends with RRF fusion:
- **Semantic** (Qdrant): Vector similarity
- **Keyword** (Weaviate): BM25 text search
- **Graph** (Future): Relationship-based

Weights configurable via env vars:
- `VETKA_SEMANTIC_WEIGHT`: 0.5 (default)
- `VETKA_KEYWORD_WEIGHT`: 0.3 (default)
- `VETKA_RRF_K`: 60 (smoothing constant)

### CAM Engine
Generates surprise metrics for files:
- Tracks unexpected findings
- Highlights anomalies
- Powers `/api/tree/data` visualization

---

## Configuration Files

### Main Config
**Path:** `data/config.json`
```json
{
  "api_keys": {
    "openrouter": {
      "paid": "sk-or-...",
      "free": ["sk-or-...", ...]
    },
    "gemini": ["ai-..."],
    "anthropic": "sk-ant-..."
  },
  "models": {
    "available": {...},
    "defaults": {...},
    "aliases": {...}
  }
}
```

### API Key Detection
Auto-detects from key format:
- OpenRouter: `sk-or-` prefix
- Anthropic: `sk-ant-` prefix
- OpenAI: `sk-` prefix
- Gemini: `ai-` prefix
- Groq: `gsk-` prefix
- xAI: `xai-` prefix

---

## Performance Tips

1. **Use hybrid search** for best results (combines semantic + keyword)
2. **Cache semantic results** - 5 minute TTL by default
3. **Parallel mode** - Enable `PARALLEL_MODE=true` for concurrent agent execution
4. **Weaviate optional** - Falls back to Qdrant if Weaviate unavailable
5. **Local models first** - Use Ollama for privacy (qwen2:7b, llama3:8b)

---

## Error Responses

All errors follow consistent format:
```json
{
  "success": false,
  "error": "Human-readable message",
  "status_code": 400,
  "timestamp": 1234567890
}
```

**Common codes:**
- `400`: Bad request (validation)
- `404`: Not found
- `500`: Server error
- `503`: Service unavailable

---

## Advanced Usage

### Add API Key with Smart Detection
```bash
curl -X POST http://localhost:8000/api/keys/add-smart \
  -H "Content-Type: application/json" \
  -d '{"key": "your-key-here"}'
```

Response auto-detects provider and confidence score.

### Group Chat (Phase 56)
```bash
# Create group
curl -X POST http://localhost:8000/api/groups \
  -d '{
    "name": "Dev Team",
    "admin_agent_id": "pm_agent",
    "admin_model_id": "deepseek/deepseek-r1:free"
  }'

# Add participant
curl -X POST http://localhost:8000/api/groups/{group_id}/participants \
  -d '{
    "agent_id": "dev_agent",
    "model_id": "anthropic/claude-3-opus",
    "role": "worker"
  }'

# Send message
curl -X POST http://localhost:8000/api/groups/{group_id}/messages \
  -d '{
    "sender_id": "pm_agent",
    "content": "Start implementation"
  }'
```

### Export to Blender (Phase 17.2)
```bash
# Get as JSON
curl http://localhost:8000/api/tree/export/blender?format=json > tree.json

# Get as GLB (3D model)
curl http://localhost:8000/api/tree/export/blender?format=glb > tree.glb
```

---

## OpenCode Bridge (Optional)

Enable: `OPENCODE_BRIDGE_ENABLED=true`

### Get Keys (for rotation)
```bash
curl http://localhost:8000/api/bridge/openrouter/keys
```

### Invoke Model with Rotation
```bash
curl -X POST http://localhost:8000/api/bridge/openrouter/invoke \
  -d '{
    "model_id": "anthropic/claude-3-opus",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Check Rotation Stats
```bash
curl http://localhost:8000/api/bridge/openrouter/stats
```

---

## MCP Integration

Claude Code (MCP) can use VETKA tools:

```python
# In Claude Code MCP context
from vetka_mcp import semantic_search, get_tree_data, call_chat

# Search for files
results = semantic_search("authentication", limit=20)

# Get tree visualization
tree = get_tree_data(mode="directory")

# Send to chat
response = call_chat("How should I implement this?", model="deepseek/deepseek-r1:free")
```

---

## Next Steps

1. **Read Full Reference:** See `API_ENDPOINTS_REFERENCE.md` for complete documentation
2. **Explore the UI:** Open http://localhost:3000 in your browser
3. **Try Search:** Test `/api/search/hybrid` with your files
4. **Add Keys:** Use `/api/keys/add-smart` to add API keys
5. **Monitor Health:** Check `/api/health/deep` for component status

---

## Support Resources

- **Full Docs:** `docs/93_ph/API_ENDPOINTS_REFERENCE.md`
- **Router Code:** `src/api/routes/`
- **Handler Code:** `src/api/handlers/`
- **MCP Bridge:** `src/mcp/vetka_mcp_bridge.py`
- **OpenCode Bridge:** `src/opencode_bridge/`

---

**Generated:** 2026-01-25
**VETKA Phase:** 93
**Status:** Production Ready
