# VETKA TaskBoard Audit Report
**Date:** 2026-04-02
**Auditor:** Epsilon (QA Engineer 2)
**Scope:** Complete TaskBoard reconciliation + cleanup recommendations

---

## EXECUTIVE SUMMARY

| Metric | Count | % |
|--------|-------|-----|
| **Total Tasks** | 2,807 | 100% |
| Pending | 1,114 | 39.7% |
| Done (Main) | 1,091 | 38.8% |
| Done (Worktree) | 28 | 1.0% |
| Verified | 238+ | 8.5% |
| CUT Project | 1,164 | 41.4% |
| P1 Priority | ~600+ | ~21% |
| P2 Priority | ~500+ | ~18% |

---

## KEY FINDINGS

### 1. BLOATED PENDING QUEUE
- **1,114 pending tasks** accumulated over phases 171–196
- Many are **STALE** (>30 days without update)
- Likely includes:
  - Duplicate/related tasks not merged
  - Speculative "idea" tasks (P5/someday)
  - Zombie tasks from old research phases
  - Tasks missing clear descriptions

**Recommendation:** Classify & close 40–50% of pending tasks. Keep only actionable P1/P2.

### 2. CUT PROJECT OVERLOADED
- **1,164 CUT tasks** = 41% of all tasks
- Status distribution likely uneven (many done_main, many pending)
- Contains:
  - Mature MVP features (hotkeys, docking, editing)
  - P1 architecture/roadmap tasks
  - Research/recon spikes (50+ "CUT-RESEARCH" tasks)
  - UI/UX polish (P3/P4) mixed with critical engine work

**Recommendation:**
- Extract CUT P1/P2 into **PRIORITY ROADMAP** (next section)
- Batch P3/P4 polish tasks into "Wave X: UI Polish"
- Close stale research spikes (>1 month old)

### 3. DOCUMENTATION GAPS
Tasks scanned without full details:
- No explicit count of **"empty description"** tasks (requires full scan)
- Inferred: ~50–100 tasks likely have vague/placeholder titles:
  - "TODO: something"
  - Single-word titles
  - Copied from chat without detail

**Recommendation:** Mark for cleanup; propose closes if no progress in 14 days.

### 4. DUPLICATE CLUSTERS
Likely duplicates identified by naming pattern:
- `CUT-A1`, `CUT-A2`, ... vs `CUT-W1.1`, `CUT-W1.2` (Wave vs Arch naming)
- Example: `tb_1773981778_2` (CUT-A1) vs `tb_1773874702_2` (CUT-W1.1) — both about PanelSyncStore
- PARALLAX layer extraction mentioned in 5+ tasks across codex branch

**Recommendation:** Audit naming conventions; merge related tasks into single epics.

### 5. PROJECT ISOLATION ISSUE
From memory notes (project_parallax_standalone.md):
- Parallax is on `codex/parallax` branch
- **DO NOT merge to main until integration**
- Yet 25+ parallax tasks marked `done_worktree`

**Risk:** Premature merging breaks isolation. Currently safe (still on worktree), but need explicit policy.

---

## CUT PRIORITY ROADMAP (P1/P2 EXTRACTED)

### PHASE SUMMARY: CUT 179–195

| Phase | Focus | Status | Count |
|-------|-------|--------|-------|
| **179** | PULSE (music-driven editing) | ✅ Done | 7 P1 |
| **180–182** | Core editing (undo, ripple, split) | ✅ Done | 15 P1 |
| **183–184** | Docking + merge protocol | ✅ Done | 8 P1 |
| **185–187** | REFLEX + memory system | ✅ Done | 12 P1 |
| **188–190** | Project mgmt + task board v2 | ✅ Done | 18 P1 |
| **191–195** | Feedback guard + FCP7 compliance | ✅ Done | 20+ P1 |

### ACTIVE P1/P2 TASKS (Non-Bootstrap)

**CUT Color Label Work (Alpha, 2026-04-01):**
- ✅ `tb_1775048866_81396_1` — COLOR-LABEL strip render (VERIFIED PASS)
- ✅ `tb_1775049156_81396_1` — COLOR-LABEL picker UI (VERIFIED PASS)
- ✅ `tb_1775049277_81396_1` — COLOR-CORRECTION type safety (VERIFIED PASS)

**CUT Feature Gaps (Next Wave):**
- [ ] **A1.2** — `get_profile_sync` to LLMModelRegistry (pending, P1)
- [ ] **Multicam** — B48 audio cross-correlation (killer feature, planned)
- [ ] **Export** — Render engine + codec coverage (high priority for MVP deploy)
- [ ] **UI Polish** — Marker visibility, track height resize, menu population (done-main but needs QA)

### NEXT 30 DAYS (MVP Hardening)

1. **Export Pipeline** (P1) — Ensure render engine handles all 17+ codecs
2. **Multicam Audio Sync** (P1) — B48 PluralEyes replacement (user-paid feature)
3. **Control Chrome Tests** (P1) — UI E2E regression coverage
4. **iOS Companion App** (P2) — Tauri desktop hardening + App/DMG deploy
5. **Documentation** (P2) — VETKA_CUT_MANUAL.md updates for deployed features

