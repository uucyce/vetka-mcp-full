# Phase 107: Chat UI Markers Report
**Agent:** Haiku
**Date:** 2026-02-02
**Status:** Complete

---

## Summary

| Feature | Location | Status | Action |
|---------|----------|--------|--------|
| Rename Button (Sidebar) | ChatSidebar.tsx:257 | ✅ WORKING | No marker needed |
| Rename Button (Header) | ChatPanel.tsx:1913 | ✅ WORKING | No marker needed |
| New Chat Button | ChatSidebar.tsx | ❌ MISSING | **ADD MARKER** |
| Scroll-to-Bottom Button | ChatPanel.tsx | ❌ MISSING | **ADD MARKER** |
| Chat Naming (Semantic) | user_message_handler.py:297 | ✅ IMPLEMENTED | Update marker |

---

## Detailed Findings

### 1. RENAME BUTTON - WORKING

**Status:** No marker needed

The rename functionality is complete:
- `ChatSidebar.tsx:130-158` - `handleRenameChat()` handler
- `ChatSidebar.tsx:257` - Edit button with onClick
- `ChatPanel.tsx:825-850` - `handleRenameChatFromHeader()`
- `ChatPanel.tsx:1913` - Header click event

Implementation includes PATCH requests, state updates, error handling.

---

### 2. NEW CHAT BUTTON - MISSING

**Status:** Add MARKER_CHAT_NEW_BUTTON

**Location:** ChatSidebar.tsx footer area (near line 280)

**Problem:**
- No "New Chat" button exists
- Users cannot start fresh conversations
- Only Refresh button exists in footer

**Marker to add:**
```typescript
// MARKER_CHAT_NEW_BUTTON: "New Chat" button missing from sidebar
// Current: Only Refresh button, no way to start new chat
// Fix: Add "+ New Chat" button that:
// 1. Clears currentChatId
// 2. Clears chat messages
// 3. Shows welcome screen
```

---

### 3. SCROLL-TO-BOTTOM BUTTON - MISSING

**Status:** Add MARKER_CHAT_SCROLL_BUTTON

**Location:** ChatPanel.tsx messages container (line 2160 area)

**Problem:**
- Only auto-scroll on new messages (Phase 50.4, lines 990-1003)
- No manual scroll button
- Users can't quickly return to latest messages

**Marker to add:**
```typescript
// MARKER_CHAT_SCROLL_BUTTON: Scroll-to-bottom button missing
// Current: Only auto-scroll, no manual button
// Fix: Add floating button when user scrolls up
// 1. Track isAtBottom state
// 2. Show floating down-arrow button
// 3. onClick: smooth scroll to bottom
// Position: absolute, bottom-right of messages
```

---

### 4. CHAT NAMING - IMPLEMENTED

**Status:** Update existing MARKER_CHAT_NAMING

**Location:** user_message_handler.py:297-312

**What's working:**
- `generate_semantic_key()` extracts keywords from messages
- Creates chat with `display_name=semantic_key`

**Issues to verify:**
1. Underscore format ("fix_bug_report") vs spaces in UI
2. All semantic chats use `file_path='unknown'`
3. Max 30 chars truncation

---

## Priority

| Priority | Feature | Reason |
|----------|---------|--------|
| 🔴 HIGH | New Chat Button | Users can't start new conversations |
| 🔴 HIGH | Scroll-to-Bottom | Users can't return to latest messages |
| 🟡 MEDIUM | Chat Naming Display | Underscore to space formatting |

---

## Files Analyzed

1. `client/src/components/chat/ChatSidebar.tsx` - 298 lines
2. `client/src/components/chat/ChatPanel.tsx` - 2300+ lines
3. `src/api/handlers/user_message_handler.py` - 1700+ lines
