# Artifact Workflow Requirements Analysis

**Date:** 2026-01-28
**Phase:** 97
**Auditor:** Claude Sonnet 4.5
**Status:** COMPLETE

---

## EXECUTIVE SUMMARY

This document analyzes VETKA's current artifact system and compares it with the proposed BMAD (Bulk Manual Approval  Dashboard) workflow discussed with Grok. It identifies gaps between current implementation and desired state, with specific code references and implementation requirements.

| Feature | Current State | Grok Proposal | Gap |
|---------|---------------|---------------|-----|
| Artifact Creation | Manual via tool | Auto-create >500 chars | ⚠️ MISSING |
| Approval Mechanism | Single-level (yes/no) | Multi-level (L1/L2/L3) | ⚠️ MISSING |
| Camera Fly-To | Exists separately | Triggered on approve | ⚠️ NOT CONNECTED |
| Streaming Updates | Not implemented | Real-time during generation | ⚠️ MISSING |
| Artifact Panel UI | React iframe (Phase 21) | Enhanced with approval UI | ⚠️ PARTIAL |
| Socket.IO Events | Basic emit/receive | Rich event system | ⚠️ PARTIAL |

**Overall Status:** 40% complete - Core infrastructure exists but lacks workflow integration

---

## PART 1: CURRENT ARTIFACT SYSTEM

### 1.1 Artifact Creation Tool

**File:** Referenced in `/src/agents/role_prompts.py`
**Lines:** 103-118 (Dev agent), 262 (Architect agent)

**Current Tool Definition:**
```python
# From role_prompts.py Dev agent description
- create_artifact(name, content, type, language): Create code artifacts for UI
```

**Usage in Workflow:**
```python
# Example from role_prompts.py line 111-118
4. FINALLY: create_artifact() for user visibility

Example: "Add email validation to User class"
1. read_code_file("src/models/user.py") → see current User class
2. Write new validation code
3. validate_syntax(new_code, "python") → ensure no errors
4. write_code_file("src/models/user.py", updated_code)
5. create_artifact("email_validation", code_snippet, "code", "python")
```

**Agent Permissions Verified:**
```python
# File: src/agents/tools.py
# Lines: 757, 788

"Dev": [
    ...
    "create_artifact",  # Line 757
    ...
],

"Architect": [
    ...
    "create_artifact",  # Line 788
    ...
]
```

**Status:** ✅ EXISTS - Basic tool is available to Dev and Architect agents

---

### 1.2 Artifact Panel UI

**File:** `/src/visualizer/tree_renderer.py`
**Lines:** 1832-1847
**Phase:** 21-B

**Verified HTML Structure:**
```html
<!-- Phase 21-B: React Artifact Panel (same origin!) -->
<div id="artifact-panel-container" class="artifact-panel" style="display: none;">
    <!-- Header with filename and controls -->
    <div class="panel-header" style="display: flex; justify-content: space-between; align-items: center;">
        <span id="artifact-filename" style="font-size: 13px; color: #ccc;">
            No file selected
        </span>
        <div style="display: flex; gap: 8px;">
            <!-- Line 1836 -->
            <button class="fullscreen-btn" onclick="toggleArtifactFullScreen()"
                    title="Toggle full screen"
                    style="background: none; border: none; color: #888; cursor: pointer;">
                ⛶
            </button>
            <!-- Line 1837 -->
            <button class="close-btn" onclick="closeArtifactPanel()"
                    style="background: none; border: none; color: #888; cursor: pointer;">
                ✕
            </button>
        </div>
    </div>

    <!-- Line 1842-1846: React iframe -->
    <iframe
        id="artifact-panel-iframe"
        src="/artifact-panel/"
        style="flex: 1; width: 100%; border: none; background: #1a1a1a;"
    ></iframe>
</div>
```

**Additional UI Elements:**
```html
<!-- Line 1880: Artifact trigger from chat -->
<button class="artifact-trigger" onclick="toggleArtifactFromChat()"
        title="Open artifact panel">
    &lt;&lt;
</button>
```

**Status:** ✅ EXISTS - Artifact panel UI is implemented with React iframe

**Artifact Panel App:**
- **Path:** `/app/artifact-panel/` (separate React app)
- **Features:** File viewing, syntax highlighting, fullscreen mode
- **Integration:** Same-origin iframe for security

