# H1 Report: Chat Context Switch Analysis

## MARKER_H1_ROOT_CAUSE
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`
**Lines:** 923-1002

The auto-chat-clearing behavior is triggered by a `useEffect` hook that listens to `selectedNode?.path` changes. When a new file is selected in the 3D tree (via node click), the chat automatically clears and loads the chat history for that file.

**Key mechanism:**
```typescript
useEffect(() => {
  // Phase 52.1: Clear chat when file selection changes
  if (!selectedNode) {
    clearChat();
    return;
  }

  // ... (rest of loading logic)
  loadChatByFilePath();
}, [selectedNode?.path, clearChat, addChatMessage]);
```

---

## MARKER_H1_TRIGGER
**Trigger Event:** File selection in 3D canvas via mouse click on FileCard

**Flow:**
1. User clicks a FileCard (3D node) in the canvas → `FileCard.tsx` line 517
2. `onClick` callback fires → `handleClick` function
3. Calls `onClick?.()` which is passed as `selectNode(node.id)` from `App.tsx` line 532
4. `selectNode(node.id)` updates Zustand store → `useStore.ts` line 194
5. Store update triggers React re-render
6. `selectedNode?.path` dependency in `ChatPanel.tsx` useEffect changes
7. `useEffect` fires and clears/reloads chat

---

## MARKER_H1_CURRENT_FLOW
**Complete Event Chain:**

```
User clicks file card (3D)
    ↓
FileCard.handleClick() (line 503-520)
    ↓
selectNode(node.id) called
    ↓
useStore.ts → selectNode action (line 194)
    ↓
selectedId: id → store state updated
    ↓
selectedNode?.path dependency changes
    ↓
ChatPanel.tsx useEffect (line 923) fires
    ↓
if (!selectedNode) → clearChat()
OR if (isNullContext) → clearChat()
OR loadChatByFilePath() → fetch and reload messages
    ↓
clearChat() → chatMessages: [], currentWorkflow: null, streamingContent: ''
```

**Related Dependency Chain:**
- App.tsx: `selectedId = useStore((state) => state.selectedId)` (line 50)
- ChatPanel.tsx: `selectedNode = useStore((s) => s.selectedId ? s.nodes[s.selectedId] : null)` (line 46)
- ChatPanel.tsx: useEffect watches `[selectedNode?.path, clearChat, addChatMessage]` (line 1002)

---

## MARKER_H1_FIX_LOCATION
**Where to disable auto-switching:**

The problematic behavior is in `ChatPanel.tsx`, lines 923-1002 in the `useEffect` hook. There are two options:

### Option A: Remove the auto-load behavior entirely
Remove or comment out the useEffect that watches `selectedNode?.path` and automatically clears/reloads chat.

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`
**Lines:** 923-1002

### Option B: Add a flag to disable auto-switching
Create a user preference or state flag that preserves the current chat even when selecting a new file.

**Implementation location:**
- Add state in ChatPanel or App.tsx
- Modify the condition in the useEffect to check this flag before clearing
- Keep the loadChatByFilePath logic for manual selection only

### Option C: Separate file selection from chat switching
Make chat switching a manual action (e.g., via sidebar, double-click, or explicit menu) rather than automatic on single click.

---

## MARKER_H1_CODE_SNIPPET

### Current Problematic Code (ChatPanel.tsx, lines 919-1002):
```typescript
// Phase 52.1: Clear chat when file selection changes
// Phase 52.3: Fixed to find chat by file_path, then load by chat_id
// Phase 52.4: Also handle deselection (null node)
// Phase 74.2: Skip auto-load for null-context paths (unknown/root/'')
useEffect(() => {
  // Phase 52.4: If no node selected, clear chat
  if (!selectedNode) {
    // console.log('[ChatPanel] No node selected - clearing chat');
    clearChat();
    return;
  }

  // Phase 74.2: Don't auto-load history for null-context paths
  // User must explicitly select a chat from sidebar for these
  const isNullContext = !selectedNode.path ||
    selectedNode.path === 'unknown' ||
    selectedNode.path === 'root';

  if (isNullContext) {
    // console.log('[ChatPanel] Null context - starting fresh (use sidebar to load specific chat)');
    clearChat();
    return;
  }

  // console.log(`[ChatPanel] File changed to: ${selectedNode.path}`);

  // Clear current messages
  clearChat();

  // Find chat by file_path, then load by chat_id
  const loadChatByFilePath = async () => {
    try {
      // 1. Get all chats
      const allChatsResponse = await fetch('/api/chats');
      if (!allChatsResponse.ok) {
        // console.log(`[ChatPanel] No chats available, starting fresh`);
        return;
      }

      const allChatsData = await allChatsResponse.json();
      const chats = allChatsData.chats || [];

      // 2. Find chat with matching file_path
      const chat = chats.find((c: any) => c.file_path === selectedNode.path);

      if (!chat) {
        // console.log(`[ChatPanel] No history found for ${selectedNode.name}, starting fresh`);
        return;
      }

      // 3. Load messages by chat_id
      // console.log(`[ChatPanel] Found chat for ${selectedNode.name}, loading messages...`);
      const messagesResponse = await fetch(`/api/chats/${chat.id}`);

      if (!messagesResponse.ok) {
        // console.warn(`[ChatPanel] Failed to load messages for chat ${chat.id}`);
        return;
      }

      const messagesData = await messagesResponse.json();

      if (messagesData.messages) {
        // console.log(`[ChatPanel] Loaded ${messagesData.messages.length} messages for ${selectedNode.name}`);

        // Add all messages from the chat history
        for (const msg of messagesData.messages) {
          addChatMessage({
            id: msg.id || crypto.randomUUID(),
            role: msg.role,
            content: msg.content,
            agent: msg.agent,
            type: msg.role === 'user' ? 'text' : 'text',
            timestamp: msg.timestamp || new Date().toISOString(),
          });
        }
      }
    } catch (error) {
      // console.log(`[ChatPanel] Error loading chat for ${selectedNode.name}:`, error);
      // Keep empty chat on error
    }
  };

  loadChatByFilePath();
}, [selectedNode?.path, clearChat, addChatMessage]);
```

### To Fix - Option A (Remove auto-load):
Comment out or delete the entire `useEffect` block above (lines 923-1002).

### To Fix - Option B (Add flag):
```typescript
// Add state flag
const [autoLoadChat, setAutoLoadChat] = useState(true); // Can be toggled by user

// Modify useEffect condition:
useEffect(() => {
  if (!autoLoadChat) return; // NEW: Skip if disabled

  // ... rest of existing logic
}, [selectedNode?.path, clearChat, addChatMessage, autoLoadChat]); // Add flag to deps
```

---

## Summary

**The Problem:** When users click on files in the 3D canvas to explore or organize them, the chat automatically switches to that file's conversation, losing the current chat context.

**Why It Happens:** The `ChatPanel` component has a `useEffect` hook (Phase 52.1) that watches for file selection changes and automatically clears the current chat and loads the selected file's chat history.

**Impact:** Users cannot freely navigate the file tree without disrupting their current conversation.

**Recommended Solution:** Remove or conditionally disable the auto-switching behavior in ChatPanel.tsx lines 923-1002, allowing users to manually select chats from the sidebar while exploring files freely.
