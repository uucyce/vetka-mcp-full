# PHASE 164 — P4 Window Trigger Matrix Recon (2026-03-08)

Status: `RECON+markers` complete.

## Scope
Build deterministic MYCO trigger coverage for all MCC mini windows (non-DEV):
- `tasks`
- `chat`
- `context`
- `stats`
- `balance`

## Findings
1. Current trigger matrix covers `nav/node/drill/role` scenarios, but does not explicitly encode window focus priority.
2. `MiniContextPayload` currently has no `window_focus` field.
3. Top MYCO hint in MCC uses node/drill priority and can keep stale drill prompts when a window is actively open (for example Balance).
4. Backend quick guidance normalizer does not consume `window_focus`; architect/MYCO packet cannot branch on window-open intent.

## New Markers (Window Layer)
1. `MARKER_164.P4.WINDOW_TRIGGER_MATRIX.ALL_MINI_WINDOWS.V1`
2. `MARKER_164.P4.WINDOW_TRIGGER_PRIORITY.OVER_NODE_DRILL.V1`
3. `MARKER_164.P4.WINDOW_FOCUS_CONTEXT_PAYLOAD_BIND.V1`
4. `MARKER_164.P4.WINDOW_FOCUS_BACKEND_NORMALIZATION.V1`
5. `MARKER_164.P4.WINDOW_FOCUS_BALANCE_GUIDANCE.V1`
6. `MARKER_164.P4.WINDOW_FOCUS_STATS_GUIDANCE.V1`
7. `MARKER_164.P4.WINDOW_FOCUS_TASKS_GUIDANCE.V1`
8. `MARKER_164.P4.WINDOW_FOCUS_CONTEXT_GUIDANCE.V1`
9. `MARKER_164.P4.WINDOW_FOCUS_CHAT_GUIDANCE.V1`

## Window Trigger Matrix (Target)
| Window | Trigger source | State key | Top hint (short) | Chat quick guidance (detailed) |
|---|---|---|---|---|
| `balance` | focused/opened mini window | `window.balance.focused` | key/provider/model guidance | explain select key, favorite, provider scope, model bind |
| `stats` | focused/opened mini window | `window.stats.focused` | diagnostics/reinforcement guidance | explain runs/success/cost + TRM/reinforcement diagnostics |
| `tasks` | focused/opened mini window | `window.tasks.focused` | select/start/stop guidance | explain queue states, heartbeat, start/retry path |
| `context` | focused/opened mini window | `window.context.focused` | inspect model/prompt/file guidance | explain node details, role prompt, model edit flow |
| `chat` | focused/opened mini window | `window.chat.focused` | ask architect/MYCO next step | explain message routes (architect vs helper_myco) |

## Acceptance (for implementation step)
1. Any focused mini window has higher hint priority than pre-drill `Press Enter...`.
2. `window_focus` is present in frontend context payload and reaches `/api/chat/quick`.
3. Backend normalization includes `window_focus` and can alter next-action packet.
4. Balance-open scenario shows API key guidance instead of drill prompt.