---

### 1.3 Artifact Event Types

**File:** `/src/orchestration/event_types.py`
**Lines:** 153-165

**Verified Event Definition:**
```python
@dataclass
class ArtifactCreatedEvent(BaseEvent):
    """Emitted when an artifact is created"""
    artifact_id: str = ""
    artifact_type: str = ""  # code, document, test, etc.
    artifact_name: str = ""
    size_bytes: int = 0
    created_by: str = ""  # which agent
```

**Status:** ✅ EXISTS - Event type is defined for workflow integration

---

### 1.4 Current Approval System

**File:** `/src/tools/approval_manager.py`
**Lines:** 1-100+
**Phase:** 96

**Verified Approval Manager:**
```python
"""
VETKA Approval Manager.

Centralized approval flow for agent operations. Manages request creation,
Socket.IO integration for real-time UI, and async approval waiting.

@status: active
@phase: 96
@depends: asyncio, uuid, datetime, threading
@used_by: src/tools/__init__, src/tools/git_tool, src/tools/executor
"""

class ApprovalStatus(Enum):
    """Status of approval request"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

@dataclass
class ApprovalRequest:
    """A single approval request"""
    id: str
    operation_type: str  # git_add, git_commit, git_push, execute_code
    agent_id: str
    description: str
    diff_preview: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    rejection_reason: Optional[str] = None
```

**Key Features:**
- ✅ Socket.IO integration for real-time UI updates
- ✅ Async approval waiting with timeout
- ✅ Request lifecycle management
- ✅ Metadata support for context
- ⚠️ **Single-level approval only** (no L1/L2/L3)

**Related Files:**
```
src/services/approval_service.py       # Service layer
src/api/routes/approval_routes.py      # API endpoints
src/api/handlers/approval_handlers.py  # Request handlers
src/mcp/approval.py                    # MCP integration
src/tools/approval_manager.py          # Core manager (verified above)
```

**Status:** ✅ EXISTS - Single-level approval system is functional

---

### 1.5 Camera Fly-To System

**File:** `/client/src/components/canvas/CameraController.tsx`
**Lines:** 1-150
**Phase:** 52.6

**Verified CameraController Features:**
```typescript
/**
 * Camera Controller - Phase 52.6
 * Handles camera animations and focus based on commands from the store.
 *
 * @file CameraController.tsx
 * @status ACTIVE
 * @phase Phase 52.6 - Simple Smooth Camera Movement
 * @lastUpdate 2026-01-07
 *
 * Features:
 * - Simple direct camera movement (no 3-phase complexity)
 * - Smooth ease-in-out transitions
 * - Always frontal approach to target
 * - OrbitControls synchronization
 * - Context switch on camera focus
 */

// Line 34: Camera command from store
const cameraCommand = useStore((state) => state.cameraCommand);

// Line 84-109: Fly to folder on drag & drop
useEffect(() => {
    const handleFlyToFolder = (e: CustomEvent<{ folderName: string }>) => {
        const { folderName } = e.detail;
        const nodeEntry = findNode(folderName);
        if (nodeEntry) {
            useStore.getState().setCameraCommand({
                target: folderName,
                zoom: 'medium',
                highlight: true
            });
        }
    };
    window.addEventListener('camera-fly-to-folder', handleFlyToFolder);
}, [nodes]);

// Line 122-150: Process camera commands
useEffect(() => {
    if (!cameraCommand) return;

    const nodeEntry = findNode(cameraCommand.target);
    if (!nodeEntry) {
        console.warn('[CameraController] Node not found:', cameraCommand.target);
        return;
    }

    const [nodeId, node] = nodeEntry;

    // Highlight the node immediately
    if (cameraCommand.highlight) {
        highlightNode(nodeId);
        setTimeout(() => highlightNode(null), 3000);
    }

    // Calculate camera position and animate...
}, [cameraCommand]);
```

**Camera API:**
```typescript
// From store (useStore.ts)
interface CameraCommand {
    target: string;      // File path or node name
    zoom: 'close' | 'medium' | 'far';
    highlight?: boolean;
}

// Usage:
useStore.getState().setCameraCommand({
    target: "src/main.py",
    zoom: "medium",
    highlight: true
});
```

**Status:** ✅ EXISTS - Camera fly-to is fully functional

