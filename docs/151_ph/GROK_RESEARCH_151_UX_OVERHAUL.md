# GROK RESEARCH PROMPT — Phase 151: UX Overhaul
## "From Developer Tool to Product People Love"
**Date: 2026-02-15**
**Context: User tested VETKA MCC for the first time, gave brutal honest feedback**

---

## WHAT IS VETKA

VETKA Mycelium Command Center (MCC) is a visual AI agent orchestration tool. Think: ComfyUI for AI agent pipelines.
- **DAG Editor** — drag & connect agent nodes (Scout → Architect → Coder → Verifier)
- **Pipeline Execution** — runs multi-model AI teams (Dragon Silver: Kimi + Grok + Qwen + GLM)
- **Task Board** — priority queue for tasks
- **Real-time Monitoring** — live streaming of agent progress
- **Playground** — git worktree sandboxes for safe agent experimentation

**Tech Stack:** React + TypeScript + xyflow/React Flow + Three.js, Tauri (Rust), Python FastAPI backend

---

## CURRENT STATE (What Exists)

### Layout (3-column)
```
┌──────────────────────────────────────────────────────────────────┐
│ [MCC] [◇silver▾] [●LIVE]    [Heartbeat off] [Playground 0] [0t 0r 0d] [stream] │
├──────────┬────────────────────────────────┬──────────────────────┤
│ TaskList │ DAG Canvas + WorkflowToolbar   │ DetailPanel          │
│ (220px)  │ (flex)                         │ (240px)              │
│          │  ┌─WorkflowToolbar─────────┐   │ Shows selected       │
│ P1 tasks │  │ ✎edit New Save Load... │   │ node/edge info       │
│ P2 tasks │  └───────────────────────────┘   │ + agent role config │
│          │  [DAG: smoothstep BT layout]  │                      │
│          │  ──StreamPanel (collapsed)──  │                      │
├──────────┴────────────────────────────────┴──────────────────────┤
│ [ARCHITECT click to chat]           [DISPATCH NEXT (4)]          │
└──────────────────────────────────────────────────────────────────┘
```

### 4 Top Tabs
- **MCC** — main workspace (DAG + tasks + detail)
- **STATS** — pipeline statistics (aggregated by preset)
- **ARCHITECT** — separate chat with planning LLM
- **BALANCE** — API key usage + costs

### Header Chips
- **HeartbeatChip** — right-click to edit interval (seconds input), left-click toggle
- **PlaygroundBadge** — shows count, dropdown with destroy button
- **"0t 0r 0d"** — total/running/done tasks mini-counter
- **stream** — toggle StreamPanel visibility

### WorkflowToolbar (inside DAG canvas, top)
```
[✎ edit] [name] [New] [Save] [Load ▾] [↩] [↪] [Validate ✓] [✦ Generate] [↓ Import] [↑ Export ▾] [▶ Execute]
```

### Connections
- Edge type: `smoothstep` (curved with rounded corners)
- Layout: Sugiyama Bottom-to-Top (root at bottom)
- Right-click node → Duplicate/Delete
- Right-click canvas → Add node (7 types)
- Right-click edge → Delete
- Drag from handle to handle → Create connection

---

## USER FEEDBACK (Raw, Prioritized)

### P0 — UNIFIED CONTROL BAR (Architecture)
**Problem:** Controls are scattered. Heartbeat in header, Workflow Save in canvas toolbar, Playground as chip, API key in Balance tab. User doesn't understand: "What are the 3 things I control?"

**User insight:** There are 3 core concepts:
1. **КТО** (WHO) — Team/Workflow (dragon_silver, custom workflow)
2. **ГДЕ** (WHERE) — Playground/Sandbox (disk location, git worktree)
3. **КОГДА** (WHEN) — Heartbeat (automatic trigger interval)

These 3 + API key should be the CENTRAL control panel in the header. Everything else flows from these 3 decisions.

**User wants:** "Like a 3-step onboarding: pick team → pick sandbox → set schedule → go!"

**Question for Grok:**
How should we design the unified control bar that houses WHO/WHERE/WHEN? Reference:
- ComfyUI's queue/prompt bar
- n8n's workflow header (name + save + execute in one row)
- Cursor IDE's model selector
- Linear's project switcher
- What patterns work for "3 core settings always visible"?
- Should this be a horizontal bar, a collapsible sidebar, or a floating control?

---

### P1 — ONBOARDING FLOW (UX)
**Problem:** Zero guidance. User opens MCC → sees empty DAG, cryptic chips, 20+ tasks in board, no idea what to do.

