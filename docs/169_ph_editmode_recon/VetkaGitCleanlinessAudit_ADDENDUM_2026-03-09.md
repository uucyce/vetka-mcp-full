# Vetka Git Cleanliness Recon — Addendum (2026-03-09)

Reference report reviewed:
- `docs/169_ph_editmode_recon/VetkaGitCleanlinessAudit.md`

This addendum re-checks current directory/commit cleanliness against live git state.

## A) What is outdated in the original report

1. `all tracked changes are staged locally` — **not true now**.
2. Ahead count `16 commits ahead of origin` — still true for current branch ref,
   but original report does not reflect the much larger working tree drift (new docs/tests/scripts).

## B) Current branch/commit state (local refs)

- Branch: `codex/mcc-wave-d-runtime-closeout`
- Divergence vs `origin/codex/mcc-wave-d-runtime-closeout` (local remote ref): `0 behind / 16 ahead`
- Divergence vs `origin/main` (local remote ref): `0 behind / 197 ahead`

Recent commit stream is active and mixed (feature + fix + docs + tooling), including:
- player-lab/media/mcc/myco fixes and features (2026-03-08..2026-03-09)
- install/bootstrap additions (2026-03-07)
- naming/oss docs harmonization (2026-03-06..2026-03-07)

## C) Current dirty tree exposure (live)

- Tracked modified: **55**
- Untracked: **275**

Hotspots by directory prefix:
- `docs`: 160
- `tests`: 102
- `src`: 25
- `client`: 23
- `scripts`: 9

Most concentrated subtrees:
- `tests/phase159`: 39
- `docs/155_ph`: 30
- `docs/157_ph`: 28
- `docs/162_ph_MCC_MYCO_HELPER`: 19
- `docs/contracts`: 19
- `client/src`: 18
- `docs/163_ph_myco_VETKA_help`: 18
- `docs/164_MYCO_ARH_MCC`: 15

## D) Concrete cleanliness risks

1. **Review fatigue risk**
   - Massive docs/tests churn mixed with runtime/frontend edits.
2. **Noise ingress risk**
   - untracked runtime/tool dirs: `.media_cache/`, `.ocr_cache/`, `.playwright-cli/`, `client/test-results/`, `pulse_playground/`.
3. **Commit scope blur**
   - branch combines product fixes, exploratory tools, and long digest trails.

## E) Recommended cleanup strategy (non-destructive)

1. Keep current feature branch for code-critical work only.
2. Move digest-heavy docs into dedicated docs branch/PR slice by phase.
3. Add ignore rules for local runtime artifacts:
   - `.media_cache/`
   - `.ocr_cache/`
   - `.playwright-cli/`
   - `client/test-results/`
   - `pulse_playground/`
4. Stage commits in small topical batches:
   - `client/src + src/*` (runtime/feature)
   - `tests/*` (contracts)
   - `docs/*` (phase reports) separately

## F) Marker set

- `MARKER_GIT_CLEANUP.3` — addendum freshness check
- `MARKER_GIT_CLEANUP.SCOPE_SPLIT` — keep feature/docs/tests split in separate commits
- `MARKER_GIT_CLEANUP.NOISE_IGNORE` — ignore local cache/test-output directories

