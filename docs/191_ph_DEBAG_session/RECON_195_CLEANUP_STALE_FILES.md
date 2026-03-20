# RECON: Phase 195 — Stale Files & Junk Cleanup

**Date:** 2026-03-20
**Phase:** 195
**Author:** Opus (Claude Code)
**Severity:** LOW (hygiene, no runtime impact)

---

## Problem Statement

After Phase 195 bug fixes (post-merge hook duplication, promote_to_main hardening),
a full scan revealed ~4.6 GB of stale backups, empty directories, and metadata junk
scattered across the project. None of it affects runtime, but it bloats the repo,
confuses searches, and makes worktree operations slower.

---

## Cleanup Targets (Verified)

### Category A: Stale Backups (~5.8 MB)

| File | Size | Date | Action |
|------|------|------|--------|
| `data/task_board.json.bak` | 1.3M | Mar 19 | KEEP (latest backup) |
| `data/chat_history.backup_20260216_192427.json` | 4.4M | Feb 16 | MOVE to quarantine |
| `data/chat_history.empty_backup.json` | 4K | Mar 15 | MOVE to quarantine |
| `data/backups/task_board_before_closed_cleanup_*.json` | 140K | Mar 9 | MOVE to quarantine |
| `.vetka_backups/` (8 .bak files) | 40K | Feb-Mar | MOVE to quarantine |

**Rule:** Keep `data/task_board.json.bak` (latest, Mar 19). Move everything else.

### Category B: Qdrant Snapshot (4.5 GB)

| Path | Size | Date |
|------|------|------|
| `data/qdrant_snapshots/backup_20260301_185855/` | 4.5G | Mar 1 |
| `data/qdrant_snapshots/tmp/` | 0B | empty |
| `data/qdrant_snapshots/vetka_elisya/` | 0B | empty |

**Note:** This is the single largest cleanup target. The backup is 20 days old (Mar 1).
Current Qdrant data lives in the running instance, not in this snapshot.

### Category C: Voice Storage (29 MB)

| Path | Size | Files |
|------|------|-------|
| `data/voice_storage/` | 29M | 27 files (.wav, .webm) |

Old voice recording artifacts. Not referenced by any active code path.

### Category D: Empty Directories

| Path | Status |
|------|--------|
| `hooks/` | Empty (stale hook was deleted in 195.1) |
| `archive/` | Empty |
| `data/qdrant_snapshots/tmp/` | Empty |
| `data/weaviate_backups/` | Empty |

### Category E: Metadata Junk

| What | Count | Action |
|------|-------|--------|
| `.DS_Store` files | 103 | MOVE to quarantine |
| `.pytest_cache/` dirs | 3 | MOVE to quarantine |

---

## NOT Touching (Explicit Exclusions)

| What | Why |
|------|-----|
| 10 stale git branches (codex/*) | User decision — Codex workflow unclear |
| `data/reflex/` | Active reflex system data |
| `data/task_board.json.bak` | Latest backup, keep as safety net |
| `data/chat_history.json` (4.4M) | Active chat history |
| `data/task_board.db` + `.db-wal` | Active SQLite database |
| Worktree directories | All healthy, user manages Codex |
| React hooks in worktrees | Not git hooks, legitimate code |

---

## Execution Protocol

### SAFETY-FIRST APPROACH

**Philosophy:** We do NOT delete anything directly. We QUARANTINE first, test, then
the user deletes manually after visual inspection.

### Step-by-step:

```
1. CREATE quarantine directory:
   _quarantine_195/

2. MOVE (not delete!) all targets into quarantine:
   _quarantine_195/
     backups/
       chat_history.backup_20260216_192427.json
       chat_history.empty_backup.json
       task_board_before_closed_cleanup_20260309_061713.json
       vetka_backups/   (entire .vetka_backups/ content)
     qdrant_snapshot/
       backup_20260301_185855/   (4.5 GB)
     voice_storage/              (27 files, 29 MB)
     empty_dirs_marker.txt       (list of empty dirs that were removed)
     ds_store/                   (103 .DS_Store files, preserving paths)
     pytest_cache/               (3 cache dirs)

3. REMOVE empty directories:
   hooks/  archive/  data/qdrant_snapshots/tmp/  data/weaviate_backups/

4. RUN KEY TESTS:
   .venv/bin/pytest tests/test_phase195_promote_guard.py \
                    tests/test_phase184_worktree_merge.py \
                    tests/test_phase193_reflex_guard.py \
                    tests/test_phase136_auto_close_commit.py -v

   Expected: all pass (none of these tests depend on moved files)

5. VERIFY MCP server health:
   curl http://localhost:5001/health

6. SHOW quarantine to user:
   du -sh _quarantine_195/
   ls -la _quarantine_195/

   User inspects and deletes: rm -rf _quarantine_195/
```

---

## Safety Warnings

1. **NEVER `rm -rf` directly.** Always `mv` to quarantine first.
   If something breaks, we can `mv` back in seconds.

2. **Qdrant snapshot (4.5 GB):** If Qdrant DB gets corrupted and we need
   to restore, this backup is the only lifeline. Verify Qdrant is healthy
   BEFORE moving. Check: `curl http://localhost:6333/collections` (if running).

3. **Voice storage:** If any user workflow uses voice input/TTS, these files
   might be needed. Check `grep -r "voice_storage" src/` for references.

4. **`.DS_Store` removal** is purely cosmetic. macOS will recreate them.
   No risk, but also no lasting benefit unless added to `.gitignore`.

5. **Disk space:** Total cleanup = ~4.6 GB. Mostly the Qdrant snapshot.
   If disk is not tight, this is low priority.

6. **Do NOT compress the quarantine folder** until after tests pass.
   If tests fail, we need fast access to move files back.
   Archive ONLY after user confirms everything works.

---

## Gitignore Additions (Recommended)

Already covered:
- `.DS_Store` (yes)
- `backups/` (yes)

Should add:
```
data/qdrant_snapshots/backup_*/
data/voice_storage/
.vetka_backups/
_quarantine_*/
```

---

## Affected Files Summary

```
MOVE to quarantine:
  data/chat_history.backup_20260216_192427.json     (4.4M)
  data/chat_history.empty_backup.json               (4K)
  data/backups/                                     (140K)
  .vetka_backups/                                   (40K)
  data/qdrant_snapshots/backup_20260301_185855/     (4.5G)
  data/qdrant_snapshots/tmp/                        (0B)
  data/qdrant_snapshots/vetka_elisya/               (0B, empty)
  data/voice_storage/                               (29M)
  103x .DS_Store files
  3x .pytest_cache/ directories

REMOVE (empty):
  hooks/
  archive/
  data/weaviate_backups/

KEEP:
  data/task_board.json.bak                          (1.3M, latest)
```

**Total savings: ~4.6 GB**
