# VETKA Agent Ecosystem — Architecture Document

**Version:** 1.1
**Date:** 2026-03-31
**Phase:** 196.16
**Status:** Living document — update as ecosystem evolves

---

## 0. Naming Conventions

### COHORT — Cooperative Orchestration of Hybrid Reasoning Teams
The VETKA multi-agent system. Different teams (Dragon, G3, Mycelium, Ralph Loop) are COHORTs — each with unique model composition, workflow chains, and interaction protocols.

| COHORT | Architect | Researcher | Coder | Verifier | Purpose |
|--------|-----------|------------|-------|----------|---------|
| **Dragon Bronze** | Qwen3-30b | Grok Fast 4.1 | Qwen3-coder-flash | Mimo-v2-flash | Quick fixes |
| **Dragon Silver** | Kimi K2.5 | Grok Fast 4.1 | Qwen3-coder | GLM-4.7-flash | Standard work |
| **Dragon Gold** | Kimi K2.5 | Grok Fast 4.1 | Qwen3-coder | Qwen3-235b | Complex tasks |
| **G3** | GPT-4o | Grok | Claude Sonnet | Claude Opus | Deep reasoning |
| **Mycelium** | Kimi K2.5 | Grok Fast 4.1 | Qwen3-coder | GLM/Qwen | Fractal decomposition |
| **Ralph Loop** | — | — | Qwen (iterative) | Self-verify | Autonomous iteration |

### WEATHER — Web Execution & Adaptive Task Heuristic Environment Router
The browser automation layer. Agents operate "in the weather" — navigating web AI services (Gemini, Kimi, Grok, Perplexity, Mistral) through Playwright/Chromium.

```
TaskBoard → WEATHER Orchestrator → Playwright → AI Service → Code extraction → Git
```

**Why "weather":** Dynamic, adaptive, conditions change (captcha, rate limits, UI updates). Agents navigate through it.

---

## 1. Overview

VETKA runs a **multi-agent ecosystem** where AI agents (local, cloud, browser-based) collaborate through a shared TaskBoard. This document describes how all pieces connect.

