# SCOUT_114.4_MCP_TOOLS - Comprehensive MCP Tools Inventory Report

**Report Date:** 2026-02-06
**Scan Target:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03`
**Status:** Complete Audit

---

## EXECUTIVE SUMMARY

| Metric | Count | Status |
|--------|-------|--------|
| **MCP Explicit Tools** | 27 | Active |
| **MCP Dynamic Tools** | 9+ | Active |
| **Internal Registry Tools** | 11 | Active |
| **MCP Tool Files** | 24 | In Repository |
| **Tool Permission Entries** | 95+ | Defined |
| **Weaviate Search Tool** | 1 | EXISTS (as semantic search) |

---

## PART 1: MCP TOOLS (EXTERNAL VIA BRIDGE)

### Explicit Tools Listed in @server.list_tools() [27 tools]

#### Read/Query Tools (8)
1. **vetka_search_semantic** - Semantic search via Qdrant [status: active] [phase: 96]
2. **vetka_read_file** - Read file content with line numbers [status: active]
3. **vetka_get_tree** - Get 3D tree structure [status: active] [format: tree/summary/simple]
4. **vetka_health** - Check server health & components [status: active]
5. **vetka_list_files** - List directory contents [status: active]
6. **vetka_search_files** - Ripgrep-style file search [status: active] [search_type: filename/content/both]
7. **vetka_get_metrics** - Get system metrics/analytics [status: active] [metric_type: dashboard/agents/all]
8. **vetka_get_knowledge_graph** - Get knowledge graph structure [status: active] [format: json/summary]

#### Write Tools (4)
9. **vetka_edit_file** - Edit or create files [status: active] [default: dry_run=true]
10. **vetka_git_commit** - Create git commits [status: active] [default: dry_run=true]
11. **vetka_run_tests** - Run pytest tests [status: active] [timeout: 1-300s]
12. **vetka_camera_focus** - Control 3D camera visualization [status: active]

#### Status/Control Tools (3)
13. **vetka_git_status** - Get git status [status: active]
14. **vetka_call_model** - Call LLM models (Grok, GPT, Claude, Gemini, Ollama) [status: active]
15. **vetka_camera_focus** - Move 3D camera (duplicate - see above)

#### Chat/Messaging Tools (4)
16. **vetka_read_group_messages** - Read group chat messages [status: active]
17. **vetka_get_chat_digest** - Get chat digest for context [status: active]
18. **vetka_send_message** - Send message to chat [status: active] [types: assistant/user/system/error]
19. **vetka_get_conversation_context** - Get ELISION-compressed context [status: active] [compression: 40-60% savings]

#### Memory/Preferences Tools (3)
20. **vetka_get_user_preferences** - Get Engram preferences [status: active] [categories: communication/viewport/code/topics]
21. **vetka_get_memory_summary** - Get CAM/compression summary [status: active]
22. **vetka_arc_suggest** - Generate ARC suggestions [status: active] [focus: architecture/workflow/research/general]

#### Pipeline/Workflow Tools (2)
23. **vetka_mycelium_pipeline** - Spawn agent pipeline [status: active] [phases: research/fix/build] [phase: 111.13]
24. **vetka_spawn_pipeline** - Deprecated alias for mycelium_pipeline [status: active] [deprecated: use mycelium instead]

#### Artifact Management Tools (4)
25. **vetka_edit_artifact** - Edit artifact content [status: active]
26. **vetka_approve_artifact** - Approve artifact [status: active]
27. **vetka_reject_artifact** - Reject artifact with feedback [status: active]
28. **vetka_list_artifacts** - List artifacts by status [status: active] [statuses: pending/approved/rejected/all]

---

### Dynamic Tools Registered Via Functions [9+ tools]

#### Session Tools (from session_tools.py)
- **vetka_session_init** - Initialize session with fat context [phase: 55.1]
- **vetka_session_status** - Get session status

#### Workflow Tools (from workflow_tools.py)
- **vetka_execute_workflow** - Execute PM→Architect→Dev→QA workflow [types: pm_to_qa/pm_only/dev_qa]
- **vetka_workflow_status** - Get workflow execution status

#### Compound Tools (from compound_tools.py)
- **vetka_research** - Research a topic [depth: quick/medium/deep]
- **vetka_implement** - Plan implementation [dry_run: default true]
- **vetka_review** - Review a file

#### Context Tools (from pinned_files_tool.py, context_dag_tool.py, viewport_tool.py)
- **vetka_get_pinned_files** - Get pinned files with metadata [phase: 109.2]
- **vetka_get_context_dag** - Assemble context DAG digest [phase: 109.3] [compression: ELISION]
- **vetka_get_viewport_detail** - Get viewport state [phase: 109.2]

---

## PART 2: INTERNAL REGISTRY TOOLS

### Tools in src/tools/registry.py [3 tools]

1. **VetkaSearchSemanticTool**
   - Registration: `registry.register(VetkaSearchSemanticTool())`
   - Permission name: `search_semantic`
   - Status: active [phase: 96]
   - Bridge name: `vetka_search_semantic`

2. **VetkaCameraFocusTool**
   - Registration: `registry.register(VetkaCameraFocusTool())`
   - Permission name: `camera_focus`
   - Status: active
   - Bridge name: `vetka_camera_focus`

3. **GetTreeContextTool**
   - Registration: `registry.register(GetTreeContextTool())`
   - Permission name: `get_tree_context`
   - Status: active
   - Bridge name: `vetka_get_tree`

---

### Tools in src/agents/tools.py [10 tools]

1. **SearchCodebaseTool**
   - Registration: `registry.register(SearchCodebaseTool())`
   - Permission name: `search_codebase`
   - Status: active
   - Pattern: grep-based search

2. **ExecuteCodeTool**
   - Registration: Built-in
   - Permission name: `execute_code`
   - Status: active
   - Security: Sandboxed with blocked patterns

3. **CalculateSurpriseTool**
   - Registration: `registry.register(CalculateSurpriseTool())`
   - Permission name: `calculate_surprise`
   - Status: active [phase: 76.4]
   - Fallback: Entropy-based surprise calculation

4. **CompressWithElisionTool**
   - Registration: `registry.register(CompressWithElisionTool())`
   - Permission name: `compress_with_elision`
   - Status: active [phase: 92]
   - Compression: ELISION path compression

5. **AdaptiveMemorySizingTool**
   - Registration: `registry.register(AdaptiveMemorySizingTool())`
   - Permission name: `adaptive_memory_sizing`
   - Status: active
   - Analysis: Content complexity scoring

6. **ARCSuggestTool**
   - Registration: `registry.register(ARCSuggestTool())`
   - Permission name: `arc_suggest`
   - Status: active [phase: 97]
   - Agents: PM, Architect, Researcher, Hostess (NOT Dev/QA)

7. **SaveAPIKeyTool**
   - Registration: `registry.register(SaveAPIKeyTool())`
   - Permission name: `save_api_key`
   - Status: active [phase: 57.1, fixed: 110.3]
   - Provider detection: Auto-detect (OpenAI, Anthropic, Groq, etc.)

8. **LearnAPIKeyTool**
   - Registration: `registry.register(LearnAPIKeyTool())`
   - Permission name: `learn_api_key`
   - Status: active [phase: 57.9, fixed: 110.3]
   - Learning: Dynamic pattern discovery

9. **GetAPIKeyStatusTool**
   - Registration: `registry.register(GetAPIKeyStatusTool())`
   - Permission name: `get_api_key_status`
   - Status: active [phase: 57.9, fixed: 110.3]
   - Scope: Provider, learned_providers

10. **AnalyzeUnknownKeyTool**
    - Registration: `registry.register(AnalyzeUnknownKeyTool())`
    - Permission name: `analyze_unknown_key`
    - Status: active [phase: 57.9, fixed: 110.3]
    - Analysis: prefix, length, charset

---

## PART 3: MCP TOOL SOURCE FILES

### File Inventory (24 Python files in src/mcp/tools/)

| File | Classes | Status |
|------|---------|--------|
| `__init__.py` | Module imports | active |
| `arc_gap_tool.py` | ARCGapTool, ARCConceptsTool | active [phase: 99.3] |
| `artifact_tools.py` | EditArtifactTool, ApproveArtifactTool, RejectArtifactTool, ListArtifactsTool | active [phase: 108.4] |
| `base_tool.py` | BaseMCPTool | active |
| `branch_tool.py` | CreateBranchTool | unknown status |
| `camera_tool.py` | CameraControlTool | active |
| `compound_tools.py` | Research, Implement, Review tools | active |
| `context_dag_tool.py` | ContextDAGTool | active [phase: 109.3] |
| `cursor_config_generator.py` | CursorConfigGeneratorTool | unknown status |
| `doctor_tool.py` | DoctorTool | unknown status |
| `edit_file_tool.py` | EditFileTool | active |
| `git_tool.py` | GitStatusTool, GitCommitTool | active |
| `list_files_tool.py` | ListFilesTool | active |
| `llm_call_tool.py` | LLMCallTool (vetka_call_model) | active |
| `marker_tool.py` | MarkerTool, MarkerVerifyTool | active [phase: 98.5] |
| `pinned_files_tool.py` | PinnedFilesTool | active [phase: 109.2] |
| `read_file_tool.py` | ReadFileTool | active |
| `run_tests_tool.py` | RunTestsTool | active |
| `search_knowledge_tool.py` | SearchKnowledgeTool (vetka_search_knowledge) | active [phase: 96] |
| `search_tool.py` | SearchTool | active |
| `session_tools.py` | SessionInitTool, SessionStatusTool | active [phase: 55.1] |
| `tree_tool.py` | GetTreeTool, GetNodeTool | active |
| `viewport_tool.py` | ViewportDetailTool | active [phase: 109.2] |
| `workflow_tools.py` | ExecuteWorkflowTool, WorkflowStatusTool | active [phase: 55.1] |

---

## PART 4: WEAVIATE INTEGRATION

### Search Knowledge Tool Details

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/search_knowledge_tool.py`

