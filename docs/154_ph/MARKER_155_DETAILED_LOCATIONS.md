# MARKER 155 — Detailed Code Locations
**Where exactly to place each MARKER comment**

---

## PLAYGROUND MANAGER (playground_manager.py)

### MARKER_155.PLAYGROUND.PATH
```python
# Line ~45 (constants section)
# Current:
PLAYGROUND_ROOT = Path("data/playgrounds")

# Change to:
# MARKER_155.PLAYGROUND.PATH: External path for isolation
PLAYGROUND_ROOT = Path.home() / ".vetka" / "playgrounds"
```

### MARKER_155.PLAYGROUND.GUARD
```python
# Line ~67 (in create() method, after params validation)
# Add:
# MARKER_155.PLAYGROUND.GUARD: Prevent creation inside project root
if "data/playgrounds" in str(worktree_path) or str(worktree_path).startswith(str(project_path)):
    raise ValueError("Playground cannot be created inside project directory")
```

### MARKER_155.PLAYGROUND.SYMLINK
```python
# Line ~92 (after worktree creation)
# Add:
# MARKER_155.PLAYGROUND.SYMLINK: Create optional symlink for UX
symlink_path = project_path / ".vetka-playground"
try:
    if not symlink_path.exists():
        symlink_path.symlink_to(worktree_path, target_is_directory=True)
except OSError:
    pass  # Windows may require admin rights
```

### MARKER_155.PLAYGROUND.GET
```python
# Line ~156 (in get_playground_root() method)
# Change return path construction to use external location
# MARKER_155.PLAYGROUND.GET: Return external path
return Path.home() / ".vetka" / "playgrounds" / f"{project_name}-playground"
```

---

## TREE ROUTES (tree_routes.py)

### MARKER_155.PERF.ASYNC_QDRANT
```python
# Line ~284 (current blocking code)
# Current:
for item in qdrant_client.scroll(collection_name="documents"):
    # process

# Change to:
# MARKER_155.PERF.ASYNC_QDRANT: Use async pagination
async def get_documents_batch(offset=0, limit=100):
    return await qdrant_client.async_scroll(
        collection_name="documents",
        offset=offset,
        limit=limit
    )

# Process in batches
offset = 0
while True:
    batch = await get_documents_batch(offset)
    if not batch:
        break
    # Process batch
    offset += 100
```

### MARKER_155.PERF.ASYNC_FILE
```python
# Line ~314 (current blocking file checks)
# Current:
for path in paths:
    if os.path.exists(path):
        valid_paths.append(path)

# Change to:
# MARKER_155.PERF.ASYNC_FILE: Batch check with asyncio.gather
async def batch_exists(paths):
    tasks = [asyncio.to_thread(os.path.exists, p) for p in paths]
    results = await asyncio.gather(*tasks)
    return [p for p, exists in zip(paths, results) if exists]

valid_paths = await batch_exists(paths)
```

---

## MAIN.PY

### MARKER_155.PERF.RELOAD
```python
# Line ~1166 (uvicorn run configuration)
# Current:
uvicorn.run(app, host="0.0.0.0", port=5001, reload=True)

# Change to:
# MARKER_155.PERF.RELOAD: Environment-controlled reload
import os
reload = os.getenv("VETKA_RELOAD", "true").lower() == "true"
uvicorn.run(app, host="0.0.0.0", port=5001, reload=reload)
```

---

## MCC ROUTES (mcc_routes.py)

### MARKER_155.INTEGRATION.CHAT_ENDPOINT
```python
# Add new endpoint after existing task endpoints
# MARKER_155.INTEGRATION.CHAT_ENDPOINT: Link VETKA chat to task
@router.post("/api/mcc/tasks/{task_id}/link-chat")
async def link_chat_to_task(task_id: str, request: LinkChatRequest):
    """Link a VETKA chat to a Mycelium task"""
    task_board = load_task_board()
    if task_id not in task_board["tasks"]:
        raise HTTPException(404, "Task not found")
    
    task_board["tasks"][task_id]["vetka_chat_id"] = request.chat_id
    task_board["tasks"][task_id]["vetka_chat_url"] = request.chat_url
    save_task_board(task_board)
    
    return {"status": "linked", "task_id": task_id, "chat_id": request.chat_id}

@router.post("/api/mcc/tasks/{task_id}/notify")
async def notify_task_result(task_id: str, result: TaskResult):
    """Post agent result to linked VETKA chat"""
    # Implementation to send message to VETKA chat API
    pass
```

