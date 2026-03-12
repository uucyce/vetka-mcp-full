# MARKER 157: Local Model Race + Search Noise Check (2026-03-04)

## Scope
- Download local models from Grok shortlist.
- Run comparable grounded voice benchmarks for local Ollama paths.
- Verify that benchmark artifacts no longer pollute normal VETKA search results.

## Downloaded / Available models
- `gemma3:latest`
- `llama3.2:3b`
- `qwen3:8b`
- `qwen2.5:7b`
- `qwen2.5:3b`
- `deepseek-r1:8b`

## Benchmark setup
- Script: `scripts/voice_mode_benchmark.py`
- Modes: `D_ollama_tts`, `E_ollama_jepa_tts`
- Grounded context: `on`
- Main run (decision-grade): `runs-per-prompt=3`, timeout 25s
- Smoke pass (faster full matrix): `runs-per-prompt=1`, timeout 20s

## Results (summary)
All tested local models produced the same outcome in current pipeline state:
- `success_rate = 0.0` for both `D_ollama_tts` and `E_ollama_jepa_tts`
- dominant failure: per-run timeout
- repeated runtime warning during stream close:
  - `RuntimeError: aclose(): asynchronous generator is already running`
- repeated semantic backend instability during grounded context prep:
  - embedding batch fallback 503
  - Engram/Qdrant init/readiness 503 in benchmark process

This indicates a **system-level bottleneck in local stream voice path**, not a model ranking issue yet.

## Artifact files
Decision-grade runs:
- `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_042048.json` (gemma3:latest)
- `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_042949.json` (llama3.2:3b)

Smoke matrix runs:
- `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_044108.json` (gemma3:latest)
- `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_044351.json` (llama3.2:3b)
- `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_044705.json` (qwen3:8b)
- `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_045030.json` (qwen2.5:7b)
- `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_045321.json` (qwen2.5:3b)
- `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_045614.json` (deepseek-r1:8b)

Audio artifacts are under:
- `docs/157_ph/benchmarks/audio/`

## Search noise validation
### Query 1
`Найди файл где все абревиатуры с памятью связано`
- benchmark hits in top-20: `0`
- top result: `docs/besedii_google_drive_docs/VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md`

### Query 2
`Найди файл где все матрицы инпутов`
- benchmark hits in top-20: `0`
- top results include:
  - `docs/155_ph/MARKER_155_INPUT_MATRIX_SCANNER_CONTRACT.md`
  - `docs/136_ph_Knowledge level_from_Phase 72/input_matrix_idea.txt`

### Query 3 (benchmark-intent)
`phase157 voice benchmark wav`
- benchmark hits in top-20: present (expected behavior)

## Conclusion
- Model download phase is complete.
- Search pollution fix behaves correctly for normal descriptive queries.
- Voice ranking is currently blocked by stream pipeline reliability (timeouts + async close race), so model comparison cannot yet be trusted for speed/quality decisions.
