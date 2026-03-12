MARKER_171.MYCO.WEB_SEARCH.ERROR.TRIGGER.PROJECT.V1
LAYER: L2
DOMAIN: SEARCH|MYCO|RUNTIME|UX
STATUS: PROJECT_BRIEF
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_171_MYCO_WEB_SEARCH_ERROR_TRIGGER_PROJECT_2026-03-11.md
LAST_VERIFIED: 2026-03-11

# PHASE_171_MYCO_WEB_SEARCH_ERROR_TRIGGER_PROJECT_2026-03-11

## Synopsis
Project brief for MYCO scenario authoring around `web/` search failures and degraded states.

Goal:
replace vague search failures like `source_errors` or `No results found` with a deterministic contract:

`runtime failure -> error_code -> UI state -> MYCO proactive trigger -> concrete remediation`

This is not just backend telemetry.
It is a scenario package for MYCO so the helper can explain exactly what is broken and what the user should do next.

## Why this project exists
Current behavior is too weak:
1. `web/` can fail with an empty list and no explanation.
2. `source_errors` is too generic for user-facing guidance.
3. MYCO cannot reliably distinguish:
   - no provider key
   - provider timeout
   - provider returned zero results
   - capability gate mismatch
   - runtime/backend version mismatch
4. Result: the lane says `No results found`, while the real problem may be operational, not semantic.

## Clarification: why `3d` showed only 5 results
In recent manual checks, `3d` returned 5 because the diagnostic calls explicitly used `limit=5`.

Important distinction:
1. Tavily itself can return more than 5 results.
2. Current UI request path uses a fixed limit, not true pagination.
3. Existing search lane visually suggests expandable results, but `web/` does not yet have a canonical cursor/load-more contract.

## Verified code-path findings
As of 2026-03-11, the active code contract is:

1. `UnifiedSearchBar.tsx` sends `limit: 20` for `web/` searches.
2. `/api/search/unified` accepts that limit and forwards it into `run_unified_search(...)`.
3. `run_unified_search(...)` forwards `limit` into `_web_search(query, limit)`.
4. `_web_search(...)` calls `WebSearchTool.execute({"max_results": min(limit, 10)})`.
5. `WebSearchTool.execute(...)` clamps again with `max_results = min(arguments.get("max_results", 3), 10)`.

Consequence:
1. `web/` is currently hard-capped at `10` fetched provider rows even when UI asks for `20`, `50`, or more.
2. The earlier observed `5` was not the global runtime cap; it was a manual diagnostic limit.
3. The real current product cap is `10`.

## Why existing "Load more" is misleading for `web/`
The lane already has a `Load more` button, but its current behavior is local-only:

1. `useSearch.ts` keeps `displayLimit` client-side.
2. `loadMore()` only increases how many already-fetched results are shown.
3. For `vetka/`, this can still be useful because the socket path may already hold a larger set.
4. For `web/`, this is not real pagination, because provider fetch is capped upstream and no cursor/offset is requested.

Consequence:
1. `Load more` in `web/` is currently a display affordance, not provider pagination.
2. After the first `10` rows, there is nothing more to reveal.
3. MYCO should not imply "more web results exist locally" unless backend explicitly says so.

So there are two separate product tasks:
1. restore trustworthy error reporting;
2. design real `load more` / pagination for web search.

## Product bug statement
Today the user sees a search lane that visually suggests:
- many web results,
- expandable browsing,
- and generic failure explanations.

But the real runtime behavior is:
- hard cap at `10`,
- no provider cursor contract,
- string-only `source_errors`,
- no deterministic MYCO guidance.

This mismatch is exactly why the MYCO scenario package is needed.

## Product statement
MYCO should not say generic lines like:
- `web provider unavailable`
- `no results found`

MYCO should instead say concrete, state-aware instructions, for example:
- `Tavily key exists, but the backend process was started before the latest search patch. Restart backend on :5001.`
- `Your query is too short for web search. Add one more token like "3d icon" or "3d modeling".`
- `Tavily answered successfully but returned zero relevant matches. Try broader wording or switch to vetka/file.`

## Proposed runtime contract

### 1. Error envelope
All `web/` failures or degraded states should emit a structured payload:

```json
{
  "context": "web",
  "provider": "tavily",
  "error_code": "WEB_PROVIDER_TIMEOUT",
  "severity": "warning",
  "user_visible": true,
  "retryable": true,
  "results_count": 0,
  "query": "3d",
  "mode": "keyword",
  "detail": "Tavily request timed out after 8s",
  "remediation": {
    "action": "retry_or_refine_query",
    "hint_id": "myco.web.timeout.retry"
  }
}
```

### 2. Event contract
MYCO should listen to a dedicated event, not infer from raw text only:

`vetka-myco-search-error`

Minimal event detail:
- `scope`
- `context`
- `provider`
- `error_code`
- `severity`
- `query`
- `results_count`
- `retryable`
- `detail`
- `hint_id`

