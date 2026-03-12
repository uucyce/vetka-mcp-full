# MARKER_162A_PIXTRAL_STATUS_AND_READINESS_2026-03-06

## Scope
Audit Pixtral learner readiness, missing deps, and practical role in current VETKA runtime.

## Evidence
- Pixtral warning text source: `src/agents/pixtral_learner.py:24-33` and init fallback `:104-111`.
- Learner registration is unconditional in dependency check: `src/initialization/dependency_check.py:279-286`.
- Runtime learner default is `qwen`, not pixtral: `src/initialization/components_init.py:393-397`.
- Pixtral selected only when `LEARNER_TYPE=pixtral`: `src/initialization/components_init.py:404-411`.
- Pixtral config expects local model dir at `~/pixtral-12b`: `src/agents/learner_initializer.py:154`.
- Pixtral marked vision-capable only in learner path: `src/agents/learner_initializer.py:148-152`.

## Local Environment Check (this machine)
- `torch`: installed.
- `transformers`: installed.
- `accelerate`: installed.
- `PIXTRAL_PATH` resolved to `/Users/danilagulin/pixtral-12b` and directory exists.
- Model artifact files present (`consolidated.safetensors`, etc.).

## Diagnosis
1. The startup warning about Pixtral deps is a generic import-guard message path, not proof of runtime failure by itself.
2. In current config, Pixtral is not the active learner (default `LEARNER_TYPE=qwen`), so warning does not block server startup.
3. If switched to `LEARNER_TYPE=pixtral`, runtime risk becomes resource-bound (VRAM/RAM) rather than package-bound.

## On “does Pixtral train and grow into Jarvis pipeline chunks?”
- Current code uses Pixtral as a **learner/analyzer** role, not as Jarvis voice inference core.
- Jarvis path is local Ollama/provider routing (`src/voice/jarvis_llm.py:34-36, 68-76`) and is independent.
- There is dataset collection/export for training (`src/orchestration/simpo_training_loop.py:383-413`), but no integrated automatic fine-tune loop that upgrades Jarvis model weights in-place.

## On “can Pixtral work together with JEPA?”
- Yes, but indirectly.
- JEPA runtime is a separate embedding service (`src/services/jepa_http_server.py:6-10, 191-205`) used for retrieval/context features.
- Pixtral does not currently call JEPA directly in learner code; integration is architectural (shared system), not a direct Pixtral+JEPA fusion pipeline.

## Recommended Agent Task (separate)
- Validate optional switch path `LEARNER_TYPE=pixtral` under controlled memory budget.
- Record cold-start load time, peak RAM/VRAM, and fallback behavior.
- Decide policy: keep qwen default, pixtral opt-in for vision-heavy tasks.

## Acceptance Criteria
- Server starts with no learner fatal errors.
- Explicit pixtral mode either loads successfully or degrades cleanly to qwen fallback.
- Jarvis path remains unaffected.
