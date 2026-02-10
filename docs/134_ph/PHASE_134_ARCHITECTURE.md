# Phase 134: Mycelium Command Center — Architecture Document

**Date:** 2026-02-10
**Status:** APPROVED
**Effort:** 8-10 days total
**Priority:** HIGH — enables autonomous monitoring & R&D pipeline

---

## Executive Summary

Phase 134 transforms DevPanel into **Mycelium Command Center (MCC)** — a standalone, floating Tauri window that provides complete autonomous monitoring and control of the VETKA agent ecosystem. MCC operates independently from the main VETKA window, enabling 24/7 pipeline oversight.

**Key Innovation:** Addition of **Playground** — an isolated R&D environment where agents autonomously experiment with codebase improvements, propose diffs, and await human approval before merge.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    VETKA Desktop (Tauri v2)                      │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐    ┌─────────────────────────────────┐ │
│  │   Main Window        │    │   Mycelium Command Center       │ │
│  │   (/index)           │    │   (/mycelium)                   │ │
│  │                      │    │                                 │ │
│  │  • 3D Knowledge      │    │  • Overview Dashboard           │ │
│  │    Graph             │    │  • Pipeline Arena               │ │
│  │  • Chat Interface    │    │  • Agent Hive                   │ │
│  │  • File Browser      │    │  • Knowledge Map                │ │
│  │                      │    │  • Resource Monitor             │ │
│  │                      │    │  • League Lab                   │ │
│  │                      │    │  • Artifact Forge               │ │
│  │                      │    │  • Playground (NEW)             │ │
│  └─────────────────────┘    └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                               │
                   ┌───────────┴───────────┐
                   ▼                       ▼
          ┌──────────────┐       ┌───────────────────┐
          │ FastAPI      │       │ mycelium_playground/│
          │ Port 5001    │       │ (Isolated R&D Fork) │
          │              │       │                     │
          │ /api/tasks   │       │ • Scoped MCP tools  │
          │ /api/debug   │       │ • task_board_pg.json│
          │ /api/playground│     │ • Agent experiments │
          └──────────────┘       └───────────────────┘
```

---

## Visual Identity

**Theme:** Christopher Nolan Batman — cold, industrial, monochrome

| Element | Color | Hex |
|---------|-------|-----|
| Background | Deep matte black | `#0a0a0a` |
| Panel | Charcoal | `#111111` |
| Border | Dark gray | `#222222` |
| Text | Light gray | `#e0e0e0` |
| Text muted | Medium gray | `#aaaaaa` |
| Accent | Cold teal-gray | `#4a6b8a` |
| Success | Dark green | `#2a3a2a` |
| Error | Dark red | `#3a2a2a` |

**Typography:** Monospace, sharp edges, no decorations, no emojis

---

## 8 Tabs Architecture

### 1. OVERVIEW (Dashboard)
- Knowledge Level Distribution (horizontal bar chart)
- Token Burn Timeline (area chart, last 20 min)
- Active Agents status bar
- Live connection indicator

### 2. PIPELINES (Pipeline Arena)
- Gantt-style timeline with RALF retries
- Live subtask progress
- Verifier confidence meters
- Cancel/restart controls

### 3. AGENTS (Agent Hive)
- Force-directed agent graph
- Memory heatmap (CAM + Engram usage)
- Claim/release controls
- Agent type badges

### 4. KNOWLEDGE (Knowledge Map)
- HDBSCAN clusters visualization
- Knowledge Level distribution
- Clickable cluster exploration
- Sugiyama layout minimap

### 5. RESOURCES (Resource Monitor)
- BalancesPanel (existing)
- Token usage by provider
- Watcher status
- Rate limit warnings

### 6. LEAGUE (League Lab)
- Tester panel (existing)
- Model comparison matrix
- Preset performance stats

### 7. ARTIFACTS (Artifact Forge)
- ArtifactViewer (existing)
- Approve/reject/rework buttons
- Diff preview
- Git staging integration

