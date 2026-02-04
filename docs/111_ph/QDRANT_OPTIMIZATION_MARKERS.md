# Phase 111.18 - Qdrant Optimization Markers Report
**Date:** 2026-02-04
**Agent:** Opus 4.5 Verification
**Status:** VERIFIED

---

## MARKER 1: Blocking Embedding Call

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/qdrant_client.py`
**Lines:** 768-771

**Code:**
```python
# Inside upsert_chat_message() function
try:
    # Get embedding for semantic search
    from src.utils.embedding_service import get_embedding
    embedding = get_embedding(content[:2000])  # Truncate for efficiency
```

**Underlying Embedding Service (src/utils/embedding_service.py:64-66):**
```python
try:
    import ollama
    result = ollama.embeddings(model=self.model, prompt=text)  # SYNC BLOCKING CALL
    embedding = result.get("embedding")
```

**Problem:**
- `upsert_chat_message()` is a **synchronous function** (not async)
- It calls `get_embedding()` which internally calls `ollama.embeddings()` - a **synchronous blocking I/O call**
- When called from async context via `asyncio.create_task()`, this blocks the event loop
- Each message save blocks for 50-200ms while waiting for Ollama API response

**Impact:**
- Message latency increases by embedding generation time
- Event loop starvation under load
- Multiple concurrent messages create embedding queue backlog

**Fix Options:**
1. **Option A - Async Embedding Service:**
```python
async def get_embedding_async(text: str) -> Optional[List[float]]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, get_embedding, text)
```

2. **Option B - Batch Embeddings with Interval Timer:**
- Queue messages without embeddings
- Every 5-10 seconds, batch generate embeddings
- Update Qdrant in single batch upsert

3. **Option C - Background Process:**
- Separate worker process for embeddings
- Use Redis/Queue for message passing

**Priority:** HIGH

---

## MARKER 2: Per-Message Qdrant Save

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/group_chat_manager.py`
**Lines:** 686-704

**Code:**
```python
# Inside send_message() method
# MARKER_103.7_START: Persist user messages to Qdrant for long-term memory
# MARKER_103_GC7: FIXED - wrapped in background task
async def _persist_user_msg_background():
    """Background task for Qdrant persistence - non-blocking."""
    try:
        from src.memory.qdrant_client import upsert_chat_message
        upsert_chat_message(
            group_id=message.group_id,
            message_id=message.id,
            sender_id=message.sender_id,
            content=message.content,
            role="user",
            metadata=message.metadata
        )
    except Exception as e:
        logger.warning(f"[GroupChat] Qdrant upsert failed (non-blocking): {e}")

asyncio.create_task(_persist_user_msg_background())
# MARKER_103.7_END
```

**Problem:**
- `asyncio.create_task()` fires for EVERY message sent
- Even though wrapped in background task, `upsert_chat_message()` is **sync blocking**
- No batch support - each message = 1 embedding + 1 Qdrant upsert
- High-frequency chat = high-frequency Qdrant writes

**Call Frequency:**
- Every `send_message()` call triggers this
- Includes user messages AND agent responses (via separate handler)
- Typical conversation: 10-50 messages = 10-50 individual upserts

**Batch Support:** NONE - each message is individually upserted

**Fix:**
- Implement message queue with interval flush (every 5-10 seconds)
- Batch embeddings: `ollama.embeddings()` supports batch
- Batch upsert: `client.upsert(points=[point1, point2, ...])` already supports batch

**Priority:** HIGH

---

## MARKER 3: _persist_to_qdrant_background()

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`
**Lines:** 1053-1086

**Code:**
```python
# MARKER_103.7_START: Persist agent response to Qdrant for long-term memory
# MARKER_103_GC7: FIXED - wrapped in background task to avoid blocking
import uuid as uuid_module
msg_id = str(uuid_module.uuid4())

async def _persist_to_qdrant_background():
    """Background task for Qdrant persistence - non-blocking."""
    try:
        from src.memory.qdrant_client import upsert_chat_message
        upsert_chat_message(
            group_id=group_id,
            message_id=msg_id,
            sender_id=agent_id,
            content=response_text,
            role="assistant",
            agent=display_name,
            model=model_id,
            metadata={
                "in_reply_to": user_message.id if user_message else None,
                "model_source": model_source,  # Phase 111.11
            }
        )
        # Phase 111.18: Removed message_saved emit
        # No frontend listener exists for this event
        # Qdrant persistence continues in background
    except Exception as qdrant_err:
        print(f"[QDRANT] Chat upsert failed (non-blocking): {qdrant_err}")

