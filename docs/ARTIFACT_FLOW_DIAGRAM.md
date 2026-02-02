# Artifact Scanner Flow Diagram

**Phase 108.3 - MARKER_108_3_ARTIFACT_SCAN**

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     VETKA 3D Tree System                         │
│                     Phase 108.3                                  │
└─────────────────────────────────────────────────────────────────┘

                              │
                              ▼

┌─────────────────────────────────────────────────────────────────┐
│  Frontend: GET /api/tree/data                                    │
└─────────────────────────────────────────────────────────────────┘

                              │
                              ▼

┌─────────────────────────────────────────────────────────────────┐
│  tree_routes.py: get_tree_data()                                │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  STEP 1: Scan File Tree (existing)                   │      │
│  │  → Qdrant query for scanned_file nodes              │      │
│  │  → Build folder hierarchy                            │      │
│  │  → FAN layout calculation                            │      │
│  └──────────────────────────────────────────────────────┘      │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  STEP 4.5: Build Chat Nodes (Phase 108.2)           │      │
│  │  → ChatHistoryManager.get_all_chats()               │      │
│  │  → Position relative to files                        │      │
│  │  → Create chat_nodes, chat_edges                     │      │
│  └──────────────────────────────────────────────────────┘      │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  STEP 4.7: Build Artifact Nodes (Phase 108.3) ✨    │      │
│  │                                                       │      │
│  │  ┌─────────────────────────────────────────┐        │      │
│  │  │ artifact_scanner.scan_artifacts()       │        │      │
│  │  │  ↓                                       │        │      │
│  │  │  1. Read data/artifacts/ directory      │        │      │
│  │  │  2. Load staging.json metadata          │        │      │
│  │  │  3. Determine type/language from ext    │        │      │
│  │  │  4. Generate stable artifact IDs        │        │      │
│  │  │  5. Link to source chat via parent_id   │        │      │
│  │  │  6. Return artifact_nodes[]             │        │      │
│  │  └─────────────────────────────────────────┘        │      │
│  │                       │                              │      │
│  │                       ▼                              │      │
│  │  ┌─────────────────────────────────────────┐        │      │
│  │  │ artifact_scanner.update_artifact_positions() │   │      │
│  │  │  ↓                                       │        │      │
│  │  │  1. Map chat_id → chat_node             │        │      │
│  │  │  2. For each artifact with parent:      │        │      │
│  │  │     - Get parent chat position          │        │      │
│  │  │     - Calculate offset (cluster)        │        │      │
│  │  │     - Update artifact position          │        │      │
│  │  │  3. For orphaned artifacts:             │        │      │
│  │  │     - Place in artifact cluster area    │        │      │
│  │  └─────────────────────────────────────────┘        │      │
│  │                       │                              │      │
│  │                       ▼                              │      │
│  │  ┌─────────────────────────────────────────┐        │      │
│  │  │ artifact_scanner.build_artifact_edges() │        │      │
│  │  │  ↓                                       │        │      │
│  │  │  1. For each artifact with parent_id:   │        │      │
│  │  │     - Create edge: chat → artifact      │        │      │
│  │  │     - Set semantics: "artifact"         │        │      │
│  │  │     - Set color from artifact type      │        │      │
│  │  │  2. Return artifact_edges[]             │        │      │
│  │  └─────────────────────────────────────────┘        │      │
│  └──────────────────────────────────────────────────────┘      │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  STEP 5: Build Response                              │      │
│  │  {                                                    │      │
│  │    tree: {nodes, edges},                             │      │
│  │    chat_nodes: [...],                                │      │
│  │    chat_edges: [...],                                │      │
│  │    artifact_nodes: [...],  ← NEW                     │      │
│  │    artifact_edges: [...]   ← NEW                     │      │
│  │  }                                                    │      │
│  └──────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘

                              │
                              ▼

┌─────────────────────────────────────────────────────────────────┐
│  Frontend: useTreeData.ts                                        │
│  → Parse artifact_nodes                                          │
│  → Parse artifact_edges                                          │
│  → Merge with tree nodes/edges                                   │
└─────────────────────────────────────────────────────────────────┘

                              │
                              ▼

┌─────────────────────────────────────────────────────────────────┐
│  Frontend: FileCard.tsx                                          │
│  → Render artifact nodes with type badges                       │
│  → Color by artifact type                                        │
│  → Show status indicator (done/streaming/error)                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Detail

```
data/artifacts/
  ├── config.py          ─┐
  ├── report.md          ─┤
  ├── data.json          ─┤
  └── chart.png          ─┤
                          │
                          ▼
┌─────────────────────────────────────┐
│  scan_artifacts()                   │
│  1. List all files                  │
│  2. Load staging.json               │
│  3. For each file:                  │
│     - Get stat (size, timestamps)   │
│     - Determine type from ext       │
│     - Link to chat (if in staging)  │
│     - Generate artifact ID          │
│     - Calculate initial position    │
│     - Set color by type             │
└─────────────────────────────────────┘
                          │
                          ▼
                  artifact_nodes[]
                    (in memory)
                          │
                          ▼
┌─────────────────────────────────────┐
│  update_artifact_positions()        │
│  1. Get chat_nodes with positions   │
│  2. For artifacts with parent:      │
│     - Find parent chat position     │
│     - Offset: +3-7 x, -2-6 y        │
│  3. For orphaned artifacts:         │
│     - Place at x=100+, y=-50-       │
└─────────────────────────────────────┘
                          │
                          ▼
                artifact_nodes[]
              (positions updated)
                          │
                          ▼
┌─────────────────────────────────────┐
│  build_artifact_edges()             │
│  1. For each artifact:              │
│     - If parent_id exists:          │
│       • Create edge                 │
│       • from: parent_id (chat)      │
│       • to: artifact_id             │
│       • semantics: "artifact"       │
│       • color: artifact type color  │
└─────────────────────────────────────┘
                          │
                          ▼
                  artifact_edges[]
                          │
                          ▼
                  API Response
```

