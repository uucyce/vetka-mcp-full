# Grok Research Prompt: Phase 122 — Unified Activity & Chat-to-Tree Binding

**For:** Grok 4.1 (The Last Samurai)
**From:** Opus Commander
**Date:** 2026-02-08
**Priority:** HIGH — Architectural Foundation

---

## Context

VETKA — 3D file tree visualization with integrated chat system. We need to implement:
1. **Activity Glow** — files/nodes that are "hot" (being worked on) should glow
2. **Chat-to-Tree Binding** — messages should be visually attached to tree nodes

Current state is fragmented. We need unified architecture.

---

## RESEARCH AREA 1: All Activity Sources

### 1.1 File Activity Sources
Identify ALL sources of file activity in VETKA:

| Source | Description | Current Tracking |
|--------|-------------|------------------|
| FileWatcher/Watchdog | OS-level file change detection | `heat_scores` dict |
| Scanner Panel | Manual/auto project scan | ? |
| Mycelium Pipeline | Agent file creation (`spawn_output/`) | Socket.IO events |
| MCP Tools | `vetka_edit_file`, `vetka_read_file` | Tool audit log |
| Git operations | Commits, checkouts, merges | ? |
| User manual edits | External editor changes | Watchdog |

**Questions for Grok:**
1. What's the current flow for each source?
2. Where are the gaps in tracking?
3. How do we unify into single "activity stream"?

### 1.2 Message Activity Sources
| Source | Description | Current Storage |
|--------|-------------|-----------------|
| User messages | Text input from UI | `chat_history.json` |
| Model responses | LLM replies | `chat_history.json` |
| System messages | Errors, notifications | ? |
| Agent pipeline | Mycelium progress updates | Socket.IO only (lost!) |
| MCP tool results | Tool execution output | Tool audit log |

**Questions:**
1. What messages are being lost (not persisted)?
2. How to capture pipeline progress as part of chat history?
3. What's the relationship between chat_id and message storage?

### 1.3 Artifact Creation (BROKEN)
Current problem: Architect in chat creates artifacts but:
- No standardized format
- No consistent storage
- No link to originating chat/message
- Approval flow unclear

**Questions:**
1. What IS an artifact? (code file, document, config?)
2. What metadata should artifacts have?
3. How should artifacts link to: chat, message, file node?
4. What's the approval workflow?

---

## RESEARCH AREA 2: Chat-to-Tree Binding Architecture

### 2.1 The Core Problem
```
┌─────────────────────────────────────────────────────────────────────┐
│                    CURRENT STATE (BROKEN)                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Chat Panel (Left)          3D Tree (Center)         Chat Feed      │
│  ┌──────────────┐          ┌──────────────┐         ┌──────────────┐│
│  │ Chat #1      │          │   src/       │         │ User: ...    ││
│  │ Chat #2      │          │   ├─ App.tsx │         │ Model: ...   ││
│  │ Chat #3 ←────┼──────────┼── │  ???     │ ←───────┼─ ???         ││
│  └──────────────┘          │   └─ ...     │         │ User: ...    ││
│                            └──────────────┘         └──────────────┘│
│                                                                      │
│  Problem: No visual link between chat messages and tree nodes!      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Desired State
```
┌─────────────────────────────────────────────────────────────────────┐
│                    TARGET STATE                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Chat Panel          3D Tree                       Chat Feed         │
│  ┌──────────┐       ┌─────────────────────┐       ┌──────────────┐  │
│  │ Chat #1  │       │     src/            │       │              │  │
│  │          │       │     ├─ App.tsx ─────┼───────┼─ Q1 + A1     │  │
│  │          │       │     │   └─ 💬       │       │              │  │
│  │          │       │     ├─ utils/ ──────┼───────┼─ Q2 + A2     │  │
│  │          │       │     │   └─ 💬💬     │       │              │  │
│  │          │       │     └─ 📍 (camera)──┼───────┼─ Q3 + A3     │  │
│  └──────────┘       └─────────────────────┘       │ (no file)    │  │
│                                                   └──────────────┘  │
│                                                                      │
│  ONE chat_id, but messages attach to DIFFERENT nodes!               │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.3 Hybrid Logic Requirements