### 3. Success-but-weak contract
Not every issue is a hard error.
We also need degraded but valid states:
- `WEB_ZERO_RESULTS`
- `WEB_LOW_CONFIDENCE_RESULTS`
- `WEB_RESULTS_TRUNCATED`
- `WEB_PAGINATION_NOT_AVAILABLE`

These should also be triggerable MYCO scenarios.

## Error code taxonomy

### A. Query/input errors
1. `WEB_QUERY_TOO_SHORT`
Meaning: user entered fewer than the minimum effective characters/tokens.
MYCO action: ask to expand the query, with one concrete example.

2. `WEB_QUERY_TOO_GENERIC`
Meaning: syntactically valid, but too broad/underspecified for useful web ranking.
MYCO action: propose 2-3 refinements like `3d icon`, `3d modeling`, `3d animation icon`.

### B. Key/provider setup errors
3. `WEB_PROVIDER_KEY_MISSING`
Meaning: no Tavily/Serper key is available in runtime.
MYCO action: direct user to API Keys / phonebook and say which provider is missing.

4. `WEB_PROVIDER_KEY_PRESENT_BUT_CAPABILITY_FALSE`
Meaning: key inventory says provider exists, but capability endpoint says unavailable.
MYCO action: explain this is a runtime/config mismatch, not user error.

5. `WEB_PROVIDER_SDK_MISSING`
Meaning: provider library is not installed or import failed.
MYCO action: show developer/operator remediation, not user blame.

### C. Provider/network/runtime errors
6. `WEB_PROVIDER_TIMEOUT`
Meaning: provider request timed out.
MYCO action: suggest retry, narrower query, or fallback to another context.

7. `WEB_PROVIDER_HTTP_ERROR`
Meaning: upstream returned 4xx/5xx.
MYCO action: mention provider and status, then suggest retry/fallback.

8. `WEB_PROVIDER_RATE_LIMITED`
Meaning: provider key is temporarily exhausted or throttled.
MYCO action: explain cooldown/fallback behavior.

9. `WEB_PROVIDER_EMPTY_RESPONSE`
Meaning: request succeeded but provider returned no rows unexpectedly.
MYCO action: say provider responded but found nothing; offer reformulation.

### D. Internal VETKA pipeline errors
10. `WEB_RESULT_NORMALIZATION_FAILED`
Meaning: provider returned rows but adapter dropped them.
MYCO action: explain this is internal pipeline failure, not bad query.

11. `WEB_RUNTIME_CODE_MISMATCH`
Meaning: current backend process behavior does not match current workspace code expectations.
MYCO action: tell operator to restart backend/runtime surface.

12. `WEB_PAGINATION_NOT_AVAILABLE`
Meaning: current result set is capped and lane cannot fetch next page yet.
MYCO action: say results are truncated and broader browse requires explicit follow-up.

13. `WEB_PROVIDER_RESULT_CAP_REACHED`
Meaning: provider returned the maximum currently allowed rows for this runtime slice, so the lane may be truncated even without an explicit provider error.
MYCO action: explain that current web browse is capped and suggest refining query or waiting for real pagination support.

## MYCO trigger matrix
| Trigger ID | Runtime condition | Error code | MYCO deterministic short hint | Deeper helper explanation | Silence rule |
|---|---|---|---|---|---|
| W-01 | query length below threshold | `WEB_QUERY_TOO_SHORT` | `Запрос слишком короткий для web/. Добавь ещё одно слово.` | `Для web/ лучше уточнить тему: например, "3d icon" вместо "3d".` | stay silent while user keeps typing |
| W-02 | no Tavily/Serper key | `WEB_PROVIDER_KEY_MISSING` | `У web/ сейчас нет ключа провайдера.` | `Открой API Keys и добавь Tavily или Serper.` | do not repeat after same state key |
| W-03 | key exists but capability false | `WEB_PROVIDER_KEY_PRESENT_BUT_CAPABILITY_FALSE` | `Ключ есть, но runtime web/ не видит его корректно.` | `Это похоже на рассинхрон capability и runtime. Нужен backend restart или fix capability gate.` | once per backend state hash |
| W-04 | timeout | `WEB_PROVIDER_TIMEOUT` | `Web provider не ответил вовремя.` | `Попробуй повторить запрос или уточнить его. Если повторяется, это уже runtime/network issue.` | silent during auto-retry |
| W-05 | upstream HTTP/rate limit | `WEB_PROVIDER_HTTP_ERROR` / `WEB_PROVIDER_RATE_LIMITED` | `Провайдер web/ сейчас отвечает ошибкой.` | `Это не ошибка твоего запроса; можно повторить позже или сменить источник.` | one hint per cooldown period |
| W-06 | provider returns 0 rows | `WEB_PROVIDER_EMPTY_RESPONSE` | `Провайдер ответил, но ничего не нашёл.` | `Попробуй более широкий или более предметный запрос.` | no repeat if query unchanged and already acknowledged |
| W-07 | adapter drops provider rows | `WEB_RESULT_NORMALIZATION_FAILED` | `Web results потерялись внутри VETKA-пайплайна.` | `Провайдер отдал данные, но агрегатор/адаптер их не донёс до UI.` | developer-facing only unless user opens diagnostics |
| W-08 | UI result cap hit | `WEB_PAGINATION_NOT_AVAILABLE` | `Показана только верхняя часть web results.` | `Для полного browse нужен load more / cursor contract.` | do not spam on every search |
| W-09 | fetched rows hit current hard cap | `WEB_PROVIDER_RESULT_CAP_REACHED` | `Web results сейчас обрезаны по runtime cap.` | `Сейчас lane получает только верхний блок результатов. Для большего нужен cursor/offset path.` | only once per query + cap signature |

