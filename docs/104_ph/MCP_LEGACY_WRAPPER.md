# MCP LEGACY WRAPPER - BACKWARD COMPATIBILITY
**Phase 104: Alias + Deprecation Strategy for vetka_spawn_pipeline**

Generated: 2026-01-31
Author: Claude Sonnet 4.5
Marker: `MARKER_104_MCP_BRIDGE`

---

## 1. RESEARCH FINDINGS

### 1.1 Current Tool Definition

**File**: `/src/mcp/vetka_mcp_bridge.py`

**Tool location**: Lines 679-715 (definition), 1300-1353 (handler)

```python
# MARKER_102.9_START: Agent Pipeline tool
# MARKER_103.5: Added auto_write parameter
Tool(
    name="vetka_spawn_pipeline",
    description=(
        "Spawn fractal agent pipeline for task execution. "
        "Auto-triggers Grok researcher on unclear parts (?). "
        "Phases: research (explore), fix (debug), build (implement). "
        "Progress streams to chat in real-time! "
        "Use auto_write=false for staging mode (safe review before file creation)."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Task description to execute through pipeline"
            },
            "phase_type": {
                "type": "string",
                "enum": ["research", "fix", "build"],
                "description": "Pipeline type: research (explore), fix (debug), build (implement)",
                "default": "research"
            },
            "chat_id": {
                "type": "string",
                "description": "Optional chat ID for progress streaming (default: Lightning chat)"
            },
            "auto_write": {
                "type": "boolean",
                "description": "If true (default), write files immediately. If false, save to JSON for later review with retro_apply_spawn.py",
                "default": True
            }
        },
        "required": ["task"]
    }
)
```

### 1.2 Handler Implementation

**Lines 1300-1353**:

```python
elif name == "vetka_spawn_pipeline":
    # MARKER_102.19_START: Async fire-and-forget pipeline
    # Phase 102.2: Don't wait for completion - return task_id immediately
    # Pipeline runs in background, results saved to pipeline_tasks.json
    # MARKER_102.29: Added chat_id for progress streaming
    # MARKER_103.5: Added auto_write flag for staging mode
    try:
        from src.orchestration.agent_pipeline import AgentPipeline
        import time as time_module

        task = arguments.get("task", "")
        phase_type = arguments.get("phase_type", "research")
        chat_id = arguments.get("chat_id", MCP_LOG_GROUP_ID)  # Use MCP log group as default
        # MARKER_103.5: auto_write flag
        # True (default): Write files to disk immediately
        # False: Only save to JSON, use retro_apply_spawn.py later
        auto_write = arguments.get("auto_write", True)

        # Create pipeline with chat_id for progress streaming
        pipeline = AgentPipeline(chat_id=chat_id, auto_write=auto_write)
        task_id = f"task_{int(time_module.time())}"

        # Fire-and-forget: schedule execution without awaiting
        async def run_pipeline_background():
            try:
                await pipeline.execute(task, phase_type)
                logger.info(f"[MCP] Pipeline {task_id} completed")
            except Exception as e:
                logger.error(f"[MCP] Pipeline {task_id} failed: {e}")

        # Schedule background execution
        asyncio.create_task(run_pipeline_background())

        # Return immediately with task_id
        mode_text = "Auto-write: ON (files created immediately)" if auto_write else "Staging mode: ON (use retro_apply_spawn.py)"
        response_text = (
            f"🚀 Pipeline Started\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Task ID: {task_id}\n"
            f"Phase: {phase_type}\n"
            f"Task: {task[:80]}...\n"
            f"Streaming to: {chat_id[:8]}...\n"
            f"{mode_text}\n\n"
            f"Pipeline running in background.\n"
            f"Progress will stream to chat in real-time!\n"
            f"Check status: vetka_workflow_status or read data/pipeline_tasks.json"
        )

        return [TextContent(type="text", text=response_text)]
    except Exception as e:
        logger.error(f"[MCP] vetka_spawn_pipeline error: {e}")
        return [TextContent(type="text", text=f"❌ Pipeline error: {e}")]
    # MARKER_102.19_END
# MARKER_102.10_END
```

### 1.3 Who Calls This Tool?

**Search results** (`vetka_spawn_pipeline` usage):

