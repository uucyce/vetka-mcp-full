# 📡 PHASE 56: API REFERENCE

**Complete REST + Socket.IO API documentation**

---

## 🔄 REST API ENDPOINTS

### Model Phonebook (`/api/models/`)

#### List All Models
```
GET /api/models
```

**Response:**
```json
{
  "models": [
    {
      "id": "qwen2:7b",
      "name": "Qwen 2 7B",
      "provider": "ollama",
      "type": "local",
      "capabilities": ["code", "reasoning"],
      "context_window": 8192,
      "cost_per_1k": 0.0,
      "rate_limit": 100,
      "rating": 0.80,
      "available": true,
      "last_health_check": "2026-01-09T12:30:45.123456"
    },
    // ... more models
  ],
  "count": 6
}
```

---

#### List Available Models
```
GET /api/models/available
```

**Response:** Same as above, but only available models.

---

#### List Local Models (Ollama)
```
GET /api/models/local
```

**Response:** Only type=`"local"` models.

---

#### List Free Models
```
GET /api/models/free
```

**Response:** type=`"local"` OR type=`"cloud_free"`

---

#### Get Favorites
```
GET /api/models/favorites
```

**Response:**
```json
{
  "models": [
    { /* ModelEntry */ }
  ]
}
```

---

#### Get Recently Used
```
GET /api/models/recent
```

**Response:** Last 10 used models.

---

#### Add to Favorites
```
POST /api/models/favorites/{model_id}
```

**Example:**
```
POST /api/models/favorites/qwen2:7b
```

**Response:**
```json
{
  "success": true
}
```

---

#### Remove from Favorites
```
DELETE /api/models/favorites/{model_id}
```

---

#### Add API Key
```
POST /api/models/keys
Content-Type: application/json

{
  "provider": "openrouter",
  "key": "sk-or-v1-abc123..."
}
```

**Response:**
```json
{
  "success": true,
  "provider": "openrouter"
}
```

---

#### Remove API Key
```
DELETE /api/models/keys/{provider}
```

**Example:**
```
DELETE /api/models/keys/openrouter
```

---

#### Auto-Select Best Model
```
GET /api/models/select?task_type=code&context_size=8192&prefer_local=true&prefer_free=true
```

**Query Parameters:**
- `task_type` (required): `"code"`, `"reasoning"`, `"chat"`, `"vision"`, `"embeddings"`
- `context_size` (optional, default=4096): Minimum context window
- `prefer_local` (optional, default=true): Prefer free local models
- `prefer_free` (optional, default=true): Prefer free models

**Response:**
```json
{
  "model": {
    "id": "deepseek-coder:6.7b",
    "name": "DeepSeek Coder 6.7B",
    "provider": "ollama",
    "type": "local",
    "capabilities": ["code"],
    "context_window": 16384,
    "rating": 0.82,
    "available": true
  }
}
```

**Error (no suitable model):**
```json
{
  "detail": "No suitable model found"
}
```

---

#### Check Model Health
```
POST /api/models/health/{model_id}
```

**Example:**
```
POST /api/models/health/qwen2:7b
```

**Response:**
```json
{
  "model_id": "qwen2:7b",
  "available": true
}
```

---

### Group Chat (`/api/groups/`)

#### List All Groups
```
GET /api/groups
```

**Response:**
```json
{
  "groups": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Build Async Runtime",
      "description": "Architecture & implementation",
      "admin_id": "@pm",
      "participants": {
        "@pm": {
          "agent_id": "@pm",
          "model_id": "llama-405b",
          "role": "admin",
          "display_name": "Project Manager",
          "permissions": ["read", "write"]
        },
        "@rust_dev": {
          "agent_id": "@rust_dev",
          "model_id": "deepseek-coder:6.7b",
          "role": "worker",
          "display_name": "Rust Dev",
          "permissions": ["read", "write"]
        }
      },
      "message_count": 42,
      "project_id": "vetka-tree-123",
      "created_at": "2026-01-09T12:00:00"
    }
  ]
}
```

---

#### Create Group
```
POST /api/groups
Content-Type: application/json

{
  "name": "Build Async Runtime",
  "description": "Architecture & implementation",
  "admin_agent_id": "@pm",
  "admin_model_id": "llama-405b",
  "admin_display_name": "Project Manager",
  "project_id": "vetka-tree-123"
}
```

**Response:**
```json
{
  "group": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Build Async Runtime",
    // ... full group object
  }
}
```

---

#### Get Group by ID
```
GET /api/groups/{group_id}
```

**Response:**
```json
{
  "group": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Build Async Runtime",
    // ... full group object
  }
}
```

**Error (not found):**
```json
{
  "detail": "Group not found"
}
```

---

#### Add Participant
```
POST /api/groups/{group_id}/participants
Content-Type: application/json

{
  "agent_id": "@rust_dev",
  "model_id": "deepseek-coder:6.7b",
  "display_name": "Rust Developer",
  "role": "worker"
}
```

