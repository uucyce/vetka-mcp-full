"""
Human-in-the-loop approval for dangerous operations.

@status: active
@phase: 96
@depends: uuid, datetime, enum
@used_by: mcp_server
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from enum import Enum


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalManager:
    """Manage approval requests for dangerous operations"""

    # Tools that require approval when dry_run=false
    DANGEROUS_TOOLS = {
        "vetka_edit_file": "File modification",
        "vetka_git_commit": "Git commit",
        "vetka_create_branch": "Create folder",
        "vetka_run_tests": "Execute code"
    }

    def __init__(self, expiry_minutes: int = 5):
        self.expiry = timedelta(minutes=expiry_minutes)
        self.pending: Dict[str, Dict] = {}  # request_id -> request data

    def needs_approval(self, tool_name: str, dry_run: bool = True) -> bool:
        """Check if tool call needs human approval"""
        if dry_run:
            return False  # Dry run never needs approval
        return tool_name in self.DANGEROUS_TOOLS

    def create_request(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        client_id: str
    ) -> Dict:
        """Create approval request, return request details"""
        request_id = str(uuid.uuid4())[:8]

        # Sanitize arguments (don't store full content)
        safe_args = {}
        for k, v in arguments.items():
            if k == "content" and isinstance(v, str) and len(v) > 200:
                safe_args[k] = v[:200] + f"...[{len(v)} chars total]"
            else:
                safe_args[k] = v

        request = {
            "id": request_id,
            "tool": tool_name,
            "description": self.DANGEROUS_TOOLS.get(tool_name, "Unknown operation"),
            "arguments": safe_args,
            "client_id": client_id,
            "status": ApprovalStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + self.expiry).isoformat()
        }

        self.pending[request_id] = request
        return request

    def approve(self, request_id: str) -> Optional[Dict]:
        """Approve a pending request"""
        if request_id not in self.pending:
            return None

        request = self.pending[request_id]

        # Check expiry
        expires = datetime.fromisoformat(request["expires_at"])
        if datetime.now() > expires:
            request["status"] = ApprovalStatus.EXPIRED.value
            return request

        request["status"] = ApprovalStatus.APPROVED.value
        request["approved_at"] = datetime.now().isoformat()
        return request

    def reject(self, request_id: str, reason: str = "") -> Optional[Dict]:
        """Reject a pending request"""
        if request_id not in self.pending:
            return None

        request = self.pending[request_id]
        request["status"] = ApprovalStatus.REJECTED.value
        request["rejected_at"] = datetime.now().isoformat()
        request["rejection_reason"] = reason
        return request

    def get_request(self, request_id: str) -> Optional[Dict]:
        """Get request by ID"""
        return self.pending.get(request_id)

    def get_pending(self) -> list:
        """Get all pending requests"""
        now = datetime.now()
        pending = []
        for req in self.pending.values():
            if req["status"] == ApprovalStatus.PENDING.value:
                expires = datetime.fromisoformat(req["expires_at"])
                if now <= expires:
                    # Add time remaining
                    req_copy = req.copy()
                    req_copy["expires_in_seconds"] = int((expires - now).total_seconds())
                    pending.append(req_copy)
                else:
                    req["status"] = ApprovalStatus.EXPIRED.value
        return pending

    def cleanup_expired(self):
        """Remove expired requests older than 1 hour"""
        now = datetime.now()
        cutoff = now - timedelta(hours=1)
        to_remove = []
        for req_id, req in self.pending.items():
            created = datetime.fromisoformat(req["created_at"])
            if created < cutoff:
                to_remove.append(req_id)
        for req_id in to_remove:
            del self.pending[req_id]
        return len(to_remove)


# Global approval manager
approval_manager = ApprovalManager()
