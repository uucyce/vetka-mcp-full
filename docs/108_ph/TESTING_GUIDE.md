# Phase 108.2 - Testing Guide

Complete testing guide for chat node frontend integration.

---

## Pre-Testing Setup

### 1. Ensure Backend is Running

```bash
# Start VETKA backend
cd ~/Documents/VETKA_Project/vetka_live_03
python src/main.py
```

### 2. Verify Backend API Returns Chat Nodes

```bash
# Test API endpoint
curl http://localhost:8000/api/tree/data | jq '.' | grep -A5 chat_nodes

# Expected output:
# "chat_nodes": [
#   {
#     "id": "chat_abc123",
#     "type": "chat",
#     ...
```

### 3. Start Frontend Dev Server

```bash
cd client
npm run dev
```

---

## Unit Tests

### Test 1: API Types

**File:** `client/src/utils/api.ts`

**Test:**
```typescript
import { ChatNodeAPI, ChatEdgeAPI } from './api';

const testChatNode: ChatNodeAPI = {
  id: "chat_test",
  type: "chat",
  name: "Test Chat",
  parent_id: "src/main.py",
  metadata: {
    chat_id: "test",
    file_path: "src/main.py",
    last_activity: "2026-02-02T12:00:00Z",
    message_count: 0,
    participants: [],
    decay_factor: 1.0,
    context_type: "file_context"
  },
  visual_hints: {
    layout_hint: { expected_x: 0, expected_y: 0, expected_z: 0 },
    color: "#4a9eff",
    opacity: 1.0
  }
};

// ✓ Should compile without errors
```

**Expected:** No TypeScript compilation errors.

---

### Test 2: convertChatNode()

**File:** `client/src/utils/apiConverter.ts`

**Test:**
```typescript
import { convertChatNode } from './apiConverter';

const apiChatNode: ChatNodeAPI = {
  id: "chat_test123",
  type: "chat",
  name: "Test Chat",
  parent_id: "src/main.py",
  metadata: {
    chat_id: "test123",
    file_path: "src/main.py",
    last_activity: "2026-02-02T12:00:00Z",
    message_count: 5,
    participants: ["@architect", "@qa"],
    decay_factor: 0.95,
    context_type: "file_context"
  },
  visual_hints: {
    layout_hint: { expected_x: 0, expected_y: 0, expected_z: 0 },
    color: "#4a9eff",
    opacity: 0.95
  }
};

const result = convertChatNode(apiChatNode);

console.assert(result.id === "chat_test123", "ID mismatch");
console.assert(result.type === "chat", "Type mismatch");
console.assert(result.participants.length === 2, "Participants mismatch");
console.assert(result.messageCount === 5, "Message count mismatch");
console.assert(result.decay_factor === 0.95, "Decay factor mismatch");
```

**Expected:**
- ✅ All assertions pass
- ✅ ChatNode object created correctly

---

### Test 3: chatNodeToTreeNode()

**File:** `client/src/utils/apiConverter.ts`

**Test:**
```typescript
import { chatNodeToTreeNode } from './apiConverter';
import { ChatNode } from '../types/treeNodes';

const chatNode: ChatNode = {
  id: "chat_test123",
  type: "chat",
  parentId: "src/main.py",
  name: "Test Chat",
  participants: ["@architect"],
  messageCount: 5,
  lastActivity: new Date(),
  artifacts: [],
  status: "active",
  decay_factor: 0.9
};

const position = { x: 10, y: 5, z: 0 };
const result = chatNodeToTreeNode(chatNode, position);

console.assert(result.id === "chat_test123", "ID mismatch");
console.assert(result.type === "file", "Type should be 'file' for 3D rendering");
console.assert(result.color === "#4a9eff", "Color should be blue");
console.assert(result.opacity === 0.9, "Opacity mismatch");
console.assert(result.position.x === 10, "Position X mismatch");
console.assert(result.backendType === "leaf", "Backend type should be leaf");
```

**Expected:**
- ✅ All assertions pass
- ✅ TreeNode created with correct properties

