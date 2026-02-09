# Phase 122: Unified Activity & Chat-to-Tree Binding — Implementation Plan

**Date:** 2026-02-08
**Sources:** Opus Recon (26 markers) + Grok Analysis
**Status:** APPROVED FOR IMPLEMENTATION
**Estimated:** 7 days total

---

## Executive Summary

Объединяем:
1. **Activity Glow** — файлы светятся когда над ними работают
2. **Chat-to-Tree Binding** — сообщения привязаны к узлам дерева
3. **Artifact Standardization** — единый формат артефактов

---

## Architecture (Grok + Opus)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     UNIFIED ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ Watchdog │  │ Scanner  │  │ Mycelium │  │   MCP    │            │
│  │ (files)  │  │ (scan)   │  │ (agents) │  │ (tools)  │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
│       │             │             │             │                   │
│       └─────────────┴──────┬──────┴─────────────┘                   │
│                            │                                         │
│                            ▼                                         │
│                   ┌────────────────┐                                │
│                   │  ActivityHub   │  ◄── Singleton, Redis/Socket   │
│                   │  heat_scores   │                                │
│                   └───────┬────────┘                                │
│                           │                                         │
│           ┌───────────────┼───────────────┐                         │
│           │               │               │                         │
│           ▼               ▼               ▼                         │
│    ┌────────────┐  ┌────────────┐  ┌────────────┐                  │
│    │ GlowSystem │  │ TreeNodes  │  │ ChatPanel  │                  │
│    │ (Three.js) │  │ (binding)  │  │ (history)  │                  │
│    └────────────┘  └────────────┘  └────────────┘                  │
│                                                                      │
│  Color: #5c8aaa → #7ab3d4 (Scanner Panel gradient)                 │
│  Glow:  rgba(122, 179, 212, 0.3)                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Models (Finalized)

### ChatMessage
```python
@dataclass
class ChatMessage:
    id: str                    # UUID
    chat_id: str               # Parent chat UUID (NEVER changes)
    role: str                  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime

    # Tree Binding
    anchor_node_id: str        # Path/UUID of tree node
    anchor_type: str           # "file" | "folder" | "camera" | "artifact"
    mentioned_files: List[str] # All files mentioned

    # Artifacts
    artifacts: List[str] = []  # Artifact IDs created

    # Heat
    heat_score: float = 0.0    # Activity score for glow

    # LLM Metadata
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
```

### Artifact
```python
@dataclass
class Artifact:
    id: str                    # UUID
    type: str                  # "code" | "document" | "config"

    # Origin
    chat_id: str
    message_id: str
    creator_agent: str         # "architect" | "coder" | "user"

    # Content
    filepath: Optional[str]    # If saved to disk
    content: str
    language: str = ""

    # Status
    status: str = "draft"      # draft → pending → approved → filed
    target_node_id: str        # Which tree node this is for
    version: int = 0
    diff_preview: str = ""     # For approval UI
```

### ActivityEvent
```python
@dataclass
class ActivityEvent:
    id: str
    timestamp: datetime

    # Source
    source_type: str           # "watchdog" | "scanner" | "agent" | "mcp" | "git"
    source_id: str

    # Target
    node_id: str               # Tree node path
    action: str                # "create" | "modify" | "delete" | "read" | "mention"

    # Glow
    score_delta: float         # +1 for edit, +0.5 for read, etc.
    glow_duration_ms: int = 5000
    glow_color: str = "#7ab3d4"

    # Context
    chat_id: Optional[str]
    message_id: Optional[str]
```

---

## Implementation Phases

### Phase 122.0: Setup (0.5 day)
**Files to create:**
- `src/services/activity_hub.py` — ActivityHub singleton
- `src/models/chat_models.py` — ChatMessage, Artifact dataclasses
- `src/models/activity_models.py` — ActivityEvent dataclass

