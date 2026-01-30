# Phase 80.11: Fix Pinned Files Persistence in Group Chat

**Date:** 2026-01-21
**Status:** ✅ FIXED
**Issue:** Pinned files were not being saved to `groups.json`

---

## Problem Statement

When users sent messages to group chats with pinned files, the `pinned_files` array was:
- ✅ Sent from frontend in the request
- ❌ NOT extracted from the request in the handler
- ❌ NOT stored in message metadata
- ❌ NOT persisted to `groups.json`

### Evidence from Audit (PHASE_80_11)

```
groups.json НЕ содержит поле pinned_files
Пины передаются в запросе но не персистятся
```

---

## Root Cause Analysis

### 1. Request Data Flow

**Frontend** (`client/src/hooks/useSocket.ts:270`)
```typescript
user_message: (data: {
  text: string;
  node_path: string;
  node_id: string;
  model?: string;
  pinned_files?: PinnedFile[];  // ✅ Sent from frontend
  viewport_context?: ViewportContext
}) => void;
```

**Handler** (`src/api/handlers/group_message_handler.py:369-372`)
```python
# BEFORE FIX:
group_id = data.get('group_id')
sender_id = data.get('sender_id', 'user')
content = data.get('content', '').strip()
reply_to_id = data.get('reply_to')
# ❌ pinned_files NOT extracted!
```

### 2. Message Storage

**Handler** (`src/api/handlers/group_message_handler.py:390-395`)
```python
# BEFORE FIX:
user_message = await manager.send_message(
    group_id=group_id,
    sender_id=sender_id,
    content=content,
    message_type='chat'
    # ❌ metadata NOT passed!
)
```

### 3. Data Structure (Already Correct)

**GroupMessage class** (`src/services/group_chat_manager.py:51-72`)
```python
@dataclass
class GroupMessage:
    id: str
    group_id: str
    sender_id: str
    content: str
    mentions: List[str]
    message_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)  # ✅ Supports metadata
    created_at: datetime

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'group_id': self.group_id,
            'sender_id': self.sender_id,
            'content': self.content,
            'mentions': self.mentions,
            'message_type': self.message_type,
            'metadata': self.metadata,  # ✅ Included in serialization
            'created_at': self.created_at.isoformat()
        }
```

**Persistence** (`src/services/group_chat_manager.py:672-673`)
```python
'messages': [
    msg.to_dict() for msg in group.messages  # ✅ Uses to_dict()
]
```

**Loading** (`src/services/group_chat_manager.py:734-743`)
```python
msg = GroupMessage(
    id=msg_dict['id'],
    group_id=msg_dict['group_id'],
    sender_id=msg_dict['sender_id'],
    content=msg_dict['content'],
    mentions=msg_dict.get('mentions', []),
    message_type=msg_dict.get('message_type', 'chat'),
    metadata=msg_dict.get('metadata', {}),  # ✅ Restores metadata
    created_at=datetime.fromisoformat(msg_dict['created_at'])
)
```

---

## Solution

### Changes Made

**File:** `src/api/handlers/group_message_handler.py`

#### Change 1: Extract pinned_files from request

```python
# Line 369-373 (AFTER FIX):
group_id = data.get('group_id')
sender_id = data.get('sender_id', 'user')
content = data.get('content', '').strip()
reply_to_id = data.get('reply_to')  # Phase 80.7: Message ID being replied to
pinned_files = data.get('pinned_files', [])  # Phase 80.11: Pinned files for context
```

#### Change 2: Pass pinned_files in metadata

```python
# Line 390-396 (AFTER FIX):
# Store user message in group (Phase 80.11: Include pinned_files in metadata)
user_message = await manager.send_message(
    group_id=group_id,
    sender_id=sender_id,
    content=content,
    message_type='chat',
    metadata={'pinned_files': pinned_files} if pinned_files else {}
)
```

---

## Verification

### Test Case 1: Send Message with Pinned Files