---

### Test 4: convertChatEdge()

**File:** `client/src/utils/apiConverter.ts`

**Test:**
```typescript
import { convertChatEdge } from './apiConverter';

const apiChatEdge: ChatEdgeAPI = {
  from: "src/main.py",
  to: "chat_test123",
  semantics: "chat",
  metadata: { type: "chat", color: "#4a9eff", opacity: 0.8 }
};

const result = convertChatEdge(apiChatEdge, 0);

console.assert(result.id === "chat_edge_0", "ID mismatch");
console.assert(result.source === "src/main.py", "Source mismatch");
console.assert(result.target === "chat_test123", "Target mismatch");
console.assert(result.type === "chat", "Type should be 'chat'");
```

**Expected:**
- ✅ All assertions pass
- ✅ TreeEdge created correctly

---

## Integration Tests

### Test 5: useTreeData Hook - With Chat Nodes

**Setup:**
1. Ensure backend returns `chat_nodes` array in API response
2. Open browser at `http://localhost:3000`

**Test Steps:**
1. Open browser DevTools Console
2. Run:
```javascript
window.store = useStore.getState();
console.log('Total nodes:', Object.keys(store.nodes).length);
console.log('Chat nodes:', Object.keys(store.nodes).filter(k => k.startsWith('chat_')));
```

**Expected:**
```
Total nodes: 25
Chat nodes: ['chat_abc123', 'chat_def456']
```

**Verification:**
- ✅ Chat nodes present in store
- ✅ Chat node IDs start with 'chat_'

---

### Test 6: useTreeData Hook - Without Chat Nodes (Backwards Compatibility)

**Setup:**
1. Modify backend to NOT return `chat_nodes` in API response
2. Reload browser

**Test Steps:**
1. Check browser console for errors
2. Verify tree still renders
3. Run:
```javascript
window.store = useStore.getState();
console.log('Chat nodes:', Object.keys(store.nodes).filter(k => k.startsWith('chat_')));
```

**Expected:**
```
Chat nodes: []
```

**Verification:**
- ✅ No console errors
- ✅ File tree renders normally
- ✅ No chat nodes in store
- ✅ Backwards compatible

---

### Test 7: chatTreeStore Population

**Setup:**
1. Ensure backend returns chat_nodes
2. Open browser at `http://localhost:3000`

**Test Steps:**
1. Open browser DevTools Console
2. Run:
```javascript
window.chatStore = useChatTreeStore.getState();
console.log('Chat nodes in chatTreeStore:', Object.keys(chatStore.chatNodes).length);
console.log('First chat:', Object.values(chatStore.chatNodes)[0]);
```

**Expected:**
```
Chat nodes in chatTreeStore: 2
First chat: {
  id: "chat_abc123",
  type: "chat",
  name: "Chat: main.py discussion",
  participants: ["@architect", "@qa"],
  messageCount: 15,
  ...
}
```

**Verification:**
- ✅ chatTreeStore contains ChatNode objects
- ✅ Participants array present
- ✅ Message count correct

---

### Test 8: Edge Integration

**Setup:**
1. Ensure backend returns `chat_edges`
2. Open browser

**Test Steps:**
1. Run in console:
```javascript
window.store = useStore.getState();
console.log('Total edges:', store.edges.length);
console.log('Chat edges:', store.edges.filter(e => e.type === 'chat'));
```

**Expected:**
```
Total edges: 30
Chat edges: [
  { id: 'chat_edge_0', source: 'src/main.py', target: 'chat_abc123', type: 'chat' },
  { id: 'chat_edge_1', source: 'src/config.py', target: 'chat_def456', type: 'chat' }
]
```

**Verification:**
- ✅ Chat edges present
- ✅ Edge type is 'chat'
- ✅ Source and target IDs correct

---

## Visual Tests

### Test 9: Chat Nodes Render in 3D Canvas

**Test Steps:**
1. Open browser at `http://localhost:3000`
2. Visually inspect 3D canvas
3. Look for blue nodes (chat nodes)

