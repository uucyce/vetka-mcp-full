# PHASE 164 — P2 Trigger Matrix (2026-03-08)

Marker: `MARKER_164.P2.FULL_TRIGGER_MATRIX_FROM_UI_ATLAS.V1`
Window extension marker: `MARKER_164.P4.WINDOW_TRIGGER_MATRIX.ALL_MINI_WINDOWS.V1`

## Purpose
Deterministic mapping from MCC UI/runtime state to MYCO/Architect guidance state key.

## Trigger Matrix
| ID | Source event | Required state | Guidance state key | Expected next action |
|---|---|---|---|---|
| T1 | roadmap node select (task) | `nav=roadmap`, `nodeKind=task` | `roadmap.task.selected` | drill into workflow |
| T2 | roadmap node select (agent) | `nav=roadmap`, `nodeKind=agent`, `role=*` | `roadmap.agent.selected` | inspect Context + run/retry |
| T3 | enter workflow | `taskDrill=expanded OR workflowInline=true` | `workflow.open` | choose agent + execute |
| T4 | workflow agent select architect | `workflow.open`, `role=architect` | `workflow.agent.architect` | adjust subtasks/team profile |
| T5 | workflow agent select coder | `workflow.open`, `role=coder` | `workflow.agent.coder` | check model/prompt + run/retry |
| T6 | workflow agent select verifier/eval | `workflow.open`, `role in {verifier,eval}` | `workflow.agent.verifier` | run gate + send retry if fail |
| T7 | module unfold | `roadmapNodeDrill=expanded OR nodeInline=true` | `roadmap.module.unfold` | double-click deeper + create task |
| T8 | project no focus | `scope=project`, no node/task selected | `project.idle` | select node and continue |
| T9 | mini window focus: balance | `windowFocus=balance` | `window.balance.focused` | choose API key/provider/model scope |
| T10 | mini window focus: stats | `windowFocus=stats` | `window.stats.focused` | inspect diagnostics + reinforcement |
| T11 | mini window focus: tasks | `windowFocus=tasks` | `window.tasks.focused` | select task + start/stop/retry |
| T12 | mini window focus: context | `windowFocus=context` | `window.context.focused` | inspect node details/model prompt |
| T13 | mini window focus: chat | `windowFocus=chat` | `window.chat.focused` | ask architect or MYCO next action |

## Binding
- Frontend context producer: `MiniChat.tsx`
- Backend normalization: `chat_routes.py` -> `_normalize_guidance_context(...)`
- Shared packet resolver: `chat_routes.py` -> `_build_role_aware_instruction_packet(...)`
