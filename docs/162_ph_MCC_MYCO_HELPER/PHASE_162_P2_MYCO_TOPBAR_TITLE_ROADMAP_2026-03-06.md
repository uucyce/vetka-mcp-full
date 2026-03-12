# PHASE 162 — P2 MYCO Topbar + Title Roadmap (2026-03-06)

Status: `ROADMAP (approved)`
Protocol: `RECON -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`

## Scope lock (P2)
1. Add `MYCO` button (icon + label) in MCC top tab-row.
2. Click toggles helper mode: `off -> passive -> active`.
3. While MYCO replies, icon temporarily switches to animated state (`APNG` preferred).
4. Window title reduced to `MYCELIUM`.

## Markers (P2)
1. `MARKER_162.P2.MYCO.TOPROW_BUTTON.V1`
2. `MARKER_162.P2.MYCO.MODE_TOGGLE_TOPROW.V1`
3. `MARKER_162.P2.MYCO.AVATAR_RESPONSE_ANIM.V1`
4. `MARKER_162.P2.MYCO.WINDOW_TITLE_MYCELIUM.V1`
5. `MARKER_162.P2.MYCO.TOPROW_LAYOUT_GUARD.V1`
6. `MARKER_162.P2.MYCO.MINICHAT_AVATAR_BIND.V1`
7. `MARKER_162.P2.MYCO.TOP_HINT_BRIDGE.V1`

## Recon summary
1. MCC has no internal header bar in grandma mode; the best stable placement is current project tab-row.
2. Current chat MYCO mode chip is too small and should remain secondary, not primary control.
3. Native macOS titlebar currently uses standard decorations (`decorations: true`), so embedding a custom button inside native titlebar is out-of-scope for narrow P2.
4. Tauri window title is set in two places and both must be aligned:
- `client/src-tauri/tauri.conf.json`
- `client/src-tauri/src/main.rs`
5. Input icon assets are alpha PNG and suitable for compact render after resizing.
6. `ffmpeg` on workspace supports `apng`, `gif`, `webp`; P2 chooses `APNG` to keep alpha quality and implementation simple.

## Implementation plan (narrow)
1. Add compact MYCO assets under `client/src/assets/myco`:
- `myco_idle_question.png`
- `myco_ready_smile.png`
- `myco_speaking_loop.apng`
2. Emit event `mcc-myco-reply` from MiniChat when MYCO returns helper output.
3. Listen in `MyceliumCommandCenter` and drive short icon state machine:
- `idle -> speaking -> ready -> idle`
4. Render top-row MYCO button with icon + label + compact mode indicator.
5. Bind click to store mode rotation (`off/passive/active`).
6. Rename MCC window title to `MYCELIUM`.

## Verify checklist
1. Chat still works for architect and MYCO triggers.
2. MYCO top button toggles modes and reflects current state.
3. MYCO icon animates only on helper reply event.
4. MCC window title shows `MYCELIUM`.
5. No changes to DAG layout logic.

## P2.1 UX polish add-on
1. Move MYCO top-row button left to avoid overlap with debug toggle.
2. Make MYCO icon in MiniChat noticeably larger/readable.
3. Show `!` indicator while MYCO is answering (same visual semantics in top-row and chat).
4. Bridge selection/system hint into top MYCO area so helper is perceived as speaker.
5. Remove explicit `MYCO` text labels from visible UI controls (icon-first helper UX).
6. Place helper icon left of top hint bubble (speaker-avatar composition).

## P2.2 behavior lock (2026-03-06)
1. `off` mode: helper visible only in top row, pinned near center-left.
2. `passive/active` mode: helper icon hidden in top row and shown in chat header.
3. Top hint bubble width must be fixed to avoid jitter on hint text length changes.
4. Top-row helper anchor must not depend on right-side controls or debug elements.
5. Node/system hint in `off` mode must animate helper avatar (`? -> ! -> smile -> ?`).

