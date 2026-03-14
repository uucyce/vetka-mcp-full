# PHASE 155C RECON — JEPA Update for Architect with MCC/VETKA Standalone Separation (2026-03-02)

Status: `RECON + markers` (implementation guidance only, no runtime code changes in VETKA requested).

## 1) Scope
Goal: decide how to implement JEPA-assisted architect context bootstrap so that:
1. MCC (separate MCP) runs standalone,
2. VETKA runs standalone,
3. first architect call on non-empty codebase can force JEPA semantic core,
4. empty/new project path skips JEPA overhead.

## 2) Verified baseline facts (current repo)

### 2.1 Phase-157 context packer exists and is integrated in chat flow
- baseline commit: `c15c26fa` (`feat(search): slice adaptive descriptive search and context packing`)
- context packer API and trigger policy: `src/orchestration/context_packer.py`
  - `ContextPacker.pack(...)` uses pressure/docs/entropy/modality trigger + hysteresis
- integration points where packed JEPA core is appended:
  - `src/api/handlers/user_message_handler.py` (`packed.json_context + packed.jepa_context`)

### 2.2 JEPA adapter/runtime exists and is shared by multiple subsystems
- adapter contract: `src/services/mcc_jepa_adapter.py`
- runtime provider bridge: `src/services/jepa_runtime.py`
- used by MCC overlay and search stacks:
  - `src/services/mcc_predictive_overlay.py`
  - `src/search/hybrid_search.py`
  - `src/search/file_search_service.py`

### 2.3 Architect chat endpoint currently does NOT use context packer
- `src/api/routes/architect_chat_routes.py` builds prompt from request context and calls model directly.
- no `get_context_packer()` path in this route at the moment.

## 3) Separation decision (shared codebase vs split)

Decision: **split runtime implementations, share only a strict contract layer**.

Reasoning:
1. Product requirement explicitly states both MCC MCP and VETKA must run independently.
2. Full shared runtime module for packer/handlers creates hidden coupling and release lockstep.
3. JEPA behavior needs same policy semantics, but transport/runtime internals may diverge per product.

Recommended architecture:
1. **Shared Contract (portable, tiny):**
   - trigger policy schema
   - JEPA digest format schema
   - env key naming contract
   - trace fields contract
2. **MCC-local implementation:** architect bootstrap path for MCC MCP.
3. **VETKA-local implementation:** keep existing chat/search pipelines and evolve independently.

## 4) Implementation plan for MCC JEPA architect update

### 4.1 Policy
1. On first architect call, if project has non-trivial codebase -> force JEPA bootstrap.
2. If project is empty/new -> skip JEPA bootstrap.
3. For subsequent calls -> standard trigger/hysteresis policy.

### 4.2 Concrete behavior
1. Build pinned bootstrap corpus from project root (README/AGENTS/config + representative code files).
2. Run ContextPacker-like pack with `force_jepa=true` only on first call and non-empty corpus.
3. Inject JEPA semantic digest into architect system context as compact “project essence”.
4. Persist trace stats for operator visibility (forced/auto/skip mode, latency, provider mode).

### 4.3 Do-not-couple rules
1. MCC must not import VETKA route handlers directly.
2. Shared contract can be copied/vendorized or packaged as minimal pure-Python module.
3. Runtime providers (HTTP endpoint URLs, fallback policy) remain per-product configurable.

## 5) Proposed markers for 155C implementation
1. `MARKER_155C.JEPA_ARCH_BOOTSTRAP_POLICY.V1`
2. `MARKER_155C.JEPA_ARCH_FIRST_CALL_FORCE.V1`
3. `MARKER_155C.JEPA_ARCH_EMPTY_PROJECT_SKIP.V1`
4. `MARKER_155C.JEPA_ARCH_SHARED_CONTRACT.V1`
5. `MARKER_155C.JEPA_ARCH_MCC_STANDALONE_GUARD.V1`
6. `MARKER_155C.JEPA_ARCH_VETKA_STANDALONE_GUARD.V1`

## 6) Suggested rollout order
1. Freeze contract doc + marker list.
2. Copy baseline logic from `c15c26fa` (`context_packer.py`, `jepa_runtime.py`, tests, probe) into MCC repo.
3. Wire architect bootstrap in MCC only.
4. Add parity tests in MCC for:
   - first-call force on non-empty project,
   - skip on empty project,
   - hysteresis after first call,
   - deterministic fallback when JEPA runtime unavailable.
5. Keep VETKA unchanged unless separately approved.

## 7) Risks and mitigations
1. Risk: drift between MCC and VETKA behavior.
   - Mitigation: shared contract tests + marker parity checklist.
2. Risk: forced JEPA on huge corpora increases latency.
   - Mitigation: bootstrap file cap + timeout + fallback path.
3. Risk: hidden runtime dependency on local JEPA service.
   - Mitigation: strict runtime mode optional; default auto with deterministic fallback.
