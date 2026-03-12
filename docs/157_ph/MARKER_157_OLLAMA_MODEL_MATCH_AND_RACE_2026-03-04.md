# MARKER 157: Ollama Model Match + Local Race (2026-03-04)

## 1) Match vs Grok recommendations

- `Qwen3.5-9B`: not installed yet. `ollama pull qwen3.5:latest` is available, but it starts a large pull (~6.6 GB). We stopped it to avoid blocking the session.
- `Llama 3.2-3B`: installed (`llama3.2:3b`).
- `Gemma 3-9B`: exact tag `gemma3:9b` not found in Ollama. Closest available is installed `gemma3:latest` (~3.3 GB).
- `DeepSeek V3-7B`: exact practical local tag is not available as expected. `deepseek-v3:latest` in Ollama resolves to a giant model (~404 GB) and is not suitable for this local setup.

Installed practical set currently used for race:
- `llama3.2:3b`
- `qwen2.5:3b`
- `qwen2.5:7b`
- `qwen3:8b`
- `gemma3:latest`
- `deepseek-r1:8b`

## 2) Environment change

- Updated Ollama from `0.11.10` to `0.17.6`.

## 3) Local speed/quality race (D/E modes)

Source index:
- `docs/157_ph/benchmarks/local_model_race_20260304_ollama0176.jsonl`

### Best by TTFA (audio reaction, lower is better)
1. `qwen2.5:3b` + `E_ollama_jepa_tts` -> `ttfa_all=2333.23 ms`, `ttft_all=99.96 ms`, `quality=0.0625`
2. `qwen2.5:7b` + `E_ollama_jepa_tts` -> `ttfa_all=3476.21 ms`, `ttft_all=194.0 ms`, `quality=0.2125`
3. `qwen2.5:7b` + `D_ollama_tts` -> `ttfa_all=4963.94 ms`, `ttft_all=287.37 ms`, `quality=0.2125`

### Stability/quality note
- Fastest raw latency: `qwen2.5:3b + E`, but quality is weak in this run.
- Best balance (speed + quality among local tested): `qwen2.5:7b + E`.
- `qwen3:8b`, `deepseek-r1:8b` were unstable/slow for this voice benchmark profile.

## 4) Practical recommendation for Jarvis now

Use default local Jarvis pair for next phase:
- primary: `qwen2.5:7b` + `E_ollama_jepa_tts`
- low-latency fallback profile for fast checks: `qwen2.5:3b` + `E_ollama_jepa_tts`

Then (separately) we can do a controlled pull + race for `qwen3.5:latest` to verify if it beats `qwen2.5:7b` on your M4 in this exact pipeline.
