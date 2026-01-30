# Artifact Flow Analysis Report

**Date**: 2026-01-09
**Phase**: 54.1
**Scope**: Tracking artifacts from creation to deployment

---

## Current Artifact Flow (What Works Today)

### Step 1: Artifact Creation
**Trigger**: Dev agent calls tool `write_file`, `create_file`, or `edit_file`

**Location**: `src/orchestration/orchestrator_with_elisya.py` (lines 590-750)

**Flow**:
```python
# LLM in Dev agent generates:
tool_calls = [
  {
    "name": "write_file",
    "arguments": {
      "file_path": "/src/app.py",
      "content": "def hello(): ..."
    }
  }
]

# Executor processes:
result = await safe_tool_executor.execute_call(tool_call)
# result = {
#   "success": true,
#   "message": "File written",
#   "file_path": "/src/app.py"
# }
```

**Status**: ✅ Working

---

### Step 2: CAM Engine Processing (NEW ARTIFACT HOOK)
**Trigger**: After write_file/create_file succeeds

**Location**: `src/orchestration/orchestrator_with_elisya.py` (lines 740-780)

**Flow**:
```python
if func_name in ('write_file', 'create_file', 'edit_file') and result.success:
    # CAM processes new artifact
    cam_result = await self._cam_engine.handle_new_artifact(
        artifact_path=file_path,
        metadata={
            'type': 'code',
            'agent': agent_type,  # 'Dev', 'QA', etc.
            'language': detect_language(file_path),
            'workflow_id': workflow_id
        }
    )
    # cam_result = CAMOperation(
    #   operation_type='branch'|'merge'|'variant',
    #   similarity_to_existing=0.85,
    #   tree_node_id='node-456',
    #   ...
    # )
```

**What CAM Does**:
1. **Compute similarity** to existing artifacts in knowledge graph
2. **Decide operation**:
   - similarity < 0.7 → BRANCH (new subtree)
   - 0.7 ≤ similarity < 0.92 → MERGE PROPOSAL
   - similarity ≥ 0.92 → VARIANT (mark as duplicate)
3. **Update tree structure** with Procrustes layout
4. **Store metadata** in Weaviate

**Status**: ✅ Working, but could emit more data to UI

---

### Step 3: Memory Persistence (TRIPLE-WRITE)
**Trigger**: After artifact is processed by CAM

**Location**: `src/services/memory_manager.py`

**Flow**:
```python
# Channel 1: Weaviate (vector database)
await memory.save_artifact_embedding(
    artifact_path=file_path,
    content=file_content,
    workflow_id=workflow_id,
    agent_type=agent_type
)

# Channel 2: Local file system
# (stored in /src/services/file_storage/)

# Channel 3: Metadata in CAM
# (already included in Step 2)
```

**What Gets Stored**:
- File content (raw)
- File path
- Agent that created it
- Workflow ID
- Timestamps
- Embeddings vector (for semantic search)
- CAM operation metadata

**Status**: ✅ Working

---

### Step 4: Quality Evaluation (EVALAGENT GATE)
**Trigger**: After all agents complete (Dev, QA)

**Location**: `src/agents/eval_agent.py` (lines 50-150)

**Flow**:
```python
eval_result = await self._evaluate_with_eval_agent(
    task=original_task,
    output=dev_output,  # Implementation artifacts
    context=architecture  # From Architect
)

# eval_result = {
#     'score': 0.82,
#     'correctness': 0.85,
#     'completeness': 0.80,
#     'code_quality': 0.85,
#     'clarity': 0.70,
#     'feedback': "Good structure, improve error handling",
#     'should_retry': False (or True if score < 0.7)
# }

if eval_result['score'] >= 0.7:
    print("✅ Quality gate passed")
    # → Proceed to Step 5
else:
    print("⚠️ Quality score too low")
    # → BLOCKING: Retry not implemented yet!
```

**Status**: ⚠️ Partial - Scores exist, but retry not triggered

---

### Step 5: Approval Gate (MISSING - PHASE 55)
**What's Missing**: Currently NO approval workflow

**Expected Flow (when implemented)**:
```python
# After quality check passes:
emit_socket_io_event('workflow_complete', {
    'artifacts': [
        {
            'file_path': '/src/app.py',
            'preview': '...',
            'status': 'pending_approval'
        }
    ],
    'approval_required': True
})

# User reviews in UI, clicks "Approve" or "Reject"

# If Approve:
await approval_service.approve_workflow(workflow_id)
# → Proceed to Step 6

# If Reject:
await approval_service.reject_workflow(workflow_id)
# → Store rejection reason
# → Cancel deployment
# → Don't persist artifacts
```

**Where to Add**:
1. `src/api/routes/approval_routes.py` (new file)
2. Endpoints:
   - `POST /api/approvals/{workflow_id}/approve`
   - `POST /api/approvals/{workflow_id}/reject`
   - `GET /api/approvals/{workflow_id}/status`
3. Storage: New table in Weaviate or local cache
4. Integration in orchestrator:
   - After eval gate, before OPS step
   - Wait for approval (or timeout after 5 min)