# Fire-and-forget: don't await, let it run in background
asyncio.create_task(_persist_to_qdrant_background())
# MARKER_103.7_END
```

**What It Does:**
- Persists agent (assistant) responses to Qdrant VetkaGroupChat collection
- Creates new UUID for message ID
- Stores: group_id, message_id, sender_id, content, role, agent, model, metadata
- Generates embedding via `get_embedding()` (blocking inside upsert_chat_message)
- Upserts single point to Qdrant

**Where Called:**
- Inside `handle_group_message()` Socket.IO handler
- After each successful agent response (line 1079)
- Also called from `group_chat_manager.send_message()` for user messages

**Problem:**
- Same issue as MARKER 2: sync blocking embedding in async wrapper
- Duplicate logic between group_chat_manager and group_message_handler
- No deduplication check for already-persisted messages

**Priority:** HIGH

---

## MARKER 4: upsert_chat_message() Function

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/qdrant_client.py`
**Lines:** 732-809

**Signature:**
```python
def upsert_chat_message(
    group_id: str,
    message_id: str,
    sender_id: str,
    content: str,
    role: str = "user",  # "user" or "assistant"
    agent: str = None,
    model: str = None,
    metadata: Dict = None
) -> bool:
```

**Full Function:**
```python
def upsert_chat_message(
    group_id: str,
    message_id: str,
    sender_id: str,
    content: str,
    role: str = "user",  # "user" or "assistant"
    agent: str = None,
    model: str = None,
    metadata: Dict = None
) -> bool:
    """
    Upsert a chat message to VetkaGroupChat collection.
    """
    client = get_qdrant_client()
    if not client or not client.client:
        logger.warning("[Chat] Qdrant not available for chat persistence")
        return False

    try:
        # Get embedding for semantic search
        from src.utils.embedding_service import get_embedding
        embedding = get_embedding(content[:2000])  # Truncate for efficiency

        if not embedding:
            logger.warning("[Chat] Failed to generate embedding")
            return False

        # Generate deterministic point ID from message_id
        import hashlib
        point_id = int(hashlib.md5(message_id.encode()).hexdigest()[:16], 16)

        payload = {
            "group_id": group_id,
            "message_id": message_id,
            "sender_id": sender_id,
            "content": content[:5000],  # Store more content in payload
            "role": role,
            "agent": agent,
            "model": model,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload=payload
        )

        client.client.upsert(
            collection_name=client.COLLECTION_NAMES['chat'],
            points=[point]
        )

        logger.debug(f"[Chat] Upserted message {message_id[:8]} to VetkaGroupChat")
        return True

    except Exception as e:
        logger.warning(f"[Chat] Upsert failed (graceful): {e}")
        return False
```

**Batch Support:**
- **PARTIAL** - The underlying `client.client.upsert(points=[point])` already supports batch
- Function signature does NOT support batch (single message only)
- Would need new function: `upsert_chat_messages_batch(messages: List[Dict]) -> int`

**Recommended Batch Function:**
```python
def upsert_chat_messages_batch(messages: List[Dict]) -> int:
    """
    Batch upsert multiple chat messages to Qdrant.

    Args:
        messages: List of message dicts with keys:
                  group_id, message_id, sender_id, content, role, agent, model, metadata

    Returns:
        Number of successfully upserted messages
    """
    client = get_qdrant_client()
    if not client or not client.client:
        return 0

    # Batch generate embeddings
    from src.utils.embedding_service import get_embedding_service
    svc = get_embedding_service()
    texts = [m['content'][:2000] for m in messages]
    embeddings = svc.get_embedding_batch(texts)

    # Build points
    points = []
    for msg, emb in zip(messages, embeddings):
        if not emb:
            continue
        point_id = int(hashlib.md5(msg['message_id'].encode()).hexdigest()[:16], 16)
        points.append(PointStruct(
            id=point_id,
            vector=emb,
            payload={...}
        ))

    # Single batch upsert
    client.client.upsert(
        collection_name=client.COLLECTION_NAMES['chat'],
        points=points
    )
    return len(points)
```

