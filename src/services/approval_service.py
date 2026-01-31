# === PHASE 55: APPROVAL SERVICE ===
"""
Approval workflow for agent artifacts.

User must approve/reject before deployment. Emits Socket.IO events for UI modals.

@status: active
@phase: 104
@depends: asyncio, dataclasses
@used_by: approval_routes.py, orchestrator_with_elisya.py
"""

import asyncio
import logging
import os
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# MARKER_104_APPROVAL_MODE
# Approval mode configuration via environment variable
# vetka = user must approve (modal in chat) - DEFAULT
# mycelium = L2 Scout auto-approves based on criteria
APPROVAL_MODE = os.environ.get("VETKA_APPROVAL_MODE", "vetka").lower()


@dataclass
class AuditReport:
    """
    Report from L2 Scout auditor for MYCELIUM mode.

    MARKER_104_MYCELIUM_AUTO
    """
    score: float  # 0.0 - 1.0
    auto_approved: bool
    issues: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)
    artifact_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'score': self.score,
            'auto_approved': self.auto_approved,
            'issues': self.issues,
            'recommendations': self.recommendations,
            'artifact_scores': self.artifact_scores
        }


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


@dataclass
class ApprovalRequest:
    """Single approval request."""
    id: str
    workflow_id: str
    artifacts: list
    eval_score: float
    eval_feedback: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    decided_at: Optional[datetime] = None
    decision_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'artifacts': self.artifacts,
            'eval_score': self.eval_score,
            'eval_feedback': self.eval_feedback,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'decided_at': self.decided_at.isoformat() if self.decided_at else None,
            'decision_reason': self.decision_reason
        }


