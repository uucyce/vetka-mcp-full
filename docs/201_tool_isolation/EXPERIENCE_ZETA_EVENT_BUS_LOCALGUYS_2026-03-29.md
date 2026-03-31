# Experience Report: Zeta — Event Bus + Localguys Session
**Date:** 2026-03-28/29 | **Agent:** Zeta (Opus 4.6) | **Branch:** claude/harness

## Tasks Completed (6 commits)

| Commit | Task | What |
|--------|------|------|
| `b0f0c89c5` | tb_1774691652_55727_1 | Event Bus Phase 1 — AgentEvent + EventBus + 3 subscribers + piggyback |
| `8bfe4a205` | tb_1774698370_8869_1 | UDS Daemon — real-time push to MCP servers, 0 CPU idle |
| `f9cae038` | tb_1774700187_8869_1 | Ollama Orchestrator — autonomous task loop via REST |
| `47d8e190` | tb_1774757222_8869_1 | Localguys Step Executor — 6-step multi-model pipeline |
| `17d5f6fb` | tb_1774771972_8869_1 | Task Decomposer — complex → atomic sub-tasks, zero cloud |
| (rebase) | — | Rebase on main after Eta merge, 1 conflict resolved |

## Q1: Bugs
1. `POST /api/taskboard/claim` returns 405 — new `taskboard_routes.py` claim endpoint conflicts with existing `task_routes.py`. Legacy path `/api/tasks/{id}/claim` works. Router prefix collision needs investigation.
2. Signal advance returns 400 "invalid localguys run role" for scout/architect — g3 contract only registers coder+verifier roles. Non-blocking but noisy.
3. deepseek-r1:8b produces 0-length visible output on verify step (thinking model — all reasoning in think tokens). Review step compensates but verify artifact is empty.
4. `localguys_executor.py --task X --method decompose` fails to create run ("Workflow contract 'core_library' not found"). Workaround: create via `localguys.py run g3` first.

## Q2: What Worked
1. **Piggyback delivery pattern** — zero overhead, events arrive in the same MCP response the agent is already reading. Elegantly avoids polling.
2. **UDSPublisher background thread** — handle() takes <0.01ms (just list.append), thread does socket I/O. emit() stays <1ms even with 4 subscribers.
3. **qwen3:8b as task decomposer** — produces well-structured plans with file paths and test hints in 33s. Good enough to break any task into atomic pieces.
4. **Multi-model pipeline** — different models for different roles (scout=qwen2.5, architect=qwen3, verifier=deepseek-r1). Each plays to its strength.
5. **Anti-recursion tag** — `auto-decomposed` tag prevents infinite decomposition loops. Simple, bulletproof.

## Q3: Ideas
1. **Auto-executor chain**: decompose creates children → ollama orchestrator auto-claims children → each runs g3 → parent auto-completed when all children done. Full autonomy, zero human.
2. **LiteRT/TurboQuant benchmark**: Google's new quantization could 2-5x our local inference on Apple Silicon ANE. Worth a benchmark task.
3. **Quality gate for local output**: before completing a task, run a cheap verifier (phi4-mini) to score the output 1-10. Below 4 → mark as needs_fix instead of done.

## Q4: Standard Patterns
1. **Event Bus subscriber pattern** — accepts()/handle() protocol. Add any new channel (UDS, WebSocket, Slack) as a subscriber, zero changes to emitter.
2. **Decompose workflow** — recon → plan → decompose. Reusable for any "break big into small" scenario.
3. **Length-prefixed UDS framing** — 4-byte big-endian + JSON. Simple, robust, language-agnostic.

## Q5: Anti-patterns
**SQLite trigger myth.** Research docs (including Grok's) claimed SQLite can call external functions from triggers. It cannot without a custom C extension. Python-level emit is the correct trigger. Always verify research against actual API — especially when the source is an LLM.

## Q6: If I Rebuilt From Scratch

I would merge `ollama_orchestrator.py` and `localguys_executor.py` into one tool. Right now there are two entry points for local model execution — the simple orchestrator and the advanced pipeline executor. They share HTTP helpers, Ollama calls, and task board interaction, but are separate scripts. The reason they're separate is history (orchestrator came first, executor added pipeline logic on top).

The unified tool would be:
```
vetka-local run --task tb_XXX                    # auto-detect: simple or pipeline
vetka-local run --task tb_XXX --decompose        # break into sub-tasks
vetka-local run --task tb_XXX --method g3        # explicit pipeline
vetka-local loop --interval 300                  # 24/7 mode
vetka-local status                               # what's running
```

One command, one mental model. The tool auto-selects: if task is complex (high cx or multi-file), decompose first. If simple (low cx, 1 file), direct g3. The model selection, prompt building, artifact handling — all internal.

But pragmatically — what we have works. Two scripts, clear separation. Unification is a polish task, not a blocker. The system runs, models execute tasks, the swarm is alive. Ship it.

## Session Metrics
- 6 commits, ~800 lines of new code
- 75 tests passing
- 1 successful rebase (5 skipped, 6 rebased, 1 conflict)
- First localguys pipeline run: 139s, 6 artifacts, 3 models
- First decomposition: 41s, 6 child tasks created
- First Ollama task completion: 22s via REST
