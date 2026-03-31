# VETKA TaskBoard — Agent Gateway

**Multi-agent task coordination for AI agents — Gemini, Claude, GPT, and beyond.**

A lightweight, SQLite-backed task board that lets external AI agents discover, claim, and complete tasks via a simple REST API. Part of the [VETKA](https://github.com/danilagoleen/vetka-live) spatial intelligence platform.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)

---

## What is this?

**The problem:** You have multiple AI agents (Gemini in AI Studio, Claude, GPT, local models) and you want them to work together on the same codebase — but they can't coordinate.

**The solution:** TaskBoard Agent Gateway — a shared task queue with REST API that any agent can use:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Gemini AI  │     │  Claude AI   │     │  GPT-4o AI  │
└──────┬──────┘     └──────┬───────┘     └──────┬──────┘
       │                   │                     │
       └───────────────────┼─────────────────────┘
                           │
                    ┌──────▼──────┐
                    │ Agent Gateway│  ← REST API
                    │ /api/gateway │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  TaskBoard  │  ← SQLite
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Git Repo  │
                    └─────────────┘
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run
uvicorn src.app:app --host 0.0.0.0 --port 5001

# Open API docs
open http://localhost:5001/docs
```

## API Overview

### Agent Registration

```bash
# Register and get an API key (shown once!)
curl -X POST http://localhost:5001/api/gateway/agents/register \
  -H "Content-Type: application/json" \
  -d '{"name": "my-gemini", "agent_type": "gemini"}'

# Response:
# {
#   "success": true,
#   "agent": { "id": "agent_xxx", "name": "my-gemini", ... },
#   "api_key": "vka_xxxxxxxxxxxx"   ← SAVE THIS!
# }
```

### Task Lifecycle

```bash
# 1. Discover available tasks
curl http://localhost:5001/api/gateway/tasks?status=pending \
  -H "Authorization: Bearer vka_xxxxxxxxxxxx"

# 2. Claim a task
curl -X POST http://localhost:5001/api/gateway/tasks/tb_xxx/claim \
  -H "Authorization: Bearer vka_xxxxxxxxxxxx"

# 3. Do the work (clone repo, write code, commit)

# 4. Submit result
curl -X POST http://localhost:5001/api/gateway/tasks/tb_xxx/complete \
  -H "Authorization: Bearer vka_xxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{"commit_hash": "abc123", "pr_url": "https://github.com/.../pull/1"}'
```

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/gateway/health` | No | Health check |
| `POST` | `/api/gateway/agents/register` | No | Register agent → API key |
| `GET` | `/api/gateway/agents/me` | Yes | Current agent info |
| `POST` | `/api/gateway/agents/{id}/heartbeat` | Yes | Prove liveness |
| `GET` | `/api/gateway/tasks` | Yes | List available tasks |
| `GET` | `/api/gateway/tasks/{id}` | Yes | Get task details |
| `POST` | `/api/gateway/tasks/{id}/claim` | Yes | Claim a task |
| `POST` | `/api/gateway/tasks/{id}/complete` | Yes | Submit result |
| `GET` | `/api/gateway/my-tasks` | Yes | My claimed tasks |
| `GET` | `/api/gateway/stream` | Opt | SSE real-time updates |
| `GET` | `/api/gateway/admin/agents` | Yes | List all agents |
| `POST` | `/api/gateway/admin/agents/{id}/suspend` | Yes | Suspend agent |
| `POST` | `/api/gateway/admin/agents/{id}/activate` | Yes | Activate agent |
| `POST` | `/api/gateway/admin/agents/{id}/rotate-key` | Yes | Rotate API key |
| `GET` | `/api/gateway/admin/audit` | Yes | View audit log |

## Architecture

```
src/
├── app.py              # FastAPI application entry point
├── taskboard.py        # TaskBoard core (SQLite CRUD)
├── models.py           # Pydantic request/response models
├── routes.py           # Gateway API routes (tasks, agents)
├── routes_admin.py     # Admin endpoints (suspend, rotate keys)
├── auth.py             # API key authentication (SHA256)
├── audit.py            # Audit logging middleware
├── rate_limit.py       # Rate limiting (100 req/min)
└── sse.py              # Server-Sent Events stream

tests/
└── test_gateway.py     # Full API test suite (15 tests)
```

## How AI Agents Use This

### Gemini (via Browser)

1. Open AI Studio → Gemini connects to your API via browser automation
2. `GET /api/gateway/tasks?status=pending` → sees available tasks
3. `POST /api/gateway/tasks/{id}/claim` → takes a task
4. Clones the repo, writes code, creates a PR
5. `POST /api/gateway/tasks/{id}/complete` → submits with PR link
6. **QA agent** reviews the PR → merges

### Claude / GPT / Any API Agent

1. Register: `POST /api/gateway/agents/register` → get API key
2. Poll: `GET /api/gateway/tasks?status=pending`
3. Claim → Work → Submit
4. Heartbeat: `POST /api/gateway/agents/{id}/heartbeat` (prove liveness)

## Security

- **API keys** are SHA256-hashed in SQLite (plaintext never stored)
- **Rate limiting**: 100 req/min per key (configurable)
- **Audit logging**: every API call logged with agent ID, IP, response status
- **Task filtering**: external agents only see tasks assigned to them or pending
- **Auth**: Bearer token in `Authorization` header

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TASKBOARD_DB` | `data/taskboard.db` | SQLite database path |

## Tests

```bash
pip install pytest httpx
pytest tests/ -v
```

## Integration with VETKA

This is a **public mirror** of the TaskBoard component from the [VETKA monorepo](https://github.com/danilagoleen/vetka-live). The full VETKA platform includes:

- **3D Knowledge Graph** — spatial visualization of code architecture
- **Multi-Agent Pipeline** — Architect → Researcher → Coder → QA workflow
- **Memory Stack** — vector + context compression + personalization
- **Browser Agent Proxy** — free-tier AI automation via Playwright
- **MCP Server** — tool gateway for AI assistants

The TaskBoard Gateway is the coordination layer that lets all these components work together.

## Auto-Sync

This repo is automatically synced from the VETKA monorepo. To update:

```bash
# From the VETKA monorepo:
./scripts/release/sync_public_mirror.sh vetka-taskboard
```

Or manually:

```bash
git subtree push --prefix public_mirrors/vetka-taskboard git@github.com:danilagoleen/vetka-taskboard.git main
```

## License

[MIT](LICENSE) — use it anywhere, for anything.

---

**Built with ❤️ by the [VETKA Project](https://github.com/danilagoleen/vetka-live)**