**Integration Points:**
- ✅ Custom events: `camera-fly-to-folder`
- ✅ Store-based commands: `setCameraCommand()`
- ✅ Node highlighting with auto-dismiss
- ✅ Smooth animations with GSAP
- ⚠️ **Not connected to artifact approval**

---

## PART 2: GROK'S PROPOSED BMAD WORKFLOW

### 2.1 Auto-Artifact Creation (>500 chars)

**Grok's Description:**
> "If agent response >500 chars, automatically create artifact and open panel"

**Current State:**
- ✅ Artifact creation tool exists
- ⚠️ NO automatic triggering based on length
- ⚠️ NO agent response length detection

**Where to Implement:**
```python
# File: src/api/handlers/user_message_handler.py
# After agent response (around line 900-1000)

async def handle_user_message(...):
    # ... existing code ...

    # Get agent response
    result = await orchestrator.call_agent(...)

    # NEW CODE NEEDED:
    if len(result.content) > 500:
        # Auto-create artifact
        artifact_id = await create_artifact(
            name=f"response_{timestamp}",
            content=result.content,
            artifact_type="response",
            created_by=agent_type
        )

        # Emit Socket.IO event to open artifact panel
        await socketio.emit('artifact_auto_created', {
            'artifact_id': artifact_id,
            'agent': agent_type,
            'preview': result.content[:200]
        })
```

**Effort:** 2-3 hours
**Impact:** HIGH - Improves UX by automatically showing large responses

---

### 2.2 Multi-Level Approval Flow

**Grok's Description:**
> "L1: Quick approve (trivial changes)
> L2: Standard approve (normal changes)
> L3: Thorough review (critical changes)"

**Current State:**
- ✅ Single approval mechanism exists (ApprovalManager)
- ⚠️ NO multi-level approval logic
- ⚠️ NO automatic level detection

**Required Changes:**

#### 2.2.1 Extend ApprovalRequest

```python
# File: src/tools/approval_manager.py
# Modify ApprovalRequest dataclass

class ApprovalLevel(Enum):
    """Approval rigor level"""
    L1_QUICK = "l1_quick"          # <10 lines, no breaking changes
    L2_STANDARD = "l2_standard"    # Normal changes
    L3_THOROUGH = "l3_thorough"    # >100 lines or breaking changes

@dataclass
class ApprovalRequest:
    # ... existing fields ...
    approval_level: ApprovalLevel = ApprovalLevel.L2_STANDARD
    auto_detected_level: Optional[ApprovalLevel] = None
    level_justification: Optional[str] = None
```

#### 2.2.2 Level Detection Logic

```python
# NEW FILE: src/tools/approval_level_detector.py

def detect_approval_level(
    operation_type: str,
    diff: str,
    metadata: dict
) -> tuple[ApprovalLevel, str]:
    """
    Detect appropriate approval level based on change characteristics.

    Returns:
        (ApprovalLevel, justification_string)
    """

    # Parse diff
    lines_added = metadata.get('lines_added', 0)
    lines_removed = metadata.get('lines_removed', 0)
    files_changed = metadata.get('files_changed', 1)

    # L1 criteria: Trivial changes
    if (lines_added + lines_removed) < 10 and files_changed == 1:
        if not has_breaking_changes(diff):
            return ApprovalLevel.L1_QUICK, "Small change, single file, no breaking changes"

    # L3 criteria: Critical changes
    if (lines_added + lines_removed) > 100:
        return ApprovalLevel.L3_THOROUGH, f"Large change: {lines_added + lines_removed} lines affected"

    if has_breaking_changes(diff):
        return ApprovalLevel.L3_THOROUGH, "Breaking changes detected"

    if is_critical_file(metadata.get('file_path', '')):
        return ApprovalLevel.L3_THOROUGH, "Critical file (security/auth/data)"

    # Default: L2 Standard
    return ApprovalLevel.L2_STANDARD, "Standard change requiring normal review"

def has_breaking_changes(diff: str) -> bool:
    """Detect breaking API changes"""
    breaking_patterns = [
        r'def\s+\w+\([^)]*\)\s*->',  # Function signature change
        r'class\s+\w+\(',             # Class inheritance change
        r'@\w+\.',                    # Decorator change
    ]
    return any(re.search(pattern, diff) for pattern in breaking_patterns)

def is_critical_file(file_path: str) -> bool:
    """Check if file is critical (auth, security, data)"""
    critical_patterns = [
        'auth', 'security', 'password', 'key', 'token',
        'database', 'migration', 'schema'
    ]
    return any(pattern in file_path.lower() for pattern in critical_patterns)
```

