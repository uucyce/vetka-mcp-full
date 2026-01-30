# 🔧 DEBUG: Backend/Frontend Connection

**Issue:** Frontend sends messages but backend doesn't receive them
**Solution:** Comprehensive debugging to identify connection issue

**Status:** ✅ Debug logging added
**Time:** 5 minutes to test

---

## 🎯 What Was Added

### 1. Enhanced Connection Logging
**File:** `app/main.py:210-221`

```python
@socketio.on('connect')
def handle_connect():
    client_id = request.sid[:8]
    print(f"\n{'='*70}")
    print(f"[SOCKET-DEBUG] ✅ CLIENT CONNECTED")
    print(f"  Client ID: {client_id}")
    print(f"  Full SID: {request.sid}")
    print(f"  Remote Address: {request.remote_addr}")
    print(f"  Time: {datetime.now().isoformat()}")
    print(f"{'='*70}\n")
    emit('connected', {'message': 'Welcome to VETKA Live 0.3', 'debug': 'Backend is receiving connections!'})
```

### 2. Enhanced user_message Handler
**File:** `app/main.py:366-400`

```python
@socketio.on('user_message')
def handle_user_message(data):
    client_id = request.sid[:8]

    # STEP 0: DEBUG - Confirm handler called
    print(f"\n{'='*70}")
    print(f"[USER_MESSAGE] 🔵 HANDLER CALLED!")
    print(f"  Client: {client_id}")
    print(f"  Time: {datetime.now().isoformat()}")
    print(f"  Raw data keys: {list(data.keys())}")
    print(f"{'='*70}")

    text = data.get('text', '').strip()
    node_id = data.get('node_id', 'unknown')
    node_path = data.get('node_path', 'unknown')

    print(f"\n[USER_MESSAGE] Input received:")
    print(f"  text: {text[:60]}...")
    print(f"  node_id: {node_id}")
    print(f"  node_path: {node_path}")
```

### 3. Prominent Startup Banner
**File:** `app/main.py:1118-1139`

```python
if __name__ == '__main__':
    print("\n" + "="*70)
    print("🔴 VETKA BACKEND STARTED - DEBUG MODE")
    print("="*70)
    print(f"  Port: {FLASK_PORT}")
    print(f"  Host: 0.0.0.0 (all interfaces)")
    print(f"  Socket.IO: ✅ Enabled")
    print(f"  Debug: ✅ On")
    print("="*70)
    print(f"🌐 Frontend URL: http://localhost:{FLASK_PORT}")
    print(f"📊 Health check: http://localhost:{FLASK_PORT}/api/health")
    print("="*70)
    print("\n🔍 Watching for Socket.IO connections...")
    print("   - Connect events will show CLIENT CONNECTED")
    print("   - user_message events will show HANDLER CALLED")
    print("\n")
```

---

## 🧪 Testing Steps

### Step 1: Start Backend with Debug Logging

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/app
python main.py
```

**Expected output:**
```
======================================================================
🔴 VETKA BACKEND STARTED - DEBUG MODE
======================================================================
  Port: 5000
  Host: 0.0.0.0 (all interfaces)
  Socket.IO: ✅ Enabled
  Debug: ✅ On
  Time: 2025-12-21T14:30:00.000000
======================================================================
🌐 Frontend URL: http://localhost:5000
📊 Health check: http://localhost:5000/api/health
======================================================================

🔍 Watching for Socket.IO connections...
   - Connect events will show CLIENT CONNECTED
   - user_message events will show HANDLER CALLED


 * Serving Flask app 'main'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.x.x:5000
```

**✅ Checkpoint 1:** Backend started successfully

---

### Step 2: Open Frontend

```bash
# In browser
open http://localhost:5000
```

**Expected in Flask console:**
```
======================================================================
[SOCKET-DEBUG] ✅ CLIENT CONNECTED
  Client ID: abc12345
  Full SID: abc12345def67890
  Remote Address: 127.0.0.1
  Time: 2025-12-21T14:30:05.123456