**Status**: 🔴 NOT IMPLEMENTED (blocked feature, Phase 55+)

---

### Step 6: Deployment (OPS Agent)
**Trigger**: Quality gate passed AND approval received (when approval implemented)

**Location**: `src/agents/` (OPS agent - reference needed)

**Expected Flow**:
```python
# After all gates pass:
ops_result = await ops_agent.deploy(
    artifacts=artifact_list,
    environment='dev'  # or 'staging', 'prod'
)

# ops_result = {
#     'success': True,
#     'deployed_artifacts': [...],
#     'deployment_id': 'deploy-789',
#     'logs': [...]
# }
```

**Status**: ⚠️ Reference exists but implementation unclear

---

### Step 7: Socket.IO Emission (Real-Time UI Updates)
**Trigger**: Throughout artifact lifecycle

**Location**: `main.py`, `src/orchestration/orchestrator_with_elisya.py`

**Events Emitted**:
```python
# During workflow execution:
socketio.emit('workflow_status', {
    'step': 'dev',
    'status': 'running',
    'progress': 'Writing files...'
})

# When artifact created:
socketio.emit('artifact_created', {
    'file_path': '/src/app.py',
    'agent': 'Dev',
    'timestamp': '2026-01-09T10:30:00Z'
})

# When eval complete:
socketio.emit('artifact_evaluated', {
    'eval_score': 0.82,
    'approval_required': True,
    'feedback': '...'
})

# Final result:
socketio.emit('workflow_result', {
    'artifacts': [...],
    'summary': '...',
    'total_tokens': 8500
})
```

**Status**: ✅ Working (but approval event missing)

---

## Missing Components (Phase 55 Work)

### 🔴 Missing #1: Artifact Approval Gate

**What's Missing**:
- No socket event for "approval_required"
- No approval handler in main.py
- No approval storage/tracking
- No timeout logic
- No rollback on rejection

**Where to Add**:
```
File: src/api/routes/approval_routes.py (NEW)
├── POST /api/approvals/{workflow_id}/approve
│   └─ Store approval decision
│   └─ Emit socket event: workflow_approved
│   └─ Trigger OPS deployment
├── POST /api/approvals/{workflow_id}/reject
│   └─ Store rejection + reason
│   └─ Don't deploy
│   └─ Don't persist artifacts
└── GET /api/approvals/{workflow_id}/status
    └─ Return: pending/approved/rejected

File: main.py
├── Add socket event handler: approve_artifact_changes
│   └─ Call approval_routes
├── Add socket event handler: reject_artifact_changes
│   └─ Call approval_routes
└── Add timeout logic:
    └─ If no approval after 5 min: auto-reject
```

**Integration Points**:
1. After EvalAgent in orchestrator:
   ```python
   if eval_result['score'] >= 0.7:
       # Wait for approval (blocking or timeout)
       approval = await wait_for_approval(workflow_id, timeout=300)
       if not approval:
           print("Approval timeout")
           return
       if not approval['approved']:
           print("Approval rejected")
           return
   ```

2. Emit approval required event:
   ```python
   if eval_result['score'] >= 0.7:
       socketio.emit('approval_required', {
           'workflow_id': workflow_id,
           'artifacts': artifacts,
           'eval_score': eval_result['score']
       })
   ```

---

### 🔴 Missing #2: Artifact Versioning

**What's Missing**:
- No version history when file is modified
- No diff tracking between Dev runs
- No rollback capability
- No "what changed" visibility

**Where to Add**:
```
File: src/services/artifact_versioning_service.py (NEW)
├── on_artifact_create(artifact):
│   └─ Create version 1
├── on_artifact_update(artifact, previous_content):
│   └─ Compute diff
│   └─ Create new version with delta
└── get_artifact_versions(artifact_id):
    └─ Return all versions with diffs

File: src/api/routes/artifacts_routes.py (NEW)
├── GET /api/artifacts/{artifact_id}/versions
│   └─ List all versions
├── GET /api/artifacts/{artifact_id}/versions/{version_id}
│   └─ Get specific version
├── POST /api/artifacts/{artifact_id}/rollback/{version_id}
│   └─ Restore to previous version
└── GET /api/artifacts/{artifact_id}/diff?from={v1}&to={v2}
    └─ Show diff between versions
```

**CAM Integration**:
- Each version is a separate node in knowledge graph
- Versions linked with "predecessor" edge
- Diffs stored as artifact metadata

---

### 🔴 Missing #3: Atomic Artifact Transactions

**What's Missing**:
- No rollback if workflow fails after partial writes
- No guarantee all files written successfully
- No cleanup on failure

**Where to Add**:
```
File: src/services/artifact_transaction_service.py (NEW)
├── begin_transaction(workflow_id)
│   └─ Create transaction record
├── add_artifact(file_path, content)
│   └─ Stage file for write
├── commit_transaction()
│   └─ Write all files atomically
└── rollback_transaction()
    └─ Delete all written files

Usage in orchestrator:
1. tx = artifact_tx.begin_transaction(workflow_id)
2. For each artifact from Dev:
   - artifact_tx.add_artifact(file_path, content)
3. After eval passes:
   - artifact_tx.commit_transaction()
4. If anything fails:
   - artifact_tx.rollback_transaction()
```