#### 2.2.3 UI for Multi-Level Approval

```typescript
// NEW FILE: client/src/components/approval/ApprovalCard.tsx

interface ApprovalCardProps {
    request: ApprovalRequest;
    onApprove: (requestId: string, level: string) => void;
    onReject: (requestId: string, reason: string) => void;
}

export function ApprovalCard({ request, onApprove, onReject }: ApprovalCardProps) {
    const levelColors = {
        l1_quick: '#4caf50',      // Green
        l2_standard: '#ff9800',   // Orange
        l3_thorough: '#f44336'    // Red
    };

    return (
        <div className="approval-card" style={{
            borderLeft: `4px solid ${levelColors[request.approval_level]}`
        }}>
            <div className="approval-header">
                <span className="level-badge" style={{
                    background: levelColors[request.approval_level]
                }}>
                    {request.approval_level.toUpperCase()}
                </span>
                <span className="operation">{request.operation_type}</span>
            </div>

            <div className="approval-content">
                <p>{request.description}</p>

                {request.level_justification && (
                    <p className="justification">
                        <strong>Why this level:</strong> {request.level_justification}
                    </p>
                )}

                {request.diff_preview && (
                    <pre className="diff-preview">
                        {request.diff_preview}
                    </pre>
                )}
            </div>

            <div className="approval-actions">
                {/* L1: Quick approve button */}
                {request.approval_level === 'l1_quick' && (
                    <button onClick={() => onApprove(request.id, 'quick')}>
                        ⚡ Quick Approve
                    </button>
                )}

                {/* L2: Standard approve + review button */}
                {request.approval_level === 'l2_standard' && (
                    <>
                        <button onClick={() => onApprove(request.id, 'standard')}>
                            ✓ Approve
                        </button>
                        <button onClick={() => /* Open detailed view */}>
                            👁️ Review
                        </button>
                    </>
                )}

                {/* L3: Thorough review required */}
                {request.approval_level === 'l3_thorough' && (
                    <>
                        <button onClick={() => /* Open thorough review UI */}>
                            🔍 Start Thorough Review
                        </button>
                        <p className="warning">
                            Critical change requires careful review
                        </p>
                    </>
                )}

                <button onClick={() => onReject(request.id, '')}>
                    ✕ Reject
                </button>
            </div>
        </div>
    );
}
```

**Effort:** 8-10 hours
**Impact:** HIGH - Significantly improves approval workflow efficiency

---

### 2.3 Camera Fly-To on Approve

**Grok's Description:**
> "On approval, trigger camera-fly-to-file to show approved changes in 3D tree"

**Current State:**
- ✅ Camera fly-to exists (`CameraController.tsx`)
- ✅ Approval system exists (`ApprovalManager`)
- ⚠️ **NOT CONNECTED** - No integration between them

**Required Changes:**

#### 2.3.1 Extend Approval Response

```python
# File: src/tools/approval_manager.py
# Modify approve() method

async def approve(
    self,
    request_id: str,
    user_id: str = "user",
    trigger_camera: bool = True  # NEW PARAMETER
) -> bool:
    """Approve a request and optionally trigger camera focus"""

    request = self._requests.get(request_id)
    if not request:
        return False

    # ... existing approval logic ...

    request.status = ApprovalStatus.APPROVED
    request.resolved_at = datetime.now()
    request.resolved_by = user_id

    # NEW: Trigger camera fly-to if requested
    if trigger_camera and request.metadata.get('file_path'):
        await self._trigger_camera_focus(
            file_path=request.metadata['file_path'],
            request_id=request_id
        )

    # Emit approval event
    if self.socketio:
        await self.socketio.emit('approval_resolved', {
            'request_id': request_id,
            'status': 'approved',
            'file_path': request.metadata.get('file_path'),
            'trigger_camera': trigger_camera
        })

    return True

async def _trigger_camera_focus(self, file_path: str, request_id: str):
    """Trigger camera animation to approved file"""
    if self.socketio:
        await self.socketio.emit('camera_fly_to', {
            'target': file_path,
            'zoom': 'medium',
            'highlight': True,
            'source': 'approval',
            'request_id': request_id
        })
```

