# VETKA Phase 104.4 - Approval Socket.IO Specification

**Status:** ACTIVE
**Phase:** 104.4
**Created:** 2026-01-31
**Author:** Claude Opus 4.5

## Overview

Real-time Socket.IO events for VETKA approval workflow. Enables users to review, approve, reject, or edit agent-generated artifacts directly in the chat UI.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        APPROVAL FLOW                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Agent (Dev)          EvalAgent           ApprovalService        │
│      │                    │                     │                │
│      │  1. Generate       │                     │                │
│      │     Artifacts      │                     │                │
│      ├───────────────────>│                     │                │
│      │                    │  2. Score &         │                │
│      │                    │     Feedback        │                │
│      │                    ├────────────────────>│                │
│      │                    │                     │                │
│      │                    │  3. emit            │                │
│      │                    │  approval_request   │                │
│      │                    │  ─────────────────> │ ──> Chat UI    │
│      │                    │                     │                │
│      │                    │                     │  4. User       │
│      │                    │                     │     reviews    │
│      │                    │                     │     & decides  │
│      │                    │                     │                │
│      │                    │  5. approval_       │                │
│      │                    │     response        │                │
│      │  <───────────────────────────────────────┤ <── Chat UI    │
│      │                    │                     │                │
│      │  6. Continue/Stop  │                     │                │
│      │     based on       │                     │                │
│      │     decision       │                     │                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Socket Events

### Server -> Client Events

#### `approval_request`

Emitted when artifacts need user approval.

```typescript
interface ApprovalRequest {
  type: 'approval_request';
  request_id: string;        // Unique ID for this approval request
  workflow_id: string;       // Parent workflow ID
  group_id: string;          // Chat room/group ID
  artifacts: ArtifactPreview[];
  eval_score: number;        // 0.0 - 1.0
  eval_feedback: string;     // EvalAgent's textual feedback
  score_level: 'high' | 'medium' | 'low';
  actions: ('approve' | 'reject' | 'edit')[];
  timeout_seconds: number;   // Default: 300 (5 min)
}

interface ArtifactPreview {
  id: string;
  filename: string;
  language: string;          // 'python', 'typescript', etc.
  content_preview: string;   // First 500 chars
  full_content?: string;     // Complete content (optional)
  lines: number;
  agent: string;             // 'Dev', 'QA', etc.
  artifact_type: 'code' | 'config' | 'doc' | 'test';
}
```

**Score Level Thresholds:**
- `high` (green): score >= 0.8
- `medium` (yellow): score >= 0.6
- `low` (red): score < 0.6

#### `approval_result`

Sent after processing user's decision.

```typescript
interface ApprovalResult {
  request_id: string;
  status: 'approved' | 'rejected' | 'editing' | 'error' | 'timeout';
  message: string;
  edited_artifacts?: string[];  // IDs of edited artifacts (for 'editing' status)
}
```

#### `approval_error`

Sent when an error occurs during approval processing.

```typescript
interface ApprovalError {
  request_id: string;
  error: string;
}
```

#### `approval_details`

Response to `get_approval_details` request.

```typescript
interface ApprovalDetails {
  id: string;
  workflow_id: string;
  artifacts: ArtifactPreview[];
  eval_score: number;
  eval_feedback: string;
  status: 'pending' | 'approved' | 'rejected' | 'timeout';
  created_at: string;         // ISO timestamp
  decided_at: string | null;
  decision_reason: string | null;
}
```

### Client -> Server Events

#### `approval_response`

User's decision on an approval request.

```typescript
interface ApprovalResponse {
  request_id: string;
  action: 'approve' | 'reject' | 'edit';
  reason?: string;            // Optional reason for rejection
  group_id?: string;          // For room-specific broadcast
  edited_content?: Record<string, string>;  // artifact_id -> new content
}
```

#### `get_approval_details`

Request full details of an approval request.

```typescript
interface GetApprovalDetails {
  request_id: string;
}
```

## UI Implementation Guide

### Approval Modal Component

The chat UI should render an approval modal when receiving `approval_request`:

```tsx
// Pseudo-code for ApprovalModal component
function ApprovalModal({ request }: { request: ApprovalRequest }) {
  return (
    <Modal>
      <Header>
        <ScoreBadge score={request.eval_score} level={request.score_level} />
        <Title>Approve Artifacts?</Title>
      </Header>

      <Body>
        {/* EvalAgent Feedback */}
        <FeedbackCard>{request.eval_feedback}</FeedbackCard>

        {/* Artifact Previews */}
        {request.artifacts.map(artifact => (
          <ArtifactPreview
            key={artifact.id}
            filename={artifact.filename}
            language={artifact.language}
            content={artifact.content_preview}
            lines={artifact.lines}
            agent={artifact.agent}
          />
        ))}
      </Body>

      <Footer>
        <RejectButton onClick={() => emit('approval_response', {
          request_id: request.request_id,
          action: 'reject',
          reason: 'User rejected'
        })} />
        <EditButton onClick={() => emit('approval_response', {
          request_id: request.request_id,
          action: 'edit'
        })} />
        <ApproveButton onClick={() => emit('approval_response', {
          request_id: request.request_id,
          action: 'approve'
        })} />
      </Footer>
    </Modal>
  );
}
```

### Score Badge Colors

| Score Level | Score Range | Badge Color | Background |
|-------------|-------------|-------------|------------|
| high        | >= 0.8      | #10B981     | #D1FAE5    |
| medium      | >= 0.6      | #F59E0B     | #FEF3C7    |
| low         | < 0.6       | #EF4444     | #FEE2E2    |

### Timeout Handling

- Default timeout: 300 seconds (5 minutes)
- UI should show countdown timer
- On timeout, `approval_result` with `status: 'timeout'` is emitted
- Workflow proceeds as if rejected on timeout

## Integration Points

### Backend Files

| File | Purpose |
|------|---------|
| `src/api/handlers/approval_socket_handler.py` | Socket.IO event handlers |
| `src/services/approval_service.py` | Approval state management |
| `src/api/handlers/approval_handlers.py` | Legacy handlers (Phase 39.7) |

### Frontend Files

| File | Purpose |
|------|---------|
| `client/src/types/approval.ts` | TypeScript type definitions |
| `client/src/hooks/useSocket.ts` | Socket event listeners (lines 84-102) |
| `client/src/components/ApprovalModal.tsx` | Approval UI component (TODO) |

### Handler Registration

Add to `src/api/handlers/__init__.py`:

```python
from .approval_socket_handler import register_approval_socket_handlers

# In register_all_handlers():
register_approval_socket_handlers(sio, app)
```

## Testing

### Manual Test Flow

1. Start VETKA server
2. Open chat UI
3. Send message that triggers artifact generation
4. Verify `approval_request` event received
5. Click Approve/Reject/Edit
6. Verify `approval_result` event received
7. Verify workflow continues/stops accordingly

### Test Events (Development)

```javascript
// Emit test approval request from browser console
socket.emit('test_approval');

// Check pending approvals
socket.emit('get_pending_approvals');
```

## Related Documentation

- `docs/103_ph/TASK_B_ARTIFACT_TO_FILE.md` - Artifact staging flow
- `docs/104_ph/INTEGRATION_VALIDATION.md` - Phase 104 integration tests
- `src/services/approval_service.py` - ApprovalService class documentation

## Changelog

| Date | Phase | Change |
|------|-------|--------|
| 2026-01-31 | 104.4 | Initial Socket.IO approval spec |
| 2026-01-31 | 104.4 | Added TypeScript types |
| 2026-01-31 | 104.4 | Added UI implementation guide |
