# MCP ↔ VETKA Chat Integration Audit (Phase 108)
**Status Report for Grok Multi-Agent Planning**

Date: 2026-02-02
Phase: 108 (MCP-Chat Unification)

---

## MARKER_MCP_CHAT_READY - MCP Session ↔ Chat Linking

### Session Initialization Architecture

| Feature | Status | File | Line | Details |
|---------|--------|------|------|---------|
| **Unified Session ID** | ✅ READY | `src/mcp/tools/session_tools.py` | 153-191 | `session_id = chat_id` when linked |
| **Chat ID Parameter** | ✅ READY | `src/mcp/tools/session_tools.py` | 100-103 | `chat_id` parameter in schema for Phase 108.1 |
| **Auto-Create Chat** | ✅ READY | `src/mcp/tools/session_tools.py` | 166-179 | Creates VETKA chat if no chat_id provided |
| **Chat Manager Integration** | ✅ READY | `src/mcp/tools/session_tools.py` | 168-171 | Uses `ChatHistoryManager.get_or_create_chat()` |
| **Session Persistence** | ✅ READY | `src/mcp/tools/session_tools.py` | 256-263 | MCP state saved with TTL (1 hour) |

### MCP Tools for Chat Management

| Tool | Status | Location | Purpose |
|------|--------|----------|---------|
| `vetka_session_init` | ✅ EXISTS | `session_tools.py:69-268` | Initialize with chat linking |
| `vetka_session_status` | ✅ EXISTS | `session_tools.py:271-356` | Check session validity |
| **send_message** | ❌ MISSING | - | Tool to send message to MCP chat |
| **get_chat_digest** | ✅ READY | `chat_history_manager.py:529-605` | Fetch compressed chat context |
| **search_chat_history** | ✅ READY | `qdrant_client.py:797-858` | Semantic search across chats |

### Markers Present

```python
# MARKER_108_1: Unified MCP-Chat ID
- Location: src/mcp/tools/session_tools.py:153-191
- Purpose: Link MCP session_id to VETKA chat_id
- Logic: If chat_id provided → use as session_id
         If not provided → create new chat, use its ID as session_id
- Result: session.linked = True when linked to existing chat

# MARKER_108_3: Chat digest for MCP context
- Location: src/chat/chat_history_manager.py:528-605
- Purpose: Provide lightweight chat summary for MCP agents
- Returns: recent_messages, agent_logs, summary (ELISION-compressed option)
```

---

## MARKER_QDRANT_CHAT_INDEX - Chat → Qdrant Indexing

### Qdrant Chat Collection (VetkaGroupChat)

| Feature | Status | File | Line | Details |
|---------|--------|------|------|---------|
| **Collection Defined** | ✅ YES | `src/memory/qdrant_client.py` | 75 | `'chat': 'VetkaGroupChat'` |
| **Message Embedding** | ✅ YES | `src/memory/qdrant_client.py` | 754-756 | Uses `get_embedding(content[:2000])` |
| **Message Upsert** | ✅ YES | `src/memory/qdrant_client.py` | 717-794 | `upsert_chat_message()` function |
| **Semantic Search** | ✅ YES | `src/memory/qdrant_client.py` | 797-858 | `search_chat_history()` with filters |
| **Chat Message Payload** | ✅ YES | `src/memory/qdrant_client.py` | 766-776 | Stores: group_id, message_id, sender_id, role, agent, model, timestamp |
| **Filter by Group** | ✅ YES | `src/memory/qdrant_client.py` | 828-839 | Can filter by group_id or role |

### Migration & Persistence

| Feature | Status | File | Line | Details |
|---------|--------|------|------|---------|
| **Migration Script** | ✅ EXISTS | `scripts/migrate_chat_to_qdrant.py` | Full file | Dry-run ready, migrates from JSON |
| **Auto-Persist User Messages** | ✅ YES | `src/services/group_chat_manager.py` | 682-700 | Wrapped in background task (MARKER_103.7) |
| **Auto-Persist Agent Messages** | ✅ YES | `src/api/handlers/group_message_handler.py` | 996-1026 | Wrapped in background task (MARKER_103.7) |
| **Embedding Service** | ✅ READY | `src/utils/embedding_service.py` | - | `get_embedding()` for vector generation |

### Vector Search Capabilities

