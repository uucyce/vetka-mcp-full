# MARKER 155: MCC Architecture Redux — Grand Unified DAG Vision
**Date:** 2026-02-18
**Status:** 🏗️ ARCHITECTURAL SPECIFICATION
**Author:** Claude Opus (Mycelium Architect)

## Status and Canonical Plan
- This document is architectural rationale/history for MARKER 155 direction.
- Canonical implementation sequencing and marker ownership is now tracked in:
  - `docs/155_ph/CODEX_UNIFIED_DAG_MASTER_PLAN.md`
- If there is a conflict between this file and execution order, follow the master plan.

---

## 🎯 Executive Summary

**Current State:** Fragmented UI with window switching (roadmap ↔ tasks ↔ workflow)
**Target State:** Single unified DAG canvas with infinite drill-down (zoom)
**Philosophy:** "Even grandma can use it" — max 3 actions, one view, progressive disclosure

---

## 📐 Core Concept: Unified DAG with Drill-Down

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNIFIED DAG CANVAS                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  LEVEL 0: Project Architecture (Zoom: 100%)                     │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐                │
│  │ Frontend │────→│  Backend │────→│ Database │                │
│  └──────────┘     └──────────┘     └──────────┘                │
│       │                │                │                       │
│       ▼                ▼                ▼                       │
│  [Double-click to drill]                                       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  After Drill: LEVEL 1: Module Tasks (Zoom: 200%)                │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐                │
│  │Task 001  │────→│Task 002  │────→│Task 003  │                │
│  │[PENDING] │     │[RUNNING] │     │[DONE]    │                │
│  └──────────┘     └──────────┘     └──────────┘                │
│       │                │                │                       │
│       ▼                ▼                ▼                       │
│  [Double-click task for workflow]                              │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  After Drill: LEVEL 2: Task Workflow (Zoom: 400%)               │
│  ┌─────────┐                                                   │
│  │Scout    │──┐                                                │
│  │@folder  │  │                                                │
│  └─────────┘  │     ┌─────────┐      ┌─────────┐              │
│               └────→│Architect│─────→│Coder    │              │
│                     │@plan    │      │@qwen3   │              │
│                     └─────────┘      └─────────┘              │
│                           │                  │                 │
│                           ▼                  ▼                 │
│                     ┌─────────┐      ┌─────────┐              │
│                     │Verifier │      │[Output] │              │
│                     │@glm4    │      │Artifact │              │
│                     └─────────┘      └─────────┘              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Navigation: Mouse wheel zoom, Pan by drag, Double-click drill, Esc zoom out
```

---

## 🏗️ Architecture Layers

### LAYER 1: Wizard Flow (Steps 1-3)
**File:** `WizardContainer.tsx` (✅ Already created)

**Purpose:** Progressive disclosure — user sees ONLY current step

**Step 1: Launch** (No Step Indicator)
```
┌─────────────────────────────────────────────────┐
│  🚀 New Project                                 │
│  How would you like to start?                   │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │   📁     │  │   🔗     │  │   ✨     │     │
│  │  Select  │  │   Clone  │  │  Create  │     │
│  │  Folder  │  │    Git   │  │   New    │     │
│  └──────────┘  └──────────┘  └──────────┘     │
│                                                 │
│  [Continue →]                                   │
└─────────────────────────────────────────────────┘
```

**Step 2: Playground**
```
┌─────────────────────────────────────────────────┐
│  🗺️ Setup Workspace                     1→[2]→3→4→5
│  Choose your playground                         │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │   🆕     │  │   📋     │  │   ▶️     │     │
│  │   New    │  │   Copy   │  │ Continue │     │
│  │ Playground│  │ Existing│  │ Current  │     │
│  └──────────┘  └──────────┘  └──────────┘     │
│                                                 │
│  [← Back]  [Continue →]                         │
└─────────────────────────────────────────────────┘
```

**Step 3: Keys**
```
┌─────────────────────────────────────────────────┐
│  🔑 Configure Keys                      1→2→[3]→4→5
│  Set up your AI providers                       │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │   🔑     │  │   ➕     │  │   🖥️     │     │
│  │  Use     │  │   Add    │  │  Local   │     │
│  │ Existing │  │   New    │  │  Model   │     │
│  └──────────┘  └──────────┘  └──────────┘     │
│                                                 │
│  [← Back]  [Continue →]                         │
└─────────────────────────────────────────────────┘
```

**MARKER_155.WIZARD.100:** Wizard completion triggers DAG initialization
```typescript
// In WizardContainer
const handleStep3Complete = () => {
  initMCC(); // Initialize project
  setNavLevel('roadmap'); // Move to DAG view
  setWizardStep(4); // Mark as complete
};
```

---

### LAYER 2: Unified DAG Component
**File:** `UnifiedDAGView.tsx` (NEW)

**Purpose:** Single ReactFlow instance for ALL levels

**Core Innovation:** No more navLevel switching!

```typescript
/**
 * MARKER_155.DAG.001: UnifiedDAGView — Single canvas for all levels
 * 
 * Replaces: DAGView + TaskDAGView + WorkflowDAGView
 * Pattern: Zoom-based drill-down instead of route switching
 */

