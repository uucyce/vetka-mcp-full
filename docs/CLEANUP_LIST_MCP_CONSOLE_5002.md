# CLEANUP LIST - MCP Console / Tauri / Port 5002

## STATUS: AUDIT COMPLETE (NO DELETIONS)
**Date:** 2026-01-23
**Task:** Mark all MCP Console references for removal by Sonnet
**Scope:** Port 5002, Tauri integration, console_client logging

---

## 1. FOLDERS TO ARCHIVE

### Complete Directory (for deletion):
```
/mcp_console/                           (entire folder)
├── .env.example
├── .gitignore
├── ARCHITECTURE.md
├── COLORS.md
├── INDEX.md
├── QUICKSTART.md
├── README.md
├── TAURI_SETUP.md
├── requirements.txt
├── setup.sh
├── test_client.py
├── server.py (PORT 5002 standalone)
└── frontend/
    ├── src/
    │   ├── App.tsx
    │   └── ... (all React components)
    ├── vite.config.ts (proxy to :5002)
    └── src-tauri/
        ├── Cargo.toml (Tauri config)
        ├── Cargo.lock
        ├── build.rs
        ├── tauri.conf.json (Tauri settings)
        ├── src/main.rs (Tauri app)
        ├── icons/
        └── target/ (build output)
```

---

## 2. PYTHON FILES WITH PORT 5002 / MCP CONSOLE REFERENCES

### A. `/src/mcp/vetka_mcp_bridge.py`
**Status:** CORE MCP BRIDGE - NEEDS CLEANUP

| Line(s) | Reference | Description |
|---------|-----------|-------------|
| 47 | `MCP_CONSOLE_URL = "http://localhost:5002"` | URL constant for port 5002 |
| 54-55 | `console_client: Optional[httpx.AsyncClient] = None` | Global client for console logging |
| 62-75 | `async def init_client()` | Initializes both http_client AND console_client |
| 78-86 | `async def cleanup_client()` | Cleanup for both http_client AND console_client |
| 90-92 | Section header: "# MCP CONSOLE LOGGING" | Entire logging section |
| 93-116 | `async def log_mcp_request(...)` | Logs to console_client on POST /api/log |
| 119-146 | `async def log_mcp_response(...)` | Logs to console_client on POST /api/log |
| 490 | `await log_mcp_request(name, arguments, request_id)` | Call in call_tool() |
| 494, 736, 747, 756, 764 | `await log_mcp_response(...)` | Multiple calls in error handling |

**To Remove:**
- Lines 47-48: Constants for MCP_CONSOLE_URL
- Lines 54-55: console_client variable declaration
- Lines 62-75: console_client initialization in init_client()
- Lines 78-86: console_client cleanup in cleanup_client()
- Lines 90-147: Entire "MCP CONSOLE LOGGING" section (log_mcp_request + log_mcp_response functions)
- All calls to log_mcp_request() and log_mcp_response() in call_tool()

---

### B. `/src/mcp/mcp_console_standalone.py`
**Status:** STANDALONE SERVER - DELETE ENTIRELY

| Line(s) | Reference | Description |
|---------|-----------|-------------|
| 4 | Port 5002 reference in docstring | Server runs on port 5002 |
| Entire file | All content | Standalone debug UI server |

**To Remove:** Entire file (no longer needed)

---

### C. `/mcp_console/server.py`
**Status:** STANDALONE SERVER - DELETE ENTIRELY

| Line(s) | Reference | Description |
|---------|-----------|-------------|
| 4 | `Port: 5002` | Docstring |
| 165 | `port=5002` | uvicorn.run() configuration |
| 157 | Print statement mentioning `:5002` | Startup message |
| All content | FastAPI server | Standalone console UI |

**To Remove:** Entire file (no longer needed)

---

### D. `/mcp_console/test_client.py`
**Status:** TEST FILE - DELETE ENTIRELY

| Line(s) | Reference | Description |
|---------|-----------|-------------|
| All | Test client | Sends test logs to port 5002 |

**To Remove:** Entire file (test utility for port 5002)

---

## 3. FASTAPI ROUTES / ENDPOINTS

### `/src/api/routes/mcp_console_routes.py`
**Status:** ROUTER MODULE - DELETE ENTIRELY

| Endpoint | Lines | Description |
|----------|-------|-------------|
| `/api/mcp-console/log` | 64-96 | POST endpoint for logging MCP events |
| `/api/mcp-console/history` | 99-133 | GET endpoint for log history |
| `/api/mcp-console/save` | 136-181 | POST endpoint to save logs |
| `/api/mcp-console/clear` | 184-198 | DELETE endpoint to clear logs |
| `/api/mcp-console/stats` | 201-245 | GET endpoint for stats |
| Router definition | 27 | `router = APIRouter(prefix="/api/mcp-console", ...)` |

**To Remove:** Entire file (all endpoints)

---

## 4. MAIN APP REGISTRATION

### `/main.py`
**Status:** APP STARTUP - NEEDS CLEANUP

| Line(s) | Reference | Description |
|---------|-----------|-------------|
| 577 | `from src.api.routes.mcp_console_routes import router as mcp_console_router` | Import statement |
| 578 | `app.include_router(mcp_console_router)` | Router registration |

**To Remove:**
- Line 577: Import of mcp_console_routes
- Line 578: app.include_router(mcp_console_router) call

---

## 5. FRONTEND FILES

### A. `/frontend/static/js/mcp_console.js`
**Status:** JAVASCRIPT CLIENT - DELETE ENTIRELY