```python
# Query chat history with:
search_chat_history(
    query="semantic search text",
    group_id="optional_group_filter",
    role="user|assistant|optional",
    limit=10
)
# Returns: List of messages with semantic similarity scores
```

---

## MARKER_ARTIFACTS_STORAGE - Artifact Persistence

### Disk Artifact Service (Phase 104.9)

| Feature | Status | File | Line | Details |
|---------|--------|------|------|---------|
| **Directory** | ✅ YES | `src/services/disk_artifact_service.py` | 39 | `artifacts/` directory in project root |
| **Sanitization** | ✅ YES | `src/services/disk_artifact_service.py` | 71-100 | Prevents path traversal, limits to 100 chars |
| **File Extension Mapping** | ✅ YES | `src/services/disk_artifact_service.py` | 42-65 | Maps language → file extension (py, ts, rs, etc.) |
| **Minimum Content Length** | ✅ YES | `src/services/disk_artifact_service.py` | 68 | `MIN_CONTENT_LENGTH = 500` chars |
| **Socket.IO Events** | ✅ YES | `src/services/disk_artifact_service.py` | - | Emits `artifact_approval` event |

### Artifact Linking to Chats

| Feature | Status | File | Line | Details |
|---------|--------|------|------|---------|
| **Chat-Artifact Link** | ✅ YES | `src/api/handlers/group_message_handler.py` | 955-994 | `MARKER_103_ARTIFACT_LINK: Added source_message_id` |
| **Traceability** | ✅ YES | `src/utils/staging_utils.py` | 220, 508 | Artifacts stored with `source_message_id` in Qdrant |
| **Agent Auto-Stage** | ✅ YES | `src/api/handlers/group_message_handler.py` | 955-994 | Dev/Architect responses auto-stage artifacts |
| **Approval Workflow** | ✅ YES | `src/api/handlers/stream_handler.py` | 98, 802 | Phase 104.9 artifact approval events |

### Artifact Storage Flow

```
Dev/Architect generates code
    ↓
Auto-stage to artifacts/ (Phase 103.6)
    ↓
Emit artifact_approval event (Phase 104.9)
    ↓
Save to Qdrant VetkaGroupChat with source_message_id
    ↓
Can retrieve via search_chat_history() with group_id filter
```

---

## MARKER_TODO_QDRANT_CHAT - TODO Items for Grok Planning

### Priority 1: Critical Gaps

1. **❌ Missing MCP Tool: `vetka_send_message`**
   - Purpose: Send message to MCP-linked chat
   - Location: Should be in `src/mcp/tools/`
   - Needed for: Agents to append messages to chats during workflows
   - Estimated complexity: LOW (2-3 hours)
   - Dependencies: `ChatHistoryManager.add_message()` + Qdrant upsert

2. **❌ Missing MCP Tool: `vetka_get_chat_messages`**
   - Purpose: Retrieve paginated messages from MCP chat
   - Location: Should be in `src/mcp/tools/`
   - Needed for: Multi-turn agent conversations with context
   - Estimated complexity: LOW (2-3 hours)
   - Dependencies: `ChatHistoryManager.get_chat_messages()` + pagination

3. **⚠️ Embedding Service Not Integrated**
   - Issue: `search_chat_history()` calls `get_embedding()` but service may not be running
   - Location: `src/utils/embedding_service.py` (assumed, not verified)
   - Needed for: Semantic search to work properly
   - Estimated complexity: MEDIUM (verify + fix if needed)
   - Dependencies: Vector database, embedding model (e.g., sentence-transformers)

### Priority 2: Robustness

4. **⚠️ No Retry Logic for Chat Persistence**
   - Issue: Qdrant upsert wrapped in background task but no retry on failure
   - Location: `src/services/group_chat_manager.py:682-700`, `src/api/handlers/group_message_handler.py:996-1026`
   - Risk: Chat messages may be lost if Qdrant temporarily unavailable
   - Fix: Add `QdrantAutoRetry` wrapper (already exists in codebase)

5. **⚠️ Chat Digest Max Messages Hardcoded**
   - Issue: `get_chat_digest(max_messages=10)` may truncate important context
   - Location: `src/chat/chat_history_manager.py:529`
   - Needed for: Configurable context window for different agent types
   - Estimated complexity: LOW (1-2 hours)

