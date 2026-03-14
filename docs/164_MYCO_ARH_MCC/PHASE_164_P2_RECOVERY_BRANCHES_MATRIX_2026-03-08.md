# PHASE 164 — P2 Recovery Branches Matrix (2026-03-08)

Marker: `MARKER_164.P2.RECOVERY_BRANCHES_MATRIX.V1`

## Purpose
Make failure/recovery guidance deterministic and non-generic.

## Recovery Matrix
| ID | Failure class | Detection hint | Recovery guidance |
|---|---|---|---|
| R1 | zero keys / no provider | empty Balance key set | open Balance -> set active key -> retry |
| R2 | provider auth error | backend quick chat fallback + auth message | rotate key / provider in Balance -> retry |
| R3 | quota / rate limit | provider response limit / 429-like fallback | switch model/provider in Context/Balance |
| R4 | provider timeout/down | timeout fallback in quick chat | retry later or switch provider |
| R5 | disabled mode/feature | UI control disabled + guard note | guide to nearest runnable path |
| R6 | context mismatch (roadmap vs workflow) | workflow open but roadmap hint leaks | prefer workflow guidance branch |

## Notes
- Recovery guidance must be one-shot and deduped per state key.
- Recovery messages must not replace valid architect-only conversation when helper mode is off.

