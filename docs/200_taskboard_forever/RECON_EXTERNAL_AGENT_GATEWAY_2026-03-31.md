# RECON: External Agent Gateway API for TaskBoard

**Task:** `tb_1774956292_51219_1`
**Date:** 2026-03-31
**Phase:** 196.7
**Project:** MCC

---

## 1. Executive Summary

VETKA already has a robust TaskBoard system with **40+ REST API endpoints** across 3 route files, plus **24 MCP tool actions**. However, all access is designed for internal agents only — no authentication, no rate limiting, no external agent onboarding.

The gap between "what exists" and "what Gemini needs" is **authentication + agent registration + a few missing endpoints**. The core TaskBoard infrastructure (SQLite, FTS5 search, claim/complete lifecycle, agent registry) is solid and reusable.

---

## 2. Existing API Endpoints

### 2A. `/api/taskboard/*` — `src/api/routes/taskboard_routes.py`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/taskboard/create` | Create task (50+ params) |
| `GET` | `/api/taskboard/list` | List tasks (status filter, limit 1-500) |
| `POST` | `/api/taskboard/dispatch` | Dispatch to Mycelium pipeline |
| `PATCH` | `/api/taskboard/{task_id}` | Update task fields |
| `GET` | `/api/taskboard/{task_id}` | Get single task |
| `GET` | `/api/taskboard/projects` | List MCC projects for autocomplete |
| `POST` | `/api/taskboard/claim` | Claim task (agent_name, agent_type) |
| `POST` | `/api/taskboard/complete` | Complete task (commit_hash, branch) |

**Bug:** `claim` and `complete` are defined twice (lines 218 and 277). FastAPI uses first match.

### 2B. `/api/tasks/*` — `src/api/routes/task_routes.py`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/tasks` | List tasks + board summary |
| `GET` | `/api/tasks/{task_id}` | Get single task |
| `GET` | `/api/tasks/{task_id}/history` | Status lifecycle history |
| `POST` | `/api/tasks` | Create task (reads `X-Agent-ID` header) |
| `PATCH` | `/api/tasks/{task_id}` | Update task fields |
| `DELETE` | `/api/tasks/{task_id}` | Remove task |
| `POST` | `/api/tasks/dispatch` | Dispatch next pending task |
| `POST` | `/api/tasks/{task_id}/claim` | Claim task for agent |
| `POST` | `/api/tasks/{task_id}/complete` | Mark task completed |
| `POST` | `/api/tasks/{task_id}/close-protocol` | Full protocol close handshake |
| `POST` | `/api/tasks/{task_id}/cancel` | Cancel running/pending task |
| `GET` | `/api/tasks/{task_id}/results` | Pipeline results |
| `GET` | `/api/tasks/active-agents` | Agents with claimed/running tasks |
| `GET` | `/api/tasks/concurrent` | Pipeline concurrency info |
| `POST` | `/api/tasks/cleanup` | Clean up stale tasks |
| `GET` | `/api/tasks/claimable` | **Pending tasks for external agents** |
| `POST` | `/api/tasks/take` | **Find + claim highest-priority task** |

### 2C. `/api/tracker/*` — `src/api/routes/task_tracker_routes.py`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/tracker/cursor-done` | Cursor marks task done |
| `POST` | `/api/tracker/started` | Mark task started |
| `GET` | `/api/tracker/status` | Current tracker state |
| `GET` | `/api/tracker/digest` | Project digest summary |
| `POST` | `/api/tracker/digest/update-phase` | Manually advance phase |

### 2D. MCP Tools — 24 actions

`add`, `list`, `get`, `update`, `remove`, `summary`, `claim`, `complete`, `active_agents`, `merge_request`, `promote_to_main`, `request_qa`, `verify`, `close`, `bulk_close`, `stale_check`, `batch_merge`, `search_fts`, `debrief_skipped`, `backfill_fts`, `context_packet`, `notify`, `notifications`, `ack_notifications`

---

## 3. TaskBoard Core (`src/orchestration/task_board.py` — 4692 lines)

### Key Methods

| Category | Methods |
|----------|---------|
| **CRUD** | `add_task()`, `get_task()`, `update_task()`, `remove_task()`, `get_queue()`, `list_tasks()` |
| **Agent Coordination** | `claim_task()`, `complete_task()`, `get_active_agents()`, `cancel_task()` |
| **Pipeline** | `dispatch_next()`, `dispatch_task()`, `get_next_task()` |
| **Merge & QA** | `merge_request()`, `promote_to_main()`, `verify_task()`, `run_closure_protocol()` |
| **Notifications** | `notify()`, `get_notifications()`, `ack_notifications()` |
| **Search** | `search_fts()`, `stale_check()`, `cleanup_stale()` |
| **Context** | `get_context_packet()`, `auto_complete_by_commit()`, `find_tasks_by_changed_files()` |
| **Stats** | `record_failure()`, `record_pipeline_stats()`, `compute_adjusted_stats()` |

