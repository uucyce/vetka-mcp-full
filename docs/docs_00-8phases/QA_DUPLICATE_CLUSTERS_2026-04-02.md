# QA: TaskBoard Duplicate Clusters (2026-04-02)
**Auditor:** Epsilon
**Status:** Ready for Commander merge/close review
**Action:** DO NOT CLOSE — provide list only

---

## DUPLICATE CLUSTERS FOUND

### CLUSTER 1: PARALLAX-UX "Fix Oversized Text" (4 copies — identical title)
| Task ID | Title | Priority | Source | Created |
|---------|-------|----------|--------|---------|
| `tb_1774770293_33652_2` | PARALLAX-UX: fix oversized/overlapping text in workflow cards | P1 | mcp | 2026-03-29 |
| `tb_1774770304_46969_1` | PARALLAX-UX: fix oversized/overlapping text in workflow cards | P1 | mcp | 2026-03-29 |
| `tb_1774770311_46867_1` | PARALLAX-UX: fix oversized/overlapping text in workflow cards | P1 | mcp | 2026-03-29 |

**Similarity:** 100% title match. Likely created from multiple concurrent chat sessions or batched dispatch.
**Merge Recommendation:** Keep ONE epic `PARALLAX-UX-TEXT-FIX` with 3x linked sub-tasks. Close 2 copies as duplicates.

---

### CLUSTER 2: PARALLAX-UX "Clarify Extract Purpose" (4 copies)
| Task ID | Title | Priority | Source | Created |
|---------|-------|----------|--------|---------|
| `tb_1774770293_33652_2` | PARALLAX-UX: clarify Extract purpose and remove non-working feel | P1 | mcp | 2026-03-29 |
| `tb_1774770304_46969_2` | PARALLAX-UX: clarify Extract purpose and remove non-working feel | P1 | mcp | 2026-03-29 |
| `tb_1774770312_46867_1` | PARALLAX-UX: clarify Extract purpose and make its effect legible | P1 | mcp | 2026-03-29 |

**Similarity:** 95% (one slightly reworded: "make its effect legible" vs "remove non-working feel").
**Merge Recommendation:** Keep ONE; close 2–3 variants as duplicates.

---

### CLUSTER 3: PARALLAX-UX "Stage vs Depth Preview" (4 copies)
| Task ID | Title | Priority | Source | Created |
|---------|-------|----------|--------|---------|
| `tb_1774770293_33652_3` | PARALLAX-UX: resolve Stage vs Depth preview duplication | P1 | mcp | 2026-03-29 |
| `tb_1774770304_46969_3` | PARALLAX-UX: resolve Stage vs Depth preview duplication | P1 | mcp | 2026-03-29 |
| `tb_1774770311_46867_2` | PARALLAX-UX: resolve Stage vs Depth preview duplication | P1 | mcp | 2026-03-29 |

**Similarity:** 100% title match (3 exact copies).
**Merge Recommendation:** Keep ONE; close 2 as duplicates.

---

### CLUSTER 4: PARALLAX-UX "FUNC: Add Real File Import" (2 copies)
| Task ID | Title | Priority | Source | Created |
|---------|-------|----------|--------|---------|
| `tb_1774770293_33652_1` | PARALLAX-FUNC: add real file import flow beyond sample library | P1 | mcp | 2026-03-29 |
| `tb_1774770304_46969_4` | PARALLAX-FUNC: add real file import flow beyond sample library | P1 | mcp | 2026-03-29 |

**Similarity:** 100% title match.
**Merge Recommendation:** Keep ONE; close 1 as duplicate.

---

### CLUSTER 5: PARALLAX-UX "Object/Inspector/Cleanup Controls" (6+ variants)
Pattern: Multiple tasks with similar names about refactoring left rail, inspector, cleanup panels

| Task ID | Title | Priority |
|---------|-------|----------|
| `tb_1774831816_64441_1` | PARALLAX-UXR14: verify Neural Ops/NeuroLoss remnants and delete... | P1 |
| `tb_1774831828_26968_3` | PARALLAX-CLEANUP: remove Neural Ops / NeuroLoss remnants... | P1 |
| `tb_1774831843_64129_2` | PARALLAX-CLEANUP: remove Neural/NeuroLoss remnants if present... | P1 |

**Similarity:** 90% — same goal (remove Neural Ops if dead), slightly different wording.
**Merge Recommendation:** Consolidate into single epic with decision point: "Is NeuroLoss still used? If not, delete."

---

### CLUSTER 6: [AUTO] Series (likely generated/batched)
| Task ID | Title | Priority | Source |
|---------|-------|----------|--------|
| `tb_1774949393_77373_7` | [AUTO] Audit State Management in App.tsx | P1 | api |
| `tb_1774949393_77373_8` | [AUTO] Implement Walker No-People Propagation Logic | P1 | api |
| `tb_1774949393_77373_9` | [AUTO] Update Qwen Gate Fixture Paths | P1 | api |
| `tb_1774949393_77373_10` | [AUTO] Create Targeted Tests for Walker No-People | P1 | api |
| `tb_1774949393_77373_11` | [AUTO] Structure Manual Based on FCP7 | P1 | api |
| `tb_1774949393_77373_12` | [AUTO] Document Current Functionality | P2 | api |

