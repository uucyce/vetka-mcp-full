# Phase 108.2 - Chat Nodes Frontend Integration

**Status:** Implemented
**Date:** 2026-02-02
**Task:** Extend `useTreeData` hook to handle chat_nodes from API

---

## Overview

Extended the frontend tree data fetching logic to integrate chat nodes from the backend API (`/api/tree/data`). Chat nodes now render alongside file/folder nodes in the 3D visualization with proper positioning and edge connections.

---

## Architecture

### Data Flow

```
Backend API (/api/tree/data)
  ↓
  Includes: { tree: {...}, chat_nodes: [...], chat_edges: [...] }
  ↓
fetchTreeData() in api.ts
  ↓
useTreeData() hook
  ↓
  ├─> convertChatNode() → ChatNode (stored in chatTreeStore)
  ├─> chatNodeToTreeNode() → TreeNode (for 3D rendering)
  └─> convertChatEdge() → TreeEdge
  ↓
Merged with file tree nodes
  ↓
useStore (unified nodes + edges)
  ↓
3D Canvas rendering
```

### Type Mapping

**API Response:**
```typescript
interface ChatNodeAPI {
  id: string;              // "chat_{uuid}"
  type: "chat";
  name: string;
  parent_id: string | null;
  metadata: {
    chat_id: string;
    file_path: string;
    last_activity: string;
    message_count: number;
    participants: string[];
    decay_factor: number;
    context_type: string;
  };
  visual_hints: {
    layout_hint: { expected_x, expected_y, expected_z };
    color: string;
    opacity: number;
  };
}
```

**Frontend Types:**
- `ChatNode` → Stored in `chatTreeStore` (chat-specific data)
- `TreeNode` → Stored in `useStore` (unified 3D rendering)

---

## Files Modified

### 1. `/client/src/utils/api.ts`

**Added:**
- `ChatNodeAPI` interface
- `ChatEdgeAPI` interface
- `chat_nodes` and `chat_edges` fields to `ApiTreeResponse`

**Changes:**
```typescript
export interface ApiTreeResponse {
  success: boolean;
  tree?: { nodes: VetkaApiNode[]; edges: VetkaApiEdge[] };
  chat_nodes?: ChatNodeAPI[];  // ✅ NEW
  chat_edges?: ChatEdgeAPI[];  // ✅ NEW
  error?: string;
}

export async function fetchTreeData(): Promise<ApiTreeResponse> {
  // ...
  return {
    success: true,
    tree: data.tree,
    chat_nodes: data.chat_nodes,  // ✅ NEW
    chat_edges: data.chat_edges,  // ✅ NEW
  };
}
```

**Marker:** `MARKER_108_CHAT_FRONTEND`

---

### 2. `/client/src/utils/apiConverter.ts`

**Added:**
- Import `ChatNode` from `../types/treeNodes`
- Import `ChatNodeAPI`, `ChatEdgeAPI` from `./api`
- `convertChatNode()` - Converts API format to frontend `ChatNode`
- `convertChatEdge()` - Converts API edges to `TreeEdge`
- `chatNodeToTreeNode()` - Converts `ChatNode` to `TreeNode` for 3D rendering

**Key Functions:**

```typescript
export function convertChatNode(apiChatNode: ChatNodeAPI): ChatNode {
  return {
    id: apiChatNode.id,
    type: 'chat',
    parentId: apiChatNode.parent_id || '',
    name: apiChatNode.name,
    participants: apiChatNode.metadata.participants,
    messageCount: apiChatNode.metadata.message_count,
    lastActivity: new Date(apiChatNode.metadata.last_activity),
    artifacts: [],
    status: 'active',
    decay_factor: apiChatNode.metadata.decay_factor,
    userId: apiChatNode.metadata.chat_id,
  };
}

export function chatNodeToTreeNode(
  chatNode: ChatNode,
  position: { x: number; y: number; z: number }
): TreeNode {
  return {
    id: chatNode.id,
    path: chatNode.id,
    name: chatNode.name,
    type: 'file',
    backendType: 'leaf',
    depth: 0,
    parentId: chatNode.parentId,
    position,
    color: '#4a9eff',  // Blue for chat nodes
    opacity: chatNode.decay_factor,
  };
}
```

**Marker:** `MARKER_108_CHAT_FRONTEND`

---

### 3. `/client/src/hooks/useTreeData.ts`

**Added:**
- Import `convertChatNode`, `convertChatEdge`, `chatNodeToTreeNode`
- Import `useChatTreeStore`
- Chat node processing logic in `loadData()`

**Key Changes:**

```typescript
export function useTreeData() {
  const { addChatNode } = useChatTreeStore();

  useEffect(() => {
    async function loadData() {
      // ... existing code ...

      if (response.tree) {
        const { nodes: convertedNodes, edges } = convertApiResponse(vetkaResponse);

        // ✅ Process chat nodes
        let chatTreeNodes: TreeNode[] = [];
        const chatEdges: typeof edges = [];

        if (response.chat_nodes && response.chat_nodes.length > 0) {
          response.chat_nodes.forEach((apiChatNode) => {
            // 1. Convert to ChatNode and store in chatTreeStore
            const chatNode = convertChatNode(apiChatNode);
            addChatNode(chatNode.parentId, chatNode);

            // 2. Convert to TreeNode for 3D rendering
            const position = {
              x: apiChatNode.visual_hints.layout_hint.expected_x,
              y: apiChatNode.visual_hints.layout_hint.expected_y,
              z: apiChatNode.visual_hints.layout_hint.expected_z,
            };
            const treeNode = chatNodeToTreeNode(chatNode, position);
            chatTreeNodes.push(treeNode);
          });

          // Convert chat edges
          if (response.chat_edges) {
            response.chat_edges.forEach((apiChatEdge, idx) => {
              chatEdges.push(convertChatEdge(apiChatEdge, idx));
            });
          }
        }

        // ✅ Merge file tree nodes and chat nodes
        const allNodes = { ...convertedNodes };
        chatTreeNodes.forEach((chatNode) => {
          allNodes[chatNode.id] = chatNode;
        });

        // ✅ Merge edges
        const allEdges = [...edges, ...chatEdges];

        setNodesFromRecord(allNodes);
        setEdges(allEdges);
      }
    }

    loadData();
  }, [setNodes, setNodesFromRecord, setEdges, setLoading, setError, addChatNode]);
}
```

