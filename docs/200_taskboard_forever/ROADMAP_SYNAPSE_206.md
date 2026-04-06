# ROADMAP: SYNAPSE — Real Multi-Window Agent Spawn (Phase 206)
**Date:** 2026-04-04 | **Author:** Zeta (Harness) | **Status:** DRAFT
**Depends on:** Phase 205 (UDS Autospawn — DONE)
**Parent doc:** ARCH_AGENT_AUTOSPAWN_205.md

---

## Problem

Phase 205 autospawn works: notify → UDS daemon → spawn_agent.sh → tmux.
BUT the tmux session runs inside Commander's terminal context — invisible, not
truly independent. Commander cannot:
- See agent windows on screen
- Send prompts to running agents
- Spawn non-Claude-Code agents (Vibe, Opencode/Codex)

## Solution: SYNAPSE

**S**pawn **Y**our **N**ew **A**gent **P**rocess **S**eparately **E**verywhere

Three capabilities:
1. **SPAWN** — open agent in new Terminal/iTerm2 window (not tmux-only)
2. **WRITE** — inject prompt/task into running agent session
3. **WAKE** — activate sleeping agent via notification → inbox read

Four agent types:
- `claude_code` — CLI in terminal
- `opencode` — CLI in terminal (Codex)
- `vibe` — browser-based (Playwright)
- `generic_cli` — any CLI tool

## Architecture

```
Commander: action=notify target_role=Alpha message="claim tb_xxx"
  │
  └─→ UDS Daemon (Phase 204/205 — DONE)
       │
       └─ Agent OFFLINE → spawn_synapse.sh Alpha
            │
            ├─ agent_type=claude_code
            │   └─ osascript → new Terminal.app window
            │       └─ tmux new-session inside window (for send-keys access)
            │           └─ cd worktree && claude --dangerously-skip-permissions
            │
            ├─ agent_type=opencode
            │   └─ osascript → new Terminal.app window
            │       └─ tmux new-session inside window
            │           └─ cd worktree && opencode
            │
            └─ agent_type=vibe
                └─ open -a "Google Chrome" vibe_url
                    └─ (future: Playwright for prompt injection)
```

### Write-to-Session Flow
```
Commander: synapse_write(role=Alpha, prompt="implement feature X")
  │
  ├─ CLI agents (claude_code, opencode):
  │   └─ tmux send-keys -t vetka-Alpha "prompt text" Enter
  │
  └─ Vibe agents:
      └─ Playwright → find chat input → type → submit
```

### Wake Flow
```
Commander: action=notify target_role=Alpha (agent sleeping but session alive)
  │
  ├─ UDS daemon detects session exists (tmux has-session = true)
  │   └─ File signal already written by notify()
  │       └─ Agent's PreToolUse hook picks it up on next tool call
  │
  └─ If agent is idle (no tool calls happening):
      └─ tmux send-keys -t vetka-Alpha "/inbox" Enter
          └─ Forces agent to read notification inbox
```

## Terminal Spawn: osascript Strategy

### Terminal.app (universal, always available)
```bash
osascript -e '
  tell application "Terminal"
    activate
    do script "tmux new-session -s vetka-Alpha \"cd /path/to/worktree && claude --dangerously-skip-permissions\""
  end tell'
```

### iTerm2 (preferred if installed — tabs, profiles)
```bash
osascript -e '
  tell application "iTerm2"
    create window with default profile
    tell current session of current window
      write text "tmux new-session -s vetka-Alpha \"cd /path/to/worktree && claude --dangerously-skip-permissions\""
    end tell
  end tell'
```

### Fallback: headless tmux (CI/server, no GUI)
```bash
tmux new-session -d -s vetka-Alpha \
  "cd /path/to/worktree && claude --dangerously-skip-permissions"
```

Detection: check `$DISPLAY` or `lsappinfo list | grep iTerm2` → pick best backend.

## agent_registry.yaml v2 Schema

New fields per role:
```yaml
- callsign: "Alpha"
  agent_type: "claude_code"     # NEW: claude_code | opencode | vibe | generic_cli
  spawn_command: null            # NEW: override default spawn command
  vibe_url: null                 # NEW: for vibe agents only
  terminal_pref: "auto"         # NEW: auto | iterm2 | terminal_app | tmux
  # ... existing fields unchanged
```

## Task Breakdown

| ID | Title | Owner | Depends | Complexity |
|----|-------|-------|---------|------------|
| 206.1 | spawn_synapse.sh — multi-backend terminal spawn | Zeta | — | medium |
| 206.2 | agent_registry.yaml v2 — add agent_type, spawn fields | Zeta | — | low |
| 206.3 | UDS daemon — wire spawn_synapse.sh replacing spawn_agent.sh | Zeta | 206.1 | low |
| 206.4 | synapse_write.sh — send prompt to running agent session | Eta | 206.1 | medium |
| 206.5 | synapse_wake.sh — force inbox read on idle agent | Eta | 206.4 | low |
| 206.6 | TaskBoard action=spawn — Commander-facing spawn command | Zeta | 206.1,206.2 | medium |
| 206.7 | Vibe spawn backend — open browser + Playwright stub | Eta | 206.2 | medium |
| 206.8 | E2E test — spawn+write+wake chain | Delta | all | medium |

## Anti-Patterns (Do NOT Build)

| Anti-pattern | Why |
|---|---|
| SSH to localhost | Needless complexity, osascript is direct |
| Electron wrapper | Overkill for terminal spawn |
| Custom IPC for write | tmux send-keys already works |
| WebSocket live bridge to Vibe | Playwright is simpler for v1 |
| Headless-only spawn | Commander needs VISIBLE windows |

## Success Criteria

1. `notify target_role=Alpha` when Alpha offline → NEW Terminal.app window opens → claude boots → reads inbox → claims task
2. `synapse_write Alpha "implement X"` → text appears in Alpha's claude session
3. `synapse_wake Alpha` → Alpha reads notification inbox
4. Agent type `vibe` → Chrome opens to Vibe URL
5. All spawn backends auto-detected (iTerm2 > Terminal.app > tmux fallback)
