# Chat Node Integration - Quick Reference

## API Response Format

```typescript
{
  success: true,
  tree: {
    nodes: [...],  // File/folder nodes
    edges: [...]
  },
  chat_nodes: [
    {
      id: "chat_abc123",
      type: "chat",
      name: "Chat: main.py discussion",
      parent_id: "src/main.py",
      metadata: {
        chat_id: "abc123",
        file_path: "src/main.py",
        last_activity: "2026-02-02T12:00:00Z",
        message_count: 15,
        participants: ["@architect", "@qa"],
        decay_factor: 0.95,
        context_type: "file_context"
      },
      visual_hints: {
        layout_hint: { expected_x: 10, expected_y: 5, expected_z: 0 },
        color: "#4a9eff",
        opacity: 0.95
      }
    }
  ],
  chat_edges: [
    {
      from: "src/main.py",
      to: "chat_abc123",
      semantics: "chat",
      metadata: { type: "chat", color: "#4a9eff", opacity: 0.8 }
    }
  ]
}
```

---

## Data Flow

```
API → fetchTreeData() → useTreeData() hook
                          ├─> convertChatNode() → chatTreeStore
                          ├─> chatNodeToTreeNode() → useStore (for 3D)
                          └─> convertChatEdge() → edges
```

---

## Modified Files

### 1. `/client/src/utils/api.ts`
- Added `ChatNodeAPI` and `ChatEdgeAPI` interfaces
- Updated `ApiTreeResponse` to include `chat_nodes?` and `chat_edges?`
- Modified `fetchTreeData()` to return chat data

### 2. `/client/src/utils/apiConverter.ts`
- Added `convertChatNode()` - API → ChatNode
- Added `convertChatEdge()` - API → TreeEdge
- Added `chatNodeToTreeNode()` - ChatNode → TreeNode (for 3D)

### 3. `/client/src/hooks/useTreeData.ts`
- Imported chat converters and `useChatTreeStore`
- Added chat node processing loop
- Merged chat nodes with file tree nodes
- Merged chat edges with tree edges

---

## Key Functions

### convertChatNode()
```typescript
// Converts API format to frontend ChatNode
ChatNodeAPI → ChatNode (stored in chatTreeStore)
```

### chatNodeToTreeNode()
```typescript
// Converts ChatNode to TreeNode for 3D rendering
ChatNode → TreeNode {
  type: 'file',
  color: '#4a9eff',
  opacity: decay_factor
}
```

### convertChatEdge()
```typescript
// Converts API edge to TreeEdge
ChatEdgeAPI → TreeEdge { type: 'chat' }
```

---

## Integration Points

### chatTreeStore
- Stores chat-specific data (`ChatNode`)
- Used by `ChatPanel` for message rendering
- Accessed via `useChatTreeStore()`

### useStore
- Stores unified `TreeNode[]` for 3D rendering
- Includes both file nodes and chat nodes
- Used by `FileCard`, `TreeEdges`, canvas components

---

## Backwards Compatibility

**API without chat_nodes:**
```typescript
{
  success: true,
  tree: { nodes: [...], edges: [...] }
  // No chat_nodes or chat_edges
}
```

**Behavior:**
- Chat processing is skipped
- Only file tree renders
- ✅ No errors

---

## Debugging

### Console Logs
```
[useTreeData] Processing chat nodes: 3
[useTreeData] Converted chat nodes: 3
[useTreeData] Chat edges: 3
```

### Browser DevTools
```javascript
// Check useStore
window.store = useStore.getState();
console.log(Object.keys(store.nodes).filter(k => k.startsWith('chat_')));

// Check chatTreeStore
window.chatStore = useChatTreeStore.getState();
console.log(chatStore.chatNodes);
```

---

## Next Steps

1. Test with real API data
2. Add chat node click handler in `FileCard.tsx`
3. Style chat edges differently in `TreeEdges.tsx`
4. Add chat icon in `FileCard` for type='chat'

---

## Markers

All code marked with: `MARKER_108_CHAT_FRONTEND`

Search:
```bash
grep -r "MARKER_108_CHAT_FRONTEND" client/src
```

---

## Example Usage

```typescript
// In a component
import { useChatTreeStore } from '../store/chatTreeStore';

function MyComponent() {
  const chatNodes = useChatTreeStore(state => state.chatNodes);
  const nodes = useStore(state => state.nodes);

  // chatNodes → Chat-specific data (message count, participants)
  // nodes → All nodes for 3D rendering (includes chat nodes as TreeNode)
}
```
