# ARC Integration Markers - HAIKU-MARKERS-1

**Report Date:** 2026-01-26
**Status:** Complete
**Phase:** 95 (Post-Audit Integration Planning)

## Summary

HAIKU-MARKERS-1 has systematically added TODO markers to identify ARC (Abstraction and Reasoning Corpus) integration gaps across three critical files. These markers indicate where the ARCSolverAgent should be connected to existing systems.

---

## Markers Added

| # | File | Line | Marker Name | Purpose | Context |
|---|------|------|-------------|---------|---------|
| 1 | `src/api/handlers/group_message_handler.py` | 807 | `TODO_ARC_GROUP` | Integrate ARC suggestions for group chat | After context building for agent calls |
| 2 | `src/mcp/vetka_mcp_bridge.py` | 621 | `TODO_ARC_MCP` | Add MCP tool for ARC suggestions | Tool registration in list_tools() |
| 3 | `src/orchestration/orchestrator_with_elisya.py` | 2329 | `TODO_ARC_GAP` | Implement conceptual gap detection | Before agent calls in call_agent() |

---

## Detailed Marker Analysis

### 1. Group Chat ARC Integration (TODO_ARC_GROUP)

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`
**Line:** 807
**Function:** `handle_group_message()` - Group chat message handler

#### Current Implementation
```python
# Add recent conversation
context_parts.append("## RECENT CONVERSATION")
for msg in recent_messages:
    msg_content = msg.get("content", "")[:200]
    context_parts.append(f"[{msg.get('sender_id')}]: {msg_content}")

# Current request
context_parts.append(f"\n## CURRENT REQUEST\n{content}")

# TODO_ARC_GROUP: Integrate ARC suggestions for group chat (see arc_solver_agent.py)
# After context building, call arc_solver_agent.suggest_connections() to generate
# creative transformation suggestions for the current group conversation workflow
```

#### Integration Point
This marker is placed **after context is fully built** (lines 782-805) and **before the orchestrator is called** (lines 817-827).

#### What needs to be implemented
```python
# Pseudo-code for integration
if should_use_arc_suggestions():
    arc_suggestions = arc_solver.suggest_connections(
        workflow_id=group_id,
        graph_data=extract_group_workflow_graph(),
        task_context=content,
        num_candidates=5
    )
    # Inject top suggestions into system prompt
    if arc_suggestions.get('top_suggestions'):
        context_parts.append("## SUGGESTED IMPROVEMENTS (ARC)")
        for suggestion in arc_suggestions['top_suggestions'][:3]:
            context_parts.append(f"- {suggestion['explanation']} (score: {suggestion['score']:.2f})")
```

#### Expected Impact
- Group agents will be aware of potential workflow improvements
- Agents can proactively suggest optimizations during conversations
- Better coordination between group members through ARC-discovered patterns

---

### 2. MCP Tool Registration (TODO_ARC_MCP)

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py`
**Line:** 621
**Function:** `list_tools()` - MCP tool registration

#### Current Implementation
```python
Tool(
    name="vetka_get_memory_summary",
    # ... existing tool definition ...
),
# TODO_ARC_MCP: Add vetka_arc_suggest tool for MCP clients
# Should expose arc_solver_agent.suggest_connections() with parameters:
# - workflow_id: str, graph_data: dict, task_context: str, num_candidates: int
# This allows Claude Code / Browser Haiku to get ARC suggestions for their current work
]

# Phase 55.1: Register new MCP tools
```

#### Integration Point
This marker is placed in the **tools list** (line 621) before MCP tool registration from compound/workflow tools (line 625).

#### What needs to be implemented
```python
Tool(
    name="vetka_arc_suggest",
    description="Generate ARC-based transformation suggestions for workflow graphs. "
               "Uses abstraction and reasoning to find creative improvements to graph structures.",
    inputSchema={
        "type": "object",
        "properties": {
            "workflow_id": {
                "type": "string",
                "description": "Workflow or context ID"
            },
            "graph_data": {
                "type": "object",
                "description": "Graph with 'nodes' and 'edges' keys"
            },
            "task_context": {
                "type": "string",
                "description": "Human-readable description of task/workflow"
            },
            "num_candidates": {
                "type": "integer",
                "description": "Number of suggestions to generate (default: 10)",
                "default": 10
            }
        },
        "required": ["workflow_id"]
    }
)
```