**Marker:** `MARKER_108_CHAT_FRONTEND`

---

## Integration Strategy

### Dual Storage Approach

**1. chatTreeStore (Chat-specific data):**
- Stores `ChatNode` with chat metadata
- Used by `ChatPanel` for message rendering
- Managed by `useChatTreeStore`

**2. useStore (Unified 3D rendering):**
- Stores `TreeNode` for all nodes (files, folders, chats)
- Used by `FileCard` and `TreeEdges` components
- Managed by `useStore`

### Why This Approach?

1. **Separation of concerns:** Chat logic separate from tree visualization
2. **Type safety:** Each store has appropriate types
3. **Backwards compatibility:** Existing components continue to work
4. **Flexibility:** Can render chat nodes with different styles in 3D

---

## Rendering Pipeline

### 3D Visualization

```typescript
// Chat nodes render as TreeNode with type='file'
TreeNode {
  id: "chat_abc123",
  name: "Chat: main.py discussion",
  type: "file",
  color: "#4a9eff",  // Blue
  opacity: 0.95,     // Based on decay_factor
  position: { x, y, z }  // From backend layout
}
```

### Edge Rendering

```typescript
TreeEdge {
  id: "chat_edge_0",
  source: "src/main.py",  // File node
  target: "chat_abc123",  // Chat node
  type: "chat"
}
```

Edges can be styled differently in `TreeEdges.tsx` based on `type === 'chat'`.

---

## Backwards Compatibility

### API Response Without Chat Nodes

```typescript
// Old API response (still supported)
{
  success: true,
  tree: { nodes: [...], edges: [...] }
  // No chat_nodes or chat_edges
}
```

**Behavior:**
- `response.chat_nodes` is `undefined`
- Condition `if (response.chat_nodes && response.chat_nodes.length > 0)` is false
- Chat processing is skipped
- Only file tree nodes are rendered
- ✅ No breaking changes

---

## Testing Checklist

- [ ] Test API response with `chat_nodes` array
- [ ] Test API response without `chat_nodes` (backwards compat)
- [ ] Verify chat nodes render in 3D canvas
- [ ] Verify chat edges connect to parent file nodes
- [ ] Check chat node colors (`#4a9eff`)
- [ ] Check chat node opacity (decay_factor)
- [ ] Verify chatTreeStore is populated
- [ ] Test clicking on chat node opens ChatPanel
- [ ] Verify layout engine handles chat nodes correctly
- [ ] Check console logs for processing info

---

## Future Enhancements

### Phase 108.3 - Chat Node Interactions

1. **Click handler for chat nodes:**
   - Open corresponding chat in `ChatPanel`
   - Highlight related file node

2. **Visual differentiation:**
   - Custom icon for chat nodes in `FileCard`
   - Animated glow for active chats

3. **Socket.IO sync:**
   - Real-time chat node updates
   - Live decay_factor animation

### Phase 108.4 - Artifact Nodes

1. Extend to support `artifact_nodes` from API
2. Render artifacts as children of chat nodes
3. Different colors/icons for artifact types

---

## Debugging

### Console Logs

```typescript
// In useTreeData.ts
console.log('[useTreeData] Processing chat nodes:', response.chat_nodes.length);
console.log('[useTreeData] Converted chat nodes:', chatTreeNodes.length);
console.log('[useTreeData] Chat edges:', chatEdges.length);
```

### Browser DevTools

```javascript
// Inspect useStore
window.store = useStore.getState();
console.log(store.nodes);  // Should include chat nodes

// Inspect chatTreeStore
window.chatStore = useChatTreeStore.getState();
console.log(chatStore.chatNodes);
```

---

## Related Files

**Frontend:**
- `/client/src/hooks/useTreeData.ts` - Main integration hook
- `/client/src/utils/api.ts` - API types and fetch
- `/client/src/utils/apiConverter.ts` - Type converters
- `/client/src/store/chatTreeStore.ts` - Chat node store
- `/client/src/types/treeNodes.ts` - ChatNode type definition

**Backend (reference):**
- `/src/api/routes/tree_routes.py` - API endpoint
- `/src/layout/knowledge_layout.py` - Chat node positioning
- `/src/chat/chat_history_manager.py` - Chat data source

---

## Markers

All changes marked with: `MARKER_108_CHAT_FRONTEND: Phase 108.2 - Chat nodes integration`

Use `grep -r "MARKER_108_CHAT_FRONTEND"` to find all related code.

---

## Summary

✅ **Completed:**
- API types for chat nodes
- Chat node converters
- useTreeData integration
- Dual storage (chatTreeStore + useStore)
- Backwards compatibility
- Console logging for debugging

🎯 **Next Steps:**
- Test with real API data
- Implement chat node click handlers
- Add visual differentiation in FileCard
- Socket.IO real-time updates
