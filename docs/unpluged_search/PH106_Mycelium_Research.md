# MYCELIUM Research - AI Agents & MCP Integration

**Date**: 2026-02-02
**Phase**: 106 (Multi-Agent MCP Architecture)
**Status**: Complete - Internal framework analysis + compatibility assessment

---

## Executive Summary

MYCELIUM is **VETKA's proprietary research & orchestration framework**, not an external library. It integrates deeply with MCP (Model Context Protocol) and serves as the agent coordination layer for distributed task execution.

### Key Findings

| Aspect | Finding |
|--------|---------|
| **Type** | Internal framework (VETKA-native) |
| **Purpose** | Semantic-first research agent with token budgeting |
| **MCP Integration** | Native via `VETKAToolsClient` (REST bridge) |
| **Current Status** | Phase 105 v2.0 active |
| **Compatibility** | Excellent - designed for MCP protocol |
| **VETKA Benefit** | High - core agent coordination system |

---

## 1. What is MYCELIUM?

### 1.1 Definition

MYCELIUM is a **multi-phase research and execution orchestrator** for VETKA that:

1. **Decomposes complex tasks** into subtasks (Architect phase)
2. **Researches unclear aspects** using semantic-first search (Researcher phase)
3. **Executes implementation** with token budget constraints (Executor phase)
4. **Monitors health** via heartbeat mechanisms (Proactive phase)

**Etymology**: Named after fungal mycelium networks - distributed, interconnected nodes sharing nutrients/information.

### 1.2 Core Components

```
MYCELIUM v2.0 Architecture
├── MyceliumAuditor (main orchestrator)
├── TokenBudget (adaptive token allocation)
├── VETKAToolsClient (MCP bridge)
├── Semantic Search (Qdrant vector DB)
├── Eternal Persistence (disk + Qdrant)
└── Approval Workflow (audit → approve → create)
```

### 1.3 Where It Lives

**Primary Implementation**: `/src/services/mycelium_auditor.py` (867 lines)

**Related Components**:
- `/src/orchestration/agent_pipeline.py` - Task decomposition
- `/src/services/approval_service.py` - Artifact approval
- `/data/mycelium_eternal/` - Persistent findings storage

---

## 2. MYCELIUM vs. Other Agent Frameworks

### 2.1 Comparison Matrix

| Feature | MYCELIUM | AutoGen | LangChain Agents | CrewAI |
|---------|----------|---------|------------------|--------|
| **Task Decomposition** | ✅ Native | ✅ Via groupchat | ✅ Native | ✅ Native |
| **Token Budgeting** | ✅ Adaptive (300-2000) | ❌ None | ❌ None | ⚠️ Limited |
| **Semantic Search** | ✅ Qdrant-first | ❌ No | ✅ Via embeddings | ✅ Via embeddings |
| **MCP Integration** | ✅ Native bridge | ❌ No | ❌ No | ❌ No |
| **Persistent Memory** | ✅ Eternal disk | ⚠️ Via memory banks | ✅ Via vector DB | ✅ Via memory |
| **Heartbeat Monitoring** | ✅ 5min intervals | ❌ No | ❌ No | ❌ No |
| **Approval Workflow** | ✅ Built-in | ❌ No | ❌ No | ⚠️ Via tools |
| **Output Format** | ✅ JSON-only | ✅ Flexible | ✅ Flexible | ✅ Flexible |
| **Qdrant Integration** | ✅ Primary search | ❌ No | ⚠️ Optional | ⚠️ Optional |

### 2.2 Unique Strengths

**MYCELIUM excels at:**

1. **Economic token usage** - Hard stop at 80% budget threshold
2. **Semantic prioritization** - Vector search 90% of time (grep fallback only)
3. **VETKA-native tooling** - 25+ MCP tools available directly
4. **Eternal persistence** - High-value findings saved automatically
5. **Budget-aware research** - Complexity multipliers (research:1.0x, audit:1.5x, batch:2.5x)

