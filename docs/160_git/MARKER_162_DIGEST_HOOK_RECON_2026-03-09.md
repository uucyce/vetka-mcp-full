# MARKER_162_DIGEST_HOOK_RECON_2026-03-09

## Scope
- Investigate noisy non-blocking pre-commit hook around digest auto-update.
- Confirm whether `data/project_digest.json` is updated when dependencies are missing.

## Reproduction
Command:

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python3 scripts/update_project_digest.py
```

Observed:
- `ModuleNotFoundError: No module named 'requests'` in `get_mcp_status()`.
- Followed by `UnboundLocalError` at `except requests.exceptions.ConnectionError`.
- Script exits with non-zero code.

## Hook Behavior
File:
- `.git/hooks/pre-commit`

Behavior:
- Runs `python3 scripts/update_project_digest.py`.
- On failure prints warning: `Digest update failed (non-critical, continuing commit)`.
- Always exits `0`.

Consequence:
- Commit succeeds.
- Digest update is skipped (or left stale) on each failed run.
- Repeating warning noise masks useful hook signal.

## Root Cause
- `get_mcp_status()` references `requests.exceptions.ConnectionError` even when `import requests` fails.
- This triggers a secondary exception (`UnboundLocalError`) and crashes the script.

## Fix Plan
1. Harden `scripts/update_project_digest.py`:
   - Handle missing `requests` dependency explicitly.
   - Avoid referencing `requests` when import failed.
   - Return degraded status instead of raising.
2. Add regression test for `requests`-missing path.
3. Re-run script to verify it completes and writes digest without noisy failure.
