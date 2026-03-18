# RECON: vetka_read_file broken (file_path vs path)

**Phase:** 191 — DEBUG Session
**Date:** 2026-03-18
**Severity:** CRITICAL — base tool is non-functional
**Estimated fix:** ~5 min

---

## Problem

`vetka_read_file` sends `file_path` in JSON body, but FastAPI backend expects `path`. Pydantic validation silently drops the unknown field, resulting in empty path and 400 error.

## Mismatch Chain

```
MCP Schema (file_path) → Bridge sends {"file_path": "..."} → Backend expects {"path": "..."} → FAIL
```

## Exact Locations

### 1. MCP Bridge — Schema Declaration
**File:** `src/mcp/vetka_mcp_bridge.py:351-364`
```python
Tool(
    name="vetka_read_file",
    inputSchema={
        "properties": {
            "file_path": { ... }        # <-- declares file_path
        },
        "required": ["file_path"]
    }
),
```

### 2. MCP Bridge — Handler
**File:** `src/mcp/vetka_mcp_bridge.py:1123-1130`
```python
elif name == "vetka_read_file":
    file_path = arguments.get("file_path", "")   # reads file_path
    response = await http_client.post(
        "/api/files/read",
        json={"file_path": file_path}             # sends file_path — WRONG KEY
    )
```

### 3. Backend — Pydantic Model
**File:** `src/api/routes/files_routes.py:49-51`
```python
class FileReadRequest(BaseModel):
    path: str                                      # expects "path", NOT "file_path"
```

### 4. Backend — Handler
**File:** `src/api/routes/files_routes.py:102-124`
```python
@router.post("/read")
async def read_file(req: FileReadRequest):
    file_path = req.path                           # reads req.path
```

## Comparison with Working Tools

| Tool | Schema param | Bridge sends | Backend expects | Status |
|------|-------------|-------------|----------------|--------|
| vetka_read_file | `file_path` | `file_path` | `path` | BROKEN |
| vetka_edit_file | `path` | `path` | `path` | OK |
| vetka_list_files | `path` | `path` | `path` | OK |

## Fix (Option A — RECOMMENDED)

Align MCP Bridge with backend convention (`path`). All other file tools already use `path`.

**`src/mcp/vetka_mcp_bridge.py`:**
1. Line ~357: `"file_path"` → `"path"` (schema property)
2. Line ~362: `"required": ["file_path"]` → `"required": ["path"]`
3. Line ~1125: `arguments.get("file_path")` → `arguments.get("path")`
4. Line ~1129: `json={"file_path": file_path}` → `json={"path": file_path}`

## Fix (Option B — Not recommended)

Change backend model. Would break consistency with other tools.

## Additional Finding

`vetka_task_import` has same `file_path` mismatch but is deprecated (moved to MYCELIUM MCP).
