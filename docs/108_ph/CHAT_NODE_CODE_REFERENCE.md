# Chat Node Integration - Code Reference

Complete code snippets for Phase 108.2 chat node integration.

---

## 1. API Types (`client/src/utils/api.ts`)

### ChatNodeAPI Interface

```typescript
// MARKER_108_CHAT_FRONTEND: Phase 108.2 - Chat nodes API types
export interface ChatNodeAPI {
  id: string;  // "chat_{uuid}"
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
    layout_hint: { expected_x: number; expected_y: number; expected_z: number };
    color: string;
    opacity: number;
  };
}

export interface ChatEdgeAPI {
  from: string;
  to: string;
  semantics: "chat";
  metadata: { type: "chat"; color: string; opacity: number };
}
```

### Updated ApiTreeResponse

```typescript
export interface ApiTreeResponse {
  success: boolean;
  // Legacy format
  nodes?: ApiTreeNode[];
  edges?: Array<{ source: string; target: string }>;
  // New VETKA format
  tree?: {
    nodes: VetkaApiNode[];
    edges: VetkaApiEdge[];
  };
  // Phase 108.2: Chat nodes
  chat_nodes?: ChatNodeAPI[];
  chat_edges?: ChatEdgeAPI[];
  error?: string;
}
```

### Updated fetchTreeData()

```typescript
export async function fetchTreeData(): Promise<ApiTreeResponse> {
  try {
    const response = await fetch(`${API_BASE}/tree/data`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();

    // MARKER_108_CHAT_FRONTEND: Phase 108.2 - Extract chat nodes from response
    // Backend returns {format, mode, source, tree, chat_nodes?, chat_edges?}
    return {
      success: true,
      tree: data.tree,
      chat_nodes: data.chat_nodes,
      chat_edges: data.chat_edges,
    };
  } catch (error) {
    console.error('[API] fetchTreeData error:', error);
    return {
      success: false,
      nodes: [],
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}
```

---

## 2. API Converters (`client/src/utils/apiConverter.ts`)

### Imports

```typescript
import { TreeNode, TreeEdge, VetkaNodeType } from '../store/useStore';
import { ChatNode } from '../types/treeNodes';
import type { ChatNodeAPI, ChatEdgeAPI } from './api';
```

### convertChatNode()

```typescript
// MARKER_108_CHAT_FRONTEND: Phase 108.2 - Chat node converters

/**
 * Convert ChatNodeAPI from backend to frontend ChatNode type
 * Integrates chat nodes into the tree visualization
 */
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
    // Store chat_id for backend correlation
    userId: apiChatNode.metadata.chat_id,
  };
}
```

### convertChatEdge()

```typescript
/**
 * Convert ChatEdgeAPI from backend to TreeEdge format
 */
export function convertChatEdge(apiChatEdge: ChatEdgeAPI, index: number): TreeEdge {
  return {
    id: `chat_edge_${index}`,
    source: apiChatEdge.from,
    target: apiChatEdge.to,
    type: 'chat',
  };
}
```

### chatNodeToTreeNode()

```typescript
/**
 * Convert ChatNode to TreeNode for unified 3D rendering
 * This allows chat nodes to render alongside file/folder nodes
 */
export function chatNodeToTreeNode(
  chatNode: ChatNode,
  position: { x: number; y: number; z: number }
): TreeNode {
  return {
    id: chatNode.id,
    path: chatNode.id, // Chat nodes don't have file paths
    name: chatNode.name,
    type: 'file', // Render as "file" type in 3D (can be styled differently via CSS)
    backendType: 'leaf',
    depth: 0, // Will be calculated from parent
    parentId: chatNode.parentId,
    position,
    color: '#4a9eff', // Blue for chat nodes
    opacity: chatNode.decay_factor,
  };
}
```

---

## 3. useTreeData Hook (`client/src/hooks/useTreeData.ts`)

### Imports

