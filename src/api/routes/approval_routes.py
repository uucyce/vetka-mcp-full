# === PHASE 55: APPROVAL API ROUTES ===
"""
REST API endpoints for approval workflow.

Provides endpoints for listing, approving, and rejecting workflow artifacts.

@status: active
@phase: 96
@depends: fastapi, approval_service
@used_by: main.py router registration
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import os
import logging

from src.services.approval_service import get_approval_service, ApprovalStatus

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


async def verify_approval_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> bool:
    """Verify API token for approval endpoints."""
    # В dev режиме без токена — разрешаем (для тестирования)
    if os.getenv('VETKA_ENV', 'development') == 'development':
        if not credentials:
            logger.warning("[Auth] No token in dev mode, allowing")
            return True

    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = credentials.credentials
    valid_token = os.getenv('APPROVAL_TOKEN')

    if not valid_token:
        logger.error("[Auth] APPROVAL_TOKEN not set in environment!")
        raise HTTPException(status_code=500, detail="Server misconfigured")

    if token != valid_token:
        logger.warning(f"[Auth] Invalid token attempt: {token[:10]}...")
        raise HTTPException(status_code=401, detail="Invalid token")

    return True


router = APIRouter(prefix="/api/approvals", tags=["approvals"])


class ApproveRequest(BaseModel):
    reason: Optional[str] = "User approved"


class RejectRequest(BaseModel):
    reason: str = "User rejected"


@router.get("/pending", dependencies=[Depends(verify_approval_token)])
async def get_pending_approvals():
    """Get all pending approval requests (requires valid token in production)."""
    service = get_approval_service()
    return {
        "success": True,
        "pending": service.get_pending(),
        "count": len(service.get_pending())
    }


@router.get("/{request_id}")
async def get_approval(request_id: str):
    """Get specific approval request."""
    service = get_approval_service()
    request = service.get_request(request_id)

    if not request:
        raise HTTPException(status_code=404, detail="Approval request not found")

    return {
        "success": True,
        "request": request
    }


@router.post("/{request_id}/approve", dependencies=[Depends(verify_approval_token)])
async def approve_request(request_id: str, body: ApproveRequest):
    """Approve workflow artifacts (requires valid token in production)."""
    service = get_approval_service()

    if service.approve(request_id, body.reason):
        return {
            "success": True,
            "message": f"Approved: {request_id}",
            "request": service.get_request(request_id)
        }
    else:
        raise HTTPException(status_code=404, detail="Approval request not found or already decided")


@router.post("/{request_id}/reject", dependencies=[Depends(verify_approval_token)])
async def reject_request(request_id: str, body: RejectRequest):
    """Reject workflow artifacts (requires valid token in production)."""
    service = get_approval_service()

    if service.reject(request_id, body.reason):
        return {
            "success": True,
            "message": f"Rejected: {request_id}",
            "request": service.get_request(request_id)
        }
    else:
        raise HTTPException(status_code=404, detail="Approval request not found or already decided")


@router.delete("/cleanup")
async def cleanup_old_requests(max_age_hours: int = 24):
    """Remove old completed requests."""
    service = get_approval_service()
    service.cleanup_old(max_age_hours)
    return {
        "success": True,
        "message": f"Cleaned up requests older than {max_age_hours} hours"
    }