**Request:**
```json
{
  "group_id": "310a871f-b981-49ca-97d0-a8d47e9428ac",
  "sender_id": "user",
  "content": "Analyze these files",
  "pinned_files": [
    {
      "node_id": "src/app.py",
      "path": "/Users/user/project/src/app.py",
      "name": "app.py"
    },
    {
      "node_id": "src/config.py",
      "path": "/Users/user/project/src/config.py",
      "name": "config.py"
    }
  ]
}
```

**Expected Result in `groups.json`:**
```json
{
  "id": "msg-uuid",
  "group_id": "310a871f-b981-49ca-97d0-a8d47e9428ac",
  "sender_id": "user",
  "content": "Analyze these files",
  "mentions": [],
  "message_type": "chat",
  "metadata": {
    "pinned_files": [
      {
        "node_id": "src/app.py",
        "path": "/Users/user/project/src/app.py",
        "name": "app.py"
      },
      {
        "node_id": "src/config.py",
        "path": "/Users/user/project/src/config.py",
        "name": "config.py"
      }
    ]
  },
  "created_at": "2026-01-21T20:00:00.000000"
}
```

### Test Case 2: Message Without Pinned Files

**Request:**
```json
{
  "group_id": "310a871f-b981-49ca-97d0-a8d47e9428ac",
  "sender_id": "user",
  "content": "Hello team"
}
```

**Expected Result:**
```json
{
  "metadata": {}
}
```

---

## Related Components

### Components That Use Pinned Files

1. **User Message Handler** (`src/api/handlers/user_message_handler.py:184`)
   ```python
   pinned_files = data.get('pinned_files', [])
   # ✅ Already extracts pinned_files
   ```

2. **CAM System** (`src/llm/context_assembly_manager.py`)
   - Uses pinned files for context assembly
   - Reads file contents and includes in prompt

3. **Frontend** (`client/src/hooks/useSocket.ts`)
   - Manages pinned files UI state
   - Sends pinned_files in both user_message and group_message events

### Metadata Already Used For

From existing codebase:
- `in_reply_to` - Phase 80.7 reply threading
- `mcp_agent` - MCP agent identification
- `icon` - Agent icon for UI
- `role` - Agent role display

---

## Impact Assessment

### Before Fix
- ❌ Pinned files lost on server restart
- ❌ Chat history incomplete (missing file context)
- ❌ Agents can't see what files user was working with

### After Fix
- ✅ Pinned files persisted to `groups.json`
- ✅ Complete chat history with file context
- ✅ Future: Agents can use pinned files for better context

---

## Next Steps (Future Enhancements)

### Phase 81: Use Pinned Files in Agent Context

**Current Flow:**
```
user message → extract pinned_files → store in metadata → [NOT USED BY AGENTS]
```

**Proposed Flow:**
```
user message → extract pinned_files → store in metadata → build_pinned_context() → pass to agents
```

**Implementation:**
```python
# In group_message_handler.py, around line 546
if pinned_files:
    # Build context from pinned files (similar to user_message_handler.py)
    pinned_context = await build_pinned_context(pinned_files)
    context_parts.append(f"## PINNED FILES\n{pinned_context}")
```

### Phase 82: Semantic Search in Pinned Files

Use Qdrant to find relevant chunks within pinned files instead of truncating:

```python
# Instead of reading full file and truncating
for pf in pinned_files[:3]:
    content = read_file(pf['path'])[:3000]  # ❌ Naive truncation

# Use semantic search
relevant_chunks = await qdrant_client.search(
    collection_name="files",
    query_vector=query_embedding,
    query_filter={"file_path": {"$in": [pf['path'] for pf in pinned_files]}},
    limit=10
)
```

---

## Files Modified

1. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`
   - Added `pinned_files = data.get('pinned_files', [])` (line 373)
   - Added `metadata={'pinned_files': pinned_files}` to send_message call (line 395)

---

## Conclusion

The fix is **minimal and surgical**:
- ✅ 2 lines changed
- ✅ No breaking changes
- ✅ Backward compatible (empty metadata for old messages)
- ✅ Follows existing patterns (metadata already used for other fields)

The infrastructure for storing and loading metadata was already correct. The only missing piece was extracting `pinned_files` from the request and passing it to `send_message()`.

**Status:** Ready for testing and deployment.