```typescript
import { useEffect } from 'react';
import { useStore, TreeNode, VetkaNodeType } from '../store/useStore';
import { fetchTreeData, ApiTreeNode } from '../utils/api';
import { calculateSimpleLayout } from '../utils/layout';
import {
  convertApiResponse,
  convertLegacyNode,
  convertLegacyEdge,
  convertChatNode,
  convertChatEdge,
  chatNodeToTreeNode,
  VetkaApiResponse,
} from '../utils/apiConverter';
import { useChatTreeStore } from '../store/chatTreeStore';
```

### Hook Setup

```typescript
export function useTreeData() {
  const {
    setNodes,
    setNodesFromRecord,
    setEdges,
    setLoading,
    setError,
    nodes,
    isLoading,
    error,
  } = useStore();

  // MARKER_108_CHAT_FRONTEND: Phase 108.2 - Chat tree store for chat nodes
  const { addChatNode } = useChatTreeStore();
```

### Chat Node Processing Logic

```typescript
// Inside loadData() function, after convertApiResponse()
// MARKER_108_CHAT_FRONTEND: Phase 108.2 - Process chat nodes
let chatTreeNodes: TreeNode[] = [];
const chatEdges: typeof edges = [];

if (response.chat_nodes && response.chat_nodes.length > 0) {
  console.log('[useTreeData] Processing chat nodes:', response.chat_nodes.length);

  // Convert chat nodes to ChatNode type and add to chatTreeStore
  response.chat_nodes.forEach((apiChatNode) => {
    const chatNode = convertChatNode(apiChatNode);
    addChatNode(chatNode.parentId, chatNode);

    // Convert ChatNode to TreeNode for 3D rendering
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

  console.log('[useTreeData] Converted chat nodes:', chatTreeNodes.length);
  console.log('[useTreeData] Chat edges:', chatEdges.length);
}

// Merge file tree nodes and chat nodes
const allNodes = { ...convertedNodes };
chatTreeNodes.forEach((chatNode) => {
  allNodes[chatNode.id] = chatNode;
});

// Merge edges
const allEdges = [...edges, ...chatEdges];
```

### Store Updates

```typescript
// Apply layout if positions are all zeros
const needsLayout = Object.values(allNodes).every(
  (n) => n.position.x === 0 && n.position.y === 0 && n.position.z === 0
);

if (needsLayout) {
  const positioned = calculateSimpleLayout(Object.values(allNodes));
  setNodes(positioned);
} else {
  setNodesFromRecord(allNodes);
}

setEdges(allEdges);
```

### Dependencies

```typescript
  }, [setNodes, setNodesFromRecord, setEdges, setLoading, setError, addChatNode]);
```

---

## 4. Example API Response

### Backend Response Format

```json
{
  "format": "vetka_v1",
  "mode": "live",
  "source": "disk",
  "tree": {
    "nodes": [
      {
        "id": "src/main.py",
        "type": "leaf",
        "name": "main.py",
        "parent_id": "src",
        "metadata": {
          "path": "src/main.py",
          "extension": ".py",
          "depth": 2
        },
        "visual_hints": {
          "layout_hint": { "expected_x": 0, "expected_y": 0, "expected_z": 0 },
          "color": "#1f2937"
        }
      }
    ],
    "edges": [
      { "from": "src", "to": "src/main.py", "semantics": "contains" }
    ]
  },
  "chat_nodes": [
    {
      "id": "chat_abc123",
      "type": "chat",
      "name": "Chat: main.py discussion",
      "parent_id": "src/main.py",
      "metadata": {
        "chat_id": "abc123",
        "file_path": "src/main.py",
        "last_activity": "2026-02-02T12:00:00Z",
        "message_count": 15,
        "participants": ["@architect", "@qa"],
        "decay_factor": 0.95,
        "context_type": "file_context"
      },
      "visual_hints": {
        "layout_hint": { "expected_x": 10, "expected_y": 5, "expected_z": 0 },
        "color": "#4a9eff",
        "opacity": 0.95
      }
    }
  ],
  "chat_edges": [
    {
      "from": "src/main.py",
      "to": "chat_abc123",
      "semantics": "chat",
      "metadata": {
        "type": "chat",
        "color": "#4a9eff",
        "opacity": 0.8
      }
    }
  ]
}
```