---

## ANALYTICS ROUTES (analytics_routes.py)

### MARKER_155.STATS.ENDPOINTS
```python
# MARKER_155.STATS.ENDPOINTS: Agent metrics endpoints

@router.get("/api/analytics/agents/summary")
async def get_agents_summary(period: str = "7d"):
    """Get aggregated metrics for all agent types"""
    metrics = load_agent_metrics()
    return {
        "period": period,
        "agents": {
            "scout": calculate_metrics("scout", metrics, period),
            "researcher": calculate_metrics("researcher", metrics, period),
            "architect": calculate_metrics("architect", metrics, period),
            "coder": calculate_metrics("coder", metrics, period),
            "verifier": calculate_metrics("verifier", metrics, period),
        }
    }

@router.get("/api/analytics/agents/{agent_id}/metrics")
async def get_agent_metrics(agent_id: str, limit: int = 50):
    """Get detailed metrics for specific agent"""
    metrics = load_agent_metrics()
    agent_runs = [m for m in metrics["runs"] if m["agent_id"] == agent_id]
    return {
        "agent_id": agent_id,
        "runs": agent_runs[-limit:],
        "total_runs": len(agent_runs),
        "avg_quality": sum(r["quality_score"] for r in agent_runs) / len(agent_runs) if agent_runs else 0
    }

@router.post("/api/analytics/agents/{run_id}/remark")
async def add_architect_remark(run_id: str, request: RemarkRequest):
    """Architect adds quality remark after execution"""
    metrics = load_agent_metrics()
    for run in metrics["runs"]:
        if run["run_id"] == run_id:
            run["architect_remark"] = request.remark
            run["quality_score"] = request.score
            save_agent_metrics(metrics)
            return {"status": "remark_added"}
    raise HTTPException(404, "Run not found")
```

---

## ROADMAP TASK NODE (RoadmapTaskNode.tsx)

### MARKER_155.INTEGRATION.CHAT_BADGE
```typescript
// In the node component, add chat link badge
// Line ~45 (in the node render)

// MARKER_155.INTEGRATION.CHAT_BADGE: Add VETKA chat link
{data.vetkaChatId && (
  <div className="chat-badge" onClick={(e) => {
    e.stopPropagation();
    window.open(data.vetkaChatUrl, '_blank');
  }}>
    💬 Chat
  </div>
)}
```

---

## MCC STORE (useMCCStore.ts)

### MARKER_155.INTEGRATION.CHAT_STORE
```typescript
// Line ~80 (Task interface definition)
// Add to Task type:

// MARKER_155.INTEGRATION.CHAT_STORE: VETKA chat linking
interface Task {
  id: string;
  title: string;
  status: TaskStatus;
  // ... existing fields
  vetkaChatId?: string;      // NEW
  vetkaChatUrl?: string;     // NEW
}

// Line ~340 (add actions)
linkTaskToChat: (taskId: string, chatId: string, chatUrl: string) => Promise<void>;
notifyChatResult: (taskId: string, result: TaskResult) => Promise<void>;
```

---

## MINI STATS (MiniStats.tsx)

### MARKER_155.STATS.UI
```typescript
// Line ~45 (add agent metrics section)

// MARKER_155.STATS.UI: Agent statistics dashboard
const AgentMetricsSection = () => {
  const { agentSummary } = useAnalytics();
  
  return (
    <div className="agent-metrics">
      <h4>Agent Performance</h4>
      {Object.entries(agentSummary).map(([type, metrics]) => (
        <div key={type} className="agent-row">
          <span className="agent-icon">{getAgentIcon(type)}</span>
          <span className="agent-name">{type}</span>
          <span className="agent-quality">{metrics.avgQuality}%</span>
          <span className="agent-cost">${metrics.totalCost.toFixed(2)}</span>
        </div>
      ))}
    </div>
  );
};

// Agent icons: 🕵️ Scout, 🔬 Researcher, 👨‍💻 Architect, 💻 Coder, ✅ Verifier
```

