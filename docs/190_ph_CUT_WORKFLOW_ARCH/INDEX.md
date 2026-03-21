# CUT Architecture Docs — Index

**Phase:** 190+ (CUT Workflow Architecture)
**Updated:** 2026-03-22

---

## Core Architecture

| Doc | What | Status |
|-----|------|--------|
| [CUT_TARGET_ARCHITECTURE.md](CUT_TARGET_ARCHITECTURE.md) | Constitution. 3-level model (Script Spine → DAG → Timeline). All design questions resolved. THE source of truth. | Active |
| [CUT_UNIFIED_VISION.md](CUT_UNIFIED_VISION.md) | Panel registry, panel focus model, overall UI vision | Active |
| [CUT_HOTKEY_ARCHITECTURE.md](CUT_HOTKEY_ARCHITECTURE.md) | Hotkey system: presets (Premiere/FCP7/Custom), panel-scoped dispatch, key capture | Active |
| [CUT_DATA_MODEL.md](CUT_DATA_MODEL.md) | Store structure, data flow, state management | Active |
| [CUT_COGNITIVE_MODEL.md](CUT_COGNITIVE_MODEL.md) | Two-circuit architecture: Circuit A (symbolic) + Circuit B (JEPA). Bridge layer. | Active |

## Commander & Multi-Agent

| Doc | What | Status |
|-----|------|--------|
| [COMMANDER_ROLE_PROMPT.md](COMMANDER_ROLE_PROMPT.md) | Commander role, dispatch format, wave execution, merge protocol, priority framework | Active |
| [HANDOFF_CUT_4OPUS_COMMANDER_SESSION_2026-03-20.md](HANDOFF_CUT_4OPUS_COMMANDER_SESSION_2026-03-20.md) | Captain's log: 4-Opus session, 30 tasks, strategy that worked | Archive |
| [HANDOFF_CUT_COMMANDER_INSPIRING_COHEN_2026-03-20.md](HANDOFF_CUT_COMMANDER_INSPIRING_COHEN_2026-03-20.md) | Commander-to-Commander handoff (inspiring-cohen) | Archive |
| [HANDOFF_CUT_MVP_PARALLEL_2026-03-20.md](HANDOFF_CUT_MVP_PARALLEL_2026-03-20.md) | MVP parallel execution handoff | Archive |
| [HANDOFF_CUT_TOOLS_AND_DOCKING_2026-03-19.md](HANDOFF_CUT_TOOLS_AND_DOCKING_2026-03-19.md) | Tools & docking migration handoff | Archive |
| [HANDOFF_196_DOCKVIEW_MIGRATION_2026-03-20.md](HANDOFF_196_DOCKVIEW_MIGRATION_2026-03-20.md) | Dockview migration handoff | Archive |
| [HANDOFF_192_CUT_UI_CLEANUP_2026-03-19.md](HANDOFF_192_CUT_UI_CLEANUP_2026-03-19.md) | UI cleanup handoff | Archive |

## Agent Feedback

| Doc | What | Status |
|-----|------|--------|
| [feedback/FEEDBACK_WAVE3_4_ALL_STREAMS_2026-03-20.md](feedback/FEEDBACK_WAVE3_4_ALL_STREAMS_2026-03-20.md) | Agent consensus from Wave 3-4. Predecessor advice chains. Priority matrix. GIVE TO EVERY NEW AGENT. | Critical |

## Reconnaissance

| Doc | What | Agent |
|-----|------|-------|
| [RECON_FCP7_DELTA2_CH41_115_2026-03-20.md](RECON_FCP7_DELTA2_CH41_115_2026-03-20.md) | FCP7 Bible audit Ch.41-115. 15 tasks created. ~33% compliance | Delta-2 |
| [RECON_192_ARCH_VS_CODE_2026-03-18.md](RECON_192_ARCH_VS_CODE_2026-03-18.md) | Gap analysis: target architecture vs actual code | General |
| [RECON_CUT_LAYOUT_COMPLIANCE_FCP7_PREMIERE.md](RECON_CUT_LAYOUT_COMPLIANCE_FCP7_PREMIERE.md) | Layout compliance audit vs FCP7/Premiere | Delta |
| [RECON_CUT_E2E_TEST_ARCHITECTURE.md](RECON_CUT_E2E_TEST_ARCHITECTURE.md) | E2E test architecture recon | Delta |
| [RECON_TIMELINE_MULTI_INSTANCE_2026-03-20.md](RECON_TIMELINE_MULTI_INSTANCE_2026-03-20.md) | Multi-timeline instance architecture | Alpha |
| [RECON_PANEL_DOCKING_2026-03-19.md](RECON_PANEL_DOCKING_2026-03-19.md) | Panel docking investigation | Gamma |
| [RECON_UI_CLEANUP.md](RECON_UI_CLEANUP.md) | UI cleanup recon | Gamma |
| [RECON_UI_LAYOUT_GROK_2026-03-19.md](RECON_UI_LAYOUT_GROK_2026-03-19.md) | UI layout analysis (Grok) | External |
| [RECON_v1_vs_CODE.md](RECON_v1_vs_CODE.md) | v1 architecture doc vs actual implementation | General |
| [RECON_B_PYAV_COLOR_PIPELINE.md](RECON_B_PYAV_COLOR_PIPELINE.md) | PyAV color pipeline research | Beta |

## Research

| Doc | What | Agent |
|-----|------|-------|
| [RESEARCH_COLOR_PROFILES_CUT_2026-03-20.md](RESEARCH_COLOR_PROFILES_CUT_2026-03-20.md) | Color pipeline: FCP7 + modern standards, LUT, camera log | Beta |

## Roadmaps

| Doc | What | Agent |
|-----|------|-------|
| [ROADMAP_CUT_FULL.md](ROADMAP_CUT_FULL.md) | Full CUT roadmap across all domains | Commander |
| [ROADMAP_CUT_MVP_PARALLEL.md](ROADMAP_CUT_MVP_PARALLEL.md) | Parallel execution plan for MVP | Commander |
| [ROADMAP_A_ENGINE_DETAIL.md](ROADMAP_A_ENGINE_DETAIL.md) | Engine domain detail roadmap | Alpha |
| [ROADMAP_B_MEDIA_DETAIL.md](ROADMAP_B_MEDIA_DETAIL.md) | Media domain detail roadmap | Beta |
| [ROADMAP_C_UX_DETAIL.md](ROADMAP_C_UX_DETAIL.md) | UX domain detail roadmap | Gamma |

---

## Reading Order for New Commander

1. `CUT_TARGET_ARCHITECTURE.md` — understand what CUT IS
2. `feedback/FEEDBACK_WAVE3_4_ALL_STREAMS_2026-03-20.md` — understand what agents learned
3. `HANDOFF_CUT_4OPUS_COMMANDER_SESSION_2026-03-20.md` — understand how parallel ops work
4. `COMMANDER_ROLE_PROMPT.md` — understand your role
5. `vetka_task_board action=list project_id=cut` — understand current state

## Reading Order for New Agent

1. `CUT_TARGET_ARCHITECTURE.md` — constitution and 3-level model
2. `feedback/FEEDBACK_WAVE3_4_ALL_STREAMS_2026-03-20.md` — predecessor advice
3. Domain-specific ROADMAP (`A`/`B`/`C`) — your plan
4. Domain-specific RECONs — what was investigated
5. Commander's dispatch — your current mission
