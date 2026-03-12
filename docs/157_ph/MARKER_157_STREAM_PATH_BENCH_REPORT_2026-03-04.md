# MARKER 157: Stream-Path Debug + Bench Report (2026-03-04)

## Scope completed
1. Fixed stream-path instability in provider registry.
2. Added interrupt-dialog benchmark scenario (user interrupts model and asks follow-up).
3. Added stronger quality scoring (relevance + language + timeout penalties).
4. Re-ran benchmark matrix on API + local models.

## Code changes
- `src/elisya/provider_registry.py`
  - Restored Ollama stream path to direct `httpx` NDJSON streaming (`trust_env=False`) instead of SDK path that produced `ResponseError 503`.
  - Added runtime marker for first token: `[STREAM_V2] first token in ...ms`.
  - Added safe stream-source close in `finally`.
- `scripts/voice_mode_benchmark.py`
  - Added prompt: `interrupt_1` (interrupt + follow-up turn benchmark).
  - Added quality scoring heuristic + `quality_notes` field.
  - Made `ContextPacker.pack` call signature-compatible (optional `force_jepa`).
  - Made `ProgressiveTtsService.stream_sentences` call signature-compatible (optional `session_key`).
  - Added local-model prompt fitting (`BENCH_LOCAL_PROMPT_CHAR_BUDGET`) to avoid local context overload in grounded mode.
  - Increased configurable TTS timeout: `BENCH_TTS_CLIENT_TIMEOUT_SEC`.

## Main benchmark run (post-fix)
Source artifacts:
- `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_062919.json`
- `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_062919.csv`
- `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260304_062919.md`

### Summary (p50)
- `B_api_tts`
  - success: `0.75`
  - reaction_text_ms_p50: `2216.28`
  - e2e_ms_p50: `4237.45`
  - quality_mean: `0.6062`
- `C_api_jepa_tts`
  - success: `1.0`
  - reaction_text_ms_p50: `1613.84`
  - e2e_ms_p50: `3825.75`
  - quality_mean: `0.8063`
- `D_ollama_tts` (llama3.2:3b)
  - success: `1.0`
  - reaction_text_ms_p50: `567.45`
  - e2e_ms_p50: `2893.75`
  - quality_mean: `0.7875`
- `E_ollama_jepa_tts` (llama3.2:3b)
  - success: `1.0`
  - reaction_text_ms_p50: `609.33`
  - e2e_ms_p50: `3306.36`
  - quality_mean: `0.775`
- `F_mimo_short`
  - success: `1.0`
  - reaction_text_ms_p50: `2322.18`
  - e2e_ms_p50: `3212.74`
  - quality_mean: `0.8`

## Interrupt scenario results (`prompt_id=interrupt_1`)
- API + JEPA (`C`) and local (`D/E`) now complete follow-up turn after interruption.
- Best observed post-interrupt TTFT in this run:
  - `D_ollama_tts`: `123.35ms`
  - `E_ollama_jepa_tts`: `115.89ms`
- Quality on interrupt rows is mostly `0.7–0.85`; main penalty is verbosity (`too_long_after_interrupt`).

## Key findings
1. Stream-path root cause was provider-side implementation path for Ollama; switching to direct HTTP fixed recurring `503` in benchmark flow.
2. Local `llama3.2:3b` currently gives the best reaction speed in this harness.
3. JEPA assist improved API quality/stability (`C > B`) but does not beat local speed in this setup.
4. `ttfa_audio_ms` remains `null` in this harness run because benchmark TTS chunk capture path still doesn't emit chunks in this specific pipeline/profile combination (while `/tts/generate` endpoint itself is healthy and returns audio). Text reaction metrics are valid.

## Search-system side effect check
Search benchmark-noise filtering remains effective for normal descriptive queries after these runs:
- Memory abbreviations query returns `VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md` as top.
- Input matrix query returns `MARKER_155_INPUT_MATRIX_SCANNER_CONTRACT.md` / `input_matrix_idea.txt` in top set.

## Recommended next step
- Stabilize benchmark audio chunk capture (resolve `ttfa_audio_ms=null`) by aligning benchmark speaker/language/profile with the exact production voice route used in live Jarvis mode.
