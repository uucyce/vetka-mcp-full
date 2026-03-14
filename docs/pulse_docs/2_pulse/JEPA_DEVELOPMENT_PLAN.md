# Pulse JEPA Development Plan (Audio-First)

Date: 2026-02-27
Owner: Pulse JEPA track (architect)

## Goal
Move from heuristic reranking to reproducible, audio-aware JEPA calibration with measurable gains in scale stability.

## Current State
- Realtime path: deterministic windowed inference + JEPA rerank fallback.
- A/B harness exists (`bench:scale:ab`) but mostly synthetic.
- Data pipeline scaffold exists (`fetch_jepa_datasets.sh`, `prepare_jepa_corpus.py`).
- New training-manifest builder exists (`build_jepa_training_manifest.py`).

## Phase 1 — Data Readiness (now)
- [ ] Download/import labeled datasets (at least MAESTRO + ChoCo + one groove set).
- [ ] Build corpus index: `prepare_jepa_corpus.py`.
- [ ] Build training manifest and stats: `build_jepa_training_manifest.py`.
- [ ] Gate: `scale_ref` coverage >= 25% and `bpm_ref` coverage >= 40%.

## Phase 2 — Offline Calibration
- [ ] Create fixed eval subset (frozen file list) in `pulse/data/processed/jepa_eval_subset.jsonl`.
- [ ] Run deterministic vs deterministic+JEPA A/B on same subset.
- [ ] Add metrics:
  - top1_accuracy
  - top3_recall
  - commit_match_rate
  - flip_rate_per_min
  - generic_fallback_rate (`Spanish|Ionian|Chromatic`)
  - commit_latency_ms
- [ ] Gate: JEPA variant improves top3_recall and reduces fallback_rate without latency regression.

## Phase 3 — Runtime Hardening
- [ ] Keep JEPA as arbitration-only when deterministic confidence is ambiguous.
- [ ] Add JEPA timeout + circuit breaker + cooldown.
- [ ] Add telemetry JSONL for decisions and reason codes.
- [ ] Gate: no audible regressions; deterministic fallback always safe.

## Phase 4 — VETKA Memory Integration
- [ ] ENGRAM: user scale preference priors (soft bias only).
- [ ] STM: short-memory consensus over recent bars to reduce scale flips.
- [ ] CAM: successful instrument mappings for stable contexts.
- [ ] Eval Agent: post-session metric scoring and threshold recommendations.

## Phase 5 — JEPA Personalization Rollout (new)
- [ ] Add feedback data collection:
  - implicit (`play_sec`, `skip_flag`, repeats),
  - explicit (`like/dislike` for suggested scale/genre).
- [ ] Add personalization profile in ENGRAM:
  - weighted preferences by scale + genre,
  - recency decay per session.
- [ ] Add bounded rerank bias:
  - deterministic candidates first,
  - apply preference bonus/penalty with cap.
- [ ] Add personalization gating:
  - enable only after minimum feedback count threshold.
- [ ] Add A/B reporting:
  - JEPA baseline vs JEPA personalized
  - include acceptance-rate metric from explicit feedback.

Personalization gates:
- Do not enable if feedback sample size is too small.
- Do not enable if flip-rate or latency regresses.
- Always allow hard fallback to non-personalized deterministic path.

## DoD
- Reproducible commands produce:
  - dataset status,
  - corpus index,
  - training manifest,
  - A/B report CSV+MD,
  - documented threshold changes.
- JEPA path must be measurable and reversible.
