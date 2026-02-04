"""VETKA MCP Tools Package.

This package contains all MCP (Model Context Protocol) tools that can be invoked
by any AI agent (Claude, GPT, Gemini, etc.) over WebSocket or REST API.

Available tools (21+):

Read-Only (safe):
- vetka_search: Search files by name/content
- vetka_search_knowledge: Semantic search with embeddings
- vetka_get_tree: Get folder/file hierarchy
- vetka_get_node: Get details about a specific node
- vetka_list_files: List directory contents
- vetka_read_file: Read file content
- vetka_git_status: Get git status
- vetka_camera_focus: Control 3D camera to show user specific nodes
- vetka_workflow_status: Get status of a workflow execution

Session Tools (Phase 55.1):
- vetka_session_init: Initialize session with fat context and ELISION compression
- vetka_session_status: Get current session status

Context Tools (Phase 109.1):
- vetka_get_pinned_files: Get pinned files with metadata for dynamic context
- vetka_get_viewport_detail: Get current viewport state (camera, focus, visible nodes)
- vetka_get_context_dag: Assemble ~500 token context digest from ALL sources with ELISION compression

Write Operations (require approval, dry_run default):
- vetka_create_branch: Create a new folder
- vetka_edit_file: Edit or create file
- vetka_git_commit: Create git commit
- vetka_run_tests: Run pytest tests

Workflow Tools (Phase 55.1):
- vetka_execute_workflow: Execute full workflow (PM -> Architect -> Dev -> QA)
- vetka_workflow_status: Get workflow execution status

ARC Tools (Phase 99.3):
- vetka_arc_gap: Analyze prompt for conceptual gaps using ARC methodology
- vetka_arc_concepts: Extract key concepts from text (fast, no LLM)

Artifact Tools (Phase 108.4):
- vetka_edit_artifact: Edit artifact content and submit for approval
- vetka_approve_artifact: Approve pending artifact
- vetka_reject_artifact: Reject artifact with feedback
- vetka_list_artifacts: List artifacts by status

Intake Tools:
- vetka_intake_url: Process URL content (YouTube, web)
- vetka_list_intakes: List processed content
- vetka_get_intake: Get intake content

@status: active
@phase: 108.4
@depends: base_tool, search_tool, tree_tool, branch_tool, list_files_tool, read_file_tool, edit_file_tool, run_tests_tool, git_tool, search_knowledge_tool, camera_tool, workflow_tools, session_tools, marker_tool, arc_gap_tool, artifact_tools
@used_by: src/mcp/vetka_mcp_bridge.py, src/mcp/mcp_server.py

FIX_98.5: Added marker_tool for @status/@phase marker management.
FIX_99.3: Added arc_gap_tool for ARC-based conceptual gap detection.
MARKER_108_4_ARTIFACT_TOOLS: Added artifact_tools for Dev/QA approval workflow.
"""

from .base_tool import BaseMCPTool
from .search_tool import SearchTool
from .tree_tool import GetTreeTool, GetNodeTool
from .branch_tool import CreateBranchTool
from .list_files_tool import ListFilesTool
from .read_file_tool import ReadFileTool
from .edit_file_tool import EditFileTool
from .run_tests_tool import RunTestsTool
from .git_tool import GitStatusTool, GitCommitTool
from .search_knowledge_tool import SearchKnowledgeTool
from .camera_tool import CameraControlTool
from .workflow_tools import (
    ExecuteWorkflowTool,
    WorkflowStatusTool,
    vetka_execute_workflow,
    vetka_workflow_status,
    register_workflow_tools,
)
from .session_tools import (
    SessionInitTool,
    SessionStatusTool,
    vetka_session_init,
    vetka_session_status,
    register_session_tools,
)
# MARKER_109_2_PINNED_TOOL: Pinned files context tool
from .pinned_files_tool import (
    PinnedFilesTool,
    vetka_get_pinned_files,
    register_pinned_files_tool,
)
# FIX_98.5: Marker tools for @status/@phase management
from .marker_tool import (
    MarkerTool,
    MarkerVerifyTool,
    marker_tool,
    marker_verify_tool,
    register_marker_tools,
)
# FIX_99.3: ARC Gap Detection tools
from .arc_gap_tool import (
    ARCGapTool,
    ARCConceptsTool,
    get_arc_gap_tool,
    get_arc_concepts_tool,
    vetka_arc_gap,
    vetka_arc_concepts,
    register_arc_tools,
)
# MARKER_108_4_ARTIFACT_TOOLS: Artifact management tools
from .artifact_tools import (
    EditArtifactTool,
    ApproveArtifactTool,
    RejectArtifactTool,
    ListArtifactsTool,
)
# MARKER_109_2_VIEWPORT_TOOL: Viewport detail tool for Phase 109.1
from .viewport_tool import (
    ViewportDetailTool,
    vetka_get_viewport_detail,
    register_viewport_tool,
)
# MARKER_109_3_CONTEXT_DAG: Context DAG tool for dynamic context injection
from .context_dag_tool import (
    ContextDAGTool,
    register_context_dag_tool,
)

__all__ = [
    'BaseMCPTool',
    'SearchTool',
    'GetTreeTool',
    'GetNodeTool',
    'CreateBranchTool',
    'ListFilesTool',
    'ReadFileTool',
    'EditFileTool',
    'RunTestsTool',
    'GitStatusTool',
    'GitCommitTool',
    'SearchKnowledgeTool',
    'CameraControlTool',
    'ExecuteWorkflowTool',
    'WorkflowStatusTool',
    'vetka_execute_workflow',
    'vetka_workflow_status',
    'register_workflow_tools',
    # Session Tools (Phase 55.1)
    'SessionInitTool',
    'SessionStatusTool',
    'vetka_session_init',
    'vetka_session_status',
    'register_session_tools',
    # Context Tools (Phase 109.1)
    'PinnedFilesTool',
    'vetka_get_pinned_files',
    'register_pinned_files_tool',
    # Marker Tools (FIX_98.5)
    'MarkerTool',
    'MarkerVerifyTool',
    'marker_tool',
    'marker_verify_tool',
    'register_marker_tools',
    # ARC Gap Tools (FIX_99.3)
    'ARCGapTool',
    'ARCConceptsTool',
    'get_arc_gap_tool',
    'get_arc_concepts_tool',
    'vetka_arc_gap',
    'vetka_arc_concepts',
    'register_arc_tools',
    # Artifact Tools (MARKER_108_4_ARTIFACT_TOOLS)
    'EditArtifactTool',
    'ApproveArtifactTool',
    'RejectArtifactTool',
    'ListArtifactsTool',
    # Viewport Tool (MARKER_109_2_VIEWPORT_TOOL)
    'ViewportDetailTool',
    'vetka_get_viewport_detail',
    'register_viewport_tool',
    # Context DAG Tool (MARKER_109_3_CONTEXT_DAG)
    'ContextDAGTool',
    'register_context_dag_tool',
]
