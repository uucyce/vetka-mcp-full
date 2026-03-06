# MARKER_160_MYCELIUM_SECURITY_POSITIONING_REVIEW_2026-03-06

Date: 2026-03-06  
Scope: `danilagoleen/mycelium` mirror + MCC module (`client/src/components/mcc`) + modular OSS positioning.

## 1) Security Check: token/key leakage

### What was checked
- Working tree scan in MCC prefix for common secret patterns (`github_pat_`, `ghp_`, `sk-`, `x-access-token`, `*_API_KEY`, private-key blocks).
- History scan for MCC path (`git log -p -- client/src/components/mcc`) against same patterns.
- Split commit (`git subtree split --prefix=client/src/components/mcc`) scanned directly before/after mirror push.
- Remote refs audit for `mycelium` (`heads/tags`).
- Verification that `docs/160_git/secret.r` and `secret.rtf` are not tracked in git.

### Result
- No key/token material detected in current MCC source or MCC commit history by pattern-based scan.
- `mycelium` remote has one branch only (`main`) and no tags/extra refs.
- Secret files under `docs/160_git/` are local workspace artifacts and are **not tracked** in git.

### Residual risk (critical view)
- Pattern scan reduces risk, but does not replace full secret scanner entropy checks.
- Recommendation: add CI secret scan (e.g. gitleaks/trufflehog) on each push in `mycelium`.

## 2) Mycelium in VETKA module graph

Current mirror map already in use:
- `src/mcp -> vetka-mcp-core`
- `src/bridge -> vetka-bridge-core`
- `src/search -> vetka-search-retrieval`
- `src/memory -> vetka-memory-stack`
- `src/scanners -> vetka-ingest-engine`
- `src/elisya -> vetka-elisya-runtime`
- `src/orchestration -> vetka-orchestration-core`
- `client/src/components/chat -> vetka-chat-ui`
- `client/src/components/mcc -> mycelium`

### Recommended next core modules to publish
1. `vetka-core` (new umbrella runtime contract package)
- Goal: stable shared contracts for IDs, session state, graph payloads, run events, model-routing envelopes.
- Value: prevents schema drift between UI/runtime/MCP modules.

2. `vetka-memory-core` (or strengthen `vetka-memory-stack` public surface)
- Goal: clear API for short/long memory, pinning, retrieval policy, context budget.
- Value: makes memory system reusable beyond current monorepo topology.

3. `vetka-runtime-contracts` (optional split)
- Goal: typed contracts for DAG nodes/edges, workflow tabs, execution lifecycle, telemetry.
- Value: safer independent releases for UI and backend.

## 3) External OSS dependencies to acknowledge

Already referenced in MCC credits:
- React
- TypeScript
- Framer Motion
- react-draggable
- React Flow (`@xyflow/react`)

Recommended to ensure consistent attribution across modules where used:
- n8n (workflow automation ecosystem reference)
- ComfyUI (visual node-based AI workflow precedent)
- OpenHands (agent automation patterns)

Note: list only where code/design patterns or integrations are actually used; avoid decorative attribution.

## 4) Competitive landscape and positioning (pragmatic)

Target comparison set (as requested): OpenClaw, Ralph Loop, G3, OpenHands, n8n, ComfyUI.

### Practical differentiation for `mycelium`
- DAG is not decorative: it is the primary operator surface for navigation and execution context.
- Multi-window command cockpit (Tasks/Chat/Context/Stats/Balance) keeps runtime state visible without mode switching.
- Minimize-to-dock + restore-to-last-position supports long sessions with high UI density.
- Context-aware team operation: graph + chat + runtime controls in one loop.
- Works as standalone UI shell, but unlocks full power with memory/routing/MCP modules.

### Critical caveat
- Claiming "better than X" should be framed as measurable outcomes (latency, task completion rate, context-switch count, operator error rate).
- Recommendation: publish benchmark methodology before strong superiority claims.

## 5) Simple product mechanic (for README / pitch)

- You operate in a live project DAG.
- Every mini-window is a tool, not a page (chat, tasks, context, telemetry).
- Windows can be expanded or minimized into dock previews, then restored where the user left them.
- New scope can be opened as separate visual tab/window context.
- Under the hood: model routing runtime + memory stack + MCP bridge + orchestration contracts.
- With configured keys, model routing can span a broad provider/model pool and fallback chains.

## 6) GitHub discovery tags (applied for `mycelium`)

Applied topics:
- `mycelium`
- `vetka`
- `dag-ui`
- `knowledge-graph`
- `multi-agent`
- `ai-agents`
- `agent-orchestration`
- `workflow-orchestration`
- `command-center`
- `operator-ui`
- `workspace-ui`
- `multi-window`
- `context-engine`
- `human-in-the-loop`
- `react`
- `tauri`

## 7) Action backlog

1. Add CI secret scanning workflow in `mycelium`.
2. Publish `vetka-core` contracts package (minimum shared schemas).
3. Publish explicit memory API docs (`vetka-memory-stack` public contract).
4. Add benchmark section (UI/runtime metrics) before aggressive competitor messaging.
