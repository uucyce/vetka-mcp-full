# VETKA CUT Sandbox Scripts

P170.1 foundation helpers for bootstrapping and syncing a standalone `VETKA CUT` sandbox.

## Files
- `bootstrap_cut_sandbox.py` - creates isolated sandbox folders and config skeleton.
- `sync_cut_core_mirror.py` - copies mirrored upstream VETKA core files into `core_mirror/` using a manifest.

## Typical flow
```bash
python3 scripts/cut/bootstrap_cut_sandbox.py \
  --sandbox-root "$HOME/Documents/VETKA_CUT_SANDBOX"

python3 scripts/cut/sync_cut_core_mirror.py \
  --source-root "$(pwd)" \
  --sandbox-root "$HOME/Documents/VETKA_CUT_SANDBOX"
```

## Notes
- The sandbox is intended to live outside the main repo by default.
- `core_mirror/` is for mirrored upstream files, not casual direct editing.
- CUT-owned code should live outside `core_mirror/`.
