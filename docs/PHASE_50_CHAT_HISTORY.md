# Phase 50: Chat History + Sidebar UI

**Status**: ✅ COMPLETE
**Date**: 2026-01-06
**Focus**: Persistent chat history storage and sidebar UI for conversation management

## Overview

Phase 50 implements persistent chat history management for VETKA, allowing users to:
- Save chat conversations automatically
- Browse conversation history via sidebar
- Load previous chats and resume conversations
- Search and manage chat history
- Export chat conversations

## Architecture

### Backend Components

#### 1. ChatHistoryManager (`src/chat/chat_history_manager.py`)
- **Purpose**: Manage persistent chat storage
- **Storage**: JSON file at `data/chat_history.json`
- **Features**:
  - Get or create chats per file path
  - Add messages to chats
  - Retrieve message history
  - Search messages across chats
  - Export chats
  - Delete chats
  - Organize by updated_at timestamp (MRU)

**Key Methods**:
```python
# Create/get chat for a file
chat_id = manager.get_or_create_chat(file_path)

# Add message to chat
manager.add_message(chat_id, {
    "role": "user|assistant",
    "content": "message text",
    "agent": "Dev|PM|QA",
    "model": "model_name"
})

# Get all chats (sorted by MRU)
chats = manager.get_all_chats()

# Load chat history
messages = manager.get_chat_messages(chat_id)

# Search messages
results = manager.search_messages("query")

# Export chat
json_str = manager.export_chat(chat_id)
```

#### 2. API Endpoints (`src/api/routes/chat_history_routes.py`)
Registered at `/api/chats/*`

**Endpoints**:
- `GET /api/chats` - List all chats for sidebar
- `GET /api/chats/{chat_id}` - Get chat with full message history
- `POST /api/chats/{chat_id}/messages` - Add message to chat
- `DELETE /api/chats/{chat_id}` - Delete chat
- `GET /api/chats/file/{file_path}` - Get chats for specific file
- `GET /api/chats/search/{query}` - Search messages
- `GET /api/chats/{chat_id}/export` - Export chat as JSON

#### 3. Chat Persistence (`src/api/handlers/handler_utils.py`)
- **Function**: `save_chat_message(node_path, message)`
- **Behavior**: Automatically saves all user and assistant messages to history
- **Integration**: Called in `user_message_handler.py` after each response
- **Fallback**: Errors don't fail the handler (graceful degradation)

**Data Flow**:
```
User sends message
    ↓
user_message_handler receives it
    ↓
Process request and get response
    ↓
save_chat_message() called for user message
    ↓
save_chat_message() called for assistant response
    ↓
ChatHistoryManager stores in data/chat_history.json
```

### Frontend Components

#### 1. ChatSidebar (`client/src/components/chat/ChatSidebar.tsx`)
**Props**:
```typescript
interface ChatSidebarProps {
  isOpen: boolean;                  // Show/hide sidebar
  onSelectChat: (chatId, filePath, fileName) => void;  // Load chat
  currentChatId?: string;           // Highlight active chat
  onClose?: () => void;            // Close sidebar
}
```

**Features**:
- Load chats from `/api/chats` on mount
- Search/filter chats by file name
- Display message count per chat
- Show last updated timestamp (relative: "5m ago", etc.)
- Hover to show delete button
- Refresh button to reload chats
- Responsive dark UI matching VETKA theme

#### 2. ChatPanel Integration
**New State**:
- `showChatHistory` - Toggle sidebar visibility
- `currentChatId` - Track active chat
- `handleSelectChat()` - Load chat from history

**UI Changes**:
- Added 📜 button in header to toggle chat history
- Sidebar slides in from left (280px width)
- Main chat panel adjusts position accordingly
- Works alongside existing Model Directory

**Flow**:
```
User clicks 📜 button
    ↓
ChatSidebar appears with list of chats
    ↓
User clicks a chat
    ↓
handleSelectChat() called
    ↓
Fetch chat messages from /api/chats/{chatId}
    ↓
Clear current chat
    ↓
Load all history messages into state
    ↓
Display messages in ChatPanel
```

## Data Structure

### History File Format (`data/chat_history.json`)
```json
{
  "chats": {
    "chat_uuid_1": {
      "id": "chat_uuid_1",
      "file_path": "/path/to/file.py",
      "file_name": "file.py",
      "created_at": "2026-01-06T18:00:00",
      "updated_at": "2026-01-06T19:00:00",
      "messages": [
        {
          "id": "msg_uuid_1",
          "role": "user",
          "content": "What does this function do?",
          "timestamp": "2026-01-06T18:00:00"
        },
        {
          "id": "msg_uuid_2",
          "role": "assistant",
          "agent": "Dev",
          "model": "deepseek-coder:6.7b",
          "content": "This function calculates...",
          "timestamp": "2026-01-06T18:00:05"
        }
      ]
    }
  },
  "groups": {
    "default": {
      "name": "Default",
      "roles": {
        "PM": "qwen2.5:7b",
        "Dev": "deepseek-coder:6.7b",
        "QA": "llama3.1:8b"
      }
    }
  }
}
```

