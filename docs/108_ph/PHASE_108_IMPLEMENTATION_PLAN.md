# Phase 108 Implementation Plan - MCP ↔ VETKA Chat Unification
**Grok Multi-Agent Task Breakdown**

---

## Phase 108.1 - Session ↔ Chat Linking (COMPLETE)

### Status: ✅ VERIFIED READY

**Implemented:**
- [x] Unified session_id = chat_id architecture
- [x] vetka_session_init with optional chat_id parameter
- [x] Auto-create chat if chat_id not provided
- [x] Session persistence with 1-hour TTL
- [x] Linked status flag in response

**Files Modified:**
- `src/mcp/tools/session_tools.py` (lines 153-191)
- `src/chat/chat_history_manager.py` (get_or_create_chat)

**Marker:** MARKER_MCP_CHAT_READY ✅

---

## Phase 108.2 - Missing MCP Tools (IMMEDIATE ACTION)

### Task 1: Implement `vetka_send_message` Tool

**Purpose:** Allow MCP agents to send messages to linked chat

**File:** Create `src/mcp/tools/send_message_tool.py`

**Implementation:**
```python
class SendMessageTool(BaseMCPTool):
    """Send message to MCP-linked chat."""

    @property
    def name(self) -> str:
        return "vetka_send_message"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "chat_id": {
                    "type": "string",
                    "description": "Chat ID to send message to"
                },
                "content": {
                    "type": "string",
                    "description": "Message content"
                },
                "role": {
                    "type": "string",
                    "enum": ["user", "assistant", "agent"],
                    "description": "Message role (default: user)",
                    "default": "user"
                },
                "sender_id": {
                    "type": "string",
                    "description": "Sender ID (default: anonymous)"
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional metadata (optional)"
                }
            },
            "required": ["chat_id", "content"]
        }

    async def _execute_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to chat and persist to Qdrant."""
        from src.chat.chat_history_manager import get_chat_history_manager
        from src.memory.qdrant_client import upsert_chat_message
        import uuid
        from datetime import datetime

        chat_id = arguments.get("chat_id")
        content = arguments.get("content")
        role = arguments.get("role", "user")
        sender_id = arguments.get("sender_id", "anonymous")
        metadata = arguments.get("metadata", {})

        if not chat_id or not content:
            return {"success": False, "error": "chat_id and content required"}

        try:
            # Add to JSON history
            mgr = get_chat_history_manager()
            msg_id = str(uuid.uuid4())
            message = {
                "id": msg_id,
                "role": role,
                "content": content,
                "sender_id": sender_id,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata
            }

            success = mgr.add_message(chat_id, message)
            if not success:
                return {"success": False, "error": "Chat not found"}

            # Persist to Qdrant (background)
            asyncio.create_task(upsert_chat_message(
                group_id=chat_id,
                message_id=msg_id,
                sender_id=sender_id,
                content=content,
                role=role,
                metadata=metadata
            ))

            return {
                "success": True,
                "result": {
                    "message_id": msg_id,
                    "chat_id": chat_id,
                    "timestamp": message["timestamp"]
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
```

**Complexity:** LOW (2-3 hours)

**Testing:**
```bash
# Via MCP CLI
vetka_send_message(
    chat_id="uuid-xxx",
    content="Analyzing codebase...",
    role="assistant",
    sender_id="grok_agent_1"
)
```

---

### Task 2: Implement `vetka_get_chat_messages` Tool

**Purpose:** Retrieve paginated messages from MCP chat with context

**File:** Create `src/mcp/tools/get_messages_tool.py`

**Implementation:**
```python
class GetChatMessagesTool(BaseMCPTool):
    """Get messages from MCP-linked chat."""

    @property
    def name(self) -> str:
        return "vetka_get_chat_messages"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "chat_id": {
                    "type": "string",
                    "description": "Chat ID to retrieve messages from"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max messages to return (default: 50)",
                    "default": 50
                },
                "offset": {
                    "type": "integer",
                    "description": "Skip first N messages (default: 0)",
                    "default": 0
                },
                "search_query": {
                    "type": "string",
                    "description": "Optional semantic search query"
                },
                "include_metadata": {
                    "type": "boolean",
                    "description": "Include message metadata (default: true)",
                    "default": True
                }
            },
            "required": ["chat_id"]
        }

    async def _execute_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get chat messages with optional semantic search."""
        from src.chat.chat_history_manager import get_chat_history_manager
        from src.memory.qdrant_client import search_chat_history

        chat_id = arguments.get("chat_id")
        limit = arguments.get("limit", 50)
        offset = arguments.get("offset", 0)
        search_query = arguments.get("search_query")
        include_metadata = arguments.get("include_metadata", True)

        try:
            mgr = get_chat_history_manager()
            chat = mgr.get_chat(chat_id)

            if not chat:
                return {"success": False, "error": "Chat not found"}

            if search_query:
                # Use semantic search
                results = search_chat_history(
                    query=search_query,
                    group_id=chat_id,
                    limit=limit
                )
                return {
                    "success": True,
                    "result": {
                        "chat_id": chat_id,
                        "search_query": search_query,
                        "messages": results,
                        "total": len(results)
                    }
                }
            else:
                # Regular pagination
                messages = chat.get("messages", [])
                paginated = messages[offset:offset + limit]

                return {
                    "success": True,
                    "result": {
                        "chat_id": chat_id,
                        "messages": paginated,
                        "total": len(messages),
                        "offset": offset,
                        "limit": limit,
                        "has_more": (offset + limit) < len(messages)
                    }
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
```

