# Claude Code Session Bridge - Proposal

**Phase:** 93.7 (proposed)
**Date:** 2026-01-25
**Status:** CONCEPT

---

## Problem Statement

Two Claude Code instances (Opus, Big Pickle) работают параллельно но:
- Не знают о контексте друг друга
- Нужно вручную передавать информацию
- Теряется время на "введение в курс дела"

---

## Proposed Solution: Session Bridge via MCP

### Architecture

```
┌─────────────────┐     MCP Tools      ┌─────────────────┐
│   Claude Opus   │◄──────────────────►│  VETKA Server   │
│   (Session A)   │                    │    :5001        │
└─────────────────┘                    │                 │
                                       │  ┌───────────┐  │
┌─────────────────┐     MCP Tools      │  │ Session   │  │
│   Big Pickle    │◄──────────────────►│  │ Bridge    │  │
│   (Session B)   │                    │  │ Storage   │  │
└─────────────────┘                    │  └───────────┘  │
                                       │                 │
                                       │  CAM + Engram   │
                                       │  + ELISION      │
                                       └─────────────────┘
```

### New MCP Tools Needed

#### 1. `vetka_session_handoff`
```json
{
  "name": "vetka_session_handoff",
  "description": "Create compressed session context for handoff to another Claude Code instance",
  "parameters": {
    "session_id": "Current session identifier",
    "target_tokens": "Target token count for compressed context (default: 4000)",
    "include_todos": "Include todo list state",
    "include_files_modified": "List files changed this session",
    "priority_topics": "Topics to prioritize in compression"
  },
  "returns": {
    "handoff_id": "UUID for retrieval",
    "compressed_context": "ELISION-compressed session summary",
    "key_decisions": "List of key decisions made",
    "open_tasks": "Pending work items",
    "files_modified": "Files changed with summaries"
  }
}
```

#### 2. `vetka_session_receive`
```json
{
  "name": "vetka_session_receive",
  "description": "Receive handoff context from another Claude Code session",
  "parameters": {
    "handoff_id": "UUID from session_handoff (optional)",
    "latest": "Get latest handoff if no ID provided"
  },
  "returns": {
    "context": "Decompressed session context",
    "sender_session": "Who created this handoff",
    "timestamp": "When it was created",
    "continuation_prompt": "Suggested prompt to continue work"
  }
}
```

#### 3. `vetka_session_message`
```json
{
  "name": "vetka_session_message",
  "description": "Leave async message for another Claude Code session",
  "parameters": {
    "target_session": "Session ID or 'all' for broadcast",
    "message": "Message content",
    "priority": "normal | urgent | fyi",
    "context_attachment": "Optional context to attach"
  }
}
```

#### 4. `vetka_session_messages_read`
```json
{
  "name": "vetka_session_messages_read",
  "description": "Read messages left by other sessions",
  "parameters": {
    "since": "Timestamp to read from",
    "limit": "Max messages to return"
  }
}
```

---

## Auto-Generated Startup Context

### Trigger: CLAUDE.md Update

Add to `~/.claude/CLAUDE.md`:

```markdown
## Session Startup Protocol

On session start:
1. Call `vetka_session_receive(latest=true)` to get any pending handoffs
2. Call `vetka_session_messages_read()` to check for messages
3. If handoff exists, acknowledge and continue work
4. If messages exist, process and respond

## Session End Protocol

Before ending significant work:
1. Call `vetka_session_handoff()` with summary of progress
2. Leave messages for other sessions if coordination needed
```

### Auto-Report Generation

Configure VETKA to generate periodic reports:

```python
# data/config.json
{
  "session_bridge": {
    "enabled": true,
    "auto_handoff_trigger": {
      "on_major_commit": true,
      "on_phase_complete": true,
      "every_n_minutes": 30,
      "on_explicit_request": true
    },
    "handoff_config": {
      "target_tokens": 4000,
      "include_todos": true,
      "include_files_modified": true,
      "compression_level": "standard"
    },
    "storage_location": "data/session_handoffs/"
  }
}
```

---

## Implementation Steps

### Phase 1: Storage Layer
- [ ] Create `data/session_handoffs/` directory structure
- [ ] Implement handoff JSON schema
- [ ] Add cleanup for old handoffs (>24h)

### Phase 2: MCP Tools
- [ ] `vetka_session_handoff` - create compressed context
- [ ] `vetka_session_receive` - retrieve handoff
- [ ] `vetka_session_message` - async messaging
- [ ] `vetka_session_messages_read` - read messages

### Phase 3: Auto-Generation
- [ ] Hook into git commit to trigger handoff
- [ ] Add phase completion detection
- [ ] Implement token-budget compression

### Phase 4: CLAUDE.md Integration
- [ ] Update global CLAUDE.md with protocol
- [ ] Add session startup/end instructions
- [ ] Create continuation prompt templates

---

## Example Flow

### Session A (Opus) - Ending Work

```
User: "Заканчиваем на сегодня"

Opus: [Calls vetka_session_handoff]
→ Creates handoff with:
  - Phase 93.6 completed
  - Group chat 400 fix applied
  - MCP memory tools added
  - Next: Test group chat in UI

Opus: "Создал handoff для Big Pickle. Ключевые моменты:
- MARKER_93.6 fix применен
- 3 новых MCP tools для памяти
- Следующий шаг: тестирование в UI"
```

### Session B (Big Pickle) - Starting Work

```
[On startup, CLAUDE.md instructs to check for handoffs]

Big Pickle: [Calls vetka_session_receive]
→ Gets context from Opus session

Big Pickle: "Получил контекст от Opus:
- Phase 93.6 завершена
- Нужно протестировать group chat в UI
- Могу продолжить отсюда"
```

---

## Token Budget Strategy

### Compression Levels

| Level | Tokens | Use Case |
|-------|--------|----------|
| Minimal | 1000 | Quick status check |
| Standard | 4000 | Full handoff |
| Detailed | 8000 | Complex projects |
| Full | 16000 | Critical handoffs |

### What to Include

**Always:**
- Current phase/task
- Key decisions made
- Open todos
- Critical files modified

**If space permits:**
- Code snippets for key changes
- Error messages encountered
- User preferences applied

**Optional:**
- Full conversation summary
- All files read
- Performance metrics

---

## Security Considerations

- Handoffs stored locally only (not sent to external APIs)
- No API keys or secrets in handoff content
- Session IDs are UUIDs (no user data)
- Auto-cleanup prevents data accumulation

---

## Future Enhancements

1. **Real-time sync** via WebSocket between sessions
2. **Priority queue** for urgent handoffs
3. **Conflict resolution** when both sessions modify same file
4. **Session clustering** for project-based grouping
5. **Analytics** on session collaboration patterns

---

**Status:** PROPOSAL - Awaiting Review
**Next Steps:**
1. User approval
2. Phase 93.7 planning
3. Implementation

---

*"Два полководца должны знать о маневрах друг друга"* - Big Pickle
