# Phase 1 Quick Start - MCP UI & Context

**Last Updated:** 2026-01-22
**Author:** Haiku Agent B

## In 2 Minutes

**Question:** Can VETKA display what subagents are doing?
**Answer:** YES - need ~370 LOC across 3 new files.

**Question:** Can Claude Code get context by just saying "branch=mcp"?
**Answer:** YES - implement `vetka_get_context` tool.

**Question:** Will this waste tokens?
**Answer:** NO - Qdrant already has embeddings, just add caching.

---

## Implementation Tasks

### Task 1: Context Retrieval Tool (1-2 hours)

**File:** Create `/src/mcp/tools/context_tool.py`

```python
class ContextBranchTool(BaseMCPTool):
    """Get full context for a code branch/topic"""

    @property
    def name(self) -> str:
        return "vetka_get_context"

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        branch = arguments.get("branch")
        depth = arguments.get("depth", "medium")

        # 1. Get memory/qdrant
        memory = self._get_memory()

        # 2. Semantic search
        query_vector = get_embedding(branch)
        results = memory.qdrant.search(
            collection_name='vetka_elisya',
            query_vector=query_vector,
            limit=50 if depth == "deep" else 20
        )

        # 3. Aggregate context
        context_files = []
        for result in results[:20]:
            file_path = result.payload.get('path')
            content = read_file(file_path)  # Full content
            context_files.append({
                'path': file_path,
                'relevance': result.score,
                'content': content
            })

        return {
            'success': True,
            'result': {
                'branch': branch,
                'files_found': len(context_files),
                'context': context_files
            }
        }
```

**Test:**
```bash
# Via MCP
vetka_get_context branch="mcp" depth="medium"

# Should return all files related to MCP architecture
```

---

### Task 2: Register Tool in Bridge (15 minutes)

**File:** Modify `/src/mcp/vetka_mcp_bridge.py`

```python
# In list_tools() around line 82:
Tool(
    name="vetka_get_context",
    description="Retrieve full context for a code branch or topic. "
               "Returns all related files with semantic ranking.",
    inputSchema={
        "type": "object",
        "properties": {
            "branch": {
                "type": "string",
                "description": "Branch name (e.g., 'authentication', 'mcp', 'api')"
            },
            "depth": {
                "type": "string",
                "enum": ["shallow", "medium", "deep"],
                "default": "medium"
            }
        },
        "required": ["branch"]
    }
),

# In call_tool() around line 640 (before final else):
elif name == "vetka_get_context":
    from src.mcp.tools.context_tool import ContextBranchTool
    tool = ContextBranchTool()
    result = tool.execute(arguments)
    return [TextContent(type="text", text=format_context_result(result))]
```

**Add formatter:**
```python
def format_context_result(result: dict) -> str:
    """Format context retrieval result"""
    if not result.get("success"):
        return f"Error: {result.get('error')}"

    data = result.get('result', {})
    files = data.get('context', [])

    lines = [
        f"Context for: {data.get('branch')}",
        f"Files found: {len(files)}",
        ""
    ]

    for f in files[:10]:
        lines.append(f"- {f['path']} (relevance: {f['relevance']:.2f})")

    if len(files) > 10:
        lines.append(f"... and {len(files) - 10} more")

    return "\n".join(lines)
```

---

### Task 3: MCP Logging API (1 hour)

**File:** Create `/src/api/routes/mcp_routes.py`