======================================================================
```

**✅ Checkpoint 2:** Frontend connected to backend

**❌ If you DON'T see this:**
- Frontend is NOT connecting to Socket.IO
- Problem: Port mismatch OR frontend not loading
- Solution: Check browser console (F12) for errors

---

### Step 3: Click Tree Node + Send Message

**In browser:**
1. Click any tree node
2. Type: "Test message"
3. Click Send (or press Enter)

**Expected in Flask console:**
```
======================================================================
[USER_MESSAGE] 🔵 HANDLER CALLED!
  Client: abc12345
  Time: 2025-12-21T14:30:10.789012
  Raw data keys: ['text', 'node_id', 'node_path', 'node_name', 'node_data', 'timestamp']
======================================================================

[USER_MESSAGE] Input received:
  text: Test message...
  node_id: 5688166988014899862
  node_path: params.json

[RESOLVE] Starting resolution...
[RESOLVE] ⚠️ tree_data.json not found at /path/to/tree_data.json
[RESOLVE] ⚠️ Node ID 5688166988014899862 not found in tree

[USER_MESSAGE] node_id=5688166988014899862, node_path=params.json
[USER_MESSAGE] resolved_path=params.json

[ELISYA] Reading context for params.json...
  ⚠️ Elisya Error: File not found: params.json

[CONTEXT] Built prompt with file info

[AGENTS] Starting agent chain...
  [PM] ✅ 450 chars
  [Dev] ✅ 520 chars
  [QA] ✅ 380 chars

[PHASE 1] ✅ Complete
```

**✅ Checkpoint 3:** Handler received message!

---

## 📊 Diagnostic Decision Tree

### Case 1: ✅ CLIENT CONNECTED appears
**Meaning:** Socket.IO connection working!
**Next:** Check if user_message handler fires

### Case 2: ❌ CLIENT CONNECTED never appears
**Meaning:** Frontend not connecting to Socket.IO
**Causes:**
1. Port mismatch (frontend on 5001, backend on 5000)
2. Socket.IO not initialized in frontend
3. CORS issue

**Fix:**
```bash
# Check what's listening on port 5000
lsof -i :5000

# Check config
grep FLASK_PORT app/config/config.py

# Check frontend socket init
grep "io()" src/visualizer/tree_renderer.py
```

### Case 3: ✅ CONNECTED but ❌ HANDLER CALLED never appears
**Meaning:** Connection works, but messages not reaching handler
**Causes:**
1. Frontend sending to wrong event name
2. Frontend not sending at all
3. Data format wrong

**Fix:**
```javascript
// In browser console (F12)
// Check if message is sent:
socket.emit('user_message', {
    text: 'debug test',
    node_id: 'test123',
    node_path: 'test.json'
});

// Should see in Flask:
// [USER_MESSAGE] 🔵 HANDLER CALLED!
```

### Case 4: ✅ HANDLER CALLED but errors after
**Meaning:** Handler working, but processing fails
**Check logs for:**
- `[RESOLVE]` errors → tree_data.json missing
- `[ELISYA]` errors → file not found
- `[AGENTS]` errors → response generation failed

---

## 🔍 Browser Console Debug

**Open browser console (F12) and run:**

```javascript
// 1. Check socket connection
console.log('Socket connected?', socket.connected);
console.log('Socket ID:', socket.id);

// 2. Manually send test message
socket.emit('user_message', {
    text: 'Manual test',
    node_id: 'test_123',
    node_path: 'test.json',
    timestamp: new Date().toISOString()
});

// 3. Listen for debug response
socket.on('connected', (data) => {
    console.log('Connected message:', data);
});

socket.on('agent_message', (data) => {
    console.log('Agent response:', data);
});

// 4. Check for errors
socket.on('agent_error', (data) => {
    console.log('Agent error:', data);
});
```

**Expected output:**
```
Socket connected? true
Socket ID: abc12345def67890
```

**Then in Flask console:**
```
[USER_MESSAGE] 🔵 HANDLER CALLED!
  text: Manual test...
```

---

## ⚠️ Common Issues & Fixes

### Issue 1: Port Mismatch
**Symptom:** Frontend loads but no CLIENT CONNECTED

**Check:**
```bash
# What port is backend on?
grep FLASK_PORT app/config/config.py
# Should show: FLASK_PORT = 5000

