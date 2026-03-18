# RECON 189: Auto-Inject Architecture Docs + Context Budget Guard

**Date:** 2026-03-18
**Author:** Opus (Claude Code)
**Phase:** 189 — MCC TaskBoard Integration
**Status:** RECON COMPLETE — ready for implementation

---

## Problem Statement

`architecture_docs` and `recon_docs` fields in tasks are **pure metadata** — the pipeline stores file paths but **never loads their content**. When a task is dispatched to a localguys model (Ollama 8B, Qwen 30B), the agent receives only `title + description` without architectural context. This significantly degrades output quality.

### Evidence Chain (code audit)

| Component | File | What it does | Loads doc content? |
|-----------|------|-------------|-------------------|
| Task storage | `task_board.py:655-656` | Stores paths as `List[str]` | N/A |
| Context packet | `roadmap_task_sync.py:186-265` | Packages paths into packet | **NO** — paths only |
| Prefetch | `architect_prefetch.py:517-524` | Counts docs (`docs=2`) | **NO** — count only |
| Architect prompt | `agent_pipeline.py:3720` | Injects path list string | **NO** — `"Packet docs: path1, path2"` |
| Dispatch | `task_board.py:2064-2066` | Builds `task_text = title + desc` | **NO** — docs ignored |

**Conclusion:** Agents must manually read referenced files. Ollama 8B/Qwen models without tool-calling capability cannot do this.

---

## Proposed Solution: Auto-Inject with Context Budget Guard

### Architecture

```
dispatch_task(task_id)
  |
  +-- 1. Build base task_text (title + description)
  +-- 2. Resolve model preset -> get model name for coder role
  +-- 3. LLMModelRegistry.get_profile(model) -> context_length
  +-- 4. Calculate docs_budget = context_length * 0.30  (30% of window for docs)
  +-- 5. Load architecture_docs + recon_docs from disk
  +-- 6. If total_docs_tokens > docs_budget:
  |     +-- Apply ELISION level 2-3 compression
  |     +-- If still > budget -> truncate each doc proportionally
  |     +-- If still > budget -> include only top-N docs by priority
  +-- 7. Inject into task_text: "\n[Architecture Context]\n{docs_content}"
  +-- 8. Log: task_weight, docs_budget, docs_included, docs_truncated
  +-- 9. pipeline.execute(task_text, phase_type)
```

### Injection Point

**File:** `src/orchestration/task_board.py`, method `dispatch_task()`, lines ~2064-2066

**Current code:**
```python
task_text = f"{task['title']}\n\n{task.get('description', '')}"
# ... (failure_history injection follows)
result = await pipeline.execute(task_text, task["phase_type"])
```

**Proposed change:** Insert doc loading + budget check between task_text assembly and pipeline.execute().

---

## Existing Infrastructure (what we can reuse)

### 1. LLMModelRegistry — context_length per model

**File:** `src/elisya/llm_model_registry.py`

Provides `context_length` for every known model:
- Claude Opus: 200K
- Gemini 2.0 Flash: 1.048M
- Qwen 30B/Coder: 131K
- GPT-5.2: 128K
- Fallback: 128K (conservative)

**Usage:**
```python
from src.elisya.llm_model_registry import LLMModelRegistry
registry = LLMModelRegistry()
profile = await registry.get_profile("qwen3-30b-a3b")
context_window = profile.context_length  # 131072
```

### 2. ELISION Compression — token savings

**File:** `src/memory/elision.py`

5 compression levels, 40-60% token savings. Already used in pipeline STM.

```python
from src.memory.elision import get_elision_compressor
compressor = get_elision_compressor()
result = compressor.compress(doc_text, level=2)
# result.compressed_length, result.compression_ratio, result.tokens_saved_estimate
```

### 3. Model Presets — tier -> model mapping

**File:** `data/templates/model_presets.json`

```json
"_tier_map": {
  "low": "dragon_bronze",
  "medium": "dragon_silver",
  "high": "dragon_gold"
}
```

Each preset defines models per role (architect, coder, etc.). The **coder model** is what matters for context budget since docs are consumed during code generation.

### 4. Context Packer — token pressure scoring

**File:** `src/orchestration/context_packer.py`

Has `token_pressure_threshold = 0.80` — triggers JEPA optimization when context > 80% of window. Can be used as secondary guard.

### 5. Adaptive Timeout — already uses model profile

**File:** `llm_model_registry.py:904-969`

`calculate_timeout()` already queries model profiles for speed metrics. Same pattern can be used for context budget.

---

## Context Budget Calculation

### Formula

```python
TOKEN_ESTIMATE = lambda text: len(text) // 4  # chars -> tokens (rough)

base_tokens = TOKEN_ESTIMATE(task_text)        # title + description
system_tokens = 2000                            # system prompt overhead
stm_tokens = 1200                               # STM buffer (5 subtasks avg)
scout_tokens = 200                              # scout report
overhead = system_tokens + stm_tokens + scout_tokens  # ~3400 tokens

available = context_length - overhead - base_tokens
docs_budget = min(available * 0.5, context_length * 0.30)  # 30% cap
```

### Budget by Model Tier

