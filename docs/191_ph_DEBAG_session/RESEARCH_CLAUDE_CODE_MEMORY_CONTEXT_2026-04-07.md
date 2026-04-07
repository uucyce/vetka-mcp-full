# Claude Code Harness Memory & Context Management — Research Report

## Executive Summary

Claude Code harness (VETKA Project, Phase 210+) implements **multi-agent orchestration with explicit context management**. Each agent role has a defined memory/context lifecycle: **spawning → initialization → checkpoint on exhaustion → recovery restart**.

Context is NOT automatically preserved across sessions. Instead:
1. **Bootstrap-only CLAUDE.md** — thin routing file pointing to dynamic session_init
2. **Session context** — loaded fresh on `vetka_session_init role=<callsign>`
3. **Checkpoint system** — saves agent state on context exhaustion + auto-restarts
4. **tmux history** — 50,000 line buffer for command retention (not conversation history)

---

## 1. MODEL TIERS & ROLE ASSIGNMENTS

**Source:** `docs/USER_GUIDE_MULTI_AGENT.md` & `data/templates/agent_registry.yaml`

| Role | Model | Client | Domain | Why This Tier |
|------|-------|--------|--------|---------------|
| **Commander** | **Opus** | Claude Code | architect | Strategic coordination, merge conflicts |
| **Zeta** | **Opus** | Claude Code | harness | Infrastructure, deep debugging |
| **Alpha** | **Sonnet** | Claude Code | engine | Complex engine architecture, timeline logic |
| **Eta** | **Sonnet** | Claude Code | harness | Partner to Zeta, infra support |
| **Beta** | **Haiku** | Claude Code | media | FFmpeg pipelines, codecs, templates |
| **Gamma** | **Haiku** | Claude Code | ux | UI wiring, SVG, CSS, fast iteration |
| **Delta** | **Haiku** | Claude Code | qa | Test execution, pytest, compliance checks |
| **Epsilon** | **Haiku** | Claude Code | qa | Additional QA capacity, contract tests |
| **Polaris** | **Qwen 3.6+** | Opencode | architect | Captain — coordinates Opencode fleet |
| **Theta, Iota, Kappa** | **Qwen 3.6+** | Opencode | weather | Profile mgr, mediator, terminal (free tier) |
| **Omicron, Pi, Rho, Sigma** | **Gemma 4** | free-code | gemma | Local inference (free, no API cost) |
| **Mistral-1, 2, 3, Nu** | **Mistral Vibe** | vibe-cli | qa/weather | Free tier, 10-15 tasks/day limit |

**Key insight:** Model tier is **read from agent_registry.yaml at spawn time**, NOT hardcoded. `spawn_synapse.sh` calls `_get_model_tier()` function (lines 96-119).

---

## 2. SPAWN MECHANISM & MEMORY INITIALIZATION

**Source:** `scripts/spawn_synapse.sh` (Phase 206.1+, MARKER_206.SYNAPSE_SPAWN_V2)

### Spawn Flow

```
spawn_synapse.sh Alpha cut-engine claude_code [INIT_PROMPT]
        ↓
1. Read model_tier from agent_registry.yaml (lines 96-119)
2. Build spawn command per agent_type (lines 154-198):
   - Claude Code: cd $WORKTREE && claude --dangerously-skip-permissions --model $MODEL_TIER
   - free_code: ... --bare --add-dir $WORKTREE (re-injects CLAUDE.md, disables OAuth)
   - opencode: cd $WORKTREE && opencode
3. Detect terminal backend (tmux / Terminal.app / iTerm2)
4. Create tmux session in detected backend
5. Register session in data/synapse_sessions.json
6. Wait 3-8s (by agent_type) for boot
7. Auto-send INIT_PROMPT via synapse_write.sh
```

### Bootstrap File: CLAUDE.md

**Key Detail:** CLAUDE.md is a **bootstrap-only stub**, NOT a conversation history cache.