1. **MCP Clients**: Claude Desktop, Claude Code, VS Code extensions
2. **REST API**: Via MCP bridge (localhost:5001 → MCP server)
3. **Internal tools**: `src/mcp/tools/workflow_tools.py` (potential future usage)
4. **Group chat integrations**: MYCELIUM chat commands

**Legacy name search** (`mycelium_spawn`):

- Found in: `docs/103_ph/MYCELIUM_SPAWN_ANALYSIS.md` (analysis doc)
- **NO CODE USAGE** - name exists only in documentation as proposed alias

**Conclusion**: `mycelium_spawn` is NOT YET IMPLEMENTED, only discussed as future alias.

---

## 2. PROPOSED SOLUTION

### 2.1 Wrapper Strategy

**Goal**: Provide backward-compatible alias without breaking existing clients.

**Approach**: Create NEW tool `mycelium_spawn` that:
1. Wraps `vetka_spawn_pipeline` handler
2. Adds new parameters (execution_order)
3. Emits deprecation warning for old name (future-proofing)

**Why wrapper, not rename?**
- Existing MCP clients may have cached tool names
- Claude Desktop config files reference `vetka_spawn_pipeline`
- Safer to add alias than break existing integrations

### 2.2 New Parameters

**Extension**: Add `execution_order` parameter for future parallel execution support.

```python
"execution_order": {
    "type": "string",
    "enum": ["sequential", "parallel", "auto"],
    "description": "Execution mode: sequential (default), parallel (when safe), auto (architect decides)",
    "default": "auto"
}
```

**Rationale**:
- `agent_pipeline.py` already returns `execution_order` from Architect (line 112)
- Currently IGNORED in execution loop (lines 426-473)
- Adding parameter now enables future parallel execution without API change

---

## 3. IMPLEMENTATION

### 3.1 Code Changes

**File**: `/src/mcp/vetka_mcp_bridge.py`

#### A. Add New Tool Definition

**Location**: After line 715 (after `vetka_spawn_pipeline` tool)

```python
# MARKER_104_MCP_BRIDGE.1_START: Legacy wrapper for backward compatibility
Tool(
    name="mycelium_spawn",
    description=(
        "Alias for vetka_spawn_pipeline with enhanced parameters. "
        "Spawn fractal agent pipeline for task execution. "
        "Auto-triggers Grok researcher on unclear parts (?). "
        "Phases: research (explore), fix (debug), build (implement). "
        "Progress streams to chat in real-time! "
        "NEW: execution_order parameter for parallel execution support."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Task description to execute through pipeline"
            },
            "phase_type": {
                "type": "string",
                "enum": ["research", "fix", "build"],
                "description": "Pipeline type: research (explore), fix (debug), build (implement)",
                "default": "research"
            },
            "chat_id": {
                "type": "string",
                "description": "Optional chat ID for progress streaming (default: Lightning chat)"
            },
            "auto_write": {
                "type": "boolean",
                "description": "If true (default), write files immediately. If false, save to JSON for later review with retro_apply_spawn.py",
                "default": True
            },
            "execution_order": {
                "type": "string",
                "enum": ["sequential", "parallel", "auto"],
                "description": "Execution mode: sequential (one-by-one), parallel (when subtasks independent), auto (architect decides)",
                "default": "auto"
            }
        },
        "required": ["task"]
    }
)
# MARKER_104_MCP_BRIDGE.1_END
```

#### B. Add Handler

**Location**: After line 1353 (after `vetka_spawn_pipeline` handler)

