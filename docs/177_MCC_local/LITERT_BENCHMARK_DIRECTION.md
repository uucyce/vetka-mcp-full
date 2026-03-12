# PHASE 177 — LiteRT benchmark direction

Date: 2026-03-12
Status: proposal
Tag: `localguys`, `litert`, `benchmark`

## Why this matters
LiteRT is now a credible on-device runtime candidate for Apple Silicon benchmarking.
For VETKA this is interesting not as a core dependency yet, but as a benchmark lane for:
- local inference acceleration on macOS
- comparison against the current local model/runtime stack
- future vision/audio/helper workers where on-device acceleration matters

## Scope for Phase 177
Keep LiteRT as a benchmark and feasibility direction, not a required MCC runtime dependency.

Phase 177 should answer:
1. Does LiteRT on Apple Silicon give useful latency/throughput gains for our likely workloads?
2. Which workloads are realistic candidates: vision, embedding helpers, classifier/router helpers, lightweight local workers?
3. Can we compare LiteRT metrics inside the same MCC/localguys benchmark surface?

## Constraints
- do not couple MCC core runtime to LiteRT in the first pass
- do not assume Apple Neural Engine support is production-ready for our macOS use case
- treat Metal/GPU as the first realistic target on M-series Macs
- benchmark with the same reporting shape we already use for localguys

## Proposed benchmark lanes
### Lane A — Runtime feasibility
- install/build LiteRT on Apple Silicon
- verify minimal macOS execution path
- confirm model loading, execution, and repeatability

### Lane B — Metrics comparison
Compare against the current local stack on:
- cold start latency
- steady-state runtime
- artifact/report overhead
- batch repeatability
- energy/thermal notes if measurable

### Lane C — Candidate workloads
Score LiteRT for these VETKA-relevant roles:
- router/classifier helper
- embeddings helper
- vision scout helper
- small verifier/helper models

## Deliverables
- benchmark notes
- reproducible command set
- metrics table with the same summary fields as localguys benchmarks
- explicit recommendation: `adopt`, `keep as benchmark`, or `drop`

## Success criteria
- we have one comparable benchmark pack on Apple Silicon
- MCC/localguys metrics can display LiteRT results in the same summary vocabulary
- we know whether LiteRT is strategic, experimental, or not worth pursuing