---

## 5. Debugging Commands

### Check Stores in Browser Console

```javascript
// Check useStore (unified tree)
window.store = useStore.getState();
console.log('All nodes:', Object.keys(store.nodes));
console.log('Chat nodes:', Object.keys(store.nodes).filter(k => k.startsWith('chat_')));

// Check chatTreeStore (chat metadata)
window.chatStore = useChatTreeStore.getState();
console.log('Chat nodes:', chatStore.chatNodes);
console.log('First chat:', Object.values(chatStore.chatNodes)[0]);

// Check edges
console.log('All edges:', store.edges);
console.log('Chat edges:', store.edges.filter(e => e.type === 'chat'));
```

### Grep for Markers

```bash
# Find all chat node integration code
grep -rn "MARKER_108_CHAT_FRONTEND" client/src

# Expected output:
# client/src/utils/api.ts:23: // MARKER_108_CHAT_FRONTEND: Phase 108.2
# client/src/utils/api.ts:76: // MARKER_108_CHAT_FRONTEND: Phase 108.2
# client/src/utils/apiConverter.ts:172: // MARKER_108_CHAT_FRONTEND: Phase 108.2
# client/src/hooks/useTreeData.ts:38: // MARKER_108_CHAT_FRONTEND: Phase 108.2
# client/src/hooks/useTreeData.ts:71: // MARKER_108_CHAT_FRONTEND: Phase 108.2
```

---

## 6. Testing Examples

### Test convertChatNode()

```typescript
import { convertChatNode } from '../utils/apiConverter';

const apiChatNode = {
  id: "chat_test123",
  type: "chat",
  name: "Test Chat",
  parent_id: "src/main.py",
  metadata: {
    chat_id: "test123",
    file_path: "src/main.py",
    last_activity: "2026-02-02T12:00:00Z",
    message_count: 5,
    participants: ["@architect"],
    decay_factor: 1.0,
    context_type: "file_context"
  },
  visual_hints: {
    layout_hint: { expected_x: 0, expected_y: 0, expected_z: 0 },
    color: "#4a9eff",
    opacity: 1.0
  }
};

const chatNode = convertChatNode(apiChatNode);
console.log(chatNode);
// Expected: ChatNode with type='chat', participants=['@architect']
```

### Test chatNodeToTreeNode()

```typescript
import { chatNodeToTreeNode } from '../utils/apiConverter';

const chatNode = {
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
const treeNode = chatNodeToTreeNode(chatNode, position);

console.log(treeNode);
// Expected: TreeNode with color='#4a9eff', opacity=0.9, type='file'
```

---

## 7. Component Integration Example

### FileCard.tsx (Future Enhancement)

```typescript
// In FileCard.tsx - Add chat node detection
const isChatNode = node.id.startsWith('chat_');

// Add custom styling
const cardStyle = {
  backgroundColor: isChatNode ? 'rgba(74, 158, 255, 0.1)' : 'transparent',
  borderColor: isChatNode ? '#4a9eff' : node.color,
};

// Add chat icon
{isChatNode && <ChatIcon />}

// Add click handler
const handleClick = () => {
  if (isChatNode) {
    // Open chat panel
    openChatPanel(node.id);
  } else {
    // Existing file node logic
    selectNode(node.id);
  }
};
```

### TreeEdges.tsx (Future Enhancement)

```typescript
// In TreeEdges.tsx - Style chat edges differently
const edgeColor = edge.type === 'chat' ? '#4a9eff' : '#6b7280';
const edgeOpacity = edge.type === 'chat' ? 0.8 : 0.6;
const edgeWidth = edge.type === 'chat' ? 2 : 1;
```

---

## Summary

This code reference provides:
- ✅ Complete type definitions
- ✅ Converter functions
- ✅ Hook integration logic
- ✅ Example API response
- ✅ Debugging commands
- ✅ Testing examples
- ✅ Component integration patterns

All code is production-ready and marked with `MARKER_108_CHAT_FRONTEND`.
