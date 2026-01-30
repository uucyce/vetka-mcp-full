# Phase 94: Agent Workflow in VETKA

**Agent:** Haiku 5
**Date:** 2026-01-26
**Status:** DETAILED - Parallel execution exists, gaps in inter-task communication

---

## 1. CURRENT WORKFLOW ARCHITECTURE

### Orchestration Engine:
**Path:** `src/orchestration/orchestrator_with_elisya.py`
**Lines:** ~800
**Purpose:** Route requests to appropriate models/agents

---

## 2. EXISTING AGENT TYPES

| Agent | Path | Role |
|-------|------|------|
| Hostess | `src/agents/hostess_agent.py` | UI greeter, task router |
| QwenLearner | `src/agents/qwen_learner.py` | Code analysis |
| PixtralLearner | `src/agents/pixtral_learner.py` | Vision tasks |
| BaseAgent | `src/agents/base_agent.py` | Abstract base class |

---

## 3. PARALLEL EXECUTION CAPABILITY

### Group Chat Parallel (WORKING):
```python
# src/services/group_chat_manager.py

async def broadcast_to_group(message, group_id):
    members = get_group_members(group_id)

    # Parallel execution
    tasks = [
        call_model(member.model_id, message)
        for member in members
    ]

    responses = await asyncio.gather(*tasks, return_exceptions=True)
    return responses
```

### Evidence of Parallel:
- Group chats with multiple models work
- asyncio.gather used for concurrent calls
- Exception handling per-task

---

## 4. CAM TREE INTEGRATION

### Constructivist Agentic Memory:
**Path:** `src/orchestration/cam_engine.py`
**Purpose:** Track artifacts created/modified by agents

### CAM Node Structure:
```json
{
  "id": "node_abc123",
  "type": "file",
  "path": "/src/memory/engram.py",
  "created_by": "dev_agent_1",
  "created_at": 1737892800,
  "parent": "node_parent",
  "children": [],
  "metadata": {
    "lines_added": 45,
    "lines_removed": 12,
    "phase": "94"
  }
}
```

### CAM Operations:
| Method | Purpose |
|--------|---------|
| `add_artifact()` | Register new file/change |
| `get_tree()` | Return full artifact tree |
| `get_by_agent()` | Filter by creator |
| `get_recent()` | Latest N artifacts |

---

## 5. PROPOSED WORKFLOW: PM → ARCHITECT → DEV → QA

### Current vs Proposed:

**Current Flow:**
```
User Request
    ↓
Hostess (route)
    ↓
Single Model (execute)
    ↓
Response
```

**Proposed Flow:**
```
User Request
    ↓
PM Agent (decompose task)
    ↓
Architect Agent (plan structure)
    ↓
┌─────────────────────────────────┐
│ Parallel Dev Pool               │
│ ┌─────┐ ┌─────┐ ┌─────┐        │
│ │Dev 1│ │Dev 2│ │Dev 3│        │
│ └──┬──┘ └──┬──┘ └──┬──┘        │
│    └───────┼───────┘            │
│            ↓                    │
│      Merge Results              │
└─────────────────────────────────┘
    ↓
QA Agent (verify)
    ↓
Response + Artifacts
```

---

## 6. MISSING COMPONENTS

### Gap 1: Inter-Task Communication
```
Problem: Parallel tasks can't share intermediate results
Missing: Shared state or message passing
Solution: Task queue with pub/sub (Redis or in-memory)
```

### Gap 2: Dependency Graph
```
Problem: No way to express "B depends on A"
Missing: DAG execution engine
Solution: Add dependency declarations to task definitions
```

### Gap 3: Result Merging
```
Problem: Multiple outputs need intelligent combination
Missing: Merge strategy per task type
Solution: Add merge agents (code merge, doc merge, etc.)
```

### Gap 4: Distributed State
```
Problem: Each agent has isolated context
Missing: Shared working memory
Solution: Redis or in-memory state store accessible to all agents
```

---

## 7. PROPOSED AGENT ROLES

### PM Agent:
```python
class PMAgent:
    """Decomposes user request into subtasks."""

    async def decompose(self, request: str) -> List[Task]:
        # Analyze request complexity
        # Identify parallel opportunities
        # Create task graph
        return tasks
```

### Architect Agent:
```python
class ArchitectAgent:
    """Plans implementation structure."""

    async def plan(self, tasks: List[Task]) -> Plan:
        # Identify files to modify
        # Design interfaces
        # Estimate dependencies
        return plan
```

### Dev Agent (Pool):
```python
class DevAgent:
    """Executes single implementation task."""

    async def implement(self, task: Task, plan: Plan) -> Artifact:
        # Read relevant files
        # Make changes
        # Register in CAM
        return artifact
```

### QA Agent:
```python
class QAAgent:
    """Verifies implementation."""

    async def verify(self, artifacts: List[Artifact]) -> Report:
        # Run tests
        # Check coverage
        # Validate against plan
        return report
```

---

## 8. HAIKU SWARM PATTERN

### For Reconnaissance Tasks:
```python
async def haiku_swarm(topics: List[str]) -> List[Report]:
    """Parallel Haiku research swarm."""

    tasks = [
        call_haiku(f"Research: {topic}")
        for topic in topics
    ]

    reports = await asyncio.gather(*tasks)

    # Save each report
    for i, report in enumerate(reports):
        save_to_file(f"docs/94_ph/HAIKU_{i+1}_{topics[i]}.md", report)

    return reports
```

### Benefits:
- Fast parallel research
- Cheap (Haiku is low-cost)
- Independent failures
- Easy to scale

---

## 9. IMPLEMENTATION PRIORITY

| Component | Effort | Impact | Priority |
|-----------|--------|--------|----------|
| Task Queue | Medium | High | 1 |
| PM Agent | Low | High | 2 |
| Haiku Swarm | Low | Medium | 3 |
| Dependency Graph | High | Medium | 4 |
| Merge Agents | Medium | Medium | 5 |

---

## SUMMARY

VETKA has PARALLEL EXECUTION capability via asyncio.gather in group chats. What's missing:
1. Inter-task communication (pub/sub)
2. Dependency graph execution
3. Intelligent result merging
4. Role-based agents (PM, Architect, Dev, QA)

The Haiku swarm pattern is ready to use immediately for reconnaissance tasks.

**Priority:** MEDIUM - Workflow improvements build on existing parallel infrastructure.