---

## 4. Storage Backend

### Primary: SQLite (`data/task_board.db`)
- **WAL mode** with `busy_timeout=15000`, `synchronous=NORMAL`
- **Schema version 2** with migrations
- **Tables:**
  - `tasks` — id (PK), title, description, priority, status, phase_type, complexity, project_id, assigned_to, agent_type, timestamps, extra (JSON blob)
  - `settings` — key (PK), value (JSON)
  - `meta` — key (PK), value (schema_version)
  - `tasks_fts` — FTS5 full-text search
  - `notifications` — id (PK), source_role, target_role, message, ntype, task_id, read_at, is_read

### Legacy: JSON file (`data/task_board.json`) — auto-migrated on startup

### In-memory cache: `self.tasks: Dict[str, Dict]` — write-through

---

## 5. Current Authentication Model

**There is none.** Authentication is implicit:
- `X-Agent-ID` header (task_routes.py)
- `agent_name` / `agent_type` in request body
- Session role from `session_tracker` (set via `vetka_session_init`)

### Agent Registry (`data/templates/agent_registry.yaml`)
- 9 registered roles: Alpha, Beta, Gamma, Delta, Epsilon, Zeta, Eta, Commander
- Each role has: callsign, domain, pipeline_stage, tool_type, worktree, branch, owned_paths, blocked_paths, model_tier
- **No API keys, no tokens, no verification**

### Authorization Layers (all warn-mode, not enforced):
1. **Tool Isolation Guard** — `allowed_tools` list on tasks
2. **Ownership Guard** — claimed tasks can't be reassigned
3. **Domain Validation** — agent domain must match task domain
4. **File Ownership Validation** — changed files vs `role.owned_paths`
5. **Branch Guard** — warns if completing on wrong branch
6. **Protocol Guard** — task-before-code rules

---

## 6. Gaps for External Agent Access

### Critical (must-have)
1. **No API key authentication** — all endpoints open to localhost
2. **No rate limiting** on taskboard endpoints
3. **No agent registration endpoint** — external agents can't register
4. **No CORS restrictions** — `allow_origins=["*"]` in main.py
5. **No audit logging** for REST API calls

### Important (should-have)
6. **Duplicate route definitions** — `claim`/`complete` defined twice in taskboard_routes.py
7. **Two overlapping route sets** — `/api/tasks/*` and `/api/taskboard/*` with different interfaces
8. **No OpenAPI schema** — using `Body(...)` without Pydantic models
9. **No pagination** — list endpoints return all tasks up to limit
10. **No webhook/callback** support for async task completion
11. **No WebSocket/SSE** for task status changes via REST

### Missing Operations (nice-to-have)
12. No `context_packet` REST endpoint (MCP only)
13. No `search_fts` REST endpoint (MCP only)
14. No `notify`/`notifications` REST endpoints (MCP only)
15. No `verify` REST endpoint (MCP only)
16. No `merge_request` REST endpoint (MCP only)

### Adapter Layer
17. Adapter pattern exists (`taskboard_adapters.py`) but is minimal
18. All adapters are identical — inherit from `GenericRESTAdapter` with no differentiation
19. No adapter-specific auth — adapters don't carry credentials

---

## 7. Recommended Architecture

### 7.1. New Endpoints (`/api/gateway/*`)

```
# Agent Registration & Auth
POST   /api/gateway/agents/register     # Register new agent, get API key
GET    /api/gateway/agents/me           # Current agent info (auth required)
POST   /api/gateway/agents/{id}/heartbeat # Prove liveness

# Task Operations (unified, paginated)
GET    /api/gateway/tasks               # List with cursor pagination
GET    /api/gateway/tasks/{id}          # Get task
GET    /api/gateway/tasks/{id}/history  # Status history
GET    /api/gateway/tasks/{id}/packet   # Context packet (MCC-ready)
GET    /api/gateway/tasks/claimable     # Available tasks for this agent
POST   /api/gateway/tasks/claim-next    # Claim highest-priority available
POST   /api/gateway/tasks/{id}/claim    # Claim specific task
POST   /api/gateway/tasks/{id}/complete # Complete task
POST   /api/gateway/tasks/{id}/cancel   # Cancel task

# Search
GET    /api/gateway/tasks/search        # FTS5 search

# Notifications
POST   /api/gateway/notify              # Send notification
GET    /api/gateway/notifications       # Get inbox
POST   /api/gateway/notifications/ack   # Acknowledge

# Board Info
GET    /api/gateway/board/summary       # Board summary
GET    /api/gateway/board/concurrent    # Concurrency info

# Real-time
GET    /api/gateway/stream              # SSE stream of task changes
```