### 8. PLAYGROUND (NEW — R&D Laboratory)
- Agent proposals table
- Confidence scores
- Side panel diff viewer
- Approve & Merge / Reject buttons
- Token budget tracker
- Proposal statistics

---

## Implementation Phases

### Phase 134.1: Tauri Multi-Window Foundation (1 day)

**Files:**
- `client/src-tauri/tauri.conf.json`
- `client/src-tauri/src/main.rs`
- `client/src/App.tsx`
- `client/src/MyceliumStandalone.tsx` (NEW)

**Tasks:**

#### C34A: Window Configuration
```json
// tauri.conf.json → windows array
{
  "label": "mycelium",
  "title": "Mycelium Command Center",
  "width": 960,
  "height": 680,
  "decorations": true,
  "alwaysOnTop": false,
  "resizable": true,
  "visible": false,
  "url": "/mycelium"
}
```
**MARKER:** `MARKER_134.C34A`

#### C34B: Rust Commands
```rust
// main.rs
#[tauri::command]
async fn open_mycelium(app: tauri::AppHandle) -> Result<(), String>;

#[tauri::command]
async fn close_mycelium(app: tauri::AppHandle) -> Result<(), String>;
```
**MARKER:** `MARKER_134.C34B`

#### C34C: React Route
```tsx
// App.tsx
<Route path="/mycelium" element={<MyceliumStandalone />} />
```
**MARKER:** `MARKER_134.C34C`

#### C34D: Toolbar Button
```tsx
import { invoke } from '@tauri-apps/api/core';
<button onClick={() => invoke('open_mycelium')}>MYCELIUM</button>
```
**MARKER:** `MARKER_134.C34D`

---

### Phase 134.2: Core Component (2 days)

**Files:**
- `client/src/components/dev/MyceliumCommandCenter.tsx` (NEW)
- `client/src/hooks/useMyceliumSocket.ts`

**Tasks:**

#### C34E: Main Component Shell
- 8-tab navigation
- Nolan color scheme
- Header with connection status
- Footer with stats
**MARKER:** `MARKER_134.C34E`

#### C34F: Data Fetching Layer
- useCallback for fetchOverview
- 8-second polling interval
- WebSocket event listeners
- Error handling
**MARKER:** `MARKER_134.C34F`

#### C34G: Overview Tab
- Knowledge Level Distribution (Recharts BarChart)
- Token Burn Timeline (Recharts AreaChart)
- Active Agents (AgentStatusBar integration)
**MARKER:** `MARKER_134.C34G`

---

### Phase 134.3: Charts & Visualizations (2-3 days)

**Files:**
- `client/src/components/dev/charts/KnowledgeLevelChart.tsx` (NEW)
- `client/src/components/dev/charts/TokenBurnTimeline.tsx` (NEW)
- `client/src/components/dev/charts/PipelineFlowGantt.tsx` (NEW)
- `client/src/components/dev/charts/AgentHiveGraph.tsx` (NEW)
- `client/src/components/dev/charts/ClusterMapMini.tsx` (NEW)

**Tasks:**

#### C34H: Knowledge Level Chart
- Vertical bar + pie hybrid
- 5-bucket distribution (0.0-0.2, 0.2-0.4, etc.)
- Cold teal gradient colors
**MARKER:** `MARKER_134.C34H`

#### C34I: Token Burn Timeline
- Line + Area chart
- Real-time updates
- Cost overlay
**MARKER:** `MARKER_134.C34I`

#### C34J: Pipeline Flow Gantt
- Horizontal timeline
- RALF retry markers
- Phase duration bars
- Subtask indicators
**MARKER:** `MARKER_134.C34J`

#### C34K: Agent Hive Graph
- Force-directed layout
- Status-based node colors
- Click to select
- Memory usage indicators
**MARKER:** `MARKER_134.C34K`

---

### Phase 134.4: Playground Tab (2-3 days)

