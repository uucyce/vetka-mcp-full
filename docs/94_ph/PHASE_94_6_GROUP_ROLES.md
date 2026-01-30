# Phase 94.6: Group Chat Roles System

**Date:** 2026-01-26
**Status:** RESEARCH COMPLETE

---

## 1. ROLE DEFINITIONS

**File:** `src/services/group_chat_manager.py:24-28`

```python
class GroupRole(Enum):
    ADMIN = "admin"      # Can assign tasks, manage group
    WORKER = "worker"    # Can execute tasks
    REVIEWER = "reviewer" # Can review/approve
    OBSERVER = "observer" # Read-only (CANNOT respond)
```

---

## 2. GROUP CONFIGURATION

**Storage:** `data/groups.json`

```json
{
  "id": "uuid",
  "name": "Group Name",
  "admin_id": "@Architect",
  "participants": {
    "@PM": {
      "agent_id": "@PM",
      "model_id": "openai/gpt-4o",
      "role": "admin",
      "display_name": "PM (GPT-4o)",
      "permissions": ["read", "write"]
    },
    "@Dev": {
      "agent_id": "@Dev",
      "model_id": "deepseek/deepseek-r1:free",
      "role": "worker",
      "display_name": "Dev (DeepSeek)"
    }
  },
  "last_responder_id": "@PM",
  "last_responder_decay": 0
}
```

---

## 3. AGENT SELECTION PRIORITY

**File:** `src/services/group_chat_manager.py:165-358`

Selection evaluated in order:

### Priority 1: Reply Routing (Phase 80.7)
```python
if reply_to_id:
    find original sender → route to that agent only
```

### Priority 2: @mentions (Phase 80.31)
```python
# Regex: @([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)
# Matches: @gpt-5.2-chat, @deepseek/deepseek-r1:free, @PM
if @mention found:
    route to mentioned participant
```

### Priority 3: Smart Reply Decay (Phase 80.28)
```python
if last_responder_id exists AND decay < threshold:
    route to last_responder  # Continues conversation
```

### Priority 4: MCP Agent Isolation (Phase 80.6)
```python
if sender is agent AND no explicit @mention:
    NO auto-response  # Prevents cascade
```

### Priority 5: Commands
| Command | Behavior |
|---------|----------|
| `/solo` | Pick first participant |
| `/team` | Select all non-observers |
| `/round` | Sequential: PM→Architect→Dev→QA |

### Priority 6: Keyword Matching
| Agent Type | Keywords |
|------------|----------|
| PM | plan, task, scope, timeline, requirements |
| Architect | architecture, design, system, pattern |
| Dev | code, implement, function, class, debug |
| QA | test, bug, review, verify, coverage |

### Priority 7: Default Fallback
```python
ADMIN → first WORKER → first participant
(always skip OBSERVER and sender)
```

---

## 4. MESSAGE BROADCASTING

**File:** `src/api/handlers/group_message_handler.py:530-977`

### Flow:
```
1. User sends message
   ↓
2. Store in group via manager.send_message()
   ↓
3. Broadcast to room group_{group_id}
   ↓
4. select_responding_agents() determines recipients
   ↓
5. WHILE LOOP (not for) - allows dynamic addition
   ↓
6. Per agent:
   - emit group_typing
   - call orchestrator (2min timeout)
   - emit group_stream_start/end
   - store response
   - CHECK response for @mentions → add to queue
   ↓
7. Safety: max 10 agents per message
```

### Chain Context
```python
previous_outputs = {}
for agent in agents:
    response = call_agent(agent, previous_outputs)
    previous_outputs[agent.id] = response
```

---

## 5. ROLE ENFORCEMENT

### OBSERVER Cannot Respond
```python
# group_chat_manager.py:select_responding_agents
if participant.role == GroupRole.OBSERVER:
    continue  # Skip
```

### Only ADMIN Can Assign Tasks
```python
# group_chat_manager.py:assign_task (line 746)
if sender_role != GroupRole.ADMIN:
    raise PermissionError
```

### REVIEWER Role
Currently defined but **not actively enforced** in routing logic.

---

## 6. INTEGRATION MARKERS

### MARKER_94.6_ROLE_SYSTEM
`src/services/group_chat_manager.py:24-46`

### MARKER_94.6_AGENT_SELECTION
`src/services/group_chat_manager.py:165-358`

### MARKER_94.6_MESSAGE_BROADCAST
`src/api/handlers/group_message_handler.py:529-977`

### MARKER_94.6_ROLE_ROUTING
`src/api/handlers/group_message_handler.py:717-734`

---

## 7. API ENDPOINTS

### Add Participant
```http
POST /api/groups/{group_id}/participants
{
  "agent_id": "@Dev",
  "model_id": "openai/gpt-4-turbo",
  "display_name": "Dev (GPT-4)",
  "role": "worker"
}
```

### Direct Model Addition (Phase 80.19)
```http
POST /api/groups/{group_id}/models/add-direct
{
  "model_id": "deepseek/deepseek-r1:free",
  "role": "worker"
}
```

### Update Model (Phase 82)
```http
PATCH /api/groups/{group_id}/participants/@agent_id/model
{"model_id": "new-model-id"}
```

---

## 8. DEPENDENCIES FOR MODEL DUPLICATION

For Phase 94.4:

1. **Model stored per-participant** in `participants[].model_id`
2. **Display name** often includes model: "PM (GPT-4o)"
3. **@ mention matching** uses agent_id, model_id, OR display_name
4. **If model duplicated** (direct + OR), need to update:
   - Participant model_id
   - Display name to show source
   - Mention matching logic

---

## 9. KEY PHASES HISTORY

| Phase | Feature |
|-------|---------|
| 56.2 | Memory management (1000 msgs/group) |
| 57.7 | Intelligent agent selection |
| 80.6 | MCP agent isolation |
| 80.7 | Reply routing |
| 80.13 | MCP @mention routing |
| 80.19 | Direct model addition |
| 80.28 | Smart reply decay |
| 80.31 | Full model ID matching |
| 82 | Model reassignment |

---

**Generated by:** Explore Agent
**Phase:** 94.6