**Rule 1: Chat ID is Persistent**
- `chat_id` = UUID, created once per conversation
- Never changes even if files discussed change
- Used for: history panel, persistence, API calls

**Rule 2: Messages Bind to Nodes**
- Each message pair (Q+A) has `anchor_node_id`
- If user asked about a file → anchor = that file's node
- If multiple files → anchor = first file OR parent folder
- If no file context → anchor = camera position (creates virtual node)

**Rule 3: Visual Representation**
- In **Chat Panel**: Single continuous chat
- In **Chat Feed**: Seamless message stream
- In **3D Tree**: Message pairs appear as child nodes of anchor

**Questions for Grok:**
1. How to determine `anchor_node_id` for each message?
2. What if user asks about file that doesn't exist yet?
3. How to handle file renames/moves mid-chat?
4. How to visualize message nodes in 3D? (size, color, decay?)
5. What's the data model for MessageNode?

---

## RESEARCH AREA 3: Data Models

### 3.1 Proposed Message Model
```python
class ChatMessage:
    id: str                    # UUID
    chat_id: str               # Parent chat UUID
    role: str                  # "user" | "assistant" | "system"
    content: str               # Message text
    timestamp: datetime

    # Binding
    anchor_node_id: str        # Tree node this message attaches to
    anchor_type: str           # "file" | "folder" | "camera" | "artifact"
    mentioned_files: List[str] # All files mentioned in message

    # Artifacts
    artifacts: List[str]       # Artifact IDs created by this message

    # Metadata
    model: str                 # Which LLM responded
    tokens_in: int
    tokens_out: int
```

### 3.2 Proposed Artifact Model
```python
class Artifact:
    id: str                    # UUID
    type: str                  # "code" | "document" | "config" | "image"

    # Origin
    chat_id: str               # Which chat created this
    message_id: str            # Which message created this
    creator_agent: str         # "user" | "architect" | "coder" | etc.

    # Content
    filepath: str              # Where saved (if saved)
    content: str               # Actual content
    language: str              # For code: "python", "typescript", etc.

    # Status
    status: str                # "draft" | "pending" | "approved" | "rejected"
    approved_by: str           # Who approved
    approved_at: datetime

    # Tree binding
    target_node_id: str        # Which tree node this artifact is for
```

### 3.3 Questions
1. Are these models complete?
2. What indexes needed for fast lookup?
3. How to handle orphaned artifacts (chat deleted)?
4. Storage: JSON vs SQLite vs Qdrant?

---

## RESEARCH AREA 4: Activity Stream Unification

### 4.1 Proposed Unified Activity Event
```python
class ActivityEvent:
    id: str
    timestamp: datetime

    # Source
    source_type: str           # "watcher" | "scanner" | "agent" | "user" | "mcp"
    source_id: str             # Specific source identifier

    # Target
    target_type: str           # "file" | "folder" | "chat" | "artifact"
    target_path: str           # File path or node ID

    # Action
    action: str                # "create" | "modify" | "delete" | "read" | "message"

    # Glow
    glow_intensity: float      # 0.0 - 1.0
    glow_duration_ms: int      # How long to glow
    glow_color: str            # Hex color (default: #7ab3d4)

    # Context
    chat_id: str               # If related to a chat
    message_id: str            # If related to a message
    agent_id: str              # If from an agent
```