**Expected:**
- ✅ Chat nodes visible in 3D space
- ✅ Blue color (#4a9eff)
- ✅ Connected to parent file nodes with edges

**Manual Verification:**
- Rotate 3D view
- Check chat nodes are positioned correctly
- Verify edges connect file → chat

---

### Test 10: Chat Node Properties

**Test Steps:**
1. Run in console:
```javascript
window.store = useStore.getState();
const chatNode = Object.values(store.nodes).find(n => n.id.startsWith('chat_'));
console.log('Chat node:', chatNode);
```

**Expected:**
```javascript
{
  id: "chat_abc123",
  path: "chat_abc123",
  name: "Chat: main.py discussion",
  type: "file",
  backendType: "leaf",
  parentId: "src/main.py",
  position: { x: 10, y: 5, z: 0 },
  color: "#4a9eff",
  opacity: 0.95
}
```

**Verification:**
- ✅ Color is blue (#4a9eff)
- ✅ Type is 'file' (for rendering)
- ✅ Opacity reflects decay_factor
- ✅ Position has valid coordinates

---

## Console Log Tests

### Test 11: Processing Logs

**Setup:**
1. Clear browser console
2. Reload page

**Expected Console Output:**
```
[useTreeData] Processing chat nodes: 2
[useTreeData] Converted chat nodes: 2
[useTreeData] Chat edges: 2
```

**Verification:**
- ✅ Logs appear in correct order
- ✅ Counts match actual data
- ✅ No error logs

---

## Error Handling Tests

### Test 12: Malformed Chat Node

**Setup:**
1. Modify backend to return malformed chat_node (missing field)
2. Reload browser

**Expected:**
- ⚠️ Error caught and logged
- ⚠️ App doesn't crash
- ⚠️ Other nodes still render

**Verification:**
- Check console for error messages
- Verify file tree still works

---

### Test 13: Empty chat_nodes Array

**Setup:**
1. Backend returns `chat_nodes: []`
2. Reload browser

**Expected:**
- ✅ No console errors
- ✅ Processing logs show: "Processing chat nodes: 0"
- ✅ File tree renders normally

---

## Performance Tests

### Test 14: Large Number of Chat Nodes

**Setup:**
1. Backend returns 50+ chat nodes
2. Reload browser

**Expected:**
- ✅ Page loads without significant delay
- ✅ All nodes render
- ✅ No memory leaks (check DevTools Performance)

**Verification:**
```javascript
console.log('Nodes:', Object.keys(useStore.getState().nodes).length);
console.log('Chat nodes:', Object.keys(useStore.getState().nodes).filter(k => k.startsWith('chat_')).length);
```

---

## Test Summary Checklist

### Unit Tests
- [ ] API types compile correctly
- [ ] convertChatNode() produces valid ChatNode
- [ ] chatNodeToTreeNode() produces valid TreeNode
- [ ] convertChatEdge() produces valid TreeEdge

### Integration Tests
- [ ] useTreeData processes chat_nodes correctly
- [ ] chatTreeStore is populated
- [ ] useStore contains merged nodes
- [ ] Edges include chat edges
- [ ] Backwards compatibility (no chat_nodes)

### Visual Tests
- [ ] Chat nodes render in 3D
- [ ] Blue color applied
- [ ] Edges connect correctly
- [ ] Opacity reflects decay_factor

### Console Tests
- [ ] Processing logs appear
- [ ] Counts are accurate
- [ ] No unexpected errors

### Error Handling
- [ ] Malformed data handled gracefully
- [ ] Empty arrays handled
- [ ] App doesn't crash on errors

### Performance
- [ ] Large datasets load smoothly
- [ ] No memory leaks
- [ ] Rendering is smooth

---

## Debugging Commands

### Quick Inspection

```javascript
// Check all stores
window.store = useStore.getState();
window.chatStore = useChatTreeStore.getState();

// Count nodes
console.log('Total nodes:', Object.keys(store.nodes).length);
console.log('File nodes:', Object.values(store.nodes).filter(n => n.type === 'file' && !n.id.startsWith('chat_')).length);
console.log('Chat nodes:', Object.values(store.nodes).filter(n => n.id.startsWith('chat_')).length);

// Inspect chat nodes
console.log('Chat nodes in useStore:', Object.values(store.nodes).filter(n => n.id.startsWith('chat_')));
console.log('Chat nodes in chatTreeStore:', chatStore.chatNodes);

// Check edges
console.log('Total edges:', store.edges.length);
console.log('Chat edges:', store.edges.filter(e => e.type === 'chat'));

// Check positions
const chatNodes = Object.values(store.nodes).filter(n => n.id.startsWith('chat_'));
console.log('Chat node positions:', chatNodes.map(n => ({ id: n.id, pos: n.position })));
```

---

## Test Automation Script

Create a test file: `client/src/__tests__/chatNodeIntegration.test.ts`

```typescript
import { describe, it, expect } from 'vitest';
import { convertChatNode, convertChatEdge, chatNodeToTreeNode } from '../utils/apiConverter';
import type { ChatNodeAPI, ChatEdgeAPI } from '../utils/api';

describe('Chat Node Integration', () => {
  const mockChatNodeAPI: ChatNodeAPI = {
    id: "chat_test",
    type: "chat",
    name: "Test Chat",
    parent_id: "src/main.py",
    metadata: {
      chat_id: "test",
      file_path: "src/main.py",
      last_activity: "2026-02-02T12:00:00Z",
      message_count: 5,
      participants: ["@architect"],
      decay_factor: 0.95,
      context_type: "file_context"
    },
    visual_hints: {
      layout_hint: { expected_x: 10, expected_y: 5, expected_z: 0 },
      color: "#4a9eff",
      opacity: 0.95
    }
  };

  it('should convert ChatNodeAPI to ChatNode', () => {
    const result = convertChatNode(mockChatNodeAPI);

    expect(result.id).toBe("chat_test");
    expect(result.type).toBe("chat");
    expect(result.participants).toEqual(["@architect"]);
    expect(result.messageCount).toBe(5);
    expect(result.decay_factor).toBe(0.95);
  });

  it('should convert ChatNode to TreeNode', () => {
    const chatNode = convertChatNode(mockChatNodeAPI);
    const position = { x: 10, y: 5, z: 0 };
    const result = chatNodeToTreeNode(chatNode, position);

    expect(result.id).toBe("chat_test");
    expect(result.type).toBe("file");
    expect(result.color).toBe("#4a9eff");
    expect(result.opacity).toBe(0.95);
    expect(result.position).toEqual(position);
  });

  it('should convert ChatEdgeAPI to TreeEdge', () => {
    const mockEdge: ChatEdgeAPI = {
      from: "src/main.py",
      to: "chat_test",
      semantics: "chat",
      metadata: { type: "chat", color: "#4a9eff", opacity: 0.8 }
    };

    const result = convertChatEdge(mockEdge, 0);

    expect(result.id).toBe("chat_edge_0");
    expect(result.source).toBe("src/main.py");
    expect(result.target).toBe("chat_test");
    expect(result.type).toBe("chat");
  });
});
```

**Run tests:**
```bash
cd client
npm run test
```

---

## Final Checklist

Before marking Phase 108.2 as complete:

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Visual verification complete
- [ ] Console logs are correct
- [ ] No TypeScript errors
- [ ] No console errors in browser
- [ ] Backwards compatibility confirmed
- [ ] Documentation reviewed
- [ ] Code markers in place
- [ ] Ready for Phase 108.3

---

## Next Phase Preparation

### Phase 108.3 Tasks
1. Implement chat node click handler in FileCard.tsx
2. Add visual differentiation (icons, styling)
3. Implement Socket.IO real-time updates
4. Add artifact nodes support

### Test Files to Create for Phase 108.3
- `chatNodeInteraction.test.ts`
- `chatNodeStyling.test.ts`
- `socketIOChatSync.test.ts`