---

## NEW FILE: StepIndicator.tsx

### MARKER_155.FLOW.STEPS
```typescript
// client/src/components/mcc/StepIndicator.tsx
// MARKER_155.FLOW.STEPS: 5-step progress indicator

import React from 'react';
import { useMCCStore } from '@/store/useMCCStore';

const steps = [
  { id: 1, label: '🚀 Launch', description: 'Select project' },
  { id: 2, label: '📁 Playground', description: 'Setup workspace' },
  { id: 3, label: '🔑 Keys', description: 'API configuration' },
  { id: 4, label: '🗺️ DAG', description: 'Plan architecture' },
  { id: 5, label: '🔍 Drill', description: 'Execute tasks' },
];

export const StepIndicator: React.FC = () => {
  const { navLevel, hasProject } = useMCCStore();
  
  const getCurrentStep = () => {
    if (!hasProject) return 1;
    if (navLevel === 'first_run') return 1;
    if (navLevel === 'roadmap') return 4;
    if (['tasks', 'workflow', 'running', 'results'].includes(navLevel)) return 5;
    return 1;
  };
  
  const currentStep = getCurrentStep();
  
  return (
    <div className="step-indicator">
      {steps.map((step, index) => (
        <div 
          key={step.id} 
          className={`step ${step.id === currentStep ? 'active' : ''} ${step.id < currentStep ? 'completed' : ''}`}
        >
          <div className="step-number">{step.id}</div>
          <div className="step-label">{step.label}</div>
        </div>
      ))}
    </div>
  );
};
```

---

## NEW FILE: agent_metrics.py (models)

### MARKER_155.STATS.MODEL
```python
# src/models/agent_metrics.py
# MARKER_155.STATS.MODEL: Agent run metrics data model

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

class AgentRunMetrics(BaseModel):
    """Metrics for a single agent run"""
    run_id: str
    agent_id: str
    agent_type: str  # scout, researcher, architect, coder, verifier
    task_id: str
    pipeline_id: str
    
    # Timing
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    
    # Cost
    cost_usd: float = 0.0
    
    # Quality
    quality_score: Optional[float] = None  # 0-100, from verifier
    architect_remark: Optional[str] = None
    
    # Status
    success: bool = False
    error_message: Optional[str] = None
    
    # Additional metadata
    model_used: Optional[str] = None
    provider: Optional[str] = None
    tier: Optional[str] = None  # bronze, silver, gold

class AgentMetricsSummary(BaseModel):
    """Aggregated metrics for an agent type"""
    agent_type: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    avg_duration: float
    avg_quality: float
    total_tokens: int
    total_cost: float
    recent_remarks: list[str]
```

---

## SUMMARY

### Files to Modify (Existing)
1. `src/orchestration/playground_manager.py` — 4 MARKERs
2. `src/api/routes/tree_routes.py` — 2 MARKERs
3. `main.py` — 1 MARKER
4. `src/api/routes/mcc_routes.py` — 1 MARKER
5. `src/api/routes/analytics_routes.py` — 3 MARKERs
6. `client/src/components/mcc/nodes/RoadmapTaskNode.tsx` — 1 MARKER
7. `client/src/store/useMCCStore.ts` — 1 MARKER
8. `client/src/components/mcc/MiniStats.tsx` — 1 MARKER

### Files to Create (New)
1. `src/models/agent_metrics.py` — MARKER_155.STATS.MODEL
2. `client/src/components/mcc/StepIndicator.tsx` — MARKER_155.FLOW.STEPS

### Files to Remove (Deprecated)
1. `client/src/components/mcc/RailsActionBar.tsx` — From render tree (already done)
2. `client/src/components/mcc/WorkflowToolbar.tsx` — Full removal