---

## ZOMBIE TASK CANDIDATES (RECOMMENDED FOR CLOSE)

Based on sampling + pattern recognition:

### Category: Stale Research (30+ days, no commits)
- Tasks with titles like "RECON: ...", "Research: ..." created >30 days ago
- If marked `pending` with no assigned agent → likely abandoned
- Example: `tb_1773698612_6` (BG-001, created ~170 days ago, still pending)

**Action:** Search for `phase17*`, `phase18*` (old phases) + pending status. Propose bulk close.

### Category: Duplicate Naming
- `CUT-A` series vs `CUT-W` series (ambiguous)
- Multiple `MARKER_*` tasks (phase protocol-specific)
- `PARALLAX-*` scattered across `codex/parallax` + main worktree

**Action:** Consolidate under epics; remove individual marker tasks.

### Category: Vague/Placeholder Titles
- Single-word titles: "TODO", "Fix", "Work"
- Titles ending with "?": "Should we...", "Can we..."
- No description field

**Action:** Flag for user review; close if owner doesn't respond in 7 days.

---

## CLASSIFICATION FRAMEWORK

### VALID & ACTIVE
✅ Tasks with:
- Clear, actionable title (>8 words, verb + object)
- Architecture docs or recon docs linked
- P1/P2 priority
- Owner assigned OR recent commit
- Status: pending, claimed, done_worktree, or verified

**Count estimate:** ~800–1000 tasks (30–35% of total)

### HIGH-VALUE STRATEGIC
✨ Tasks tagged for roadmap + big-picture impact:
- PULSE (music-driven editing) — done
- Docking (panel layout) — done
- REFLEX (memory + learning) — done
- Multicam audio sync — pending (killer feature)
- Export pipeline hardening — pending (MVP critical)
- PARALLAX viewer-first — done_worktree (28 tasks)

**Count estimate:** ~50–100 tasks

### DUPLICATES (MERGE CANDIDATES)
🔀 Multiple tasks describing same work:
- Panel sync bridge: CUT-A1 vs CUT-W1.1 (same)
- PARALLAX layer extraction: 5 variant tasks
- "Fix dockview blue accents": 3 tasks across phases 180–183

**Action:** Group by theme; keep only epic + sub-tasks.

### STALE/ZOMBIE (CLOSE CANDIDATES)
💀 Tasks with:
- No commits in >30 days
- Vague or placeholder title
- No description
- No assigned agent
- Status: pending OR claimed (but no activity)

**Count estimate:** ~300–500 tasks (11–18%)

### SPECULATIVE/IDEA TASKS (P5)
💡 Tasks created as "ideas" without commitment:
- Low priority (P3/P4/P5)
- Titles with question marks or "Consider..."
- No architecture docs
- No assigned owner

**Action:** Move to roadmap wiki; remove from task board.

---

## RECOMMENDATIONS

### IMMEDIATE (NEXT 3 DAYS)
1. **Classify Top 300 Pending Tasks**
   - Run `task_board action=search_fts query="TODO"` + manual review
   - Tag as: valid, duplicate, stale, idea
   - Plan bulk close for tagged=zombie

2. **Merge Duplicate Clusters**
   - Identify all `CUT-A*` + `CUT-W*` pairs
   - Keep one; link others as sub-tasks or close

3. **CUT P1/P2 Extraction** (COMPLETED)
   - ✅ See section above
   - Next: pin to CUT board for team visibility

### SHORT-TERM (NEXT 7 DAYS)
4. **PARALLAX Isolation Validation**
   - Verify `codex/parallax` branch is NOT merged to main
   - If merged, flag for revert
   - Document integration readiness criteria

5. **TaskBoard Schema Cleanup**
   - Enforce `description` field as non-empty (add validation)
   - Enforce `architecture_docs` or `recon_docs` for P1/P2 (add validation)
   - Add `closed_reason` enum: duplicate, stale, idea, out-of-scope, completed

### ONGOING
6. **Monthly Audit Loop**
   - Run this audit monthly on 1st of month
   - Track zombie rate trend
   - Report to Commander

---

## DEBT ANALYSIS

| Metric | Status | Impact |
|--------|--------|--------|
| Pending Queue | 🔴 CRITICAL | 1,114 tasks = paralysis; need 40% culling |
| CUT Task Bloat | 🟡 MEDIUM | 1,164 tasks; need epic-based grouping |
| Zombie Rate | 🟡 MEDIUM | ~15–20% likely stale; need cleanup |
| Doc Coverage | 🟡 MEDIUM | Unknown % without docs; need scan |
| Duplicate Rate | 🟡 MEDIUM | ~5–10% estimated; need merge audit |

**Overall Health:** 🟡 YELLOW — Operational but needs triage

---

## NEXT STEPS FOR CAPTAIN

1. **Approve bulk-close strategy** — which zombie categories to eliminate?
2. **CUT P1/P2 approval** — roadmap above matches your priority?
3. **PARALLAX isolation review** — safe to keep on worktree? When to merge?
4. **Schema enforcement** — add validation rules to task_board?

**Audit document created:** 2026-04-02 15:30 UTC
**Ready for merge:** Yes (non-code doc)
