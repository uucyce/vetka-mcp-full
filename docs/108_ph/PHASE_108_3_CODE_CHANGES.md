# Phase 108.3: Chat Node Click Handler - Code Changes

**Marker:** `MARKER_108_3_CLICK_HANDLER`

## Quick Reference

### 1. TreeNode Type Extension

**File:** `client/src/store/useStore.ts`

```typescript
export interface TreeNode {
  id: string;
  path: string;
  name: string;
  type: 'file' | 'folder' | 'chat' | 'artifact'; // Added 'chat' | 'artifact'
  backendType: VetkaNodeType;
  depth: number;
  parentId: string | null;
  position: { x: number; y: number; z: number };
  color: string;
  extension?: string;
  semanticPosition?: {
    x: number;
    y: number;
    z: number;
    knowledgeLevel: number;
  };
  children?: string[];
  isGhost?: boolean;
  opacity?: number;
  // MARKER_108_3_CHAT_METADATA: Phase 108.3 - Chat node metadata
  metadata?: {
    chat_id?: string;
    message_count?: number;
    participants?: string[];
    decay_factor?: number;
    last_activity?: string;
    context_type?: string;
  };
}
```

---

### 2. Chat Node Converter

**File:** `client/src/utils/apiConverter.ts`

```typescript
export function chatNodeToTreeNode(chatNode: ChatNode, position: { x: number; y: number; z: number }): TreeNode {
  return {
    id: chatNode.id,
    path: chatNode.id,
    name: chatNode.name,
    type: 'chat', // MARKER_108_3_CHAT_TYPE: Changed from 'file' to 'chat'
    backendType: 'leaf',
    depth: 0,
    parentId: chatNode.parentId,
    position,
    color: '#4a9eff',
    opacity: chatNode.decay_factor,
    // MARKER_108_3_CHAT_METADATA: Phase 108.3 - Include chat metadata for click handling
    metadata: {
      chat_id: chatNode.userId, // userId stores the backend chat_id
      message_count: chatNode.messageCount,
      participants: chatNode.participants,
      decay_factor: chatNode.decay_factor,
      last_activity: chatNode.lastActivity.toISOString(),
      context_type: 'chat',
    },
  };
}
```

---

### 3. FileCard Click Handler

**File:** `client/src/components/canvas/FileCard.tsx`

**Location:** Inside `handleClick` callback (around line 735)

```typescript
const handleClick = useCallback(
  (e: any) => {
    // Phase 65: Ctrl/Cmd+Click reserved for drag initiation
    if (e.ctrlKey || e.metaKey) return;

    e.stopPropagation();

    // Phase 65: Shift+Click = Smart Pin (file → toggle, folder → subtree)
    if (e.shiftKey) {
      pinNodeSmart(id);
      return;
    }

    // MARKER_108_3_CLICK_HANDLER: Phase 108.3 - Chat node click opens ChatPanel
    if (type === 'chat') {
      const chatId = metadata?.chat_id;
      if (chatId) {
        // Dispatch custom event to open ChatPanel with this chat
        window.dispatchEvent(new CustomEvent('vetka-open-chat', {
          detail: {
            chatId,
            fileName: name,
            filePath: path,
          },
        }));
        console.log('[FileCard] Phase 108.3: Opening chat', chatId, 'via event');
      }
      return;
    }

    // Normal click = Select
    onClick?.();
  },
  [onClick, id, pinNodeSmart, type, metadata, name, path] // Added: type, metadata, name, path
);
```

---

### 4. ChatPanel Event Listener

**File:** `client/src/components/chat/ChatPanel.tsx`

**Location:** After `askHostessAboutKey` useEffect (around line 230)

