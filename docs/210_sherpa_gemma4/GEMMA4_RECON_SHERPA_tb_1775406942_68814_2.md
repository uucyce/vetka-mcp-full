# SHERPA-210: Gemma 4 Recon -- Evaluate as Sherpa/Scout Candidate

**Task ID:** `tb_1775406942_68814_2`
**Agent:** Eta (Harness Engineer 2)
**Date:** 2026-04-05
**Phase:** 210 (Sherpa Model Evaluation)

---

## 1. Gemma 4 Family Overview

Released April 2, 2026 by Google DeepMind. Built from Gemini 3 architecture. Licensed **Apache 2.0** (confirmed -- a shift from prior Gemma releases which used a custom Gemma license). All four variants are available on HuggingFace, Ollama, and Kaggle.

### 1.1 Model Comparison Table

| Variant | Total Params | Effective/Active Params | Architecture | Context | Vision | Audio | Ollama Tag | Ollama Size | HF Downloads (it) |
|---------|-------------|------------------------|--------------|---------|--------|-------|------------|-------------|-------------------|
| **E2B** | 5.1B | 2.3B effective | Dense (any-to-any) | 128K | Yes | Yes | `gemma4:e2b` | 7.2 GB | 167K |
| **E4B** | 8.0B | 4.5B effective | Dense (any-to-any) | 128K | Yes | Yes | `gemma4:e4b` | 9.6 GB | 198K |
| **26B-A4B** | 26.5B | 3.8B active (MoE) | Mixture-of-Experts | 256K | Yes | No | `gemma4:26b` | 18 GB | 271K |
| **31B** | 32.7B | 32.7B (dense) | Dense | 256K | Yes | No | `gemma4:31b` | 20 GB | 490K |

**Key observations:**
- E2B and E4B are "any-to-any" models with both vision AND audio input support.
- 26B-A4B and 31B are image-text-to-text (vision input, text output -- no audio).
- All variants have native vision capability -- critical for Sherpa screenshot analysis.
- 31B ranks #3 on Arena AI text leaderboard; 26B-A4B ranks #6.
- All support function-calling, structured JSON output, and native system instructions.

### 1.2 Memory Budget Analysis (M4 Mac 24GB)

| Variant | Q4 (4-bit) | Q8 (8-bit) | BF16 | Fits 24GB at Q4? | Fits 24GB at Q8? |
|---------|-----------|-----------|------|-------------------|-------------------|
| E2B | ~4 GB | ~5-8 GB | ~10 GB | YES (plenty room) | YES |
| E4B | ~5.5-6 GB | ~9-12 GB | ~16 GB | YES (plenty room) | YES |
| 26B-A4B | ~16-18 GB | ~28-30 GB | ~52 GB | TIGHT (6-8 GB for KV cache) | NO |
| 31B | ~17-20 GB | ~34-38 GB | ~62 GB | TIGHT (4-7 GB for KV cache) | NO |

**With 256K context on MoE/Dense models, KV cache can consume 4-8 GB.** On 24GB M4:
- E4B Q8: ~12 GB model + plenty of room for context = **comfortable fit**
- 26B-A4B Q4: ~18 GB model + limited KV cache headroom = **usable but constrained** (may need to limit context to ~32K-64K in practice)
- 31B Q4: ~20 GB = **too tight** for meaningful context window

### 1.3 GGUF Quantization Availability

All four variants have multiple GGUF providers with strong community support:

| Provider | E2B | E4B | 26B-A4B | 31B |
|----------|-----|-----|---------|-----|
| **unsloth** (imatrix) | 177K dl | 317K dl | 487K dl | 409K dl |
| **lmstudio-community** | 35K dl | 92K dl | 304K dl | 68K dl |
| **bartowski** (imatrix) | 28K dl | 36K dl | 53K dl | 50K dl |
| **ggml-org** (official) | -- | -- | 47K dl | -- |

Quant levels available: Q2_K, Q3_K_S, Q3_K_M, Q3_K_L, Q4_0, Q4_K_S, **Q4_K_M** (recommended), Q5_K_S, Q5_K_M, Q6_K, **Q8_0**, BF16.

