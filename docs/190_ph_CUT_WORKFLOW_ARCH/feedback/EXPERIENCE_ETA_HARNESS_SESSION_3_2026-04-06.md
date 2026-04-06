# Eta Harness Session 3 — 2026-04-06
**Agent:** Eta (Opus) | **Branch:** claude/harness-eta | **Duration:** ~2 hours

## Q1: What bugs did you find?
- LiteLLM system install broken on macOS — `from proxy_server import` fails. Must use venv.
- `tmux pane_last_activity` returns empty on macOS — only `session_activity` works for idle detection.
- `_GENERIC_ROOT_CLAUDE_MD` in generate_claude_md.py was missing notifications steps entirely (session_init -> task list, skipping notifications). This was the root cause of the wake bug.
- free-code validates model names against hardcoded list — rejects non-Anthropic models. LiteLLM proxy required as translation layer.
- `_auto_notify` on `NOTIF_TASK_COMPLETED` only notified Commander, not verification_agent. Delta never auto-woke on task complete.

## Q2: What unexpectedly worked?
- SSE buffer + replay approach for tool call conversion: buffer all stream events, detect tool calls in accumulated text, rebuild SSE with tool_use blocks. 7 tool calls converted in one session.
- Bulk CLAUDE.md regeneration from worktree template to all 15 worktrees in one Python pass.
- `_synapse_wake` tmux send-keys chain: Delta woke within 2s of notification, confirmed via pane capture ("Percolating...").
- tmux color application from agent_registry.yaml — instant visual distinction for 10 sessions.

## Q3: What idea came to mind?
- **The biggest lesson of this session:** we almost fell into a regression trap. I reported PARTIAL on the Gemma bridge test. Commander Bell read PARTIAL as failure and nearly pivoted to opencode. But PARTIAL meant "90% done, Gemma IS making tool calls, just wrong format." The correct fix was prompt engineering (tell Gemma the right format), not switching the entire client stack. This "broken telephone" effect (agent reports nuance -> commander reads binary) is a systemic risk in multi-agent orchestration.
- Agent activity monitor should check pane content for busy indicators ("Percolating", "Thinking"), not just session_activity epoch.
- Post-merge hook should auto-run `spawn_synapse.sh --recolor-all` so tmux colors update when registry changes.

## Q4: What tools/patterns would you want?
- `action=agent_activity` (built this session) — Commander calls one command, sees all agents.
- LiteLLM venv bootstrapper script — too many deps fail on system Python.
- Template regeneration as post-merge hook (not manual).

## Q5: What's the anti-pattern to avoid?
- Building converter layers instead of fixing the source (prompt engineering). My 250-line SSE bridge was a crutch — the correct fix is a system prompt + native function calling.
- Interpreting PARTIAL as FAIL without reading the full report. Multi-agent telephone game is dangerous.
- Installing Python packages globally on macOS — always use venv for tools like LiteLLM.

## Q6: Session output summary

### Commits on claude/harness-eta (8 total):
| Hash | Description |
|------|-------------|
| 5c7cf15e | CLAUDE.md template MANDATORY notifications (vibe/opencode/claude_code) |
| 6d696f17 | AGENTS.md template MANDATORY notifications |
| 08c54118 | Delta QA_AUTOFIX + all 15 roles regenerated |
| 2e3fe196 | action=agent_activity — tmux idle detection monitor |
| 914dda9c | SYNAPSE-UX tmux colors + --recolor-all flag |
| 4bcf55f1 | WAKE_CHAIN: auto-notify verifier on task complete |
| d506b8e2 | GEMMA-BRIDGE-2: JSON->tool_use SSE converter (works but is a crutch) |

### Commits on main:
| Hash | Description |
|------|-------------|
| a467c7dc2 | LITELLM_BRIDGE_TEST.md — PARTIAL verdict + full infrastructure doc |

### Docs created:
- docs/210_sherpa_gemma4/LITELLM_BRIDGE_TEST.md — test results
- docs/210_sherpa_gemma4/ROADMAP_GEMMA_BRIDGE_INTEGRATION.md — correct path forward

### Operational:
- Polaris respawned (opencode, captain worktree)
- All 10 tmux sessions color-coded
- Delta wake chain verified E2E (2s wake time)
- Vibe fleet (Lambda/Mu/Nu) blocked — no vibe CLI installed

### Next session priority:
1. Test native Ollama function calling for Gemma4 (curl test, 5 min)
2. If works: E2E with free-code (15 min) -> done
3. If fails: system prompt + thin XML parser (30 min)
4. Merge harness-eta to main (8 commits, all Delta-verified)
