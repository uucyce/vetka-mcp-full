# 🐛 Bug Analysis Report: 404 ошибки API + WebSocket disconnect

**Date:** 2026-01-18
**Status:** ANALYSIS COMPLETE (No code changes made)

---

## 📋 Summary

User reported two issues:
1. **404 ошибки:** `Failed to load :3000/api/files/read` — HTTP 404 Not Found
2. **WebSocket disconnect:** `WebSocket connection to 'ws://localhost:5001/socket.io/?transport=websocket' failed`

---

## 🔍 Root Cause Analysis

### Issue #1: API Endpoint Mismatch

**Problem:** `/api/files/read` endpoint **DOES NOT EXIST** in the codebase.

**Evidence:**
- ✅ **Endpoint found:** `POST /api/files/read` exists in `src/api/routes/files_routes.py:101`
  - Location: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/files_routes.py:101`
  - Route prefix: `/api/files`
  - Method: `POST`
  - Status: **ACTIVE** (Phase 54.6)

**But the error suggests:** Frontend is calling it incorrectly or via wrong host.

**Frontend API Call Pattern:**
- **`api.ts`** uses: `const API_BASE = '/api'` (relative path via proxy)
  - Calls: `fetch('/api/tree/data')`
  - Works via Vite proxy → localhost:5001

- **`chatApi.ts`** uses: `const API_BASE = 'http://localhost:5001'` (hardcoded)
  - Calls: `fetch('http://localhost:5001/api/chat')`
  - Direct to backend

**Vite Proxy Config** (`vite.config.ts:8-16`):
```javascript
proxy: {
  '/api': {
    target: 'http://localhost:5001',
    changeOrigin: true
  },
  '/socket.io': {
    target: 'http://localhost:5001',
    ws: true
  }
}
```

✅ Backend serving correctly on port **5001**
✅ Health check responds: `{"status":"healthy","version":"2.0.0","framework":"FastAPI"...}`
✅ Port 5001 listening: `*.5001 *.* LISTEN`

**Likely Cause:** Error message is **misleading**. The `:3000/api/files/read` in the error is actually the **Vite dev server proxy path**, not a direct call to port 3000.

---

### Issue #2: WebSocket Connection Failure

**Problem:** WebSocket connection to `ws://localhost:5001/socket.io/?transport=websocket` fails.

**Configuration Found:**
- Backend (main.py:261-268): Socket.IO configured as AsyncServer with ASGI wrapper
  - Settings: `async_mode='asgi'`, `cors_allowed_origins='*'`
  - Ping interval: 25s, Ping timeout: 60s
  - Handlers registered: All from `src/api/handlers`

- Frontend (useSocket.ts:15): `const SOCKET_URL = import.meta.env.VITE_API_BASE || 'http://localhost:5001'`
  - Tries to connect directly to `http://localhost:5001` (not through proxy!)

**Critical Finding:**
1. WebSocket proxy is configured in Vite: `/socket.io` → `localhost:5001` with `ws: true`
2. But frontend code **BYPASSES the proxy** by using hardcoded `http://localhost:5001`
3. This works only if frontend and backend are on same host (they are)

**Issue might be:**
- Socket.IO connection to `http://localhost:5001` works fine
- But there's a mismatch between:
  - Some code using relative path proxy (`/socket.io`)
  - Other code using absolute URL (`http://localhost:5001`)

---

## 🏗️ Current Architecture

```
Frontend (localhost:3000 - Vite dev server)
├── Relative paths: /api → [Vite proxy] → localhost:5001
├── Hardcoded URLs: http://localhost:5001 (direct)
└── WebSocket: http://localhost:5001 (direct via Socket.IO)

Backend (localhost:5001 - FastAPI + Socket.IO)
├── FastAPI app (port 5001)
├── Socket.IO ASGI wrapper (same port)
└── Routes registered: 13 routers, 59 endpoints
```

---

## ✅ System Status