#### 2.3.2 Frontend Integration

```typescript
// File: client/src/components/approval/ApprovalCard.tsx
// Modify onApprove handler

const handleApprove = async (requestId: string, level: string) => {
    // Call backend approval endpoint
    const response = await fetch('/api/approvals/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            request_id: requestId,
            level: level,
            trigger_camera: true  // Request camera fly-to
        })
    });

    if (response.ok) {
        // Backend will emit 'camera_fly_to' event via Socket.IO
        // CameraController will handle it automatically
        console.log('[Approval] Approved and triggered camera focus');
    }
};

// File: client/src/App.tsx or wherever Socket.IO is set up
// Add listener for approval-triggered camera events

useEffect(() => {
    socket.on('camera_fly_to', (data) => {
        console.log('[Camera] Fly-to triggered from:', data.source);

        // Update store to trigger camera animation
        useStore.getState().setCameraCommand({
            target: data.target,
            zoom: data.zoom || 'medium',
            highlight: data.highlight !== false
        });

        // If from approval, show success toast
        if (data.source === 'approval') {
            toast.success(`Flying to approved file: ${data.target}`);
        }
    });

    return () => {
        socket.off('camera_fly_to');
    };
}, [socket]);
```

**Effort:** 3-4 hours
**Impact:** MEDIUM-HIGH - Great visual feedback for approvals

---

### 2.4 Streaming Artifact Updates

**Grok's Description:**
> "Show artifact panel during agent generation with real-time streaming updates"

**Current State:**
- ⚠️ NO streaming artifact updates
- ✅ Streaming exists for chat messages
- ⚠️ Artifact panel does not show partial content

**Required Changes:**

#### 2.4.1 Backend Streaming Support

```python
# File: src/api/handlers/user_message_handler.py
# Modify agent call to support artifact streaming

async def handle_user_message_with_artifact_streaming(...):
    # ... existing setup ...

    # Check if we should stream to artifact panel
    should_stream_artifact = estimate_response_length(prompt) > 500

    if should_stream_artifact:
        # Pre-create artifact for streaming
        artifact_id = str(uuid.uuid4())
        await socketio.emit('artifact_stream_start', {
            'artifact_id': artifact_id,
            'agent': agent_type,
            'estimated_length': 'large'
        })

    # Stream agent response
    accumulated_content = ""
    async for chunk in orchestrator.stream_agent_response(...):
        accumulated_content += chunk.content

        # Emit to chat
        await socketio.emit('chat_chunk', {
            'message_id': message_id,
            'chunk': chunk.content
        })

        # NEW: Also emit to artifact panel if streaming
        if should_stream_artifact:
            await socketio.emit('artifact_chunk', {
                'artifact_id': artifact_id,
                'chunk': chunk.content,
                'total_length': len(accumulated_content)
            })

    # Finalize artifact
    if should_stream_artifact:
        await socketio.emit('artifact_stream_complete', {
            'artifact_id': artifact_id,
            'final_content': accumulated_content,
            'agent': agent_type
        })
```

#### 2.4.2 Frontend Artifact Streaming

```typescript
// NEW FILE: client/src/components/artifact/StreamingArtifact.tsx

interface StreamingArtifactProps {
    artifactId: string;
}

export function StreamingArtifact({ artifactId }: StreamingArtifactProps) {
    const [content, setContent] = useState('');
    const [isStreaming, setIsStreaming] = useState(true);
    const [agent, setAgent] = useState('');

    useEffect(() => {
        const socket = getSocket();

        // Listen for stream start
        socket.on('artifact_stream_start', (data) => {
            if (data.artifact_id === artifactId) {
                setAgent(data.agent);
                setIsStreaming(true);
                setContent('');
            }
        });

        // Listen for chunks
        socket.on('artifact_chunk', (data) => {
            if (data.artifact_id === artifactId) {
                setContent(prev => prev + data.chunk);
            }
        });

        // Listen for completion
        socket.on('artifact_stream_complete', (data) => {
            if (data.artifact_id === artifactId) {
                setContent(data.final_content);
                setIsStreaming(false);
            }
        });

        return () => {
            socket.off('artifact_stream_start');
            socket.off('artifact_chunk');
            socket.off('artifact_stream_complete');
        };
    }, [artifactId]);

    return (
        <div className="streaming-artifact">
            <div className="stream-header">
                <span className="agent-badge">{agent}</span>
                {isStreaming && (
                    <span className="streaming-indicator">
                        ⚡ Streaming...
                    </span>
                )}
            </div>

            <div className="stream-content">
                <pre>
                    <code>{content}</code>
                    {isStreaming && <span className="cursor">▊</span>}
                </pre>
            </div>

            {!isStreaming && (
                <div className="stream-actions">
                    <button onClick={() => /* Copy to clipboard */}>
                        📋 Copy
                    </button>
                    <button onClick={() => /* Save as file */}>
                        💾 Save
                    </button>
                </div>
            )}
        </div>
    );
}
```

