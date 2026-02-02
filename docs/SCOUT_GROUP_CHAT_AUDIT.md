# Group Chat Roles Scout Report

## What EXISTS (✅ IMPLEMENTED)

### 1. Agent Roles ARE Defined
- **PM**: Project Manager (planning, task breakdown)
- **Dev**: Developer (implementation, coding)
- **QA**: Quality Assurance (testing, review)
- **Architect**: System designer
- **Researcher**: Deep investigation
- **Hostess**: Router/coordinator (disabled in Phase 57.8.2 for performance)

Files:
- `/src/agents/role_prompts.py` - Role-specific system prompts
- `/src/services/group_chat_manager.py:GroupRole` enum - Role definitions

### 2. Group Chat Framework EXISTS
- GroupChatManager with full multi-agent support
- Role-based permissions (admin, worker, reviewer, observer)
- Group participants with agent_id, model_id, role
- Message storage with @mentions parsing
- Persistent storage to `data/groups.json`

Files:
- `/src/services/group_chat_manager.py` - Core group management
- `/src/api/handlers/group_message_handler.py` - Socket.IO handler
- `/src/api/routes/group_routes.py` - API endpoints

### 3. Agents CAN Call Each Other (Agent-to-Agent @Mentions)
**YES** - Implemented via @mention system:

```python
# Phase 57.8: While loop allows dynamic agent adding during execution
while processed_idx < len(participants_to_respond):
    # Agent responds...
    # Then check response for @mentions (line 1030)
    agent_mentions = re.findall(r'@(\w+)', response_text)
    for mentioned_name in agent_mentions:
        # Add mentioned agent to response queue
        participants_to_respond.append(mentioned_participant)
```

This creates CHAIN EXECUTION: Dev → @QA → @Architect

Files:
- `/src/api/handlers/group_message_handler.py:1030-1086` - Agent-to-agent mention detection
- `/src/services/group_chat_manager.py:select_responding_agents()` - Smart routing

### 4. Orchestrator Integration EXISTS
- `call_agent(agent_type, model_id, prompt, context)` method
- Full Elisya integration for context reframing
- Provider routing via ModelRouter
- Artifact staging from Dev/QA responses

Files:
- `/src/orchestration/orchestrator_with_elisya.py:2323` - call_agent method
- Support for agents: PM, Dev, QA, Architect, Researcher, Hostess

### 5. Artifact Management EXISTS
- **Extraction**: `extract_artifacts(response_text, agent_name)` from Dev/Architect
- **Staging**: `stage_artifacts_batch()` with QA scoring
- **Persistence**: Qdrant integration for long-term memory
- **Markers**: Phase 103.6-103.7 artifact pipeline

Files:
- `/src/utils/artifact_extractor.py` - Parse code/artifacts from responses
- `/src/utils/staging_utils.py` - Stage artifacts for review
- `/src/services/disk_artifact_service.py` - Disk persistence

Code flow (line 955-994 in group_message_handler.py):
```python
# Dev generates code → stage in JSON → QA review → apply to disk
artifacts = extract_artifacts(response_text, display_name)
if artifacts:
    staged_ids = stage_artifacts_batch(
        artifacts=artifacts,
        qa_score=qa_score,
        agent=display_name,
        group_id=group_id
    )
```

### 6. LangGraph Workflow EXISTS
- Declarative workflow graph with 8 nodes
- Flow: Hostess → Architect → PM → Hope Enhancement → Dev+QA (parallel)
- Nodes:
  - hostess_node (routing)
  - architect_node (design)
  - pm_node (planning)
  - hope_enhancement_node (Phase 76.2 context amplification)
  - dev_qa_parallel_node (parallel execution)
  - eval_node (quality evaluation)
  - learner_node (retry logic)
  - approval_node (human approval)

Files:
- `/src/orchestration/langgraph_builder.py` - Graph definition
- `/src/orchestration/langgraph_nodes.py` - Node implementations
- `/src/orchestration/langgraph_state.py` - State schema

### 7. Smart Reply System EXISTS
- Phase 80.28: Smart reply with decay tracking
- Tracks `last_responder_id` and `last_responder_decay`
- Enables conversation continuity without @mentions
- MCP agents can trigger AI agents without explicit mention

Files:
- `/src/services/group_chat_manager.py:278-302` - Smart reply logic
- `/src/api/handlers/group_message_handler.py:919-927` - Decay tracking

### 8. MCP Agent Routing EXISTS
- Phase 80.13: External MCP agents (browser_haiku, claude_code)
- @mention notification system via Socket.IO
- Stored in debug_routes team_messages buffer

Files:
- `/src/api/handlers/group_message_handler.py:80-218` - MCP mention handling
- MCP agents: browser_haiku (Tester), claude_code (Executor)