| Tier | Context Window | 30% Budget | Typical docs fit |
|------|---------------|------------|-----------------|
| Bronze (Qwen 30B) | 131K | ~39K tokens | 10-15 docs easily |
| Silver (Kimi K2.5) | 131K | ~39K tokens | 10-15 docs |
| Gold (Qwen 235B) | 131K | ~39K tokens | 10-15 docs |
| Gold+GPT (GPT-5.2) | 128K | ~38K tokens | 10-15 docs |
| Quality (Claude Opus) | 200K | ~60K tokens | 20+ docs |
| **Localguys (Ollama 8B)** | **8K-32K** | **2.4K-9.6K** | **1-3 docs MAX** |

**Critical:** Localguys models (8K-32K context) need aggressive truncation. This is where the guard matters most.

---

## Task Weight Estimation

No need for a new schema field — compute on the fly:

```python
def estimate_task_weight(task: dict) -> dict:
    """Estimate total token weight of task + docs."""
    desc_tokens = len(task.get("description", "")) // 4
    title_tokens = len(task.get("title", "")) // 4

    doc_tokens = 0
    doc_details = []
    for doc_path in (task.get("architecture_docs") or []) + (task.get("recon_docs") or []):
        path = Path(doc_path)
        if path.exists():
            size = path.stat().st_size // 4  # chars ~ bytes for UTF-8 text
            doc_tokens += size
            doc_details.append({"path": str(path), "est_tokens": size})
        else:
            doc_details.append({"path": str(path), "est_tokens": 0, "warning": "FILE_NOT_FOUND"})

    return {
        "title_tokens": title_tokens,
        "description_tokens": desc_tokens,
        "docs_tokens": doc_tokens,
        "total_tokens": title_tokens + desc_tokens + doc_tokens,
        "docs": doc_details,
    }
```

### Auto-split Warning

If `task_weight.total_tokens > model_context * 0.40`:
```
WARNING: Task tb_xxx estimated at ~52K tokens but target model
(qwen3-8b) has only 8K context. Consider splitting into smaller tasks
or upgrading to a higher tier preset.
```

---

## Validation: architecture_docs Path Check

Add to `add_task()` in `task_board.py`:

```python
# After _normalize_doc_refs()
warnings = []
for field in ("architecture_docs", "recon_docs"):
    for doc_path in payload.get(field, []):
        if not Path(doc_path).exists():
            warnings.append(f"{field}: '{doc_path}' not found on disk")

if warnings:
    payload["_doc_warnings"] = warnings
    logger.warning(f"[TaskBoard] Task {task_id} doc warnings: {warnings}")
```

This catches:
- Worktree docs referenced from main (invisible files)
- Typos in paths
- Deleted/moved docs

---

## Implementation Plan

| Step | What | File(s) | Complexity | Priority |
|------|------|---------|-----------|----------|
| 1 | Add `_load_task_docs()` helper | `task_board.py` | Easy | HIGH |
| 2 | Add `_estimate_docs_budget()` using LLMModelRegistry | `task_board.py` | Easy | HIGH |
| 3 | Inject loaded docs into `task_text` in `dispatch_task()` | `task_board.py:~2064` | Easy | HIGH |
| 4 | Add truncation/ELISION if docs > budget | `task_board.py` | Medium | HIGH |
| 5 | Add doc path validation in `add_task()` | `task_board.py` | Easy | MEDIUM |
| 6 | Add `_doc_warnings` to task response | `task_board.py` | Easy | MEDIUM |
| 7 | Log task_weight metrics on dispatch | `task_board.py` | Easy | LOW |
| 8 | Add auto-split warning if weight > 40% of model context | `task_board.py` | Easy | LOW |

### Dependencies

- `LLMModelRegistry` must be importable from `task_board.py` (check circular imports)
- `elision.py` compressor must be available (already used in pipeline)
- Model preset resolution: need to map `task.preset` -> coder model name -> profile

### Test Plan

1. Unit test: `_load_task_docs()` with existing/missing files
2. Unit test: `_estimate_docs_budget()` with various model profiles
3. Integration test: dispatch task with architecture_docs -> verify docs appear in pipeline input
4. Edge case: task with 10+ large docs -> verify truncation works
5. Edge case: localguys 8K model -> verify aggressive truncation
6. Edge case: docs reference worktree-only files -> verify warning

---

## Related Work

- **MARKER_189.10C:** Fixed project_id filter in MCP list (same dispatch area)
- **Phase 189.8:** Include unassigned tasks in project views
- **Pending task:** "A1.2: Add get_profile_sync to LLMModelRegistry" — sync version needed if dispatch_task is called from sync context
- **Context Packer:** `src/orchestration/context_packer.py` — token pressure scoring, could integrate

---

## Files Referenced

| File | Purpose |
|------|---------|
| `src/orchestration/task_board.py` | Dispatch point, doc storage, validation |
| `src/orchestration/agent_pipeline.py` | Pipeline context assembly |
| `src/elisya/llm_model_registry.py` | Model profiles, context_length |
| `src/memory/elision.py` | Compression engine |
| `src/orchestration/context_packer.py` | Token pressure guard |
| `src/services/architect_prefetch.py` | Current (non-loading) doc injection |
| `src/services/roadmap_task_sync.py` | Task context packet builder |
| `data/templates/model_presets.json` | Tier -> model mapping |
