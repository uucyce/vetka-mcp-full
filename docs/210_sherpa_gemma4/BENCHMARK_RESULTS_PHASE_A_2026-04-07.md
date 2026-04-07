# Benchmark Results — Phase A (Ollama + Metal GPU, pre-LiteRT)
**Date:** 2026-04-07
**Hardware:** M4 Mac, 24GB RAM
**Runtime:** Ollama + Metal GPU (43/43 layers offloaded)
**LiteRT:** Installed (ai_edge_litert 2.1.3) but NOT yet optimized
**Task:** tb_1775575539_88421_6

## Sequential Benchmark (no GPU contention)

### MICRO (Drone tier)
| Model | Accuracy | Avg Time | Grade | Notes |
|-------|----------|----------|-------|-------|
| tinyllama | 100% | **0.4s** | A | Surprise champion — all 3/3 correct |
| gemma4:e2b | 100% | 3.2s | A | Reliable, slower due to chain-of-thought |
| phi4-mini | 67% | 1.0s | B | Failed error categorization (runtime vs import) |
| gemma3:1b | 67% | 0.4s | B | Fast but inaccurate on error category |

**Winner:** tinyllama (0.4s, 100%) — but needs more tests to confirm
**Reliable:** gemma4:e2b (3.2s, 100%) — consistent

### SCOUT
| Model | Accuracy | Avg Time | Grade | Notes |
|-------|----------|----------|-------|-------|
| gemma4:e2b | 100% | 4.0s | **A** | Perfect: relevance + file routing |
| phi4-mini | 50% | 1.1s | C | Failed file path routing (said src/ instead of tests/) |

**Winner:** gemma4:e2b — clear champion for Scout role

### SHERPA
| Model | Accuracy | Avg Time | Grade | Notes |
|-------|----------|----------|-------|-------|
| gemma4:e4b | 100% | **4.0s** | **A** | JSON:clean + XML:clean, **8x faster than Qwen** |
| qwen3.5 | 100% | 32.1s | A | Same accuracy, 8x slower |

**Winner:** gemma4:e4b — replaces Qwen 3.5 as Sherpa

### ALPHA-GAMMA (Code Generation + Tool Use)
| Model | Accuracy | Avg Time | Grade | Notes |
|-------|----------|----------|-------|-------|
| gemma4:e4b | 100% | **6.1s** | **A** | Code gen + XML tool call, **7x faster** |
| qwen3.5 | 100% | 41.8s | A | Same accuracy, 7x slower |

**Winner:** gemma4:e4b — clear champion for Alpha-Gamma role

## XML Tool-Call Benchmark (separate test)
| Model | Clean XML | Avg Time | Grade |
|-------|-----------|----------|-------|
| gemma4:e2b | 3/3 | 11.9s | A |
| gemma4:e4b | 3/3 | 24.7s | A |
| phi4-mini | 3/3 | 12.1s | A |
| qwen3.5 | 3/3 | 17.1s | A |

All models produce clean XML with strict system prompt. No bridge needed.

## Recommended Role Assignment

| Role | Model | Why |
|------|-------|-----|
| MICRO (Drone) | tinyllama or gemma4:e2b | tinyllama fastest, e2b most reliable |
| SCOUT | gemma4:e2b | Only model with 100% on routing tasks |
| SHERPA | gemma4:e4b | 8x faster than Qwen, same accuracy |
| ALPHA-GAMMA | gemma4:e4b | 7x faster than Qwen, clean XML tool calls |
| VISION | gemma4:e4b (untested this run) | Polaris data: 37.8s, structured analysis |

## Key Insight: Bridge Was Unnecessary
Zeta's litellm_gemma_bridge.py (port 4001) buffered entire responses, adding 2+ min latency.
Strict system prompt achieves 100% clean XML/JSON output on all models.
Bridge archived to backup/phase_210_bridge/.

## vs Polaris Benchmarks (2026-04-05)

| Metric | Polaris | This Run | Delta |
|--------|---------|----------|-------|
| gemma4:e2b classification | 9.6s | 3.2s | **3x faster** (warm cache) |
| gemma4:e4b enrichment | 26.3s | 4.0s | **6.5x faster** (warm + strict prompt) |
| phi4-mini classification | 3.8s | 1.0s | **3.8x faster** (warm cache) |
| qwen3.5 enrichment | 53.9s | 32.1s | 1.7x faster (warm cache) |

Models were warm from XML test run. Cold start would be slower.

## Next: Phase B (with LiteRT optimization)
- Same tests after LiteRT Metal acceleration is wired into Ollama pipeline
- Expected: additional 1.4x GPU speedup per Google benchmarks

## Test Scripts (saved to tests/benchmark/)
- `benchmark_sequential.py` — 4 roles, quality + speed
- `benchmark_xml_toolcall.py` — XML tool-call format validation
