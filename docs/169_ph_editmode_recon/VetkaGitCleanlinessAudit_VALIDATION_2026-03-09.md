# Vetka Git Cleanliness Audit Validation (2026-03-09)

Source validated:
- `docs/169_ph_editmode_recon/VetkaGitCleanlinessAudit.md`

Validation method:
- `git status --porcelain`
- `git rev-list --left-right --count origin/codex/mcc-wave-d-runtime-closeout...HEAD`
- recent commit log snapshot (`git log --oneline -n 12`)

## Line-by-line verdict

1. Claim: branch is `codex/mcc-wave-d-runtime-closeout` and 16 commits ahead of origin.
- Verdict: **ACTUAL**
- Evidence: `git rev-list ...` => `0 16`.

2. Claim: "All tracked changes are staged locally".
- Verdict: **OUTDATED / FALSE**
- Evidence: `git status --porcelain` shows many lines prefixed with ` M` (modified, unstaged), not only staged entries.

3. Claim: no merge conflicts now.
- Verdict: **ACTUAL (at snapshot time)**
- Evidence: no conflict markers (`UU`, `AA`, etc.) in status.

4. Claim: tracked changes are broad and include client/docs/run.sh/services/tests.
- Verdict: **ACTUAL**
- Evidence: modified paths include `client/*`, `docs/*`, `run.sh`, `src/*`, `tests/*`.

5. Claim: untracked noise includes caches and test outputs (`.media_cache`, `.ocr_cache`, `.playwright-cli`, `client/test-results`).
- Verdict: **ACTUAL**
- Evidence: all listed directories present as `??` in status.

6. Claim: digest contamination risk (`docs/155_ph` and similar bulk phase docs).
- Verdict: **ACTUAL**
- Evidence: large untracked sets in `docs/155_ph`, `docs/157_ph`, `docs/162_*`, `docs/163_*`, `docs/164_*`.

7. Recommendation: split digest/doc bulk into dedicated branch/PR.
- Verdict: **VALID RECOMMENDATION**
- Evidence: current tree has high docs/tests volume relative to focused code changes.

8. Recommendation: add cache/test-output directories to `.gitignore`.
- Verdict: **VALID RECOMMENDATION (NOT DONE)**
- Evidence: current `.gitignore` does not include `.media_cache`, `.ocr_cache`, `.playwright-cli`, `client/test-results`, `pulse_playground`.

9. Recommendation: review huge transcript-style docs before merge.
- Verdict: **VALID RECOMMENDATION**
- Evidence: modified/untracked docs include long-form report/transcript directories.

## Summary

- **Accurate core diagnosis:** dirty tree, high docs/tests churn, risk of mixed-scope commits.
- **Primary outdated point:** staged-state assertion is no longer true.
- **Action priority now:** apply ignore rules for runtime noise and split commit streams (code/tests/docs).

## Marker

- `MARKER_GIT_CLEANUP.VALIDATION_2026-03-09`