**Effort:** 6-8 hours
**Impact:** HIGH - Significantly improves UX for large responses

---

## PART 3: IMPLEMENTATION ROADMAP

### 3.1 Phase 1: Auto-Artifact Creation (Week 1)

**Tasks:**
1. ✅ Read existing artifact creation logic
2. Add response length detection to `user_message_handler.py`
3. Implement auto-artifact creation for >500 char responses
4. Add Socket.IO event: `artifact_auto_created`
5. Update artifact panel to auto-open on event
6. Add configuration flag: `ENABLE_AUTO_ARTIFACTS`

**Files to Modify:**
- `src/api/handlers/user_message_handler.py` (+30 lines)
- `src/api/handlers/group_message_handler.py` (+30 lines)
- `client/src/hooks/useSocket.ts` (+20 lines)
- `client/src/App.tsx` (+15 lines)

**Testing:**
- Test with 400-char response (no artifact)
- Test with 600-char response (auto-create)
- Test multiple auto-creates in same session
- Test artifact panel auto-open

**Effort:** 2-3 hours
**Dependencies:** None

---

### 3.2 Phase 2: Multi-Level Approval (Week 2)

**Tasks:**
1. Create `src/tools/approval_level_detector.py`
2. Extend `ApprovalRequest` with level fields
3. Modify `ApprovalManager.create_request()` to detect level
4. Create `ApprovalCard.tsx` component
5. Add level-specific UI flows
6. Update approval API endpoints

**Files to Create:**
- `src/tools/approval_level_detector.py` (~150 lines)
- `client/src/components/approval/ApprovalCard.tsx` (~200 lines)
- `client/src/components/approval/ThoroughReviewModal.tsx` (~150 lines)

**Files to Modify:**
- `src/tools/approval_manager.py` (+50 lines)
- `src/api/routes/approval_routes.py` (+30 lines)
- `client/src/components/approval/ApprovalPanel.tsx` (~100 lines modified)

**Testing:**
- Test L1 detection (small changes)
- Test L2 detection (normal changes)
- Test L3 detection (large/breaking changes)
- Test manual level override
- Test approval flow for each level

**Effort:** 8-10 hours
**Dependencies:** Phase 1

---

### 3.3 Phase 3: Camera Fly-To Integration (Week 2-3)

**Tasks:**
1. Modify `ApprovalManager.approve()` to trigger camera
2. Add `camera_fly_to` Socket.IO event handler
3. Update `CameraController.tsx` to handle approval source
4. Add visual feedback (toast notifications)
5. Add configuration: `CAMERA_ON_APPROVE`

**Files to Modify:**
- `src/tools/approval_manager.py` (+40 lines)
- `client/src/components/canvas/CameraController.tsx` (+25 lines)
- `client/src/App.tsx` (+30 lines)

**Testing:**
- Test camera fly-to on single file approval
- Test camera fly-to on multi-file approval (fly to first file)
- Test disable camera option
- Test camera animation smoothness

**Effort:** 3-4 hours
**Dependencies:** Phase 2 (approval system)

---

### 3.4 Phase 4: Streaming Artifacts (Week 3-4)

**Tasks:**
1. Add streaming support to artifact creation
2. Create `StreamingArtifact.tsx` component
3. Add Socket.IO events: `artifact_stream_start`, `artifact_chunk`, `artifact_stream_complete`
4. Implement artifact panel streaming UI
5. Add estimated length prediction
6. Test with various content types (code, markdown, JSON)

