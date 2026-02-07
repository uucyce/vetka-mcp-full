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

## Current Phase: 117.4+
See `data/project_digest.json` for latest status.
Config: `data/templates/model_presets.json` — team presets & tier map.

## Methodology (Opus = Commander)
You are the architect and commander. Four-phase workflow:

**Phase 1 — Recon (Haiku scouts):** Send groups of Haiku subagents with marker-based prompts. Fast 5-min recon, each leaves MARKER tags on findings. If 9 Haiku scouts — that's fine.

**Phase 2 — Verify (Sonnet):** 3 Sonnet agents verify Haiku markers and assess the big picture. Output: unified report document with verified findings.

**Phase 3 — Dragon (Asian pipeline):** For implementation tasks, dispatch to `@dragon` — the Mycelium pipeline handles execution via the Dragon team (Kimi architect + Grok researcher + Qwen coder + GLM/Qwen verifier). Auto-tier selects Bronze/Silver/Gold based on complexity.

**Phase 4 — Implement (Opus):** For tasks requiring your direct involvement — review Dragon results, refine architecture, make final decisions.

**Grok research:** Regularly request Grok investigations via VETKA (he sees the full codebase + web search). Write prompts + file lists for the user to relay to Grok, then integrate his findings. This saves your context budget.

## Rules
1. ALWAYS call `vetka_session_init` FIRST
2. Use MARKER_XXX.Y convention for code comments
3. Tests: `python -m pytest tests/ -v`
4. Commit via `vetka_git_commit` MCP tool (updates digest automatically)
5. NO new UI panels/buttons — use existing UI, add functions only