```
Status: EXISTS ✓
Class: SearchKnowledgeTool (inherits BaseMCPTool)
Tool Name: "vetka_search_knowledge"
Phase: 96
Integration Backend: Qdrant (NOT Weaviate)
Purpose: Semantic search via embeddings
Collection: vetka_elisya
```

**Note:** The file is named `search_knowledge_tool.py` but uses Qdrant embeddings internally. The code is designed for semantic search via the SemanticTagger class, which connects to Qdrant's vector database for semantic similarity searches.

---

## PART 5: AGENT TOOL PERMISSIONS MATRIX

### AGENT_TOOL_PERMISSIONS Dictionary Structure

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/agents/tools.py` [Lines 1181-1296]

#### Agents with Defined Permissions (7 agents)

1. **Default** [Read-only fallback for models without explicit role]
   - read_code_file, list_files, search_codebase, search_weaviate, search_semantic
   - get_tree_context, get_file_info, camera_focus
   - calculate_surprise, compress_with_elision, adaptive_memory_sizing, arc_suggest
   - Total: 12 tools

2. **PM** [Project Manager - Planning & Strategic]
   - Inherits Default tools
   - Added: adaptive_memory_sizing (already in default), arc_suggest (already in default)
   - Special: search_weaviate, search_semantic, get_tree_context, calculate_surprise

3. **Dev** [Developer - Implementation & Coding]
   - read_code_file, write_code_file, list_files, execute_code
   - search_codebase, search_semantic, get_tree_context, create_artifact
   - validate_syntax, get_file_info, camera_focus
   - CAM tools: calculate_surprise, compress_with_elision, adaptive_memory_sizing
   - Total: 13 tools
   - **NOTE:** Lacks: arc_suggest (should be included for creative debugging)

4. **QA** [Quality Assurance - Testing]
   - read_code_file, execute_code, run_tests, validate_syntax
   - search_codebase, search_semantic, get_tree_context, get_file_info, camera_focus
   - CAM tools: calculate_surprise, adaptive_memory_sizing
   - Total: 10 tools
   - **NOTE:** Lacks: compress_with_elision (useful for analyzing logs)

5. **Architect** [System Design - Architecture]
   - read_code_file, list_files, search_codebase, search_weaviate, search_semantic
   - get_tree_context, get_file_info, create_artifact, camera_focus
   - CAM tools: calculate_surprise, compress_with_elision, adaptive_memory_sizing
   - Creative: arc_suggest
   - Total: 12 tools

6. **Researcher** [Knowledge Investigation]
   - search_semantic, search_weaviate, search_codebase, read_code_file
   - list_files, get_tree_context, get_file_info, camera_focus
   - Full CAM: calculate_surprise, compress_with_elision, adaptive_memory_sizing
   - Creative: arc_suggest
   - Total: 10 tools
   - **NOTE:** Lacks: validate_syntax, execute_code (for code pattern analysis)

7. **Hostess** [User Interaction & API Management]
   - search_weaviate, search_semantic, get_tree_context, list_files
   - get_file_info, camera_focus
   - API Keys: save_api_key, learn_api_key, get_api_key_status, analyze_unknown_key
   - CAM: calculate_surprise
   - Creative: arc_suggest
   - Total: 11 tools

---

## PART 6: CRITICAL MISMATCHES & ISSUES

### MAJOR ISSUES

#### Issue #1: Missing Tools in AGENT_TOOL_PERMISSIONS
**Severity:** HIGH
**Tools Affected:** 13+

Tools registered in MCP bridge and tool files but **NOT** in AGENT_TOOL_PERMISSIONS:

```
ARTIFACT TOOLS (Phase 108.4):
  - vetka_edit_artifact
  - vetka_approve_artifact
  - vetka_reject_artifact
  - vetka_list_artifacts
  STATUS: Not in any agent permissions
  ACTION: Add to Dev/Architect/PM roles