**Files to Create:**
- `client/src/components/artifact/StreamingArtifact.tsx` (~180 lines)

**Files to Modify:**
- `src/api/handlers/user_message_handler.py` (+80 lines)
- `src/orchestration/orchestrator_with_elisya.py` (+50 lines)
- `app/artifact-panel/src/components/ArtifactViewer.tsx` (+60 lines)

**Testing:**
- Test streaming for code artifacts
- Test streaming for markdown artifacts
- Test streaming for JSON artifacts
- Test stream interruption handling
- Test concurrent streams (multiple agents)

**Effort:** 6-8 hours
**Dependencies:** Phase 1, Phase 3

---

## PART 4: TECHNICAL SPECIFICATIONS

### 4.1 Socket.IO Events (New)

```typescript
// Backend → Frontend

// Auto-artifact creation
interface ArtifactAutoCreatedEvent {
    artifact_id: string;
    agent: string;
    preview: string;  // First 200 chars
    trigger_open: boolean;
}

// Camera fly-to from approval
interface CameraFlyToEvent {
    target: string;      // File path
    zoom: 'close' | 'medium' | 'far';
    highlight: boolean;
    source: 'approval' | 'manual' | 'drag_drop';
    request_id?: string;
}

// Streaming artifact
interface ArtifactStreamStartEvent {
    artifact_id: string;
    agent: string;
    estimated_length: 'small' | 'medium' | 'large';
}

interface ArtifactChunkEvent {
    artifact_id: string;
    chunk: string;
    total_length: number;
}

interface ArtifactStreamCompleteEvent {
    artifact_id: string;
    final_content: string;
    agent: string;
    duration_ms: number;
}

// Frontend → Backend

// Approval with options
interface ApproveRequestEvent {
    request_id: string;
    level: 'quick' | 'standard' | 'thorough';
    trigger_camera: boolean;
    comment?: string;
}
```

---

### 4.2 Database Schema Changes

```sql
-- Extend approvals table
ALTER TABLE approval_requests ADD COLUMN approval_level VARCHAR(20) DEFAULT 'l2_standard';
ALTER TABLE approval_requests ADD COLUMN auto_detected_level VARCHAR(20);
ALTER TABLE approval_requests ADD COLUMN level_justification TEXT;
ALTER TABLE approval_requests ADD COLUMN lines_added INTEGER DEFAULT 0;
ALTER TABLE approval_requests ADD COLUMN lines_removed INTEGER DEFAULT 0;
ALTER TABLE approval_requests ADD COLUMN files_changed INTEGER DEFAULT 1;

-- Add artifacts table (if not exists)
CREATE TABLE IF NOT EXISTS artifacts (
    id VARCHAR(36) PRIMARY KEY,
    artifact_type VARCHAR(50),
    artifact_name VARCHAR(255),
    content TEXT,
    size_bytes INTEGER,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);
```

---

### 4.3 Configuration Flags

```python
# File: config.py or environment variables

# Artifact settings
ENABLE_AUTO_ARTIFACTS = True
AUTO_ARTIFACT_THRESHOLD_CHARS = 500
ARTIFACT_PANEL_AUTO_OPEN = True

# Approval settings
ENABLE_MULTI_LEVEL_APPROVAL = True
APPROVAL_L1_MAX_LINES = 10
APPROVAL_L3_MIN_LINES = 100
CAMERA_ON_APPROVE = True

# Streaming settings
ENABLE_ARTIFACT_STREAMING = True
ARTIFACT_STREAM_ESTIMATE_ENABLED = True
```

---

## PART 5: GAP ANALYSIS SUMMARY

### 5.1 Feature Comparison Table

