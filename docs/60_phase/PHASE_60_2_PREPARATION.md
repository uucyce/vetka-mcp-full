# 🚀 Phase 60.2 Preparation Guide

**Based on:** Phase 60.1 Reconnaissance
**Status:** Ready to Proceed
**Timeline:** Phase 60.2 Implementation

---

## What's Phase 60.2?

**Phase 60.2: Real-time Socket.IO Streaming**

Добавить real-time streaming событий через Socket.IO, чтобы frontend видел прогресс workflow в реальном времени.

---

## Prerequisites (Already Done ✅)

From Phase 60.1:
- ✅ LangGraph workflow structure
- ✅ 7 nodes (hostess, architect, pm, dev_qa, eval, learner, approval)
- ✅ Feature flag infrastructure
- ✅ Streaming method: `execute_with_langgraph_stream()`
- ✅ Checkpointing system
- ✅ LearnerAgent (self-learning)

---

## Phase 60.2 Tasks

### Task 1: Socket.IO Integration in Orchestrator

**File:** `src/orchestration/orchestrator_with_elisya.py`

**Changes needed:**
```python
# Add imports
import socketio

# In __init__:
self.sio = socketio.AsyncServer(
    async_mode='aiohttp',
    cors_allowed_origins='*'
)

# In each node call:
await self.sio.emit('node_started', {
    'node': 'hostess',
    'timestamp': datetime.now().isoformat()
})

# When node completes:
await self.sio.emit('node_completed', {
    'node': 'hostess',
    'status': 'success',
    'output_preview': '...'
})
```

### Task 2: Event Type Definitions

**File:** Create `src/orchestration/event_types.py`

```python
# Event types for workflow
EVENT_TYPES = {
    'node_started': 'Node execution started',
    'node_completed': 'Node execution completed',
    'node_error': 'Node execution failed',
    'score_computed': 'Evaluation score available',
    'retry_decision': 'Retry decision made',
    'workflow_complete': 'Entire workflow complete',
}

# Event schemas
class NodeStartedEvent:
    node: str
    timestamp: str
    input_size: int

class ScoreComputedEvent:
    score: float
    feedback: str
    passed: bool  # >= 0.75

class RetryDecisionEvent:
    retry_count: int
    max_retries: int
    will_retry: bool
    reason: str
```

### Task 3: Add Emit Calls to Each Node

**Locations in `src/orchestration/langgraph_nodes.py`:**

```python
# In hostess_node:
await self.emit('node_started', {'node': 'hostess'})
# ... logic ...
await self.emit('node_completed', {
    'node': 'hostess',
    'routing': state['next']
})

# In architect_node:
await self.emit('node_started', {'node': 'architect'})
# ... logic ...
await self.emit('node_completed', {
    'node': 'architect',
    'tasks_count': len(state['tasks'])
})

# In eval_node:
await self.emit('node_started', {'node': 'eval'})
# ... logic ...
await self.emit('score_computed', {
    'score': state['eval_score'],
    'feedback': state['eval_feedback'],
    'passed': state['eval_score'] >= 0.75
})

# In learner_node:
await self.emit('node_started', {'node': 'learner'})
# ... logic ...
await self.emit('retry_decision', {
    'retry_count': state['retry_count'],
    'max_retries': state['max_retries'],
    'will_retry': state['retry_count'] < state['max_retries']
})
```

### Task 4: Frontend Socket.IO Listener

**File:** `client/src/hooks/useSocket.ts`

```typescript
// Add handler after line 261 (existing listeners)

// Workflow streaming events
socket.on('node_started', (data) => {
    console.log(`📍 Node started: ${data.node}`);
    setWorkflowStatus(prev => ({
        ...prev,
        current_node: data.node,
        status: 'running'
    }));
});

socket.on('node_completed', (data) => {
    console.log(`✅ Node completed: ${data.node}`);
    setWorkflowStatus(prev => ({
        ...prev,
        completed_nodes: [...prev.completed_nodes, data.node]
    }));
});

socket.on('score_computed', (data) => {
    console.log(`📊 Score: ${data.score}`);
    setWorkflowStatus(prev => ({
        ...prev,
        eval_score: data.score,
        eval_passed: data.passed,
        eval_feedback: data.feedback
    }));
});

socket.on('retry_decision', (data) => {
    console.log(`🔄 Retry: ${data.will_retry}`);
    setWorkflowStatus(prev => ({
        ...prev,
        retry_count: data.retry_count,
        will_retry: data.will_retry
    }));
});

socket.on('workflow_complete', (data) => {
    console.log(`🎉 Workflow complete`);
    setWorkflowStatus(prev => ({
        ...prev,
        status: 'complete',
        final_output: data.result
    }));
});
```

### Task 5: UI Components for Real-Time Updates

**File:** Create `client/src/components/WorkflowMonitor.tsx`