---

## Socket Events Map (Current vs Needed)

| Event | Currently | Needed? | Implementation |
|-------|-----------|---------|-----------------|
| workflow_status | ✅ Emitted | ✅ Keep | Broadcast during execution |
| workflow_result | ✅ Emitted | ✅ Keep | After all steps complete |
| artifact_created | ⚠️ Mentioned | ✅ Add | After write_file succeeds |
| artifact_evaluated | ⚠️ Mentioned | ✅ Add | After EvalAgent scores |
| approval_required | ❌ Missing | ✅ Add | After eval gate, if score ≥ 0.7 |
| artifact_approved | ❌ Missing | ✅ Add | After user approves |
| artifact_rejected | ❌ Missing | ✅ Add | After user rejects |
| deployment_started | ❌ Missing | ✅ Add | Before OPS runs |
| deployment_complete | ❌ Missing | ✅ Add | After OPS succeeds |
| artifact_versioned | ❌ Missing | ⚠️ Add | If versioning implemented |
| tree_updated | ✅ Emitted | ✅ Keep | After CAM restructuring |

---

## Data Flow Diagram (Complete)

```
┌──────────────────┐
│  Dev Agent       │
│  Creates artifact│
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Tool Executor: write_file()      │
│ Writes to file system            │
└────────┬─────────────────────────┘
         │ (if success)
         ▼
┌──────────────────────────────────┐
│ CAM Engine                       │
│ - Compute similarity             │
│ - Decide: branch/merge/variant   │
│ - Update tree structure          │
│ - Store metadata                 │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Memory Manager (Triple-Write)    │
│ - Weaviate embeddings            │
│ - Local file storage             │
│ - CAM metadata                   │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Socket.IO                        │
│ emit('artifact_created')         │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ All Agents Complete              │
│ - Dev done                       │
│ - QA done                        │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ EvalAgent Quality Gate           │
│ Score ≥ 0.7 ?                    │
└────────┬──────────────┬──────────┘
         │ YES          │ NO
         ▼              ▼
    ┌────────┐      ┌─────────────────┐
    │ Gate   │      │ ⚠️ RETRY NEEDED │
    │ Pass   │      │ (Not impl yet)  │
    └────┬───┘      └─────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ 🔴 MISSING: Approval Gate        │
│ emit('approval_required')        │
│ Wait for user: approve/reject    │
└────────┬──────────────┬──────────┘
         │ APPROVED     │ REJECTED
         ▼              ▼
    ┌────────┐      ┌─────────────┐
    │ Deploy │      │ Don't store │
    │ (OPS)  │      │ artifacts   │
    └────┬───┘      └─────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ OPS Agent Deployment             │
│ Apply artifacts to target env    │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Socket.IO                        │
│ emit('deployment_complete')      │
│ emit('workflow_result')          │
└──────────────────────────────────┘
```

---

## Implementation Priority for Phase 55

### Priority 1 (Critical Path)
1. **Artifact Approval Gate** (blocks deployment)
   - Estimated: 3-4 hours
   - Impact: Prevents accidental deployments
   - Required for: User control over AI changes

2. **Approval Timeout Logic** (safety feature)
   - Estimated: 1 hour
   - Impact: Prevents hanging workflows
   - Required for: Production stability

### Priority 2 (Quality)
3. **Retry Logic on Low Scores** (quality improvement)
   - Estimated: 3-4 hours
   - Impact: Auto-fixes problems < 0.7 threshold
   - Required for: Reliable artifact generation

4. **Socket.IO Approval Events** (UI feedback)
   - Estimated: 1 hour
   - Impact: Real-time user notifications
   - Required for: Good UX

### Priority 3 (Nice to Have)
5. **Artifact Versioning** (history tracking)
   - Estimated: 4-5 hours
   - Impact: Can rollback to previous versions
   - Required for: Advanced workflows

6. **Atomic Transactions** (reliability)
   - Estimated: 2-3 hours
   - Impact: Rollback on partial failures
   - Required for: Large multi-file changes

---

## Testing Checklist for Phase 55

When implementing approval gate:
- [ ] Approval event emitted when eval score ≥ 0.7
- [ ] Approval event NOT emitted when eval score < 0.7
- [ ] User can click "approve" in UI
- [ ] POST /api/approvals/{workflow_id}/approve works
- [ ] After approval, OPS agent runs
- [ ] User can click "reject" in UI
- [ ] POST /api/approvals/{workflow_id}/reject works
- [ ] After rejection, artifacts NOT persisted
- [ ] Timeout after 5 minutes → auto-reject
- [ ] Rejection reason stored in workflow history
- [ ] Socket events flow correctly to frontend

---

## Conclusion

**Current State**: Artifacts are created, evaluated, and stored successfully.

**Main Gap**: Missing approval gate between evaluation and deployment.

**Impact**: Without approval gate, bad artifacts could be deployed if EvalAgent's quality gate threshold is lowered.

**Recommendation**: Implement approval gate in Phase 55 as Priority 1. It's a critical safety feature for production use.
