# Activity Monitor Recon Report

**Date:** 2026-02-10
**Phase:** 131
**Status:** RECON_COMPLETE — needs Grok research

## Current Implementation

**File:** `client/src/components/panels/ActivityLog.tsx`

### Existing Features
- MARKER_127.2A: Real-time pipeline activity log
- MARKER_128.6A: Message parsing (tool_call, verifier, file_create, retry, error)
- MARKER_128.6B: Rich formatting (icons, badges, progress bars)
- MARKER_128.6C: Per-task grouping with collapsible sections
- MARKER_129.3B: Throttled event processing (500ms flush)

### Current Data Available
```typescript
interface LogEntry {
  id: string;
  timestamp: number;
  role: string;        // @scout, @researcher, @coder, @verifier, @architect
  model: string;       // e.g., "kimi-k2.5", "qwen3-coder"
  message: string;
  subtask_idx: number;
  total: number;
  task_id?: string;
  preset?: string;
}
```

## Missing Visualizations (MARKER_131.ACTIVITY_RECON)

### 1. Timeline Graph
- **What:** Gantt-style timeline showing agent activity over time
- **Why:** Understand parallel vs sequential work, identify bottlenecks
- **Data needed:** task_id, role, start_time, end_time

### 2. Token Usage Graph
- **What:** Line/bar chart of tokens in/out over time
- **Why:** Monitor API costs, identify token-heavy operations
- **Data needed:** tokens_in, tokens_out per event (currently not in LogEntry)

### 3. Success Rate Chart
- **What:** Pie/donut chart of verifier pass/fail ratio
- **Why:** Quality monitoring, identify problematic patterns
- **Data needed:** Already have in verifier messages

### 4. Agent Activity Bars
- **What:** Horizontal bars showing activity per agent role
- **Why:** Understand workload distribution
- **Data needed:** role + timestamp (already available)

### 5. Pipeline Duration Tracker
- **What:** Bar chart of pipeline durations
- **Why:** Performance monitoring, regression detection
- **Data needed:** pipeline start/end times (from task_board)

### 6. Cost Accumulation Graph
- **What:** Running total of $ spent over session
- **Why:** Budget monitoring
- **Data needed:** cost_usd per LLM call (from usage_tracking)

### 7. File Touch Heatmap
- **What:** List of most frequently modified files
- **Why:** Identify hot spots, potential conflicts
- **Data needed:** filePath from file_create messages

## Grok Research Questions

Prompt for Grok research on agent monitoring dashboards:

```
Research: Best practices for multi-agent AI system monitoring dashboards

Questions:
1. What metrics are most important for monitoring LLM agent orchestration?
2. What visualizations are used in production agent monitoring systems?
3. How do systems like LangSmith, Weights & Biases, or Helicone visualize agent activity?
4. What alerts/anomaly detection is useful for agent pipelines?
5. How to visualize:
   - Agent communication patterns
   - Token efficiency
   - Task completion rates
   - Error cascades
   - Cost attribution per agent

Context: We have a multi-agent pipeline (Architect → Researcher → Coder → Verifier)
with real-time event streaming. Current UI shows a log list with basic grouping.
Want to add meaningful graphs/charts for monitoring agent health and performance.
```

## Implementation Priority

| Feature | Complexity | Value | Priority |
|---------|------------|-------|----------|
| Agent Activity Bars | Low | High | P1 |
| Success Rate Chart | Low | High | P1 |
| Token Usage Graph | Medium | High | P2 |
| Pipeline Duration | Medium | Medium | P2 |
| Cost Graph | Medium | High | P2 |
| File Touch Heatmap | Low | Medium | P3 |
| Timeline Graph | High | High | P3 |

## Next Steps

1. **Send to Grok:** Research prompt above for best practices
2. **Add metrics to backend:** Emit tokens/cost with each event
3. **Start with P1:** Agent Activity Bars + Success Rate (simple CSS bars)
4. **Consider charting lib:** If complex graphs needed, evaluate:
   - recharts (React-friendly, minimal)
   - visx (D3-based, flexible)
   - No lib (pure CSS bars like PipelineStats)

## Related Files

- `src/orchestration/agent_pipeline.py` — emits events
- `src/services/socketio_bridge.py` — forwards to frontend
- `client/src/components/panels/PipelineStats.tsx` — example of CSS-only bars
