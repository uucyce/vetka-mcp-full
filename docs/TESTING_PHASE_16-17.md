# 🧪 TESTING PHASE 16-17 INTEGRATION

**Quick Start Guide for Testing Phase 16-17 Features**

---

## 🚀 Start the Server

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
source .venv/bin/activate
python main_fixed_phase_7_8.py
```

**Expected Output:**
```
============================================================
🌳 VETKA PHASE 7.8 - RESOURCE LEAK FIXED
============================================================

🔧 Key Fixes:
   ✅ Global MemoryManager singleton
   ✅ Enhanced error handling
   ✅ Service initialization validation

🧠 Initializing Phase 16-17 CAM/KG Integration...
✅ Phase 16-17 global state initialized

📊 Services:
   • Flask API: http://localhost:5001
   • Socket.IO: ws://localhost:5001/socket.io/
```

---

## 🌐 Open the Frontend

Navigate to: **http://localhost:5001/3d**

You should see:
1. **3D Tree Visualization** (center)
2. **Agent Response Panel** (right side)
3. **CAM Status Panel** (left side)
4. **Mode Toggle Buttons** (bottom center)

---

## 🧪 Test 1: Agent Response Panel

### Via Browser Console:

Open DevTools (F12) → Console tab → Paste:

```javascript
// Connect to Socket.IO (should be automatic)
const socket = io();

// Simulate agent workflow result
socket.emit('workflow_result', {
  agent: 'dev',
  response: 'Successfully analyzed Flask application structure. Found 15 routes and 8 Socket.IO handlers.',
  file_analyzed: '/app/main_fixed_phase_7_8.py'
});
```

**Expected Result:**
- Agent Response Panel (right) updates with:
  - Agent badge: "dev"
  - Status: ✅
  - Response text: "Successfully analyzed..."

---

## 🧪 Test 2: CAM Status Panel

### Via Browser Console:

```javascript
// Simulate CAM branch operation
socket.emit('cam_operation', {
  operation: 'branch',
  file_path: '/test/new_file.py',
  metadata: { author: 'test_user' }
});

// Simulate merge proposals
socket.on('merge_proposals', (data) => {
  console.log('✅ Received merge proposals:', data);
});

socket.emit('cam_operation', {
  operation: 'merge',
  threshold: 0.92
});

// Simulate prune candidates
socket.on('pruning_candidates', (data) => {
  console.log('✅ Received prune candidates:', data);
});

socket.emit('cam_operation', {
  operation: 'prune',
  threshold: 0.2
});
```

**Expected Result:**
- CAM Status Panel (left) updates with:
  - Branches count increases
  - Merge count shows number of proposals
  - Prune count shows number of candidates
  - "Review Merges" button appears (if merge candidates > 0)
  - "Confirm Prunes" button appears (if prune candidates > 0)

---

## 🧪 Test 3: Mode Toggle

### Via Browser Console:

```javascript
// Toggle to Knowledge Graph mode
document.getElementById('kg-mode').click();
```

**Expected Result:**
- "🔄 Transitioning..." indicator appears
- Mode button states update (Knowledge Graph becomes active)
- Console shows: `[KG] Toggle layout: directory → knowledge`
- **NOTE:** Full animation won't work until PROMPT 5 is complete

### Via Browser Console:

```javascript
// Toggle back to Directory mode
document.getElementById('dir-mode').click();
```

**Expected Result:**
- Transitions back to Directory mode
- Console shows: `[KG] Toggle layout: knowledge → directory`

---

## 🧪 Test 4: Flask API Endpoints

### Test Last Agent Response:

```bash
curl http://localhost:5001/api/last-agent-response
```

**Expected Response:**
```json
{
  "agent": null,
  "response": null,
  "timestamp": null,
  "file_analyzed": null
}
```

*(After running Test 1, this will show the agent data)*

---

### Test Merge Confirmation:

```bash
curl -X POST http://localhost:5001/api/cam/merge \
  -H "Content-Type: application/json" \
  -d '{
    "old_id": "node_test_123",
    "merged_id": "node_test_456"
  }'
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Merged node_test_123 into node_test_456"
}
```

**Socket.IO Event Emitted:** `merge_confirmed`

---

### Test Prune Confirmation:

```bash
curl -X POST http://localhost:5001/api/cam/prune \
  -H "Content-Type: application/json" \
  -d '{
    "node_ids": ["node_test_123", "node_test_456", "node_test_789"]
  }'
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Pruned 3 nodes"
}
```

**Socket.IO Event Emitted:** `prune_confirmed`

---

## 🧪 Test 5: Socket.IO Event Flow (Full Integration)

### Via Browser Console:

```javascript
// Set up all event listeners
socket.on('agent_response_updated', (data) => {
  console.log('✅ Agent Response Updated:', data);
});

socket.on('cam_operation_result', (data) => {
  console.log('✅ CAM Operation Result:', data);
});

socket.on('merge_proposals', (data) => {
  console.log('✅ Merge Proposals:', data);
});

socket.on('pruning_candidates', (data) => {
  console.log('✅ Pruning Candidates:', data);
});

socket.on('merge_confirmed', (data) => {
  console.log('✅ Merge Confirmed:', data);
});