**Files:**
- `client/src/components/dev/PlaygroundTab.tsx` (NEW)
- `src/api/routes/playground_routes.py` (NEW)
- `data/playground_proposals.json` (NEW)
- `scripts/mirror_to_playground.py` (NEW)

**Tasks:**

#### C34L: Playground Backend
```python
# playground_routes.py
@router.get("/proposals")
async def get_playground_proposals()

@router.post("/{proposal_id}/approve")
async def approve_proposal()

@router.post("/{proposal_id}/reject")
async def reject_proposal()
```
**MARKER:** `MARKER_134.C34L`

#### C34M: Proposals Table
- Sortable columns (agent, confidence, status)
- Row click → select
- Status badges (pending/accepted/rejected)
- Token usage column
**MARKER:** `MARKER_134.C34M`

#### C34N: Review Side Panel
- Slide-in from right (520px)
- Diff preview (monospace, syntax highlighting)
- Files changed list
- Approve & Merge button
- Reject with reason button
**MARKER:** `MARKER_134.C34N`

#### C34O: Mirror Script
```python
# scripts/mirror_to_playground.py
- rsync-based incremental sync
- Exclude patterns (data/, node_modules/, .git/)
- Create .mcp_playground.json
- Logging + summary
```
**MARKER:** `MARKER_134.C34O`

---

### Phase 134.5: Integration & Polish (2 days)

**Files:**
- Existing DevPanel.tsx (add standalone prop)
- BalancesPanel, ArtifactViewer, AgentStatusBar (lazy load)

**Tasks:**

#### C34P: Lazy Loading
```tsx
const BalancesPanel = lazy(() => import('./BalancesPanel'));
const ArtifactViewer = lazy(() => import('./ArtifactViewer'));
```
**MARKER:** `MARKER_134.C34P`

#### C34Q: Virtualization
- react-window for long lists
- Virtualized task table
- Virtualized artifact list
**MARKER:** `MARKER_134.C34Q`

#### C34R: Keyboard Shortcuts
- `j/k` — navigate list
- `r` — refresh
- `a` — approve selected
- `x` — reject selected
- `Escape` — close panel
**MARKER:** `MARKER_134.C34R`

#### C34S: Notifications
- Tauri notification on proposal complete
- Toast for approve/reject actions
- Connection lost warning
**MARKER:** `MARKER_134.C34S`

---

## API Endpoints

### Existing (from Phase 133)
- `GET /api/tasks` — list tasks
- `POST /api/tasks` — create task
- `POST /api/tasks/{id}/dispatch` — dispatch
- `GET /api/tasks/concurrent` — concurrency info

### New for Phase 134

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/debug/playground/proposals` | GET | List all proposals |
| `/api/debug/playground/{id}/approve` | POST | Approve proposal |
| `/api/debug/playground/{id}/reject` | POST | Reject proposal |
| `/api/debug/playground/stats` | GET | Playground statistics |
| `/api/debug/knowledge-levels` | GET | Knowledge level distribution |
| `/api/debug/usage/history` | GET | Token burn history |

---

## Data Files

### New Files
- `data/playground_proposals.json` — agent proposals storage
- `data/task_board_playground.json` — playground-specific task board
- `data/stats_playground.json` — playground metrics

### Proposal Schema
```typescript
interface PlaygroundProposal {
  id: string;                    // "prop_1740001234"
  agent: string;                 // "dragon_gold", "claude_code"
  description: string;           // What this proposal does
  confidence: number;            // 0.0-1.0 (verifier score)
  status: 'pending' | 'reviewed' | 'accepted' | 'rejected';
  diff_preview: string;          // Unified diff string
  tokens_used: number;           // LLM tokens consumed
  created_at: number;            // Unix timestamp
  files_changed: string[];       // Affected file paths
  reviewed_at?: number;          // When reviewed
  review_reason?: string;        // Approval/rejection reason
}
```

---

## Playground Isolation Architecture

```
Main Codebase (/vetka_live_03/)
    │
    │  rsync --exclude data/ node_modules/ .git/
    ▼
