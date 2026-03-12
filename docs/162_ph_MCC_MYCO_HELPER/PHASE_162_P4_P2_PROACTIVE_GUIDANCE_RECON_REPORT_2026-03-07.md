# PHASE 162 — P4.P2 Proactive Guidance Recon Report (2026-03-07)

Status: `RECON COMPLETE`
Protocol: `RECON -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`

## Why this recon
Observed UX gap: after drill/open workflow, top MYCO hint still repeats `Press Enter to drill into workflow` instead of guiding next actionable step.

## Scope scanned
1. `client/src/components/mcc/MyceliumCommandCenter.tsx`
2. `client/src/components/mcc/MiniChat.tsx`
3. `docs/162_ph_MCC_MYCO_HELPER/MYCO_HELP_RULES_LIBRARY_V1.md`
4. `docs/162_ph_MCC_MYCO_HELPER/MYCO_CONTEXT_PAYLOAD_CONTRACT_V1.md`
5. `docs/161_ph_MCC_TRM/MYCO_AGENT_INSTRUCTIONS_GUIDE_V1_2026-03-06.md`

## Current behavior map (as-is)
### Top hint channel (MYCO in top bar, helper off)
1. Main branch currently prioritizes:
- if `navLevel in {roadmap,tasks}` and `selectedNode` -> always `Press Enter to drill into <workflow/module/task>`
- else fallback to generic labels (`task linked`, `roadmap context`, `workflow context`)
2. `taskDrillState === 'expanded'` is **not** considered in this priority branch.
3. `roadmapNodeDrillState === 'expanded'` also not used in top-hint wording.

Result:
- after successful drill/open, hint can remain stale/redundant.

### Chat channel (MYCO in chat, helper on)
1. `buildMycoReply(context)` keys only on `navLevel/nodeKind/label/role`.
2. It does not consume drill-state (`taskDrillState`, `roadmapNodeDrillState`) nor explicit next-action matrix for post-drill state.
3. Proactive context change trigger is now present (`P4.P1`), but text granularity remains coarse.

Result:
- proactive trigger works, but action guidance depth is limited.

## Scenario matrix audit
### Covered reasonably
1. Project/root selected in roadmap.
2. Task selected before drill.
3. Agent selected (model/prompt hint).
4. File/directory selected (inspect Context and links).

### Under-covered / missing
1. `roadmap + selected task + drill already expanded`:
- Expected: "workflow opened -> pick agent node -> check model/prompt -> run/retry".
- Actual: still can say "Press Enter to drill".

2. `roadmap node drill expanded (matryoshka)`:
- Expected: "module unfolded -> double-click deeper / select task / create task here".
- Actual: generic drill hint.

3. `workflow active + no node selected`:
- Expected: "select agent node to inspect stream/context; select coder to adjust model".
- Actual: generic workflow text.

4. `task done` or `task running` status-aware micro-guidance:
- Expected action should branch by status.
- Not implemented in top hint and only weakly implied in chat.

5. "what are my options now" compact list:
- No deterministic top-level option pack (2-3 short actions) by state.

## Root cause
1. Top-hint builder is state-poor for drill lifecycle (selection dominates, drill state ignored).
2. MYCO rules library is high-level; not mapped to concrete MCC state machine transitions.
3. Chat reply builder does not consume richer context payload despite contract availability.

## Proposed narrow target (P4.P2)
Goal: deterministic, state-aware proactive guidance with strict no-spam behavior.

### Rule priority order (new)
1. `if helperMode=off and taskDrillState=expanded and navLevel=roadmap`:
- top hint should switch to **post-drill actions**, not "press Enter".
2. `if roadmapNodeDrillState=expanded`:
- top hint should switch to unfold/navigation actions.
3. `if workflow focus active`:
- top hint should propose node selection/model/context actions.
4. Only pre-drill states may show `Press Enter to drill ...`.

### Guidance format
1. Top hint: one concise line (`what now`).
2. Chat (helper mode): expanded 2-3 steps (`what -> why -> next`).

## Markers (P4.P2 recon lock)
1. `MARKER_162.P4.P2.MYCO.TOP_HINT_POST_DRILL_PRIORITY.V1`
2. `MARKER_162.P4.P2.MYCO.TOP_HINT_WORKFLOW_ACTIONS.V1`
3. `MARKER_162.P4.P2.MYCO.TOP_HINT_NODE_UNFOLD_ACTIONS.V1`
4. `MARKER_162.P4.P2.MYCO.CHAT_REPLY_STATE_MATRIX.V1`
5. `MARKER_162.P4.P2.MYCO.NO_STALE_DRILL_PROMPT_AFTER_EXPAND.V1`
6. `MARKER_162.P4.P2.MYCO.PROACTIVE_NEXT_ACTION_PACK.V1`

## Suggested acceptance criteria
1. After drill is expanded, top hint never says `Press Enter to drill ...`.
2. Top hint changes within one render cycle after state transition.
3. Chat MYCO proactive reply includes state-specific next actions.
4. Architect mode remains clean: no helper message echo in chat.
5. Guidance remains concise (top <= 1 line; chat <= 3 bullets by default).

## Test plan (for implementation step)
1. `tests/test_phase162_p4_p2_myco_guidance_matrix_contract.py`:
- marker presence;
- post-drill hint priority contract;
- no stale pre-drill prompt when drill expanded.
2. Extend `tests/test_phase162_p4_p1_myco_proactive_chat_contract.py`:
- ensure helper reply text switches across drill states.

## GO token for implementation
`GO 162-P4.P2`
