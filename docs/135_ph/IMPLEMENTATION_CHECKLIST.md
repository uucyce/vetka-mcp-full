# Phase 135: DAG-Centric MCC — Implementation Checklist

## Quick Reference

```
Main View:    DAGView.tsx (xyflow + dagre)
Detail Panel: DetailPanel.tsx
Backend:      dag_aggregator.py + dag_routes.py
WebSocket:    /ws/dag (real-time updates)
Layout:       Sugiyama inverted (root at bottom)
```

---

## Phase 135.1: DAG Foundation

### Install Dependencies
```bash
cd client
npm install @xyflow/react dagre @types/dagre
```

### Files to Create

- [ ] `client/src/types/dag.ts` — TypeScript interfaces
- [ ] `client/src/components/mcc/DAGView.tsx` — Main DAG component
- [ ] `client/src/components/mcc/nodes/TaskNode.tsx` — Task node (rectangle, bold)
- [ ] `client/src/components/mcc/nodes/AgentNode.tsx` — Agent node (rounded)
- [ ] `client/src/components/mcc/nodes/SubtaskNode.tsx` — Subtask node (small)
- [ ] `client/src/components/mcc/nodes/ProposalNode.tsx` — Proposal node (diamond)
- [ ] `client/src/utils/dagLayout.ts` — Sugiyama inverted layout helper

### Tasks
- [ ] Create DAGView with xyflow
- [ ] Implement `layoutSugiyamaInverted()` function
- [ ] Register custom node types
- [ ] Add Background, Controls, MiniMap
- [ ] Test with hardcoded 10-15 nodes

### MARKERs
| MARKER | File | Description |
|--------|------|-------------|
| 135.1A | DAGView.tsx | Main DAG visualization component |
| 135.1B | dagLayout.ts | Sugiyama inverted layout algorithm |
| 135.1C | TaskNode.tsx | Custom task node renderer |
| 135.1D | ProposalNode.tsx | Diamond-shaped proposal node |

---

## Phase 135.2: Data Integration

### Backend Files
- [ ] `src/services/dag_aggregator.py` — Build DAG from multiple sources
- [ ] `src/api/routes/dag_routes.py` — REST endpoints for DAG data

### Endpoints
- [ ] `GET /api/dag` — Full DAG data with filters
- [ ] `GET /api/dag/node/{id}` — Single node detail
- [ ] `POST /api/dag/node/{id}/action` — Execute action on node

### Aggregation Sources
- [ ] Task Board → layer 0 (root tasks)
- [ ] Pipeline tasks → layer 1 (agents)
- [ ] Subtasks → layer 2-3
- [ ] Proposals/Artifacts → layer 4

### Tasks
- [ ] Implement DAGAggregator class
- [ ] Connect to existing TaskBoard service
- [ ] Connect to pipeline_tasks.json
- [ ] Build edges from parent-child relationships
- [ ] Register dag_routes in `__init__.py`

### MARKERs
| MARKER | File | Description |
|--------|------|-------------|
| 135.2A | dag_aggregator.py | DAG data aggregation service |
| 135.2B | dag_routes.py | REST API for DAG data |

---

## Phase 135.3: Detail Panel

### Files
- [ ] `client/src/components/mcc/DetailPanel.tsx` — Right sidebar
- [ ] `client/src/components/mcc/NodeInfo.tsx` — Node details display
- [ ] `client/src/components/mcc/StatsBox.tsx` — Aggregated stats
- [ ] `client/src/components/mcc/ActionButtons.tsx` — Approve/Reject/Retry

### Features
- [ ] Show selected node info
- [ ] Display node metadata (duration, tokens, timestamps)
- [ ] Aggregated stats for visible graph
- [ ] Action buttons based on node type
- [ ] Code preview for subtasks
- [ ] Diff viewer for proposals
- [ ] Collapsible panel (maximize DAG view)

### MARKERs
| MARKER | File | Description |
|--------|------|-------------|
| 135.3A | DetailPanel.tsx | Right sidebar container |
| 135.3B | NodeInfo.tsx | Node details renderer |
| 135.3C | ActionButtons.tsx | Context-aware actions |