```typescript
export interface WorkflowStatus {
    current_node: string;
    completed_nodes: string[];
    eval_score: number;
    eval_passed: boolean;
    eval_feedback: string;
    retry_count: number;
    will_retry: boolean;
    status: 'idle' | 'running' | 'complete' | 'error';
}

export const WorkflowMonitor: React.FC = () => {
    const [status, setStatus] = useState<WorkflowStatus>(initialState);

    return (
        <div className="workflow-monitor">
            <div className="current-node">
                Current: {status.current_node}
            </div>
            
            <div className="progress">
                {NODES.map(node => (
                    <div
                        key={node}
                        className={status.completed_nodes.includes(node) ? 'complete' : 'pending'}
                    >
                        {node}
                    </div>
                ))}
            </div>

            {status.eval_score > 0 && (
                <div className="eval-result">
                    Score: {status.eval_score.toFixed(2)}
                    {status.eval_passed ? '✅ PASSED' : '❌ RETRY'}
                </div>
            )}

            {status.will_retry && (
                <div className="retry-info">
                    Retrying... (Attempt {status.retry_count + 1}/3)
                </div>
            )}
        </div>
    );
};
```

---

## Testing Checklist

### 1. Backend Streaming Tests
```bash
# Test streaming execution
pytest tests/test_langgraph_streaming.py -v

# Test event emission
pytest tests/test_socket_events.py -v

# Test with feature flag
FEATURE_FLAG_LANGGRAPH=True pytest tests/test_langgraph_phase60.py -v
```

### 2. Frontend Testing
```bash
# Test Socket.IO connection
npm run test -- useSocket.ts

# Test WorkflowMonitor component
npm run test -- WorkflowMonitor.tsx

# Test real-time updates
npm run test -- integration
```

### 3. End-to-End Testing
```bash
# Start backend
python src/main.py

# Start frontend
npm start

# Manual testing:
# 1. Trigger workflow
# 2. Watch events in console
# 3. Verify UI updates in real-time
# 4. Check eval score display
# 5. Test retry mechanism
```

---

## Implementation Steps

### Step 1: Backend Streaming (Days 1-2)
- [ ] Add Socket.IO to orchestrator
- [ ] Define event types
- [ ] Add emit calls to nodes
- [ ] Write streaming tests
- [ ] Verify events are emitted

### Step 2: Frontend Listener (Days 2-3)
- [ ] Add Socket.IO handler in useSocket.ts
- [ ] Implement WorkflowMonitor component
- [ ] Add event-based UI updates
- [ ] Test Socket.IO connection
- [ ] Verify message reception

### Step 3: Integration Testing (Days 3-4)
- [ ] End-to-end workflow test
- [ ] Retry cycle with streaming
- [ ] Error handling
- [ ] Performance testing
- [ ] Load testing (multiple concurrent)

### Step 4: Documentation & Polish (Day 4)
- [ ] Update architecture docs
- [ ] Add API documentation
- [ ] Write troubleshooting guide
- [ ] Performance benchmarks

---

## Key Files to Modify

| File | Changes |
|------|---------|
| `src/orchestration/orchestrator_with_elisya.py` | Socket.IO setup, emit calls |
| `src/orchestration/langgraph_nodes.py` | Add emit to each node |
| `client/src/hooks/useSocket.ts` | Add event listeners |
| Create: `src/orchestration/event_types.py` | Event definitions |
| Create: `client/src/components/WorkflowMonitor.tsx` | UI component |
| Create: `tests/test_langgraph_streaming.py` | Streaming tests |

---

## Potential Challenges

### 1. Timing Issues
**Problem:** Events emitted before listener ready
**Solution:** Use message queue with replay capability

### 2. Large Payloads
**Problem:** Eval feedback or artifacts too large
**Solution:** Send only summary, allow detail fetch via HTTP

### 3. Network Disconnects
**Problem:** Client disconnects mid-workflow
**Solution:** Implement reconnect with state sync

### 4. Multiple Clients
**Problem:** Broadcasting events to multiple concurrent workflows
**Solution:** Use namespace/room per workflow_id

---

## Success Criteria

✅ Events emitted for each node
✅ Frontend receives events in real-time
✅ UI updates show workflow progress
✅ Eval score displayed correctly
✅ Retry mechanism visible to user
✅ No blocking on event emission
✅ Streaming tests pass
✅ E2E tests pass

---

## Documentation to Generate

1. **API Documentation**
   - Event types & payloads
   - Socket.IO endpoint reference
   - Error codes

2. **Architecture Document**
   - Workflow streaming architecture
   - Event flow diagram
   - Timing expectations

3. **Troubleshooting Guide**
   - Common issues
   - Debug checklist
   - Performance optimization

---

## Performance Targets

- Event emission latency: < 100ms
- Frontend UI update: < 500ms
- No workflow slowdown from streaming
- Support 10+ concurrent workflows

---

## Next Phase: Phase 60.3?

Possible improvements after 60.2:
- WebSocket compression
- Event batching for high-frequency updates
- Client-side event caching
- Workflow replay for debugging
- Real-time collaboration

---

## Questions to Answer

1. How to handle very long outputs (artifacts)?
2. Should we batch events or emit immediately?
3. How often should we update the UI (throttle)?
4. What happens if Socket connection drops?
5. How to sync state on reconnect?

---

**Next:** Start Phase 60.2 Implementation! 🚀
