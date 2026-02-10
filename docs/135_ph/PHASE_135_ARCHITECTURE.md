# Phase 135: Mycelium Command Center — DAG Architecture

## Vision

**Единое окно вместо 7 вкладок.** DAG-граф как основной интерфейс, где все сущности (tasks, agents, subtasks, proposals) — это ноды, а их связи — рёбра.

**Корень внизу** — как в VETKA 3D. Пользователи привыкают к пространственной метафоре: основа внизу, ветвление вверх.

```
                         ┌─────────────┐
                         │  PROPOSAL   │  ← результат (верх)
                         │  conf: 0.87 │
                         └──────┬──────┘
                    ┌──────────┴──────────┐
                    ▼                     ▼
             ┌──────────────┐      ┌──────────────┐
             │   SUBTASK    │      │   SUBTASK    │  ← работа агентов
             │   coder      │      │   verifier   │
             └──────┬───────┘      └──────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
  ┌──────────┐┌──────────┐┌──────────┐
  │ ARCHITECT││RESEARCHER││  SCOUT   │  ← pipeline agents
  │  done    ││  done    ││  done    │
  └──────────┘└──────────┘└──────────┘
                    │
                    ▼
             ┌──────────────┐
             │    TASK      │  ← корень внизу
             │ "Add cache"  │
             └──────────────┘
```

---

## 1. Layout: Sugiyama Inverted

### 1.1 Слои (снизу вверх)

| Layer | Y Position | Content |
|-------|------------|---------|
| 0 | Bottom | Root tasks (from Task Board) |
| 1 | | Pipeline agents (Scout, Architect, Researcher) |
| 2 | | Subtasks (coder work items) |
| 3 | | Verifier results |
| 4 | Top | Proposals / Artifacts |

### 1.2 Визуальное кодирование

```
┌─────────────────────────────────────────────────────────────┐
│  NODE ENCODING                                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Status:                                                    │
│    pending  → border: #444 (dim)                            │
│    running  → border: #e0e0e0 + pulse animation             │
│    done     → border: #6a8a6a (green-gray)                  │
│    failed   → border: #8a6a6a (red-gray)                    │
│                                                             │
│  Confidence (proposals):                                    │
│    > 0.85   → glow: green, auto-approve ready               │
│    0.5-0.85 → glow: amber, needs review                     │
│    < 0.5    → glow: red, likely reject                      │
│                                                             │
│  Node Type:                                                 │
│    task     → rectangle, bold border                        │
│    agent    → rounded rectangle                             │
│    subtask  → small rectangle                               │
│    proposal → diamond shape                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  EDGE ENCODING                                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Type:                                                      │
│    structural → solid, #6a8a6a (parent-child)               │
│    dataflow   → dashed, #8aa0b0 (data passes)               │
│    temporal   → animated, #aa8a6a (sequence)                │
│                                                             │
│  Strength:                                                  │
│    weak       → strokeWidth: 1, opacity: 0.5                │
│    normal     → strokeWidth: 2, opacity: 0.7                │
│    strong     → strokeWidth: 3, opacity: 1.0                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Window Layout: DAG + Detail Panel

```
┌─────────────────────────────────────────────────┬──────────────────┐
│                                                 │                  │
│                  DAG VIEW                       │   DETAIL PANEL   │
│                  (80%)                          │      (20%)       │
│                                                 │                  │
│         [proposal]                              │ ┌──────────────┐ │
│             │                                   │ │  SELECTED    │ │
│      ┌──────┴──────┐                            │ │              │ │
│  [subtask]    [subtask]                         │ │ subtask_003  │ │
│      │                                          │ │ Status: done │ │
│   [agents]                                      │ │ Duration: 8s │ │
│      │                                          │ │ Tokens: 892  │ │
│   [task] ← root                                 │ │              │ │
│                                                 │ │ [View Code]  │ │
│                                                 │ │ [View Diff]  │ │
│                                                 │ └──────────────┘ │
│                                                 │                  │
│  ┌─────────────────────────────────────────┐    │ ┌──────────────┐ │
│  │ FILTERS                                 │    │ │   STATS      │ │
│  │ Status: [all ▾]  Time: [1h ▾]  Type: ▾ │    │ │ Total: 5     │ │
│  └─────────────────────────────────────────┘    │ │ Running: 1   │ │
│                                                 │ │ Success: 80% │ │
│  [─────────── MINIMAP ───────────]              │ └──────────────┘ │
│                                                 │                  │
└─────────────────────────────────────────────────┴──────────────────┘
```

### 2.1 DAG View Features

- **Pan & Zoom** — навигация по графу
- **Fit View** — показать весь граф
- **MiniMap** — overview в углу
- **Node Selection** — клик выбирает ноду
- **Multi-select** — shift+клик для группы
- **Filters** — скрыть/показать по статусу, типу, времени

### 2.2 Detail Panel Features

- **Node Info** — детали выбранной ноды
- **Stats Summary** — агрегированная статистика
- **Actions** — approve, reject, retry, view diff
- **Code Preview** — для subtasks с кодом
- **Collapsible** — можно свернуть для полноэкранного DAG

---

## 3. Data Model

### 3.1 DAG Node Types

```typescript
// client/src/types/dag.ts