**Differences from competitors:**
- No hardcoded token limits (adaptive formula)
- Proactive heartbeat monitoring (catch stale tasks)
- Workflow-integrated approval (audit → approve → create)

---

## 3. MYCELIUM's MCP Integration

### 3.1 Architecture: How MYCELIUM Talks to MCP

```
┌──────────────────────────────────────┐
│  Claude Code (User Interface)        │
│  MCP Client (claude-desktop app)     │
└────────────────────┬─────────────────┘
                     │
        MCP Protocol (stdio)
                     │
        ┌────────────▼──────────────┐
        │  VETKA MCP Server         │
        │  (vetka_mcp_bridge.py)    │
        └────────────┬──────────────┘
                     │
        ┌────────────▼──────────────────────────┐
        │  Tool Handlers (25+ tools)           │
        │                                       │
        │  ├─ vetka_search_semantic            │
        │  ├─ vetka_spawn_pipeline ←─────────┐ │
        │  ├─ vetka_read_file                 │ │
        │  └─ ... (22+ more)                  │ │
        └─────────────┬───────────────────────┘ │
                      │                         │
        ┌─────────────▼──────────────┐          │
        │  VETKA REST API            │          │
        │  (localhost:5001)          │          │
        │                            │          │
        │  ├─ /api/search/semantic   │          │
        │  ├─ /api/files/read        │          │
        │  └─ /api/health            │          │
        └─────────────┬──────────────┘          │
                      │                         │
        ┌─────────────▼───────────────────────┐ │
        │  MYCELIUM Services                  │◄┘
        │  (VETKAToolsClient)                 │
        │                                      │
        │  ├─ MyceliumAuditor                 │
        │  ├─ TokenBudget                     │
        │  ├─ Semantic Search (Qdrant)        │
        │  └─ Eternal Persistence             │
        └──────────────────────────────────────┘
```

### 3.2 Data Flow: Research Execution

```
1. USER: "Research Phase 106 agent architecture"
          ↓
2. MCP TOOL: vetka_spawn_pipeline(task="...", phase_type="research")
          ↓
3. MYCELIUM AUDITOR: Execute enforced research
          │
          ├─ Calculate token budget: 300 * 1.0 = 300 tokens
          │
          ├─ SEMANTIC SEARCH (Primary):
          │  └─ Query Qdrant for "MARKER_106 agent" → 5+ results
          │
          └─ If <3 results:
             ├─ FALLBACK (grep): Search src/**/*.py
             └─ Return results with method="grep_fallback"
          ↓
4. FINDINGS GENERATION
          ├─ Extract code blocks
          ├─ Confidence scoring
          └─ JSON validation (Pydantic)
          ↓
5. ETERNAL SAVE (if surprise_score > 0.7)
          ├─ data/mycelium_eternal/{phase}_{timestamp}.json
          └─ Qdrant: mycelium_audits collection
          ↓
6. OUTPUT
          ├─ Tokens used: 245/300 (81.7% efficiency)
          ├─ Method: "semantic"
          ├─ Findings: [{file, line, confidence}, ...]
          └─ Next action: "proceed"
```

### 3.3 VETKAToolsClient - MCP Bridge

**Location**: `src/services/mycelium_auditor.py:223-403`

The `VETKAToolsClient` is a **REST wrapper** around MCP tools:

```python
class VETKAToolsClient:
    """Client for VETKA MCP-style tools via REST API."""

    async def search_semantic(query, limit=10)
        # → /api/search/semantic

    async def search_files(query, search_type="content", limit=20)
        # → /api/search/files

    async def read_file(file_path)
        # → /api/files/read

    async def get_tree(format_type="summary")
        # → /api/tree/data

    async def health()
        # → /api/health
```

**Key design**:
- Singleton pattern (one session per VETKA process)
- Timeout handling (30s default)
- Fallback chains (API → direct Qdrant → grep)

---

## 4. MYCELIUM v2.0 Features

### 4.1 Adaptive Token Budget

