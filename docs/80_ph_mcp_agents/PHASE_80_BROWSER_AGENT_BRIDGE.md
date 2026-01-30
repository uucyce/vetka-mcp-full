# Phase 80: Browser Agent Bridge

> **Status:** ✅ COMPLETE
> **Date:** 2026-01-21
> **Tested by:** Browser Haiku

## Summary

Добавлен REST API мост для браузерных AI-агентов (Claude Haiku в Chrome).
Позволяет внешним агентам помогать дебажить VETKA без MCP доступа.

## Architecture

```
┌─────────────────────┐     ┌─────────────────────┐
│   Browser Haiku     │     │    Claude Code      │
│   (Chrome Console)  │     │       (MCP)         │
└─────────┬───────────┘     └─────────┬───────────┘
          │                           │
          │ REST API                  │ MCP Tools
          │ (read-only + camera)      │ (full access)
          ▼                           ▼
┌─────────────────────────────────────────────────┐
│                 VETKA Backend                    │
│  /api/debug/* endpoints + SocketIO camera       │
└─────────────────────────────────────────────────┘
```

## Components

### Backend (`src/api/routes/debug_routes.py`)

**9 endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/debug/inspect` | GET | Full state inspection |
| `/api/debug/formulas` | GET | Layout formula values |
| `/api/debug/tree-state` | GET | Quick health check |
| `/api/debug/recent-errors` | GET | Error history |
| `/api/debug/logs` | GET | Debug logs |
| `/api/debug/modes` | GET | Visualization modes |
| `/api/debug/agent-info` | GET | API documentation |
| `/api/debug/chat-context` | GET | Same context as internal agents |
| `/api/debug/camera-focus` | POST | Control 3D camera |

### Frontend (`client/src/utils/browserAgentBridge.ts`)

Exposes `window.vetkaAPI` with methods:

```javascript
vetkaAPI.quickStatus()      // One-command health check
vetkaAPI.inspect()          // Full state
vetkaAPI.getErrors()        // Error history
vetkaAPI.getFormulas(mode)  // Layout formulas
vetkaAPI.getModes()         // Visualization modes
vetkaAPI.getChatContext()   // Agent context
vetkaAPI.focusCamera(file)  // Camera control
vetkaAPI.help()             // Show commands
```

## Test Results (by Browser Haiku)

```
✅ quickStatus()     - PASSED (44 files, 0 errors, all systems operational)
✅ inspect()         - PASSED (6 components active)
✅ getErrors()       - PASSED (0 errors)
✅ getModes()        - PASSED (4 modes available)
✅ getFormulas()     - PARTIAL (fan_layout module unavailable)
✅ getChatContext()  - PASSED (Phase 80.1, 44 files)
✅ focusCamera()     - PASSED (camera moved to main.py)
```

## Workflow

```
Browser Haiku                    Claude Code (MCP)
─────────────                    ────────────────
1. quickStatus()
2. inspect('sugiyama')
3. "Found: layer_assignment empty"  →  4. Read sugiyama_layout.py
                                     5. Find bug
                                     6. Fix & commit
```

## Files Changed

| File | Change |
|------|--------|
| `src/api/routes/debug_routes.py` | NEW - Debug API endpoints |
| `src/api/routes/__init__.py` | Added debug_router |
| `client/src/utils/browserAgentBridge.ts` | NEW - Frontend bridge |
| `client/src/main.tsx` | Initialize bridge |
| `VETKA_AGENT_GUIDE.md` | NEW - Documentation for browser agents |

## Key Decisions

1. **REST API, not MCP** - Browser agents can't use MCP, need HTTP endpoints
2. **Read-only + camera** - No code modification, only observation and visualization control
3. **Same context as internal agents** - Browser agents see what VETKA agents see
4. **Async SocketIO emit** - Fixed bug with `await socketio.emit()` for AsyncServer

## Future Improvements

- [ ] Add more formulas to `/api/debug/formulas` (Sugiyama constants)
- [ ] Real-time log streaming via WebSocket
- [ ] Multi-agent coordination protocol

---

*Phase 80.1 complete. Browser Haiku is now part of the debug team.*