**ActivityHub skeleton:**
```python
# src/services/activity_hub.py
from dataclasses import dataclass
from typing import Dict, Optional
import asyncio

class ActivityHub:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.heat_scores: Dict[str, float] = {}  # node_id → score (0-1)
        self.sio = None  # Set by app init
        self._decay_task = None

    async def emit_glow(self, node_id: str, intensity: float, reason: str):
        """Emit activity glow event."""
        self.heat_scores[node_id] = max(
            self.heat_scores.get(node_id, 0),
            intensity
        )
        if self.sio:
            await self.sio.emit('activity_glow', {
                'node_id': node_id,
                'intensity': intensity,
                'reason': reason,
                'color': '#7ab3d4'
            })

    def start_decay(self):
        """Start background decay task (every 30s)."""
        async def decay_loop():
            while True:
                await asyncio.sleep(30)
                for node_id in list(self.heat_scores):
                    self.heat_scores[node_id] *= 0.95
                    if self.heat_scores[node_id] < 0.01:
                        del self.heat_scores[node_id]
        self._decay_task = asyncio.create_task(decay_loop())

def get_activity_hub() -> ActivityHub:
    return ActivityHub()
```

### Phase 122.1: Activity Sources (1 day)
**Connect all sources to ActivityHub:**

| Source | File | Hook Point |
|--------|------|------------|
| Watchdog | `file_watcher.py` | `_handle_event()` |
| Scanner | `file_scanner.py` | `scan_directory()` |
| Mycelium | `agent_pipeline.py` | `_extract_and_write_files()` |
| MCP Tools | `edit_file_tool.py`, `read_file_tool.py` | `execute()` |
| Git | New: `git_watcher.py` | Post-commit hook |

**Example hook (Watchdog):**
```python
# In file_watcher.py, after debounced event
from src.services.activity_hub import get_activity_hub

async def _handle_event(self, event):
    # ... existing logic ...
    hub = get_activity_hub()
    await hub.emit_glow(
        node_id=event.src_path,
        intensity=0.8 if event.is_create else 0.5,
        reason=f"watchdog:{event.event_type}"
    )
```

### Phase 122.2: Chat-to-Tree Binding (2 days)
**Add anchor_node_id to messages:**

```python
# In chat_handlers.py or message_utils.py
def determine_anchor(content: str, context: dict) -> tuple[str, str]:
    """Determine anchor_node_id from message content."""

    # Priority 1: Explicit file mention
    mentioned_files = extract_file_paths(content)
    if mentioned_files:
        return mentioned_files[0], "file"

    # Priority 2: Pinned files in context
    pinned = context.get('pinned_files', [])
    if pinned:
        return pinned[0]['path'], "file"

    # Priority 3: Viewport visible files
    viewport = context.get('viewport_nodes', [])
    if viewport:
        return viewport[0]['id'], "folder"

    # Priority 4: Camera position (virtual node)
    camera_pos = context.get('camera_position', [0, 0, 0])
    return f"camera:{camera_pos[0]:.1f},{camera_pos[1]:.1f},{camera_pos[2]:.1f}", "camera"
```

**Frontend socket handler:**
```typescript
// In useStore.ts or socket handler
socket.on('activity_glow', (data) => {
  setGlowingNodes(prev => ({
    ...prev,
    [data.node_id]: {
      intensity: data.intensity,
      color: data.color,
      expiresAt: Date.now() + 5000
    }
  }));
});
```

### Phase 122.3: Artifact Standardization (1.5 days)
**Create ArtifactService:**