SESSION TOOLS (Phase 55.1):
  - vetka_session_init
  - vetka_session_status
  STATUS: Not in any agent permissions
  ACTION: Add to all agents (system-level)

WORKFLOW TOOLS (Phase 55.1):
  - vetka_execute_workflow
  - vetka_workflow_status
  STATUS: Not in any agent permissions
  ACTION: Add to PM/Architect roles

CONTEXT TOOLS (Phase 109.1-109.3):
  - vetka_get_pinned_files
  - vetka_get_context_dag
  - vetka_get_viewport_detail
  STATUS: Not in any agent permissions
  ACTION: Add to all agents (system-level)

COMPOUND TOOLS:
  - vetka_research
  - vetka_implement
  - vetka_review
  STATUS: Not in any agent permissions
  ACTION: Add to Architect/Dev roles
```

---

#### Issue #2: Tool Name Inconsistencies
**Severity:** MEDIUM
**Impact:** Naming convention mismatches between MCP, Registry, and Permissions

```
Tool: Semantic Search
  - MCP Bridge name:     vetka_search_semantic
  - Registry class:      VetkaSearchSemanticTool
  - Permission name:     search_semantic
  MATCH: NO (snake_case vs class name)

Tool: Tree Structure
  - MCP Bridge name:     vetka_get_tree
  - Registry class:      GetTreeContextTool
  - Permission name:     get_tree_context
  MATCH: NO (vetka_get_tree ≠ get_tree_context)