- **Location:** `.claude/worktrees/<worktree>/CLAUDE.md` (per-role)
- **Content:** Minimal routing instructions + link to session_init
- **Generation:** `src/tools/generate_claude_md.py` (called post-merge)
- **Lifetime:** Regenerated every merge, not a persistent memory store

**Quote from generate_claude_md.py (lines 118-123):**
> "CLAUDE.md is now a bootstrap file only. All dynamic context (owned_paths, predecessor advice, key docs, pending tasks) comes from session_init's role_context — the universal JSON contract for any coding tool (Claude Code, Codex, Gemini, Cursor, MCC, Mycelium)."

### Default Init Prompt

**Default:** `"vetka session init"` (line 47)

**What session_init returns (from USER_GUIDE, lines 296-301):**
- `role_context` — callsign, domain, branch, owned_paths, blocked_paths
- `task_board_summary` — pending/claimed/done counts
- `predecessor_advice` — lessons from previous agent instance
- `protocol_status` — checklist (session_init ✓, task_board ?, claimed ?)

**Flow-stop signal:** If session_init is skipped, agent doesn't have:
- Role identity
- Task board access
- Path guards (owned vs blocked)
- Predecessor context

---

## 3. CLAUDE CODE SETTINGS & CONFIGURATION

**Source:** `~/.claude/settings.json`

```json
{
  "skipDangerousModePermissionPrompt": true
}
```

**Analysis:**
- **No conversation history limit** — Claude Code manages context internally
- **No max-turns or max-context flags** — controlled by API (Anthropic SDK)
- **Dangerous mode enabled** — agents can read/write freely (required for CI/CD)
- **No OAuth/keychain overrides** — free_code uses --bare to ignore saved creds

**Important:** Context window is **NOT configured in settings.json**. It's handled by:
1. Anthropic API (model-specific limits: Opus 200k, Sonnet 200k, Haiku 100k)
2. Claude Code's internal context management (auto-compacting)
3. Harness checkpoint system (explicit save on exhaustion)

---

## 4. CONTEXT EXHAUSTION & AUTO-RESTART SYSTEM

**Source:** `scripts/synapse_context_monitor.sh` (Phase 209.1, MARKER_209.CONTEXT_MONITOR)

### Detection Patterns (lines 32-42)

Claude Code emits these strings when context is full:
```
"conversation is getting long"
"context window"
"compacting conversation"
"auto-compact"
"messages were compressed"
"message limit"
"prior messages in your conversation"
"context limits"
"will automatically compress"
```

### Monitoring Loop

**Usage:**
```bash
scripts/synapse_context_monitor.sh              # one-time check
scripts/synapse_context_monitor.sh --daemon     # loop every POLL_INTERVAL
scripts/synapse_context_monitor.sh --status     # show compacting state
```

**Env vars (lines 13-16):**
```
SYNAPSE_POLL_INTERVAL=30      # seconds between checks
SYNAPSE_CAPTURE_LINES=50      # tmux lines to scan per check
SYNAPSE_AUTO_RESTART=true     # auto-restart on detection (default)
```

### Recovery Checkpoint (lines 71-128)

On context exhaustion:
1. **Save checkpoint** → `data/checkpoints/{ROLE}_checkpoint.json`
   - task_id (claimed task)
   - branch (current git branch)
   - files_modified (git diff --name-only)
   - checkpoint_time (ISO UTC)
   - detected_signal (the warning message)

2. **Kill session** → `tmux kill-session -t $SESSION_NAME`

3. **Respawn** → Call `spawn_synapse.sh` with recovery prompt:
   ```
   "CONTEXT RESTART: I was restarted due to context exhaustion.
    My previous task was $task_id. Please run:
    vetka session init role=$role — then check
    data/checkpoints/${role}_checkpoint.json for my saved state
    and resume the task."
   ```

4. **Clear flag** → `mark_compacting false` in session registry

**Note:** This is **explicit, not transparent**. The agent receives a message and must actively call session_init + read checkpoint.

---

## 5. TMUX HISTORY & TERMINAL CONFIGURATION