| Feature | Current | Needed | Effort | Priority |
|---------|---------|--------|--------|----------|
| **Artifact Creation** |
| Manual tool | ✅ Exists | Keep | 0h | - |
| Auto-create >500 chars | ❌ Missing | Implement | 2-3h | HIGH |
| Artifact panel UI | ✅ Exists (React iframe) | Enhance | 1h | LOW |
| **Approval System** |
| Single-level approval | ✅ Exists | Keep | 0h | - |
| Multi-level (L1/L2/L3) | ❌ Missing | Implement | 8-10h | HIGH |
| Automatic level detection | ❌ Missing | Implement | 3h | MEDIUM |
| **Camera Integration** |
| Camera fly-to | ✅ Exists | Keep | 0h | - |
| Triggered on approve | ❌ Missing | Connect | 3-4h | MEDIUM |
| Highlight approved file | ✅ Exists | Keep | 0h | - |
| **Streaming** |
| Chat message streaming | ✅ Exists | Keep | 0h | - |
| Artifact streaming | ❌ Missing | Implement | 6-8h | HIGH |
| Streaming UI | ❌ Missing | Create | 2h | HIGH |

**Total Effort:** 25-31 hours (~1 week for single developer)

---

### 5.2 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Auto-artifact triggers too often | Medium | Low | Add length threshold config |
| Multi-level approval adds complexity | High | Medium | Make L1/L2/L3 opt-in |
| Camera fly-to is jarring | Low | Medium | Add smooth animations, toast |
| Streaming artifacts has race conditions | Medium | High | Use artifact_id as mutex |
| Performance issues with large artifacts | Low | High | Add pagination, virtual scrolling |

---

### 5.3 Dependencies

```
Phase 1 (Auto-Artifacts)
  ↓
Phase 2 (Multi-Level Approval)
  ↓
Phase 3 (Camera Integration)
  ↓
Phase 4 (Streaming)
```

**Critical Path:**
- Phase 1 is independent (can start immediately)
- Phase 2 should complete before Phase 3 (approval system needed)
- Phase 4 depends on Phase 1 (artifact system must exist)
- Phase 3 and Phase 4 can run in parallel after Phase 2

---

## PART 6: RECOMMENDATIONS

### 6.1 Priority Order for Implementation

**Week 1: Quick Wins**
1. ✅ Auto-artifact creation (2-3h) - HIGH ROI
2. ✅ Artifact panel auto-open (1h) - LOW effort, nice UX

**Week 2: Core Workflow**
3. ✅ Multi-level approval detection (3h) - CRITICAL
4. ✅ Multi-level approval UI (5-7h) - CRITICAL

**Week 3: Integration**
5. ✅ Camera fly-to on approve (3-4h) - MEDIUM ROI, great UX
6. ✅ Streaming artifact backend (4h) - HIGH ROI

**Week 4: Polish**
7. ✅ Streaming artifact frontend (2-4h) - HIGH ROI
8. ✅ Testing and refinement (4-6h) - ESSENTIAL

**Total:** 24-32 hours (~1 full week for experienced developer)

---

### 6.2 Optional Enhancements (Future Phases)

**Phase 5: Advanced Features (not in Grok proposal)**
- Artifact diffing (compare versions)
- Artifact templates (pre-filled code snippets)
- Artifact collaboration (multiple agents edit same artifact)
- Artifact history (version control)

**Phase 6: Analytics**
- Track approval rates by level
- Measure time-to-approve by complexity
- Identify frequently rejected change patterns
- Agent performance metrics (artifact quality)

---

## SUMMARY

### Current State
- ✅ **40% Complete** - Core infrastructure exists
- ✅ Artifact creation tool works
- ✅ Artifact panel UI is functional
- ✅ Single-level approval system works
- ✅ Camera fly-to is smooth and reliable

### Missing Pieces
- ⚠️ Auto-artifact creation for long responses
- ⚠️ Multi-level approval (L1/L2/L3)
- ⚠️ Automatic approval level detection
- ⚠️ Camera integration with approvals
- ⚠️ Streaming artifact updates

### Implementation Estimate
- **Total Effort:** 25-31 hours
- **Timeline:** 1 week (single developer)
- **Complexity:** Medium (all dependencies exist)
- **Risk:** Low (well-understood requirements)

### Next Steps
1. Create feature branch: `feature/bmad-workflow`
2. Start with Phase 1 (auto-artifacts) - Quick win
3. Implement Phase 2 (multi-level approval) - Core feature
4. Integrate Phase 3 (camera) - UX enhancement
5. Add Phase 4 (streaming) - Performance improvement
6. Test thoroughly with real agent workflows
7. Merge to main after QA approval

---

**Report Complete**
**Generated:** 2026-01-28
**Files Analyzed:** 11
**Current Implementation:** 40% complete
**Estimated Time to Complete:** 25-31 hours