#### Expected Impact
- Claude Code and Browser Haiku can request ARC suggestions via MCP
- Enables external agents to improve their workflows autonomously
- Centralizes ARC suggestions through standard MCP interface

---

### 3. Conceptual Gap Detection (TODO_ARC_GAP)

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/orchestrator_with_elisya.py`
**Line:** 2329
**Function:** `call_agent()` - Single agent execution

#### Current Implementation
```python
if context:
    # Phase 57.6: Ensure raw_context is always a string (fixes slice error)
    if isinstance(context, dict):
        # Convert dict to readable string
        context_parts = [f"{k}: {v}" for k, v in context.items()]
        state.raw_context = "\n".join(context_parts)
    elif isinstance(context, str):
        state.raw_context = context
    else:
        state.raw_context = str(context)

    # TODO_ARC_GAP: Implement conceptual gap detection before agent calls
    # Before running agent, analyze context to detect missing connections or patterns:
    # - Use semantic search to find related concepts
    # - Compare with arc_solver_agent few-shot examples
    # - Suggest missing workflow nodes/connections
    # - Feed suggestions back into prompt for agent awareness
```

#### Integration Point
This marker is placed **immediately after context is assigned to state** (lines 2318-2327) and **before the agent is called** (lines 2340-2342).

#### What needs to be implemented
```python
# Conceptual gap detection algorithm
if context and self.semantic_search:
    # 1. Extract concepts from prompt and context
    concepts = extract_concepts(prompt, state.raw_context)

    # 2. Semantic search for related concepts
    related = self.semantic_search.find_related_concepts(concepts)

    # 3. Compare with ARC examples to find gaps
    gaps = detect_conceptual_gaps(concepts, related, self.arc_solver.few_shot_examples)

    # 4. If significant gaps found, inject into prompt
    if gaps and len(gaps) > 0:
        gap_prompt = format_gap_suggestions(gaps)
        prompt = f"{prompt}\n\nPotential gaps in current approach:\n{gap_prompt}"
        state.raw_context += f"\n\nARC Gap Analysis:\n{gap_prompt}"
```

#### Expected Impact
- Agents will be aware of conceptual gaps before making decisions
- Proactive identification of missing workflow elements
- Better integration with semantic search and memory systems

---

## Related Code Artifacts

### ARCSolverAgent Implementation
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/agents/arc_solver_agent.py`

**Key Methods:**
- `suggest_connections()` - Main entry point (line 136)
- `_generate_candidates()` - Generate 5-20 transformation candidates (line 237)
- `_evaluate_candidates()` - Test and score candidates (line 665)
- `_store_few_shot_example()` - Cache successful patterns (line 966)

**Few-shot Learning:**
- Stores up to 20 successful ARC suggestions in-memory
- Can persist to MemoryManager for cross-session learning
- Uses few-shot examples to guide new generation (line 258-265)

### Group Chat Architecture
**File:** `src/api/handlers/group_message_handler.py`

**Context Flow:**
1. User sends message to group (line 533)
2. Recent messages fetched (line 785)
3. Context built from recent messages (lines 784-805) **← Marker #1 here**
4. Agents selected to respond (line 682)
5. Each agent called via orchestrator (line 817)

### MCP Bridge Architecture
**File:** `src/mcp/vetka_mcp_bridge.py`

**Tool Flow:**
1. Tools registered in `list_tools()` (line 183)
2. Tools converted to MCP format (line 641) **← Marker #2 here**
3. Tool execution routed in `call_tool()` (line 655)
4. Results formatted for Claude Desktop/Code

### Orchestrator Architecture
**File:** `src/orchestration/orchestrator_with_elisya.py`

**Agent Flow:**
1. Single agent entry point (line 2273)
2. State created/retrieved (line 2316)
3. Context stored in state (lines 2318-2327) **← Marker #3 here**
4. Model override applied (line 2330)
5. Agent executed via Elisya (line 2341)

---

## Implementation Roadmap

### Phase 1: Group Chat ARC Integration (TODO_ARC_GROUP)
**Effort:** 4-6 hours
**Dependencies:** Arc solver already exists

