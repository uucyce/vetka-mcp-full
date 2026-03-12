# LiteRT Feasibility Notes — 2026-03-12

Status: verified notes
Task: `tb_1773275513_6`

## Verified facts
- LiteRT is the official successor to TensorFlow Lite and remains open source under Google AI Edge.
- Official upstream repo: `google-ai-edge/LiteRT`.
- LiteRT docs currently present desktop/laptop support in the product overview.
- macOS support is relevant for our Apple Silicon benchmark lane, but we should treat Metal/GPU as the practical first target.
- Apple Neural Engine on macOS should not be assumed production-ready for our lane until verified by our own smoke test and current upstream docs.

## What this means for VETKA
Use LiteRT as a benchmark candidate, not a Phase 177 core dependency.
The first question is not "can LiteRT replace MCC runtime".
The first question is "does LiteRT produce enough measurable benefit on Apple Silicon for one of our helper lanes".

## Candidate VETKA lanes
1. router/classifier helper
2. embedding helper
3. vision scout helper
4. small verifier/helper model lane

## Initial benchmark shape
- runtime name: `litert`
- device profile: Apple Silicon local machine
- accelerator: `cpu` or `gpu_metal`
- cold start ms
- avg runtime ms
- success rate
- notes

## First-pass smoke plan
1. confirm minimal local install/build path
2. identify one small compatible model path
3. run one CPU smoke
4. run one GPU/Metal smoke if available
5. record whether the benchmark lane stays viable

## Explicit non-goals for first pass
- no MCC runtime replacement
- no ANE assumptions
- no broad integration work before one reproducible benchmark

## 2026-03-12 smoke bench update
- Added `scripts/litert_smoke_bench.py` as the bounded execution slice for local LiteRT detection and MCC benchmark publishing.
- Current host result: `run_status=blocked`, `device_profile=apple_silicon`, `accelerator=gpu_metal`, `notes=ai_edge_litert_not_installed`.
- Next live step after install: run `python scripts/litert_smoke_bench.py --publish` against the local MCC server to push the first real LiteRT benchmark row into `/api/mcc/localguys/benchmark-summary`.