```python
# src/services/artifact_service.py
class ArtifactService:
    def __init__(self):
        self.artifacts: Dict[str, Artifact] = {}

    async def create(
        self,
        content: str,
        artifact_type: str,
        chat_id: str,
        message_id: str,
        target_node_id: str,
        creator: str = "architect"
    ) -> Artifact:
        artifact = Artifact(
            id=str(uuid.uuid4()),
            type=artifact_type,
            chat_id=chat_id,
            message_id=message_id,
            creator_agent=creator,
            content=content,
            target_node_id=target_node_id,
            status="pending"
        )
        self.artifacts[artifact.id] = artifact

        # Emit for approval
        hub = get_activity_hub()
        await hub.emit_glow(target_node_id, 0.9, "artifact_created")

        return artifact

    async def approve(self, artifact_id: str, filepath: str) -> bool:
        artifact = self.artifacts.get(artifact_id)
        if not artifact:
            return False

        artifact.status = "filed"
        artifact.filepath = filepath

        # Write to disk
        Path(filepath).write_text(artifact.content)

        # Emit glow
        hub = get_activity_hub()
        await hub.emit_glow(filepath, 1.0, "artifact_approved")

        return True
```

### Phase 122.4: Three.js Glow (1 day)
**Modify FileCard.tsx:**

```typescript
// FileCard.tsx
import { MeshStandardMaterial } from 'three';

interface FileCardProps {
  // ... existing props
  glowIntensity?: number;  // 0-1 from ActivityHub
  glowColor?: string;      // Default: #7ab3d4
}

// In component:
const material = useMemo(() => {
  if (glowIntensity && glowIntensity > 0) {
    return new MeshStandardMaterial({
      map: texture,
      transparent: true,
      opacity,
      emissive: new Color(glowColor || '#7ab3d4'),
      emissiveIntensity: glowIntensity * 0.5,
    });
  }
  return new MeshBasicMaterial({
    map: texture,
    transparent: true,
    opacity,
  });
}, [texture, opacity, glowIntensity, glowColor]);
```

**Optional: Add Bloom postprocessing:**
```typescript
// App.tsx
import { EffectComposer, Bloom } from '@react-three/postprocessing';

<Canvas>
  {/* ... existing content ... */}
  <EffectComposer>
    <Bloom
      intensity={0.3}
      luminanceThreshold={0.8}
      luminanceSmoothing={0.9}
    />
  </EffectComposer>
</Canvas>
```

### Phase 122.5: Persist & Polish (0.5 day)
- SQLite schema for messages/artifacts
- Orphan cleanup cron
- Rename/move handling via Watchdog remap
- Parent folder glow propagation

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Tree pollution (too many message nodes) | Use overlays, not real nodes |
| Performance (360+ nodes glow) | LOD + foveated render + decay |
| Anchor drift (file rename) | Watchdog remap + versioning |
| Socket drops | Redis persist + retry |
| LLM anchor accuracy | Fallback: camera/parent |

---

## Files to Modify

### Backend (Create)
- `src/services/activity_hub.py` — NEW
- `src/models/chat_models.py` — NEW
- `src/models/activity_models.py` — NEW
- `src/services/artifact_service.py` — NEW

### Backend (Modify)
- `src/scanners/file_watcher.py` — Add hub.emit_glow
- `src/services/activity_emitter.py` — Integrate with hub
- `src/api/handlers/chat_handlers.py` — Add anchor_node_id
- `src/orchestration/agent_pipeline.py` — Connect to hub
- `src/mcp/tools/edit_file_tool.py` — Emit activity
- `src/mcp/tools/read_file_tool.py` — Emit activity

### Frontend (Modify)
- `client/src/store/useStore.ts` — Add glowingNodes state
- `client/src/components/canvas/FileCard.tsx` — Add emissive material
- `client/src/App.tsx` — Optional Bloom, socket handler

---

## Success Criteria

- [ ] ALL activity sources emit to ActivityHub
- [ ] Files glow when worked on (white + cold blue)
- [ ] Chat messages saved with anchor_node_id
- [ ] Messages visually attach to tree nodes
- [ ] Artifacts have standard model
- [ ] Single chat_id, multiple anchors
- [ ] History panel = continuous chat
- [ ] 3D tree shows message pairs at anchors

---

**Ready to start Phase 122.0?**