## Markers (P2.2)
1. `MARKER_162.P2.MYCO.TOP_CENTER_ANCHOR.V1`
2. `MARKER_162.P2.MYCO.TOP_HINT_FIXED_WIDTH.V1`
3. `MARKER_162.P2.MYCO.CHAT_ONLY_WHEN_ENABLED.V1`
4. `MARKER_162.P2.MYCO.TOP_SYSTEM_HINT_PRIORITY.V1`
5. `MARKER_162.P2.MYCO.CHAT_MYCO_PLACEHOLDER_CONTEXT.V1`
6. `MARKER_162.P2.MYCO.CHAT_REDUCED_NOISE_WHEN_ACTIVE.V1`
7. `MARKER_162.P2.MYCO.DOCK_RESTORE_SPEAKING.V1`
8. `MARKER_162.P2.MYCO.CHAT_SINGLE_LEFT_ANCHOR.V1`
9. `MARKER_162.P2.MYCO.CHAT_BUBBLE_TAIL.V1`
10. `MARKER_162.P2.MYCO.WINDOW_TITLE_DOC_SYNC.V1`

## P2.3 behavior + docs sync (2026-03-06)
1. Top-click handoff to chat must be race-safe: MYCO always speaks on first activation.
2. Top hint in `off` mode renders as comic speech bubble with pointer tail to MYCO avatar.
3. MYCO top avatar should not be visually clipped inside tab row.
4. Integrate parallel-agent instructions guide into MYCO docs and roadmap:
- source: `docs/161_ph_MCC_TRM/MYCO_AGENT_INSTRUCTIONS_GUIDE_V1_2026-03-06.md`
- action: align Phase 162 contracts and keep split-to-RAG as planned follow-up.

## Markers (P2.3)
1. `MARKER_162.P2.MYCO.TOP_ACTIVATE_RACE_GUARD.V1`
2. `MARKER_162.P2.MYCO.TOP_HINT_COMIC_BUBBLE.V1`
3. `MARKER_162.P2.MYCO.TOP_AVATAR_NO_CLIP.V1`
4. `MARKER_162.P2.MYCO.INSTR_GUIDE_SYNC.V1`

## Carry-forward to next phase (memory/rag backend-only)
1. Hidden scan/index of instructions and readmes into triple-memory for MYCO/agents.
2. ENGRAM binding for MYCO:
- user name;
- latest tasks per project;
- latest workflow context.
3. Local-first retrieval path:
- JEPA + Gemma as fast local answer path;
- API escalation only when local confidence is insufficient.
4. Strict UX rule:
- no new memory widgets or toggles in MCC UI; all memory work remains invisible in UI.

## Markers (carry-forward)
1. `MARKER_162.P3.MYCO.HIDDEN_TRIPLE_MEMORY_INDEX.V1`
2. `MARKER_162.P3.MYCO.README_SCAN_PIPELINE.V1`
3. `MARKER_162.P3.MYCO.ENGRAM_USER_TASK_MEMORY.V1`
4. `MARKER_162.P3.MYCO.JEPA_GEMMA_LOCAL_FASTPATH.V1`
5. `MARKER_162.P3.MYCO.NO_UI_MEMORY_SURFACE.V1`

## P3.P2 (implemented, 2026-03-06)
1. Add orchestration snapshot (`multitask + project_digest`) to hidden MYCO payload.
2. Persist lightweight runtime facts back to ENGRAM (`myco_last_project`, `myco_last_focus`, `myco_last_phase`).
3. Surface orchestration hints in MYCO quick replies and JEPA pack input.

## Markers (P3.P2)
1. `MARKER_162.P3.P2.MYCO.ORCHESTRATION_SNAPSHOT.V1`
2. `MARKER_162.P3.P2.MYCO.ENGRAM_PERSIST_RUNTIME_FACTS.V1`

## P3.P3 (implemented, 2026-03-06)
1. Split instruction corpus into RAG-ready docs:
- `myco_core`
- `agent_roles`
- `user_playbook`
2. Enrich multitask snapshot with execution config (`max_concurrent`, `auto_dispatch`, board phase).
3. Reflect enriched orchestration snapshot in quick MYCO reply contract.