**User wants:** Step-by-step for first launch:
- Step 0: Enter/select API key
- Step 1: Choose team (preset selector)
- Step 2: Choose sandbox (create/select playground)
- Step 3: Start heartbeat OR type task directly in Architect chat

After setup: contextual tooltips on hover ("hover over node to see agent status", "click Execute to run workflow").
During pipeline: progress hints ("watch the Activity tab", "check Stats for team performance").

**Question for Grok:**
Design an onboarding system that:
1. Is NOT modal/wizard (doesn't block the app)
2. Shows progress dots (step 1/2/3/4)
3. Highlights relevant UI elements with glow/pulse
4. Disappears after first successful run
5. Can be re-triggered from Help menu

Reference: Figma's onboarding, Linear's first-run, VS Code's Getting Started, Notion's templates.
What's the best pattern for a tool that has 3-4 required settings before first use?

---

### P2 — EDGE ROUTING (Visual)
**Problem:** Edges make "roundabout loops" before connecting to nodes. Doesn't look like ComfyUI/n8n. Hard to follow cause-effect relationships.

**Current:** `smoothstep` edge type in xyflow + Sugiyama BT layout with dagre
- `rankdir: 'BT'` (bottom to top)
- `ranksep: 80px`, `nodesep: 50px`
- Edges curve around nodes, sometimes making U-turns

**User wants:** Clean, straight connections like:
- ComfyUI: horizontal left-to-right, straight lines with minimal curves
- n8n: vertical top-to-bottom, clean orthogonal routing
- Weaviate: simple direct connections

**Also:** "Go from root upward, like our VETKA tree metaphor"

**Question for Grok:**
1. xyflow edge types: `default` (bezier) vs `smoothstep` vs `straight` vs custom — which gives cleanest routing for BT DAGs?
2. Is dagre the right layout engine? Alternatives: ELK, d3-dag, @antv/layout?
3. How to prevent edge crossings and U-turns in BT layout?
4. ComfyUI uses a custom edge router with control points — should we implement similar?
5. How does n8n achieve clean orthogonal routing? Library or custom?
6. What's the optimal `ranksep`/`nodesep` for 5-10 node workflows?

---

### P3 — HEARTBEAT DROPDOWN (UX)
**Problem:** Right-click for interval is invisible (user tried, saw only "Reload, Inspect Element"). Interval in raw seconds (86399s = 24h) is inhuman.

**User wants:**
- Regular LEFT CLICK → dropdown menu (not right-click context menu)
- Human presets: 10 min, 30 min, 1 hour, 4 hours, 12 hours, 1 day, 1 week
- Custom interval input
- Start/Stop toggle IN the dropdown
- Must NOT interfere with manual task dispatch

**Question for Grok:**
Design a heartbeat dropdown that:
1. Opens on regular click
2. Has preset intervals with human labels
3. Shows a mini-status: last tick time, tasks dispatched, next tick countdown
4. Start/Stop toggle
5. Reference: GitHub Actions cron, Grafana alert interval, macOS Time Machine frequency
6. How to indicate "heartbeat is running but doesn't prevent manual actions"?

---

### P4 — STATS OVERHAUL (Data)
**Problem:** Current stats panel is "absolutely useless crap" (user's words). Shows:
- Vertical bar chart in horizontal space
- Only verifier self-assessment (agents grade themselves)
- No user feedback loop (approve/reject doesn't affect stats)
- No per-agent breakdown
- No way to identify weak agent in team
- No team comparison

**User wants:**
1. **Per-agent stats** — each agent (Scout, Architect, Researcher, Coder, Verifier) has its own metrics
2. **Per-team stats** — compare Dragon Bronze vs Silver vs Gold
3. **User feedback in stats** — approve/reject affects success rate
4. **Weak link detection** — which agent in the team fails most?
5. **Architect can use stats** to swap out underperforming agents
6. **Useful for both human and AI** — human sees "Coder fails 40% of time", Architect sees "switch to Qwen-235b"

**Current data sources:**
- `pipeline_stats` from AgentPipeline: preset, llm_calls, tokens, duration, verifier_avg_confidence
- `result_status` in TaskCard: applied/rejected/rework (user feedback)
- `feedback_service.py`: verifier low-score reports → `data/feedback/reports/`
- Per-subtask verifier: passed, confidence, issues, retry_count

**Question for Grok:**
Design a stats dashboard for AI agent team monitoring:
1. What metrics matter for each agent role? (Scout: files found, relevance; Coder: code quality, retries; Verifier: accuracy vs human agreement)
2. How to combine self-assessment (verifier) with human feedback (approve/reject)?
3. What visualization works for "5 agents in a pipeline, find the weak link"?
4. Reference: DataDog agent monitoring, Weights & Biases run comparison, MLflow model registry
5. Horizontal layout for horizontal space — what chart types?
6. Should stats be real-time (streaming) or historical (runs over time)?
7. How to make stats actionable for the Architect agent (auto-swap models)?

---

### P5 — PANEL = ZOOM Philosophy (Architecture)
**Problem:** Architect chat exists BOTH as a tab AND as a panel in DAG. Stats exist as a tab. This duplication confuses.

**User wants:** Single source of truth per panel:
- **Chat with Architect** — always the SAME chat. In DAG view it's a small panel on the right. Click "expand" → opens as full tab. Same state, same messages.
- **Stats** — same logic. Preview in DAG, expand to full tab.
- **Balance** — preview in DAG (compact), expand to full tab.

**Philosophy:** Every panel has 2 modes:
1. **Compact** — embedded in DAG view (right column or overlay)
2. **Expanded** — full tab (same component, different layout)

**Question for Grok:**
1. How do ComfyUI/n8n handle sidepanel ↔ fullscreen transitions?
2. React pattern for "same component, two layouts" (responsive vs separate routes)?
3. How does VS Code handle panel ↔ editor ↔ sidebar transitions?
4. Should we use a portal system, flexbox responsive breakpoints, or layout slots?
5. What's the cleanest way to keep state between compact ↔ expanded?

---

### P6 — NODE CREATION (UX)
**Problem:** Right-click shows only "Reload, Inspect Element" (browser context menu). DAG is NOT in edit mode by default. Even in edit mode, right-click context menu is hidden.

**User wants:** ComfyUI-style:
- Double-click on canvas → search popup for node types
- Or: drag from a palette/sidebar onto canvas
- Or: "+" button that opens node picker
- No right-click dependency

**Question for Grok:**
Node creation patterns in visual editors:
1. ComfyUI: double-click → search, right-click → node menu
2. n8n: "+" button → node catalog with search
3. Unreal Blueprints: right-click → search + category tree
4. Which pattern has lowest learning curve?
5. How to combine with our existing "+" button (bottom-left zoom controls)?
6. Should we add a sidebar node palette (always visible, drag to canvas)?

---

### P7 — CONNECTIONS HANDLING (UX)
**Problem:** Connections between nodes don't work intuitively. Right-click doesn't trigger connection in browser.

**Current:** xyflow handles are configured, `nodesConnectable={editMode}`. Should work by dragging from handle to handle.

**BUT:** Edit mode is OFF by default. User must click "✎ edit" first. This is invisible.

**Question for Grok:**
1. Should edit mode be ON by default? (ComfyUI is always editable)
2. Or: separate "view" vs "edit" toggle, but make it prominent?
3. How does n8n handle view-only vs edit mode?
4. Handle visibility: should source/target ports be always visible or appear on hover?
5. Connection validation: visual preview while dragging (can vs can't connect)?

---

### P8 — PLAYGROUND = WORKFLOW? (Concept)
**Problem:** User doesn't understand: "Why multiple playgrounds? Why would I keep them? Can a playground have multiple workflows?"

**Current architecture:**
- Playground = git worktree (isolated directory for safe agent writes)
- Workflow = DAG definition (nodes + edges + execution plan)
- They're NOT linked. You can run any workflow in any playground.

**User insight:** "Should 1 playground = 1 workflow? Or can one playground hold multiple commands?"

**Question for Grok:**
Design the relationship between Playground (execution sandbox) and Workflow (execution plan):
1. VS Code workspace ↔ task model: one workspace, many tasks
2. Docker container ↔ Docker Compose: one env, many services
3. Git branch ↔ PR model: one branch per feature, contains multiple commits
4. n8n: workflows are independent, no sandbox concept
5. ComfyUI: no sandbox, just queue/prompt

Which mental model works best for AI agent orchestration?
- **Option A:** 1 Playground = 1 Workflow (simple, clear)
- **Option B:** 1 Playground = N Workflows (flexible, workspace-like)
- **Option C:** Auto-create playground per workflow execution (transparent)
- **Option D:** No visible playground, always sandbox (hidden complexity)

Consider: our goal is "grandma can run Mycelium". Minimum visible complexity.

---

### P9 — IMPORT/EXPORT VISIBILITY (Feature)
**Problem:** User can't find Import/Export buttons. They're hidden in WorkflowToolbar inside the DAG canvas (only visible in edit mode).

**User wants:**
- Architect agent should auto-import from n8n/ComfyUI libraries
- Manual import also accessible from main menu / file picker
- Export available from workflow context menu

**Question for Grok:**
1. Where should Import/Export live? Top menu? Workflow context? Both?
2. How does n8n handle workflow sharing/import?
3. Should Architect agent have access to n8n/ComfyUI workflow libraries for search + adapt?
4. Is there a community library format we should support?

---

### P10 — VISUAL CONSISTENCY (Visual)
**Problem:** Buttons from different libraries. Inconsistent styling. "0t 0r 0d" and unknown symbols in header. Two "LIVE" indicators.

**User wants:** Swedish wardrobe — clean, uniform, every piece belongs.

**Question for Grok:**
1. Design token system for VETKA (colors, spacing, typography, border-radius)
2. Reference: Nolan palette (pure grayscale), accent = teal #4ecdc4
3. Button hierarchy: primary (filled) vs secondary (outline) vs ghost (text only)
4. How to audit and unify existing components?
5. Icon system: should we use Lucide, Phosphor, custom SVGs, or emoji?

---

## BONUS — EDGE ROUTING DEEP DIVE

User specifically called out:
> "Connections make roundabout before reaching the node. This prevents clear cause-effect understanding. Not like ComfyUI/n8n/Weaviate where everything is simple."

Current tech:
- xyflow with `smoothstep` edge type
- dagre layout with `BT` rankdir
- `ranksep: 80`, `nodesep: 50`
- No custom edge routing

**What we need:**
1. Clean vertical flow (bottom → top, like VETKA tree)
2. No U-turns or roundabouts
3. Minimal edge crossings
4. Straight segments where possible, curves only at turns
5. Similar visual quality to ComfyUI/n8n

**Grok: please analyze xyflow edge options and layout alternatives to achieve ComfyUI-quality routing.**

---

## DELIVERABLES EXPECTED FROM GROK

1. **Unified Control Bar** — wireframe + component structure
2. **Onboarding Flow** — step-by-step design + state machine
3. **Edge Routing** — recommended xyflow config + layout engine
4. **Heartbeat Dropdown** — wireframe + interval presets
5. **Stats Dashboard v2** — per-agent metrics + visualizations + data pipeline
6. **Panel Zoom Pattern** — React architecture for compact ↔ expanded
7. **Node Creation** — recommended pattern + wireframe
8. **Playground ↔ Workflow** — mental model recommendation + state diagram
9. **Import/Export** — location + Architect auto-import design
10. **Design Tokens** — color/spacing/typography system

**Format:** For each deliverable, provide:
- Recommended approach (one paragraph)
- Wireframe (ASCII or description)
- Key files to modify
- Estimated complexity (S/M/L)
- Reference links

---

## FILES FOR CONTEXT

```
# UI Components
client/src/components/mcc/MyceliumCommandCenter.tsx  — 3-column layout
client/src/components/mcc/DAGView.tsx                — DAG canvas (xyflow)
client/src/components/mcc/DAGContextMenu.tsx          — right-click menus
client/src/components/mcc/WorkflowToolbar.tsx         — Save/Load/Execute toolbar
client/src/components/mcc/HeartbeatChip.tsx           — heartbeat control
client/src/components/mcc/PlaygroundBadge.tsx          — playground status
client/src/components/mcc/StreamPanel.tsx              — pipeline event stream
client/src/components/mcc/nodes/TaskNode.tsx           — node visual
client/src/components/panels/DevPanel.tsx              — 4-tab container
client/src/components/panels/PipelineStats.tsx         — stats display
client/src/components/panels/ArchitectChat.tsx         — architect chat
client/src/components/panels/BalancesPanel.tsx         — API key management
client/src/components/panels/MCCTaskList.tsx            — task board list
client/src/components/panels/MCCDetailPanel.tsx        — selected item details

# Layout & Hooks
client/src/utils/dagLayout.ts           — Sugiyama BT layout + edge styling
client/src/hooks/useDAGEditor.ts        — edit mode, node/edge CRUD
client/src/hooks/useSocket.ts           — WebSocket events
client/src/stores/useMCCStore.ts        — MCC global state

# Backend
src/orchestration/agent_pipeline.py    — pipeline execution + stats collection
src/orchestration/task_board.py        — task board + stats recording
src/services/feedback_service.py       — verifier feedback collection
src/services/approval_service.py       — user approval workflow
src/api/routes/debug_routes.py         — REST API endpoints
```

---

*Written by Opus Commander for Grok 4.1 Research | Phase 151 | 2026-02-15*