**Source:** `~/.tmux.conf` (3 lines)

```bash
set -g mouse on
set -g history-limit 50000          # ← KEY: tmux scrollback buffer
set -g status-style 'bg=colour235 fg=colour136'
```

### What history-limit does

- **50,000 lines** of terminal output buffering (tmux scrollback)
- **NOT conversation history** — it's raw tmux pane content
- **Per-session** — each tmux session has its own buffer
- **Cleared on session kill** — lost when agent is restarted

**Important distinction:** This is a **terminal buffer**, not Claude Code's internal conversation context. The conversation is **NOT preserved** via tmux scrollback.

---

## 6. MEMORY/CONTEXT SERVICES IN CODEBASE

**Source:** Search results for context management

### Services Found

| File | Purpose | Key Details |
|------|---------|------------|
| `src/memory/aura_store.py` | User preferences store | `max_tokens=500` for compression |
| `src/memory/spiral_context_generator.py` | Context assembly | `max_tokens=2000` per call |
| `src/tools/fc_loop.py` | Free-code loop utilities | `max_tokens=4000` default |
| `src/orchestration/task_board.py` | Session state (owned by Zeta) | Checkpoint support |
| `src/services/session_tracker.py` | Track agent state | Restarted flag detection |

None of these configure Claude Code's conversation history directly. They're **optional services** for specific workflows (memory, context packing).

---

## 7. DIFFERENCES: LOCAL CLI vs OAUTH vs FREE_CODE

### Claude Code (Local --dangerously-skip-permissions)

```bash
cd ~/.claude/worktrees/cut-engine
claude --dangerously-skip-permissions --model sonnet
```

- **Auth:** Local API key from env
- **Context:** Model's full context window (200k for Sonnet)
- **History:** Auto-compacting by Claude Code
- **Settings:** `~/.claude/settings.json` applies
- **Model selection:** Via `--model` flag (overrides any saved preference)

### Free-code (Gemma via LiteLLM + Bridge)

```bash
ANTHROPIC_BASE_URL=http://localhost:4001 ANTHROPIC_API_KEY=sk-ollama \
  ~/free-code/cli-dev --bare --dangerously-skip-permissions --model gemma4:e4b
```

- **--bare flag:** Skip OAuth, use ANTHROPIC_API_KEY strictly (Phase 165 fix)
- **--add-dir $WORKTREE:** Re-inject CLAUDE.md (lines 166-167)
- **Context:** Gemma 4 (4B/2B/26B params) — much smaller window
- **Bridge:** LiteLLM converts Anthropic→OpenAI→Ollama protocol
- **History:** Local Ollama model (no auto-compacting)

### Opencode (Qwen)

```bash
cd ~/.claude/worktrees/weather-core
VETKA_AGENT_ROLE=Lambda opencode -m opencode/qwen3.6-plus-free
```

- **Signal delivery:** `PRETOOL_HOOK` env var (Phase 205+)
- **Role detection:** VETKA_AGENT_ROLE env variable
- **Context:** Qwen 3.6 Plus Free (via Qwen API)
- **Settings:** No ~/.claude/settings.json (Opencode-specific config)
- **History:** Opencode manages internally

---

## 8. NOTIFICATION/SIGNAL SYSTEM

**Source:** `docs/USER_GUIDE_MULTI_AGENT.md` lines 341-466

### Signal Delivery (Phase 204+)

```
Commander: vetka_task_board action=notify target_role=Alpha message="..."
                ↓
        Data saved to ~/.claude/signals/Alpha.json
                ↓
        PreToolUse hook (scripts/check_notifications.sh)
                ↓
        Agent sees message AUTOMATICALLY before next tool call
                ↓
        Signal file deleted (one-shot)
```

**Signal file format:**
```json
[
  {"id": "notif_xxx", "from": "Commander", "message": "...", "ts": "ISO", "ntype": "custom"}
]
```

**Key:** Signal delivery is **not part of conversation history**. It's a separate **out-of-band notification channel** via file system + PreToolUse hook.

