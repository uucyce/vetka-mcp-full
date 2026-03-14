# Vetka Web Search Health Audit

## Problem observed
While using the search lane (`web/` context) the UI shows: **"Web provider unavailable: configure Tavily or Serper key"** (see screenshot). Agents can no longer fetch internet results because the backend reports no healthy provider even though the config contains `"tavily": "tvly-dev-..."` and all other components (KeyManager, web search tool) are wired correctly.

## Root cause (marker: `MARKER_169.TAVILY_CAPABILITY_ENV`)
`src/api/handlers/unified_search.py::get_search_capabilities` uses `bool(os.getenv("TAVILY_API_KEY"))` to set `provider_health.tavily.available`. That means capability gating is tied to an *environment variable*, not to the actual keys stored in `data/config.json` (or the UnifiedKeyManager). As a result, if `TAVILY_API_KEY` is absent from `process.env`, the UnifiedSearchBar displays the error shown in the screenshot despite the key being configured.

## Evidence
- `data/config.json` includes `"tavily": "tvly-dev-..."`, so KeyManager knows about the key. (`ProviderType.TAVILY` is registered.)
- `src/mcp/tools/web_search_tool.py` calls `km.get_key_with_rotation(ProviderType.TAVILY)` and would succeed if a key existed. No exception is thrown, so the API can talk to Tavily.
- The UI block is triggered when `/api/search/capabilities?context=web` returns `provider_health.tavily.available === false`, which comes directly from the env check.

## How to verify
1. Call `curl http://localhost:8000/api/search/capabilities?context=web`. The response currently contains `{"provider_health": {"tavily": {"available": false}}}`.
2. Set `TAVILY_API_KEY` in the runtime environment (`export TAVILY_API_KEY=tvly-dev-…`). Restart the backend and rerun the endpoint: the flag should flip to `true`, the UI stops showing the error, and `web/` searches return results again.
3. Alternatively, implement a fix (Option B below) and rerun the same call to ensure availability is derived from KeyManager.

## Remediation options
1. **Quick fix (dev/env level):** Export the Tavily key as `TAVILY_API_KEY` in every environment (local shell, `scripts/run_dev.sh`, Docker env). The backend will then report the provider as available, and the UI will allow `web/` queries again. This is what agents should do when their search lane breaks: copy the TVLY key from `data/config.json` or the key drawer and export it before restarting.
2. **Permanent fix (code change):** Update `get_search_capabilities` to ask `UnifiedKeyManager` whether a key exists (`get_key_with_rotation(ProviderType.TAVILY)`) instead of relying on env vars. That aligns the UI capability flag with the rest of the key stack and removes the mismatch that causes false negatives.

## Recommendations for agents
- When you see the “configure Tavily or Serper key” toast, confirm `curl /api/search/capabilities?context=web` (or `GET /search/capabilities`). If `provider_health.tavily.available` is `false`, export `TAVILY_API_KEY` and restart `run.sh`/`run_vetka.sh` before retrying search.
- Avoid committing the key to git; prefer storing it in `~/.bashrc` or `env.local`. Use the existing `data/learned_key_patterns.json` as reference for key format if you need to re-add it.
- Long term, propose Option B to prevent future outages (the annotation `MARKER_169.TAVILY_CAPABILITY_ENV` in `src/api/handlers/unified_search.py` records where the fix belongs).

Report saved in `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/169_ph_editmode_recon/VetkaWebSearchHealth.md`. Include the image of the toast for further audits.