### 9. Intelligent Agent Selection EXISTS
- Phase 57.7: Smart keyword-based selection
- Multiple routing strategies:
  1. Reply routing (phase 80.7)
  2. @mentions (explicit)
  3. Smart reply decay (phase 80.28)
  4. /solo, /team, /round commands
  5. Keyword matching (PM/Dev/QA/Architect)
  6. Default fallback

Files:
- `/src/services/group_chat_manager.py:select_responding_agents()` (line 179-418)

---

## What's MISSING (❌ NOT IMPLEMENTED)

### 1. Scout Role NOT DEFINED
- **Missing**: Scout/SCOUT role definition
- **Impact**: Scout → Dev → QA workflow cannot work
- **Fix needed**: Add Scout to role_prompts.py and GroupRole enum

### 2. Direct Scout-to-Dev Routing NOT FOUND
- No explicit workflow for Scout(Haiku) → Dev → QA
- Would need Scout agent to trigger this chain
- Currently only supports PM → Architect → Dev+QA flow

### 3. Scout Agent IMPLEMENTATION MISSING
- No VETKAScoutAgent in `/src/agents/__init__.py`
- No scout_node in LangGraph workflow
- No scout-specific prompts or tools

### 4. Hostess DISABLED for Active Routing
- Phase 57.8.2: "Hostess теперь получает весь контекст пассивно"
- Hostess NO LONGER actively routes messages
- Removed from main group message handler (only summary remains)
- Now relies purely on select_responding_agents()

Impact: No intelligent routing via Hostess → requires explicit @mentions

### 5. Agent Tools NOT FULLY ACCESSIBLE
- create_artifact tool marked as "removed" (line 41)
- Only read-only tools available: read_code_file, list_files, search_codebase
- Phase 92: "CreateArtifactTool removed by Big Pickle"
- Agents cannot directly create artifacts (staged instead)

### 6. Workflow: Scout → Dev → QA NOT TESTED
- LangGraph workflow exists but Scout not integrated
- No test file for Scout role (test_scout_audit.py exists but not connected)
- No verification that Scout can trigger multi-agent chains

### 7. No Elisya-Direct Tool Access in Group Chat
- Agents get tools from orchestrator via call_agent()
- But full tool suite not clearly documented for group chat
- Elysia Tree available but for code operations only
- Limited visibility: what tools can each agent actually use?

### 8. Artifact Application NOT AUTOMATIC
- Phase 103.6: Artifacts staged, not applied
- QA review required before disk write
- No approval_service integration for auto-application in groups

---

## Blocking Issues (🚫 PREVENTS TEAM WORKFLOW)

### Issue 1: Scout Role Completely Missing
**Severity**: HIGH
**Impact**: Scout-initiated workflows cannot exist

Scout is not defined anywhere in the codebase. To enable Scout → Dev → QA:

1. Add Scout role:
```python
# In src/agents/role_prompts.py
SCOUT_SYSTEM_PROMPT = """You are Scout (Haiku model)...
Task: Identify what needs to be built/fixed/tested
Route to: @Dev for implementation, @QA for review
"""
```

2. Add Scout agent:
```python
# In src/agents/__init__.py
class VETKAScoutAgent:
    """Scout role - fast analysis and routing"""
```

3. Add Scout to orchestrator:
```python
# In orchestrator_with_elisya.py
valid_agent_types.append("Scout")
```

4. Add Scout to LangGraph:
```python
# In langgraph_builder.py
builder.add_node("scout", self.nodes.scout_node)
```

### Issue 2: Hostess Router DISABLED
**Severity**: MEDIUM
**Impact**: No intelligent message routing without explicit @mentions

The comment at line 690-692 explicitly disables Hostess:
```python
# Phase 57.8.2: REMOVED Hostess routing - она слишком медленная для роутинга
# Hostess теперь только для: камера, навигация, context awareness
# Вместо этого полагаемся на select_responding_agents + agent-to-agent @mentions
```

**Consequence**:
- User must @mention agents explicitly OR use /solo, /team, /round
- No smart routing decision like "this looks like a design task → send to @Architect"
- Fall back to keyword matching in select_responding_agents()

### Issue 3: No Verification That Scout Works in Group Chat
**Severity**: MEDIUM
**Impact**: Scout role may fail when actually implemented

Current test coverage:
- test_scout_audit.py exists but tests Scout as auditor
- No test for Scout in group chat context
- No test for Scout → Dev → QA chain in LangGraph

Need:
```python
# Test: Can Scout mention Dev?
# Test: Does Dev get Scout context?
# Test: Can chain continue to QA?
```

### Issue 4: Artifact Application Blocked by QA Review
**Severity**: LOW (by design, but limiting)
**Impact**: No auto-implementation, requires manual approval

Phase 103.6 stages artifacts but doesn't apply them. Flow:
1. Dev generates code → staged
2. QA reviews → scored
3. BLOCKED: Human approval needed for disk write

Cannot be fully automated without approval_service integration.

---

## Current Working Workflow (What ACTUALLY Works)

