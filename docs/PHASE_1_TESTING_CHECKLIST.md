# 🧪 PHASE 1 TESTING CHECKLIST

## Quick Start

```bash
# Terminal 1: Start Flask app
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/app
python main.py

# Terminal 2: Open browser
open http://localhost:5000
```

---

## ✅ Checklist

### Step 1: App Startup
- [ ] Flask starts without errors
- [ ] See: `🚀 Starting VETKA Live 0.3 on port 5000`
- [ ] See: `✅ VETKA components initialized`
- [ ] Browser opens to http://localhost:5000

### Step 2: UI Loads
- [ ] 3D tree visualization appears
- [ ] Chat panel visible on right side
- [ ] Artifact panel hidden initially
- [ ] Can see nodes in the tree

### Step 3: Node Selection
- [ ] Click any tree node
- [ ] Node changes color/appearance
- [ ] Node ID appears somewhere in UI
- [ ] Browser console (F12) shows node data

### Step 4: Send Message
- [ ] Type in chat input: "What does this file do?"
- [ ] Click Send button (or press Enter)
- [ ] Input field clears
- [ ] "Processing..." message appears

### Step 5: Flask Console Output
Look for this in Flask terminal:

```
======================================================================
[PHASE 1] User message from [client_id]
  Text: What does this file do?...
  Node: [file_path]
======================================================================

[ELISYA] Reading context for [file_path]...
  ✅ Got context summary: [summary]

[CONTEXT] Built prompt with file info

[AGENTS] Starting agent chain...
  [PM] ✅ [N] chars
  [Dev] ✅ [N] chars
  [QA] ✅ [N] chars

[PHASE 1] ✅ Complete
```

- [ ] See all the above output
- [ ] No error messages
- [ ] All 3 agents complete

### Step 6: Browser Console Output
Open DevTools (F12) → Console, look for:

```
[CHAT] Sending message: {...}
[SOCKET-RX] 📨 Received agent_message: {agent: "PM", ...}
[SOCKET-RX] 📨 Received agent_message: {agent: "Dev", ...}
[SOCKET-RX] 📨 Received agent_message: {agent: "QA", ...}
```

- [ ] See "Sending message" log
- [ ] See 3 "Received agent_message" logs
- [ ] Each has different agent name (PM, Dev, QA)

### Step 7: Chat Panel Display
- [ ] Chat panel shows user message
- [ ] PM response appears (~500ms delay)
- [ ] Dev response appears (~1000ms delay)
- [ ] QA response appears (~1500ms delay)
- [ ] Each response has agent name/icon
- [ ] Responses mention the file context

### Step 8: Artifact Panel (Optional)
- [ ] If response > 800 chars → artifact opens
- [ ] Can drag artifact panel left/right
- [ ] Can close with `<<` button
- [ ] Artifact content is readable

---

## 🐛 Troubleshooting

### "Module not found: elisya_integration"
**Fix:**
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
cd app
python main.py
```

### "File not found" in Elisya
**Fix:**
- Check that `node_path` is correct in Flask console
- Try clicking a different node
- Ensure the file actually exists at that path

### "Socket not connected"
**Fix:**
- Check browser console for Socket.IO errors
- Ensure Flask is running on port 5000
- Try refreshing the browser

### No agent responses appear
**Fix:**
1. Check Flask console for errors in agent loop
2. Check browser console for Socket.IO receive errors
3. Verify `socket.on('agent_message')` listener exists in tree_renderer.py
4. Try restarting Flask app

### Responses are generic/placeholder
**Expected!** Phase 1 uses placeholder text.
- This is normal - Phase 2 will add real LLM calls
- For now, just verify the FLOW works (messages sent/received)

---

## 📊 Success Criteria

**Phase 1 is COMPLETE if:**

✅ All checklist items pass
✅ Flask console shows agent processing
✅ Browser receives 3 agent messages
✅ Chat panel displays all 3 responses
✅ Responses mention file context (even if generic)

**Then you're ready for Phase 2!** 🚀

---

## 🎬 Test Examples

### Test 1: Simple Question
- Node: `src/main.py`
- Question: "What does this file do?"
- Expected: 3 responses mentioning main.py

### Test 2: Specific Question
- Node: `elisya_integration/context_manager.py`
- Question: "How does filter_context work?"
- Expected: 3 responses mentioning context_manager.py, might include relevant code lines

### Test 3: Non-existent File
- Node: (node with invalid path)
- Question: "Test question"
- Expected: Responses with "(File not accessible: ...)" message, but no crash

### Test 4: Long Response (Artifact Test)
- Any node
- Question: "Explain everything about this file"
- Expected: Dev response might be > 800 chars → artifact panel opens

---

## 📝 Notes

- Placeholder responses are INTENTIONAL for Phase 1
- Focus on verifying the MESSAGE FLOW, not response quality
- Real LLM integration comes in Phase 2
- If you see 3 agent responses with file context → SUCCESS! ✅

---

**Happy testing! 🎉**
