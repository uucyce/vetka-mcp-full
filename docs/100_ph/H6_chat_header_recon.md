# H6 Reconnaissance Report: Missing Chat Header

**Status:** INVESTIGATION COMPLETE
**Severity:** Medium
**Date:** 2026-01-29

---

## Executive Summary

The editable chat header that displays the chat name/title **DOES EXIST IN CODE** but is **NOT VISIBLE** in normal solo chat usage. The header only appears in two specific scenarios:
1. When loading an existing chat from history
2. When creating/viewing a group chat

**Root Cause:** `currentChatInfo` state is never set during normal solo chat flow, causing the header condition to fail.

---

## Finding #1: Header Code IS Present

**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`
**Lines:** 1869-1957

### Code Structure
```tsx
// Phase 74.3: Chat name header - like pinned context, editable
// Phase 74.5: Don't show if file chat and file is already in pinned context
{(activeTab === 'chat' || activeTab === 'group') && currentChatInfo &&
 !(currentChatInfo.contextType === 'file' && pinnedFileIds.length > 0) && (
  <div style={{...}}>
    {/* Icon based on context type (folder/group/topic/file) */}
    {/* Chat name display */}
    {/* Edit icon */}
    {/* Close/clear icon */}
  </div>
)}
```

### Header Features (all implemented)
- **Editable:** Click to rename via prompt dialog (line 1879, `handleRenameChatFromHeader`)
- **Context Icons:** SVG icons for file, folder, group, topic types (lines 1904-1922)
- **Rename Function:** Updates backend via PATCH `/api/chats/{id}` (lines 802-806)
- **Clear Button:** Can close/clear chat info (lines 1936-1954)

---

## Finding #2: `currentChatInfo` State is Never Set in Solo Chat

**Problem Location:** State initialization at line 90

```tsx
const [currentChatInfo, setCurrentChatInfo] = useState<{
  id: string;
  displayName: string | null;
  fileName: string;
  contextType: string;
} | null>(null);
```

### Where `currentChatInfo` IS Set

| Location | Scenario | Lines |
|----------|----------|-------|
| `handleSelectChat` | Loading chat from history | 838-843 |
| `handleCreateGroup` | After group creation | 626-631 |
| `handleRenameChatFromHeader` | After successful rename | 809 |
| User action | Clear/close header | 1946 |

### Where `currentChatInfo` Should Be Set (But Isn't)

**`handleSend` callback** (lines 663-733) - No `setCurrentChatInfo` call for solo chat:

```tsx
const handleSend = useCallback(() => {
  if (!input.trim()) return;
  if (!isConnected) { /* error */ return; }

  if (activeGroupId) {
    sendGroupMessage(activeGroupId, 'user', input.trim(), replyTo?.id);
    // Group flow sets currentChatInfo via group creation
    return;
  }

  // SOLO CHAT FLOW - currentChatInfo is NOT set here
  const userMessage: ChatMessage = { /* ... */ };
  addChatMessage(userMessage);
  sendMessage(input.trim(), contextPath, modelToUse);
  setInput('');
  setSelectedModel(null);
  setReplyTo(null);
  setIsTyping(true);
  // Missing: No setCurrentChatInfo for auto-generated/transient chat
}, [input, isConnected, selectedNode, selectedModel, replyTo, ...]);
```

---

## Finding #3: Display Condition Requires `currentChatInfo` to be Truthy

**Line 1871-1872 (Render Condition):**
```tsx
{(activeTab === 'chat' || activeTab === 'group') && currentChatInfo &&
 !(currentChatInfo.contextType === 'file' && pinnedFileIds.length > 0) && (
```

**Evaluation:**
- `activeTab === 'chat'` ✓ (true in normal chat mode)
- `currentChatInfo` ✗ (null → FAILS)
- Only if both true: render header

---

## Finding #4: Header Design Rationale

From Phase 74 commit (`fffa4a4d`):

> "Phase 74: Chat History — Folder Support + Rename + Groups
> - Added editable chat name header in ChatPanel
> - Phase 74.5: Don't show if file chat and file is already in pinned context"

**Design Intent:** Header should show:
1. Renamed chats (via `display_name`)
2. Folder context chats
3. Group chats
4. NOT show when file context is already in pinned files (avoid duplication)

**Current Behavior:** Only shows for explicitly loaded chats (#1-3 above) or newly created groups.

---

## Finding #5: Rename Handler IS Functional

**Line 791-816 - `handleRenameChatFromHeader`:**

```tsx
const handleRenameChatFromHeader = useCallback(async () => {
  if (!currentChatInfo) return;

  const currentName = currentChatInfo.displayName || currentChatInfo.fileName;
  const newName = prompt('Enter new name for this chat:', currentName);

  if (!newName || newName.trim() === '' || newName.trim() === currentName) {
    return;
  }

  try {
    const response = await fetch(`/api/chats/${currentChatInfo.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ display_name: newName.trim() })
    });

    if (response.ok) {
      setCurrentChatInfo(prev => prev ? { ...prev, displayName: newName.trim() } : null);
    }
  } catch (error) {
    console.error('[ChatPanel] Error renaming chat:', error);
  }
}, [currentChatInfo]);
```

✓ Fully implemented, no bugs detected

---

## Problem Analysis

### Why User Sees Missing Header

1. User clicks "Chat" tab
2. User sends first message without loading from history
3. `handleSend()` executes but doesn't create `currentChatInfo`
4. `currentChatInfo === null`
5. Header render condition fails: `null && ...` = false
6. **Header not rendered** even though UI code exists

### Current Workflow vs Expected

| Scenario | Expected | Current |
|----------|----------|---------|
| Load chat from history | Header appears | Header appears ✓ |
| Create group chat | Header appears | Header appears ✓ |
| Start fresh solo chat | Header appears? | Header doesn't appear ✗ |
| Auto-sync chat on file select | Header appears? | No auto-sync, stays null ✗ |

---

## Recommendations

### Option A: Show Header for All Solo Chats (Restore Original Behavior)

**When to implement:** If Phase 74 intended headers for all chats

**Change location:** `handleSend()` or file selection effect

**Logic:**
```tsx
// When user sends first message in solo chat
if (!activeGroupId && !currentChatInfo && selectedNode) {
  setCurrentChatInfo({
    id: crypto.randomUUID(), // temp ID until backend persistence
    displayName: null,       // auto-derive from first query
    fileName: selectedNode.name,
    contextType: 'file'
  });
}
```

### Option B: Backend Auto-Create Chat Records (Recommended)

**When to implement:** For proper persistence of solo chats

**Logic:**
- Backend creates chat record on first message
- Return `chat_id` in response
- Client calls `setCurrentChatInfo()` after backend confirmation
- Aligns with chat history persistence (Phase 74 design)

### Option C: Keep Header for History/Groups Only (Current State)

**Decision:** If solo chats are intentionally transient

**Update:** Add comment explaining design choice

---

## Code References

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| State init | ChatPanel.tsx | 90-95 | `currentChatInfo` declaration |
| Render logic | ChatPanel.tsx | 1869-1872 | Header condition |
| Rename handler | ChatPanel.tsx | 791-816 | Editable rename feature |
| History load | ChatPanel.tsx | 838-843 | Sets header on load |
| Group creation | ChatPanel.tsx | 626-631 | Sets header on group creation |
| Send handler | ChatPanel.tsx | 663-733 | MISSING: No currentChatInfo set |

---

## Git History

**Introduced:** Phase 74 (commit `fffa4a4d`)
**Date:** Jan 20, 2026
**Last modified:** Jan 28, 2026 (commit `6f866f38` - minor refinements)

No code removal detected - feature is intact but inactive.

---

## Conclusion

The chat header functionality is **100% implemented and functional**. The disappearance is due to a **missing initialization step** in the solo chat flow, not code removal or bugs.

**Status:** READY FOR DECISION
**Next Step:** Recommend Option B (backend auto-create) or add Option A (frontend temp creation) to restore header visibility.