**Priority:** MEDIUM (enable batch first, then use it)

---

## MARKER 5: create_disk_artifact() Qdrant Integration

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/disk_artifact_service.py`
**Lines:** 114-218

**Current Qdrant Save:** NONE

**Function Overview:**
```python
async def create_disk_artifact(
    name: str,
    content: str,
    artifact_type: str,
    workflow_id: str,
    socketio=None
) -> Optional[str]:
```

- Saves artifact to disk at `artifacts/{sanitized_name}.{ext}`
- Emits `artifact_approval` Socket.IO event
- **No Qdrant persistence** - artifacts are NOT indexed for semantic search

**Where to Add Qdrant Hook (after line 213):**
```python
# After successful disk write and socket emit, add:
# MARKER_111.18: Persist artifact to Qdrant for semantic search
try:
    from src.memory.qdrant_client import QdrantVetkaClient
    client = QdrantVetkaClient()
    if client.client:
        # Queue artifact for batch indexing (non-blocking)
        _artifact_queue.append({
            'artifact_id': artifact_data["artifact_id"],
            'name': safe_name,
            'content': content[:5000],
            'artifact_type': artifact_type,
            'workflow_id': workflow_id,
            'filepath': str(filepath),
        })
except Exception as e:
    logger.warning(f"[DiskArtifact] Qdrant queue failed: {e}")
```

**Recommended Architecture:**
1. Add artifact to queue (non-blocking)
2. Background task processes queue every 10 seconds
3. Batch generates embeddings
4. Batch upserts to VetkaArtifacts collection

**Priority:** MEDIUM (enables artifact semantic search)

---

## MARKER 6: send_message() Full Flow

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/group_chat_manager.py`
**Lines:** 630-708

**Full Save Flow:**

1. **Lock acquisition** (line 642):
```python
async with self._lock:
```

2. **Parse mentions** (line 649):
```python
mentions = await self.parse_mentions(content)
```

3. **Create GroupMessage** (line 657-665):
```python
message = GroupMessage(
    id=str(uuid.uuid4()),
    group_id=group_id,
    sender_id=sender_id,
    content=content,
    mentions=mentions,
    message_type=message_type,
    metadata=metadata or {}
)
```

4. **Append to deque** (line 668):
```python
group.messages.append(message)  # In-memory only
```

5. **Update activity timestamp** (line 671):
```python
group.last_activity = datetime.now()
```

6. **JSON Persistence** (line 684):
```python
await self.save_to_json()  # Writes entire groups.json file
```

7. **Qdrant Persistence** (line 688-703):
```python
asyncio.create_task(_persist_user_msg_background())
```

**JSON vs Qdrant Comparison:**

| Aspect | JSON | Qdrant |
|--------|------|--------|
| When | Every message | Every message |
| What | All groups, all messages | Single message |
| Blocking | Async file I/O | Sync embedding + async upsert |
| Batch | Full file rewrite | No (1 message = 1 upsert) |
| Search | None | Semantic search |
| Recovery | Full restore | Partial (semantic only) |

**Problems Identified:**
1. JSON: Writes ENTIRE groups.json on every message (inefficient for large groups)
2. Qdrant: Sync embedding blocks event loop
3. No coordination: JSON and Qdrant writes happen independently
4. No transaction: JSON success + Qdrant failure = inconsistent state

**Priority:** HIGH

---

## SUMMARY TABLE

| # | Marker | File | Lines | Status | Priority | Fix Required |
|---|--------|------|-------|--------|----------|--------------|
| 1 | Blocking Embedding | qdrant_client.py | 768-771 | VERIFIED | HIGH | Async wrapper or batch |
| 2 | Per-Message Save | group_chat_manager.py | 686-704 | VERIFIED | HIGH | Interval batch queue |
| 3 | _persist_to_qdrant_background | group_message_handler.py | 1053-1086 | VERIFIED | HIGH | Use shared queue |
| 4 | upsert_chat_message | qdrant_client.py | 732-809 | VERIFIED | MEDIUM | Add batch function |
| 5 | Disk Artifact Hook | disk_artifact_service.py | 114-218 | NO HOOK | MEDIUM | Add Qdrant indexing |
| 6 | send_message Flow | group_chat_manager.py | 630-708 | VERIFIED | HIGH | Optimize JSON + batch Qdrant |