## Markers (P3.P3)
1. `MARKER_162.P3.P3.MYCO.RAG_CORE_SPLIT.V1`
2. `MARKER_162.P3.P3.MYCO.RAG_AGENT_ROLES_SPLIT.V1`
3. `MARKER_162.P3.P3.MYCO.RAG_USER_PLAYBOOK_SPLIT.V1`
4. `MARKER_162.P3.P3.MYCO.MULTITASK_CFG_SNAPSHOT.V1`

## P3.P4 (recon locked, waiting GO)
1. Connect hidden instruction index to real MYCO retrieval path.
2. Add glossary alias expansion from canonical memory abbreviations glossary.
3. Add retrieval quality gate + deterministic fallback.
4. Add retrieval coverage tests for phase-162 gate.

## Markers (P3.P4)
1. `MARKER_162.P3.P4.MYCO.RETRIEVAL_BRIDGE.V1`
2. `MARKER_162.P3.P4.MYCO.GLOSSARY_ALIAS_EXPANSION.V1`
3. `MARKER_162.P3.P4.MYCO.RETRIEVAL_QUALITY_GATE.V1`
4. `MARKER_162.P3.P4.MYCO.RETRIEVAL_COVERAGE_TESTS.V1`

Status: `implemented (2026-03-06)` in:
- `PHASE_162_P3_P4_RETRIEVAL_QUALITY_IMPL_REPORT_2026-03-06.md`

## P4.P1 (implemented, 2026-03-06)
1. Proactive MYCO reply on context switch in compact chat (deduped by stable context key).
2. Proactive MYCO reply on context switch in expanded chat (deduped by stable context key).
3. Remove compact-mode regression path that wrote to expanded-chat state (`setMessages`).

## Markers (P4.P1)
1. `MARKER_162.P4.P1.MYCO.CONTEXT_PROACTIVE_CHAT_COMPACT.V1`
2. `MARKER_162.P4.P1.MYCO.CONTEXT_PROACTIVE_CHAT_EXPANDED.V1`
3. `MARKER_162.P4.P1.MYCO.COMPACT_NO_STALE_SETMESSAGES.V1`

Status: `implemented (2026-03-06)` in:
- `PHASE_162_P4_P1_PROACTIVE_CHAT_RECON_REPORT_2026-03-06.md`
- `PHASE_162_P4_P1_PROACTIVE_CHAT_IMPL_REPORT_2026-03-06.md`

## P4.P2 (implemented, 2026-03-07)
Goal: make MYCO proactive guidance state-aware after drill/unfold transitions.

1. Top hint must switch from pre-drill prompt to post-drill actions once drill is expanded.
2. Workflow-focused hinting should propose concrete next actions (select agent, inspect context, change model, run/retry).
3. Roadmap node unfold hinting should propose unfold/navigation actions instead of generic drill prompt.
4. Chat MYCO replies should use a state matrix (`what -> why -> next`) based on real MCC drill state.

## Markers (P4.P2)
1. `MARKER_162.P4.P2.MYCO.TOP_HINT_POST_DRILL_PRIORITY.V1`
2. `MARKER_162.P4.P2.MYCO.TOP_HINT_WORKFLOW_ACTIONS.V1`
3. `MARKER_162.P4.P2.MYCO.TOP_HINT_NODE_UNFOLD_ACTIONS.V1`
4. `MARKER_162.P4.P2.MYCO.CHAT_REPLY_STATE_MATRIX.V1`
5. `MARKER_162.P4.P2.MYCO.NO_STALE_DRILL_PROMPT_AFTER_EXPAND.V1`
6. `MARKER_162.P4.P2.MYCO.PROACTIVE_NEXT_ACTION_PACK.V1`

Status: `recon complete (2026-03-07)` in:
- `PHASE_162_P4_P2_PROACTIVE_GUIDANCE_RECON_REPORT_2026-03-07.md`

Status: `implemented (2026-03-07)` in:
- `PHASE_162_P4_P2_PROACTIVE_GUIDANCE_IMPL_REPORT_2026-03-07.md`

## P4.P3 (implemented, 2026-03-07)
Goal: align MYCO instructions with real MYCELIUM capability surface and make RAG retrieval state-key aware.