interface UnifiedDAGViewProps {
  // Level 0: Project architecture (modules)
  architectureNodes: DAGNode[];
  architectureEdges: DAGEdge[];
  
  // Level 1: Tasks (when zoomed into module)
  taskNodes: DAGNode[];
  taskEdges: DAGEdge[];
  
  // Level 2: Workflow (when zoomed into task)
  workflowNodes: DAGNode[];
  workflowEdges: DAGEdge[];
  
  // Current view state
  currentLevel: 0 | 1 | 2;
  focusedNodeId: string | null; // What's currently zoomed
  
  // Actions
  onDrillDown: (nodeId: string, level: number) => void;
  onZoomOut: () => void;
  onNodeSelect: (nodeId: string) => void;
}
```

**Zoom Behavior:**
```typescript
// MARKER_155.DAG.002: Zoom-based level switching
const ZOOM_LEVELS = {
  0: { min: 0.5, max: 1.5, label: 'Architecture' },
  1: { min: 1.5, max: 3.0, label: 'Tasks' },
  2: { min: 3.0, max: 5.0, label: 'Workflow' },
};

// On zoom change, determine visible level
useEffect(() => {
  const zoom = reactFlowInstance.getZoom();
  if (zoom < 1.5) setVisibleLevel(0);
  else if (zoom < 3.0) setVisibleLevel(1);
  else setVisibleLevel(2);
}, [zoom]);
```

**Node Rendering by Level:**
```typescript
// MARKER_155.DAG.003: Different node types per zoom level
const nodeTypes = {
  // Level 0: Large modules
  architecture_module: ArchitectureNode,
  
  // Level 1: Task cards
  task_card: TaskNode,
  
  // Level 2: Agent workflow
  agent_node: AgentNode,
  artifact_node: ArtifactNode,
};
```

---

### LAYER 3: Unified FooterActionBar
**File:** `FooterActionBar.tsx` (MODIFY)

**Rule:** EXACTLY 3 buttons, context-aware

**Level 0 (Architecture):**
```
[Create Task] [Ask Architect] [Execute ▶]
     ↑              ↑            ↑
  On selected    Opens chat   Runs selected
    node                      task/workflow
```

**Level 1 (Tasks):**
```
[Launch Task] [Edit Task] [⬅ Back]
     ↑            ↑          ↑
  Execute      Modify      Zoom out to
  selected     params      architecture
```

**Level 2 (Workflow):**
```
[▶ Run] [⏸ Pause] [⬅ Back]
   ↑        ↑          ↑
Start    Stop/Pause  Zoom out to
pipeline  execution   tasks
```

**MARKER_155.ACTION.001:** Dynamic button generation
```typescript
const LEVEL_ACTIONS: Record<number, ActionDef[]> = {
  0: [
    { id: 'createTask', label: 'Create Task', icon: '➕', shortcut: 'C' },
    { id: 'askArchitect', label: 'Ask Architect', icon: '💬', shortcut: 'A' },
    { id: 'execute', label: 'Execute', icon: '▶️', shortcut: 'Enter', primary: true },
  ],
  1: [
    { id: 'launch', label: 'Launch Task', icon: '▶️', shortcut: 'Enter', primary: true },
    { id: 'edit', label: 'Edit Task', icon: '✏️', shortcut: 'E' },
    { id: 'back', label: 'Back', icon: '←', shortcut: 'Esc' },
  ],
  2: [
    { id: 'run', label: 'Run', icon: '▶️', shortcut: 'Enter', primary: true },
    { id: 'pause', label: 'Pause', icon: '⏸', shortcut: 'Space' },
    { id: 'back', label: 'Back', icon: '←', shortcut: 'Esc' },
  ],
};
```

---

### LAYER 4: Draggable Mini-Windows
**Files:** `MiniChat.tsx`, `MiniStats.tsx`, `MiniTasks.tsx` (✅ Already updated)

**Features:**
- ✅ Draggable (react-draggable)
- ✅ Position persistence (localStorage)
- ✅ Compact/expanded modes
- ✅ Snap-to-grid optional

**MARKER_155.MINIWINDOW.001:** Position saving
```typescript
// Position saved per window ID
const savePosition = (windowId: string, pos: { x: number; y: number }) => {
  localStorage.setItem(`mcc_window_${windowId}`, JSON.stringify(pos));
};