### 7.2. Database Schema Additions

```sql
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    agent_type TEXT NOT NULL,  -- 'gemini', 'claude', 'gpt', 'custom'
    capabilities TEXT,          -- JSON: ['python', 'typescript', 'react', ...]
    model_tier TEXT,            -- 'bronze', 'silver', 'gold'
    owned_paths TEXT,           -- JSON: list of file patterns
    blocked_paths TEXT,         -- JSON: list of file patterns
    api_key_hash TEXT NOT NULL,
    status TEXT DEFAULT 'active',  -- 'active', 'suspended', 'retired'
    last_heartbeat TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT REFERENCES agents(id),
    action TEXT NOT NULL,       -- 'claim', 'complete', 'create', 'update'
    task_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    request_body TEXT,          -- JSON (truncated)
    response_status INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 7.3. Authentication Flow

```
1. Agent registers: POST /api/gateway/agents/register
   → Returns: { agent_id, api_key }

2. Agent authenticates: All requests include header
   → Authorization: Bearer <api_key>

3. Gateway middleware validates API key against agents table
   → Injects agent_id into request context

4. Heartbeat: POST /api/gateway/agents/{id}/heartbeat
   → Updates last_heartbeat, auto-releases stale claims
```

### 7.4. Security Additions
- **Pydantic models** for all request/response bodies
- **Rate limiting** per API key (e.g., 100 req/min)
- **Request audit logging** to `audit_log` table
- **CORS restriction** for gateway endpoints
- **IP-based access control** for sensitive ops (merge, promote)

---

## 8. Implementation Plan

### Phase 1: Foundation (MVP)
1. Add `agents` and `audit_log` tables to SQLite
2. Create agent registration endpoint
3. Add API key authentication middleware
4. Create unified `/api/gateway/tasks` endpoints (list, get, claim, complete)
5. Add rate limiting

### Phase 2: Agent Experience
6. Add `context_packet` REST endpoint
7. Add `search_fts` REST endpoint
8. Add notifications REST endpoints
9. Add SSE stream for real-time updates
10. Add heartbeat endpoint with auto-release

### Phase 3: Security & Polish
11. Fix duplicate route definitions in taskboard_routes.py
12. Add Pydantic models for all endpoints
13. Add OpenAPI schema generation
14. Add CORS restrictions
15. Add audit log viewer

### Phase 4: External Integration
16. Create agent SDK/client library (Python, TypeScript)
17. Create agent onboarding documentation
18. Create demo agent (Gemini integration example)
19. Add webhook support for external CI/CD

---

## 9. Files to Modify

| File | Changes |
|------|---------|
| `src/orchestration/task_board.py` | Add `register_agent()`, `get_agent()`, `heartbeat()` methods |
| `src/api/routes/gateway_routes.py` | **NEW** — Gateway API endpoints |
| `src/api/middleware/auth.py` | **NEW** — API key authentication middleware |
| `src/api/middleware/rate_limit.py` | **NEW** — Rate limiting middleware |
| `src/services/agent_registry.py` | Extend to support runtime agent registration |
| `data/migrations/003_agents.sql` | **NEW** — Schema migration for agents table |
| `data/migrations/004_audit_log.sql` | **NEW** — Schema migration for audit_log table |
| `src/api/models/gateway.py` | **NEW** — Pydantic models for gateway API |

---

## 10. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| External agents claim tasks they can't complete | Medium | Agent capability validation during registration |
| API key leakage | High | Key rotation, per-agent rate limits, audit logging |
| SQLite contention with many agents | Medium | Connection pooling, WAL mode already enabled |
| Duplicate route conflicts | Low | Consolidate to `/api/gateway/*` namespace |
| Breaking existing internal agents | High | Keep existing `/api/tasks/*` and `/api/taskboard/*` unchanged |

---

## 11. Conclusion

The VETKA TaskBoard is **80% ready** for external agent access. The core infrastructure (SQLite storage, claim/complete lifecycle, agent registry, FTS5 search) is solid. What's missing is:

1. **Authentication layer** (API keys + middleware)
2. **Agent registration** (self-service onboarding)
3. **A few missing REST endpoints** (context_packet, search, notifications)
4. **Security hardening** (rate limiting, audit logging, CORS)

Estimated effort: **3-4 days** for MVP (Phase 1), **1-2 weeks** for full implementation.
