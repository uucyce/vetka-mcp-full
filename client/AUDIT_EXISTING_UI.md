# VETKA UI Audit Report
## Phase 27.7 - Existing Components Analysis

**Date:** 2026-01-02
**Auditor:** Claude Code
**Scope:** Chat Panel, Artifact Panel, Socket.IO Events, Agent Tools

---

## 1. EXISTING CHAT PANEL

### Location: `frontend/static/js/ui/chat_panel.js`

**Type:** Vanilla JavaScript (not React)

**Features:**
- 8-direction resize (4 corners + 4 edges)
- Dock/undock functionality
- localStorage persistence for position/size
- CSS-based styling

**Architecture:**
```javascript
const VETKAChatPanel = {
  // Resize system: N, S, E, W, NE, NW, SE, SW
  // Dock button toggles between docked/floating
  // State saved to localStorage
}
```

**Verdict:** Legacy Vanilla JS. Not compatible with React Three Fiber architecture. **REWRITE REQUIRED.**

---

## 2. EXISTING ARTIFACT PANEL

### Location: `app/artifact-panel/`

**Type:** Full React/TypeScript application (separate build)

**Structure:**
```
app/artifact-panel/
├── src/
│   ├── components/
│   │   ├── ArtifactPanel.tsx    # Main panel
│   │   ├── CodeViewer.tsx       # Monaco-based code editor
│   │   ├── ImageViewer.tsx      # Image display
│   │   ├── MarkdownViewer.tsx   # MD rendering
│   │   ├── PDFViewer.tsx        # PDF display
│   │   ├── AudioWaveform.tsx    # Audio visualization
│   │   ├── ThreeDViewer.tsx     # 3D model viewer
│   │   ├── MediaViewer.tsx      # Video/audio
│   │   └── RichTextEditor.tsx   # WYSIWYG editor
│   ├── hooks/
│   │   └── useIframeApi.ts      # Parent communication
│   └── App.tsx
├── package.json
└── vite.config.ts
```

**API Integration:**
- Uses iframe postMessage API for parent communication
- Fetches files via `/api/files/read` and `/api/files/save`
- Supports types: `code`, `richtext`, `markdown`, `image`, `media`, `audio`, `pdf`, `3d`

**Key Functions:**
```typescript
// ArtifactPanel.tsx
const handleOpen = (path: string) => {
  postToParent('FILE_OPENED', { path });
};

const handleSave = async () => {
  await fetch('/api/files/save', {
    method: 'POST',
    body: JSON.stringify({ path, content })
  });
};
```

**Verdict:** Well-structured React app but runs as separate iframe. **CAN REUSE VIEWERS**, need to adapt for R3F integration.

---

## 3. SOCKET.IO EVENTS

### Location: `frontend/static/js/socket_handler.js` + `main.py`

**Existing Events (server -> client):**

| Event | Payload | Description |
|-------|---------|-------------|
| `agent_message` | `{ agent, content, artifacts?, context?, source_files? }` | Main agent response |
| `file_highlighted` | `{ path }` | Agent focuses on file |
| `file_unhighlighted` | `{ path }` | Agent releases focus |
| `knowledge_refactored` | `{ ... }` | Tree structure changed |
| `branch_forked` | `{ ... }` | New branch created |
| `node_moved` | `{ id, position }` | Node position updated |
| `tree_updated` | `{ nodes, edges }` | Full tree refresh |
| `layout_changed` | `{ layout }` | Layout algorithm changed |
| `camera_control` | `{ action, target, zoom, highlight }` | Camera focus (Phase 22) |

**Existing Events (client -> server):**

| Event | Payload | Description |
|-------|---------|-------------|
| `user_message` | `{ path, payload, user }` | Chat message from user |
| `request_tree` | `{}` | Request tree data |
| `move_node` | `{ id, position }` | User moved a node |
| `select_node` | `{ id }` | User selected a node |

**Agent Message Format:**
```javascript
emit('agent_message', {
  agent: 'Dev',                    // PM, Dev, QA, Architect, Hostess
  content: 'Response text...',     // Main response
  artifacts: [{                    // Optional created files
    name: 'utils.py',
    content: '...',
    type: 'code',
    language: 'python'
  }],
  context: {                       // Optional context
    selected_file: 'src/main.py',
    conversation_id: '...'
  },
  source_files: ['file1.py']       // Files referenced
});
```

**Verdict:** Socket events are well-defined. **REUSE PROTOCOL**, just connect from R3F.

---

## 4. AGENT TOOLS INTEGRATION

### Location: `src/agents/tools.py` + `src/agents/agentic_tools.py`

**Available Tools by Agent:**