const loadPosition = (windowId: string, defaultPos: Position) => {
  const saved = localStorage.getItem(`mcc_window_${windowId}`);
  return saved ? JSON.parse(saved) : defaultPos;
};
```

---

### LAYER 5: First-Time Onboarding
**File:** `useOnboarding.ts` (MODIFY)

**Current Problem:** Shows always
**Solution:** Check localStorage flag

**MARKER_155.ONBOARDING.001:** First-time detection
```typescript
const ONBOARDING_KEY = 'mcc_onboarding_completed_v1';

export function useOnboarding() {
  const [isFirstTime, setIsFirstTime] = useState<boolean>(() => {
    // Check if onboarding was ever completed
    const completed = localStorage.getItem(ONBOARDING_KEY);
    return completed !== 'true';
  });
  
  const completeOnboarding = useCallback(() => {
    localStorage.setItem(ONBOARDING_KEY, 'true');
    setIsFirstTime(false);
  }, []);
  
  return { isFirstTime, completeOnboarding };
}
```

**Onboarding Flow:**
1. **Tooltip 1:** "Welcome to Mycelium! 3 steps to get started"
2. **Tooltip 2:** "Select how you want to begin" (Step 1)
3. **Tooltip 3:** "Choose your workspace" (Step 2)
4. **Tooltip 4:** "Configure AI keys" (Step 3)
5. **Tooltip 5:** "Now you're ready! Click any module to explore"

---

## 🗺️ Data Flow Architecture

### State Management
```typescript
// MARKER_155.STATE.001: Unified state structure
interface MCCState {
  // Wizard flow
  wizardStep: 1 | 2 | 3 | 4 | 5;
  wizardData: {
    1?: { method: 'folder' | 'git' | 'description'; value: string };
    2?: { action: 'new' | 'copy' | 'continue'; source?: string };
    3?: { method: 'existing' | 'new' | 'local'; keyId?: string };
  };
  
  // DAG view
  currentLevel: 0 | 1 | 2;
  focusedNodeId: string | null;
  cameraPosition: { x: number; y: number; zoom: number };
  
  // Selection
  selectedNodeId: string | null;
  selectedTaskId: string | null;
  
  // Mini-windows positions
  windowPositions: {
    chat: { x: number; y: number };
    stats: { x: number; y: number };
    tasks: { x: number; y: number };
  };
}
```

### Navigation (No More navLevel!)
```typescript
// MARKER_155.NAV.001: Zoom-based navigation replaces navLevel
const actions = {
  // Instead of: setNavLevel('tasks')
  // Use: zoomToNode(nodeId)
  
  zoomToNode: (nodeId: string) => {
    const node = findNode(nodeId);
    const nextLevel = getNextZoomLevel();
    
    // Animate camera to node
    reactFlowInstance.setCenter(node.position.x, node.position.y, {
      zoom: ZOOM_LEVELS[nextLevel].min,
      duration: 800,
    });
    
    setCurrentLevel(nextLevel);
    setFocusedNodeId(nodeId);
  },
  
  zoomOut: () => {
    const prevLevel = Math.max(0, currentLevel - 1);
    const center = calculateParentCenter(focusedNodeId);
    
    reactFlowInstance.setCenter(center.x, center.y, {
      zoom: ZOOM_LEVELS[prevLevel].max,
      duration: 800,
    });
    
    setCurrentLevel(prevLevel);
    setFocusedNodeId(getParentId(focusedNodeId));
  },
};
```

---

## 🎨 UI Specification

### Color Coding by Level
```css
/* MARKER_155.STYLE.001: Level-based visual hierarchy */

/* Level 0: Architecture - Cool blues */
--arch-node-bg: rgba(74, 158, 255, 0.1);
--arch-node-border: rgba(74, 158, 255, 0.5);
--arch-edge: rgba(74, 158, 255, 0.3);