type DAGNodeType = 'task' | 'agent' | 'subtask' | 'proposal' | 'artifact';

interface DAGNode {
  id: string;
  type: DAGNodeType;
  label: string;
  status: 'pending' | 'running' | 'done' | 'failed';

  // Visual encoding
  layer: number;           // Sugiyama layer (0 = bottom)
  confidence?: number;     // For proposals (0-1)

  // Metadata
  startedAt?: string;
  completedAt?: string;
  duration?: number;
  tokens?: number;

  // Links
  parentId?: string;       // For tree structure
  taskId: string;          // Root task reference
}

interface DAGEdge {
  id: string;
  source: string;
  target: string;
  type: 'structural' | 'dataflow' | 'temporal';
  strength: number;        // 0-1
  animated?: boolean;
}

interface DAGData {
  nodes: DAGNode[];
  edges: DAGEdge[];
  rootIds: string[];       // Task IDs at layer 0
}
```

### 3.2 Backend Aggregation

```python
# src/services/dag_aggregator.py

class DAGAggregator:
    """MARKER_135.2A: Aggregate all MCC data into DAG structure."""

    async def build_dag(self, filters: DAGFilters = None) -> DAGData:
        """Build unified DAG from multiple sources."""

        nodes = []
        edges = []

        # Layer 0: Tasks from Task Board
        tasks = await self.task_board.list_tasks(filters.status)
        for task in tasks:
            nodes.append(self._task_to_node(task, layer=0))

        # Layer 1: Pipeline agents
        for task in tasks:
            if task.pipeline_task_id:
                agents = await self._get_pipeline_agents(task.pipeline_task_id)
                for agent in agents:
                    nodes.append(self._agent_to_node(agent, task.id, layer=1))
                    edges.append(self._create_edge(task.id, agent.id, 'structural'))

        # Layer 2-3: Subtasks
        # Layer 4: Proposals
        # ...

        return DAGData(nodes=nodes, edges=edges, rootIds=[t.id for t in tasks])
```

---

## 4. API Endpoints

### 4.1 DAG Data

```python
# src/api/routes/dag_routes.py

@router.get("/api/dag")
async def get_dag(
    status: str = None,
    time_range: str = "1h",
    include_completed: bool = True,
) -> DAGData:
    """Get unified DAG data for visualization."""

@router.get("/api/dag/node/{node_id}")
async def get_node_detail(node_id: str) -> DAGNodeDetail:
    """Get detailed info for a specific node."""

@router.post("/api/dag/node/{node_id}/action")
async def node_action(node_id: str, action: str, params: dict = None):
    """Execute action on node (approve, reject, retry, etc.)."""
```

### 4.2 Real-time Updates

```python
# WebSocket for live DAG updates
@router.websocket("/ws/dag")
async def dag_websocket(websocket: WebSocket):
    """Stream DAG updates in real-time."""
    # Send node status changes
    # Send new nodes (subtasks spawned)
    # Send edge updates
```

---

## 5. Component Structure

```
client/src/components/
├── mcc/
│   ├── MyceliumCommandCenter.tsx   # Main container
│   ├── DAGView.tsx                 # DAG visualization (xyflow)
│   ├── DetailPanel.tsx             # Right sidebar
│   ├── FilterBar.tsx               # Status/time/type filters
│   └── nodes/
│       ├── TaskNode.tsx            # Custom node: task
│       ├── AgentNode.tsx           # Custom node: agent
│       ├── SubtaskNode.tsx         # Custom node: subtask
│       └── ProposalNode.tsx        # Custom node: proposal (diamond)
```

### 5.1 Main Component

```tsx
// client/src/components/mcc/MyceliumCommandCenter.tsx

export function MyceliumCommandCenter() {
  const [dagData, setDagData] = useState<DAGData | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [filters, setFilters] = useState<DAGFilters>(defaultFilters);

  // Fetch DAG data
  useEffect(() => {
    fetchDAG(filters).then(setDagData);
  }, [filters]);

  // WebSocket for real-time updates
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:5001/ws/dag');
    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      applyDAGUpdate(setDagData, update);
    };
    return () => ws.close();
  }, []);

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      {/* DAG View - 80% */}
      <div style={{ flex: 1 }}>
        <FilterBar filters={filters} onChange={setFilters} />
        <DAGView
          data={dagData}
          selectedNode={selectedNode}
          onNodeSelect={setSelectedNode}
        />
      </div>

      {/* Detail Panel - 20% */}
      <DetailPanel
        nodeId={selectedNode}
        dagData={dagData}
        onAction={handleNodeAction}
      />
    </div>
  );
}
```

### 5.2 DAG View with xyflow

```tsx
// client/src/components/mcc/DAGView.tsx

