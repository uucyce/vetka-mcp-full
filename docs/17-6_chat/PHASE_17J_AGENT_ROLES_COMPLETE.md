# Phase 17-J: Agent Role Prompts + Artifact Fix - Complete

**Date:** 2025-12-27
**Status:** COMPLETE
**Author:** Claude Opus 4.5

---

## Summary

Implemented role-specific prompts for PM, Dev, QA agents with chain context passing. Dev now creates artifacts (code blocks) that are extracted and emitted to frontend.

---

## Changes Made

### New Files

| File | Lines | Purpose |
|------|-------|---------|
| `src/agents/role_prompts.py` | ~220 | Role-specific system prompts for PM, Dev, QA |
| `src/utils/artifact_extractor.py` | ~200 | Extract code artifacts from agent responses |

### Modified Files

| File | Lines Changed | Description |
|------|---------------|-------------|
| `main.py` | 373-400 | Added imports for role_prompts and artifact_extractor |
| `main.py` | 1108-1126 | Updated `get_agents()` to use new role prompts |
| `main.py` | 2962-3068 | Rewrote agent call loop with chain context |
| `main.py` | 3106-3123 | Added artifact emit to Socket.IO |

---

## Agent Behaviors

### Before (Problem)

| Agent | Behavior | Issue |
|-------|----------|-------|
| PM | Generic analysis | No task decomposition |
| Dev | Generic analysis | No code output |
| QA | Generic analysis | No scoring |
| All | Same prompt style | No chain awareness |

### After (Fixed)

| Agent | Role | Output Format |
|-------|------|---------------|
| PM | Analyze, decompose | Tasks for Dev, Acceptance Criteria, Risks |
| Dev | Write code | Complete code blocks with `### File:` headers |
| QA | Review, score | Checklist, Issues, SCORE: X.X/1.0, Verdict |

---

## Chain Context Flow

```
User: "напиши функцию сортировки"
         │
         ▼
┌─────────────────────────────────────────────────┐
│  PM (first in chain)                            │
│  Context: "You are FIRST in chain PM→Dev→QA"   │
│  Output: "Tasks for Dev:                        │
│           1. Create sort_list() function        │
│           2. Handle empty list edge case..."    │
└─────────────────────────────────────────────────┘
         │
         │ previous_outputs['PM'] = pm_response
         ▼
┌─────────────────────────────────────────────────┐
│  Dev (second in chain)                          │
│  Context: "PM's ANALYSIS AND TASKS:             │
│            [PM's full output here]"             │
│  Output: "### File: sorter.py                   │
│           ```python                             │
│           def sort_list(items):                 │
│               return sorted(items)              │
│           ```"                                  │
└─────────────────────────────────────────────────┘
         │
         │ previous_outputs['Dev'] = dev_response
         │ artifacts = extract_artifacts(dev_response)
         ▼
┌─────────────────────────────────────────────────┐
│  QA (third in chain)                            │
│  Context: "DEV's CODE:                          │
│            [Dev's full output here]"            │
│  Output: "## Code Review                        │
│           [x] Syntax correct                    │
│           [ ] Edge case: empty list             │
│           SCORE: 0.75/1.0                       │
│           Verdict: ACCEPT"                      │
└─────────────────────────────────────────────────┘
         │
         ▼
    emit('artifact_created', {...})
```

---

## Key Code Changes

### 1. Role Prompts (src/agents/role_prompts.py)

```python
PM_SYSTEM_PROMPT = """You are PM in the VETKA AI team.
## YOUR ROLE
- Analyze user requests and break them into CONCRETE tasks
- Create clear specifications for Dev agent
...
## OUTPUT FORMAT
## Tasks for Dev
1. [Specific task with file names]
..."""

DEV_SYSTEM_PROMPT = """You are Dev in the VETKA AI team.
...
## OUTPUT FORMAT
### File: [filename.py]
```python
# Complete code here
```
..."""

QA_SYSTEM_PROMPT = """You are QA in the VETKA AI team.
...
## OUTPUT FORMAT
## SCORE: X.X/1.0
### Verdict: ACCEPT/REFINE/REJECT
..."""
```

### 2. Chain Context (src/agents/role_prompts.py)

```python
def get_chain_context(agent_type, previous_outputs, user_task):
    if agent_type == "Dev":
        pm_output = previous_outputs.get('PM', '')
        return f"""
## CHAIN CONTEXT
PM has analyzed the request and created tasks for you.

## PM's ANALYSIS AND TASKS
{pm_output}
"""
```

### 3. Artifact Extraction (src/utils/artifact_extractor.py)

```python
def extract_artifacts(agent_output, agent_name):
    """Extract ```python code blocks with optional ### File: headers"""
    # Pattern: ### File: name.py\n```python\ncode\n```
    file_pattern = r'(?:###?\s*)?(?:File|Файл):\s*`?([^\n`]+)`?\n```(\w+)\n(.*?)```'
    ...
    return artifacts  # [{id, filename, language, content, lines}]