## Usage Examples

### Backend: Save a message
```python
from src.api.handlers.handler_utils import save_chat_message

save_chat_message("/path/to/file.py", {
    "role": "user",
    "text": "Explain this function",
    "node_id": "node_123"
})

save_chat_message("/path/to/file.py", {
    "role": "assistant",
    "agent": "Dev",
    "model": "deepseek-coder",
    "text": "This function..."
})
```

### Frontend: Load chat history
```typescript
const response = await fetch('/api/chats');
const data = await response.json();
const chats = data.chats;  // Array of chat objects

// Load specific chat
const chatResponse = await fetch(`/api/chats/${chatId}`);
const chat = await chatResponse.json();
chat.messages.forEach(msg => addChatMessage(msg));
```

### Search messages
```typescript
const response = await fetch('/api/chats/search/redux');
const results = await response.json();
// results.results = array of matching messages with context
```

## Testing

Run the comprehensive test suite:
```bash
python3 test_phase50.py
```

**Tests Included**:
1. ✅ ChatHistoryManager creation and operations
2. ✅ Singleton pattern verification
3. ✅ Data persistence to disk
4. ✅ JSON structure validation
5. ✅ Message retrieval and search
6. ✅ Chat export functionality

**All tests passing**: 100% ✓

## File Changes Summary

### New Files Created
- `src/chat/chat_history_manager.py` - Core history manager (260 lines)
- `src/api/routes/chat_history_routes.py` - REST API endpoints (210 lines)
- `client/src/components/chat/ChatSidebar.tsx` - React sidebar component (170 lines)
- `client/src/components/chat/ChatSidebar.css` - Sidebar styling (150 lines)
- `test_phase50.py` - Test suite (220 lines)

### Modified Files
- `src/api/routes/__init__.py` - Register chat_history routes
- `src/api/handlers/handler_utils.py` - Implement save_chat_message
- `client/src/components/chat/ChatPanel.tsx` - Add sidebar integration
- `client/src/components/chat/index.ts` - Export ChatSidebar

### Build Status
- ✅ Backend: Python imports compile successfully
- ✅ Frontend: TypeScript builds without errors
- ✅ All tests pass

## Performance Characteristics

### Storage
- Small files: <1KB per message (JSON overhead included)
- 1000 messages ≈ 150-200 KB
- Efficient JSON format with proper indexing

### Loading
- Get all chats: ~O(n) file read + parse
- Get single chat: O(1) lookup after file loaded
- Search: O(n) message scan (linear, acceptable for <10k messages)
- Future: Can migrate to Qdrant for semantic search

### Memory
- Lazy loading: Only loaded chats stay in memory
- Sidebar: Lightweight list component, rerenders only on updates
- Message history: Loaded on-demand when selected

## Future Enhancements

### Phase 51 Candidates
1. **Qdrant Integration**: Migrate to vector DB for semantic search
2. **Chat Categories**: Organize chats by project, agent type, date range
3. **Export Formats**: PDF, Markdown, CSV export options
4. **Sharing**: Export and share chat transcripts
5. **Analytics**: Chat statistics, agent performance metrics
6. **Pinning**: Mark important chats for quick access
7. **Tagging**: Add custom tags to chats for organization
8. **Full-Text Search**: Elasticsearch-based search UI
9. **Chat Diff**: Compare responses across versions
10. **Conversation Branching**: Fork conversations, explore alternatives

### Known Limitations
- Currently JSON-based (scales to ~50k messages)
- No built-in encryption (consider for sensitive conversations)
- No multi-user isolation (all users share history)
- No rate limiting on API endpoints
- No automatic cleanup/archival policy

## Integration Checklist

- ✅ ChatHistoryManager implemented and tested
- ✅ API routes created and registered
- ✅ Handler integration working
- ✅ ChatSidebar component built
- ✅ ChatPanel integration complete
- ✅ Build verification passed
- ✅ Test suite created and passing
- ✅ Documentation complete

## Related Phases

- **Phase 46**: Streaming support for long responses
- **Phase 49.2**: Chat jitter fix (batched rendering)
- **Phase 48**: Model directory and routing
- **Future Phase 51+**: Qdrant integration, advanced search

## Notes

- Chat history is automatically persisted with no user action required
- Each file path gets its own isolated conversation thread
- Messages are immutable (create new, don't modify existing)
- Graceful error handling ensures chat functionality never breaks
- All timestamps are ISO 8601 format
- UUID for all IDs (chat_id, message_id)
