# JEPA Architect Context Contract V1

Marker: `MARKER_155C.JEPA_ARCH_SHARED_CONTRACT.V1`  
Status: active  
Date: 2026-03-02

## 1) Purpose
Unified contract for JEPA-assisted architect bootstrap context between MCC and VETKA runtimes.

This is a shared-contract artifact, not a requirement to share route/runtime implementations.

## 2) Context payload
`jepa_context` is an optional compact semantic digest string that can be injected into architect system prompt.

When absent, architect flow must continue via deterministic fallback path (no hard failure).

## 3) Required trace fields
Bootstrap trace must expose these fields:
1. `jepa_forced: bool`
2. `jepa_trigger: bool`
3. `provider_mode: str`
4. `latency_ms: float`
5. `fallback_reason: str`

Additional fields are allowed (for example: `jepa_skip_reason`, `scope_root`, `jepa_trigger_forced`).

## 4) Policy semantics
1. First architect turn + non-empty codebase:
   - force JEPA bootstrap (`jepa_forced=true`).
2. First architect turn + empty/new project:
   - skip JEPA (`fallback_reason=empty_project_skip`).
3. Non-first turn:
   - no forced bootstrap (`fallback_reason=not_first_turn`).

## 5) Runtime behavior guarantees
1. Architect request must not fail solely due to JEPA runtime unavailability.
2. Any runtime failure must map to trace fallback (`fallback_reason=bootstrap_error:*`) and continue request processing.
3. Provider-specific details can vary, but the required fields above must remain stable.