import ReactFlow, { Background, Controls, MiniMap } from 'xyflow';
import dagre from 'dagre';

export function DAGView({ data, selectedNode, onNodeSelect }: DAGViewProps) {
  const { nodes, edges } = useMemo(() => {
    if (!data) return { nodes: [], edges: [] };
    return layoutSugiyamaInverted(data);
  }, [data]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={customNodeTypes}
      onNodeClick={(_, node) => onNodeSelect(node.id)}
      fitView
      minZoom={0.2}
      maxZoom={3}
    >
      <Background color="#222" gap={24} />
      <Controls position="bottom-left" />
      <MiniMap
        position="bottom-right"
        nodeColor={getNodeColor}
        maskColor="rgba(10,10,10,0.85)"
      />
    </ReactFlow>
  );
}

function layoutSugiyamaInverted(data: DAGData) {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: 'BT' }); // Bottom-to-Top = root at bottom
  g.setDefaultEdgeLabel(() => ({}));

  // ... dagre layout logic
  // Returns positioned nodes and edges
}
```

---

## 6. Migration from Tabs

### What Gets Absorbed into DAG

| Old Tab | → DAG Representation |
|---------|---------------------|
| Board | Root nodes (layer 0) |
| Stats | Aggregated in Detail Panel |
| Test | Actions on nodes |
| Balance | Metadata on agent nodes |
| Watcher | Events as temporal edges |
| Artifacts | Artifact nodes (layer 4) |
| Playground | Experiment/Proposal nodes |

### What Stays Separate

- **Quick Model Test** → stays as modal/popover (не часть workflow)
- **League Benchmark** → stays as action button

---

## 7. Implementation Phases

### Phase 135.1: DAG Foundation
- [ ] Install xyflow + dagre
- [ ] Create DAGView component with Sugiyama inverted layout
- [ ] Custom node types (task, agent, subtask, proposal)
- [ ] Basic styling (Nolan monochrome)

### Phase 135.2: Data Integration
- [ ] DAGAggregator service
- [ ] `/api/dag` endpoint
- [ ] Connect to Task Board data
- [ ] Connect to Pipeline data

### Phase 135.3: Detail Panel
- [ ] DetailPanel component
- [ ] Node info display
- [ ] Stats summary
- [ ] Action buttons

### Phase 135.4: Real-time
- [ ] WebSocket `/ws/dag`
- [ ] Live node status updates
- [ ] New node animations
- [ ] Running node pulse effect

### Phase 135.5: Playground Integration
- [ ] Experiment nodes
- [ ] Proposal nodes (diamond shape)
- [ ] Confidence glow
- [ ] Approve/Reject actions

---

## 8. Visual Style: Nolan Monochrome

```typescript
const NOLAN_PALETTE = {
  // Backgrounds
  bg: '#0a0a0a',
  bgNode: '#111111',
  bgPanel: '#0d0d0d',

  // Borders & Lines
  borderDim: '#333333',
  borderNormal: '#555555',
  borderBright: '#888888',
  borderAccent: '#e0e0e0',

  // Text
  textDim: '#555555',
  textNormal: '#888888',
  textBright: '#cccccc',
  textAccent: '#e0e0e0',

  // Status (subtle, not saturated)
  statusRunning: '#e0e0e0',   // white pulse
  statusDone: '#6a8a6a',      // gray-green
  statusFailed: '#8a6a6a',    // gray-red
  statusPending: '#444444',   // dim gray

  // Confidence (for proposals)
  confHigh: '#6a8a6a',        // green-gray
  confMid: '#8a8a6a',         // amber-gray
  confLow: '#8a6a6a',         // red-gray

  // Edges
  edgeStructural: '#4a5a4a',
  edgeDataflow: '#5a6a7a',
  edgeTemporal: '#6a5a4a',
};
```

---

## 9. Success Criteria

- [ ] Single DAG view replaces 7 tabs
- [ ] Root tasks at bottom, proposals at top
- [ ] Real-time updates via WebSocket
- [ ] Node selection shows details
- [ ] Actions work from Detail Panel
- [ ] Filters work (status, time, type)
- [ ] MiniMap for navigation
- [ ] Smooth pan/zoom
- [ ] Running nodes pulse
- [ ] Proposals show confidence glow

---

## References

- Sugiyama Layout: Grok research `docs/135_ph/2D DAG в стиле Sugiyama_GROK.txt`
- xyflow: https://reactflow.dev (2026 leader for React DAG)
- dagre: https://github.com/dagrejs/dagre (Sugiyama algorithm)
- VETKA 3D: Inspiration for root-at-bottom metaphor

---

*Phase 135 Architecture v2.0 — DAG-Centric*
*Updated: 2026-02-10*
