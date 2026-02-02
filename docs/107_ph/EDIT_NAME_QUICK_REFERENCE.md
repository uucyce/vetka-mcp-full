# Edit Name / Rename Chat - Quick Reference

## 🔍 Where the Button Is

### ✅ Solo Chat - Sidebar
- **File:** `client/src/components/chat/ChatSidebar.tsx` (Line 284)
- **Icon:** Pencil ✎
- **Status:** WORKING
- **Marker:** `MARKER_EDIT_NAME_SIDEBAR`

### ✅ Solo Chat - Header
- **File:** `client/src/components/chat/ChatPanel.tsx` (Line 1952)
- **Button:** Click on chat name in header
- **Status:** WORKING
- **Marker:** `MARKER_EDIT_NAME_CHAT`

### ⚠️ Group Chat - Creation Panel
- **File:** `client/src/components/chat/GroupCreatorPanel.tsx` (Line 420)
- **Field:** "Group Name" text input
- **Status:** WORKS ON CREATION ONLY, NO RENAME AFTER
- **Marker:** `MARKER_EDIT_NAME_GROUP`

---

## 🔌 API Endpoint

```
PATCH /api/chats/{chat_id}

Request:
{
  "display_name": "New Chat Name"
}

Response:
{
  "success": true,
  "chat_id": "uuid...",
  "display_name": "New Chat Name"
}
```

**File:** `src/api/routes/chat_history_routes.py` (Line 245)
**Marker:** `MARKER_EDIT_NAME_API`
**Status:** WORKING

---

## 🛠️ Backend Handler

**Method:** `ChatHistoryManager.rename_chat(chat_id, new_name)`
**File:** `src/chat/chat_history_manager.py` (Line 391)
**Marker:** `MARKER_EDIT_NAME_HANDLER`
**Status:** WORKING

**What it does:**
1. Updates `display_name` field in chat object
2. Updates `updated_at` timestamp
3. Saves to `data/chat_history.json`
4. Returns True/False

---

## 📊 Functionality Matrix

| Feature | Sidebar | Header | Group | Status |
|---------|---------|--------|-------|--------|
| See Button | ✅ | ✅ | ✅ | All visible |
| Click Button | ✅ | ✅ | N/A | Works |
| Rename | ✅ | ✅ | ❌ | Solo works |
| Persist | ✅ | ✅ | N/A | JSON storage |
| Update UI | ✅ | ✅ | N/A | Immediate |

---

## 🚀 How It Works

### Solo Chat Rename Flow

```
User clicks "Edit Name" button
    ↓
prompt("Enter new name...")
    ↓
Validate (not empty, not same)
    ↓
PATCH /api/chats/{id}
    ↓
ChatHistoryManager.rename_chat()
    ↓
Save to data/chat_history.json
    ↓
Update local state
    ↓
UI reflects new name immediately
```

---

## ⚠️ Known Issues

### Group Chat Rename
- **Problem:** Can only rename on creation, no rename after
- **Root Cause:** No PATCH endpoint for `/api/groups/{group_id}`
- **Fix Needed:**
  - Add group rename endpoint
  - Add UI button in edit mode
  - Add backend handler

---

## 🔍 Validation Rules

1. **Not Empty**
   - Rejects empty strings
   - Error: "display_name is required and cannot be empty"

2. **Not Same**
   - Doesn't allow renaming to current name
   - Uses `prompt()` which returns null on cancel

3. **Trimmed**
   - All names automatically trimmed of whitespace
   - Prevents leading/trailing space issues

---

## 📝 Testing Quick Checklist

```
[ ] Sidebar rename works (click pencil icon)
[ ] Header rename works (click chat name)
[ ] Rename persists after refresh
[ ] Empty names rejected
[ ] No-change renames rejected
[ ] Error on network failure shown
[ ] Both updates show immediately (sidebar + header)
```

---

## 🔗 Related Files

**Frontend:**
- `client/src/components/chat/ChatSidebar.tsx` - Sidebar UI + handler
- `client/src/components/chat/ChatPanel.tsx` - Header UI + handler
- `client/src/components/chat/GroupCreatorPanel.tsx` - Group creation

**Backend:**
- `src/api/routes/chat_history_routes.py` - API endpoint
- `src/chat/chat_history_manager.py` - Storage handler

**Data:**
- `data/chat_history.json` - Persistent storage

---

## 💡 Development Tips

### To Test Rename:
```bash
# 1. Start app
npm start

# 2. Create a chat with some messages
# 3. Click pencil icon (sidebar) or chat name (header)
# 4. Enter new name
# 5. Check both locations update immediately
# 6. Refresh page - new name persists
```

### To Debug:
```javascript
// In browser console
// Check if API call succeeded
fetch('/api/chats/{chat_id}')
  .then(r => r.json())
  .then(d => console.log(d.display_name))

// Check storage
localStorage.getItem('vetka_chat_width')
```

### To Add Group Rename:
1. Add PATCH handler to `GroupChatManager`
2. Add API endpoint `/api/groups/{group_id}`
3. Add rename button to edit mode UI
4. Call endpoint like solo chat rename

---

**Last Updated:** 2026-02-02
**Audit Status:** Complete with Markers
**Markers Added:** 5 total (2 frontend, 3 backend)
