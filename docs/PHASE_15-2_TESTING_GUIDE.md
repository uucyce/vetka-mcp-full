# 🧪 PHASE 15-2 TESTING GUIDE
## Quick Verification Steps

**Goal:** Verify smart response display + artifact creation works

**Time:** 5 minutes

---

## 🚀 Quick Start

```bash
# Terminal 1: Start Flask
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/app
python main.py

# Should see:
# 🚀 Starting VETKA Live 0.3 on port 5000
# 🌐 Open http://localhost:5000 in your browser

# Terminal 2: Watch artifacts directory
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
watch -n 1 'find artifacts -type f 2>/dev/null | tail -5'
```

---

## ✅ Test Checklist

### Test 1: Short Response (1 min)
**Goal:** Verify responses < 800 chars stay in chat only

- [ ] Open http://localhost:5000
- [ ] Click any tree node
- [ ] Type: "Hi"
- [ ] Click Send or press Enter
- [ ] Wait for 3 agent responses (~1.5 seconds)

**Expected:**
```
Chat panel shows:
  [You] Hi

  [PM] As Project Manager analyzing...
       (Full response, ~450 chars)

  [Dev] As Developer working on...
        (Full response, ~520 chars)

  [QA] As QA Engineer reviewing...
       (Full response, ~380 chars)
```

**Artifact panel:**
- [ ] Stays CLOSED (hidden on left)
- [ ] `<<` button visible

**✅ PASS if:** All 3 full responses visible in chat, artifact panel closed

---

### Test 2: Long Response (2 min)
**Goal:** Verify responses >= 800 chars auto-open artifact

- [ ] Click tree node
- [ ] Type: "Explain everything about this file in detail"
- [ ] Click Send

**Expected in chat:**
```
[You] Explain everything...

[PM] As Project Manager analyzing...
     (Full text ~450 chars)

[Dev] As Developer working on...
      (Truncated to 200 chars)
      ...[See artifact panel →]

[QA] As QA Engineer reviewing...
     (Full text ~380 chars)
```

**Artifact panel:**
- [ ] AUTO-OPENS (slides in from left)
- [ ] Shows "TEXT" badge
- [ ] Shows full Dev response (with code block)
- [ ] Footer has 4 buttons:
  - [ ] "📁 Create in Tree"
  - [ ] "✏️ Edit"
  - [ ] "📋 Copy"
  - [ ] "✖️ Cancel"
- [ ] Can drag panel left/right
- [ ] `>>` button changes to visible

**Flask console:**
```
[ARTIFACT] ✅ Opening panel for long/code response (length=1200)
```

**Browser console (F12):**
```
[SOCKET-RX] 📨 Received agent_message: {agent: "Dev", text: "...", ...}
[ARTIFACT] ✅ Opening panel for long/code response (length=1200)
[ARTIFACT] Opening panel with type: text
```

**✅ PASS if:** Summary in chat, full response in artifact, panel auto-opened

---

### Test 3: Create Artifact (2 min)
**Goal:** Verify artifact file creation works

**Prerequisites:** Artifact panel is open from Test 2

- [ ] Click "📁 Create in Tree" button
- [ ] Wait 1 second

**Expected in UI:**
- [ ] Footer changes to: "💾 Creating artifact..."
- [ ] After ~1 second:
  - [ ] Artifact panel closes
  - [ ] Chat shows success message:
    ```
    [System] ✅ Artifact created: Dev Analysis (Dec 21)
             📁 Saved to: /path/to/artifacts/.../dev_response_....md
    ```

**Flask console:**
```
======================================================================
[ARTIFACT-CREATE] a1b2c3d4 from Dev
  Node: src/main.py (or whatever node you clicked)
  Type: text
  Length: 1200 chars (or actual length)
======================================================================
  ✅ Directory created: /path/to/artifacts/src_main_py
  ✅ Filename: dev_response_20251221_143023.md
  ✅ Saved to: /path/to/artifacts/src_main_py/dev_response_20251221_143023.md
  ✅ Tree node prepared: artifact_src_main_py_20251221_143023

[ARTIFACT-CREATE] ✅ Complete
```

**Browser console:**
```
[CREATE-ARTIFACT] Sending to backend... {
  agent: "Dev",
  node_id: "src_main_py",
  node_path: "src/main.py",
  content_length: 1200,
  type: "text"
}
[ARTIFACT-CREATED-RX] Received: {success: true, artifact_id: "...", ...}
  ✅ Artifact saved to: /path/to/file.md
  ✅ Tree node: Dev Analysis (Dec 21)
[ARTIFACT-CREATED] Complete ✅
```

**On filesystem:**
- [ ] File exists:
  ```bash
  ls -la /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/artifacts/
  ```
- [ ] Directory created for node:
  ```bash
  ls artifacts/*/
  # Should show: dev_response_20251221_HHMMSS.md
  ```