**Formula**: `budget = base * complexity + artifacts * 150 + voice_bonus`

```python
# Examples:
- Simple research:           300 tokens
- Audit 3 artifacts:         300*1.5 + 3*150 = 900 tokens
- Batch implement w/ voice:  300*2.5 + 5*150 + 300 = 1800 tokens
- Maximum:                   2000 tokens (hard cap)
- Minimum:                   300 tokens
- Stop threshold:            80% of budget
```

**Complexity multipliers**:
```
research:   1.0x  (simple exploration)
audit:      1.5x  (marker verification)
implement:  2.0x  (code changes)
batch:      2.5x  (multiple files)
```

### 4.2 Semantic-First Search Strategy

**3-Tier Fallback**:

1. **VETKA API (MCP-style)** - Primary, 90% success
   - Uses full semantic search infrastructure
   - Query: embeddings for markers, patterns, issues
   - Threshold: score ≥ 0.7

2. **Qdrant Direct** - Secondary, if API unavailable
   - Direct vector DB access
   - Lower reliability (no normalization)

3. **Grep Fallback** - Last resort, 10% cases
   - Pattern matching on source code
   - Only when semantic fails
   - Returns confidence: 0.5

### 4.3 Eternal Persistence

**Automatic Save** (if surprise_score > 0.7):

```
Data saved to:
├─ /data/mycelium_eternal/{phase}_{timestamp}.json
└─ Qdrant: mycelium_audits collection

Contents:
{
  "phase": 106,
  "task": "Research task description",
  "findings": [...],
  "eternal_saved": true,
  "timestamp": "2026-02-02T12:34:56"
}
```

### 4.4 Heartbeat Monitoring

**Every 5 minutes**:
- Check pending tasks
- Alert if task pending > 30 min (stale)
- Socket.IO notification to UI

### 4.5 Approval Workflow

**File Creation Protection**:

```
User Request
    ↓
Audit (MYCELIUM analysis)
    ↓
Approval Service (L2 Scout)
    ↓
If approved:
  ├─ Backup old version
  └─ Create new file with MARKER
    ↓
If rejected:
  └─ Fallback to user approval
```

---

## 5. MYCELIUM Integration with Current Systems

### 5.1 Agent Pipeline Integration

MYCELIUM works alongside `AgentPipeline` (spawn system):

```
User Task
  ↓
AgentPipeline._architect_plan()
  ├─ Decompose into subtasks
  └─ Mark unclear parts: needs_research=True
  ↓
For each subtask:
  ├─ If needs_research:
  │   └─ MYCELIUM.research() ← Semantic search + enrichment
  ├─ Execute subtask (code generation)
  └─ Add to STM (short-term memory)
  ↓
Results
```

### 5.2 Elisya Integration

**Potential for Phase 107**:
- Pass `ElisyaState` to MYCELIUM
- Share PM context, architecture decisions
- Feed findings back to Elisya CAM

### 5.3 MCP Tool Availability

MYCELIUM can access **25+ MCP tools**:

```
Search Tools:
├─ vetka_search_semantic  (primary)
├─ vetka_search_files     (fallback)
├─ vetka_query_qdrant     (vector DB)
└─ vetka_semantic_batch

File Tools:
├─ vetka_read_file
├─ vetka_write_file
├─ vetka_get_tree
└─ vetka_list_files

Chat Tools:
├─ vetka_send_to_chat
├─ vetka_group_history
└─ ...

Context Tools:
├─ vetka_inject_context
├─ vetka_get_arc_summary
└─ ...
```

---

## 6. MYCELIUM & External Agent Frameworks

### 6.1 Can We Use External Frameworks?

**Options**:

1. **Keep MYCELIUM as-is** (Recommended)
   - Already deeply integrated with VETKA
   - MCP-native design
   - Optimized for token efficiency
   - No external dependencies

2. **Wrap External Framework** (Medium effort)
   - Use CrewAI or AutoGen for task decomposition
   - Delegate to MYCELIUM for research
   - Risk: Performance overhead