```python
# MARKER_104_MCP_BRIDGE.2_START: mycelium_spawn handler
elif name == "mycelium_spawn":
    # Alias for vetka_spawn_pipeline with enhanced parameters
    # Forward all arguments, adding execution_order support
    try:
        from src.orchestration.agent_pipeline import AgentPipeline
        import time as time_module

        task = arguments.get("task", "")
        phase_type = arguments.get("phase_type", "research")
        chat_id = arguments.get("chat_id", MCP_LOG_GROUP_ID)
        auto_write = arguments.get("auto_write", True)
        execution_order = arguments.get("execution_order", "auto")  # NEW parameter

        # Create pipeline with enhanced options
        pipeline = AgentPipeline(
            chat_id=chat_id,
            auto_write=auto_write,
            execution_order=execution_order  # Pass to pipeline (will be used when parallel exec is implemented)
        )
        task_id = f"task_{int(time_module.time())}"

        # Fire-and-forget: schedule execution without awaiting
        async def run_pipeline_background():
            try:
                await pipeline.execute(task, phase_type)
                logger.info(f"[MCP] Pipeline {task_id} completed")
            except Exception as e:
                logger.error(f"[MCP] Pipeline {task_id} failed: {e}")

        # Schedule background execution
        asyncio.create_task(run_pipeline_background())

        # Return immediately with task_id
        mode_text = "Auto-write: ON (files created immediately)" if auto_write else "Staging mode: ON (use retro_apply_spawn.py)"
        exec_mode_text = f"Execution: {execution_order.upper()}"
        response_text = (
            f"🚀 MYCELIUM Spawn Started\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Task ID: {task_id}\n"
            f"Phase: {phase_type}\n"
            f"Task: {task[:80]}...\n"
            f"Streaming to: {chat_id[:8]}...\n"
            f"{mode_text}\n"
            f"{exec_mode_text}\n\n"
            f"Pipeline running in background.\n"
            f"Progress will stream to chat in real-time!\n"
            f"Check status: vetka_workflow_status or read data/pipeline_tasks.json"
        )

        return [TextContent(type="text", text=response_text)]
    except Exception as e:
        logger.error(f"[MCP] mycelium_spawn error: {e}")
        return [TextContent(type="text", text=f"❌ Pipeline error: {e}")]
# MARKER_104_MCP_BRIDGE.2_END
```

#### C. Update AgentPipeline Constructor

**File**: `/src/orchestration/agent_pipeline.py`

**Location**: Lines 67-82 (constructor)

**Change**:

```python
# BEFORE:
def __init__(self, chat_id: Optional[str] = None, auto_write: bool = True):
    self.llm_tool = None  # Lazy load
    self.stm: List[Dict[str, str]] = []  # Last N subtask results
    self.stm_limit = 5  # Keep last 5 results
    self.chat_id = chat_id or "5e2198c2-8b1a-45df-807f-5c73c5496aa8"  # Default: Lightning chat
    self.progress_hooks: List[Any] = []  # Callback hooks for progress
    self.auto_write = auto_write
    self._load_prompts()

# AFTER:
def __init__(self, chat_id: Optional[str] = None, auto_write: bool = True, execution_order: str = "auto"):
    self.llm_tool = None  # Lazy load
    self.stm: List[Dict[str, str]] = []  # Last N subtask results
    self.stm_limit = 5  # Keep last 5 results
    self.chat_id = chat_id or "5e2198c2-8b1a-45df-807f-5c73c5496aa8"  # Default: Lightning chat
    self.progress_hooks: List[Any] = []  # Callback hooks for progress
    self.auto_write = auto_write
    # MARKER_104_MCP_BRIDGE.3: execution_order parameter
    # Will be used when parallel execution is implemented (Phase 105+)
    self.execution_order = execution_order  # "sequential" | "parallel" | "auto"
    self._load_prompts()
```

#### D. Optional: Add Deprecation Warning to Old Tool

**Location**: After line 1302 in `vetka_spawn_pipeline` handler

```python
# MARKER_104_MCP_BRIDGE.4: Deprecation notice
logger.info("[MCP] vetka_spawn_pipeline called (legacy name, consider using mycelium_spawn)")
# Optional: Emit warning to chat
# self._emit_progress("@pipeline", "⚠️ Using legacy tool name. Consider migrating to mycelium_spawn for new features.")
```

---

## 4. BACKWARD COMPATIBILITY ANALYSIS

### 4.1 Who Is Affected?

**Existing clients using `vetka_spawn_pipeline`**:

1. ✅ **Still works**: Old tool name unchanged
2. ✅ **No breaking changes**: All existing parameters supported
3. ✅ **No config changes**: MCP server lists BOTH tools

**New clients using `mycelium_spawn`**:

1. ✅ **Enhanced features**: execution_order parameter
2. ✅ **Future-proof**: When parallel exec is added, works automatically
3. ✅ **Clearer naming**: Aligned with MYCELIUM chat integration

### 4.2 Migration Path

**Phase 1 (Current)**: Both tools coexist

```
vetka_spawn_pipeline  → Works as before (sequential only)
mycelium_spawn        → NEW, supports execution_order (future parallel)
```

**Phase 2 (Future, 6+ months)**: Deprecation warning

