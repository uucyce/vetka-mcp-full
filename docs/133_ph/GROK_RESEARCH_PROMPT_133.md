# Grok Research Prompt — Phase 133: E2E Pipeline Stability

**Context for Grok:** You are researching for VETKA project — a Tauri+React+Python AI agent platform. We have a Mycelium pipeline (fractal agent system) that runs Dragon teams (Asian LLM models via Polza provider). Pipeline: Heartbeat scans chat → TaskBoard queues → AgentPipeline executes 5 phases (Scout, Architect, Researcher, Coder, Verifier).

**What we just fixed (Phase 132):**
1. heartbeat_tick() missing await — now fixed
2. Architect + Coder LLM retry with exponential backoff
3. Universal client endpoints (progress, release)

**What Cursor is implementing now (Phase 133 C33A-D):**
- C33A: Provider resilience decorator (retry + fallback chain: polza → openrouter → ollama)
- C33B: Per-phase timeouts (30-90s per phase)
- C33C: Concurrent semaphore (max 2 simultaneous pipelines)
- C33D: client_id tracking (X-Agent-ID header)

---

## Research Questions for Grok:

### 1. Pipeline Checkpoint & Recovery
After phase timeout or crash, how to resume mid-pipeline? Current state: if Architect times out, we abort. If Coder times out on subtask 3/5, we lose subtasks 1-2 results.
- **Question:** Best patterns for checkpoint/resume in async Python pipelines? Save state after each phase to JSON? Redis? SQLite?
- **Constraint:** No external DB (we use JSON files). Must be lightweight.

### 2. EvalAgent Model Upgrade
Current EvalAgent uses `ollama/deepseek-coder:6.7b` — too weak for quality gating. Scores biased.
- **Question:** Which model from Polza (Kimi K2.5, Grok Fast 4.1, Qwen3-235b, GLM-4.7-flash) is best for code evaluation? Need: fast, accurate scoring, low hallucination.
- **Metrics:** correctness(40%), completeness(30%), quality(20%), clarity(10%). Threshold 0.75.

### 3. Heartbeat Daemon Reliability
Heartbeat runs as asyncio.create_task() in FastAPI startup. If it crashes, it's gone.
- **Question:** Best pattern for self-healing daemon in FastAPI? Supervisor pattern? Watchdog task? systemd integration?
- **Constraint:** Must work on macOS dev + Linux prod.

### 4. Multi-Agent File Locking
Cursor and Claude Code both edit files in the same repo. TaskBoard uses JSON file.
- **Question:** Lightweight file locking for Python (fcntl.flock vs filelock lib vs advisory locks)? Cross-platform? What about race conditions on task_board.json?

### 5. Pipeline Metrics & Observability
We stream progress via WebSocket but have no persistent metrics.
- **Question:** Minimal metrics system for pipeline runs? (success rate, avg duration per phase, provider failure rate, eval scores over time). File-based? SQLite? Prometheus?

---

## Files to Reference (semantic search in VETKA):
- `src/orchestration/agent_pipeline.py` — main pipeline (2862 lines)
- `src/orchestration/mycelium_heartbeat.py` — heartbeat engine
- `src/orchestration/task_board.py` — task queue
- `src/agents/eval_agent.py` — quality evaluation
- `src/mcp/tools/llm_call_tool_async.py` — LLM call handler
- `data/templates/model_presets.json` — team configs
- `src/services/approval_service.py` — approval chain

## Output Format
For each question:
1. Short answer (2-3 sentences)
2. Recommended approach with code snippet
3. Pros/cons table
4. Estimated implementation time

Save as: `docs/133_ph/GROK_RESEARCH_E2E_STABILITY.md`
