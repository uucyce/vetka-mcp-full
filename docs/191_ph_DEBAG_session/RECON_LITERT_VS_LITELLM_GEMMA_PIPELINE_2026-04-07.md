# RECON: LiteRT vs LiteLLM — Gemma Pipeline Clarification
**Date:** 2026-04-07
**Task:** tb_1775571427_88421_1 (parent recon)
**Status:** FINAL UNDERSTANDING

---

## Two Different Things With Similar Names

### LiteLLM (proxy/translator)
- **What:** OpenAI-compatible API proxy from BerriAI
- **Purpose:** Translates API formats (Anthropic ↔ OpenAI ↔ Ollama)
- **Port:** 4000
- **Status:** INSTALLED, RUNNING
- **Role in chain:** free-code → LiteLLM (:4000) → Ollama (:11434)
- **Verdict:** NEEDED as format translator between free-code and Ollama

### LiteRT (on-device AI runtime)
- **What:** Google's evolution of TensorFlow Lite for on-device ML inference
- **Purpose:** GPU/NPU/Metal hardware acceleration for ML models
- **Supports:** Android, iOS, macOS, Windows, Linux, Web
- **Features:** CompiledModel API, OpenCL, Metal, WebGPU, zero-copy buffers
- **Package:** `ai_edge_litert`
- **Status:** NOT INSTALLED (litert_smoke_bench.py returns blocked)
- **Role:** Should accelerate Gemma inference via Metal on M4
- **Verdict:** NEEDS INSTALLATION — without it Gemma runs slower than possible

### Zeta's Bridge (DELETE)
- **What:** `litellm_gemma_bridge.py` on port 4001
- **Purpose:** Intercept SSE stream, buffer entire response, parse XML tool calls
- **Problem:** Buffers ALL output before forwarding = 2+ min perceived latency
- **Status:** MUST BE REMOVED
- **Verdict:** Fifth wheel. Strict system prompt solves tool-call formatting without blocking

---

## The Correct Gemma Pipeline

### Current (broken — Zeta's setup):
```
free-code → bridge (:4001) [BUFFERS ALL] → LiteLLM (:4000) → Ollama (CPU/Metal?) → model
                    ↑ DELETE THIS
```

### Target (fast — based on Polaris benchmarks):
```
free-code → LiteLLM (:4000) → Ollama (:11434) + Metal GPU → model
                                        ↑
                              + LiteRT acceleration (TO INSTALL)
```

### Tool-call format solution:
- **NOT:** Block-buffering bridge that catches XML
- **YES:** Strict system prompt that forces Gemma to output correct format
- Polaris proved: strict prompt = 9.5x speedup + clean output
- Same approach for XML (Claude Code format) as for JSON

---

## Polaris Benchmark Summary (from BENCHMARK_RESULTS_LIVE.md)

| Model | Task | Time | Notes |
|-------|------|------|-------|
| gemma4:e2b | Cold start | 5.3s → 0.38s warm | 16x speedup with warm cache |
| gemma4:e4b | Task enrichment | 26.3s | 2x faster than Qwen 3.5 (53.9s) |
| gemma4:e4b | With strict prompt | 0.73s | 9.5x vs without (6.9s) |
| phi4-mini | Code classification | 3.8s | Fastest accurate drone |

**Key insight:** Ollama already uses Metal GPU (43/43 layers offloaded, 8.9 GiB on Metal).
LiteRT would add ADDITIONAL acceleration layer on top.

---

## Qwen 3.5 + LiteRT Reference

Qwen 3.5 as Sherpa already works fast and quiet with LiteRT optimization.
This is the baseline we need to match/exceed with Gemma.

---

## Action Items

1. **DELETE** `litellm_gemma_bridge.py` (or archive to backup/)
2. **INSTALL** LiteRT (`ai_edge_litert`) for Metal acceleration
3. **UPDATE** spawn_synapse.sh: free-code → LiteLLM (:4000) direct, no bridge
4. **CREATE** strict system prompt for XML tool-call format (like Polaris did for JSON)
5. **TEST** E2E: spawn Gemma agent → tool call → verify response time

---

## Name Collision Prevention

| Abbreviation | Full Name | What It Does | Port |
|---|---|---|---|
| **LiteLLM** | LiteLLM (BerriAI) | API format proxy | :4000 |
| **LiteRT** | LiteRT (Google) | On-device ML acceleration | N/A (runtime) |
| **Bridge** | litellm_gemma_bridge.py | SSE buffering wrapper (DELETE) | :4001 |
| **Ollama** | Ollama | Model serving | :11434 |

---

## Execution Order (agreed with user)

**Phase 1: Unlock Gemma**
1. Install LiteRT
2. Remove bridge, wire free-code → LiteLLM direct
3. Strict XML system prompt
4. E2E test
5. Verify Gemma helps (benchmarks match Polaris)

**Phase 2: Unlock Alpha-Gamma Team**
1. Fix memory pipeline (3 wires: load_recent + ENGRAM ingestion + file watcher)
2. Set tmux history-limit appropriately
3. Verify agents retain context across sessions
4. All hands on CUT
