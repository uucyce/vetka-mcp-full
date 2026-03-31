# Recon: Local Task Decomposer
**Date:** 2026-03-29 | **Author:** Zeta
**Phase:** 201 / 177_MCC_local

## Problem
Local models (7b-8b) can't handle complex tasks (high complexity, multi-file, architecture decisions). But they CAN handle atomic sub-tasks (1 file, 10-30 lines, clear contract). Missing piece: automatic decomposition of big tasks into small ones — entirely locally, no cloud API.

## Key Insight
Localguys pipeline already does steps `recon` (facts.json) and `plan` (plan.json). The plan contains `steps` and `files_to_modify` — this IS a decomposition. We just need to materialize it into real task board sub-tasks instead of executing the plan monolithically.

## Design

### New workflow: `decompose_localguys`
```
recon → plan → decompose → (done)
```

The `decompose` step:
1. Reads `plan.json` from previous step
2. For each step in plan, creates a child task on task board:
   - title: step description
   - allowed_tools: ["local_ollama"]
   - allowed_paths: [file from plan]
   - complexity: low
   - parent_task_id: original task
   - implementation_hints: step detail from plan
3. Original task status → "decomposed" (new status or tag)

### Flow
```
Commander/Human creates task:
  "Add multicam sync to timeline" (high, build)
         ↓
localguys_executor.py --task tb_XXX --method decompose
         ↓
    Step 1: recon (qwen2.5:7b, 8s)
      → facts.json: affected files, scope, risks
         ↓
    Step 2: plan (qwen3:8b, 18s)
      → plan.json: {
          "approach": "Add sync infrastructure in 3 layers",
          "steps": [
            {"description": "Add sync_offset to MediaClip", "file": "src/models/clip.py"},
            {"description": "Write cross_correlate()", "file": "src/services/audio_sync.py"},
            {"description": "Add Sync button to timeline", "file": "client/src/components/..."}
          ]
        }
         ↓
    Step 3: decompose (no LLM — pure code)
      → Creates 3 tasks on task board via REST:
        tb_child_1: "Add sync_offset to MediaClip" (low, local_ollama)
        tb_child_2: "Write cross_correlate()" (low, local_ollama)
        tb_child_3: "Add Sync button to timeline" (low, local_ollama)
         ↓
    Original task tagged: decomposed, children: [tb_child_1, tb_child_2, tb_child_3]
         ↓
Each child picked up by localguys executor (g3 method)
  → recon → plan → execute → verify → review → finalize
  → 2-3 min per child, all local, all autonomous
```

### Prompt for plan step (decomposition-optimized)
```
You are a task decomposer. Break this task into atomic sub-tasks.
Each sub-task must:
- Touch exactly 1 file
- Be completable in under 50 lines of code
- Have a clear, testable outcome
- Be independent (no ordering dependencies if possible)

Produce plan.json with:
- "approach": 1-2 sentence strategy
- "steps": list of objects, each with:
  - "description": what to do (imperative, specific)
  - "file": exact file path to modify
  - "complexity": "low" or "medium"
  - "test_hint": how to verify this sub-task

Task: {title}
Description: {description}
Known files: {allowed_paths}
Recon facts: {facts.json}
```

### Child task template
```python
{
    "title": f"[AUTO] {step['description']}",
    "description": f"Sub-task of {parent_task_id}. {step['description']}",
    "phase_type": parent.phase_type,  # inherit
    "priority": parent.priority,
    "complexity": "low",
    "project_id": parent.project_id,
    "allowed_tools": ["local_ollama"],
    "allowed_paths": [step["file"]],
    "parent_task_id": parent_task_id,
    "implementation_hints": step.get("test_hint", ""),
    "tags": ["auto-decomposed", "local-ready"],
}
```

## What this enables

### Without decomposer (current)
- Complex task → local model tries → garbage output or partial solution
- 7b models can't reason about multi-file changes

### With decomposer
- Complex task → 3-5 atomic tasks → each solved by local model in 2 min
- Total: 10-15 min for a complex task, fully autonomous, zero API calls
- Failed sub-task → re-run just that one, not the whole thing

## Implementation

One new file: extend `localguys_executor.py` with:
1. `decompose` step handler (parses plan.json → creates tasks via REST)
2. New prompt template optimized for decomposition
3. Parent-child task linking

~100 lines of new code. No new dependencies.

## Risks
1. qwen3:8b plan quality — may produce vague steps. Mitigation: prompt engineering, require "file" field
2. Too many sub-tasks — cap at 7 per decomposition
3. Circular decomposition — never decompose an already-decomposed task (check tags)