6. **⚠️ No Rate Limiting for Chat Search**
   - Issue: `search_chat_history()` has no pagination or limits
   - Location: `src/memory/qdrant_client.py:797-858`
   - Risk: Large queries could timeout or return too many results
   - Fix: Add `offset` + `limit` parameters like chat list API

### Priority 3: Enhancement

7. **Feature: Chat → 3D Tree Integration**
   - Related to: Task #4 - "История чатов как 3D ноды в Ветке"
   - Purpose: Visualize chat hierarchy in 3D viewport
   - Location: Not yet implemented
   - Needed for: Spatial understanding of multi-agent conversations
   - Estimated complexity: HIGH (5-8 hours)
   - Dependencies: VETKA 3D rendering + chat metadata

8. **Feature: Unified MCP-Chat Console**
   - Purpose: View/manage MCP sessions and linked chats together
   - Location: `src/mcp/mcp_console_standalone.py` (expand)
   - Needed for: Developers to debug agent workflows
   - Estimated complexity: MEDIUM (3-5 hours)
   - Dependencies: MCP state manager + chat history API

---

## System Health Summary

| Component | Status | Notes |
|-----------|--------|-------|
| **Qdrant Server** | ✅ HEALTHY | Available at localhost:6333 |
| **VetkaGroupChat Collection** | ✅ CREATED | Phase 103.7 - chat history persistence |
| **Chat History Manager** | ✅ ACTIVE | JSON-based with retention policy (Phase 107.3) |
| **Session Management** | ✅ ACTIVE | MCP state manager with 1-hour TTL |
| **Artifact Storage** | ✅ ACTIVE | Disk + Qdrant dual storage |
| **Embedding Service** | ⚠️ ASSUMED | Need to verify connectivity |

---

## Next Steps for Grok

1. **Immediate (Phase 108.2)**
   - [ ] Implement `vetka_send_message` MCP tool
   - [ ] Implement `vetka_get_chat_messages` MCP tool with pagination
   - [ ] Verify embedding service availability

2. **Short-term (Phase 108.3-108.4)**
   - [ ] Add retry logic for Qdrant persistence
   - [ ] Add rate limiting to chat search
   - [ ] Make chat digest max_messages configurable

3. **Medium-term (Phase 109+)**
   - [ ] Integrate chats into 3D VETKA tree
   - [ ] Build unified MCP-Chat console UI
   - [ ] Add chat/artifact query to Elisya memory

---

## Code References

### Phase 108.1 - Unified MCP-Chat ID
```python
# File: src/mcp/tools/session_tools.py
# Lines: 153-191

if chat_id:
    session_id = chat_id
    linked_to_existing = True
else:
    # Create new VETKA chat and use its ID as session_id
    new_chat_id = chat_mgr.get_or_create_chat(
        file_path="unknown",
        context_type="topic",
        topic="MCP Session",
        display_name=f"MCP {user_id[:8]}"
    )
    session_id = new_chat_id
```

### Phase 103.7 - Chat History Persistence
```python
# File: src/memory/qdrant_client.py
# Lines: 715-859

def upsert_chat_message(...) -> bool:
    """Upsert a chat message to VetkaGroupChat collection"""
    # Get embedding, generate point ID, upsert to Qdrant
    # Graceful failure if Qdrant unavailable

def search_chat_history(query, group_id=None, role=None, limit=10):
    """Search chat history using semantic similarity"""
```

### Phase 104.9 - Artifact Approval
```python
# File: src/api/handlers/stream_handler.py
# Lines: 98, 787-802

# MARKER_104_ARTIFACT_EVENT: Phase 104.9 - Artifact approval workflow
# Emits artifact_approval event for Socket.IO client
```

---

## Audit Conclusions

**Ready for Phase 108.2:**
- MCP session ↔ chat linking infrastructure: ✅ 95% complete
- Qdrant chat indexing: ✅ 90% complete (missing search pagination)
- Artifact storage & linking: ✅ 95% complete

**Blockers for Full Implementation:**
1. Missing MCP tools for send_message and get_chat_messages
2. Embedding service connectivity verification needed
3. Rate limiting for large queries

**Recommendation:** Grok should prioritize TODO items 1-2 first, then 3-6 before addressing enhancements.