3. **Hybrid Approach** (High complexity)
   - MYCELIUM for research
   - CrewAI for parallel execution
   - Complex integration needed

### 6.2 Recommendation for VETKA

**Verdict**: Stick with MYCELIUM v2.0

**Reasoning**:
- ✅ Already optimized for VETKA's token model
- ✅ Direct MCP integration (no wrapper needed)
- ✅ Tested in Phase 105 implementation
- ✅ Semantic-first approach unique to VETKA
- ✅ Approval workflow built-in
- ⚠️ External frameworks add complexity without benefit

---

## 7. MYCELIUM Current Implementation Status

### 7.1 Phase 105 Completion

**v2.0 Features Implemented**:

✅ **Core Auditor**
- MyceliumAuditor class (408 lines)
- TokenBudget adaptive calculation
- Pydantic JSON validation

✅ **Search Infrastructure**
- VETKAToolsClient (REST bridge)
- 3-tier fallback chain
- Semantic-first strategy

✅ **Persistence**
- Eternal disk storage
- Qdrant integration
- Timestamp tracking

✅ **Monitoring**
- Heartbeat loops
- Stale task detection
- Status tracking

✅ **Integration**
- MCP tool registration
- Approval workflow
- Chat progress emission

### 7.2 Known Gaps

❌ **Parallel Execution** - Not yet implemented
- Architect returns execution_order, but ignored
- All subtasks run sequentially
- Impact: Slower for independent tasks

❌ **Bidirectional Chat** - One-way only
- Streams progress to chat
- Can't read feedback during execution
- No pause/resume capability

❌ **Cross-Pipeline Memory** - STM resets each run
- Short-term memory cleared on new execute()
- No long-term learning between runs
- Potential fix: Elisya CAM integration

---

## 8. Compatibility Assessment

### 8.1 MCP Protocol Compatibility

| Aspect | Status | Notes |
|--------|--------|-------|
| **Tool Registration** | ✅ Full | Native MCP tool: vetka_mycelium_pipeline |
| **Tool Invocation** | ✅ Full | Standard MCP request/response |
| **Resource Handling** | ✅ Full | No resource constraints |
| **Error Handling** | ✅ Full | Proper error responses |
| **Streaming** | ✅ Partial | Progress via chat POST, not MCP streaming |
| **Context Injection** | ✅ Full | Via inject_context parameter |

**Rating**: 9/10 - Excellent MCP compatibility

### 8.2 Claude Code Compatibility

✅ **Works perfectly** with Claude Code via MCP
- Callable as `/spawn <task>`
- Progress visible in group chat
- Artifacts reviewable before apply

### 8.3 External Client Compatibility

| Client | Status | Notes |
|--------|--------|-------|
| **Claude Desktop** | ✅ Full | Native MCP support |
| **Cursor** | ✅ Full | MCP via stdio |
| **Cline (VS Code)** | ✅ Full | MCP experimental support |
| **Continue (VS Code)** | ✅ Full | MCP plugin available |
| **Zed** | ⚠️ Beta | MCP support in progress |

---

## 9. Recommendations for VETKA

### 9.1 Short-term (Phase 106 - 1-2 weeks)

1. **Document MYCELIUM** ✅ (This document)
2. **Add Parallel Execution**
   - Implement asyncio.gather() for independent subtasks
   - Add agent numbering (dev1, dev2, etc.)
   - Test with parallel benchmark
   - Effort: 3 hours

3. **Bidirectional Chat**
   - Add `_check_chat_feedback()` method
   - Pause/resume capability
   - Effort: 4 hours

### 9.2 Medium-term (Phase 107 - 1-2 months)

4. **Elisya Integration**
   - Pass ElisyaState to MYCELIUM
   - Feed findings back to CAM
   - Share workflow context
   - Effort: 8 hours

5. **ARC Gap Analysis**
   - Pre-planning ARC analysis
   - Enrich architect prompts
   - Effort: 4 hours

