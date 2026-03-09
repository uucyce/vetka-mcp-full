# Vetka Git Cleanliness Recon

Date: 2026-03-09
Scope: branch/directory cleanliness, staged-vs-unstaged drift, doc/test noise risk

## 1. Branch health snapshot

- Current branch: `codex/mcc-wave-d-runtime-closeout`
- Ahead/behind vs `origin/codex/mcc-wave-d-runtime-closeout`: `0 behind / 16 ahead`
- No merge-conflict states in `git status` (`UU`, `AA`, etc. absent)

Markers:
- `MARKER_GIT_CLEANUP.1` keep digest/doc scatter out of routine commits
- `MARKER_GIT_CLEANUP.2` avoid accidental wide `client/src` + backend merges while branch is ahead

## 2. Strict validation of prior claims

### Claim: "All tracked changes are staged locally"
- Status: **OUTDATED**
- Evidence: current `git status --porcelain` shows many ` M` entries (unstaged tracked modifications).

### Claim: "Tracked changes are broad (client/docs/src/tests/run.sh)"
- Status: **ACTUAL**
- Evidence: modified paths span all of these areas.

### Claim: "Untracked noise includes runtime caches and outputs"
- Status: **ACTUAL**
- Evidence: `?? .media_cache/`, `?? .ocr_cache/`, `?? .playwright-cli/`, `?? client/test-results/`, `?? pulse_playground/`.

### Claim: "Digest contamination risk in phase docs"
- Status: **ACTUAL**
- Evidence: large untracked clusters in `docs/155_ph`, `docs/157_ph`, `docs/162_*`, `docs/163_*`, `docs/164_*`.

Validation marker:
- `MARKER_GIT_CLEANUP.VALIDATION_2026-03-09`

## 3. Current exposure metrics (live)

- Tracked modified: **55**
- Untracked: **275**

Largest top-level pressure zones:
- `docs`: 160
- `tests`: 102
- `src`: 25
- `client`: 23

Hot subtrees:
- `tests/phase159`: 39
- `docs/155_ph`: 30
- `docs/157_ph`: 28
- `docs/162_ph_MCC_MYCO_HELPER`: 19
- `docs/contracts`: 19

Markers:
- `MARKER_GIT_CLEANUP.DOC`
- `MARKER_GIT_CLEANUP.DIGEST`

## 4. Recommendations

1. Split commit streams by concern:
   - code/runtime (`client/src`, `src/*`)
   - tests/contracts (`tests/*`)
   - phase docs (`docs/*`) in dedicated doc commits/PRs
2. Ignore local runtime noise:
   - `.media_cache/`, `.ocr_cache/`, `.playwright-cli/`, `client/test-results/`, `pulse_playground/`
3. Keep transcript-style or bulk phase dumps out of feature commits.
4. Establish a team cleanliness guide for future agents/humans.

Markers:
- `MARKER_GIT_CLEANUP.CACHE`
- `MARKER_GIT_CLEANUP.CLEAN`
- `MARKER_GIT_CLEANUP.SCOPE_SPLIT`

## 5. Implementation status (this phase)

- [x] Audit deepened and validated against current git state.
- [x] Noise ignore policy implemented in `.gitignore`.
- [x] Team-facing guide added: `docs/GIT_CLEANLINESS_GUIDE.md`.
- [ ] Working tree fully cleaned (intentionally not auto-cleaned to avoid deleting active work from parallel agents).

Implementation marker:
- `MARKER_GIT_CLEANUP.IMPLEMENT_2026-03-09`