---

## Phase 135.4: Real-time Updates

### Backend
- [ ] `src/api/routes/dag_routes.py` — Add WebSocket endpoint
- [ ] Emit DAG updates on task status change
- [ ] Emit new node events (subtask spawned)
- [ ] Emit edge updates

### Frontend
- [ ] WebSocket connection in MyceliumCommandCenter
- [ ] Apply incremental updates to DAG state
- [ ] Animate new nodes (fade in)
- [ ] Pulse animation for running nodes
- [ ] Smooth position transitions

### MARKERs
| MARKER | File | Description |
|--------|------|-------------|
| 135.4A | dag_routes.py | WebSocket /ws/dag endpoint |
| 135.4B | DAGView.tsx | Real-time update handling |
| 135.4C | animations.css | Pulse + fade animations |

---

## Phase 135.5: Filters & Polish

### FilterBar
- [ ] `client/src/components/mcc/FilterBar.tsx`
- [ ] Status filter: all / pending / running / done / failed
- [ ] Time range: 1h / 6h / 24h / all
- [ ] Type filter: tasks / agents / subtasks / proposals

### Visual Polish
- [ ] Running nodes pulse animation
- [ ] Confidence glow on proposals
- [ ] Selected node highlight
- [ ] Edge hover tooltip
- [ ] Keyboard navigation (arrows, enter)

### MARKERs
| MARKER | File | Description |
|--------|------|-------------|
| 135.5A | FilterBar.tsx | Filter controls |
| 135.5B | styles.ts | Nolan palette + animations |

---

## File Structure (Final)

```
client/src/
├── types/
│   └── dag.ts                    # MARKER_135.1A_types
├── components/mcc/
│   ├── MyceliumCommandCenter.tsx # Main container (updated)
│   ├── DAGView.tsx               # MARKER_135.1A
│   ├── DetailPanel.tsx           # MARKER_135.3A
│   ├── FilterBar.tsx             # MARKER_135.5A
│   ├── NodeInfo.tsx              # MARKER_135.3B
│   ├── StatsBox.tsx              # Stats aggregation
│   ├── ActionButtons.tsx         # MARKER_135.3C
│   └── nodes/
│       ├── TaskNode.tsx          # MARKER_135.1C
│       ├── AgentNode.tsx
│       ├── SubtaskNode.tsx
│       └── ProposalNode.tsx      # MARKER_135.1D
└── utils/
    └── dagLayout.ts              # MARKER_135.1B

src/
├── services/
│   └── dag_aggregator.py         # MARKER_135.2A
└── api/routes/
    └── dag_routes.py             # MARKER_135.2B + 135.4A
```

---

## What Gets Removed (Migration)

After Phase 135 is complete, these become obsolete:

```
- DevPanel tabs system (Board, Stats, Test, Balance, Watcher, Artifacts)
- PipelineStats.tsx → absorbed into DetailPanel
- TaskCard.tsx → replaced by TaskNode.tsx
- WatcherStats.tsx → watcher events as edges
- BalancesPanel.tsx → metadata on agent nodes
```

Keep only:
- LeagueTester quick test (as modal)
- Quick Model Test (as popover)

---

## Success Criteria

### Must Have
- [ ] DAG renders with root at bottom
- [ ] Nodes show correct status colors
- [ ] Click node → details in panel
- [ ] Real-time updates work
- [ ] Filters work

### Should Have
- [ ] Pulse animation on running
- [ ] Confidence glow on proposals
- [ ] MiniMap navigation
- [ ] Smooth zoom/pan

### Nice to Have
- [ ] Keyboard navigation
- [ ] Edge hover tooltips
- [ ] Animated new nodes
- [ ] Collapse/expand subtrees

---

## Testing

```bash
# Unit tests
python -m pytest tests/test_dag_aggregator.py -v

# Frontend (manual)
1. Start backend: python -m src.main
2. Start frontend: cd client && npm run dev
3. Open http://localhost:3002/mcc
4. Dispatch a task
5. Verify DAG updates in real-time
```

---

*Phase 135 Implementation Checklist v2.0 — DAG-Centric*
*Updated: 2026-02-10*