```
┌─────────────────────────────────────────────────────────────────┐
│                    VETKA Agent Ecosystem                        │
│                                                                 │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│   │  Local   │  │  Cloud   │  │ WEATHER  │  │ External │      │
│   │  Agents  │  │  Agents  │  │  Scouts  │  │  Agents  │      │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│        │              │              │              │            │
│   ┌────▼──────────────▼──────────────▼──────────────▼────┐      │
│   │              Agent Gateway (REST API)                 │      │
│   │         /api/gateway/*  — auth + rate limit           │      │
│   └────────────────────┬─────────────────────────────────┘      │
│                        │                                         │
│   ┌────────────────────▼─────────────────────────────────┐      │
│   │                  TaskBoard (SQLite)                   │      │
│   │   claim → work → commit → complete → QA → merge      │      │
│   └────────────────────┬─────────────────────────────────┘      │
│                        │                                         │
│   ┌────────────────────▼─────────────────────────────────┐      │
│   │              COHORT Pipelines                         │      │
│   │   Dragon / G3 / Mycelium / Ralph Loop                 │      │
│   └──────────────────────────────────────────────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Agent Types

### 2.1 Local Agents (VETKA Instance)

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| **Opus** (Commander) | Architecture | Claude Opus | Planning, RECON, decisions |
| **Qwen** (Coder) | Implementation | Qwen3-coder | Code writing, fixes |
| **Scouts** (NEW) | Context gathering | LiteRT (Qwen small) | Fast grep/read, parallel |
| **Ollama** | Fallback | Local models | Offline tasks |

### 2.2 Cloud Agents (via API)

| Agent | Role | Provider | Access |
|-------|------|----------|--------|
| **Grok** | Researcher | xAI (Polza) | `mycelium_call_model` |
| **GPT** | Researcher | OpenAI | `mycelium_call_model` |
| **Gemini** | Researcher | Google | `mycelium_call_model` |
| **Kimi** | Architect | Moonshot | `mycelium_call_model` |

### 2.3 Browser Agents (via Playwright)

| Agent | Role | Service | Access |
|-------|------|---------|--------|
| **Gemini (web)** | Researcher | aistudio.google.com | Browser Proxy |
| **Kimi (web)** | Researcher | kimi.ai | Browser Proxy |
| **Grok (web)** | Researcher | grok.x.ai | Browser Proxy |
| **Perplexity (web)** | Researcher | perplexity.ai | Browser Proxy |

### 2.4 External Agents (via Agent Gateway)

| Agent | Role | Access |
|-------|------|--------|
| **Gemini (AI Studio)** | Any | `/api/gateway/*` |
| **Claude (API)** | Any | `/api/gateway/*` |
| **GPT (API)** | Any | `/api/gateway/*` |
| **Any agent** | Any | Register → API key → REST |

---

## 3. Core Components

### 3.1 TaskBoard (`src/orchestration/task_board.py`)

Central task queue. All agents interact through it.

**Key methods:**
- `add_task()` — create task
- `claim_task(agent, type)` — take ownership
- `complete_task(commit_hash)` — mark done
- `dispatch_task()` — start pipeline
- `auto_complete_by_commit()` — match commits to tasks

**Status flow:**
```
pending → claimed → running → done_worktree → need_qa → verified → done_main
```

### 3.2 Agent Gateway (`src/api/routes/gateway_routes.py`)

REST API for external agents. Auth via API keys.

| Endpoint | Purpose |
|----------|---------|
| `POST /api/gateway/agents/register` | Get API key |
| `GET /api/gateway/tasks` | List available tasks |
| `POST /api/gateway/tasks/{id}/claim` | Claim task |
| `POST /api/gateway/tasks/{id}/complete` | Submit result |
| `GET /api/gateway/stream` | SSE real-time updates |
| `GET /api/gateway/admin/*` | Admin endpoints |

### 3.3 COHORT Pipelines (`src/orchestration/agent_pipeline.py`)

Fractal agent system. Decomposes tasks into subtasks via different COHORTs.

**COHORT Types:**
- **Dragon** (Bronze/Silver/Gold) — Asian model squad, auto-tier selection
- **G3** — GPT + Grok + Claude deep reasoning
- **Mycelium** — Fractal decomposition with scouts
- **Ralph Loop** — Autonomous iterative refinement

**Roles within each COHORT:**
1. **Architect** — plans, breaks into subtasks
2. **Scouts** — fast context gathering
3. **Researcher** — investigates unclear parts
4. **Coder** — implements with STM context
5. **Verifier** — QA review

### 3.4 WEATHER Browser Proxy (`src/services/browser_agent_proxy.py`)

Automates web AI services via Playwright. Acts as "Researcher" alternative within the WEATHER layer.

```
TaskBoard → WEATHER Orchestrator → Playwright → Gemini/Kimi/Grok → Code extraction → Git commit
```

**WEATHER = Web Execution & Adaptive Task Heuristic Environment Router**

### 3.5 Scout Agents (`src/services/scout_agents.py`) [NEW]

Fast parallel context gatherers. LiteRT models for speed.

```
Architect says "I need context on X"
  → 3-5 scouts run in parallel
  → grep, read files, collect facts
  → aggregate into single context object
  → Architect plans with full picture
```

---

## 4. The 3 Core Gaps (and Fixes)

All agent paths shared 3 common gaps. Fixes are in progress.

### Gap 1: Auto-commit after file write

**Problem:** Pipeline writes files but never creates a git commit.
Code sits as uncommitted changes forever.

**Fix:** `_auto_commit_pipeline_files()` in task_board.py.
After pipeline.execute(), collect files_written → git add → commit with `[task:{task_id}]`.

**Status:** ✅ Verified

### Gap 2: Code extraction from responses

**Problem:** Chat/MCP agent responses never extract code blocks or write files.
Infrastructure exists but wasn't wired.

**Fix:** `response_applier.py` — thin wrapper around `extract_code_blocks()` + `write_file_safe()`.
Wired into chat_routes.py (apply_code flag) and llm_call_tool.py.

**Status:** ✅ Verified

### Gap 3: Response → task completion

**Problem:** No universal path from "agent produced result" → "task completed".

**Fix:** `complete_task_from_result()` in task_board.py.
Extract code → write files → git commit → auto_complete_by_commit().

**Status:** 🔧 Needs fix (2 bugs found by QA)

---

## 5. Data Flow: Full COHORT Pipeline

```
User: @dragon "Implement parallax effect"
  │
  ▼
MCC dispatches task to TaskBoard
  │
  ▼
COHORT Pipeline starts (auto-selects Dragon Silver)
  │
  ├── Architect (Kimi): Plan subtasks
  │   └── estimates complexity → selects tier
  │
  ├── Scouts (LiteRT × 3): Gather context
  │   ├── Scout 1: grep "parallax" → 5 files
  │   ├── Scout 2: read src/parallax/ → structure
  │   └── Scout 3: search Qdrant → related docs
  │   └── Results aggregated → DOM context
  │
  ├── Researcher (Grok API OR WEATHER Browser Proxy):
  │   └── investigates unclear parts
  │   └── WEATHER: opens Gemini.ai, scrapes response
  │
  ├── Coder (Qwen): Implements
  │   └── uses STM context + scout results
  │   └── writes code via _extract_and_write_files()
  │
  └── Verifier (GLM): QA review
      └── checks syntax, tests, patterns
  │
  ▼
CORE-GAP-1: auto-commit files → git
  │
  ▼
TaskBoard: status → done_worktree
  │
  ▼
Agent Gateway: external agents can see completed task
  │
  ▼
QA (Delta): verify → merge to main
```

---

## 6. Super-Economy Hybrid Model

The goal: maximize AI output while minimizing API costs.

| Layer | What | Cost | Speed |
|-------|------|------|-------|
| **Scouts** | LiteRT local | Free | ⚡ 0.1s |
| **Architect** | Kimi (Polza) | Cheap | 🔄 2s |
| **Researcher** | Grok API OR WEATHER | Cheap/Free | 🔄 5-30s |
| **Coder** | Qwen3-coder (Polza) | Cheap | 🔄 10s |
| **Verifier** | GLM-4.7-flash (Polza) | Cheap | 🔄 5s |
| **WEATHER** | Gemini/Kimi/Grok web | Free | 🐌 30-60s |

**Strategy:** Use free WEATHER agents for bulk work, API agents for speed-critical tasks.

---

## 7. File Map

| Component | File | Status |
|-----------|------|--------|
| TaskBoard core | `src/orchestration/task_board.py` | ✅ |
| Agent Gateway routes | `src/api/routes/gateway_routes.py` | ✅ |
| Gateway admin | `src/api/routes/gateway_admin_routes.py` | ✅ |
| Auth middleware | `src/api/middleware/auth.py` | ✅ |
| Rate limiting | `src/api/middleware/rate_limit.py` | ✅ |
| Audit logging | `src/api/middleware/audit.py` | ✅ |
| SSE stream | `src/services/gateway_sse.py` | ✅ |
| Response applier | `src/utils/response_applier.py` | ✅ (CORE-GAP-2) |
| Browser proxy | `src/services/browser_agent_proxy.py` | 🔧 BP-1.x |
| Browser manager | `src/services/browser_manager.py` | 🔧 BP-1.x |
| Scout agents | `src/services/scout_agents.py` | 🔧 SCOUT-1 |
| Pipeline | `src/orchestration/agent_pipeline.py` | ✅ |
| Pydantic models | `src/api/models/gateway.py` | ✅ |
| Public mirror | `public_mirrors/vetka-taskboard/` | ✅ |

---

## 8. Configuration

| File | Purpose |
|------|---------|
| `data/templates/model_presets.json` | Team tiers (Bronze/Silver/Gold) |
| `config/browser_agents.yaml` | Browser account credentials |
| `.mcp.json` | MCP server config |
| `AGENTS.md` | Agent instructions & methodology |

---

## 9. Testing

```bash
# Gateway tests
pytest tests/test_agent_gateway.py -v

# Full test suite
pytest tests/ -v
```

---

## 10. Changelog

| Date | Phase | Change |
|------|-------|--------|
| 2026-03-31 | 196.7 | Agent Gateway (auth, rate limit, audit) |
| 2026-03-31 | 196.14 | Browser Proxy RECON |
| 2026-03-31 | 196.15 | CORE-GAP fixes (auto-commit, code extract, task wiring) |
| 2026-03-31 | 196.15 | Scout agents + Browser Researcher roles |
| 2026-03-31 | 196.15 | This document created |

---

*This document is the single source of truth for the VETKA Agent Ecosystem.
Update it when adding new agent types, roles, or changing the pipeline.*