```typescript
// MARKER_108_3_CLICK_HANDLER: Phase 108.3 - Listen for chat node clicks from 3D view
useEffect(() => {
  const handleOpenChat = async (e: CustomEvent) => {
    const { chatId, fileName, filePath } = e.detail;
    if (!chatId) return;

    console.log('[ChatPanel] Phase 108.3: Opening chat from 3D node click:', chatId);

    // Dispatch event to open ChatPanel if not already open
    // App.tsx will handle the state change
    if (!isOpen) {
      window.dispatchEvent(new CustomEvent('vetka-toggle-chat-panel'));
    }

    // Switch to chat tab
    setActiveTab('chat');

    // Load the chat using handleSelectChat
    await handleSelectChat(chatId, filePath, fileName);
  };

  window.addEventListener('vetka-open-chat', handleOpenChat as EventListener);
  return () => {
    window.removeEventListener('vetka-open-chat', handleOpenChat as EventListener);
  };
}, [isOpen, handleSelectChat]);
```

---

### 5. App.tsx Panel Toggle

**File:** `client/src/App.tsx`

**Location:** Before "Phase 65: G key for grab mode" (around line 200)

```typescript
// MARKER_108_3_CLICK_HANDLER: Phase 108.3 - Listen for chat panel open requests
useEffect(() => {
  const handleToggleChatPanel = () => {
    if (!isChatOpen) {
      setIsChatOpen(true);
    }
  };

  window.addEventListener('vetka-toggle-chat-panel', handleToggleChatPanel);
  return () => window.removeEventListener('vetka-toggle-chat-panel', handleToggleChatPanel);
}, [isChatOpen]);
```

---

## Custom Events

### Event: `vetka-open-chat`

**Dispatched by:** FileCard.tsx
**Listened by:** ChatPanel.tsx

```typescript
// Dispatch
window.dispatchEvent(new CustomEvent('vetka-open-chat', {
  detail: {
    chatId: string,      // Backend chat UUID
    fileName: string,    // Display name
    filePath: string,    // Node path
  },
}));

// Listen
window.addEventListener('vetka-open-chat', (e: CustomEvent) => {
  const { chatId, fileName, filePath } = e.detail;
  // Handle...
});
```

---

### Event: `vetka-toggle-chat-panel`

**Dispatched by:** ChatPanel.tsx
**Listened by:** App.tsx

```typescript
// Dispatch
window.dispatchEvent(new CustomEvent('vetka-toggle-chat-panel'));

// Listen
window.addEventListener('vetka-toggle-chat-panel', () => {
  setIsChatOpen(true);
});
```

---

## Files Changed

1. `client/src/store/useStore.ts` - TreeNode type extension
2. `client/src/utils/apiConverter.ts` - chatNodeToTreeNode update
3. `client/src/components/canvas/FileCard.tsx` - Click handler
4. `client/src/components/chat/ChatPanel.tsx` - Event listener
5. `client/src/App.tsx` - Panel toggle listener

---

## Testing

```bash
# 1. Start backend
cd /path/to/vetka_live_03
python src/main.py

# 2. Start frontend
cd client
npm run dev

# 3. Click on blue chat node in 3D viewport
# 4. Check console for:
[FileCard] Phase 108.3: Opening chat {chatId} via event
[ChatPanel] Phase 108.3: Opening chat from 3D node click: {chatId}
```

---

## Integration Checklist

- [x] TreeNode type supports 'chat' type
- [x] TreeNode has metadata field with chat_id
- [x] chatNodeToTreeNode sets type='chat'
- [x] chatNodeToTreeNode includes metadata
- [x] FileCard detects chat type clicks
- [x] FileCard dispatches vetka-open-chat event
- [x] ChatPanel listens for vetka-open-chat
- [x] ChatPanel dispatches vetka-toggle-chat-panel if needed
- [x] App.tsx listens for vetka-toggle-chat-panel
- [x] handleSelectChat loads chat by ID
- [x] Event listeners cleaned up on unmount
- [x] Console logging for debugging

---

**Marker Search:** `MARKER_108_3_CLICK_HANDLER`
**Related Markers:** `MARKER_108_3_CHAT_METADATA`, `MARKER_108_3_CHAT_TYPE`