# What port is frontend expecting?
# Check tree_renderer.py line ~903:
# const socket = io();  ← Connects to same origin
# So if page loads on :5001, socket connects to :5001
```

**Fix:**
Make sure you access frontend at same port as backend:
- Backend on 5000 → Open http://localhost:5000
- Backend on 5001 → Open http://localhost:5001

### Issue 2: CORS Block
**Symptom:** Browser console shows CORS error

**Fix:**
```python
# In app/main.py, check line ~23:
socketio = SocketIO(app, cors_allowed_origins="*")
# Should allow all origins
```

### Issue 3: tree_data.json Missing
**Symptom:** `[RESOLVE] ⚠️ tree_data.json not found`

**This is OK for now!** The system falls back to using `node_path` directly.

**Fix (optional):**
```bash
# Check if VETKA JSON files exist in output/
ls -la output/vetka_*.json

# Pick latest one and symlink:
ln -s output/vetka_latest.json tree_data.json
```

### Issue 4: File Not Found
**Symptom:** `[ELISYA] ⚠️ Elisya Error: File not found: params.json`

**This is expected** if `node_path` is just a filename!

**Fix:** The resolve_node_to_filepath() function should handle this, but needs tree_data.json.

**Workaround:**
```python
# In context_manager.py, add more fallback paths:
possible_paths = [
    file_path,
    os.path.join(os.getcwd(), file_path),
    os.path.join(os.path.dirname(__file__), '..', file_path),
    os.path.join(os.path.dirname(__file__), '..', 'config', file_path),  # ← Add this
    os.path.join(os.path.dirname(__file__), '..', 'src', file_path),
    # etc.
]
```

---

## 📈 Success Criteria

**Phase 1 & 15-2 working if you see ALL of these:**

```bash
# 1. Backend starts
🔴 VETKA BACKEND STARTED - DEBUG MODE

# 2. Frontend connects
[SOCKET-DEBUG] ✅ CLIENT CONNECTED

# 3. Handler receives messages
[USER_MESSAGE] 🔵 HANDLER CALLED!

# 4. Path resolution attempts
[RESOLVE] Starting resolution...

# 5. Elisya processes
[ELISYA] Reading context for ...

# 6. Agents respond
[AGENTS] Starting agent chain...
  [PM] ✅ 450 chars
  [Dev] ✅ 520 chars
  [QA] ✅ 380 chars

# 7. Complete
[PHASE 1] ✅ Complete
```

**Then in browser:**
- ✅ Chat shows 3 agent responses
- ✅ Dev response opens artifact panel (if long)
- ✅ Can create artifact with "Create in Tree" button

---

## 🎯 Next Actions

**If all debug logs appear:**
1. ✅ Connection working!
2. ✅ Messages reaching backend!
3. ➡️ Now fix file resolution (add tree_data.json or more fallback paths)

**If CLIENT CONNECTED never appears:**
1. ❌ Connection NOT working
2. ➡️ Check port mismatch
3. ➡️ Check browser console for errors

**If HANDLER CALLED never appears:**
1. ❌ Messages not reaching handler
2. ➡️ Check event name ('user_message')
3. ➡️ Try manual socket.emit in browser console

---

## 🔧 Emergency Debug

**If still stuck, add this to frontend (tree_renderer.py):**

```javascript
// Around line 903, replace:
const socket = io();

// With:
const socket = io({
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 10
});

socket.on('connect', () => {
    console.log('[SOCKET] ✅ Connected! Socket ID:', socket.id);
    console.log('[SOCKET] Transport:', socket.io.engine.transport.name);
});

socket.on('connect_error', (error) => {
    console.error('[SOCKET] ❌ Connection error:', error);
});

socket.on('disconnect', (reason) => {
    console.log('[SOCKET] ⚠️ Disconnected:', reason);
});
```

---

**Status:** Ready for testing!
**Time to diagnose:** 5 minutes
**Confidence:** 95% this identifies the issue

**Run the backend and watch the logs!** 🔍