---

## RECOMMENDED ARCHITECTURE

### Phase 1: Interval-Based Batch Queue

```python
# src/memory/qdrant_batch_manager.py

class QdrantBatchManager:
    """Manages batched Qdrant operations with interval flush."""

    def __init__(self, flush_interval: float = 5.0, max_batch_size: int = 50):
        self._message_queue: List[Dict] = []
        self._artifact_queue: List[Dict] = []
        self._lock = asyncio.Lock()
        self._flush_interval = flush_interval
        self._max_batch_size = max_batch_size
        self._flush_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start background flush task."""
        self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop(self):
        """Stop and flush remaining items."""
        if self._flush_task:
            self._flush_task.cancel()
            await self._flush_pending()

    async def queue_message(self, message: Dict):
        """Add message to queue (non-blocking)."""
        async with self._lock:
            self._message_queue.append(message)
            # Immediate flush if batch full
            if len(self._message_queue) >= self._max_batch_size:
                asyncio.create_task(self._flush_messages())

    async def queue_artifact(self, artifact: Dict):
        """Add artifact to queue (non-blocking)."""
        async with self._lock:
            self._artifact_queue.append(artifact)

    async def _flush_loop(self):
        """Periodic flush every interval."""
        while True:
            await asyncio.sleep(self._flush_interval)
            await self._flush_pending()

    async def _flush_pending(self):
        """Flush all queued items."""
        await self._flush_messages()
        await self._flush_artifacts()

    async def _flush_messages(self):
        """Batch upsert queued messages."""
        async with self._lock:
            if not self._message_queue:
                return
            batch = self._message_queue[:self._max_batch_size]
            self._message_queue = self._message_queue[self._max_batch_size:]

        # Run in executor to not block
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._upsert_messages_sync, batch)

    def _upsert_messages_sync(self, messages: List[Dict]):
        """Sync batch upsert (runs in executor)."""
        from src.memory.qdrant_client import get_qdrant_client
        from src.utils.embedding_service import get_embedding_service

        client = get_qdrant_client()
        if not client or not client.client:
            return

        # Batch embeddings
        svc = get_embedding_service()
        texts = [m['content'][:2000] for m in messages]
        embeddings = svc.get_embedding_batch(texts)

        # Build points
        points = []
        for msg, emb in zip(messages, embeddings):
            if not emb:
                continue
            point_id = int(hashlib.md5(msg['message_id'].encode()).hexdigest()[:16], 16)
            points.append(PointStruct(
                id=point_id,
                vector=emb,
                payload=msg
            ))

        if points:
            client.client.upsert(
                collection_name='VetkaGroupChat',
                points=points
            )
            logger.info(f"[QdrantBatch] Flushed {len(points)} messages")
```

### Phase 2: Artifact Trigger Integration

```python
# In disk_artifact_service.py, after line 213:
from src.memory.qdrant_batch_manager import get_batch_manager

batch_mgr = get_batch_manager()
await batch_mgr.queue_artifact({
    'artifact_id': artifact_data["artifact_id"],
    'name': safe_name,
    'content': content[:5000],
    'artifact_type': artifact_type,
    'workflow_id': workflow_id,
    'filepath': str(filepath),
})
```

### Benefits

1. **Non-blocking**: All operations are async
2. **Efficient**: Batch embeddings (1 call for 50 texts vs 50 calls)
3. **Reduced load**: 1 upsert per batch vs per message
4. **Scalable**: Queue handles burst traffic
5. **Consistent**: Single source of truth for Qdrant writes

---

## NEXT STEPS

1. [ ] Create `src/memory/qdrant_batch_manager.py` with interval flush
2. [ ] Add `upsert_chat_messages_batch()` to qdrant_client.py
3. [ ] Update `group_chat_manager.send_message()` to use queue
4. [ ] Update `group_message_handler._persist_to_qdrant_background()` to use queue
5. [ ] Add artifact indexing hook in disk_artifact_service.py
6. [ ] Initialize batch manager in app startup
7. [ ] Add flush on app shutdown
8. [ ] Create tests for batch operations
