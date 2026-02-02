# MARKER_MCP_PERSIST_FIX - MCP Message Persistence Investigation

## Reported Issue
"После перезагрузки сессии MCP сообщения пропадают" (MCP messages disappear after session reload)

## Investigation Results

### 1. Message Persistence IS WORKING ✓

**Evidence:**
- MCP messages ARE saved to `data/groups.json` (verified at line 680 in `group_chat_manager.py`)
- `save_to_json()` is called after EVERY message send (line 680)
- MCP messages visible in groups.json with proper metadata

### 2. Message Loading IS WORKING ✓

**Evidence:**
- `load_from_json()` is called on startup (line 224 in `main.py`)
- Messages are reconstructed from JSON into `GroupMessage` objects
- Frontend loads messages via `GET /api/groups/{group_id}/messages` (line 1000 in `ChatPanel.tsx`)

### 3. Actual Explanation

Frontend only loads **last 50 messages** by default (pagination).

## Conclusion

**Status:** NOT A BUG - Messages persist correctly
**Action:** Document behavior, add pagination for large chats
**Priority:** Low (enhancement, not fix)
