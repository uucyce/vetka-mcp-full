# Grok Research Intake (Phase 159)
**Date:** 2026-03-04  
**Input:** user-provided Grok synthesis (queue/workflow, Premiere bridge, feature envelope, E2E matrix).

## Decision Summary
Материал принимается как strong reference baseline. Ниже фиксируется engineering cut для VETKA (accept/adapt/defer).

## 1) Async Orchestration (Media-MCP)
### Accept
1. State model: `queued | running | partial | done | error`.
2. Idempotency key (`job_id` + stable input hash).
3. Retry with exponential backoff and capped attempts.
4. DLQ for non-transient failures.
5. Separate queues by priority (`preview` vs `heavy`).

### Adapt for VETKA
1. Start with existing stack first (no immediate Temporal lock-in).
2. Add workflow engine as pluggable layer after queue + schema freeze.
3. Progress transport: SSE first, WebSocket optional.

### Defer
1. Kubernetes autoscaling policy as phase-after baseline worker stability.

## 2) Premiere Live Bridge Reliability
### Accept
1. Correlation ID + ack/result protocol.
2. Timeout + retry + deterministic fallback to XML interchange.
3. Operation allowlist for live mode.
4. Locking semantics per sequence/job.

### Adapt for VETKA
1. Keep file-bridge v1 (already implemented) and harden protocol fields before moving to websocket transport.
2. Keep `PremiereAdapter` as sole boundary (no route-level bridge logic).

### Defer
1. Full websocket JSON-RPC bridge as P6.x hardening phase.

## 3) Unified JEPA/PULSE/CAM Feature Envelope
### Accept
1. Canonical segment schema with per-dimension scores (`rhythm/motion/uniqueness/semantics`).
2. Per-segment `confidence` and `latency_ms`.
3. Enricher identity/mode in payload.

### Adapt for VETKA
1. Keep backwards compatibility with current `media_chunks_v1` by additive fields only.
2. Use `plugin_mode` + `schema_version` guards for non-breaking evolution.

## 4) Real-World Validation
### Accept
1. E2E matrix: ingest -> scan -> preview -> transcript -> export -> Premiere import.
2. Failover cases as mandatory tests (timeout, malformed media, missing bridge).
3. Explicit acceptance thresholds.

### Adapt for VETKA
1. Start with local reproducible fixtures (Berlin set + synthetic audio/video), then broaden.
2. Add manual Premiere import smoke as release gate until full automation is stable.

## Anti-Patterns (Adopted as hard rules)
1. No sync heavy processing in UI/API request path.
2. No infinite retries.
3. No endpoint-specific schema drift.
4. No live-bridge operations outside allowlist.

## Immediate Implementation Mapping (next)
1. L0.1: `MediaMCPJob` schema + validation tests.
2. L1.1: `MediaPipelineService` with thin routes.
3. L2.1: real async progress source for media startup (replace static phases).