**Response:**
```json
{
  "success": true
}
```

**Valid roles:** `"admin"`, `"worker"`, `"reviewer"`, `"observer"`

---

#### Remove Participant
```
DELETE /api/groups/{group_id}/participants/{agent_id}
```

**Example:**
```
DELETE /api/groups/550e8400-e29b-41d4-a716-446655440000/participants/%40rust_dev
```

**Note:** URL-encode the `@` sign as `%40`

**Response:**
```json
{
  "success": true
}
```

---

#### Get Messages
```
GET /api/groups/{group_id}/messages?limit=50
```

**Query Parameters:**
- `limit` (optional, default=50): Number of recent messages

**Response:**
```json
{
  "messages": [
    {
      "id": "msg-123",
      "group_id": "550e8400-e29b-41d4-a716-446655440000",
      "sender_id": "@pm",
      "content": "@rust_dev fix the async issue @qa review when done",
      "mentions": ["rust_dev", "qa"],
      "message_type": "chat",
      "metadata": {},
      "created_at": "2026-01-09T12:30:45"
    },
    {
      "id": "msg-124",
      "group_id": "550e8400-e29b-41d4-a716-446655440000",
      "sender_id": "@rust_dev",
      "content": "Fixed! Ready for review.",
      "mentions": [],
      "message_type": "chat",
      "metadata": {},
      "created_at": "2026-01-09T12:35:10"
    }
  ]
}
```

---

#### Send Message
```
POST /api/groups/{group_id}/messages
Content-Type: application/json

{
  "sender_id": "@pm",
  "content": "@rust_dev fix the async issue @qa review when done",
  "message_type": "chat"
}
```

**Message types:** `"chat"`, `"task"`, `"artifact"`, `"system"`

**Response:**
```json
{
  "message": {
    "id": "msg-123",
    "group_id": "550e8400-e29b-41d4-a716-446655440000",
    "sender_id": "@pm",
    "content": "@rust_dev fix the async issue @qa review when done",
    "mentions": ["rust_dev", "qa"],
    "message_type": "chat",
    "metadata": {},
    "created_at": "2026-01-09T12:30:45"
  }
}
```

---

#### Assign Task
```
POST /api/groups/{group_id}/tasks
Content-Type: application/json

{
  "assigner_id": "@pm",
  "assignee_id": "@rust_dev",
  "description": "Implement async scheduler with proper error handling",
  "dependencies": ["@qa-review"]
}
```

**Response:**
```json
{
  "task": {
    "id": "task-456",
    "group_id": "550e8400-e29b-41d4-a716-446655440000",
    "assigned_by": "@pm",
    "assigned_to": "@rust_dev",
    "description": "Implement async scheduler with proper error handling",
    "status": "pending",
    "dependencies": ["@qa-review"],
    "created_at": "2026-01-09T12:40:00"
  }
}
```

**Error (not admin):**
```json
{
  "detail": "Failed to assign task"
}
```

---

## 🔌 SOCKET.IO EVENTS

### Event Types (TypeScript)

```typescript
interface ServerToClientEvents {
    // === PHASE 56: GROUP CHAT ===
    group_created: (data: GroupCreatedEvent) => void
    group_joined: (data: GroupJoinedEvent) => void
    group_left: (data: GroupLeftEvent) => void
    group_message: (data: GroupMessageEvent) => void
    group_typing: (data: GroupTypingEvent) => void
    agent_response: (data: AgentResponseEvent) => void
    task_created: (data: TaskCreatedEvent) => void
    model_status: (data: ModelStatusEvent) => void

    // === EXISTING ===
    tree_updated: (data: TreeUpdatedEvent) => void
    // ... other existing events
}

interface ClientToServerEvents {
    // === PHASE 56: GROUP CHAT ===
    join_group: (data: JoinGroupRequest) => void
    leave_group: (data: LeaveGroupRequest) => void
    group_message: (data: SendGroupMessageRequest) => void
    group_typing: (data: SendTypingIndicatorRequest) => void

    // === EXISTING ===
    request_tree: () => void
    // ... other existing events
}
```

---

### Server → Client Events

#### Group Created
```javascript
socket.on('group_created', (data) => {
    console.log(`Group created: ${data.name}`);
    // {
    //   "id": "550e8400-e29b-41d4-a716-446655440000",
    //   "name": "Build Async Runtime",
    //   "admin_id": "@pm",
    //   "participants": { ... }
    // }
});
```

---

#### Group Joined
```javascript
socket.on('group_joined', (data) => {
    console.log(`${data.participant.agent_id} joined`);
    // {
    //   "group_id": "550e8400-e29b-41d4-a716-446655440000",
    //   "participant": {
    //     "agent_id": "@rust_dev",
    //     "model_id": "deepseek-coder:6.7b",
    //     "role": "worker",
    //     "display_name": "Rust Dev"
    //   }
    // }
});
```

