# Local Models Playbook For MYCELIUM

Date: 2026-03-13

Marker: `MARKER_173.P6.LOCAL_MODELS.PLAYBOOK`

Implementation markers: `MARKER_173.P6.MYCELIUM_LOCAL_PATCH_PRESET`, `MARKER_173.P6.MYCELIUM_LOCAL_OWNERSHIP_PRESET`

## Goal

Capture practical rules from the REFLEX + local Ollama/Qwen integration work and turn them into guidance that can be reused inside MYCELIUM workflows.

## What actually worked

1. Local Qwen can reliably do read-first repository work when the tool surface is small.
2. Local Qwen can claim task-board work when mutating actions are opt-in, not default.
3. Local Qwen can complete a live read -> edit -> test chain when:
   - the tool arguments are explicit,
   - the workflow is staged,
   - the tool set is narrow,
   - and the loop can inject a follow-up nudge after idle turns.
4. REFLEX helps most when it biases tool order and adds a compact system hint, not when it tries to replace the workflow.

## Hard lessons

### 1. Treat Ollama tool calls as native objects, not only dicts

Ollama returned native `ToolCall` objects in live runs. Any response filter that assumes only JSON dicts will silently drop valid tool calls.

Rule:
- normalize tool calls at the direct MCP boundary;
- only then run allowlist and safety checks.

### 2. Read-safe by default is correct

Local models should not see a broad write surface by default.

Rule:
- keep `task_board` read-only unless `_allow_task_board_writes=True`;
- keep `vetka_edit_file` blocked unless `_allow_edit_file_writes=True`;
- never expose recursive LLM tools to local models.

This prevents “tool curiosity” from turning into workspace damage.

### 3. Multi-turn loops need argument-shape normalization

The outward MCP result used normalized stringified tool arguments. For follow-up turns, Ollama expected assistant `tool_calls[].function.arguments` as dicts, not strings.

Rule:
- normalize outgoing tool calls for transport;
- rehydrate arguments back to dicts before feeding assistant tool-call messages into the next local-model turn.

### 4. Local models need narrower prompts and narrower tool sets

When the prompt is broad and the tool set is broad, local models drift toward meta-tools or orchestration tools.

Rule:
- for local FC, pass only the 2-4 tools needed for the current micro-step;
- describe the expected argument names in the prompt;
- if the target file is already known, do not offer discovery tools unless needed.

### 5. “One-shot autonomy” is weaker than staged autonomy

Local Qwen succeeded more reliably when the flow was:
- discover or read,
- then explicit follow-up,
- then mutate,
- then explicit verification.

Rule:
- in MYCELIUM, build local-model workflows as short state machines;
- do not expect one giant prompt to do search, edit, verify, and summarize in one shot.

### 6. Direct environment checks matter more than CLI assumptions

`ollama list` was not stable in this environment. The HTTP tags endpoint was stable.

Rule:
- prefer `http://127.0.0.1:11434/api/tags` for local model discovery;
- avoid shelling out to `ollama list` in production workflows unless strictly necessary.

### 7. Verification tools must use the same runtime as the active test environment

The built-in `RunTestsTool` called a Python binary that did not have `pytest` in this environment.

Rule:
- verification tools in MYCELIUM should use the active interpreter or explicit environment binding;
- do not assume `/usr/bin/python3` or a global `python3` matches the running agent environment.

## Recommended MYCELIUM pattern

### Tier A: Read-only local workflow

Use for:
- repo inspection,
- file reading,
- task lookup,
- workflow planning.

Allowed tools:
- `vetka_search_files`
- `vetka_read_file`
- `mycelium_task_board` read-only actions
- `select_best_local_qwen_model`

Behavior:
- REFLEX preflight
- schema filtering
- small tool set
- no write opt-ins

### Tier B: Controlled ownership workflow

Use for:
- claim a task,
- update ownership metadata,
- move work into “claimed” state.

Allowed tools:
- Tier A tools
- `mycelium_task_board` with `_allow_task_board_writes=True`

Behavior:
- ownership-only write surface
- explicit agent name and agent type in prompt
- closure via task state check

### Tier C: Patch workflow

Use for:
- tiny localized fixes,
- deterministic edits,
- targeted test reruns.

Allowed tools:
- `vetka_read_file`
- `vetka_edit_file` with `_allow_edit_file_writes=True`
- `vetka_run_tests`

Behavior:
- read target file
- read target test
- apply one patch
- run one targeted verification step
- stop

This should be implemented as a loop with idle nudges, not a single prompt.

## Recommended workflow contract for MYCELIUM

Each local-model workflow node should declare:

- `allowed_tools`
- `write_opt_ins`
- `expected_sequence`
- `verification_target`
- `max_turns`
- `idle_nudge_template`

Example:

```json
{
  "workflow": "local_patch_chain",
  "allowed_tools": ["vetka_read_file", "vetka_edit_file", "vetka_run_tests"],
  "write_opt_ins": {
    "edit_file": true,
    "task_board": false
  },
  "expected_sequence": ["vetka_read_file", "vetka_edit_file", "vetka_run_tests"],
  "verification_target": "targeted_pytest",
  "max_turns": 6
}
```

## What to instrument in MYCELIUM

At minimum, log:

- recommended tools from REFLEX;
- filtered tool schemas actually sent to the local model;
- returned tool calls before and after safety filtering;
- idle turns that required a nudge;
- final executed tool sequence;
- whether the verification step passed.

Without this, local-model failures look random even when they are structural.

## Migration recommendations

1. Port the direct REFLEX preflight helper into MYCELIUM local-model workflows as a first-class step.
2. Preserve safe-by-default surfaces; keep writes behind explicit workflow opt-ins.
3. Reuse the staged FC loop pattern for local models instead of single-pass orchestration prompts.
4. Normalize Ollama tool-call objects in every MYCELIUM boundary that touches local-model outputs.
5. Bind verification tools to the active runtime, not to a guessed system Python.

## Implementation status

The first concrete MYCELIUM presets from this playbook are `patchchain_localguys` and `ownership_localguys`.

They encode:
- the narrow direct tool surfaces for patching and task ownership,
- the required sequence for tiny patch loops,
- explicit task-board write opt-in for ownership-only flows,
- and the REFLEX preflight assumptions that made local Qwen reliable in live tests.

## Bottom line

Local models are usable in MYCELIUM, but only when the workflow is constrained.

They perform best as:
- deterministic readers,
- narrow-scope task owners,
- tiny patch executors,
- and targeted verifiers inside explicit workflow rails.

They perform badly when treated like unconstrained orchestration agents with a large tool surface.