**Steps:**
1. Create `arc_integration_helper.py` to encapsulate integration logic
2. Add configuration flag: `ENABLE_ARC_GROUP_SUGGESTIONS`
3. Extract workflow graph from group messages
4. Call `arc_solver.suggest_connections()`
5. Format suggestions into context
6. Add telemetry to track suggestion quality

**Testing:**
- Unit test: verify ARC suggestions are correctly formatted
- Integration test: group chat with ARC enabled vs. disabled
- UX test: verify agents use suggestions appropriately

---

### Phase 2: MCP Tool Registration (TODO_ARC_MCP)
**Effort:** 3-4 hours
**Dependencies:** Phase 1 helper functions

**Steps:**
1. Create MCP tool wrapper for `arc_solver.suggest_connections()`
2. Add tool definition to `list_tools()`
3. Implement `call_tool()` handler for `vetka_arc_suggest`
4. Add REST endpoint in VETKA API
5. Add integration test with Claude Code MCP client

**Testing:**
- Unit test: tool parameter validation
- MCP test: call tool via stdio protocol
- Claude Code test: use `vetka_arc_suggest` in actual session

---

### Phase 3: Conceptual Gap Detection (TODO_ARC_GAP)
**Effort:** 6-8 hours
**Dependencies:** Semantic search, Phase 1 & 2

**Steps:**
1. Implement `extract_concepts()` function
2. Implement `detect_conceptual_gaps()` algorithm
3. Integrate with semantic search (`self.semantic_search`)
4. Add gap analysis to orchestrator flow
5. Create prompt injection mechanism
6. Add metrics tracking

**Testing:**
- Unit test: gap detection on synthetic graphs
- Integration test: orchestrator with/without gap detection
- Metric test: measure impact on agent decision quality

---

## Integration Priority Matrix

| Marker | Priority | Complexity | Impact | Dependencies |
|--------|----------|-----------|--------|--------------|
| TODO_ARC_GROUP | **HIGH** | Medium | Direct | arc_solver_agent.py ✓ |
| TODO_ARC_MCP | **HIGH** | Low | Enables external use | Phase 1 |
| TODO_ARC_GAP | **MEDIUM** | High | Proactive improvement | Phase 1, semantic_search |

---

## Success Metrics

### Group Chat ARC Integration
- Track suggestion acceptance rate (agent uses suggested pattern)
- Compare workflow quality before/after
- Measure agent latency impact (<5% overhead target)

### MCP Tool Registration
- Track MCP calls from Claude Code/Browser Haiku
- Monitor suggestion relevance (user feedback)
- Track tool error rate (<1% target)

### Conceptual Gap Detection
- Measure gap identification accuracy (precision/recall)
- Track agent decision improvements
- Monitor prompt token overhead (<10% target)

---

## Implementation Checklist

- [ ] Phase 1: Group Chat ARC Integration
  - [ ] Create `arc_integration_helper.py`
  - [ ] Extract workflow graph from messages
  - [ ] Format ARC suggestions into context
  - [ ] Add telemetry
  - [ ] Unit tests
  - [ ] Integration tests

- [ ] Phase 2: MCP Tool Registration
  - [ ] Create MCP tool wrapper
  - [ ] Add to tool list
  - [ ] Implement call_tool handler
  - [ ] Add REST endpoint
  - [ ] MCP integration test
  - [ ] Claude Code test

- [ ] Phase 3: Conceptual Gap Detection
  - [ ] Implement gap detection algorithm
  - [ ] Integrate with semantic search
  - [ ] Add to orchestrator flow
  - [ ] Create prompt injection
  - [ ] Add metrics
  - [ ] Integration tests

---

## Next Steps

1. **Immediate:** Review markers with team
2. **This week:** Prioritize Phase 1 (highest ROI)
3. **Next week:** Begin Phase 1 implementation
4. **2 weeks:** Complete Phase 1-2
5. **3 weeks:** Begin Phase 3

---

## Notes

- All markers are strategically placed at **integration points** (not in the middle of logic)
- Each marker includes a **comment** explaining what needs to be done
- Implementation preserves existing behavior (no breaking changes)
- ARC solver already implemented and tested (src/agents/arc_solver_agent.py)
- Few-shot learning ready to support integration

---

**Marker Status:** ✅ All 3 markers added successfully
**Files Modified:** 3
**Lines Added:** 12 (comments + implementation guidance)