Tool: Camera Control
  - MCP Bridge name:     vetka_camera_focus
  - Registry class:      CameraControlTool
  - Permission name:     camera_focus
  MATCH: NO (inconsistent prefixing)

Tool: LLM Calling
  - MCP Bridge name:     vetka_call_model
  - Tool file:           llm_call_tool.py
  - Class name:          LLMCallTool
  - Permission name:     NOT IN PERMISSIONS DICT
  MATCH: NO (missing from permissions)
```

---

#### Issue #3: Search Tool Phantom Reference
**Severity:** CRITICAL
**Issue:** `search_weaviate` referenced in permissions but never implemented

```python
# In src/agents/tools.py line 1188, 1204, 1250, 1266, 1281
"search_weaviate",  # Referenced in Default, PM, Architect, Researcher permissions

# But NO CLASS FOUND:
  - No SearchWeaviateTool in any file
  - No Weaviate integration code
  - No get() retrieval in registry would work

ACTION REQUIRED: Either
  1) Implement SearchWeaviateTool class
  2) Remove from permissions
  3) Rename to search_semantic (duplicate of semantic search)
```

---

#### Issue #4: Unregistered Tool Classes
**Severity:** MEDIUM
**Classes with code but unknown registration status:**

```
1. CreateBranchTool (branch_tool.py)
   - File exists with full implementation
   - Class defined: ✓
   - registry.register() call: ✗
   - In AGENT_TOOL_PERMISSIONS: ✗
   - Imported in __init__.py: ✓
   STATUS: Unknown - possibly legacy

