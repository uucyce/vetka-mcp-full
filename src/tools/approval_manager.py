"""
VETKA Approval Manager.

Centralized approval flow for agent operations. Manages request creation,
Socket.IO integration for real-time UI, and async approval waiting.

@status: active
@phase: 96
@depends: asyncio, uuid, datetime, threading
@used_by: src/tools/__init__, src/tools/git_tool, src/tools/executor

Usage:
    from src.tools.approval_manager import ApprovalManager, ApprovalRequest

    manager = ApprovalManager(socketio=socketio)

    # Create approval request
    request_id = await manager.create_request(
        operation_type="git_commit",
        agent_id="dev-001",
        description="Commit: Fix login bug",
        diff_preview="..."
    )

    # Frontend handles via Socket.IO:
    # - 'approval_needed' event emitted
    # - User clicks Approve/Reject
    # - 'approval_response' event received

    # Check result
    result = await manager.wait_for_approval(request_id, timeout=120)
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List
from enum import Enum
import threading


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

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "operation_type": self.operation_type,
            "agent_id": self.agent_id,
            "description": self.description,
            "diff_preview": self.diff_preview[:2000] if self.diff_preview else None,
            "metadata": self.metadata,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "expires_in_seconds": self.expires_in_seconds,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "rejection_reason": self.rejection_reason
        }

    @property
    def expires_in_seconds(self) -> Optional[int]:
        if not self.expires_at:
            return None
        remaining = (self.expires_at - datetime.now()).total_seconds()
        return max(0, int(remaining))

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


class ApprovalManager:
    """
    Manages approval requests for agent operations.

    Features:
    - Request creation with timeout
    - Socket.IO integration for real-time UI
    - Async wait for approval result
    - Auto-reject on timeout
    """

    DEFAULT_TIMEOUT = 120  # 2 minutes

    def __init__(
        self,
        socketio=None,
        default_timeout: int = DEFAULT_TIMEOUT
    ):
        self.socketio = socketio
        self.default_timeout = default_timeout
        self._requests: Dict[str, ApprovalRequest] = {}
        self._events: Dict[str, asyncio.Event] = {}
        self._lock = threading.Lock()

        # Callbacks
        self._on_approved: Optional[Callable] = None
        self._on_rejected: Optional[Callable] = None

    def set_socketio(self, socketio):
        """Set Socket.IO instance (can be done after init)"""
        self.socketio = socketio

    async def create_request(
        self,
        operation_type: str,
        agent_id: str,
        description: str,
        diff_preview: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> str:
        """
        Create a new approval request.

        Args:
            operation_type: Type of operation (git_add, git_commit, etc.)
            agent_id: ID of the agent requesting approval
            description: Human-readable description
            diff_preview: Code/diff preview for user review
            metadata: Additional metadata
            timeout: Timeout in seconds (default: 120)

        Returns:
            Request ID
        """
        timeout = timeout or self.default_timeout

        request_id = f"approval_{uuid.uuid4().hex[:12]}"

        request = ApprovalRequest(
            id=request_id,
            operation_type=operation_type,
            agent_id=agent_id,
            description=description,
            diff_preview=diff_preview,
            metadata=metadata or {},
            expires_at=datetime.now() + timedelta(seconds=timeout)
        )

        with self._lock:
            self._requests[request_id] = request
            self._events[request_id] = asyncio.Event()

        # Emit to frontend via Socket.IO
        if self.socketio:
            self.socketio.emit('approval_needed', request.to_dict())
            print(f"[APPROVAL] Emitted 'approval_needed' for {request_id}")

        # Start expiration timer
        asyncio.create_task(self._expiration_timer(request_id, timeout))

        return request_id

    async def _expiration_timer(self, request_id: str, timeout: int):
        """Auto-reject request after timeout"""
        await asyncio.sleep(timeout)

        with self._lock:
            request = self._requests.get(request_id)
            if request and request.status == ApprovalStatus.PENDING:
                request.status = ApprovalStatus.EXPIRED
                request.resolved_at = datetime.now()

                # Signal waiting coroutines
                event = self._events.get(request_id)
                if event:
                    event.set()

                # Emit to frontend
                if self.socketio:
                    self.socketio.emit('approval_resolved', {
                        'id': request_id,
                        'status': 'expired',
                        'message': 'Request expired'
                    })

                print(f"[APPROVAL] Request {request_id} expired")

    def approve(
        self,
        request_id: str,
        approved_by: str = "user"
    ) -> bool:
        """
        Approve a pending request.

        Args:
            request_id: ID of the request
            approved_by: Who approved (default: "user")

        Returns:
            True if successfully approved
        """
        with self._lock:
            request = self._requests.get(request_id)

            if not request:
                print(f"[APPROVAL] Request not found: {request_id}")
                return False

            if request.status != ApprovalStatus.PENDING:
                print(f"[APPROVAL] Request not pending: {request_id} ({request.status})")
                return False

            if request.is_expired:
                request.status = ApprovalStatus.EXPIRED
                print(f"[APPROVAL] Request expired: {request_id}")
                return False

            request.status = ApprovalStatus.APPROVED
            request.resolved_at = datetime.now()
            request.resolved_by = approved_by

            # Signal waiting coroutines
            event = self._events.get(request_id)
            if event:
                event.set()

            # Emit to frontend
            if self.socketio:
                self.socketio.emit('approval_resolved', {
                    'id': request_id,
                    'status': 'approved',
                    'message': f'Approved by {approved_by}'
                })

            print(f"[APPROVAL] Request {request_id} APPROVED by {approved_by}")

            # Call callback if set
            if self._on_approved:
                self._on_approved(request)

            return True

    def reject(
        self,
        request_id: str,
        reason: str = "",
        rejected_by: str = "user"
    ) -> bool:
        """
        Reject a pending request.

        Args:
            request_id: ID of the request
            reason: Rejection reason
            rejected_by: Who rejected

        Returns:
            True if successfully rejected
        """
        with self._lock:
            request = self._requests.get(request_id)

            if not request:
                print(f"[APPROVAL] Request not found: {request_id}")
                return False

            if request.status != ApprovalStatus.PENDING:
                print(f"[APPROVAL] Request not pending: {request_id}")
                return False

            request.status = ApprovalStatus.REJECTED
            request.resolved_at = datetime.now()
            request.resolved_by = rejected_by
            request.rejection_reason = reason

            # Signal waiting coroutines
            event = self._events.get(request_id)
            if event:
                event.set()

            # Emit to frontend
            if self.socketio:
                self.socketio.emit('approval_resolved', {
                    'id': request_id,
                    'status': 'rejected',
                    'reason': reason,
                    'message': f'Rejected by {rejected_by}'
                })

            print(f"[APPROVAL] Request {request_id} REJECTED by {rejected_by}: {reason}")

            # Call callback if set
            if self._on_rejected:
                self._on_rejected(request)

            return True

    async def wait_for_approval(
        self,
        request_id: str,
        timeout: Optional[int] = None
    ) -> ApprovalRequest:
        """
        Wait for approval request to be resolved.

        Args:
            request_id: ID of the request
            timeout: Max wait time in seconds

        Returns:
            ApprovalRequest with final status
        """
        timeout = timeout or self.default_timeout + 10  # Extra buffer

        event = self._events.get(request_id)
        if not event:
            raise ValueError(f"Unknown request: {request_id}")

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            # Force expire
            with self._lock:
                request = self._requests.get(request_id)
                if request and request.status == ApprovalStatus.PENDING:
                    request.status = ApprovalStatus.EXPIRED

        return self._requests.get(request_id)

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get approval request by ID"""
        return self._requests.get(request_id)

    def get_pending_requests(self) -> List[ApprovalRequest]:
        """Get all pending requests"""
        with self._lock:
            return [
                r for r in self._requests.values()
                if r.status == ApprovalStatus.PENDING and not r.is_expired
            ]

    def cancel_request(self, request_id: str) -> bool:
        """Cancel a pending request"""
        with self._lock:
            request = self._requests.get(request_id)
            if request and request.status == ApprovalStatus.PENDING:
                request.status = ApprovalStatus.CANCELLED
                request.resolved_at = datetime.now()

                event = self._events.get(request_id)
                if event:
                    event.set()

                return True
            return False

    def cleanup_old_requests(self, max_age_hours: int = 24):
        """Remove old resolved requests"""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        with self._lock:
            to_remove = [
                rid for rid, r in self._requests.items()
                if r.status != ApprovalStatus.PENDING and r.created_at < cutoff
            ]

            for rid in to_remove:
                del self._requests[rid]
                self._events.pop(rid, None)

            if to_remove:
                print(f"[APPROVAL] Cleaned up {len(to_remove)} old requests")


# ============================================================================
# APPROVAL CALLBACK FOR SafeToolExecutor
# ============================================================================

async def create_approval_callback(manager: ApprovalManager):
    """
    Create an approval callback for SafeToolExecutor.

    Usage:
        from src.tools.executor import SafeToolExecutor
        from src.tools.approval_manager import ApprovalManager, create_approval_callback

        manager = ApprovalManager(socketio=socketio)
        callback = await create_approval_callback(manager)
        executor = SafeToolExecutor(approval_callback=callback)
    """
    async def approval_callback(tool_call) -> bool:
        """
        Callback for SafeToolExecutor.
        Returns True if approved, False if rejected/expired.
        """
        request_id = await manager.create_request(
            operation_type=f"tool_{tool_call.tool_name}",
            agent_id=tool_call.agent_type,
            description=f"Execute tool: {tool_call.tool_name}",
            metadata={"arguments": tool_call.arguments}
        )

        result = await manager.wait_for_approval(request_id)

        return result.status == ApprovalStatus.APPROVED

    return approval_callback


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'ApprovalManager',
    'ApprovalRequest',
    'ApprovalStatus',
    'create_approval_callback'
]
