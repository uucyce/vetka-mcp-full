# === PHASE 55: SERVICES ===
"""
Service layer for VETKA - business logic services.

MARKER_104_SERVICES_INIT

@status: active
@phase: 104.4
@depends: approval_service, file_lock_manager, scout_auditor
@used_by: src.api.handlers, src.orchestration
"""

from src.services.approval_service import (
    get_approval_service,
    ApprovalService,
    get_approval_mode,
    set_approval_mode,
    AuditReport,
    APPROVAL_MODE,
)
from src.services.file_lock_manager import get_file_lock_manager, FileLockManager
from src.services.scout_auditor import (
    get_scout_auditor,
    reset_scout_auditor,
    L2ScoutAuditor,
    ScoutAuditReport,
    AuditResult,
    AuditIssue,
    AuditSeverity,
)

__all__ = [
    # Approval service (VETKA + MYCELIUM modes)
    'get_approval_service',
    'ApprovalService',
    'get_approval_mode',
    'set_approval_mode',
    'AuditReport',
    'APPROVAL_MODE',
    # File lock manager
    'get_file_lock_manager',
    'FileLockManager',
    # L2 Haiku Auditor (MYCELIUM auto-approval)
    'get_scout_auditor',
    'reset_scout_auditor',
    'L2ScoutAuditor',
    'ScoutAuditReport',
    'AuditResult',
    'AuditIssue',
    'AuditSeverity',
]
