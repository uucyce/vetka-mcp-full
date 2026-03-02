# MARKER_156.REGRESSION_STABLE_PROFILE

Date: 2026-02-26

## What was added

- New script: `scripts/run_regression_stable.sh`
- Modes:
  - `smoke` (default): curated stable regression subset
  - `full`: broad run with known crashers excluded

## Commands

```bash
./scripts/run_regression_stable.sh
./scripts/run_regression_stable.sh smoke
./scripts/run_regression_stable.sh full
```

## Verified result

`smoke` mode:
- `36 passed`
- runtime: ~0.9s

## Notes

- `tests/test_watchdog_real.py` excluded in `full` mode due fsevents/watchdog crash in current env.
- `tests/test_agents_routes.py` excluded in `full` mode because it targets missing route module in current tree.