```

### 4. Main.py Agent Loop

```python
# Track previous outputs for chain context
previous_outputs = {}
all_artifacts = []

for agent_name in agents_to_call:
    # Build prompt with chain context
    full_prompt = build_full_prompt(
        agent_type=agent_name,
        user_message=text,
        file_context=context_for_llm,
        previous_outputs=previous_outputs
    )

    response_text = agent_instance.call_llm(prompt=full_prompt, ...)

    # Save for next agent
    previous_outputs[agent_name] = response_text

    # Extract artifacts from Dev
    if agent_name == 'Dev':
        artifacts = extract_artifacts(response_text, agent_name)
        all_artifacts.extend(artifacts)

# Emit artifacts to frontend
for artifact in all_artifacts:
    emit('artifact_created', {...})
```

---

## Test Results

```
=== Testing Role Prompts ===
PM prompt length: 876 chars
Contains "Tasks for Dev": True
Dev prompt length: 940 chars
Contains "code blocks": True
QA prompt length: 1084 chars
Contains "SCORE": True

=== Testing Chain Context ===
PM context mentions FIRST: True
Dev context contains PM output: True
QA context contains Dev output: True

=== Testing Artifact Extractor ===
Extracted artifacts: 2
  - calculator.py (2 lines)
  - test_calc.py (2 lines)
QA Score: 0.85, Verdict: ACCEPT

All tests passed!
```

---

## Socket.IO Events

### Existing: `agent_message`
```json
{
    "agent": "Dev",
    "model": "deepseek",
    "text": "### File: sorter.py\n```python\n...",
    "response_type": "code"
}
```

### New: `artifact_created`
```json
{
    "id": "uuid",
    "type": "code",
    "filename": "sorter.py",
    "language": "python",
    "content": "def sort_list(items):\n    return sorted(items)",
    "lines": 2,
    "agent": "Dev",
    "created_at": "2025-12-27T...",
    "node_path": "/project/src"
}
```

---

## Frontend Integration

The frontend should listen for `artifact_created`:

```javascript
socket.on('artifact_created', function(artifact) {
    console.log('[ARTIFACT] Received:', artifact.filename);

    // Add artifact button to last message
    const btn = document.createElement('button');
    btn.className = 'artifact-btn';
    btn.textContent = `📄 ${artifact.filename} (${artifact.lines} lines)`;
    btn.onclick = () => showArtifactModal(artifact);

    // Append to Dev message
    document.querySelector('.agent-message:last-child')?.appendChild(btn);
});
```

---

## Verification Commands

### 1. Check imports work
```bash
python -c "from src.agents.role_prompts import get_agent_prompt; print('OK')"
python -c "from src.utils.artifact_extractor import extract_artifacts; print('OK')"
```

### 2. Check main.py syntax
```bash
python -m py_compile main.py
```

### 3. Watch server logs for chain context
```
[Agent] PM: Using Phase 17-J chain-aware prompt
[Agent] PM: ✅ Generated 500 chars
[Agent] Dev: Using Phase 17-J chain-aware prompt
[Agent] Dev: ✅ Generated 1200 chars
[Agent] Dev: 📦 Extracted 2 artifact(s)
         → sorter.py (15 lines)
         → test_sorter.py (10 lines)
[Agent] QA: Using Phase 17-J chain-aware prompt
[Agent] QA: ✅ Generated 400 chars
[Agent] QA: ⭐ Score: 0.85/1.0, Verdict: ACCEPT
[SOCKET] 📦 Emitting 2 artifact(s)...
```

---

## Files Summary

| Component | File | Status |
|-----------|------|--------|
| Role Prompts | `src/agents/role_prompts.py` | NEW |
| Artifact Extractor | `src/utils/artifact_extractor.py` | NEW |
| Main Integration | `main.py` | MODIFIED |
| Agent Classes | `src/agents/vetka_*.py` | UNCHANGED |
| Orchestrator | `src/orchestration/orchestrator_with_elisya.py` | UNCHANGED |

---

## Next Steps

- [ ] Update frontend to display artifact modal
- [ ] Add syntax highlighting for code artifacts (highlight.js)
- [ ] Persist artifacts to tree node metadata
- [ ] Add "Copy code" button to artifacts
- [ ] Consider streaming artifacts for large code blocks

---

## Conclusion

Phase 17-J successfully implements:

1. **Role-specific prompts** - Each agent has clear responsibilities
2. **Chain context passing** - PM→Dev→QA with full context
3. **Artifact extraction** - Code blocks parsed and emitted
4. **QA scoring** - Numeric scores extracted from QA output

The agent chain now produces differentiated, useful output instead of generic analysis.
