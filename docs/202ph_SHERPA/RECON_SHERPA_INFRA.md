# RECON: Sherpa Infrastructure — What Exists, What's Missing

> **PARTIALLY OUTDATED**: Status flow now includes `scout_recon` and `recon_done` (Phase 203).
> Scout service (`src/services/scout.py`) was added after this recon.

**Task:** `tb_1775084719_37380_1`
**Date:** 2026-04-02
**Phase:** 202
**Author:** Commander (Opus) + 4 Haiku recon agents

---

## 1. Executive Summary

All infrastructure for Sherpa exists. No new services to build. The script is ~300 lines of glue connecting:

| Component | Status | How to Call |
|-----------|--------|-------------|
| TaskBoard | Ready | HTTP `localhost:5000/api/tasks/*` |
| Ollama/Qwen | Ready | HTTP `localhost:11434/api/chat` |
| Browser automation | Ready | Playwright via existing `browser_manager.py` |
| Code extraction | Ready | Existing `code_extractor.py` |
| Codebase search | Ready | VETKA HTTP `localhost:5001` or direct file grep |

**Critical finding:** Control Chrome MCP is Claude-Code-only. Standalone Python must use Playwright. But `browser_manager.py` already implements persistent Playwright contexts — this is existing code, not new WEATHER infrastructure.

---

## 2. TaskBoard HTTP API

**Base:** `http://localhost:5000`

### Key Endpoints for Sherpa

| Action | Method | URL | Key Params |
|--------|--------|-----|------------|
| Get claimable tasks | `GET` | `/api/tasks/claimable` | `limit`, `phase_type` (research/build/fix/test) |
| Claim highest-priority | `POST` | `/api/tasks/take` | `agent_name` (req), `agent_type`, `phase_type` |
| Get task details | `GET` | `/api/tasks/{task_id}` | — |
| Update task | `PATCH` | `/api/tasks/{task_id}` | `recon_docs`, `implementation_hints`, etc. |
| Complete task | `POST` | `/api/tasks/{task_id}/complete` | `commit_hash`, `commit_message` |
| Cancel/release | `POST` | `/api/tasks/{task_id}/cancel` | `reason` |
| List tasks | `GET` | `/api/tasks` | `status`, `limit` |

### Task Status Values
`pending` → `claimed` → `running` → `done` / `done_worktree` / `failed` / `cancelled`

### Sherpa-Specific Usage
```python
# 1. Claim a research task
resp = requests.post("http://localhost:5000/api/tasks/take", json={
    "agent_name": "sherpa",
    "agent_type": "mycelium",
    "phase_type": "research"
})
task = resp.json()

# 2. Get full details
details = requests.get(f"http://localhost:5000/api/tasks/{task['task_id']}").json()

# 3. Update with recon
requests.patch(f"http://localhost:5000/api/tasks/{task['task_id']}", json={
    "recon_docs": ["docs/sherpa_recon/sherpa_{task_id}.md"],
    "implementation_hints": "Sherpa recon attached. Key files: ...",
    "status": "pending"  # release back to pool, enriched
})
```

---

## 3. Local Models (Ollama)

**Base:** `http://localhost:11434`
**Status:** Running, 24 models installed

### Best Models for Sherpa

| Model | Size | Use Case |
|-------|------|----------|
| `qwen3.5:latest` | 9.7B Q4_K_M | Prompt building, response parsing |
| `qwen2.5:7b` | 7.6B Q4_K_M | Lighter alternative |
| `deepseek-coder:6.7b` | 7B Q4_0 | Code-focused tasks |

### API Call
```python
resp = requests.post("http://localhost:11434/api/chat", json={
    "model": "qwen3.5:latest",
    "messages": [{"role": "user", "content": prompt}],
    "stream": False,
    "options": {"temperature": 0.3, "num_predict": 2048}
})
answer = resp.json()["message"]["content"]
```

### Limitations
- **No function/tool calling** — `supports_tools = False` in OllamaProvider
- Text generation only — Sherpa must use fixed pipeline, not dynamic tool calls
- Max 3 concurrent calls (semaphore in provider)
- Qwen role: build prompts from context, parse/summarize responses. NOT code generation.

---

## 4. Browser Automation

### Option A: Playwright (Recommended for Sherpa)

