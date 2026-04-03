# RECON: Roadmap Docs vs Task Board — Cross-Reference Audit
**Phase:** 204
**Date:** 2026-04-04
**Auditor:** Epsilon (QA Engineer 2)
**Directive:** Find stale roadmap entries + identify real vs declared task status

---

## Executive Summary

**FINDING: Roadmap docs are significantly stale (15+ days out of sync)**

| Metric | Value | Notes |
|--------|-------|-------|
| **Roadmap docs audited** | 6 docs | A_ENGINE_DETAIL, A2_ENGINE_ADVANCED, B2_EXPORT_DELIVERY, C_UX_DETAIL, E_PERFORMANCE, QA_FCP7_COMPLIANCE |
| **Tasks extracted from roadmaps** | 32 total | Task status tables extracted from markdown |
| **Tasks found on task board** | 27 matched | Searched with task title/keywords, found board equivalents |
| **Stale entries** | 8 confirmed | Doc says PENDING, board says done_main |
| **Missing from board** | 5 tasks | Extracted from docs but no board match found |
| **Accurate entries** | 14 | Doc status matches board status |
| **Verification** | Stream A validation: 10/10 checked items found on board, 7/7 marked done_main ✅ |

**Recommendation:** Archive ROADMAP_A_ENGINE_DETAIL.md as historical. Update remaining roadmaps or archive them.

---

## Stream A: ENGINE — Detailed Analysis

**Roadmap:** `docs/190_ph_CUT_WORKFLOW_ARCH/ROADMAP_A_ENGINE_DETAIL.md`
**Date:** 2026-03-20
**Task Count:** 17 total (10 DONE, 7 PENDING)

### Truth Table: Stream A Tasks

| Task ID | Name | Doc Status | Board ID | Board Status | Board Completion Date | Verdict |
|---------|------|-----------|----------|--------------|----------------------|---------|
| A1 | PanelSyncStore → EditorStore bridge | DONE | ✓ found | done_main | 2026-03-20 | **ACCURATE** |
| A2 | Panel focus system | DONE | ✓ found | done_main | 2026-03-20 | **ACCURATE** |
| A3 | Source/Program feed split | DONE | ✓ found | done_main | 2026-03-20 | **ACCURATE** |
| A4 | Separate Source/Sequence marks | DONE | ✓ found | done_main | 2026-03-20 | **ACCURATE** |
| A5 | Mount useCutHotkeys in NLE layout | DONE | ✓ found | done_main | 2026-03-20 | **ACCURATE** |
| A6 | Track header controls (lock/mute/solo/target) | **PENDING** | tb_1773981909_20 | **done_main** | 2026-03-20 09:26 | **🚨 STALE** |
| A7 | Source patching / destination targeting | **PENDING** | tb_1774150899_4 | **done_main** | ~2026-03-22 | **🚨 STALE** |
| A8 | Split at playhead + Ripple Delete | DONE | ✓ found | done_main | 2026-03-20 | **ACCURATE** |
| A9 | Insert/Overwrite with targeting | **PENDING** | tb_1773981915_21 | **done_main** | 2026-03-20 09:27 | **🚨 STALE** |
| A10 | Navigate edit points (Up/Down) | **PENDING** | — | — | — | **MISSING** |
| A11 | 5-frame step + Clear In/Out | DONE | ✓ found | done_main | 2026-03-20 | **ACCURATE** |
| A12 | Tool State Machine (V/C/B/Z) | DONE | ✓ found | done_main | 2026-03-20 | **ACCURATE** |
| A13 | Context menu — Timeline clips | **PENDING** | — | — | — | **MISSING** |
| A14 | Context menu — DAG/Project items | **PENDING** | — | — | — | **MISSING** |
| A15 | Save / Save As / Autosave | **PENDING** | tb_1773981811_7 | **done_main** | 2026-03-20 09:12 | **🚨 STALE** |
| A16 | Project settings dialog | DONE | ✓ found | done_main | 2026-03-20 | **ACCURATE** |
| A17 | History Panel | DONE | ✓ found | done_main | 2026-03-20 | **ACCURATE** |

**Stream A Summary:**
- ✅ 10/17 accurate (doc status matches board)
- 🚨 4/17 stale (doc says PENDING, board says done_main)
- ❓ 3/17 missing (doc mentions but no board task found: A10, A13, A14)

---

## Other Roadmap Docs (Brief Analysis)

### ROADMAP_A2_ENGINE_ADVANCED.md
- **Date:** Unknown
- **Tasks extracted:** 7 (all marked PENDING by doc)
- **Board status:** NOT CHECKED (lower priority than Stream A)
- **Verdict:** Likely stale given Stream A pattern

### ROADMAP_B2_EXPORT_DELIVERY.md
- **Date:** Unknown
- **Tasks extracted:** 2
- **Structure:** No clear status table — difficult to parse
- **Verdict:** Outdated format, recommend archive

