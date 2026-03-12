# PHASE 164 — P0 MYCO UI Action Catalog (2026-03-07)

Status: `IMPL NARROW` (doc-contract only)  
Marker: `MARKER_164.P0.MYCO_UI_ACTION_CATALOG.V1`

Purpose: deterministic mapping `UI element -> what it does -> what MYCO should say`.

## Action Contract Schema
For each UI element:
1. `intent`: purpose in operator flow
2. `prerequisites`: context needed
3. `user_action`: click/double-click/enter/etc
4. `system_reaction`: deterministic MCC behavior
5. `myco_short_hint`: top hint wording (when helper off)
6. `architect_detail_hint`: detailed wording for project/task architect

## Catalog

| UI element | intent | prerequisites | user_action | system_reaction | myco_short_hint | architect_detail_hint |
|---|---|---|---|---|---|---|
| Project tab | switch active project | tab exists | click tab | active project context changes | `project switched: verify active task` | `project architect: refresh DAG health, then choose next task anchor` |
| `+ project` | create new project scope | none | click | new project bootstrap flow | `create project: choose disk/git` | `project architect: initialize source, then build baseline DAG` |
| Top MYCO avatar | handoff to guided mode | helper off | click | helper mode activates, chat restores | `MYCO moved to chat` | `open helper chat and request step-by-step for current node` |
| Top MYCO hint | passive next action | helper off | none (read) | top short advice updates by context | `next action shown here` | `ask architect in chat for expanded rationale` |
| Node select | set focus context | node visible | click node | context/stats/tasks sync to selected node | `node selected: open Context` | `task architect: inspect model/prompt/state and decide run/retry` |
| Node drill | enter deeper graph level | node supports drill | double-click / Enter | inline workflow/module unfolds | `module unfolded: select agent` | `project architect: inspect branch quality, then assign next task` |
| Canvas context menu | create graph entities | edit path enabled | right-click canvas | add-node actions shown | `add node from menu` | `architect: add minimal nodes only, preserve clean DAG` |
| Node context `Create Task Here` | anchor task to code node | non-task node | right-click node -> action | new anchored task created | `task anchored to selected node` | `task architect: define acceptance criteria, then start` |
| Node context `Approve Suggested Anchor` | convert suggested link to approved | suggested task overlay selected | right-click task overlay -> action | anchor state updates to approved | `suggested anchor approved` | `project architect: confirm ownership and dependency order` |
| Edge context `Delete Edge` | remove relation | edge selected | right-click edge -> action | edge removed + validation | `edge removed` | `architect: verify no orphan/regression after relation removal` |
| MiniTasks `start` | dispatch selected task | task pending/queued/hold | click `start` | task dispatch called | `task started` | `task architect: monitor stream, verifier, retry policy` |
| MiniTasks `stop` | cancel active run | task running | click `stop` | cancel path called | `task stopped` | `task architect: inspect partial output, decide retry/hold` |
| MiniTasks heartbeat toggle | periodic orchestrator cycle | heartbeat available | toggle on/off | heartbeat state updates | `heartbeat on/off updated` | `project architect: use heartbeat for long queue supervision` |
| MiniTasks heartbeat interval | schedule cadence | heartbeat available | choose interval | interval persists in store | `heartbeat interval changed` | `project architect: lower interval for active incident response` |
| MiniChat in architect mode | standard architect Q/A | helper off | send message | `/api/chat/quick` role `architect` | `architect chat active` | `project/task architect: answer with context-bound actions only` |
| MiniChat in MYCO mode | guided helper Q/A | helper on | send message | `/api/chat/quick` role `helper_myco` | `MYCO guidance active` | `MYCO should return what/why/next with concrete controls` |
| MiniContext `change model` | role-level model override | agent node selected | expand context -> select model -> save | preset role model update call | `agent model updated` | `task architect: align model to role cost/quality target` |
| MiniContext prompt preview | inspect role instructions | agent node selected | expand context | role preprompt shown read-only | `prompt visible in context` | `architect: validate role prompt before rerun` |
| MiniStats compact | monitor run health | none | read panel | live aggregate metrics shown | `check run/success/cost` | `project architect: detect drift and apply corrective routing` |
| MiniBalance key select | choose active provider key | keys available | click key row | selected key context updates | `active key changed` | `architect: confirm model availability and cost envelope` |
| MiniWindowDock restore chat | resume collapsed chat | chat minimized | click dock `Chat` | chat window restores; MYCO anim trigger if active | `chat restored` | `continue last context thread; avoid reset` |

## Guardrails
1. MYCO short hint must stay single-line in top bar.
2. Architect detail hint must stay action-first (`do -> inspect -> decide`).
3. No speculative instructions for controls that are not visible in current mode.
