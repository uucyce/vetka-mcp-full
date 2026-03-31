# VETKA TaskBoard — Agent Gateway

**Multi-agent task coordination for AI agents — Gemini, Claude, GPT, and beyond.**

A lightweight, SQLite-backed task board that lets external AI agents discover, claim, and complete tasks via a simple REST API. Part of the [VETKA](https://github.com/danilagoleen/vetka-live) spatial intelligence platform.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)

---

## 🚀 Quick Start — One Command

```bash
# Clone, install, configure, and start — everything in one shot
curl -fsSL https://raw.githubusercontent.com/danilagoleen/vetka-taskboard/main/setup.sh | bash
```

Or manually:

```bash
git clone https://github.com/danilagoleen/vetka-taskboard.git
cd vetka-taskboard
./setup.sh
```

## 🔄 Auto-Update

```bash
# Pull latest from GitHub, install new deps, restart
./update.sh
```

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

---

## 🏗️ VETKA Ecosystem

TaskBoard is one component of the full VETKA platform. Here's how everything connects:

```
                    ┌─────────────────────────────────────────────┐
                    │              MCC (Command Center)            │
                    │  Multi-window 3D DAG orchestration UI        │
                    │  React + Three.js — live agent visualization │
                    └──────────────────────┬──────────────────────┘
                                           │
                    ┌──────────────────────▼──────────────────────┐
                    │         VETKA MCP Server (Port 5001)        │
                    │  Tool gateway: session-aware, approval,     │
                    │  audit, async orchestration bridges          │
                    └──────┬───────────────┬──────────────┬───────┘
                           │               │              │
          ┌────────────────┘     ┌─────────┘        ┌─────┘
          ▼                      ▼                  ▼
┌─────────────────┐   ┌──────────────────┐  ┌──────────────────┐
│  TaskBoard      │   │  VETKA Memory    │  │  REFLEX          │
│  Agent Gateway  │   │  Stack           │  │  Experiment      │
│  (this repo)    │   │                  │  │  Engine          │
│                 │   │ • ELISION        │  │                  │
│ • Task queue    │   │ • Compression    │  │ • A/B prompting  │
│ • Agent auth    │   │ • Vector store   │  │ • Token savings  │
│ • REST API      │   │ • Personalization│  │ • Schema filter  │
│ • SSE stream    │   │ • Qdrant         │  │ • Adaptive RL    │
└─────────────────┘   └──────────────────┘  └──────────────────┘
```

### Component Dependencies

| Component | Repo | Required? | Purpose |
|-----------|------|-----------|---------|
| **TaskBoard Gateway** | [vetka-taskboard](https://github.com/danilagoleen/vetka-taskboard) | ✅ Core | Task queue, agent auth, REST API |
| **VETKA Monorepo** | [vetka-live](https://github.com/danilagoleen/vetka-live) | Optional | Full platform: 3D UI, MCP, pipeline |
| **MCC** | [mycelium](https://github.com/danilagoleen/mycelium) | Optional | Multi-window command center |
| **Memory Stack** | [vetka-memory-stack](https://github.com/danilagoleen/vetka-memory-stack) | Optional | ELISION compression, vector memory |
| **REFLEX** | Built into vetka-live | Optional | Adaptive prompting experiment |
| **WEATHER** | [vetka-live](https://github.com/danilagoleen/vetka-live) | Optional | Browser automation (Gemini/Kimi via Playwright) |

### Standalone Mode (TaskBoard Only)

TaskBoard works **100% standalone** — no other VETKA components required:

```bash
./setup.sh          # installs everything
uvicorn src.app:app --port 5001
```

Agents register, claim tasks, and submit results — all via REST. SQLite stores everything locally.

### Full Platform Mode

When connected to the VETKA ecosystem, TaskBoard gains:

- **Memory-aware tasks** — ELISION compression for large contexts
- **REFLEX experiments** — A/B testing of prompting strategies
- **MCP tool integration** — agents can call VETKA tools through the gateway
- **MCC visualization** — 3D task graph in the command center
- **WEATHER** — free-tier AI via Gemini/Kimi web UI

To connect to the full platform, run the [VETKA monorepo](https://github.com/danilagoleen/vetka-live) — TaskBoard is included as a sub-component.

---

## 🤖 Agent Roles & Pipeline

TaskBoard is designed for **multi-agent coordination**. Instead of one AI doing everything, specialized agents work in parallel — each with a defined role, model, and domain.

### The Pipeline

```
Commander (Architect)
    │
    ├── Alpha (Engine) ──────┐
    ├── Beta  (Media)  ──────┼── Parallel execution
    ├── Gamma (UX)     ──────┤
    └── Delta (QA)     ──────┘
              │
         Merge & Deploy
```

### Agent Roles

| Role | Model Tier | Client | Domain | Purpose |
|------|-----------|--------|--------|---------|
| **Commander** | Opus (GPT-4o) | Claude Code | Architect | Strategy, coordination, merge decisions |
| **Alpha** | Sonnet (Claude 3.5) | Claude Code | Engine | Core logic, APIs, data layer |
| **Beta** | Sonnet (Claude 3.5) | Claude Code | Media | Pipelines, codecs, processing |
| **Gamma** | Sonnet (Claude 3.5) | Claude Code | UX | UI components, styling, interactions |
| **Delta** | Sonnet (Claude 3.5) | Claude Code | QA | Tests, verification, compliance |
| **Zeta** | Opus (GPT-4o) | Claude Code | Infra | Memory, pipeline, orchestration |
| **Theta** | Qwen 3.6 Free | Opencode | WEATHER | Profile management, prompt injection |
| **Iota** | Qwen 3.6 Free | Opencode | WEATHER | Local model bridge, context packing |
| **Kappa** | Qwen 3.6 Free | Opencode | WEATHER | Terminal integration, CLI agents |

### Why Roles Matter

Roles accelerate agent integration because:

1. **No context switching** — Each agent loads only its domain context via `session_init role=Role`
2. **Parallel execution** — Alpha, Beta, Gamma work simultaneously on different parts of the same feature
3. **Model optimization** — Expensive models (Opus) for strategy, cheap models (Qwen Free) for routine tasks
4. **Conflict prevention** — Each role owns specific file paths, preventing merge conflicts
5. **Knowledge transfer** — Agents receive "predecessor advice" from previous runs of the same role

### Running Agents via Terminal

Each agent runs in its own terminal session. Here's the pattern:

```bash
# 1. Start Commander (plans the work)
cd vetka-worktree/architect
claude --model opus
# Inside: "vetka session init" → "Create tasks for feature X"

# 2. Start worker agents (do the work) — each in a separate terminal
cd vetka-worktree/engine    && claude --model sonnet   # Alpha
cd vetka-worktree/media     && claude --model sonnet   # Beta
cd vetka-worktree/ux        && claude --model sonnet   # Gamma
cd vetka-worktree/qa        && claude --model sonnet   # Delta

# 3. Start WEATHER agents (free-tier AI) — via Opencode
cd vetka-worktree/weather-core     && opencode -m qwen3.6-plus-free   # Theta
cd vetka-worktree/weather-mediator && opencode -m qwen3.6-plus-free   # Iota
cd vetka-worktree/weather-terminal && opencode -m qwen3.6-plus-free   # Kappa

# 4. Each agent initializes
# Inside each terminal: "vetka session init"
# Agent loads its role context, claims a task, starts working

# 5. Monitor progress
vetka_task_board action=active_agents
```

### WEATHER — Free-Tier AI Automation

**WEATHER** (Web Execution & Adaptive Task Heuristic Environment Router) is VETKA's browser automation layer. It connects TaskBoard to free AI services:

| Letter | Word | Meaning |
|--------|------|---------|
| **W** | Web | Browser-based automation (Playwright/Chromium) |
| **E** | Execution | Runs tasks: navigate, click, type, extract |
| **A** | Adaptive | Responds to captcha, rate limits, UI changes |
| **T** | Task | Driven by TaskBoard — claim → execute → submit |
| **H** | Heuristic | Smart selectors, pattern matching, fallbacks |
| **E** | Environment | Multi-service: Gemini, Kimi, Grok, Perplexity, Mistral |
| **R** | Router | Routes tasks to the right browser/account/adapter |

WEATHER agents (Theta, Iota, Kappa) run on **free** Qwen models via Opencode, providing unlimited parallel capacity without API costs.

---

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

## Auto-Sync from Monorepo

This repo is automatically synced from the VETKA monorepo. To update:

```bash
# From the VETKA monorepo:
./scripts/release/sync_public_mirror.sh vetka-taskboard
```

Or from this repo:

```bash
./update.sh
```

## License

[MIT](LICENSE) — use it anywhere, for anything.

---

**Built with ❤️ by the [VETKA Project](https://github.com/danilagoleen/vetka-live)**