## Copy direction for MYCO scenario writer
Tone:
1. short
2. operational
3. concrete
4. no vague apology loops

Good:
- `Tavily ключ есть, но backend ещё не перечитал новый search runtime. Перезапусти :5001.`
- `Провайдер ответил пусто. Попробуй "3d icon" или "3d modeling".`

Bad:
- `Что-то пошло не так.`
- `Попробуйте позже.`
- `No results found.` without context

## Required backend fields
Current `source_errors` is not enough.

Need a structured object per source:

```json
{
  "source_errors": {
    "web": {
      "provider": "tavily",
      "error_code": "WEB_PROVIDER_TIMEOUT",
      "severity": "warning",
      "detail": "timeout after 8s",
      "retryable": true,
      "results_count": 0,
      "hint_id": "myco.web.timeout.retry"
    }
  }
}
```

Recommended extension for truncation-aware states:

```json
{
  "source_errors": {
    "web": {
      "provider": "tavily",
      "error_code": "WEB_PROVIDER_RESULT_CAP_REACHED",
      "severity": "info",
      "detail": "Current runtime clamps Tavily max_results to 10",
      "retryable": false,
      "results_count": 10,
      "results_truncated": true,
      "provider_cap": 10,
      "requested_limit": 20,
      "hint_id": "myco.web.cap.truncated"
    }
  }
}
```

## Required UI behavior
1. If `error_code` exists, lane must not collapse everything into plain `No results found`.
2. Deterministic MYCO trigger should be fed from `error_code`, not substring heuristics.
3. If `results_count > 0` but `results_truncated=true`, show `load more` affordance or explicit truncation note.
4. `web/` and `MYCO` should share the same state key so repeated identical failures do not spam.
5. If `results_count == provider_cap`, lane should show `Top 10 web results` style copy until true pagination exists.
6. `Load more` must be visually disabled or relabeled unless backend confirms `has_more=true`.

## Scope split

### In scope for MYCO scenario package
1. error taxonomy
2. trigger matrix
3. short/deep hint text
4. silence rules
5. fallback routing between `web/`, `vetka/`, `file/`

### Not in scope
1. actual Tavily provider implementation
2. full pagination backend
3. provider billing logic
4. broad cloud/social expansion

## Deliverables for scenario author
1. deterministic trigger matrix for all `WEB_*` codes
2. short RU hints
3. optional EN mirror hints
4. deep helper explanation texts
5. silence and dedupe policy
6. remediation verbs mapped to real UI controls

## Recommended next implementation slice
1. Replace string-only `source_errors` with structured `error_code` payload.
2. Emit `vetka-myco-search-error`.
3. Add `WEB_PAGINATION_NOT_AVAILABLE`, `WEB_PROVIDER_RESULT_CAP_REACHED`, and `results_truncated`.
4. Split `Load more` into:
   - local reveal only
   - real provider pagination
5. Bind MYCO short hint to lane state when `web/` fails or truncates.
6. Add browser/runtime test matrix for `web/`.

## Implementation notes for scenario writer handoff
The MYCO writer should assume three distinct families of user-facing moments:

1. Hard failure:
   - key missing
   - timeout
   - upstream HTTP failure
   - runtime mismatch

2. Soft degradation:
   - query too short
   - query too generic
   - zero results
   - low-confidence results

3. Truncation:
   - provider cap reached
   - pagination not available
   - local-only load more

These need different copy, different silence rules, and different remediation verbs.

## Cross-links
- [PHASE_163A_MYCO_MODE_A_SCENARIO_MATRIX_2026-03-08.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/163_ph_myco_VETKA_help/PHASE_163A_MYCO_MODE_A_SCENARIO_MATRIX_2026-03-08.md)
- [MYCO_SCENARIO_AUTHOR_CHECKLIST_V1.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/163_ph_myco_VETKA_help/MYCO_SCENARIO_AUTHOR_CHECKLIST_V1.md)
- [MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/163_ph_myco_VETKA_help/MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1.md)