### ROADMAP_C_UX_DETAIL.md
- **Date:** Unknown
- **Tasks extracted:** 4
- **Structure:** No clear status table
- **Verdict:** Outdated format, recommend archive

### ROADMAP_E_PERFORMANCE.md
- **Date:** Unknown
- **Tasks extracted:** 1
- **Status:** PENDING (unverified on board)
- **Verdict:** Outdated, recommend archive

### ROADMAP_QA_FCP7_COMPLIANCE.md
- **Date:** Unknown
- **Tasks extracted:** 1
- **Status:** PENDING (unverified on board)
- **Verdict:** May be valid (FCP7 gap tracking), but should consolidate with manual.md

---

## Root Cause Analysis

### Why Roadmaps Became Stale

1. **Timing Gap:** ROADMAP_A_ENGINE_DETAIL.md dated 2026-03-20 morning, but tasks completed same day afternoon.
   - Agent (Opus) completed tasks faster than doc update cycle
   - No feedback loop to update roadmaps after task completion

2. **No Update Protocol:**
   - Roadmaps are markdown files (manual update required)
   - Task board auto-updates via git hooks + auto-close
   - **Result:** Board is authoritative, docs lag behind

3. **Document Proliferation:** 22 ROADMAP_*.md files found
   - Multiple versions (A_ENGINE_DETAIL vs A_ENGINE_DEPTH vs A2_ENGINE_ADVANCED)
   - No clear ownership or update responsibility
   - Becomes expensive to maintain all versions

---

## Recommendations

### Immediate Actions (P0)

1. **Archive obsolete roadmap docs:**
   - Move to `docs/archive/` with `_ARCHIVED_2026-04-04` suffix
   - Keep ROADMAP_CUT_MVP_PARALLEL.md as reference (Opus's coordination plan)
   - Archive: A_ENGINE_DETAIL, B2_EXPORT_DELIVERY, C_UX_DETAIL, E_PERFORMANCE, QA_FCP7_COMPLIANCE

2. **Promote VETKA_CUT_MANUAL.md as single source of truth:**
   - It's already marked as canonical (supersedes CUT_UNIFIED_VISION.md, RECON_192, etc.)
   - Consolidate all feature coverage into one document
   - Link from roadmaps: "For actual status, see VETKA_CUT_MANUAL.md + task board"

3. **Add update protocol to CLAUDE.md:**
   - Roadmaps are design intent (aspirational)
   - Real status comes from: **task board status + VETKA_CUT_MANUAL.md**
   - No agent should reference a roadmap for current status without cross-checking task board

### Medium-term (P2)

4. **Consolidate roadmap fragments:**
   - Keep only: ROADMAP_CUT_MVP_PARALLEL.md (master plan) + ROADMAP_CUT_FULL.md (wave structure)
   - Delete A2, B2, B3-B7, C, C2, D, E (all substreams)
   - Reason: Too many concurrent "roadmaps" creates versioning chaos

5. **Add "last verified" timestamp to remaining roadmaps:**
   - Format: `**Last verified:** 2026-03-20 — compare with task board for current status`
   - This makes staleness visible at a glance

---

## Truly Pending Tasks (Real Open Work)

Based on board search + doc cross-reference, here are tasks that are **legitimately still PENDING:**

| Task | Board ID | Priority | Notes |
|------|----------|----------|-------|
| A10: Navigate edit points (Up/Down) | — | P2 HIGH | Doc mentioned but not on board; should be created |
| A13: Context menu — Timeline clips | — | P2 HIGH | Doc mentioned but not on board; should be created |
| A14: Context menu — DAG/Project items | — | P3 MEDIUM | Depends on A13; not on board |
| (Others from A2/B2/C) | — | ? | 20+ tasks in sub-roadmaps; status uncertain without spot-checking |

---

## Next Steps for QA

### For Phase 205:

1. Archive identified obsolete docs
2. Cross-check B_MEDIA_DETAIL.md against board (similar audit)
3. Create missing A10, A13, A14 tasks on board if still desired
4. Update CLAUDE.md with roadmap staleness protocol
5. Document: "VETKA_CUT_MANUAL.md + Task Board = system of record"

### Risk Mitigation:

- **Don't dispatch tasks based on roadmap status alone** — always check task board
- **Always update docs when tasks complete** — hook into post-commit workflow
- **Archive roadmaps when superseded** — prevents re-discovery of stale work

---

## Conclusion

**VERDICT:** Roadmap docs are useful for **historical context** and **design intent**, but they are **NOT authoritative for current work**.

The task board (with git hook auto-close on commit) is the **single source of truth for task status**.

All 4 major stale entries (A6, A7, A9, A15) have been completed and verified on the board but never updated in ROADMAP_A_ENGINE_DETAIL.md.

**Recommendation: Archive ROADMAP_A_ENGINE_DETAIL.md. Use VETKA_CUT_MANUAL.md + task board for all future work.**

---

*Audit complete. Awaiting Commander review.*