socket.on('prune_confirmed', (data) => {
  console.log('✅ Prune Confirmed:', data);
});

socket.on('layout_frame', (data) => {
  console.log(`📊 Frame ${data.frame}/${data.total_frames} (${data.mode} mode)`);
});

// Test workflow: Branch → Merge → Confirm
socket.emit('workflow_result', {
  agent: 'pm',
  response: 'Created feature plan for authentication system',
  file_analyzed: '/docs/feature_plan.md'
});

setTimeout(() => {
  socket.emit('cam_operation', {
    operation: 'merge',
    threshold: 0.92
  });
}, 2000);

// (Click "Review Merges" button when it appears)
```

**Expected Console Output:**
```
✅ Agent Response Updated: {agent: "pm", response: "Created feature plan...", ...}
✅ Merge Proposals: {proposals: [...], count: X}
(Button appears in UI)
(Click "Review Merges")
✅ Merge Confirmed: {old_id: "...", merged_id: "...", ...}
```

---

## 🧪 Test 6: Error Handling

### Test Invalid Merge Request:

```bash
curl -X POST http://localhost:5001/api/cam/merge \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected Response:**
```json
{
  "error": "Missing old_id or merged_id"
}
```

**Status Code:** 400

---

### Test Invalid Prune Request:

```bash
curl -X POST http://localhost:5001/api/cam/prune \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected Response:**
```json
{
  "error": "No node_ids provided"
}
```

**Status Code:** 400

---

## 🔍 Debugging Tips

### Check Server Logs:

The Flask server will log all events:
```
[CAM] workflow_result from agent: dev
[CAM] Operation requested: merge on /test/file.py
[KG] Toggle layout: directory → knowledge
```

### Check Browser Console:

Look for:
- Socket.IO connection: `Connected to VETKA Phase 7.8`
- Event logs from your test scripts
- Any JavaScript errors

### Check Network Tab:

- Socket.IO messages appear under "WS" (WebSocket)
- POST requests to `/api/cam/*` should return 200 status
- GET requests to `/api/last-agent-response` should return JSON

---

## ✅ Success Checklist

After testing, verify:

- [ ] Agent Response Panel updates on `workflow_result`
- [ ] CAM Status Panel shows correct counts
- [ ] Mode toggle buttons change state
- [ ] "🔄 Transitioning..." indicator appears during mode switch
- [ ] "Review Merges" button appears when merge candidates > 0
- [ ] "Confirm Prunes" button appears when prune candidates > 0
- [ ] `/api/last-agent-response` returns correct data
- [ ] `/api/cam/merge` accepts merge confirmations
- [ ] `/api/cam/prune` accepts prune confirmations
- [ ] All Socket.IO events fire correctly
- [ ] Error handling works for invalid requests

---

## 🚧 Known Limitations (Until PROMPT 5)

1. **Mode Toggle Animation:** Currently just shows "🔄 Transitioning..." but doesn't animate the tree. PROMPT 5 will implement the 60 FPS Three.js animation.

2. **Button Actions:** Clicking "Review Merges" or "Confirm Prunes" only logs to console. Full confirmation UI will be added in PROMPT 6.

3. **layout_frame Handler:** Currently just logs frames to console. PROMPT 5 will apply position updates to Three.js meshes.

---

## 📊 Test Results Template

Use this to document your testing:

```
============================================================
PHASE 16-17 INTEGRATION TEST RESULTS
============================================================

Date: _________________
Tester: _______________

Test 1: Agent Response Panel       [ ] PASS  [ ] FAIL
Test 2: CAM Status Panel            [ ] PASS  [ ] FAIL
Test 3: Mode Toggle                 [ ] PASS  [ ] FAIL
Test 4: Flask API Endpoints         [ ] PASS  [ ] FAIL
Test 5: Socket.IO Event Flow        [ ] PASS  [ ] FAIL
Test 6: Error Handling              [ ] PASS  [ ] FAIL

Overall Status: [ ] ALL TESTS PASSING  [ ] ISSUES FOUND

Issues/Notes:
_____________________________________________________________
_____________________________________________________________
_____________________________________________________________

Next Steps:
_____________________________________________________________
_____________________________________________________________
_____________________________________________________________
```

---

## 📚 Additional Resources

- **PROMPT 1 Validation:** [`docs/PROMPT_1_VALIDATION_REPORT.md`](./PROMPT_1_VALIDATION_REPORT.md)
- **Backend Integration:** [`docs/PHASE_16-17_BACKEND_INTEGRATION_COMPLETE.md`](./PHASE_16-17_BACKEND_INTEGRATION_COMPLETE.md)
- **Complete Status:** [`docs/PHASE_16-17_COMPLETE_STATUS.md`](./PHASE_16-17_COMPLETE_STATUS.md)
- **Phase 16 Summary:** [`docs/PHASE_16_SUMMARY.md`](./PHASE_16_SUMMARY.md)
- **Phase 17 Implementation:** [`docs/PHASE_17_KG_IMPLEMENTATION.md`](./PHASE_17_KG_IMPLEMENTATION.md)

---

**Happy Testing! 🎉**

*Test Guide Created: December 21, 2025*
