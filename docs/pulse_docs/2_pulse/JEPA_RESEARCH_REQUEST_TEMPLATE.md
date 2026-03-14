# JEPA Audio Research Request Template (for Grok/ChatGPT)

Use this prompt as-is when requesting external research.

---

You are helping with Pulse (Tauri + React + Tone.js), a realtime gesture synth with scale/key/BPM inference.

## Task
Design a practical **audio-JEPA calibration/training strategy** for realtime scale inference stability.

## Constraints
- Realtime budget: inference fallback <= 700 ms timeout, no added audible latency.
- Deterministic engine remains primary; JEPA is arbitration/fallback under ambiguity.
- Need measurable gains on:
  - top1 scale accuracy,
  - top3 recall,
  - generic fallback rate (Ionian/Chromatic/Spanish),
  - flip-rate per minute,
  - commit latency.

## Existing pipeline
- Dataset fetch/index scripts already exist.
- Corpus index schema: `sample_id,dataset,path,split,bpm_ref,key_ref,scale_ref,label_quality,source_type`.
- A/B benchmark exists for deterministic vs deterministic+JEPA.

## What I need from you
1. Best open-source **audio JEPA-compatible** repos/models with active maintenance (2025-2026), and exact why-fit for scale inference.
2. Exact training recipe for low-latency reranking:
   - input features,
   - model head,
   - losses,
   - calibration strategy,
   - confidence estimation.
3. Dataset strategy using MAESTRO, ChoCo, Lakh, Groove, GTZAN:
   - what to use for supervised labels,
   - what to use for self-supervised pretraining,
   - split policy to avoid leakage.
4. Evaluation protocol with formulas and recommended threshold targets.
5. Deployment strategy in Pulse:
   - fallback/circuit-breaker policy,
   - model quantization options,
   - CPU-only path.
6. Risks and mitigations (domain shift, noisy mic, overfitting synthetic data).

## Output format
- Give a step-by-step implementation plan (week-by-week).
- Include concrete hyperparameter ranges.
- Include a minimal reproducible experiment spec.
- Include “reject conditions” when JEPA should not be enabled.

---