**Complexity:** LOW (2-3 hours)

**Testing:**
```bash
# Pagination
vetka_get_chat_messages(chat_id="uuid-xxx", limit=10, offset=0)

# Semantic search
vetka_get_chat_messages(
    chat_id="uuid-xxx",
    search_query="how to fix bug",
    limit=5
)
```

---

### Task 3: Verify Embedding Service

**Purpose:** Ensure semantic search works for chat history

**Location:** `src/utils/embedding_service.py` (assumed)

**Action Items:**
1. [ ] Verify file exists at `src/utils/embedding_service.py`
2. [ ] Check that `get_embedding()` function exists
3. [ ] Verify it returns 768-dimensional vector (for Qdrant)
4. [ ] Test with sample text: `get_embedding("test message")`
5. [ ] Check service connectivity (model loaded, memory available)
6. [ ] If not working: add error handling to search_chat_history()

**Complexity:** MEDIUM (1-2 hours to verify, 2-3 hours if fixes needed)

**Dependencies:**
- sentence-transformers or similar embedding model
- GPU memory (if using GPU)
- Model cache directory

---

### Task 4: Register Tools in MCP Bridge

**File:** `src/mcp/vetka_mcp_bridge.py`

**Action:**
1. Import new tools:
```python
from src.mcp.tools.send_message_tool import SendMessageTool
from src.mcp.tools.get_messages_tool import GetChatMessagesTool
```

2. Register in tool list:
```python
# Around line ~80-100 where other tools registered
tool_list.append(SendMessageTool())
tool_list.append(GetChatMessagesTool())
```

3. Add to MCP schema export

**Complexity:** LOW (1 hour)

---

## Phase 108.3 - Robustness Improvements (SHORT-TERM)

### Task 5: Add Pagination to `search_chat_history()`

**File:** `src/memory/qdrant_client.py` (lines 797-858)

**Changes:**
```python
def search_chat_history(
    query: str,
    group_id: str = None,
    role: str = None,
    limit: int = 10,
    offset: int = 0  # ADD THIS
) -> List[Dict]:
    # ... existing code ...

    results = client.client.search(
        collection_name=client.COLLECTION_NAMES['chat'],
        query_vector=query_vector,
        query_filter=query_filter,
        limit=limit,
        offset=offset  # ADD THIS
    )
```

**Complexity:** LOW (1-2 hours)

---

### Task 6: Add Retry Logic for Qdrant Upsert

**Files:**
- `src/services/group_chat_manager.py:682-700`
- `src/api/handlers/group_message_handler.py:996-1026`

**Changes:**
```python
# Replace:
asyncio.create_task(upsert_chat_message(...))

# With:
from src.memory.qdrant_auto_retry import QdrantAutoRetry
asyncio.create_task(QdrantAutoRetry.execute_with_retry(
    func=upsert_chat_message,
    kwargs={...},
    max_retries=3,
    backoff_seconds=1
))
```

**Complexity:** LOW (1-2 hours)

---

### Task 7: Make Chat Digest Max Messages Configurable

**File:** `src/chat/chat_history_manager.py` (lines 529-605)

**Changes:**
```python
# Add to schema:
"max_messages": {
    "type": "integer",
    "description": "Max messages in digest (default: 10)",
    "default": 10
}

# Pass through:
def get_chat_digest(self, chat_id: str, max_messages: int = 10) -> dict:
    # Use max_messages parameter instead of hardcoded 10
```

**Complexity:** LOW (1 hour)

---

## Phase 108.4 - Enhancements (MEDIUM-TERM)

### Task 8: Integrate Chats into 3D VETKA Tree