### 1.4 Ollama Availability

**Day-one support confirmed.** Available at `ollama.com/library/gemma4` with 17 tags.

```bash
# Quick install commands:
ollama pull gemma4:e4b      # 9.6 GB -- recommended for Sherpa
ollama pull gemma4:26b      # 18 GB  -- if memory allows
ollama pull gemma4:e2b      # 7.2 GB -- lightweight Scout
```

### 1.5 MLX Support (macOS native)

Unsloth provides an install script for MLX:
```bash
curl -fsSL https://raw.githubusercontent.com/unslothai/unsloth/refs/heads/main/install_gemma4_mlx.sh | sh
```
Dynamic 4-bit and 8-bit quants available for macOS. Metal support enabled by default.

---

## 2. Recommendation: Best Variant for Sherpa on M4 24GB

### Primary: gemma-4-E4B-it (Q8_0)

**Why E4B over 26B-A4B:**
1. **Comfortable memory fit**: ~12 GB at Q8, leaving 12 GB for KV cache + OS = full 128K context usable
2. **Vision + Audio**: any-to-any model handles screenshots AND audio input (future: voice commands to Sherpa)
3. **Higher quality quant**: Q8 preserves much more model quality than Q4 on the larger models
4. **Fast inference**: 4.5B effective params = fast token generation on M4 (likely 40-60 tok/s)
5. **Function calling**: native support for structured JSON output and tool use -- perfect for Sherpa's task enrichment pipeline

**Why not 26B-A4B:**
- At Q4 it barely fits (18 GB) and leaves only ~6 GB for KV cache
- Would need to limit context to ~32K-64K in practice
- MoE routing overhead + vision encoder = additional memory pressure
- Q4 quant on a model this size degrades quality more than Q8 on E4B
- No audio support (only image-text-to-text)

### Secondary/Scout: gemma-4-E2B-it (Q8_0)

- 5-8 GB at Q8, extremely fast
- Ideal for Scout's code analysis tasks where speed matters more than depth
- Could run alongside E4B Sherpa simultaneously (both fit in 24 GB)
- Audio + vision capable

### Stretch option: gemma-4-26B-A4B-it (Q4_K_M)

- Only viable if Sherpa operates in "focused mode" with ~32K context limit
- Better reasoning than E4B but practically constrained on 24 GB
- Worth testing empirically: does MoE routing (only 3.8B active) actually stay within budget?

---

## 3. Integration Points with Existing Sherpa Pipeline

### 3.1 Current Architecture

The Sherpa pipeline consists of:

1. **Scout** (`src/services/scout.py`): PULSAR local code analysis via ripgrep + ast.parse. Deterministic, no LLM. Injects `scout_context` into tasks.
2. **Scout Auditor** (`src/services/scout_auditor.py`): L2 artifact auditor for MYCELIUM auto-approval. Heuristic-based, no LLM.
3. **LLM Call Tool** (`src/mcp/tools/llm_call_tool.py`): Routes to any provider via `ProviderRegistry.detect_provider()`. Supports Ollama local models.
4. **Task Board** (`src/orchestration/task_board.py`): Tracks `sherpa_status` (idle/busy/stopped), `sherpa_pid`, `sherpa_tasks_enriched`.

### 3.2 Integration Plan

**Phase A: Ollama deployment (Day 1)**
```bash
# Pull the recommended models
ollama pull gemma4:e4b      # Sherpa role
ollama pull gemma4:e2b      # Scout-LLM role (optional)
```

**Phase B: Provider registry update**
- Add `gemma4:e4b` and `gemma4:e2b` to known Ollama models in `src/elisya/provider_registry.py`
- Update LLM call tool description to list Gemma 4 variants
- No architectural changes needed -- Ollama provider already supported

**Phase C: Sherpa prompt engineering**
- Gemma 4 has native system instruction support -- use for Sherpa role prompt
- Leverage function-calling for structured output (task enrichment JSON)
- Vision input: pass screenshots via Ollama multimodal API for UI analysis tasks

