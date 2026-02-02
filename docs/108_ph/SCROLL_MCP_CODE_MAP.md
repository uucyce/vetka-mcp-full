# Scroll Button + MCP Persistence - Code Map

Quick reference for debugging and future work.

---

## Scroll Button Flow

### 1. State Management
```typescript
// client/src/components/chat/ChatPanel.tsx:74
const [isAtBottom, setIsAtBottom] = useState(true);
```

### 2. Scroll Detection
```typescript
// client/src/components/chat/ChatPanel.tsx:1097-1110
const handleScroll = useCallback(() => {
  const atBottom = scrollHeight - scrollTop - clientHeight < 50;
  setIsAtBottom(atBottom);
}, [isAtBottom]);
```

### 3. Event Listener (FIXED)
```typescript
// client/src/components/chat/ChatPanel.tsx:1113-1119
useEffect(() => {
  const container = messagesContainerRef.current;
  if (container) {
    container.addEventListener('scroll', handleScroll);
    handleScroll(); // ✅ FIX: Initialize on mount
    return () => container.removeEventListener('scroll', handleScroll);
  }
}, [handleScroll]);
```

---

## MCP Persistence Flow

### 1. Send Message
```python
# src/api/routes/debug_routes.py:1143
@router.post("/mcp/groups/{group_id}/send")
async def send_group_message_from_mcp(...):
    message = await manager.send_message(...)  # ✅ Calls save_to_json()
```

### 2. Save to JSON
```python
# src/services/group_chat_manager.py:680
async def send_message(...):
    group.messages.append(message)
    await self.save_to_json()  # ✅ Auto-save
```

### 3. Load from JSON
```python
# main.py:224
manager = get_group_chat_manager(socketio=sio)
await manager.load_from_json()  # ✅ Load on startup
```

### 4. Frontend Load
```typescript
// client/src/components/chat/ChatPanel.tsx:1000
const response = await fetch(`/api/groups/${groupId}/messages?limit=50`);
```

---

## Key Files

| File | Purpose |
|------|---------|
| `client/src/components/chat/ChatPanel.tsx` | UI + scroll button |
| `src/services/group_chat_manager.py` | Message storage |
| `src/api/routes/group_routes.py` | REST API |
| `data/groups.json` | Persistent storage |

---

## Debug Commands

```bash
# Check saved messages
tail -100 data/groups.json | grep "@claude_mcp"

# Load more via API
curl "http://localhost:5001/api/groups/{id}/messages?limit=200"
```