### 4.2 Activity Stream Architecture
```
┌─────────────────────────────────────────────────────────────────────┐
│                     UNIFIED ACTIVITY STREAM                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ Watcher  │  │ Scanner  │  │ Mycelium │  │   MCP    │            │
│  │ (files)  │  │ (scan)   │  │ (agents) │  │ (tools)  │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
│       │             │             │             │                   │
│       └─────────────┴──────┬──────┴─────────────┘                   │
│                            │                                         │
│                            ▼                                         │
│                   ┌────────────────┐                                │
│                   │ ActivityHub    │                                │
│                   │ (unified bus)  │                                │
│                   └───────┬────────┘                                │
│                           │                                         │
│           ┌───────────────┼───────────────┐                         │
│           │               │               │                         │
│           ▼               ▼               ▼                         │
│    ┌────────────┐  ┌────────────┐  ┌────────────┐                  │
│    │ GlowSystem │  │ TreeNodes  │  │ ChatPanel  │                  │
│    │ (visual)   │  │ (binding)  │  │ (history)  │                  │
│    └────────────┘  └────────────┘  └────────────┘                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## RESEARCH AREA 5: Implementation Priorities

### Phase 122.1: Activity Hub
- Create unified ActivityEvent model
- Create ActivityHub service
- Connect: Watcher, Scanner, MCP tools

### Phase 122.2: Glow System
- Frontend: glowingNodes state
- FileCard: emissive material
- Socket.IO: activity_glow event

### Phase 122.3: Message Binding
- Add anchor_node_id to ChatMessage
- Implement anchor detection logic
- Create MessageNode 3D component

### Phase 122.4: Artifact Standardization
- Define Artifact model
- Create ArtifactService
- Integrate with Mycelium pipeline

### Phase 122.5: Chat History Persistence
- Save all messages to Vetka
- Implement message-to-node binding
- Add visual message nodes to 3D tree

---

## Specific Questions for Grok

### Architecture
1. Is ActivityHub the right abstraction, or should we use event sourcing?
2. How to handle high-frequency events (watcher can fire 100s/sec)?
3. Should we use Redis/RabbitMQ for the activity bus, or in-memory?

### Chat Binding
4. Algorithm for determining anchor_node_id from message content?
5. How to handle "camera position" anchors? (no file, just 3D coords)
6. Should message nodes be real tree nodes or overlay decorations?

### Artifacts
7. Current artifact creation flow — what's broken specifically?
8. How to integrate artifact approval with chat flow?
9. Should artifacts be first-class tree nodes?

### Storage
10. Current chat storage (chat_history.json) — limitations?
11. Should we migrate to SQLite for structured queries?
12. How to sync between local JSON and Qdrant vectors?

### Visual
13. How should message nodes look in 3D? (icon, size, animation)
14. How to show "activity glow" that's visible but not distracting?
15. Should glow propagate to parent folders?

---

## Files to Analyze

**Backend:**
- `src/scanners/file_watcher.py` — Watchdog integration, heat_scores
- `src/services/disk_artifact_service.py` — Artifact storage
- `src/services/activity_emitter.py` — Current activity events
- `src/orchestration/agent_pipeline.py` — Mycelium file operations
- `src/api/handlers/chat_handlers.py` — Chat message handling
- `src/api/handlers/user_message_handler.py` — User message processing
- `data/chat_history.json` — Current chat storage format

**Frontend:**
- `client/src/store/useStore.ts` — Global state, TreeNode type
- `client/src/components/canvas/FileCard.tsx` — Node rendering
- `client/src/components/chat/` — Chat panel components
- `client/src/utils/apiConverter.ts` — API data conversion

**Docs:**
- `docs/121_ph/PHASE_121_LABEL_HEAT_SYSTEM.md` — Heat system implementation
- `docs/121_ph/PHASE_122_AGENT_GLOW_RECON.md` — Initial glow research

---

## Expected Deliverables from Grok

1. **Architecture Document** — Unified activity & chat binding system design
2. **Data Model Spec** — Final models for Message, Artifact, ActivityEvent
3. **Gap Analysis** — What's missing in current implementation
4. **Implementation Roadmap** — Ordered phases with dependencies
5. **Risk Assessment** — What could go wrong, how to mitigate

---

## Success Criteria

After Phase 122 complete:
- [ ] ALL file activity sources emit unified events
- [ ] Files glow when being worked on (white with cold blue tint)
- [ ] Chat messages are saved to Vetka
- [ ] Messages visually attach to tree nodes
- [ ] Artifacts have standardized model and flow
- [ ] Single chat_id, multiple anchor nodes
- [ ] History panel shows continuous chat
- [ ] 3D tree shows message pairs at anchor points

---

**End of Research Prompt**

*Opus Commander awaits Grok's analysis.*