---

## 9. CONTEXT INJECTION VIA CLAUDE.md & ENVIRONMENT

### Root CLAUDE.md (lines 51-86)

Generic, visible to ALL agents:
```
## Start Here
1. mcp__vetka__vetka_session_init role=<YourCallsign>
2. mcp__vetka__vetka_task_board action=notifications
3. mcp__vetka__vetka_task_board action=ack_notifications
4. mcp__vetka__vetka_task_board action=list ...
5. Claim → Work → complete
```

**Mandatory: Steps 2-3 (notifications) MUST NOT be skipped.**

### Per-Role CLAUDE.md (generated)

Minimal template-based content:
```markdown
# Alpha — Engine Domain
## Role Context
- Callsign: Alpha
- Domain: engine
- Owned paths: [list from registry]
- Blocked paths: [list from registry]

## First Action
Run: `mcp__vetka__vetka_session_init role=Alpha`
```

**Note:** The actual content (docs, tasks, predecessor advice) is **NOT in CLAUDE.md**. It comes from session_init response.

---

## SUMMARY: Memory/Context Lifecycle

```
┌─────────────────────────────────────────────────────┐
│ SPAWN: spawn_synapse.sh Alpha cut-engine claude_code │
│  ├─ Read model_tier from agent_registry.yaml        │
│  ├─ Launch: claude --dangerously-skip-permissions   │
│  └─ Wait for boot (8s)                              │
├─────────────────────────────────────────────────────┤
│ BOOTSTRAP: Auto-send init_prompt (default: empty)   │
│  └─ First message: "vetka session init"             │
├─────────────────────────────────────────────────────┤
│ INITIALIZATION: session_init response               │
│  ├─ Load: role_context (owned/blocked paths)        │
│  ├─ Load: task board (pending tasks)                │
│  ├─ Load: predecessor advice                        │
│  └─ Load: protocol checklist                        │
├─────────────────────────────────────────────────────┤
│ ACTIVE SESSION: Normal conversation                 │
│  ├─ Claude Code manages internal context (200k)     │
│  ├─ Auto-compacting on exhaustion                   │
│  └─ Notifications via ~/.claude/signals/ (async)    │
├─────────────────────────────────────────────────────┤
│ EXHAUSTION: synapse_context_monitor.sh detects      │
│  ├─ Save checkpoint: data/checkpoints/{ROLE}.json   │
│  ├─ Kill tmux session                               │
│  └─ Respawn with recovery prompt                    │
├─────────────────────────────────────────────────────┤
│ RECOVERY: New session starts                        │
│  └─ Auto-send recovery init (with task_id hint)     │
└─────────────────────────────────────────────────────┘
```

**Key Finding:** Context is **NOT automatically preserved**. Each restart requires explicit session_init call.

---

## RECOMMENDATIONS FOR INTEGRATION

1. **For new agents:** Call `mcp__vetka__vetka_session_init role=<callsign>` first thing
2. **For context management:** Use checkpoint system (automatic) + session_init (manual recovery)
3. **For notifications:** Enable PreToolUse hook (install_notification_hooks.sh)
4. **For tmux history:** Increase history-limit beyond 50k if needed (e.g., 100k for long-running agents)
5. **For OAuth vs local:** Use --bare flag for free-code to avoid credential confusion

---

## FILE PATHS (RESEARCH)

- `scripts/spawn_synapse.sh` — spawn mechanism
- `scripts/synapse_context_monitor.sh` — context monitor
- `src/tools/generate_claude_md.py` — CLAUDE.md generator
- `data/templates/agent_registry.yaml` — role definitions
- `docs/USER_GUIDE_MULTI_AGENT.md` — user documentation
- `~/.claude/settings.json` — Claude Code settings (minimal)
- `~/.tmux.conf` — tmux config (history-limit=50000)

---

**Report Generated:** 2026-04-07
**VETKA Phase:** 210+ (Gemma Fleet Integration)