| Agent | Tools |
|-------|-------|
| PM | read_code_file, list_files, search_codebase, search_weaviate, search_semantic, get_tree_context, get_file_info, camera_focus |
| Dev | read_code_file, write_code_file, list_files, execute_code, search_codebase, search_semantic, get_tree_context, create_artifact, validate_syntax, get_file_info, camera_focus |
| QA | read_code_file, execute_code, run_tests, validate_syntax, search_codebase, search_semantic, get_tree_context, get_file_info, camera_focus |
| Architect | read_code_file, list_files, search_codebase, search_weaviate, search_semantic, get_tree_context, get_file_info, create_artifact, camera_focus |
| Hostess | search_weaviate, search_semantic, get_tree_context, list_files, get_file_info, camera_focus |

**Key Integration Points:**

1. **Camera Control (Phase 22):**
   ```python
   class CameraFocusTool(BaseTool):
       # Emits 'camera_control' via SocketIO
       mcp.socketio.emit('camera_control', {
           'action': 'focus',
           'target': target,  # file path or 'overview'
           'zoom': zoom,      # 'close', 'medium', 'far'
           'highlight': True
       })
   ```

2. **Artifact Creation:**
   ```python
   class CreateArtifactTool(BaseTool):
       # Creates artifact visible in UI
       # Artifact types: code, markdown, json, config, test
   ```

3. **Tree Context:**
   ```python
   class GetTreeContextTool(BaseTool):
       # Returns: parent, children, siblings, related files
   ```

**Verdict:** Rich tool ecosystem. **Camera control already implemented**. Need to handle `camera_control` event in R3F.

---

## 5. RECOMMENDATIONS

### 5.1 Chat Panel
**Decision: WRITE NEW in React**
- Legacy Vanilla JS not compatible with R3F
- Use existing Socket.IO protocol (`user_message` / `agent_message`)
- Keep same message format for backend compatibility

### 5.2 Artifact Panel
**Decision: ADAPT VIEWERS**
- Reuse existing viewer components (CodeViewer, MarkdownViewer, etc.)
- Remove iframe architecture
- Integrate directly into R3F scene or as HTML overlay

### 5.3 Socket.IO
**Decision: REUSE PROTOCOL**
- Already have `useSocket.ts` hook in client/
- Add missing events: `agent_message`, `camera_control`, `file_highlighted`
- Keep same payload format

### 5.4 Camera Control
**Decision: IMPLEMENT HANDLER**
- Agents can already emit `camera_control` events
- Need to handle in R3F:
  ```typescript
  socket.on('camera_control', ({ target, zoom, highlight }) => {
    // Animate camera to target node
    // Apply highlight effect
  });
  ```

---

## 6. MIGRATION PLAN

### Phase 27.7a: Chat Panel (React)
1. Create `client/src/components/ui/ChatPanel.tsx`
2. Use existing `useSocket` hook
3. Handle `agent_message` event
4. Emit `user_message` event
5. Support @mention parsing (use existing `parse_mentions` from agentic_tools.py)

### Phase 27.7b: Artifact Panel (React)
1. Copy viewers from `app/artifact-panel/src/components/`
2. Create `client/src/components/ui/ArtifactPanel.tsx`
3. Remove iframe logic, use direct props
4. Connect to store for selected file

### Phase 27.7c: Camera Control
1. Add `camera_control` handler to `useSocket.ts`
2. Store target in Zustand
3. Animate camera in `App.tsx` using useFrame

### Phase 27.7d: File Highlight
1. Handle `file_highlighted` / `file_unhighlighted` events
2. Add `highlightedId` to store
3. Apply glow effect in `FileCard.tsx`

---

## 7. FILES TO REUSE

| Source | Destination | Action |
|--------|-------------|--------|
| `app/artifact-panel/src/components/CodeViewer.tsx` | `client/src/components/ui/viewers/` | Copy & adapt |
| `app/artifact-panel/src/components/MarkdownViewer.tsx` | `client/src/components/ui/viewers/` | Copy & adapt |
| `app/artifact-panel/src/components/ImageViewer.tsx` | `client/src/components/ui/viewers/` | Copy & adapt |
| `frontend/static/js/socket_handler.js` | (reference only) | Use protocol |
| `src/agents/agentic_tools.py:parse_mentions` | `client/src/utils/mentions.ts` | Port to TS |

---

## 8. CONCLUSION

The existing codebase has:
- **Good:** Well-defined Socket.IO protocol, rich artifact viewers, camera control already in agents
- **Bad:** Legacy Vanilla JS chat, iframe-based artifact panel, no R3F integration

**Recommended approach:**
1. Write new Chat Panel in React
2. Adapt existing artifact viewers (remove iframe, keep functionality)
3. Reuse Socket.IO protocol exactly
4. Add camera control handler to R3F

**Estimated effort:**
- Chat Panel: New component with existing protocol
- Artifact Panel: Port viewers, remove iframe wrapper
- Socket events: Add 3-4 event handlers to existing hook
- Camera control: Animate OrbitControls target
