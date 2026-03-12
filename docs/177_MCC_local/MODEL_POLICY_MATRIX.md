# PHASE 177 — localguys Model Policy Matrix

Date: 2026-03-12
Status: planning
Tag: `localguys`

## Purpose
This matrix defines how real local models participate in MCC workflows.
It is not only about capability labels; it is the operational policy layer used for role assignment, preprompt sizing, tool budget, and failure expectations.

## Source layers to merge
- `LLMModelRegistry` -> context length, speed, provider, source
- `ModelRegistry` -> local/cloud type and capabilities
- `reflex_decay` profiles -> FC reliability, max tools, schema simplicity preference

## Policy fields
- `model_id`
- `provider`
- `role_fit`
- `capabilities`
- `context_class`
- `latency_class`
- `tool_budget_class`
- `prompt_style`
- `risk_notes`
- `workflow_usage`

## Matrix

| model_id | role_fit | capabilities | prompt_style | tool_budget_class | workflow_usage |
|---|---|---|---|---|---|
| `qwen3:8b` | `coder` primary | code, chat, reasoning-lite | concise, file-scoped, action-first | medium | `g3_localguys` default coder |
| `qwen2.5:7b` | `coder` fallback | code, chat | strict narrow instructions | medium | alternate coder |
| `qwen2.5:3b` | cheap `coder` / support | code-lite, chat | tiny context, single-step instructions | low | budget mode only |
| `deepseek-r1:8b` | `verifier` primary | reasoning, review | structured critique, no open-ended planning | low-medium | G3 critic/verifier |
| `phi4-mini:latest` | router / cheap verifier | chat, compact reasoning | short deterministic prompts | low | fallback verifier/router |
| `qwen2.5vl:3b` | `scout` visual | vision, chat | screenshot-driven, compare-first | low | visual recon only |
| `embeddinggemma:300m` | retrieval only | embeddings | no agent prompting | n/a | search/index/memory |
| `gemma3:4b` | support/general | chat, light reasoning | simple prompts, small scope | low | optional helper only |
| `gemma3:12b` | heavier generalist | chat, reasoning-lite | bounded tasks only | medium | optional hybrid use |
| `mistral-nemo:latest` | general fallback | chat, broad text work | explicit contract, low autonomy | medium | docs/support fallback |

## Context classes
- `small`: <= 8k effective working context
- `medium`: 8k-32k effective working context
- `large`: > 32k effective working context

Initial assumptions for localguys:
- `qwen3:8b` -> `medium`
- `qwen2.5:7b` -> `medium`
- `deepseek-r1:8b` -> `medium`
- `phi4-mini:latest` -> `small`
- `qwen2.5vl:3b` -> `small`

## Latency classes
- `fast`: router/scout-level response speed
- `balanced`: acceptable for executor loop
- `slow`: only for gated review or non-interactive jobs

Initial assumptions:
- `phi4-mini:latest` -> `fast`
- `qwen2.5:3b` -> `fast`
- `qwen3:8b` -> `balanced`
- `qwen2.5:7b` -> `balanced`
- `deepseek-r1:8b` -> `balanced` leaning slow due to reasoning verbosity

## Prompt styles
### `coder_compact_v1`
For `qwen3:8b`, `qwen2.5:7b`
- file allowlist first
- expected output artifact first
- no long theory
- explicit step order
- must report concrete edits and verify commands

### `verifier_attack_v1`
For `deepseek-r1:8b`
- review diff and tests, not the whole universe
- mandatory verdict fields
- must emit blocking issues or pass
- capped iterations

### `router_tiny_v1`
For `phi4-mini:latest`
- classify only
- no large summaries
- single JSON output

### `visual_scout_v1`
For `qwen2.5vl:3b`
- visual diff / screenshot questions only
- no code patch ownership

## Tool budget classes
- `low`: 1-4 tool calls per step
- `medium`: 3-8 tool calls per step
- `high`: 6-12 tool calls per step

Initial mapping:
- `qwen3:8b` -> `medium`
- `qwen2.5:7b` -> `medium`
- `deepseek-r1:8b` -> `low-medium`
- `phi4-mini:latest` -> `low`
- `qwen2.5vl:3b` -> `low`

## Policy decisions
1. Local executor models must never run without playground lock.
2. Local verifier models must never be optional in `g3_localguys`.
3. Visual models do not own code patches.
4. Embedding models are not conversation agents.
5. Small models must receive shorter prompts and fewer tools, not just weaker expectations.

## Gaps to close in code
- map real Ollama IDs to explicit policy instead of fallback matching
- expose merged profile through MCC API
- include policy snapshot in workflow contract response
- record chosen policy in run artifacts and TaskBoard proof