```python
from fastapi import APIRouter, Request
from datetime import datetime
from pathlib import Path
import json

router = APIRouter(prefix="/api/mcp", tags=["mcp"])

# In-memory log (production: use database)
_mcp_log = []
MAX_LOG_SIZE = 1000

@router.get("/requests")
async def get_mcp_requests(limit: int = 50):
    """Get recent MCP requests"""
    requests = [r for r in _mcp_log if 'tool' in r and 'arguments' in r]
    return {'requests': requests[-limit:], 'total': len(requests)}

@router.get("/responses")
async def get_mcp_responses(limit: int = 50):
    """Get recent MCP responses"""
    responses = [r for r in _mcp_log if 'result' in r]
    return {'responses': responses[-limit:], 'total': len(responses)}

@router.post("/save")
async def save_mcp_log(request: Request):
    """Save MCP log to /docs/mcp_chat/"""
    body = await request.json()
    session_id = body.get('session_id', 'default')

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"mcp_chat_{session_id}_{timestamp}.json"
    filepath = Path("docs/mcp_chat") / filename

    filepath.write_text(json.dumps(_mcp_log, indent=2))

    return {
        'success': True,
        'path': str(filepath),
        'entries': len(_mcp_log)
    }

def add_mcp_request(tool: str, arguments: dict):
    """Log a tool request"""
    global _mcp_log
    _mcp_log.append({
        'type': 'request',
        'tool': tool,
        'arguments': arguments,
        'timestamp': datetime.now().isoformat()
    })
    if len(_mcp_log) > MAX_LOG_SIZE:
        _mcp_log.pop(0)

def add_mcp_response(tool: str, result: dict, duration_ms: float):
    """Log a tool response"""
    global _mcp_log
    _mcp_log.append({
        'type': 'response',
        'tool': tool,
        'result': result,
        'duration_ms': duration_ms,
        'timestamp': datetime.now().isoformat()
    })
    if len(_mcp_log) > MAX_LOG_SIZE:
        _mcp_log.pop(0)
```

**Register in main.py:**
```python
from src.api.routes.mcp_routes import router as mcp_router
app.include_router(mcp_router)
```

---

### Task 4: Integration Hooks (30 minutes)

**In `/src/mcp/vetka_mcp_bridge.py` call_tool():**

```python
import time

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    start_time = time.time()

    # Log request
    try:
        from src.api.routes.mcp_routes import add_mcp_request
        add_mcp_request(name, arguments)
    except:
        pass  # Ignore logging errors

    try:
        # ... existing tool execution code ...
        result = execute_tool(name, arguments)

        # Log response
        duration_ms = (time.time() - start_time) * 1000
        try:
            from src.api.routes.mcp_routes import add_mcp_response
            add_mcp_response(name, result, duration_ms)
        except:
            pass  # Ignore logging errors

        return result

    except Exception as e:
        # ... existing error handling ...
        pass
```

---

## Testing Checklist

- [ ] Start VETKA: `python main.py`
- [ ] Test context tool via MCP:
  ```
  vetka_get_context branch="mcp" depth="medium"
  ```
- [ ] Should return: 10-15 files related to MCP
- [ ] Check API endpoints:
  ```bash
  curl http://localhost:5001/api/mcp/requests
  curl http://localhost:5001/api/mcp/responses
  ```
- [ ] Should show requests/responses from tool calls
- [ ] Test save:
  ```bash
  curl -X POST http://localhost:5001/api/mcp/save \
    -H "Content-Type: application/json" \
    -d '{"session_id": "test"}'
  ```
- [ ] Check `/docs/mcp_chat/mcp_chat_test_*.json` exists

---

## Success Criteria

✅ Claude Code can call: `vetka_get_context branch="authentication"`
✅ Returns 10-30 files with relevance scores
✅ MCP requests/responses logged automatically
✅ Responses saved to `/docs/mcp_chat/` directory
✅ No performance degradation (< 50ms added latency)
✅ Caching prevents token waste (repeat queries instant)

---

## File Summary

| File | Lines | Status |
|------|-------|--------|
| /src/mcp/tools/context_tool.py | 150 | CREATE |
| /src/api/routes/mcp_routes.py | 80 | CREATE |
| /src/mcp/vetka_mcp_bridge.py | +50 | MODIFY |
| /main.py | +3 | MODIFY |

**Total new code: ~283 LOC**
**Estimated effort: 3-4 hours**

---

## Phase 1 Deliverables

1. ✅ Context retrieval tool (`vetka_get_context`)
2. ✅ MCP logging API (`/api/mcp/*`)
3. ✅ Request/response persistence (`/docs/mcp_chat/`)
4. ✅ Analysis report (PHASE1_HAIKU_B_MCP_UI_CONTEXT.md)

Ready for Phase 2: Real-time UI & visualization

---

**Generated:** 2026-01-22 22:52 UTC
**Next:** Implement tasks in order above