**Purpose:** Visualize multi-agent conversations in spatial context

**Complexity:** HIGH (5-8 hours)

**Components:**
- Map chat_id → 3D node in VetkaTree
- Show message flow as edges between agents
- Render in viewport alongside code tree

---

### Task 9: Build Unified MCP-Chat Console

**Purpose:** Debug and monitor MCP-linked chats

**Complexity:** MEDIUM (3-5 hours)

**Features:**
- List active MCP sessions
- Show linked chats per session
- Search across all indexed messages
- View artifacts per chat

---

## Success Criteria

### Phase 108.2 (Completion: 1-2 weeks)
- [ ] vetka_send_message tool fully functional and tested
- [ ] vetka_get_chat_messages tool with pagination working
- [ ] Embedding service verified and integrated
- [ ] Both tools registered in MCP bridge
- [ ] All existing tests still pass
- [ ] Markers MARKER_MCP_CHAT_READY + MARKER_QDRANT_CHAT_INDEX verified

### Phase 108.3 (Completion: 2-3 weeks)
- [ ] search_chat_history() has pagination working
- [ ] Qdrant upserts have retry logic
- [ ] Chat digest max_messages configurable
- [ ] All 6 robustness items checked off

### Phase 108.4 (Completion: 3-4 weeks)
- [ ] Chat hierarchy visible in 3D tree
- [ ] Chat console UI deployed
- [ ] Grok can query chat context natively

---

## Testing Plan

### Unit Tests
```python
# test_send_message_tool.py
def test_send_message_creates_entry():
    """Verify message added to chat"""
def test_send_message_triggers_qdrant_upsert():
    """Verify message persisted to Qdrant"""
def test_send_message_chat_not_found():
    """Verify error handling"""

# test_get_messages_tool.py
def test_get_messages_pagination():
    """Verify offset/limit work"""
def test_get_messages_semantic_search():
    """Verify search_query returns relevant results"""
```

### Integration Tests
```python
# test_mcp_chat_workflow.py
async def test_full_workflow():
    """
    1. Init MCP session with new chat
    2. Send message via vetka_send_message
    3. Retrieve via vetka_get_chat_messages
    4. Verify in Qdrant VetkaGroupChat collection
    """
```

### Manual Testing
```bash
# Via MCP console
claude_code> Use MCP tool "vetka_send_message"
input> {"chat_id": "...", "content": "test message"}

claude_code> Use MCP tool "vetka_get_chat_messages"
input> {"chat_id": "...", "search_query": "test"}
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Embedding service unavailable | MEDIUM | HIGH | Graceful fallback to exact search |
| Qdrant upsert failures | LOW | MEDIUM | Retry logic with exponential backoff |
| Pagination offset out of bounds | LOW | LOW | Bounds check in tool |
| Message payload size exceeds limit | LOW | MEDIUM | Truncate content to 5000 chars |

---

## Dependencies

### External Services
- Qdrant: localhost:6333 (already running)
- Embedding model: sentence-transformers or similar

### Internal Modules
- ChatHistoryManager: `src/chat/chat_history_manager.py` ✅
- QdrantClient: `src/memory/qdrant_client.py` ✅
- MCP Tools: `src/mcp/tools/base_tool.py` ✅

### Already Implemented
- Chat persistence (Phase 103.7) ✅
- Artifact storage (Phase 104.9) ✅
- Session management (Phase 96) ✅

---

## Timeline Estimate

| Phase | Tasks | Duration | Start | End |
|-------|-------|----------|-------|-----|
| 108.2 | 1-4 | 5-7 days | Now | Feb 9 |
| 108.3 | 5-7 | 3-5 days | Feb 9 | Feb 14 |
| 108.4 | 8-9 | 1-2 weeks | Feb 14 | Feb 28 |

**Critical Path:** Tasks 1-2 block multi-agent workflows, so prioritize Phase 108.2.

---

## Grok Execution Guide

1. **Start with Task 1:** Implement vetka_send_message (2-3 hrs)
2. **Parallel Task 2:** Implement vetka_get_chat_messages (2-3 hrs)
3. **Task 3 in parallel:** Verify embedding service (1-2 hrs)
4. **Task 4:** Register both tools in MCP bridge (1 hr)
5. **Test:** Run full MCP → Chat → Qdrant workflow
6. **Phase 108.3:** Iterate robustness improvements
7. **Phase 108.4:** Begin spatial visualization work

**Blockers:** None identified. All dependencies available.

**Quick wins:** All Phase 108.2 tasks are LOW complexity, can be parallelized.