**Existing code:** `src/services/browser_manager.py` (MARKER_196.BP1.2)
- Persistent contexts (userDataDir) — sessions survive restarts
- N browser slots with health checks
- Already integrated with adapters (Gemini, Grok, Kimi, Perplexity, Mistral)

**Existing code:** `src/services/browser_agent_proxy.py` (MARKER_196.BP1.1)
- Full pipeline: TaskBoard poll → browser slot → adapter → extract → git
- Code extraction via `code_extractor.py`

**What Sherpa reuses:**
- `BrowserManager.acquire_slot()` / `release_slot()`
- `ServiceAdapter.send_prompt()` / `wait_response()` / `extract_code()`
- `CodeExtractor.extract_from_html()`

**What Sherpa adds:** Qwen orchestration layer + recon-focused prompts (not code generation)

### Option B: Control Chrome MCP (NOT for standalone Sherpa)

- Only works inside Claude Code sessions
- Cannot be called from Python scripts
- Good for interactive work, not automation

### Decision: **Playwright** — standalone, free, 24/7, existing code

---

## 5. Codebase Search

### Via VETKA MCP (localhost:5001)
```python
# Semantic search
resp = requests.post("http://localhost:5001/api/search/semantic", json={
    "query": "timeline playback FFmpeg",
    "limit": 10
})

# File search
resp = requests.post("http://localhost:5001/api/search/files", json={
    "query": "TimelineTrackView",
    "search_type": "both"
})
```

### Direct (Faster, No Dependencies)
```python
import subprocess
# ripgrep for content search
result = subprocess.run(["rg", "-l", pattern, project_root], capture_output=True)
# find for file search
result = subprocess.run(["find", project_root, "-name", f"*{name}*"], capture_output=True)
```

---

## 6. Revised Sherpa Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  TaskBoard   │────▶│  sherpa.py        │────▶│  Playwright     │
│  HTTP API    │     │  (Python, ~300L)  │     │  (persistent    │
│  :5000       │◀────│                   │◀────│   contexts)     │
└─────────────┘     │  Qwen 3.5 local   │     └────────┬────────┘
                    │  :11434            │              │
                    │                   │       ┌──────┼──────┐
                    │  rg/find local    │       │      │      │
                    │  (codebase grep)  │    Grok   Gemini  Kimi
                    └──────────────────┘
```

### Pipeline
```
1. GET /api/tasks/claimable?phase_type=research → pick task
2. POST /api/tasks/take (agent_name=sherpa) → claim
3. rg/find → local codebase search → relevant files
4. Qwen 3.5 → build research prompt from task context + files
5. Playwright → send to Grok/Gemini → wait → extract response
6. Save to docs/sherpa_recon/sherpa_{task_id}.md
7. PATCH /api/tasks/{task_id} → add recon_docs, release as pending
8. sleep(120) → next task
```

---

## 7. Existing Adapter Code to Reuse

From `src/services/adapters/`:

| Adapter | File | Status | Selectors |
|---------|------|--------|-----------|
| Base | `base_adapter.py` | Ready | Abstract interface |
| Gemini | `gemini_adapter.py` | Ready | Google AI Studio selectors |
| Grok | `grok_adapter.py` | Skeleton | TODO: selectors |
| Kimi | `kimi_adapter.py` | Skeleton | TODO: selectors |
| Perplexity | `perplexity_adapter.py` | Skeleton | TODO: selectors |
| Mistral | `mistral_adapter.py` | Skeleton | TODO: selectors |

**MVP:** Start with Gemini adapter (ready) + add Grok selectors (~50 lines).

---

## 8. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Playwright detected as bot | Medium | `playwright-stealth`, human-like delays |
| AI service UI changes | Medium | Selector registry, fallback patterns |
| Account rate limits | Low | 120s cooldown, rotate services |
| Qwen prompt quality | Low | Fixed templates, not dynamic |
| VETKA server not running | Low | Health check before loop start |

---

## 9. Implementation Estimate

| Item | Lines | Time |
|------|-------|------|
| `sherpa.py` main loop | ~150 | 30 min |
| Grok adapter selectors | ~50 | 15 min |
| Prompt templates | ~50 | 15 min |
| Health checks + error handling | ~50 | 15 min |
| **Total** | **~300** | **~1.5 hours** |

No new infrastructure. No new services. Just glue.

---

*Sherpa: carries the load, shows the way.*
