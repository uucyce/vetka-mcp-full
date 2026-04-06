# ROADMAP: Signal Delivery — Phase 204
**Date:** 2026-04-04 | **Author:** Zeta (Harness Engineer) + Grok-4.1 (scalability review)
**Status:** APPROVED — ready for implementation
**Parent task:** tb_1775251260_77255_1 (ZETA-PUSH)
**Arch docs:** VETKA_RT_COMMS_ARCHITECTURE.md, RFC_UNIFIED_EVENT_BUS.md

---

## Problem

Commander sends `action=notify` to agents. Message lands in SQLite. User manually
runs between 5-8 terminal windows telling each agent to check notifications.
Infrastructure (Event Bus, UDS Daemon, MCP Receiver, File Inbox) is **built but not wired end-to-end**.

## What EXISTS (done_main)

| Layer | Task ID | File | Status |
|-------|---------|------|--------|
| Event Bus + AgentEvent + subscribers | tb_1774691652_55727_1 | src/orchestration/event_bus.py | done_main |
| UDS Daemon + UDSPublisher | tb_1774698370_8869_1 | scripts/uds_daemon.py | verified |
| MCPNotificationReceiver in mcp_bridge | tb_1774784237_9082_1 | src/mcp/vetka_mcp_bridge.py | done_main |
| File inbox + hook script | tb_1774675774_6996_1 | scripts/check_inbox.sh | done_main |

## Scalability Matrix (Grok analysis)

| CLI / Agent Type | Signal Path | Coverage | Notes |
|------------------|-------------|----------|-------|
| **Claude Code** (Alpha-Zeta, Eta) | file signal + settings.json PreToolUse hook | **100%** | Native hooks, ~/.claude/ |
| **Opencode** (Polaris, Lambda, Mu, Theta, Iota, Kappa) | file signal + env PRETOOL_HOOK | **~70%** | No settings.json, needs wrapper script |
| **Vibe CLI** (Mistral-1/2/3) | REST Gateway API webhook | **~50%** | No MCP hooks, API-first |
| **External** (Gemini, Kimi, Codex) | REST /api/gateway/notify | **~50%** | Webhook callback on claim |

**Strategy:** Phase 204 = Claude Code (instant win). Phase 205 = Opencode + others.

## What's MISSING

```
action=notify → SQLite ──────────────────────── DONE
                  ↓
           file signal write ─────────────────── 204.1 (Zeta)
                  ↓
           UDS Daemon running ────────────────── 204.2 (Zeta)
                  ↓
           hooks in agent settings.json ──────── 204.3 (Eta)
                  ↓
           E2E test: Commander → Agent sees ──── 204.4 (Delta)
                  ↓
           cross-CLI test: Opencode compat ───── 204.5 (Epsilon)
                  ↓
           docs updated ──────────────────────── 204.6 (Eta)
                  ↓
           Opencode signal wrapper ───────────── 204.7 (Eta, P2 — Phase 205 prep)
```

---

## Tasks

### 204.1 — Wire notify → file signal (Zeta, P1)
**Task ID:** tb_1775252923_23835_1
**File:** src/orchestration/task_board.py (notify handler)
**What:** After SQLite write, create JSON signal file:
```
~/.claude/signals/{target_role}.json  (append to array, not overwrite)
```
**Format:** `[{"id": "notif_xxx", "from": "Commander", "message": "...", "ts": "ISO"}]`
**Lines:** ~10 in task_board.py + mkdir -p guard
**Acceptance:** `action=notify target_role=Alpha` creates `~/.claude/signals/Alpha.json`

### 204.2 — UDS Daemon auto-start (Zeta, P1)
**Task ID:** tb_1775252927_23835_1
**File:** scripts/start_uds_daemon.sh (NEW), scripts/uds_daemon.py (exists)
**What:**
- Shell wrapper: PID file guard, start if not running
- launchd plist for macOS auto-start
- Socket: /tmp/vetka-events.uds
**Acceptance:** `./scripts/start_uds_daemon.sh` → daemon running, socket exists

### 204.3 — Agent hook installation (Eta, P1)
**Task ID:** tb_1775252935_23835_1
**Files:** scripts/check_notifications.sh (NEW), .claude/settings.json per worktree
**What:**
- Shell script: `stat ~/.claude/signals/{ROLE}.json` → if exists, cat + delete + stderr
- PreToolUse hook in each agent's settings.json
- Install via generate_claude_md.py --hooks or standalone script
**Constraint:** Hook <1sec. stat = instant, read+delete only when file exists
**Acceptance:** Signal file → agent sees message on next tool use