class ApprovalService:
    """
    Manages approval workflow for agent artifacts.

    Flow (VETKA mode - default):
    1. Agent creates artifacts
    2. EvalAgent scores (>= 0.7)
    3. ApprovalService.request_approval()
    4. Socket event → UI shows modal
    5. User approves/rejects
    6. Workflow continues or stops

    Flow (MYCELIUM mode):
    1. Agent creates artifacts
    2. EvalAgent scores (>= 0.7)
    3. ApprovalService.request_approval()
    4. L2 Scout auditor evaluates artifacts
    5. If auto_approved: workflow continues immediately
    6. If flagged: falls back to user approval (VETKA mode)

    MARKER_104_MYCELIUM_AUTO
    """

    def __init__(self):
        self._pending: Dict[str, ApprovalRequest] = {}
        self._completed: Dict[str, ApprovalRequest] = {}  # Track completed requests
        self._decisions: Dict[str, asyncio.Event] = {}
        self._timeout_seconds = 300  # 5 minutes
        self._approval_mode = APPROVAL_MODE
        logger.info(f"[ApprovalService] Initialized with mode: {self._approval_mode}")

    async def auto_approve_with_haiku(
        self,
        workflow_id: str,
        artifacts: list,
        eval_score: float
    ) -> Tuple[bool, AuditReport]:
        """
        MYCELIUM mode: Use L2 Scout for auto-approval.

        MARKER_104_MYCELIUM_AUTO

        Args:
            workflow_id: ID of the workflow
            artifacts: List of artifact dicts to audit
            eval_score: Score from EvalAgent (0-1)

        Returns:
            Tuple of (approved: bool, report: AuditReport)
        """
        try:
            # Lazy import to avoid circular dependencies
            from src.services.scout_auditor import get_scout_auditor

            auditor = get_scout_auditor()
            overall, individual = auditor.audit_batch(artifacts)

            if overall.auto_approved:
                logger.info(
                    f"[MYCELIUM] Auto-approved {len(artifacts)} artifacts "
                    f"(score={overall.score:.2f}, workflow={workflow_id})"
                )
                # Create auto-approved request for audit trail
                request = ApprovalRequest(
                    id=str(uuid.uuid4()),
                    workflow_id=workflow_id,
                    artifacts=artifacts,
                    eval_score=eval_score,
                    eval_feedback=f"Auto-approved by L2 Scout (score={overall.score:.2f})",
                    status=ApprovalStatus.APPROVED,
                    decided_at=datetime.now(),
                    decision_reason="MYCELIUM auto-approval"
                )
                self._completed[request.id] = request
                return True, overall
            else:
                logger.warning(
                    f"[MYCELIUM] Flagged for review: {overall.issues} "
                    f"(workflow={workflow_id})"
                )
                return False, overall

        except ImportError as e:
            # scout_auditor module not yet implemented
            logger.warning(
                f"[MYCELIUM] scout_auditor not available, falling back to VETKA mode: {e}"
            )
            # Return a failed audit report to trigger fallback
            return False, AuditReport(
                score=0.0,
                auto_approved=False,
                issues=["scout_auditor module not available"],
                recommendations=["Implement src/services/scout_auditor.py"]
            )
        except Exception as e:
            logger.error(f"[MYCELIUM] Audit error, falling back to VETKA mode: {e}")
            return False, AuditReport(
                score=0.0,
                auto_approved=False,
                issues=[f"Audit error: {str(e)}"],
                recommendations=["Check scout_auditor configuration"]
            )

    async def request_approval(
        self,
        workflow_id: str,
        artifacts: list,
        eval_score: float,
        eval_feedback: str,
        socketio=None
    ) -> ApprovalRequest:
        """
        Request approval for artifacts.

        In VETKA mode (default): Waits for user approval via UI modal.
        In MYCELIUM mode: L2 Scout auto-approves if criteria met,
                         otherwise falls back to user approval.

        MARKER_104_APPROVAL_MODE_CHECK

        Args:
            workflow_id: ID of the workflow
            artifacts: List of artifact dicts
            eval_score: Score from EvalAgent (0-1)
            eval_feedback: Feedback from EvalAgent
            socketio: Socket.IO instance for emitting events

        Returns:
            ApprovalRequest object
        """
        # MARKER_104_APPROVAL_MODE_CHECK
        if self._approval_mode == "mycelium":
            logger.info(f"[MYCELIUM] Attempting auto-approval for workflow {workflow_id}")
            approved, report = await self.auto_approve_with_haiku(
                workflow_id, artifacts, eval_score
            )
            if approved:
                # Return immediately, no user wait needed
                return ApprovalRequest(
                    id=str(uuid.uuid4()),
                    workflow_id=workflow_id,
                    artifacts=artifacts,
                    eval_score=report.score,
                    eval_feedback="Auto-approved by L2 Scout",
                    status=ApprovalStatus.APPROVED,
                    decided_at=datetime.now(),
                    decision_reason=f"MYCELIUM auto-approval (score={report.score:.2f})"
                )
            # Fall through to VETKA mode (user approval) if flagged
            logger.info(f"[MYCELIUM] Falling back to user approval for workflow {workflow_id}")

        # VETKA mode: User approval required
        request_id = str(uuid.uuid4())

        request = ApprovalRequest(
            id=request_id,
            workflow_id=workflow_id,
            artifacts=artifacts,
            eval_score=eval_score,
            eval_feedback=eval_feedback
        )

        self._pending[request_id] = request
        self._decisions[request_id] = asyncio.Event()

        # Emit socket event for UI
        if socketio:
            await socketio.emit('approval_required', request.to_dict())
            logger.info(f"[ApprovalService] Emitted approval_required: {request_id}")

        return request

    async def wait_for_decision(
        self,
        request_id: str,
        timeout: Optional[int] = None
    ) -> Optional[ApprovalRequest]:
        """
        Wait for user decision with timeout.

        Args:
            request_id: ID of the approval request
            timeout: Seconds to wait (default: 300)

        Returns:
            ApprovalRequest with decision, or None if timeout
        """
        timeout = timeout or self._timeout_seconds
        event = self._decisions.get(request_id)

        if not event:
            logger.error(f"[ApprovalService] Unknown request: {request_id}")
            return None

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return self._pending.get(request_id)
        except asyncio.TimeoutError:
            # CRITICAL: Move to completed to prevent memory leak
            request = self._pending.get(request_id)
            if request:
                request.status = ApprovalStatus.TIMEOUT
                request.decided_at = datetime.now()
                request.decision_reason = f"Timeout after {timeout}s"

                # Set event to unblock any waiters
                if event:
                    event.set()

                # Move from pending to completed
                self._pending.pop(request_id, None)
                self._completed[request_id] = request

                logger.warning(f"[ApprovalService] Timeout: {request_id}")
            return request

    def approve(self, request_id: str, reason: str = "User approved") -> bool:
        """
        Approve an artifact.

        Args:
            request_id: ID of the approval request
            reason: Reason for approval

        Returns:
            True if approved, False if not found
        """
        request = self._pending.get(request_id)
        if not request:
            logger.error(f"[ApprovalService] Approve failed - not found: {request_id}")
            return False

        request.status = ApprovalStatus.APPROVED
        request.decided_at = datetime.now()
        request.decision_reason = reason

        # Signal waiting coroutine
        event = self._decisions.get(request_id)
        if event:
            event.set()

        # CRITICAL: Move to completed (consistent with timeout behavior)
        self._pending.pop(request_id, None)
        self._completed[request_id] = request
        self._decisions.pop(request_id, None)

        logger.info(f"[ApprovalService] Approved: {request_id}")
        return True

    def reject(self, request_id: str, reason: str = "User rejected") -> bool:
        """
        Reject an artifact.

        Args:
            request_id: ID of the approval request
            reason: Reason for rejection

        Returns:
            True if rejected, False if not found
        """
        request = self._pending.get(request_id)
        if not request:
            logger.error(f"[ApprovalService] Reject failed - not found: {request_id}")
            return False

        request.status = ApprovalStatus.REJECTED
        request.decided_at = datetime.now()
        request.decision_reason = reason

        # Signal waiting coroutine
        event = self._decisions.get(request_id)
        if event:
            event.set()

        # CRITICAL: Move to completed (consistent with approve/timeout)
        self._pending.pop(request_id, None)
        self._completed[request_id] = request
        self._decisions.pop(request_id, None)

        logger.info(f"[ApprovalService] Rejected: {request_id} - {reason}")
        return True

    def get_pending(self) -> list:
        """Get all pending approval requests."""
        return [r.to_dict() for r in self._pending.values()
                if r.status == ApprovalStatus.PENDING]

    def get_request(self, request_id: str) -> Optional[Dict]:
        """Get specific approval request (checks both pending and completed)."""
        request = self._pending.get(request_id) or self._completed.get(request_id)
        return request.to_dict() if request else None

    def cleanup_old(self, max_age_hours: int = 24):
        """Remove old completed requests to prevent memory leak."""
        now = datetime.now()
        removed_count = 0

        # 1. Clean old from _pending (shouldn't have any, but safety)
        to_remove = []
        for req_id, request in list(self._pending.items()):
            if request.status != ApprovalStatus.PENDING:
                if request.decided_at:
                    age_hours = (now - request.decided_at).total_seconds() / 3600
                    if age_hours > 1:  # Keep decided items only 1 hour in pending
                        to_remove.append(req_id)

        for req_id in to_remove:
            self._pending.pop(req_id, None)
            self._decisions.pop(req_id, None)
            removed_count += 1

        # 2. Clean old from _completed (CRITICAL for memory)
        to_remove = []
        for req_id, request in list(self._completed.items()):
            if request.decided_at:
                age_hours = (now - request.decided_at).total_seconds() / 3600
                if age_hours > max_age_hours:
                    to_remove.append(req_id)

        for req_id in to_remove:
            self._completed.pop(req_id, None)
            removed_count += 1

        if removed_count > 0:
            logger.info(f"[ApprovalService] Cleaned {removed_count} old requests. "
                       f"Remaining: {len(self._pending)} pending, {len(self._completed)} completed")

    def get_mode(self) -> str:
        """Get current approval mode (vetka or mycelium)."""
        return self._approval_mode

    def set_mode(self, mode: str) -> None:
        """
        Set approval mode at runtime.

        MARKER_104_APPROVAL_MODE

        Args:
            mode: 'vetka' or 'mycelium'
        """
        mode = mode.lower()
        if mode not in ("vetka", "mycelium"):
            logger.warning(f"[ApprovalService] Invalid mode '{mode}', keeping '{self._approval_mode}'")
            return
        old_mode = self._approval_mode
        self._approval_mode = mode
        logger.info(f"[ApprovalService] Mode changed: {old_mode} -> {mode}")


# Singleton instance
_approval_service: Optional[ApprovalService] = None


def get_approval_service() -> ApprovalService:
    """Get or create singleton ApprovalService."""
    global _approval_service
    if _approval_service is None:
        _approval_service = ApprovalService()
    return _approval_service


def get_approval_mode() -> str:
    """
    Get current approval mode.

    MARKER_104_APPROVAL_MODE

    Returns:
        'vetka' (user approval) or 'mycelium' (L2 Scout auto-approval)
    """
    return get_approval_service().get_mode()


def set_approval_mode(mode: str) -> None:
    """
    Set approval mode at runtime.

    MARKER_104_APPROVAL_MODE

    Args:
        mode: 'vetka' or 'mycelium'
    """
    get_approval_service().set_mode(mode)