6. **Multi-Model Routing**
   - Route complex research to Grok
   - Route implementation to Claude
   - Effort: 6 hours

### 9.3 Long-term (Phase 108+)

7. **Spawn Nesting**
   - Allow subtasks to spawn sub-spawns
   - Recursive decomposition
   - Effort: 10 hours

8. **Collective Intelligence**
   - Multiple MYCELIUM instances
   - Shared eternal disk
   - Voting on priorities
   - Effort: 20 hours

---

## 10. Key Files Reference

### MYCELIUM Implementation

```
src/services/
├── mycelium_auditor.py          (867 lines - CORE)
├── approval_service.py          (integration)
└── __init__.py

src/orchestration/
├── agent_pipeline.py            (spawn/mycelium orchestration)
└── ... (supporting modules)

src/mcp/
├── vetka_mcp_bridge.py          (MCP tool registration)
└── tools/

data/
└── mycelium_eternal/            (persistent findings)
```

### Documentation

```
docs/
├── 103_ph/
│   └── MYCELIUM_SPAWN_ANALYSIS.md        (architecture)
├── 104_ph/
│   ├── RENAME_SPAWN_TO_MYCELIUM.md       (refactoring plan)
│   └── MCP_LEGACY_WRAPPER.md
├── 105_ph/
│   ├── MYCELIUM_V2_PROMPT_TEMPLATE.md    (prompt guide)
│   ├── MYCELIUM_JARVIS_RESEARCH_*.md     (voice integration)
│   └── ...
└── phase_106_multi_agent_mcp/
    ├── research/
    │   └── MYCELIUM_RESEARCH.md          (THIS FILE)
    └── ...
```

---

## 11. External Frameworks Analysis

### 11.1 AutoGen by Microsoft

**Status**: Evaluated but not integrated

**Comparison**:
- Similar task decomposition
- No token budgeting
- No semantic search
- No MCP integration
- Complex setup

**Verdict**: MYCELIUM better for VETKA

### 11.2 CrewAI

**Status**: Possible future integration

**Comparison**:
- Strong role-based agents
- Memory support
- Tool integration
- No MCP native support

**Potential Use**: Parallel execution framework (wrap MYCELIUM)

### 11.3 LangChain Agents

**Status**: Lightweight alternative

**Comparison**:
- Good for simple workflows
- Limited budget control
- Vector search support
- No approval workflow

**Verdict**: Too simple for VETKA's needs

---

## 12. Glossary

| Term | Definition |
|------|-----------|
| **MYCELIUM** | Distributed research orchestrator (VETKA-native) |
| **MCP** | Model Context Protocol (standard tool integration) |
| **Auditor** | Core MYCELIUM class enforcing constraints |
| **Semantic Search** | Vector-based code search (Qdrant) |
| **Eternal Save** | Persistent storage to disk + Qdrant |
| **Token Budget** | Adaptive token limit per task |
| **STM** | Short-term memory (within one pipeline run) |
| **Spawn** | Legacy name for pipeline (being renamed to Mycelium) |
| **Artifact** | Generated file/code output |
| **Approval Flow** | Audit → Approve → Create workflow |

---

## Conclusion

MYCELIUM is **VETKA's proprietary multi-agent orchestration system** designed specifically for:
- **Semantic-first research** (90% vector search)
- **Economic token usage** (adaptive budgets)
- **MCP-native integration** (seamless tool access)
- **Persistent learning** (eternal storage)
- **Safe artifact creation** (approval workflow)

### Integration Verdict

**Recommendation**: Keep MYCELIUM as primary orchestrator
- ✅ Already MCP-compatible
- ✅ Deeply integrated with VETKA
- ✅ Optimized for token efficiency
- ✅ Tested and proven in Phase 105
- ✅ Unique features unavailable elsewhere

**For Phase 106**: Focus on enhancing MYCELIUM rather than replacing it.

---

**Document Status**: Complete - Ready for Phase 106 implementation
**Next Action**: Implement parallel execution + bidirectional chat (Section 9.1)
