# Codex Brief: Wave 2 — Stats Dashboard + Task DAG

**Phase:** 152 Wave 2
**Assigned to:** Codex
**Priority:** P1
**Depends on:** Wave 1 backend (ALL DONE ✅)

## Context

Opus completed the entire Wave 1 backend:
- `src/orchestration/pipeline_analytics.py` — 9 aggregation functions
- `src/api/routes/analytics_routes.py` — 8 REST endpoints
- Timeline events in agent_pipeline.py
- Task provenance (source_chat_id/source_group_id)
- 42 tests passing

Your job: build the React frontend that consumes these APIs.

## Task 152.5 — Stats Dashboard Panel

### What to build
A `StatsDashboard.tsx` component that displays pipeline analytics.

### API endpoints to call
```
GET /api/analytics/summary    → top summary cards
GET /api/analytics/agents     → per-agent efficiency data
GET /api/analytics/trends?period=day&metric=success_rate → trend data
GET /api/analytics/cost       → cost breakdown
GET /api/analytics/teams      → preset comparison
```

### Layout (Grok Research — Option B: Expandable Cards)
```
┌─────────────────────────────────────────────────────┐
│ Summary Row:  [Total Runs] [Success %] [Avg Duration] [Cost] │
├─────────────────────────────────────────────────────┤
│ Time Series Chart (Recharts LineChart)                        │
│   - success_rate, tokens, cost over time                      │
│   - Toggle: day/week                                          │
├─────────────────────────────────────────────────────┤
│ Agent Efficiency Cards (5x — scout/arch/res/coder/verifier)   │
│   [calls] [tokens] [duration] [success%] [retries]            │
│   ⚠️ WEAK badge if in weak_links                              │
├─────────────────────────────────────────────────────┤
│ Team Comparison (grouped BarChart — bronze/silver/gold)       │
│   Metrics: success_rate, avg_duration, cost                   │
└─────────────────────────────────────────────────────┘
```

### Data shapes (from API)

**Summary response:**
```json
{
  "success": true,
  "data": {
    "total_runs": 25,
    "success_rate": 80.0,
    "adjusted_success_avg": 75.0,
    "total_tokens": 500000,
    "total_cost_estimate": 1.25,
    "avg_duration_s": 180.5,
    "total_retries": 15,
    "total_llm_calls": 200,
    "tasks_by_status": {"done": 20, "failed": 5},
    "tasks_by_preset": {"dragon_silver": 15, "dragon_bronze": 10},
    "weak_links": [{"role": "coder", "severity": 3, "reasons": [...]}],
    "time_series": [{"bucket": "2026-02-14", "total": 5, "success_rate": 80.0, ...}],
    "agent_efficiency": [{"role": "coder", "calls": 30, "success_rate": 75.0, ...}]
  }
}
```

**Agents response:**
```json
{
  "success": true,
  "agents": [
    {"role": "coder", "calls": 30, "tokens_total": 100000, "avg_duration": 15.0,
     "success_rate": 75.0, "retries": 5, "efficiency_score": 72.0}
  ],
  "weak_links": [{"role": "coder", "severity": 3, "reasons": ["Low success rate: 50%"]}]
}
```

**Trends response:**
```json
{
  "success": true,
  "data": {
    "metric": "success_rate",
    "period": "day",
    "trend": "up",
    "current_value": 85.0,
    "previous_value": 75.0,
    "change_pct": 13.3,
    "data_points": [{"bucket": "2026-02-14", "total": 5, "success_rate": 80.0}]
  }
}
```

**Teams response:**
```json
{
  "success": true,
  "teams": [
    {"preset": "dragon_silver", "runs": 15, "success_rate": 86.0,
     "avg_duration_s": 120.0, "total_tokens": 300000, "total_cost": 0.45}
  ]
}
```