**Phase D: Scout-LLM hybrid (Phase 2)**
- Current Scout is pure ripgrep + ast -- no LLM dependency
- Add optional LLM pass: Scout finds code locations, Gemma 4 E2B summarizes relevance
- This is additive, not a replacement -- Scout stays deterministic

### 3.3 Specific Code Touchpoints

| File | Change Required |
|------|----------------|
| `src/elisya/provider_registry.py` | Add gemma4 model aliases to Ollama provider |
| `src/mcp/tools/llm_call_tool.py` | Update model list in description/schema |
| `src/orchestration/task_board.py` | No change (sherpa_status already generic) |
| `src/services/scout.py` | No change (deterministic, no LLM) |
| `src/services/scout_auditor.py` | No change (heuristic-based) |

---

## 4. Deployment Path Comparison

| Method | Pros | Cons |
|--------|------|------|
| **Ollama** (recommended) | One-command install, automatic GGUF, Metal acceleration, API compatible | Slightly less control over quant selection |
| **llama.cpp** | Full control, latest quant formats, server mode | Manual GGUF download, more setup |
| **MLX** (Apple native) | Best Metal performance, Apple-optimized | Newer ecosystem, fewer quant options |
| **vLLM** | Production-grade serving, batching | Overkill for single-user Sherpa |

**Recommendation: Ollama for initial deployment**, MLX as a performance upgrade path.

---

## 5. Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| E4B vision quality insufficient for code screenshots | Low | 26B-A4B as fallback; E4B benchmarks strong on vision tasks |
| Memory pressure with long contexts | Medium | Set `num_ctx` to 32768 initially, expand as tested |
| Ollama Gemma 4 bugs (day-3 release) | Medium | Pin to tested version; llama.cpp fallback |
| Function calling reliability | Medium | Validate JSON schema enforcement; add retry logic |
| Model quality regression vs DeepSeek | Low | Current Sherpa uses DeepSeek; Gemma 4 E4B likely comparable or better per-param |

---

## 6. Benchmarks Reference (from Google announcement)

- 31B: #3 open model globally (Arena AI text leaderboard)
- 26B-A4B: #6 open model globally
- All variants: multi-step planning, deep logic, 140+ languages
- Native agentic capabilities: function-calling, structured JSON, system instructions
- "Most capable open models" -- intelligence-per-parameter claim

---

## 7. Action Items

1. **IMMEDIATE**: `ollama pull gemma4:e4b` on M4 Mac, verify 9.6 GB download and inference speed
2. **TEST**: Run Sherpa-style prompt with vision input (code screenshot) through Ollama API
3. **MEASURE**: Token/s throughput, memory usage under load, vision quality on code images
4. **INTEGRATE**: Update provider_registry.py aliases -- estimated 30min task
5. **COMPARE**: Side-by-side with current DeepSeek Sherpa on 5 representative tasks
6. **DOCUMENT**: Performance results in follow-up task

---

## Sources

- [Google Gemma 4 announcement](https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/)
- [Ollama Gemma 4 library](https://ollama.com/library/gemma4)
- [Unsloth Gemma 4 docs](https://unsloth.ai/docs/models/gemma-4)
- [HuggingFace google/gemma-4-E4B-it](https://hf.co/google/gemma-4-E4B-it) (8.0B params, Apache 2.0)
- [HuggingFace google/gemma-4-26B-A4B-it](https://hf.co/google/gemma-4-26B-A4B-it) (26.5B params, Apache 2.0)
- [HuggingFace google/gemma-4-31B-it](https://hf.co/google/gemma-4-31B-it) (32.7B params, Apache 2.0)
- [HuggingFace unsloth/gemma-4-E4B-it-GGUF](https://hf.co/unsloth/gemma-4-E4B-it-GGUF) (317K downloads)
- [HuggingFace unsloth/gemma-4-26B-A4B-it-GGUF](https://hf.co/unsloth/gemma-4-26B-A4B-it-GGUF) (487K downloads)
