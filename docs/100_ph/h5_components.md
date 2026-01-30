# H5: React Components Report - VETKA Phase 100 Tauri Migration

## Summary

**32 TSX Components** organized in 9 feature modules.

## Component Tree

```
src/components/
├── App.tsx (33KB - main entry)
├── ModelDirectory.tsx (sidebar)
├── WorkflowMonitor.tsx
│
├── artifact/ (file viewer)
│   ├── ArtifactPanel.tsx [FEATURE]
│   ├── ArtifactWindow.tsx
│   ├── FloatingWindow.tsx
│   ├── Toolbar.tsx
│   └── viewers/
│       ├── CodeViewer.tsx (lazy)
│       ├── ImageViewer.tsx (lazy)
│       └── MarkdownViewer.tsx
│
├── canvas/ (3D visualization)
│   ├── FileCard.tsx [LAYOUT] (24KB, 10 LOD levels)
│   ├── CameraController.tsx
│   ├── Edge.tsx
│   ├── TreeEdges.tsx
│   └── Scene.tsx
│
├── chat/ (messaging)
│   ├── ChatPanel.tsx [LAYOUT] (80KB, main interface)
│   ├── MessageList.tsx
│   ├── MessageBubble.tsx
│   ├── MessageInput.tsx (23KB)
│   ├── MentionPopup.tsx
│   ├── ChatSidebar.tsx
│   ├── GroupCreatorPanel.tsx (28KB)
│   ├── CompoundMessage.tsx
│   └── WorkflowProgress.tsx
│
├── ui/ (primitives)
│   ├── Panel.tsx [UI]
│   ├── FilePreview.tsx
│   └── viewers/CodeViewer.tsx
│
├── voice/ (audio)
│   ├── SmartVoiceInput.tsx [FEATURE]
│   ├── VoiceButton.tsx
│   ├── VoiceWave.tsx
│   └── useTTS.ts
│
├── search/
│   └── UnifiedSearchBar.tsx [FEATURE] (42KB)
│
├── scanner/
│   └── ScanPanel.tsx [FEATURE] (25KB)
│
└── panels/
    └── RoleEditor.tsx
```

## Components by Type

### [COMP_LAYOUT] - Main Layout (3)
| Component | Size | Purpose |
|-----------|------|---------|
| ChatPanel | 80KB | Main chat, tabs, history |
| FileCard | 24KB | 3D nodes, LOD, drag |
| App | 33KB | Root, canvas + chat |

### [COMP_UI] - Reusable UI (3)
| Component | Purpose |
|-----------|---------|
| Panel | Collapsible sidebar |
| FloatingWindow | Draggable window |
| Toolbar | Action buttons |

### [COMP_FEATURE] - Feature Modules (6)
| Component | Size | Purpose |
|-----------|------|---------|
| ArtifactPanel | - | Code/MD/Image viewer |
| UnifiedSearchBar | 42KB | Semantic search |
| MessageInput | 23KB | Voice, mention, files |
| SmartVoiceInput | 11KB | VAD, streaming |
| ScanPanel | 25KB | File browser |
| GroupCreatorPanel | 28KB | Multi-agent groups |

## Tauri Integration Points

### 1. File System Access
- **Components:** ScanPanel, ArtifactPanel, FileCard
- **Current:** Browser FileSystemHandle API
- **Tauri:** `@tauri-apps/plugin-fs`

### 2. Window Management
- **Components:** ArtifactWindow, FloatingWindow, ChatPanel
- **Current:** Fixed viewport
- **Tauri:** Separate Tauri windows

### 3. Native Dialogs
- **Components:** ScanPanel (folder), ArtifactPanel (open in Finder)
- **Current:** HTML drag-drop
- **Tauri:** `@tauri-apps/plugin-dialog`

### 4. Clipboard
- **Components:** UnifiedSearchBar, MessageInput, ArtifactPanel
- **Current:** `navigator.clipboard`
- **Tauri:** `@tauri-apps/plugin-clipboard-manager`

### 5. Keyboard Shortcuts
- **Component:** App (G-key grab, Ctrl+Z undo)
- **Tauri:** `@tauri-apps/plugin-hotkey`

## Key Hooks

| Hook | Purpose |
|------|---------|
| useStore() | Global state (zustand) |
| useSocket() | Socket.IO messaging |
| useTreeData() | 3D tree sync |
| useTTS() | Voice output |
| useDrag3D() | Node dragging |

## Dependencies

```json
{
  "react": "^19",
  "@react-three/fiber": "^9",
  "@react-three/drei": "^10",
  "three": "^0.170",
  "zustand": "^4.5",
  "socket.io-client": "*",
  "lucide-react": "^0.562"
}
```

## Markers

[COMP_LAYOUT] ChatPanel, FileCard, App
[COMP_UI] Panel, FloatingWindow, Toolbar
[COMP_FEATURE] ArtifactPanel, Search, Voice, Scanner
[NATIVE_BRIDGE] ScanPanel, ArtifactPanel (file access)
[WINDOW_MANAGEMENT] ArtifactWindow, ChatPanel

## Complexity Map

- **Highest (>20KB):** ChatPanel, UnifiedSearchBar, FileCard, MessageInput, GroupCreatorPanel
- **Medium (10-20KB):** ScanPanel, ChatSidebar, SmartVoiceInput
- **Lower (<10KB):** All other components

## Tauri Migration Checklist

- [ ] Split ChatPanel/ArtifactWindow into Tauri windows
- [ ] Migrate ScanPanel to `@tauri-apps/plugin-fs`
- [ ] Replace drag-drop with native dialogs
- [ ] Use Tauri clipboard for rich content
- [ ] Register global hotkeys
- [ ] Add native app menu
- [ ] Create proper app icon

---
Generated: 2026-01-29 | Agent: H5 Haiku | Phase 100