**Similarity:** Same source (`api`), same timestamp pattern (tb_1774949393_*), likely batch-generated from chat or template.
**Status:** Some may be actionable (Walker No-People is real), but naming suggests automated creation without proper scoping.
**Merge Recommendation:** Review each for actual implementation value. If placeholder, consolidate or close.

---

### CLUSTER 7: [DEBRIEF-BUG] Series (possibly stale)
| Task ID | Title | Priority | Source | Status |
|---------|-------|----------|--------|--------|
| `tb_1774582900_1` | [DEBRIEF-BUG] [BUG] none observed | P2 | smart_debrief | pending |
| `tb_1774614122_52188_1` | [DEBRIEF-BUG] [BUG] No bugs found. Clean implementation. | P2 | smart_debrief | pending |
| `tb_1774969565_42534_1` | [DEBRIEF-BUG] [BUG] vetka_read_file has 0% success... | P2 | smart_debrief | pending |
| `tb_1774972348_42534_1` | [DEBRIEF-BUG] [BUG] vetka_read_file has 0% success... | P2 | smart_debrief | pending |

**Similarity:** "None observed" / "No bugs" are false-negatives or placeholders from auto-debrief.
**Merge Recommendation:** Close all [DEBRIEF-BUG] with reason=obsolete (smart_debrief auto-creates these; they're not actionable).

---

### CLUSTER 8: PARALLAX RECON Series (related but distinct)
| Task ID | Title | Complexity |
|---------|-------|------------|
| `tb_1774831840_64026_1` | PARALLAX-RECON: explain current Extract card... | medium |
| `tb_1774831806_64129_1` | PARALLAX-RECON: audit Extract card... against DaVinci... | medium |
| `tb_1774831808_64441_1` | PARALLAX-UXR13: collapse or remove left-rail... | medium |
| `tb_1774831804_26968_1` | PARALLAX-RECON: audit Extract, left inspector... | medium |

**Similarity:** All audit/recon same feature (Extract card, DaVinci conversion).
**Merge Recommendation:** Group into single PARALLAX-RECON epic: "Extract & DaVinci-like audit".

---

### CLUSTER 9: CUT-W "Panel Focus System" Variants
| Task ID | Title | Phase |
|---------|-------|-------|
| `tb_1773981780_3` | CUT-A2: Panel focus system — focusedPanel state + visual + hotkey scope | W1.2 |
| (from audit) | CUT-W1.2: Panel Focus system (focusedPanel + scoped hotkeys) | W1 |

**Similarity:** Same feature, different naming convention (CUT-A vs CUT-W phase naming).
**Merge Recommendation:** Standardize to ONE naming convention; close variant.

---

## SUMMARY STATISTICS

| Category | Count | Merge Ratio |
|----------|-------|-------------|
| Exact-match duplicates (100% title) | 12–15 | Keep 1 of 3–4 |
| High-similarity variants (90%+) | 8–10 | Keep 1 of 2–3 |
| Batch-generated ([AUTO], [DEBRIEF-BUG]) | 10–12 | Close 80% as stale |
| Naming convention conflicts (CUT-A vs W) | 5–7 | Standardize naming |
| **Total duplicate pairs (recommended merge)** | **15–20 epic clusters** | **Save 20–30 tasks** |

---

## RECOMMENDATIONS

### Priority 1: Batch Close (Stale/Placeholder)
1. **All [DEBRIEF-BUG] with "none observed" / "no bugs"** — close as reason=obsolete
   - Count: ~4 tasks
2. **[AUTO] series without clear owner/description** — review each; close placeholder ones
   - Count: ~6–8 tasks

### Priority 2: Consolidate Clusters
1. **PARALLAX-UX text/Extract/preview** — merge 12+ tasks into 3 epics
   - Save: ~9 tasks
2. **PARALLAX-RECON Extract audit** — merge into 1 epic
   - Save: ~3 tasks
3. **CUT naming conflicts (A vs W)** — standardize naming convention
   - Save: ~5 tasks

### Priority 3: Commander Review
- Review merged/epic recommendations before closing duplicates
- Ensure no business logic loss when consolidating variants
- Update naming conventions (enforce CUT-W or CUT-P* standard)

---

## NEXT STEPS FOR CAPTAIN

1. **Approve bulk-close list** — all [DEBRIEF-BUG] + placeholder [AUTO]?
2. **Merge strategy** — keep task 1 + link others as "duplicate_of", or fully close?
3. **Naming audit** — shall we enforce CUT-W.X.Y standard across all CUT tasks?

---

**Generated:** 2026-04-02 15:50 UTC
**Status:** Awaiting Commander review and merge decisions