- [ ] File has correct structure:
  ```bash
  cat artifacts/*/dev_response_*.md
  ```
  Should show:
  ```markdown
  ---
  agent: Dev
  timestamp: 2025-12-21T14:30:23.123456
  source_node: src/main.py
  response_type: text
  version: 1
  conversation_id: ...
  ---

  As Developer working on main.py (715 lines, .py file):

  Analyzing your question: "Explain everything..."
  ...
  [Full response here]
  ```

**✅ PASS if:** File created with YAML frontmatter + full content

---

### Test 4: Multiple Artifacts (1 min)
**Goal:** Verify multiple artifacts from different agents

- [ ] Ask another long question
- [ ] Wait for PM response (if long, artifact opens)
- [ ] Click "📁 Create in Tree"
- [ ] Repeat for QA

**Expected on filesystem:**
```bash
find artifacts -type f

# Should show:
# artifacts/src_main_py/pm_response_20251221_143022.md
# artifacts/src_main_py/dev_response_20251221_143023.md
# artifacts/src_main_py/qa_response_20251221_143024.md
```

**✅ PASS if:** Multiple artifacts exist in same directory

---

### Test 5: Different Nodes (1 min)
**Goal:** Verify artifacts organized by node

- [ ] Click DIFFERENT tree node
- [ ] Ask long question
- [ ] Create artifact

**Expected on filesystem:**
```bash
find artifacts -type d

# Should show:
# artifacts/src_main_py/
# artifacts/preferences_json/  (or whatever node you clicked)
```

**✅ PASS if:** Artifacts separated by node_id directories

---

## 🐛 Troubleshooting

### "Artifact panel doesn't open"
**Check:**
1. Browser console for errors
2. Response length > 800 chars?
3. Try forcing: Add `force_artifact: true` in backend emit

**Fix:**
```javascript
// In browser console:
shouldOpenArtifactPanel("test".repeat(300), {})  // Should return true
```

### "Create button does nothing"
**Check:**
1. Socket connected? `socket.connected` in console
2. Flask running?
3. Browser console for errors

**Fix:**
```bash
# Restart Flask
cd app && python main.py
```

### "File not created"
**Check:**
1. Flask console for errors
2. Directory permissions
3. Path exists

**Fix:**
```bash
# Create directory manually
mkdir -p /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/artifacts

# Check permissions
ls -la /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/
```

### "Response always short"
**Force long response:**

Edit `app/main.py:440-516` (generate_agent_response):
```python
responses = {
    'Dev': f"""As Developer working on {context}:

Analyzing your question: "{user_question}"

**Current Structure:**
- File: {context}
- Key components identified
- Dependencies understood

**Implementation Plan:**
1. Step one
2. Step two
3. Step three

""" + ("Additional analysis details here.\n" * 50)  # Force > 800 chars
}
```

---

## 📊 Success Metrics

**All tests pass if:**
- [x] Short responses stay in chat
- [x] Long responses trigger artifact panel
- [x] Artifact panel auto-opens
- [x] Create button sends socket event
- [x] Backend creates file with YAML frontmatter
- [x] Success message shows in chat
- [x] Artifact panel closes on success
- [x] Files organized by node_id
- [x] No crashes or errors

**Total time:** ~10 minutes for all tests

---

## 🎓 Advanced Testing

### Test YAML Parsing
```bash
# Install yq (YAML parser)
brew install yq  # macOS

# Parse artifact metadata
yq eval artifacts/*/pm_response_*.md | head -20

# Should show:
# agent: PM
# timestamp: 2025-12-21T14:30:22.123456
# source_node: src/main.py
# response_type: text
# version: 1
```

### Test Artifact Count
```bash
# Count artifacts per node
find artifacts -type f | cut -d/ -f2 | sort | uniq -c

# Example output:
#   3 src_main_py
#   1 preferences_json
#   2 config_py
```

### Test File Size Distribution
```bash
# Show artifact sizes
find artifacts -type f -exec ls -lh {} \; | awk '{print $5, $NF}'

# Example output:
# 1.2K artifacts/src_main_py/pm_response_20251221_143022.md
# 1.5K artifacts/src_main_py/dev_response_20251221_143023.md
# 890B artifacts/src_main_py/qa_response_20251221_143024.md
```

---

## 🎉 Completion Criteria

**Phase 15-2 is COMPLETE when:**

✅ All 5 basic tests pass
✅ Artifacts created with correct structure
✅ YAML frontmatter present and valid
✅ Files organized by node_id
✅ No errors in Flask console
✅ No errors in browser console
✅ Success messages visible in chat

**Then you're ready for Phase 15-3!** 🚀

---

**Questions? Check:**
- `docs/PHASE_15-2_COMPLETE.md` - Full implementation details
- Browser console (F12) - Frontend logs
- Flask console - Backend logs
- `artifacts/` directory - Created files

**Happy testing!** 🧪✨