### Requirements
1. **Use Recharts** — `npm install recharts` if needed
2. **Nolan style** — dark background (#111, #1a1a1a), minimal color, monochrome with accent green (#22c55e) for success, red (#ef4444) for failures
3. **Place in:** `client/src/components/panels/StatsDashboard.tsx`
4. **Integration:** Import in DevPanel's Stats tab (replace existing PipelineStats.tsx or extend it)
5. **Fetch on mount** — useEffect → fetch all endpoints, loading state
6. **Error handling** — show "-" for missing data, don't crash
7. **Compact/expanded** — support `mode: "compact" | "expanded"` prop (like PipelineStats)

### DO NOT
- Do NOT modify Python backend files
- Do NOT add new dependencies beyond recharts
- Do NOT create new panels or tabs — integrate into existing DevPanel Stats tab

---

## Task 152.6 — Task Drill-Down Modal

### What to build
A `TaskDrillDown.tsx` modal that shows detailed analytics for a single task.

### API endpoint
```
GET /api/analytics/task/{task_id}
```

### Layout
```
┌──────────────────────────────────────┐
│ Task: "Add bookmark toggle"          │
│ Status: ✅ Done | Preset: 🐉 Silver  │
│ Duration: 66.8s | LLM Calls: 12     │
├──────────────────────────────────────┤
│ Timeline (Gantt-like horizontal bars)│
│  scout    ████░░░░░░░░░░  8.0s       │
│  architect     █████████░  12.0s      │
│  researcher   █████░░░░░  6.0s        │
│  coder              ████████████ 30s  │
│  verifier                  █████ 10s  │
├──────────────────────────────────────┤
│ Token Distribution (Recharts PieChart)│
│  coder: 60% | architect: 25% | ...   │
├──────────────────────────────────────┤
│ Agent Stats Table                    │
│  role | calls | tokens | duration    │
├──────────────────────────────────────┤
│ Adjusted Score: 85% (verifier×0.7 + │
│   user_feedback×0.3)                 │
│ User Feedback: ✅ Applied             │
└──────────────────────────────────────┘
```

### Data shape (from API)
```json
{
  "success": true,
  "data": {
    "task_id": "tb_001",
    "title": "Add bookmark toggle",
    "status": "done",
    "preset": "dragon_silver",
    "phase_type": "build",
    "duration_s": 66.8,
    "llm_calls": 12,
    "tokens_in": 15000,
    "tokens_out": 8000,
    "subtasks_total": 3,
    "subtasks_completed": 3,
    "agent_stats": {
      "scout": {"calls": 2, "tokens_in": 3000, "tokens_out": 1000, "duration_s": 8.0, ...},
      "architect": {...},
      "coder": {...},
      "verifier": {...}
    },
    "adjusted_stats": {
      "adjusted_success": 0.910,
      "user_feedback": "applied",
      "has_user_feedback": true
    },
    "token_distribution": [
      {"role": "coder", "tokens": 7000, "pct": 30.4},
      {"role": "architect", "tokens": 6000, "pct": 26.1}
    ],
    "timeline_events": [
      {"ts": 1000.0, "offset_s": 0, "role": "pipeline", "event": "start", ...},
      {"ts": 1001.0, "offset_s": 1.0, "role": "scout", "event": "start", ...},
      ...
    ],
    "cost_estimate": 0.0023,
    "retries_total": 1,
    "verifier_confidence": 0.9,
    "source_chat_id": ""
  }
}
```

### Requirements
1. **Modal/Overlay** — triggered by clicking task in MCCTaskList (NOT TaskCard — it's dead UI)
2. **Timeline** — horizontal bars using Recharts BarChart or custom div bars
3. **PieChart** — token distribution
4. **Close button** — Escape key closes
5. **Place in:** `client/src/components/panels/TaskDrillDown.tsx`
6. **Integration:** Import in `MCCTaskList.tsx` — add 📊 button that opens drill-down (RECON confirmed TaskCard is unused)

### Timeline events format
- If `timeline_events[0]` has `offset_s` → use REAL timestamped events (152.4)
- If `timeline_events[0]` has `start_offset` → use approximate Gantt (legacy)
- Both formats work — render differently:
  - Real: scatter plot / event markers on time axis
  - Approximate: horizontal bar chart (role = Y axis, time = X axis)

### DO NOT
- Do NOT modify Python backend
- Do NOT add new tabs to DevPanel — this is a MODAL opened from task list

---

## TypeScript Checks
After implementation:
```bash
npx tsc --noEmit client/src/components/panels/StatsDashboard.tsx
npx tsc --noEmit client/src/components/panels/TaskDrillDown.tsx
```

## File List (to create)
- `client/src/components/panels/StatsDashboard.tsx` — NEW
- `client/src/components/panels/TaskDrillDown.tsx` — NEW

## Files to modify (carefully)
- `client/src/components/panels/DevPanel.tsx` — import StatsDashboard into Stats tab (expanded mode only, keep PipelineStats compact)
- `client/src/components/mcc/MCCTaskList.tsx` — add 📊 button for drill-down (NOT TaskCard.tsx — dead UI per RECON)

## Commit convention
Commit as: `feat(152.5-6): Stats Dashboard + Task Drill-Down Modal`
