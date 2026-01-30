# VETKA UI Debug Report

## 🚨 Issue Found: Backend Not Running

**Status**: UI loaded ✅ BUT Backend API not responding ❌

### Symptoms
```
❌ WebSocket: ws://localhost:3000/socket.io/ → Failed
❌ API: POST /api/files/read → 404
❌ No server listening on port 3000
```

### Root Cause
**Backend (Python Flask/FastAPI) is NOT started**
- UI (React) runs on port 3000 ✅
- But it expects backend API on SAME port (proxied)
- Backend needs to serve API endpoints

---

## 🔍 Current State

### What's Running
```bash
✅ Frontend (npm dev): localhost:3000 (React UI)
✅ MCP Server: port 5097 (vetka_mcp_server.py)
✅ MCP Bridge: Running
✅ Main.py: Running (demo mode only)

❌ Backend API: NOT running!
❌ WebSocket server: NOT running!
❌ File read endpoint: NOT running!
```

### What's Needed
```
Frontend needs:
1. WebSocket server (Socket.io) on port 3000
2. API endpoints:
   - POST /api/files/read
   - POST /api/search
   - GET /api/tree
   - etc.

Currently:
- main.py = Demo/visualization only
- Not serving API endpoints!
```

---

## 🛠️ How to Fix

### Option 1: Start Backend API Server (RECOMMENDED NOW)

**Find the API server file:**
```bash
find src -name "*main*.py" -o -name "*api*.py" -o -name "*server*.py" | grep -v test
```

**Check if Flask/FastAPI app exists:**
```bash
grep -r "Flask\|FastAPI\|app = " src/*.py | head -10
```

**Start the backend:**
```bash
# If using Flask:
export FLASK_APP=src/api/main.py
export FLASK_ENV=development
flask run --port 3000

# If using FastAPI:
uvicorn src.api.main:app --host 0.0.0.0 --port 3000 --reload

# Generic Python:
python src/api/main.py --port 3000 --debug
```

### Option 2: Configure Proxy (Vite dev server)

**File: `client/vite.config.ts`**

Should have proxy config:
```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:5000',  // Backend port
      changeOrigin: true,
    },
    '/socket.io': {
      target: 'http://localhost:5000',
      ws: true,  // WebSocket
    }
  }
}
```

---

## 📋 Checklist

### For Real-time 3D Updates

- [ ] **Backend API running** (see Option 1 above)
- [ ] **Port 3000** listening for WebSocket
- [ ] **CORS enabled** (allow localhost:3000)
- [ ] **Socket.io** middleware configured
- [ ] **File endpoints** working (`/api/files/read`)

### For Purescan Visualization

- [ ] Run rescan script (DONE ✅)
- [ ] Backend ingests scanned data
- [ ] Vectors uploaded to Qdrant
- [ ] UI requests data from `/api/tree`
- [ ] 3D tree renders with new data

---

## 🎯 What Should Happen (When Fixed)

```
1. Run backend API server
   ↓
2. Frontend WebSocket connects to backend
   ↓
3. User clicks "Run Rescan"
   ↓
4. Backend processes scan
   ↓
5. Data updates in Qdrant
   ↓
6. WebSocket broadcasts changes
   ↓
7. 3D tree UPDATES IN REAL-TIME ✨
   ↓
8. Chaotic lines → Clean structure
```

---

## 🔧 Next Steps for Haiku

### Immediate (5 min)
1. **Find backend entry point**
   ```bash
   grep -r "if __name__" src/*.py | grep -v test
   ```

2. **Identify which framework**
   ```bash
   grep -r "from flask\|from fastapi\|import fastapi" src/
   ```

3. **Check requirements.txt for server**
   ```bash
   grep -i "flask\|fastapi\|uvicorn" requirements.txt
   ```

### Then (2 min)
- Start backend on port 3000
- Refresh browser
- Watch WebSocket connect ✅

### Finally
- Re-run rescan with UI open
- Watch 3D tree transform live! 🎬

---

## 📊 System Architecture (What's Missing)

```
┌─────────────────────────────────────┐
│          React Frontend             │ ✅ Running
│      (localhost:3000/React)         │
└────────────────┬────────────────────┘
                 │
          WebSocket + REST
                 │
     ❌ MISSING: Backend API

     Should be:
     - Flask app / FastAPI app
     - Running on port 3000 (or proxied)
     - Serving:
       • WebSocket (Socket.io)
       • File read endpoints
       • Tree data endpoints
       • Search endpoints
```

---

## 💡 Why Tree Didn't Update

**The full cycle:**
```
Frontend sends: "rescan_project"
         ↓
Backend should: Process scan, update Qdrant
         ↓
Backend broadcasts: "tree_updated" via WebSocket
         ↓
Frontend receives: Updates 3D tree
         ↓
UI shows: Clean, organized tree ✨

WHAT HAPPENED:
Frontend sent: "rescan_project"
         ↓
Backend: NOT LISTENING (NOT RUNNING!)
         ↓
Frontend: Timeout, no WebSocket connection
         ↓
UI: Tree unchanged (no updates received)
```

---

## ✅ Solution Summary

### Current
- ✅ Rescan completed (2244 files, 2438 imports extracted)
- ✅ Frontend UI loads
- ❌ Backend API not running

### To Fix
- Start backend API server (see Option 1)
- Backend MUST listen on port 3000 (or be proxied)
- WebSocket MUST be enabled
- Then: Real-time updates will work! ✨

### Expected Result
```
Browser refresh → WebSocket connects ✅
Run rescan → Tree updates live 🎬
Files organized → Chaos becomes order ✨
```

---

**Key Point**: The rescan worked fine! The 2244 files are scanned and imports extracted. The UI just needs the **backend API to be running** to see the changes reflected in the 3D tree.

**Status**: READY FOR BACKEND START ✅

---

*Instructions created for: Claude Code Haiku 4.5*
*Date: 2026-01-20*