### 204.4 — E2E signal delivery test (Delta, P1)
**Task ID:** tb_1775252937_23835_1
**File:** tests/test_signal_delivery_e2e.py
**What:** Full cycle test (written by Delta from Zeta's spec):
1. Call `action=notify source_role=Commander target_role=Alpha message="test"`
2. Verify: signal file created at ~/.claude/signals/Alpha.json
3. Verify: JSON array format, correct fields (id, from, message, ts)
4. Run check_notifications.sh → verify output contains message
5. Verify: signal file deleted after read
6. Verify: multiple notifies append (not overwrite)
7. Verify: piggyback delivery via MCP task_board call includes push_notifications
**Acceptance:** 7 checks pass, <5sec total
**Depends on:** 204.1, 204.2, 204.3

### 204.5 — Cross-CLI compatibility test (Epsilon, P2)
**File:** tests/test_signal_opencode_compat.py
**What:** Verify signal delivery works for non-Claude agents:
1. Signal file path resolution with VETKA_AGENT_ROLE env var
2. check_notifications.sh works outside ~/.claude/ context
3. UDS Daemon accepts connections from non-MCP processes
4. REST /api/taskboard/notifications endpoint returns correct data
5. Concurrent signals to 5 agents don't race-condition
**Acceptance:** 5 checks pass. Document gaps for Phase 205
**Depends on:** 204.4

### 204.6 — Documentation update (Eta, P2)
**Task ID:** tb_1775252941_23835_1
**File:** docs/USER_GUIDE_MULTI_AGENT.md
**What:**
- "Signal Delivery" section: architecture, setup, troubleshooting
- Auto-start daemon instructions
- Commander workflow: no-relay model
- Agent launch with VETKA_AGENT_ROLE env var
- Known limitations: Opencode/Vibe → Phase 205
**Depends on:** 204.4 (confirmed working)

### 204.7 — Opencode signal wrapper (Eta, P2 — Phase 205 prep)
**File:** scripts/check_opencode_signals.sh (NEW)
**What:** Wrapper for Opencode agents:
- Signal dir: ~/.opencode/signals/ (or universal ~/.vetka/signals/)
- env PRETOOL_HOOK integration for Opencode CLI
- Same JSON format as Claude signals
- Reuse check_notifications.sh core logic with configurable signal_dir
**Acceptance:** Opencode agent with env VETKA_AGENT_ROLE=Lambda sees notifications

---

## Ownership Split

| Task | Owner | Model | Reason |
|------|-------|-------|--------|
| 204.1 — file signal write | **Zeta** | Opus | task_board.py = owned_path, core wiring |
| 204.2 — daemon auto-start | **Zeta** | Opus | scripts/uds_daemon.py = infra |
| 204.3 — hooks install | **Eta** | Sonnet | settings.json gen, shell scripts |
| 204.4 — E2E test | **Delta** | Haiku | QA spec execution, pytest |
| 204.5 — cross-CLI test | **Epsilon** | Haiku | Opencode compat, edge cases |
| 204.6 — docs | **Eta** | Sonnet | USER_GUIDE updates |
| 204.7 — Opencode wrapper | **Eta** | Sonnet | Shell scripts, Phase 205 prep |

## Dependencies

```
204.1 (Zeta: file signal) ──┐
                              ├──→ 204.4 (Delta: E2E test) ──→ 204.5 (Epsilon: cross-CLI)
204.2 (Zeta: daemon start) ──┘                                        ↓
204.3 (Eta: hooks) ──────────┘                                  204.6 (Eta: docs)
                                                                       ↓
                                                                 204.7 (Eta: Opencode wrapper)
```

**Parallelism:** Zeta (204.1+204.2) || Eta (204.3) — then Delta (204.4) → Epsilon (204.5) → Eta (204.6+204.7)

## Success Criteria

**Phase 204 (Claude Code):**
Commander sends `action=notify target_role=Alpha message="claim tb_xxx"` →
Alpha sees message in terminal within **next tool use** (<30sec) →
**Zero user intervention.**

**Phase 205 (Full fleet, future):**
Same flow works for Opencode (Lambda/Theta) + Vibe (Mistral-1) + External agents.
Signal dir: universal `~/.vetka/signals/` or per-CLI override.
