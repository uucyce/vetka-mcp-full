# RECON: Agent Memory Pipeline Audit
**Date:** 2026-04-07
**Task:** tb_1775571427_88421_1
**Agent:** Opus (terminal_54d1 worktree)
**Status:** COMPLETE

## Executive Summary

Full recon of agent memory/context system after tmux migration. 4 areas investigated via parallel subagents.

---

## Area 1: Claude Code Harness Memory

### How Context Actually Works
- Claude Code stores conversation history in **JSONL files**: `~/.claude/projects/<slug>/<uuid>.jsonl`
- Each session = separate file (1-2 MB, 1000+ lines structured JSON)
- Contains: user messages, assistant responses, tool uses, file snapshots
- `tmux send-keys` delivers input via PTY stdin, NOT through scrollback buffer
- **Compaction** (context shrinking) happens automatically inside API when context window fills
- Early instructions can get lost during compaction — this is the "forgetting" users observe

### Key Settings
- `settings.json`: only `skipDangerousModePermissionPrompt=true`, no conversation/memory settings
- No `--max-conversation-turns` or `autoCompact` flags available
- Context window: 200K (Opus/Sonnet), 100K (Haiku) — managed by Anthropic API

### Context Exhaustion Recovery
- `synapse_context_monitor.sh` detects exhaustion patterns ("conversation is getting long")
- Saves checkpoint, kills session, respawns with recovery prompt
- This is the ONLY mechanism preventing infinite context burn

## Area 2: tmux Scroll/History

### Definitive Answer: tmux history-limit does NOT affect agent context

**Evidence:**
- Agent reads from process stdin via PTY, not terminal buffer
- JSONL conversation log persists independently of tmux
- `--continue` / `--resume` restore from JSONL, not scrollback
- Current `history-limit 50000` in `~/.tmux.conf` is fine for human debugging

**Recommendation:** Keep 50000, don't overthink it. Agent memory problems are elsewhere.

## Area 3: Memory Folder — WRITE-ONLY PIPELINE (Critical Finding)

### The Problem
Agents write memory docs diligently, but **nobody reads them back**.

### Write Side (Working)
- `smart_debrief.py` records Q1/Q2/Q3 answers to `memory/roles/{Callsign}/MEMORY.md`
- Files exist: Zeta (42 lines), Alpha (42 lines), Epsilon (24 lines)

### Read Side (BROKEN)
- `load_recent()` in `role_memory_writer.py` exists but is **never called**
- `session_init()` passes only the memory path as a string, not actual content
- File watcher in `file_watcher.py` skips `~/.claude/` directory entirely
- Qdrant has no integration with role memory files
- **feedback_*.md files are the ONLY type that gets loaded** into ENGRAM L1

### Three Wires Needed
1. Call `load_recent()` in session context setup (`session_tools.py` ~line 1567)
2. Create `ingest_role_memories()` function in `engram_cache.py` (like feedback has)
3. Extend `file_watcher.py` to monitor `~/.claude/projects/*/memory/`

### Files Involved
- Write: `src/memory/role_memory_writer.py`
- Missing load: `src/mcp/tools/session_tools.py`
- Missing ingestion: `src/memory/engram_cache.py`
- Missing watch: `src/scanners/file_watcher.py`

## Area 4: Gemma Integration Gaps

### What's Done
- 4 worktrees created (gemma-engine, gemma-scout, gemma-sherpa, gemma-qa)
- spawn_synapse.sh has `free_code` agent type with LiteLLM bridge
- `--bare` flag fix for credential bypass
- `litellm_gemma_bridge.py` Priority B (XML parser) written

### What's Missing (P0 Blockers)
1. **MCP config** not generated in Gemma worktrees — agents can't call tools
2. **E2E bridge test** — bridge written but never tested end-to-end
3. **LiteRT not wired** — Gemma running raw Ollama on CPU = slow + hot
4. **Health checks** missing in spawn_synapse.sh

### Model Composition (Current — OK)
```
Alpha=sonnet, Beta=haiku, Gamma=haiku, Delta=haiku
Epsilon=haiku, Eta=opus, Zeta=sonnet, Commander=opus
Gemma: Omicron=e4b, Pi=e2b, Rho=26b, Sigma=e4b
Qwen: 3 roles (qwen tier)
```

## Root Cause Analysis: Why Agents "Forget"

1. **API compaction** — Claude Code auto-compacts context, losing early instructions (unavoidable, by design)
2. **Memory pipeline broken** — role memories written but never loaded back (fixable, 3 wires)
3. **No ENGRAM ingestion** for role memory docs (only feedback gets ingested)
4. **File watcher blind spot** — `~/.claude/` directory excluded from monitoring

## Recommendations

### Immediate (Today)
- Fix memory pipeline (3 wires) — this is likely the root cause of agent regression
- Keep tmux history-limit 50000

### This Week
- Gemma: wire LiteRT for GPU acceleration (not raw Ollama CPU)
- Gemma: generate MCP config in worktrees
- Gemma: E2E bridge test

### After Gemma Stabilized
- All hands on CUT
