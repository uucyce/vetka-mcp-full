# TODO: Next Session — Mycelium Pipeline Debugging (Phase 128+)

## Context
Pipeline generates code but quality needs improvement. Phases 127.1-127.3 fixed verifier + retry loop.
Now confidence=0.9 and retries work. Next: fix the CODE QUALITY itself.

## Priority 1: Coder Project Awareness
**Problem:** Coder writes generic code — imports MobX instead of Zustand, guesses file paths.
- Scout finds files but coder doesn't fully use scout_report context
- FC loop: coder calls search but doesn't always read the right files
- **Fix idea:** Inject project stack info into coder prompt (Zustand, React, Three.js, FastAPI)
- **Fix idea:** Force first FC turn to read target file (not just search)
- **Files:** `data/templates/pipeline_prompts.json` (coder prompt), `src/tools/fc_loop.py`

## Priority 2: Dynamic Token Limits per Model
**Problem:** All models get same max_tokens, but GLM-4.7-flash has 8K context vs Qwen3-coder 128K.
- **Idea:** Query model registry/presets for max_context_length, set per-role limits
- **Files:** `data/templates/model_presets.json`, `src/orchestration/agent_pipeline.py`
- **Approach:** Add `max_tokens` field to preset role config, pipeline reads it before LLM call

## Priority 3: E2E Quality Test Loop
**Method:** One task → dispatch → analyze code → find specific issue → fix → re-dispatch → compare
- Task board has 8 pending tasks to test with
- Compare: code output chars, verifier confidence, retry count, actual correctness
- Focus on: does generated code use correct imports? correct file paths? correct patterns?

## Priority 4: Doctor Triage (if Cursor didn't finish)
- Brief: `docs/126_phCur/CURSOR_BRIEF_DOCTOR_TRIAGE.md`
- Doctor should show analysis in chat before dispatching

## Current Test Status
- **444 pipeline tests passing** (phases 122-127)
- **18 pre-existing failures** (not our responsibility, see MEMORY.md)

## Cursor Status
- ✅ Key Selection (126.9)
- ✅ Activity Log (127.2)
- 📝 Stats Monitor — `CURSOR_BRIEF_STATS_MONITOR.md`
- 📝 Results Viewer — `CURSOR_BRIEF_RESULTS_VIEWER.md`
- 📝 Doctor Triage — `CURSOR_BRIEF_DOCTOR_TRIAGE.md` (NEW)

## Key Insight from E2E Testing
The pipeline WORKS end-to-end. Code IS generated and saved. The remaining issue is
code QUALITY — it's plausible but project-unaware. Coder needs more context about
the specific project it's coding for (imports, patterns, file structure).