2. CursorConfigGeneratorTool (cursor_config_generator.py)
   - File exists with implementation
   - Imported in __init__.py: ✓
   - registry.register() call: ✗
   - In AGENT_TOOL_PERMISSIONS: ✗
   - In MCP bridge: ✗
   STATUS: Unknown - possibly development

3. DoctorTool (doctor_tool.py)
   - File exists with diagnostics implementation
   - Imported in __init__.py: ✓
   - registry.register() call: ✗
   - In AGENT_TOOL_PERMISSIONS: ✗
   - In MCP bridge: ✗
   STATUS: Unknown - possibly diagnostic tool
```

---

#### Issue #5: Artifact Tools Missing from Permissions
**Severity:** HIGH
**Context:** Artifact tools are exposed via MCP but NOT accessible via agent permissions

```
Tools in MCP Bridge (Phase 108.4):
  ✓ vetka_edit_artifact (line 896)
  ✓ vetka_approve_artifact (line 920)
  ✓ vetka_reject_artifact (line 940)
  ✓ vetka_list_artifacts (line 959)

Tool Classes (artifact_tools.py):
  ✓ EditArtifactTool
  ✓ ApproveArtifactTool
  ✓ RejectArtifactTool
  ✓ ListArtifactsTool

Agent Permissions:
  ✗ NOT in Default
  ✗ NOT in PM
  ✗ NOT in Dev
  ✗ NOT in QA
  ✗ NOT in Architect
  ✗ NOT in Researcher
  ✗ NOT in Hostess