| Content | Description |
|---------|-------------|
| Entire file | MCP Console UI JavaScript client |
| Constructor | MCPConsole class |
| Socket.IO | Connection handling |
| REST API calls | Calls to /api/mcp-console endpoints |

**To Remove:** Entire file

---

### B. `/frontend/static/css/mcp_console.css`
**Status:** STYLESHEET - DELETE ENTIRELY

| Content | Description |
|---------|-------------|
| Entire file | CSS styling for MCP Console widget |

**To Remove:** Entire file

---

### C. `/mcp_console/frontend/src/App.tsx`
**Status:** REACT APP - DELETE ENTIRELY

| Content | Description |
|---------|-----------|
| Entire file | React UI component for console |
| Socket.IO client | Real-time updates |
| REST calls | API integration |

**To Remove:** Entire file

---

### D. `/mcp_console/frontend/vite.config.ts`
**Status:** BUILD CONFIG - DELETE WITH FOLDER

| Line(s) | Reference | Description |
|---------|-----------|-------------|
| 12-23 | proxy configuration | Proxies to `http://localhost:5002` |

**To Remove:** Entire file (part of mcp_console folder)

---

## 6. TAURI CONFIGURATION

### A. `/mcp_console/frontend/src-tauri/tauri.conf.json`
**Status:** TAURI APP CONFIG - DELETE WITH FOLDER

| Content | Description |
|---------|-------------|
| productName | "MCP Console" |
| identifier | "com.vetka.mcp-console" |
| bundle settings | Desktop app configuration |

**To Remove:** Entire file (part of mcp_console folder)

---

### B. `/mcp_console/frontend/src-tauri/Cargo.toml`
**Status:** RUST DEPENDENCIES - DELETE WITH FOLDER

| Content | Description |
|---------|-------------|
| Entire file | Rust dependencies for Tauri app |

**To Remove:** Entire file (part of mcp_console folder)

---

### C. `/mcp_console/frontend/src-tauri/src/main.rs`
**Status:** TAURI APP - DELETE WITH FOLDER

| Content | Description |
|---------|-------------|
| Entire file | Rust/Tauri desktop app launcher |

**To Remove:** Entire file (part of mcp_console folder)

---

## 7. DOCUMENTATION FILES (OPTIONAL ARCHIVE)

Location: `/docs/80_ph_mcp_agents/`

Files mentioning MCP Console (for reference):
- `MCP_CONSOLE_ARCHITECTURE.md`
- `MCP_CONSOLE_QUICK_START.md`
- `PHASE2_SONNET_C_MCP_CONSOLE.md`
- `MCP_DEBUG_CONSOLE.md`

**Note:** These are documentation only. Archive or keep for historical reference.

---

## 8. BUILD ARTIFACTS & CACHE

### Directories to delete:
```
/mcp_console/frontend/src-tauri/target/          (Tauri build output)
/src/api/routes/__pycache__/mcp_console*         (Python cache)
/mcp_console/frontend/node_modules/              (npm dependencies)
/mcp_console/frontend/build/                     (React build output)
```

---

## 9. SUMMARY TABLE

| Category | Count | Action |
|----------|-------|--------|
| Python files with 5002 refs | 4 | Clean 2 files, delete 2 files |
| FastAPI route files | 1 | Delete entire file |
| Frontend JS/CSS files | 2 | Delete entire files |
| React components | 1 | Delete entire file |
| Build configs (Vite, Tauri) | 2 | Delete entire files |
| Rust/Cargo files | 2 | Delete entire files |
| Folders to delete | 1 | /mcp_console/ (entire) |
| Standalone servers | 2 | server.py, mcp_console_standalone.py |

**Total Clean-up Lines:** ~500+ lines across codebase

---

## 10. SONNET CLEANUP STEPS

### Step 1: Backup/Archive
- Archive `/mcp_console/` folder to external location
- Archive relevant docs to `/docs_archive/`

### Step 2: Core Cleanup

**File: `/src/mcp/vetka_mcp_bridge.py`**
1. Remove lines 47-48 (MCP_CONSOLE_URL constant)
2. Remove lines 54-55 (console_client variable)
3. Remove lines 62-75 (init_client console_client setup)
4. Remove lines 78-86 (cleanup_client console_client cleanup)
5. Remove lines 90-147 (log_mcp_request + log_mcp_response functions + section header)
6. Remove all calls to log_mcp_request() and log_mcp_response() in call_tool()

**File: `/main.py`**
1. Remove line 577 (mcp_console_routes import)
2. Remove line 578 (app.include_router call)

### Step 3: Delete Files
- Delete `/src/api/routes/mcp_console_routes.py`
- Delete `/src/mcp/mcp_console_standalone.py`
- Delete `/mcp_console/server.py`
- Delete `/mcp_console/test_client.py`
- Delete `/frontend/static/js/mcp_console.js`
- Delete `/frontend/static/css/mcp_console.css`
- Delete entire `/mcp_console/` directory

### Step 4: Cleanup Imports
- Remove Socket.IO references to 'mcp_log' event (if unused elsewhere)
- Clean up any import cache files

### Step 5: Testing
- Verify MCP bridge still works without console_client
- Run tests to ensure no broken imports
- Verify main.py starts without errors

---

## NOTES FOR SONNET

1. **Port 5002** is completely freed for other use
2. **Tauri integration** is completely removed
3. **Console logging** is removed from MCP bridge (requests/responses can be logged elsewhere if needed)
4. **Frontend widget** (mcp_console.js) is removed
5. **All endpoints** under `/api/mcp-console/*` are removed
6. **No breaking changes** to core VETKA functionality

**Verification:** After cleanup, `grep -r "5002\|mcp_console\|console_client" --include="*.py" src/` should return NO results.