✅ **THIS WORKS**:
```
User sends message → Hostess analyzes (DISABLED) OR keyword match
→ Selects PM/Dev/QA/Architect
→ Agent responds with @mention of next agent
→ Next agent added to queue dynamically
→ Chain continues: PM → Dev → @QA → end

Example:
User: "Build a REST API"
→ keyword match → PM selected
→ PM: "I'll design this. @Architect please create architecture"
→ Architect added to queue
→ Architect: "@Dev implement according to spec"
→ Dev added to queue
→ Dev generates code → staged
```

✅ **Agent-to-Agent Calling Works**:
- Any agent can @mention any other agent in response
- Mentioned agent is added to response queue
- Full context passed via ChainContext

❌ **Scout Workflow BLOCKED**:
- Scout role doesn't exist
- Cannot be @mentioned
- Cannot trigger workflows

---

## Summary

### Green Lights (✅)
- Multi-agent group chat framework is **COMPLETE**
- Agent-to-agent @mention routing **WORKS**
- LangGraph orchestration **EXISTS** and working
- Artifact staging pipeline **IMPLEMENTED**
- Smart reply system **OPERATIONAL**
- Elisya context integration **ACTIVE**

### Red Lights (❌)
- Scout role **NOT DEFINED** - must be created
- Hostess routing **DISABLED** - needs re-enabling or replacement
- Scout → Dev → QA workflow **NOT IMPLEMENTED** - Scout missing
- No auto-artifact application **BY DESIGN** - blocks automation

### Recommendation
To enable full Scout-led team workflows:

1. **Priority 1**: Define Scout role + add to agents
2. **Priority 2**: Re-enable Hostess or enhance select_responding_agents()
3. **Priority 3**: Integrate approval_service for artifact auto-application
4. **Priority 4**: Add comprehensive tests for multi-agent chains

Current state: **80% complete** - only missing Scout implementation.

---

## Key Files Reference

### Group Chat System
- `/src/services/group_chat_manager.py` - GroupChatManager, GroupRole, GroupParticipant
- `/src/api/handlers/group_message_handler.py` - Socket.IO message handling (1200 lines)
- `/src/api/routes/group_routes.py` - REST API endpoints

### Agent Orchestration
- `/src/orchestration/orchestrator_with_elisya.py` - call_agent() method (114KB)
- `/src/agents/role_prompts.py` - System prompts for each role
- `/src/agents/__init__.py` - Agent implementations

### LangGraph Workflow
- `/src/orchestration/langgraph_builder.py` - Graph definition
- `/src/orchestration/langgraph_nodes.py` - Node implementations (1100 lines)
- `/src/orchestration/langgraph_state.py` - State schema

### Artifact Pipeline
- `/src/utils/artifact_extractor.py` - Extract artifacts from responses
- `/src/utils/staging_utils.py` - Stage artifacts for review
- `/src/services/disk_artifact_service.py` - Persist to disk

### Intelligent Routing
- `/src/services/group_chat_manager.py:select_responding_agents()` - Lines 179-418
- Smart reply decay: Lines 275-302
- Keyword matching for agent selection

---

## Code Examples

### Agent-to-Agent @Mention Detection
```python
# src/api/handlers/group_message_handler.py:1030-1086
agent_mentions = re.findall(r'@(\w+)', response_text)
if agent_mentions:
    for mentioned_name in agent_mentions:
        if mentioned_name.lower() == display_name.lower():
            continue  # Skip self-mention

        # Find mentioned agent in participants
        for pid, pdata in group.get("participants", {}).items():
            if pdata.get("display_name", "").lower() == mentioned_name.lower():
                mentioned_participant = pdata
                break

        if mentioned_participant and mentioned_participant.get("role") != "observer":
            # Check if already queued
            already_queued = any(
                p.get("agent_id") == mentioned_participant.get("agent_id")
                for p in participants_to_respond
            )
            if not already_queued:
                participants_to_respond.append(mentioned_participant)
```

### Smart Reply with Decay
```python
# src/services/group_chat_manager.py:278-302
if is_agent_sender and group and group.last_responder_id and group.last_responder_decay < 2:
    # MCP agent can trigger AI agent continuation
    for pid, p in participants.items():
        agent_id = p.get('agent_id', '').lower().lstrip('@')
        if agent_id == group.last_responder_id.lower().lstrip('@'):
            if p.get('role') != 'observer' and p.get('agent_id') != sender_id:
                return [p]  # Enable MCP→Agent chain
```

### Artifact Staging
```python
# src/api/handlers/group_message_handler.py:955-994
artifacts = extract_artifacts(response_text, display_name)
if artifacts:
    qa_score = extract_qa_score(response_text) or 0.5
    staged_ids = stage_artifacts_batch(
        artifacts=artifacts,
        qa_score=qa_score,
        agent=display_name,
        group_id=group_id,
        source_message_id=user_message.id
    )
```
