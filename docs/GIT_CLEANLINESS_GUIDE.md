# Git Cleanliness Guide (VETKA)

Purpose: keep commits reviewable in a multi-agent, high-churn monorepo.

## 1) Split by scope

Use separate commits (or PR slices) for:
- `code/runtime` changes (`client/src`, `src/*`)
- `tests/contracts` (`tests/*`)
- `phase docs/digests` (`docs/*`)

Do not mix all three in one commit unless absolutely required.

## 2) Keep runtime noise out of git

Ignored local artifacts include:
- `.media_cache/`
- `.ocr_cache/`
- `.playwright-cli/`
- `client/test-results/`
- `pulse_playground/`

Never commit local secrets:
- `docs/160_git/secret.r`
- `docs/160_git/secret.rtf`

## 3) Pre-commit checklist

1. `git status --short`
2. verify staged files match ticket scope
3. if docs are bulk phase logs, commit separately
4. ensure no local cache/output dirs are staged

## 4) Team policy markers

- `MARKER_GIT_CLEANUP.1`: keep digest/doc scatter out of routine commits
- `MARKER_GIT_CLEANUP.2`: avoid accidental broad merges while branch is ahead
- `MARKER_GIT_CLEANUP.SCOPE_SPLIT`: commit code/tests/docs separately
- `MARKER_GIT_CLEANUP.CACHE`: keep runtime noise ignored

## 5) References

- Audit recon:
  - `docs/169_ph_editmode_recon/VetkaGitCleanlinessAudit.md`