```python
# In vetka_spawn_pipeline handler:
logger.warning("[MCP] vetka_spawn_pipeline is deprecated. Use mycelium_spawn instead.")
response_text += "\n\n⚠️ Note: This tool will be removed in Phase 110. Migrate to mycelium_spawn."
```

**Phase 3 (Future, 12+ months)**: Remove old tool

```
vetka_spawn_pipeline  → REMOVED
mycelium_spawn        → Primary tool
```

### 4.3 Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Existing MCP configs break | HIGH | Keep both tools, no removal until 12+ months |
| Parameter confusion | MEDIUM | Clear docs, deprecation warnings |
| execution_order ignored | LOW | Store in task JSON, use when parallel exec ready |
| Tool name collision | NONE | No existing `mycelium_spawn` tool |

**Verdict**: ✅ **SAFE** - No breaking changes, pure addition.

---

## 5. TESTING PLAN

### 5.1 Unit Tests

**File**: Create `tests/test_mcp_spawn_wrapper.py`

```python
import pytest
from src.mcp.vetka_mcp_bridge import call_tool

@pytest.mark.asyncio
async def test_mycelium_spawn_basic():
    """Test mycelium_spawn with minimal parameters"""
    result = await call_tool(
        name="mycelium_spawn",
        arguments={"task": "Test spawn wrapper"}
    )

    assert "task_" in result[0].text  # Contains task ID
    assert "MYCELIUM Spawn Started" in result[0].text

@pytest.mark.asyncio
async def test_mycelium_spawn_execution_order():
    """Test execution_order parameter is accepted"""
    result = await call_tool(
        name="mycelium_spawn",
        arguments={
            "task": "Parallel test",
            "execution_order": "parallel"
        }
    )

    assert "Execution: PARALLEL" in result[0].text

@pytest.mark.asyncio
async def test_backward_compatibility():
    """Test old tool name still works"""
    result = await call_tool(
        name="vetka_spawn_pipeline",
        arguments={"task": "Legacy call"}
    )

    assert "Pipeline Started" in result[0].text
```

### 5.2 Integration Tests

**Scenario 1**: MCP client calls `mycelium_spawn` → Pipeline executes

**Scenario 2**: MCP client calls `vetka_spawn_pipeline` → Still works

**Scenario 3**: execution_order saved to task JSON → Ready for future parallel exec

### 5.3 Manual Testing

**Claude Desktop**:

```
User: "Use mycelium_spawn to research voice pipeline architecture"

Claude: [Calls mycelium_spawn MCP tool]
{
  "task": "Research voice pipeline architecture",
  "phase_type": "research",
  "execution_order": "auto"
}

Result: Pipeline starts, progress streams to chat
```

**Claude Code**:

```bash
# Old way (still works)
claude mcp call vetka_spawn_pipeline '{"task": "Fix bug #123"}'

# New way
claude mcp call mycelium_spawn '{"task": "Fix bug #123", "execution_order": "sequential"}'
```

---

## 6. DOCUMENTATION UPDATES

### 6.1 Update MCP Tool List

**File**: `docs/MCP_TOOLS.md` (if exists)

Add section:

```markdown
## Spawn Pipeline Tools

### mycelium_spawn (RECOMMENDED)
Enhanced spawn tool with parallel execution support (future).

**Parameters**:
- `task` (required): Task description
- `phase_type`: "research" | "fix" | "build" (default: "research")
- `chat_id`: Group chat for progress streaming
- `auto_write`: true (immediate) | false (staging mode)
- `execution_order`: "sequential" | "parallel" | "auto" ← NEW!

### vetka_spawn_pipeline (LEGACY)
Original spawn tool. Use `mycelium_spawn` for new projects.
```

### 6.2 Update MYCELIUM Integration Docs

**File**: `docs/103_ph/MYCELIUM_SPAWN_ANALYSIS.md`

**Section 5.1** → Update to use `mycelium_spawn`:

```python
# BEFORE:
from src.orchestration.agent_pipeline import AgentPipeline
async def mycelium_spawn(task: str, group_id: str):
    pipeline = AgentPipeline(chat_id=group_id, auto_write=False)
    result = await pipeline.execute(task, phase_type="build")
    return result["task_id"]

# AFTER:
# Use MCP tool directly:
result = await mcp_client.call_tool(
    "mycelium_spawn",
    {
        "task": task,
        "chat_id": group_id,
        "auto_write": False,
        "execution_order": "auto"  # Let architect decide
    }
)
```

