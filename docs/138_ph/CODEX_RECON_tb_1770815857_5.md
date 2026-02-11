# MARKER_138.RECON_S2_5_MODEL_AUTODETECT
# Recon Report: tb_1770815857_5 (S2.5 Model Directory auto-detect)

Date: 2026-02-11
Workspace: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

## Scope
S2.5 Model Directory: auto-detect all models (Polza voice, local Qwen TTS, Ollama) and remove static assumptions.

## Findings
1. Frontend currently fetches three separate endpoints on open:
- `/api/models` (cloud)
- `/api/models/local` (Ollama)
- `/api/models/mcp-agents`
This split can lead to partial empty states and inconsistent source metadata.

2. Backend has strong discovery building blocks already:
- `get_all_models(force_refresh)` in `src/elisya/model_fetcher.py` (OpenRouter/Gemini/Polza/Poe/NanoGPT)
- `discover_ollama_models()` and `discover_voice_models()` in `src/services/model_registry.py`

3. Gap for S2.5 requirements:
- No single auto-detect endpoint that returns unified dynamic model inventory + categorized counts.
- No explicit local Qwen TTS server detection in model API responses.
- Polza models are fetched, but voice/stt/tts classification is not guaranteed for all provider payload variants.

## Planned isolated implementation
1. Add `GET /api/models/autodetect` in `src/api/routes/model_routes.py`:
- unified dynamic response for cloud/local/mcp + categories text/voice/image/embedding
- optional `force_refresh=true`
- detect local Qwen TTS health (port 5003) and add local voice model entry

2. Update `POST /api/models/refresh` to use autodetect pipeline and return richer stats.

3. Update `client/src/components/ModelDirectory.tsx`:
- replace triple-fetch boot with `/api/models/autodetect`
- refresh uses `/api/models/autodetect?force_refresh=true`
- keep existing provider/source badges rendering path

4. Add backend tests for autodetect route behavior and category output.