1. Add MYCELIUM capability matrix to MYCO instruction guide.
2. Add proactive message state matrix (pre/post drill, workflow, tasks).
3. Add state-key enrichment policy for hidden retrieval (`nav_level`, drill states, `node_kind`).
4. Send drill-state fields from MiniChat to backend quick-chat context.
5. Use state-aware next-action pack in quick MYCO replies.

## Markers (P4.P3)
1. `MARKER_162.P4.P3.MYCO.MYCELIUM_CAPABILITY_MATRIX.V1`
2. `MARKER_162.P4.P3.MYCO.PROACTIVE_MESSAGE_STATE_MATRIX.V1`
3. `MARKER_162.P4.P3.MYCO.RAG_STATE_KEY_ENRICHMENT.V1`
4. `MARKER_162.P4.P3.MYCO.CHAT_CONTEXT_DRILL_FIELDS.V1`
5. `MARKER_162.P4.P3.MYCO.PROACTIVE_NEXT_ACTION_PACK.V1`

Status: `recon complete (2026-03-07)` in:
- `PHASE_162_P4_P3_MYCELIUM_CAPABILITY_RAG_RECON_REPORT_2026-03-07.md`

Status: `implemented (2026-03-07)` in:
- `PHASE_162_P4_P3_MYCELIUM_CAPABILITY_RAG_IMPL_REPORT_2026-03-07.md`

## P4.P4 (implemented, 2026-03-07)
Goal: remove generic roadmap fallback in workflow contexts and provide node/role/workflow-family specific guidance.

1. Expand MiniChat->quick-chat context with `graph_kind/workflow_id/team_profile/workflow_family/status/model/path`.
2. Extend MYCO quick response matrix by:
- node kind (`task/agent/file/directory/project`);
- agent role (`architect/coder/verifier/eval/...`);
- workflow family (`dragons/titans/g3/ralph_loop/bmad/custom`).
3. Extend top hint matrix with role/family cues while workflow is open.
4. Add detailed instruction matrix to guide (node/subnode/agent/role/workflow switch/run paths).

## Markers (P4.P4)
1. `MARKER_162.P4.P4.MYCO.TOP_HINT_NODE_ROLE_WORKFLOW_MATRIX.V1`
2. `MARKER_162.P4.P4.MYCO.CHAT_REPLY_NODE_ROLE_WORKFLOW_MATRIX.V1`
3. `MARKER_162.P4.P4.MYCO.NODE_ROLE_WORKFLOW_NEXT_ACTIONS.V1`
4. `MARKER_162.P4.P4.MYCO.NODE_ROLE_WORKFLOW_GUIDE_MATRIX.V1`

Status: `recon complete (2026-03-07)` in:
- `PHASE_162_P4_P4_NODE_ROLE_WORKFLOW_RECON_REPORT_2026-03-07.md`

Status: `implemented (2026-03-07)` in:
- `PHASE_162_P4_P4_NODE_ROLE_WORKFLOW_IMPL_REPORT_2026-03-07.md`

## P4.P5 (implemented, 2026-03-07)
Goal: lock runtime MYCO scenario behavior by executable tests on real quick-reply matrix.

1. Add direct runtime tests for `_build_myco_quick_reply(...)` (not only static marker contracts).
2. Cover critical scenarios:
- roadmap + module unfold;
- roadmap + workflow expanded + architect (dragons);
- roadmap + workflow expanded + coder (titans);
- roadmap + workflow expanded + verifier;
- task scope with family hint.
3. Prevent regression to generic roadmap fallback on workflow-level contexts.

## Markers (P4.P5)
1. `MARKER_162.P4.P5.MYCO.RUNTIME_SCENARIO_MATRIX_LOCK.V1`

Status: `recon complete (2026-03-07)` in:
- `PHASE_162_P4_P5_RUNTIME_SCENARIO_MATRIX_RECON_REPORT_2026-03-07.md`

Status: `implemented (2026-03-07)` in:
- `PHASE_162_P4_P5_RUNTIME_SCENARIO_MATRIX_IMPL_REPORT_2026-03-07.md`