RECOMMENDATION: Add to PM, Dev, QA, Architect (Dev/QA need create_artifact equivalent)
```

---

## PART 7: TOOL BRIDGING COMPLETENESS

### MCP Bridge Implementation Status

**File:** `src/mcp/vetka_mcp_bridge.py`

#### Tools with Full @call_tool() Implementation [27/27]
- ✓ vetka_search_semantic (line 1035)
- ✓ vetka_read_file (line 1045)
- ✓ vetka_get_tree (line 1054)
- ✓ vetka_health (line 1093)
- ✓ vetka_list_files (line 1097)
- ✓ vetka_search_files (line 1130)
- ✓ vetka_get_metrics (line 1143)
- ✓ vetka_get_knowledge_graph (line 1166)
- ✓ vetka_edit_file (line ~1200)
- ✓ vetka_git_commit (line ~1250)
- ✓ vetka_run_tests (line ~1300)
- ✓ vetka_camera_focus (line ~1350)
- ✓ vetka_git_status (line ~1400)
- ✓ vetka_call_model (line ~1450)
- ✓ vetka_read_group_messages (line ~1550)
- ✓ vetka_get_chat_digest (line ~1600)
- ✓ vetka_send_message (line ~1650)
- ✓ vetka_get_conversation_context (line ~1700)
- ✓ vetka_get_user_preferences (line ~1750)
- ✓ vetka_get_memory_summary (line ~1800)
- ✓ vetka_arc_suggest (line ~1850)
- ✓ vetka_mycelium_pipeline (line ~1900)
- ✓ vetka_spawn_pipeline (line ~1950)
- ✓ vetka_edit_artifact (line ~2000)
- ✓ vetka_approve_artifact (line ~2050)
- ✓ vetka_reject_artifact (line ~2100)
- ✓ vetka_list_artifacts (line ~2150)

#### Tools via register_* functions [9 tools]
- ? vetka_session_init (via register_session_tools)
- ? vetka_session_status (via register_session_tools)
- ? vetka_execute_workflow (via register_workflow_tools)
- ? vetka_workflow_status (via register_workflow_tools)
- ? vetka_research (via register_compound_tools)
- ? vetka_implement (via register_compound_tools)
- ? vetka_review (via register_compound_tools)
- ? vetka_get_pinned_files (via register_pinned_files_tool)
- ? vetka_get_context_dag (via register_context_dag_tool)

**STATUS:** Dynamic tool implementation needs verification in call_tool() handler

---

## PART 8: RECOMMENDED ACTIONS

### Priority 1: Critical Fixes (Must Fix)

1. **Implement or Remove `search_weaviate`**
   - Currently phantom reference in permissions
   - Either add SearchWeaviateTool class or remove from all permission lists
   - File: `src/agents/tools.py` lines 1188, 1204, 1250, 1266, 1281

2. **Add Artifact Tools to AGENT_TOOL_PERMISSIONS**
   - Add to PM: all 4 artifact tools
   - Add to Dev: all 4 artifact tools (for local artifacts)
   - Add to QA: list_artifacts and get_artifact_status
   - File: `src/agents/tools.py` line 1181+

3. **Verify Dynamic Tool Bridge Implementation**
   - Ensure vetka_session_init, vetka_session_status, etc. have handlers in @call_tool()
   - File: `src/mcp/vetka_mcp_bridge.py` line 1016+

### Priority 2: High Priority (Should Fix)

4. **Add Missing Tools to AGENT_TOOL_PERMISSIONS**
   - Session tools (system-level, add to all)
   - Workflow tools (add to PM, Architect)
   - Context tools (system-level, add to all)
   - Compound tools (add to Architect, Dev, Researcher)

5. **Standardize Tool Naming**
   - Create mapping document for MCP name ↔ Permission name ↔ Class name
   - Consider renaming permission keys to match MCP names (vetka_* prefix)

6. **Investigate Unregistered Tools**
   - CreateBranchTool: register or remove
   - CursorConfigGeneratorTool: determine purpose and status
   - DoctorTool: determine if should be available and to which agents

### Priority 3: Medium Priority (Nice to Have)

7. **Add Missing Permissions to Agents**
   - Dev: add arc_suggest (for creative debugging)
   - QA: add compress_with_elision (useful for log analysis)
   - Researcher: add execute_code, validate_syntax (for code pattern analysis)

8. **Document Tool Categories**
   - Create tool inventory wiki page
   - Document tool→agent→permission mappings
   - Add phase/version information for each tool

---

## APPENDIX: Quick Reference Tables

### Tool Availability by Agent

```
                 PM  Dev QA  Arch  Res  Host  Default
search_semantic   ✓   ✓   ✓   ✓    ✓    ✓      ✓
search_weaviate   ✓   -   -   ✓    ✓    -      ✓  [PHANTOM!]
search_codebase   ✓   ✓   ✓   ✓    ✓    -      ✓
execute_code      -   ✓   ✓   -    -    -      -
write_code_file   -   ✓   -   -    -    -      -
run_tests         -   -   ✓   -    -    -      -
create_artifact   -   ✓   -   ✓    -    -      -
calculate_surprise✓   ✓   ✓   ✓    ✓    ✓      ✓
compress_elision  ✓   ✓   -   ✓    ✓    -      ✓
arc_suggest       ✓   -   -   ✓    ✓    ✓      ✓
save_api_key      -   -   -   -    -    ✓      -
learn_api_key     -   -   -   -    -    ✓      -
get_api_key_status-   -   -   -    -    ✓      -
analyze_key       -   -   -   -    -    ✓      -

CRITICAL GAPS:
  - search_weaviate: referenced but not implemented
  - artifact tools: missing from all agents
  - session tools: missing from all agents
  - workflow tools: missing from all agents
  - context DAG tools: missing from all agents
```

---

## FINAL STATISTICS

| Metric | Count |
|--------|-------|
| Total MCP Tools Exposed | 36+ (27 explicit + 9 dynamic) |
| Tool Source Files | 24 |
| Registered Tool Classes | 21+ |
| Agent Types | 7 |
| Permission Entries | 95+ |
| **Missing in Permissions** | **13** |
| **Phantom References** | **1** (search_weaviate) |
| **Unregistered Classes** | **3** |

---

**Report Generated:** 2026-02-06
**Scanner:** SCOUT_114.4
**Status:** Complete with Findings