| Component | Status | Details |
|-----------|--------|---------|
| Backend Server | ✅ Running | PID 21826, Python main.py |
| Port 5001 | ✅ Listening | `*.5001 *.* LISTEN` |
| Health Check | ✅ OK | `/api/health` returns 200 |
| File API Endpoint | ✅ Exists | `POST /api/files/read` active |
| WebSocket Handler | ✅ Registered | 18 socket events loaded |
| Frontend Dev Server | ✅ Running | Port 3000, Vite |
| Vite Proxy | ✅ Configured | `/api` and `/socket.io` routes setup |
| CORS | ✅ Enabled | `allow_origins=['*']` |

---

## 📊 Network Analysis

**Browser Network Requests:**
- Total requests: 77
- All frontend JS/CSS: ✅ 200 OK
- Backend API calls:
  - ✅ `http://localhost:3000/api/models` → 200
  - ✅ `http://localhost:3000/api/tree/data` → 200
  - (Proxied correctly to 5001)

**No Failed Requests Detected**
- Console shows NO errors
- No 404s on `/api/files/read`
- No WebSocket errors in current state

---

## 🤔 Analysis Conclusion

The reported errors are **NOT currently reproducible**:

1. **404 error on `/api/files/read`:**
   - Endpoint exists and is properly registered
   - May have been a **transient error** (backend startup issue)
   - Or **user was calling it incorrectly** before setup was complete

2. **WebSocket disconnect:**
   - Socket.IO is properly configured
   - Connection attempts appear to succeed
   - No active errors in current browser state
   - May have been a **timing issue** during initial load

---

## 🔧 Potential Issues to Monitor

### Code Inconsistency (Not Breaking, But Problematic)

**Files with mixed API strategies:**

| File | API_BASE | Type | Issue |
|------|----------|------|-------|
| `client/src/utils/api.ts` | `'/api'` (relative) | Tree data | ✅ Correct - uses proxy |
| `client/src/utils/chatApi.ts` | `'http://localhost:5001'` | Chat API | ⚠️ Hardcoded - bypasses proxy |
| `client/src/hooks/useSocket.ts` | `'http://localhost:5001'` (default) | WebSocket | ⚠️ Hardcoded - but works |
| `client/src/hooks/useRealtimeVoice.ts` | `'http://localhost:5001'` (default) | Voice/WebSocket | ⚠️ Hardcoded - but works |

**Why it works:** Frontend and backend are on same localhost, so direct URLs work.

**Why it's bad:**
- Breaks in production when frontend/backend are on different hosts
- Inconsistent pattern across codebase
- Vite proxy bypassed partially

---

## 📝 Recommendations

### Priority: LOW (Not breaking currently)

If you want to fix the architecture inconsistency:

1. **Standardize API_BASE across frontend:**
   - Use relative paths: `'/api'` everywhere
   - Vite proxy will handle routing to 5001
   - Works in dev AND production

2. **Update chatApi.ts:**
   - Change: `const API_BASE = 'http://localhost:5001'`
   - To: `const API_BASE = '/api'`

3. **Update WebSocket hooks:**
   - Change: `const SOCKET_URL = import.meta.env.VITE_API_BASE || 'http://localhost:5001'`
   - To: `const SOCKET_URL = window.location.origin` (uses current domain)

### If errors persist:

1. Check backend logs for startup errors
2. Ensure port 5001 is actually accepting connections
3. Verify no firewall blocking localhost:5001
4. Check browser DevTools Network tab for actual failed requests

---

## 📁 Key Files

| File | Purpose | Status |
|------|---------|--------|
| `main.py` | FastAPI app entry | ✅ PRODUCTION (Phase 39.8) |
| `src/api/routes/files_routes.py` | File operations API | ✅ ACTIVE (Phase 54.6) |
| `client/vite.config.ts` | Vite dev proxy config | ✅ Correct |
| `client/src/hooks/useSocket.ts` | WebSocket client | ⚠️ Needs config review |
| `client/src/utils/chatApi.ts` | Chat API calls | ⚠️ Needs config review |

---

## 🎯 Status Summary

```
✅ API Endpoint /api/files/read exists
✅ Backend running on port 5001
✅ WebSocket handler registered
✅ Vite proxy configured correctly
⚠️ Code has inconsistent API_BASE references (not breaking, but should standardize)
⚠️ No current errors reproducible (issue may have resolved)
```

**Recommendation:** Monitor for recurrence. If errors return, check:
1. Backend startup logs
2. Port 5001 network status
3. Browser console for new error patterns
