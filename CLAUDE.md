# VETKA Project — Agent Instructions

## ON CONNECT (MANDATORY)
ALWAYS call `vetka_session_init` as your FIRST action when starting a new conversation.
This loads project context, current phase, user preferences, and recent state.

## Architecture
- **Stack:** Tauri (Rust) + React (TypeScript) + Python FastAPI backend
- **MCP Server:** Port 5001, 35+ tools registered
- **Backend:** FastAPI + SocketIO on port 5001
- **Frontend:** React + Three.js 3D visualization

## Mycelium Pipeline (Fractal Agent System)
The Mycelium pipeline decomposes tasks into subtasks via a fractal architecture:

1. **Architect** plans — breaks task into subtasks (JSON)
2. **Researcher** investigates unclear parts (needs_research=true)
3. **Coder** implements each subtask with STM (Short-Term Memory) context
4. **Verifier** reviews results (QA)

Pipeline streams progress in real-time to chat via SocketIO.
Auto-tier: Architect estimates complexity — pipeline selects team tier automatically.

## Dragon Team (Asian Model Squad)
Three tiers of Asian models via Polza provider:

| Tier | Preset | Architect | Researcher | Coder | Verifier |
|------|--------|-----------|------------|-------|----------|
| Bronze | `dragon_bronze` | Qwen3-30b | Grok Fast 4.1 | Qwen3-coder-flash | Mimo-v2-flash |
| Silver | `dragon_silver` | Kimi K2.5 | Grok Fast 4.1 | Qwen3-coder | GLM-4.7-flash |
| Gold | `dragon_gold` | Kimi K2.5 | Grok Fast 4.1 | Qwen3-coder | Qwen3-235b |

Default: `dragon_silver`. Auto-switches based on architect's `estimated_complexity`.
Grok Fast 4.1 = "The Last Samurai" — researcher in ALL tiers.

## System Commands (available in any chat via @mention)
- `@dragon <task>` — Build/implement pipeline (default: dragon_silver)
- `@doctor <question>` — Research/diagnostic pipeline (debug tasks, system health, navigation)
- `@help <question>` — Alias for @doctor
- `@pipeline <task>` — Explicit pipeline invocation

## MCP Tools (key ones)
- `vetka_session_init` — MUST call first! Loads project context
- `vetka_mycelium_pipeline` — Run agent pipeline with preset/provider
- `vetka_heartbeat_tick` — Scan chat for @dragon/@doctor tasks
- `vetka_call_model` — Call any LLM (Grok, GPT, Claude, Gemini, Ollama)
- `vetka_search_semantic` — Qdrant vector search
- `vetka_read_file` / `vetka_edit_file` — File operations
- `vetka_git_commit` — Commit via VETKA (updates project digest)
- `vetka_run_tests` — Run pytest

## Architecture Validation (Cursor Research, Feb 2026)

Cursor's scaling agents research independently validates VETKA's architecture:

| Cursor Discovery | VETKA Implementation |
|---|---|
| Hierarchical roles, not flat peers | Opus Commander → Haiku/Sonnet scouts → Dragon pipeline |
| Planners spawn sub-planners recursively | Mycelium fractal: Architect → subtasks → sub-research |
| Workers push independently, no integrator | Dragon coder/researcher — fire-and-forget + STM |
| Different models for different roles | Триада: Kimi=architect, Grok=researcher, Qwen=coder |
| Prompts matter more than harness | CLAUDE.md + pipeline_prompts.json = the magic |
| Fresh starts combat drift | vetka_session_init + STM auto-reset (MARKER_117.5B) |
| Judge agent evaluates continuation | Verifier (GLM/Qwen-235b) in pipeline |

Key insights applied:
- **Event-driven wakeup** (MARKER_117.5A): Pipeline completion triggers heartbeat check for follow-up tasks
- **Auto context reset** (MARKER_117.5B): STM resets after 10 subtasks to prevent drift
- **GPT-5.2 option** (MARKER_117.5C): `dragon_gold_gpt` preset for extended autonomous work

## Current Phase: 117.5
See `data/project_digest.json` for latest status.
Config: `data/templates/model_presets.json` — team presets & tier map.

## Methodology (Opus = Commander)
You are the architect and commander. When planning ANY non-trivial task, deploy your full army:

### Your Army

| Regiment | Model | Count | Role | Speed |
|----------|-------|-------|------|-------|
| Haiku Scouts | claude-haiku | 3-9 parallel | Recon: grep, read files, leave MARKERs | Fast (seconds) |
| Sonnet Verifiers | claude-sonnet | 2-3 parallel | Cross-check Haiku findings, assess big picture | Medium |
| Dragon Bronze | Qwen+Grok+Mimo | 4 roles | Quick build/fix for simple tasks | Fast, cheap |
| Dragon Silver | Kimi+Grok+Qwen+GLM | 4 roles | Standard implementation | Balanced |
| Dragon Gold | Kimi+Grok+Qwen+Qwen-235b | 4 roles | Complex/critical tasks | Best quality |
| Grok (via user) | Grok 4.1 | 1 (relay) | Deep web research + codebase analysis | User relays |
| Opus (you) | claude-opus | 1 | Architecture, final decisions, synthesis | Expensive — save budget |

### Battle Plan (every task)

**Phase 1 — Recon:** Deploy 3-9 Haiku scouts in parallel. Each gets a focused prompt + file list. Each leaves MARKER_XXX tags. Done in ~5 min.

**Phase 2 — Verify:** Deploy 2-3 Sonnet verifiers to cross-check Haiku markers. Output: single unified report with verified findings, gaps, and risks.

**Phase 3 — Research (Grok):** Write a research prompt for Grok (codebase + web). Include specific files and questions. User relays to Grok, brings back findings. This saves YOUR context.

**Phase 4 — Dragon Execute:** Dispatch `@dragon <task>` for implementation. Mycelium pipeline auto-selects tier (Bronze/Silver/Gold) based on architect's complexity estimate. Streams progress to chat. Dragon team handles: planning (Kimi), research (Grok Fast), coding (Qwen), verification (GLM/Qwen).

**Phase 5 — Opus Review:** Review Dragon output. Refine architecture. Make final decisions. Commit.

### Key: Always write the FULL plan with all regiments before executing. The user wants to see WHO does WHAT.

## Rules
1. ALWAYS call `vetka_session_init` FIRST
2. Use MARKER_XXX.Y convention for code comments
3. Tests: `python -m pytest tests/ -v`
4. Commit via `vetka_git_commit` MCP tool (updates digest automatically)
5. NO new UI panels/buttons — use existing UI, add functions only
