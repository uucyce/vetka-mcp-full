# MARKER_162B_OPENROUTER_UTILITY_WARNING_RECON_2026-03-06

## Scope
Investigate `[WARNING] OpenRouter call utility not found (src.elisya.openrouter_api)`.

## Evidence
- Warning originates in `src/elisya/api_aggregator_v3.py:107-121`.
- It imports from `src.elisya.openrouter_api` (`:110`), but that module does not exist in `src/elisya/`.
- OpenRouter key still loads successfully (`:105-117`).
- Live OpenRouter client exists elsewhere: `src/elisya/providers/openrouter_client.py` (used in `src/elisya/call_model_with_fallback.py:96-101`).

## Diagnosis
1. Warning is real: stale import path in `api_aggregator_v3.py`.
2. Not a full outage because other routing paths can still call OpenRouter via provider clients.
3. Risk is architectural confusion: one code path reports missing utility while another path is valid.

## Impact
- Startup noise and ambiguous operator signal.
- Potential dead branch in `api_aggregator_v3` when model selection expects `call_openrouter` from old path.

## Recommended Agent Task (separate)
- Normalize OpenRouter call path to a single canonical provider client.
- Remove legacy import branch and replace with explicit fallback/feature flag.
- Add startup self-check that verifies the effective OpenRouter call function, not just key presence.

## Acceptance Criteria
- No startup warning for missing OpenRouter utility path.
- A single documented call path for OpenRouter in runtime.
- Smoke test confirms one OpenRouter model can be called when key exists.