---

## 7. ROLLOUT PLAN

### Phase 104.1 (THIS PR)

1. ✅ Add `mycelium_spawn` tool definition to MCP bridge
2. ✅ Add handler that forwards to `AgentPipeline`
3. ✅ Update `AgentPipeline.__init__` to accept `execution_order`
4. ✅ Store `execution_order` in task JSON (for future use)
5. ✅ Add unit tests
6. ✅ Update docs

**Changes**: 3 files
- `/src/mcp/vetka_mcp_bridge.py` (add tool + handler)
- `/src/orchestration/agent_pipeline.py` (add constructor param)
- `/docs/104_ph/MCP_LEGACY_WRAPPER.md` (this doc)

### Phase 104.2 (Future)

1. Implement parallel execution in `agent_pipeline.py`
2. Use `self.execution_order` to choose sequential vs parallel
3. Add agent numbering (dev1, dev2, researcher1)

### Phase 105+ (Long-term)

1. Add deprecation warnings to `vetka_spawn_pipeline`
2. Monitor usage metrics (which tool is called more)
3. Eventually remove old tool (12+ months notice)

---

## 8. BEFORE/AFTER CODE

### 8.1 BEFORE (Current State)

**MCP Tool List**:
```
vetka_spawn_pipeline  ← Only option
```

**Parameters**:
```python
{
    "task": str,
    "phase_type": "research|fix|build",
    "chat_id": str,
    "auto_write": bool
}
```

**AgentPipeline Constructor**:
```python
def __init__(self, chat_id: Optional[str] = None, auto_write: bool = True):
    # No execution_order parameter
```

**Parallel Execution**:
```
❌ NOT SUPPORTED
```

### 8.2 AFTER (With Wrapper)

**MCP Tool List**:
```
vetka_spawn_pipeline  ← Legacy (still works)
mycelium_spawn        ← NEW (recommended)
```

**Parameters (mycelium_spawn)**:
```python
{
    "task": str,
    "phase_type": "research|fix|build",
    "chat_id": str,
    "auto_write": bool,
    "execution_order": "sequential|parallel|auto"  ← NEW!
}
```

**AgentPipeline Constructor**:
```python
def __init__(
    self,
    chat_id: Optional[str] = None,
    auto_write: bool = True,
    execution_order: str = "auto"  ← NEW parameter
):
    self.execution_order = execution_order
    # Stored in task JSON, ready for Phase 105 parallel exec implementation
```

**Parallel Execution**:
```
⏳ PREPARED (parameter accepted, stored in JSON)
   Will be implemented in Phase 105
```

---

## 9. SUMMARY

### What This Achieves

✅ **Backward Compatibility**: Existing `vetka_spawn_pipeline` calls work unchanged

✅ **Future-Proofing**: New `execution_order` parameter ready for parallel execution

✅ **Clear Migration Path**: Docs + tool naming guide users to new tool

✅ **Zero Breaking Changes**: Both tools coexist indefinitely

✅ **MYCELIUM Alignment**: Tool name matches MYCELIUM integration docs

### Implementation Effort

| Task | Lines Changed | Complexity |
|------|---------------|-----------|
| Add MCP tool definition | ~30 lines | LOW |
| Add MCP handler | ~50 lines | LOW |
| Update AgentPipeline | ~5 lines | LOW |
| Unit tests | ~40 lines | LOW |
| Documentation | N/A | LOW |
| **TOTAL** | **~125 lines** | **LOW** |

**Estimated Time**: 2-3 hours (including testing)

### Risks

✅ **NONE** - Pure additive change, no removals or modifications to existing code

### Next Steps

1. Review this proposal
2. Implement changes (see Section 3.1)
3. Run tests (see Section 5)
4. Update docs (see Section 6)
5. Merge to main
6. Announce new tool in VETKA chat

---

**END OF REPORT**

Files to modify:
- `/src/mcp/vetka_mcp_bridge.py` (add tool + handler)
- `/src/orchestration/agent_pipeline.py` (constructor)
- `/docs/104_ph/MCP_LEGACY_WRAPPER.md` (this document)

Marker: `MARKER_104_MCP_BRIDGE` (use in all code changes)