Playground Fork (/mycelium_playground/)
    │
    ├── .mcp_playground.json     (scoped config)
    ├── src/                      (mirror of main src)
    ├── data/
    │   ├── task_board_playground.json
    │   └── pipeline_tasks_playground.json
    │
    └── Agents experiment here...
            │
            │ Proposal with confidence > 0.95
            ▼
        ┌─────────────────────────┐
        │  Unified Diff + Tests   │
        └───────────┬─────────────┘
                    │
                    ▼
        ┌─────────────────────────┐
        │  Human Review in MCC    │
        │  (Playground Tab)       │
        └───────────┬─────────────┘
                    │
            Approve │ Reject
                    ▼
        ┌─────────────────────────┐
        │  Apply to Main Codebase │
        └─────────────────────────┘
```

### Scoped MCP Tools
- `scoped_read_file` — read only from playground dir
- `scoped_edit_file` — write only to playground dir
- `scoped_run_tests` — run tests in playground context
- `generate_proposal_diff` — create unified diff

### Safety Limits
- Max 3 parallel pipelines
- 2M tokens/day budget
- Verifier gate threshold: 0.95
- Timeout: 300s per pipeline
- No writes to main codebase

---

## File Structure Summary

```
client/
├── src/
│   ├── components/
│   │   └── dev/
│   │       ├── MyceliumCommandCenter.tsx  (NEW)
│   │       ├── PlaygroundTab.tsx          (NEW)
│   │       └── charts/
│   │           ├── KnowledgeLevelChart.tsx
│   │           ├── TokenBurnTimeline.tsx
│   │           ├── PipelineFlowGantt.tsx
│   │           ├── AgentHiveGraph.tsx
│   │           └── ClusterMapMini.tsx
│   ├── MyceliumStandalone.tsx             (NEW)
│   └── App.tsx                            (update routes)
└── src-tauri/
    ├── tauri.conf.json                    (add window)
    └── src/main.rs                        (add commands)

src/
└── api/
    └── routes/
        └── playground_routes.py           (NEW)

scripts/
└── mirror_to_playground.py                (NEW)

data/
├── playground_proposals.json              (NEW)
├── task_board_playground.json             (NEW)
└── stats_playground.json                  (NEW)
```

---

## Execution Order

```
Week 1:
├── Day 1: C34A-D (Tauri multi-window)
├── Day 2-3: C34E-G (Core component + Overview)
└── Day 4-5: C34H-K (Charts)

Week 2:
├── Day 6-7: C34L-O (Playground tab + backend)
└── Day 8-10: C34P-S (Polish + integration)
```

---

## DO NOT TOUCH
- Backend Python logic (except new endpoints)
- Existing DevPanel.tsx internals (just add standalone prop)
- main.py
- approval_service.py
- agent_pipeline.py (except playground_mode if needed)

---

## Success Criteria

1. MCC opens as independent floating window
2. All 8 tabs functional with live data
3. Playground proposals flow: create → review → approve/reject
4. Charts render without lag (< 100ms)
5. WebSocket connection maintained independently from main window
6. Token budget enforced for playground experiments
7. Tests: 20+ new tests for Phase 134 components

---

## References

- Grok Research: `docs/134_ph_Myc_MCC/MCC_GROK.txt`
- Grok Research: `docs/134_ph_Myc_MCC/MyceliumCommandCenter_GROK`
- Grok Research: `docs/139_ph/Mycelium Playground_Grok.txt`
- Grok Research: `docs/139_ph/mirror_to_playgroundGROK.txt`
- Grok Research: `docs/139_ph/MyceliumCommandCenter_tsxGROK`
- Tauri Multi-Window: `docs/133_ph/CURSOR_BRIEF_134_DEVPANEL_WINDOW.md`
- Model Presets: `data/templates/model_presets.json`
