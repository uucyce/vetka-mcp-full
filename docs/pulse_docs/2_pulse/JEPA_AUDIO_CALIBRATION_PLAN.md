# Pulse — JEPA Audio Calibration Plan

Date: 2026-02-27  
Scope: scale/key robustness improvements via JEPA-compatible calibration loop

## 1) Reality Check (Current State)
- JEPA runtime is available at `http://127.0.0.1:8099`.
- Current Pulse JEPA usage is rerank fallback, not fully trained Audio-JEPA classifier.
- Deterministic scale inference remains primary decision layer.
- BPM is now more stable, but scale still tends to generic fallbacks in ambiguous/noisy phrases.

## 2) What Was Added in Code
- `ScaleInferenceWindowed` now exposes feature snapshots:
  - 3 rolling window histograms (12-d),
  - unique note counts,
  - per-window evidence weights,
  - bpm/window stride metadata.
- `JepaScaleResolver` now accepts structured audio feature snapshots for reranking context.
- Synthetic benchmark harness added:
  - `src/music/ScaleBenchmark.ts`
  - `src/__tests__/scale_benchmark.test.ts`
  - run via `npm run bench:scale`

## 3) Why Matrix-Only Is Not Enough
Interval matrix alone cannot robustly disambiguate:
- modal neighbors (Dorian vs Aeolian vs Phrygian),
- noisy partial-note captures,
- phrase-dependent context where important notes appear sparsely.

Need temporal + confidence-aware training/calibration data.

## 4) Dataset Stack (Recommended)
Primary symbolic:
- Groove MIDI / E-GMD
- Lakh MIDI
- MAESTRO
- ChoCo

Audio robustness:
- GTZAN (for noisy/real audio stress checks)

Tooling:
- MUSPY
- mirdata
- Magenta loaders

## 5) Label Schema (Minimum)
Each sample/chunk should include:
- `sample_id`
- `source` (synthetic|dataset|live)
- `bpm_ref`
- `key_ref`
- `scale_ref`
- `confidence_ref`
- `notes/chroma summary`
- `genre(optional)`

## 6) Calibration Pipeline
1. Generate synthetic baseline set (known key/scale/bpm).
2. Add curated real clips with trusted labels.
3. Run deterministic baseline benchmark.
4. Run deterministic + JEPA rerank benchmark.
5. Compare metrics:
- top1 accuracy
- top3 recall
- commit-match rate
- flip rate/min
- latency overhead
6. Keep JEPA path only if gain is measurable.

## 7) Immediate Next Tasks (Execution Checklist)
- [ ] Build dataset ingest manifest (CSV/JSONL) with schema above.
- [ ] Add benchmark report writer (CSV + markdown summary).
- [ ] Add A/B runner: deterministic vs deterministic+JEPA.
- [ ] Tune generic penalties (Spanish/Chromatic/Ionian) using benchmark outputs.
- [ ] Prepare first calibration batch from live Pulse sessions.

## 8) Acceptance Criteria
- JEPA-enabled path improves scale top1/top3 metrics over deterministic baseline.
- Generic fallback rate decreases on ambiguous phrases.
- No perceptible realtime latency degradation in live gesture play.