## Artifact Node Data Structure

```
artifact_node
├── id: "artifact_c9e6f153"
├── type: "artifact"
├── name: "config.py"
├── parent_id: "chat_abc123" (or null)
├── metadata
│   ├── file_path: "data/artifacts/config.py"
│   ├── artifact_type: "code"
│   ├── language: "python"
│   ├── size_bytes: 1234
│   ├── created_at: "2026-02-02T10:30:00Z"
│   ├── modified_at: "2026-02-02T10:35:00Z"
│   ├── source_message_id: "msg_xxx"
│   ├── source_chat_id: "chat_abc123"
│   ├── status: "done"
│   └── extension: ".py"
└── visual_hints
    ├── layout_hint
    │   ├── expected_x: 120
    │   ├── expected_y: 300
    │   └── expected_z: 0
    ├── color: "#10b981" (type-based)
    └── opacity: 1.0
```

## Position Calculation Strategy

```
Parent Chat Position: (50, 30, 0)

Artifacts (index 0-8):

Index 0: (53, 28, 0)  ←─┐
Index 1: (55, 28, 0)  ←─┼─ Row 1 (3 artifacts)
Index 2: (57, 28, 0)  ←─┘

Index 3: (53, 26, 0)  ←─┐
Index 4: (55, 26, 0)  ←─┼─ Row 2 (3 artifacts)
Index 5: (57, 26, 0)  ←─┘

Index 6: (53, 24, 0)  ←─┐
Index 7: (55, 24, 0)  ←─┼─ Row 3 (3 artifacts)
Index 8: (57, 24, 0)  ←─┘

Formula:
  x = parent_x + 3 + (index % 3) * 2
  y = parent_y - 2 - (index // 3) * 2
  z = parent_z
```

## Type Detection Flow

```
File: "config.py"
  ↓
Extension: ".py"
  ↓
ARTIFACT_TYPES lookup
  ↓
Result: ('code', 'python')
  ↓
Color: ARTIFACT_COLORS['code'] = '#10b981'
```

## Staging.json Link Flow

```
staging.json:
{
  "artifacts": {
    "art_1": {
      "filename": "config.py",
      "source_chat_id": "chat_abc123",
      "source_message_id": "msg_456"
    }
  }
}
  ↓
_load_staging_links()
  ↓
staging_links = {
  "config.py": {
    "source_chat_id": "chat_abc123",
    "source_message_id": "msg_456"
  }
}
  ↓
scan_artifacts() - for config.py:
  parent_id = "chat_abc123"
  metadata.source_message_id = "msg_456"
```

## Edge Creation Flow

```
artifact_node:
  id: "artifact_c9e6f153"
  parent_id: "chat_abc123"
  visual_hints.color: "#10b981"

chat_nodes:
  {id: "chat_abc123", ...}
  ↓
build_artifact_edges():
  ↓
  parent_id in chat_map? YES
  ↓
  Create edge:
    from: "chat_abc123"
    to: "artifact_c9e6f153"
    semantics: "artifact"
    metadata:
      type: "artifact"
      color: "#10b981"
      opacity: 0.5
```

## Complete Integration Timeline

```
Phase 108.2: Chat Nodes
  ├── Chat visualization in tree
  └── Chat → File edges

Phase 108.3: Artifact Nodes ← YOU ARE HERE
  ├── Artifact scanning service
  ├── Artifact → Chat linking
  ├── Position calculation
  ├── Type detection
  ├── API integration
  └── Test coverage

Phase 108.4: Artifact Editor (PLANNED)
  ├── Artifact preview modal
  ├── Syntax highlighting
  ├── Edit capabilities
  └── Save to artifacts/

Phase 108.5: Artifact Streaming (PLANNED)
  ├── Real-time status updates
  ├── Streaming progress indicator
  └── Error state handling
```

## Performance Metrics

```
Scan 25 artifacts:
  ├── Directory list: 2ms
  ├── staging.json load: 1ms
  ├── Type detection: 3ms
  ├── Position calc: 2ms
  ├── Edge building: 1ms
  └── Total: ~10ms

Memory:
  ├── Per artifact node: ~1KB
  ├── 25 artifacts: ~25KB
  └── Negligible impact
```

## Error Handling

```
try:
    artifact_nodes = scan_artifacts()
except DirectoryNotFound:
    ↓
    artifact_nodes = []
    log warning

try:
    staging = load_staging()
except JSONDecodeError:
    ↓
    staging_links = {}
    log warning

try:
    update_positions()
except PositionError:
    ↓
    use default positions
    log warning
```

## Frontend Rendering (Planned)

```
artifact_node (type: artifact)
  ↓
FileCard.tsx:
  ├── Badge: artifact_type (code/document/data/image)
  ├── Icon: based on language
  ├── Color: from visual_hints.color
  ├── Status: done ✓ | streaming ⟳ | error ✗
  └── Opacity: from visual_hints.opacity

artifact_edge (semantics: artifact)
  ↓
TreeEdges.tsx:
  ├── Color: from metadata.color
  ├── Style: dashed (vs solid for files)
  ├── Opacity: 0.5
  └── Arrow: from chat to artifact
```