/* Level 1: Tasks - Warm oranges */
--task-node-bg: rgba(255, 165, 0, 0.1);
--task-node-border: rgba(255, 165, 0, 0.5);
--task-pending: #666;
--task-running: #4a9eff;
--task-done: #4ade80;

/* Level 2: Workflow - Agent colors */
--agent-scout: #fbbf24;      /* Amber */
--agent-researcher: #60a5fa; /* Blue */
--agent-architect: #c084fc;  /* Purple */
--agent-coder: #4ade80;      /* Green */
--agent-verifier: #f87171;   /* Red */
```

### Node Sizes by Level
```typescript
// MARKER_155.NODE_SIZES.001: Responsive node sizing
const NODE_DIMENSIONS = {
  0: { width: 240, height: 120, fontSize: 14 },  // Architecture modules
  1: { width: 180, height: 80, fontSize: 12 },   // Tasks
  2: { width: 120, height: 60, fontSize: 10 },   // Agents
};
```

---

## 📁 File Structure

```
client/src/components/mcc/
│
├── WizardContainer.tsx          # ✅ Created - Steps 1-3
├── steps/
│   ├── StepLaunch.tsx           # ✅ Inline in WizardContainer
│   ├── StepPlayground.tsx       # ✅ Inline in WizardContainer
│   ├── StepKeys.tsx             # ✅ Inline in WizardContainer
│   └── StepDAG.tsx              # Placeholder - real DAG
│
├── UnifiedDAGView.tsx           # 🆕 NEW - Single DAG canvas
├── nodes/
│   ├── ArchitectureNode.tsx     # 🆕 NEW - Level 0
│   ├── TaskNode.tsx             # Modify existing
│   ├── AgentNode.tsx            # 🆕 NEW - Level 2
│   └── ArtifactNode.tsx         # 🆕 NEW - Level 2
│
├── FooterActionBar.tsx          # Modify - 3 buttons max
├── MiniWindow.tsx               # ✅ Updated - draggable
├── MiniChat.tsx                 # ✅ Updated
├── MiniStats.tsx                # ✅ Updated
├── MiniTasks.tsx                # ✅ Updated
│
├── hooks/
│   ├── useOnboarding.ts         # Modify - first-time check
│   ├── useUnifiedDAG.ts         # 🆕 NEW - unified data
│   └── useCameraController.ts   # 🆕 NEW - zoom/pan
│
└── MyceliumCommandCenter.tsx    # Modify - integrate all
```

---

## 🔧 Implementation Phases

### Phase 1: Foundation (P0) ✅ DONE
- [x] WizardContainer with steps 1-3
- [x] Draggable MiniWindow
- [x] First-time onboarding check
- [x] Performance fixes (P0)

### Phase 2: DAG Unification (P1) NEXT
- [ ] Create UnifiedDAGView component
- [ ] Implement zoom-based level switching
- [ ] Create ArchitectureNode component
- [ ] Create AgentNode component
- [ ] Create ArtifactNode component
- [ ] Integrate VETKA fan-layout

### Phase 3: State Refactoring (P2)
- [ ] Remove navLevel dependency
- [ ] Add camera position state
- [ ] Implement zoomToNode/zoomOut actions
- [ ] Update FooterActionBar for 3 buttons

### Phase 4: Polish (P3)
- [ ] Smooth zoom animations
- [ ] Node selection highlights
- [ ] Stats integration per node
- [ ] Final UI cleanup

---

## 🎯 Success Criteria

**For User:**
- [ ] Opens app → sees Step 1 with 3 clear options
- [ ] Completes steps 1-3 → sees DAG (not confused by multiple steps)
- [ ] Double-clicks module → zooms into tasks (feels like drill-down)
- [ ] Double-clicks task → zooms into workflow
- [ ] Presses Esc → zooms out
- [ ] Drags mini-windows → they move and stay in place
- [ ] Only sees 3 buttons in footer at any time

**For Developer:**
- [ ] Single source of truth for DAG data
- [ ] No navLevel switching logic
- [ ] Camera state in URL (shareable views)
- [ ] < 1000 lines per major component

---

## 📝 Notes

**Why this works:**
1. **Progressive Disclosure:** User sees only what they need
2. **Spatial Navigation:** Zoom = context, no "where am I?"
3. **Muscle Memory:** Always 3 buttons, always same position
4. **Visual Continuity:** Same canvas, different zoom = less cognitive load

**Why NOT tabs/windows:**
- Tabs require mental model switching
- Multiple windows = fragmented attention
- "Grandma test" fails with complexity

---

**END OF ARCHITECTURAL SPECIFICATION**
