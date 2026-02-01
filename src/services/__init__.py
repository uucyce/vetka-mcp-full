# === PHASE 55: SERVICES ===
"""
Service layer for VETKA - business logic services.

MARKER_104_SERVICES_INIT

@status: active
@phase: 105
@depends: approval_service, file_lock_manager, scout_auditor, persistence_service, mycelium_auditor
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
# MARKER_104_CHAT_SAVE: Persistence service for chat event storage
from src.services.persistence_service import (
    save_chat_history,
    load_chat_history,
    delete_chat_history,
    REDIS_AVAILABLE,
)
# MARKER_104_ARTIFACT_DISK: Disk artifact persistence service
from src.services.disk_artifact_service import (
    create_disk_artifact,
    sanitize_artifact_name,
    get_artifact_path,
    list_artifacts,
    read_artifact,
    delete_artifact,
    ARTIFACTS_DIR,
    EXT_MAP,
    MIN_CONTENT_LENGTH,
)
# MARKER_MYCELIUM_V2_ENFORCEMENT: MYCELIUM v2.0 enforcement service
# MARKER_MYCELIUM_MCP_INTEGRATION: VETKA Tools client for MCP-style calls
from src.services.mycelium_auditor import (
    get_mycelium_auditor,
    MyceliumAuditor,
    MyceliumTaskType,
    mycelium_research,
    MyceliumOutput,
    TokenBudget,
    # MCP Integration
    VETKAToolsClient,
    get_vetka_tools_client,
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
    # Persistence service (MARKER_104_CHAT_SAVE)
    'save_chat_history',
    'load_chat_history',
    'delete_chat_history',
    'REDIS_AVAILABLE',
    # MARKER_104_ARTIFACT_DISK: Disk artifact service
    'create_disk_artifact',
    'sanitize_artifact_name',
    'get_artifact_path',
    'list_artifacts',
    'read_artifact',
    'delete_artifact',
    'ARTIFACTS_DIR',
    'EXT_MAP',
    'MIN_CONTENT_LENGTH',
    # MARKER_MYCELIUM_V2_ENFORCEMENT: MYCELIUM v2.0 enforcement service
    'get_mycelium_auditor',
    'MyceliumAuditor',
    'MyceliumTaskType',
    'mycelium_research',
    'MyceliumOutput',
    'TokenBudget',
    # MARKER_MYCELIUM_MCP_INTEGRATION: VETKA Tools client
    'VETKAToolsClient',
    'get_vetka_tools_client',
]