---

#### Group Left
```javascript
socket.on('group_left', (data) => {
    console.log(`${data.agent_id} left`);
    // {
    //   "group_id": "550e8400-e29b-41d4-a716-446655440000",
    //   "agent_id": "@rust_dev"
    // }
});
```

---

#### Group Message
```javascript
socket.on('group_message', (data) => {
    console.log(`${data.sender_id}: ${data.content}`);
    // {
    //   "id": "msg-123",
    //   "group_id": "550e8400-e29b-41d4-a716-446655440000",
    //   "sender_id": "@pm",
    //   "content": "@rust_dev fix the async issue",
    //   "mentions": ["rust_dev"],
    //   "message_type": "chat",
    //   "created_at": "2026-01-09T12:30:45"
    // }
});
```

---

#### Group Typing
```javascript
socket.on('group_typing', (data) => {
    console.log(`${data.agent_id} is typing...`);
    // {
    //   "group_id": "550e8400-e29b-41d4-a716-446655440000",
    //   "agent_id": "@rust_dev"
    // }
});
```

---

#### Agent Response
```javascript
socket.on('agent_response', (data) => {
    console.log(`${data.agent_id}: ${data.content}`);
    // {
    //   "agent_id": "@rust_dev",
    //   "content": "Fixed! Ready for review.",
    //   "status": "done"
    // }
});
```

---

#### Task Created
```javascript
socket.on('task_created', (data) => {
    console.log(`Task: ${data.description}`);
    // {
    //   "id": "task-456",
    //   "group_id": "550e8400-e29b-41d4-a716-446655440000",
    //   "assigned_to": "@rust_dev",
    //   "description": "Implement async scheduler",
    //   "status": "pending"
    // }
});
```

---

#### Model Status
```javascript
socket.on('model_status', (data) => {
    console.log(`${data.model_id}: ${data.available ? 'online' : 'offline'}`);
    // {
    //   "model_id": "qwen2:7b",
    //   "available": true
    // }
});
```

---

### Client → Server Events

#### Join Group
```javascript
socket.emit('join_group', {
    group_id: '550e8400-e29b-41d4-a716-446655440000'
});
```

---

#### Leave Group
```javascript
socket.emit('leave_group', {
    group_id: '550e8400-e29b-41d4-a716-446655440000'
});
```

---

#### Send Message
```javascript
socket.emit('group_message', {
    group_id: '550e8400-e29b-41d4-a716-446655440000',
    sender_id: '@pm',
    content: '@rust_dev fix the async issue @qa review when done'
});
```

---

#### Send Typing Indicator
```javascript
socket.emit('group_typing', {
    group_id: '550e8400-e29b-41d4-a716-446655440000',
    agent_id: '@pm'
});
```

---

## 🔐 Error Responses

### HTTP Errors

#### 400 Bad Request
```json
{
  "detail": "Invalid data format" | "Missing group_id" | "Content too long"
}
```

#### 404 Not Found
```json
{
  "detail": "Group not found" | "Model not found" | "No suitable model found"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## 📝 Usage Examples

### Python Client
```python
import httpx
import json

BASE_URL = "http://localhost:5001"

async def create_group():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/api/groups",
            json={
                "name": "Build Async Runtime",
                "admin_agent_id": "@pm",
                "admin_model_id": "llama-405b",
                "admin_display_name": "Project Manager"
            }
        )
        group = resp.json()["group"]
        print(f"Created group: {group['id']}")
        return group["id"]

async def send_message(group_id: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/api/groups/{group_id}/messages",
            json={
                "sender_id": "@pm",
                "content": "@rust_dev fix the async issue"
            }
        )
        message = resp.json()["message"]
        print(f"Message mentions: {message['mentions']}")

# Run
import asyncio
group_id = asyncio.run(create_group())
asyncio.run(send_message(group_id))
```

---

### JavaScript/TypeScript Client
```typescript
import { io } from 'socket.io-client';

const socket = io('http://localhost:5001');

// Join group
socket.emit('join_group', {
    group_id: 'group-123'
});

// Listen for messages
socket.on('group_message', (message) => {
    console.log(`${message.sender_id}: ${message.content}`);
    console.log(`Mentions: ${message.mentions.join(', ')}`);
});

// Send message
socket.emit('group_message', {
    group_id: 'group-123',
    sender_id: '@user',
    content: '@rust_dev @qa let\'s sync on the design'
});
```

---

## 🎯 Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| All | 100 req/sec | Per client IP |
| `/api/models/health` | 1 req/10sec | Per model |
| `/api/groups/*/messages` | 10 msg/sec | Per group |

---

**Generated:** 2026-01-09
**Status:** Complete
