# === PHASE 55: SERVICES ===
"""
Service layer for VETKA - business logic services.

@status: active
@phase: 96
@depends: approval_service, file_lock_manager
@used_by: src.api.handlers, src.orchestration
"""

from src.services.approval_service import get_approval_service, ApprovalService
from src.services.file_lock_manager import get_file_lock_manager, FileLockManager

__all__ = [
    'get_approval_service',
    'ApprovalService',
    'get_file_lock_manager',
    'FileLockManager'
]
