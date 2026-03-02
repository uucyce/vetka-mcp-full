# Pulse × VETKA — Unified Implementation Roadmap

Date: 2026-02-27  
Owner: Pulse subproject team  
Status: Active (execution checklist)

## 0) Context
Pulse is a standalone app now, but must become a VETKA submodule with memory-aware music adaptation.

Current reality from codebase:
- BPM stability improved with lock/guard, but scale inference still collapses to fallback scales too often (e.g. Spanish/Ionian).
- Current JEPA integration is **reranking via text-embedding runtime**, not dedicated audio JEPA.
- Deterministic path remains primary for realtime control; ML must be fallback and measurable.
- New research update (2026-02-27): JEPA personalization is feasible and promising, but requires user-specific feedback data (implicit + explicit) and strict anti-overfit gates.

## 1) Non-Negotiable Product Goals
- Stable key/scale under live mic noise.
- Realtime playable latency (no perceptible lag in gesture-to-sound).
- Scale must be reflected both in UI and in actual quantized audio output.
- One coherent behavior model: no contradictions between active/detected states.
- Future-ready memory loop with VETKA subsystems.
- Personalized scale/genre behavior must improve user outcomes without destabilizing realtime inference.

## 2) Execution Rules (Checklist Protocol)
- [ ] Each phase has explicit Done Criteria and acceptance tests.
- [ ] No move to next phase before current phase acceptance passes.
- [ ] Every tuning change must be logged (config diff + metric delta).
- [ ] Any ML fallback must show measurable gain over deterministic baseline.
- [ ] Regression suite must pass before packaging builds.

## 3) Phase Plan

Related doc:
- `PULSE_UI_V2_ONE_CIRCLE_ROADMAP.md` (performance-first UI + Dev Panel split)
- `JEPA_AUDIO_CALIBRATION_PLAN.md` (JEPA calibration datasets/metrics/tasks)
- `JEPA_DEVELOPMENT_PLAN.md` (execution phases for JEPA audio-first rollout)
- `JEPA_RESEARCH_REQUEST_TEMPLATE.md` (external research prompt template)

## 3.1) Progress Snapshot (2026-02-27, verified)
- Completed:
  - Offline A/B harness + reports (`scale_ab_report`, `scale_ab_offline_report`).
  - Threshold sweep and calibration pack generators.
  - Personalization core (`PersonalizationFeedback.ts`) with bounded bias cap and tests.
  - Runtime JEPA personalization flag and profile wiring in app.
  - Personalization bias sweep added (`bench:personalization:sweep`) with reproducible CSV/MD report.
- Partial:
  - ENGRAM/CAM integration is local-file bridge only (not full VETKA memory bus).
  - Feedback event collection is not fully wired from live UI interactions to durable event log.
  - Offline benchmark currently uses synthesized replay from labeled subset, not full live-session replay.
- Risk now:
  - Metrics can look ideal offline while realtime UX still drifts on scale due to missing real feedback loop and weak live-ground-truth evaluation.

Calibration note (current defaults):
- `scaleWeightFactor = 0.04`
- `genreWeightFactor = 0.03`
- `maxBias = 0.08`

Reproduce:
- `npm run bench:personalization:sweep`
- Report outputs:
  - `pulse/data/processed/personalization_bias_sweep.csv`
  - `pulse/data/processed/personalization_bias_sweep.md`

### Phase A — Deterministic Stabilization (short horizon)
Objective: make baseline reliable before heavy ML.

Checklist:
- [ ] A1. Add scale decision telemetry JSONL (top3, chosen, margin, reason, bpm, notes).
- [ ] A2. Add hold/commit hysteresis tuning table in config (single source of truth).
- [ ] A3. Add stronger anti-fallback policy:
  - if top1 is generic (`Spanish/Chromatic/Ionian`) and top2/3 close, delay commit.
- [ ] A4. Add “candidate aging”: keep previous stable scale unless new candidate wins for N cycles.
- [ ] A5. Add “manual lock” priority guard:
  - manual scale/key must never be overridden by auto.

Done Criteria:
- Wrong commits/min reduced by >= 35% on internal live test set.
- Generic fallback share (`Spanish/Chromatic/Ionian`) reduced by >= 40%.
- No added audible latency.

---

### Phase B — Evaluation Harness and Calibration Data
Objective: move from subjective tuning to measurable tuning.

Checklist:
- [ ] B1. Create offline benchmark runner for Pulse inference (no camera dependency).
- [ ] B2. Build reference dataset pack:
  - synthetic clips (known BPM/key/scale),
  - short curated real clips with known labels.
- [ ] B3. Export metrics:
  - BPM MAE,
  - scale top1 accuracy,
  - scale top3 recall,
  - flip rate per minute,
  - commit latency.
- [ ] B4. Add auto-report CSV + markdown summary.
- [ ] B5. Add threshold sweep tool (grid search for commit penalties/holds).

Done Criteria:
- Reproducible benchmark command returns stable metrics table.
- Tuning decisions are justified by measured deltas, not intuition.

---

### Phase C — JEPA Layer (Proper Audio Path)
Objective: replace weak rerank heuristics with audio-aware embeddings.

Status note:
- Groundwork added: windowed feature snapshots + JEPA feature-aware resolver.

Checklist:
- [ ] C1. Introduce JEPA adapter interface in Pulse:
  - deterministic features in,
  - ranked scale proposals out.
- [ ] C2. Add **audio feature payload** (not text-only):
  - 3 rolling windows histograms,
  - onset envelope summary,
  - BPM stability stats,
  - recent commit history.
- [ ] C3. Add ML arbitration policy:
  - deterministic wins when confidence high,
  - JEPA used only when deterministic low/conflicted.
- [ ] C4. Add JEPA timeout/circuit-breaker:
  - fallback to deterministic only on delay/failure.
- [ ] C5. Add A/B switch:
  - deterministic vs deterministic+JEPA.

Done Criteria:
- ML variant beats deterministic baseline on top1/top3 without raising latency regressions.

---

### Phase D — Training Data and Model Lifecycle
Objective: establish repeatable model training/calibration loop.

Datasets/libraries to include in pipeline:
- Groove MIDI / E-GMD
- Lakh MIDI
- MAESTRO
- ChoCo
- GTZAN (for audio-side robustness checks)
- MUSPY, mirdata, Magenta tools

Checklist:
- [ ] D1. Define canonical label schema:
  - bpm, key, scale, confidence, source provenance.
- [ ] D2. Build dataset ingestion scripts and split strategy (train/val/test).
  - status: implemented base scripts `fetch_jepa_datasets.sh`, `prepare_jepa_corpus.py`, `build_jepa_training_manifest.py`.
- [ ] D3. Add synthetic data generator (known-scale MIDI renders).
- [ ] D4. Define calibration set from real Pulse sessions.
- [ ] D5. Add model card template (what changed, why, metric impact).

Done Criteria:
- One command can reproduce training/eval dataset indexes and metrics.
- Calibration set exists and is versioned.

---

### Phase D2 — JEPA Personalization (ENGRAM/CAM)
Objective: adapt JEPA reranking to user preferences in genre/scale while keeping deterministic safety.

Research-backed assumptions:
- Generic datasets are required for base representations, but personalization requires user feedback data.
- Strongest practical setup is hybrid feedback:
  - implicit: playtime/skip/repeat behavior,
  - explicit: like/dislike/rating on suggested scale/genre.
- Deterministic engine remains primary; personalized JEPA only reranks candidate set.

Checklist:
- [ ] D2.1 Define personalization event schema:
  - `user_id, session_id, timestamp, detected_scale, committed_scale, genre, bpm, confidence, play_sec, skip_flag, explicit_feedback`.
- [ ] D2.2 Add implicit feedback collection in Pulse sessions:
  - play duration buckets, skip events, repeat counts.
- [ ] D2.3 Add explicit feedback controls:
  - post-jam `+1 / -1` for scale and optional genre rating.
- [ ] D2.4 Add ENGRAM contract for preference memory:
  - `preferred_scales`, `preferred_genres`, `confidence`, `aging_decay`.
- [ ] D2.5 Add CAM linkage:
  - map preferred genre/scale pairs to successful synth/preset context.
- [ ] D2.6 Implement personalization bias layer in reranking:
  - deterministic top candidates first,
  - apply bounded user-bias score (`+w_pref`, `-w_dislike`) to candidate confidences.
- [ ] D2.7 Add anti-overfit protections:
  - minimum evidence threshold before applying prefs,
  - recency decay (session aging),
  - fallback to non-personalized ranking when confidence low.
- [ ] D2.8 Add A/B evaluation:
  - baseline JEPA vs personalized JEPA on same eval subset + session logs.

Done Criteria:
- Personalized mode improves at least one of:
  - top3 recall,
  - commit match rate,
  - user feedback acceptance rate,
  without regression in:
  - flip rate,
  - commit latency,
  - realtime stability.
- Personalization can be disabled at runtime by config flag.

---

### Phase E — Pulse Audio UX and ARP Coherence
Objective: keep performance musical and predictable in live play.

Checklist:
- [ ] E1. Confirm single-voice morph model:
  - legato <-> pulse-arp via ADSR + gate/swing only.
- [ ] E2. Add debug overlays:
  - current quantized note source scale,
  - commit reason,
  - BPM lock state.
- [ ] E3. Add anti-click smoothing and envelope transitions.
- [ ] E4. Add preset diversity expansion with clear timbre separation.
- [ ] E5. Validate that ARP and legato use same synth voice chain.

Done Criteria:
- No “separate instrument” perception during legato↔arp transitions.
- Internal sounds audibly distinct and controllable.

---

### Phase G — JEPA Ops Console (Dev Panel, low-token autonomy)
Objective: дать оператору полный self-serve цикл без терминала/Codex.

Checklist:
- [x] G1. Dev Panel кнопки пайплайна:
  - `Prepare`, `Verify`, `ENGRAM Build`, `Bench Offline`, `Quality Gate`.
- [x] G2. Backend команды Tauri для запуска pipeline steps и возврата stdout/stderr/status.
- [x] G3. Snapshot виджет:
  - training stats preview,
  - offline A/B preview,
  - quality gate preview,
  - spectral telemetry event count + last event.
- [x] G4. Teletype теги для pipeline/snapshot:
  - `PIPELINE_OK`, `PIPELINE_ERR`, `JEPA_SNAPSHOT`.
- [x] G5. Автономный handoff-док с командами и форматом labels.

Done Criteria:
- Пользователь может запускать JEPA cycle из Dev Panel без terminal.
- Результаты видны сразу в UI и пишутся в отчеты/артефакты.

---

### Phase F — Pulse → VETKA Integration (Memory + Intelligence)
Objective: prepare Pulse as memory-aware VETKA component.

#### ENGRAM (preference memory)
Use case:
- persist which scales/modes user repeatedly stabilizes on,
- weighted by session outcome quality.

Checklist:
- [ ] F1. Define `preferred_scales` memory contract.
- [ ] F2. Read ENGRAM priors to bias scale candidate ranking.
- [ ] F3. Write back preference updates after validated sessions.
- [ ] F3.1 Add preference aging:
  - decay older interactions to avoid stale taste lock-in.
- [ ] F3.2 Separate implicit vs explicit preference channels:
  - explicit feedback has higher trust weight.

#### CAM (successful instrumentation memory)
Use case:
- remember winning instrument/preset choices for contexts.

Checklist:
- [ ] F4. Define `successful_instrument_context` contract.
- [ ] F5. Auto-suggest preset/VST from CAM when genre/scale stable.
- [ ] F6. Session feedback updates CAM scores.
- [ ] F6.1 Add personalization bridge:
  - if user prefers scale/genre cluster, boost matching CAM contexts first.

#### ARC (hypothesis engine)
Use case:
- propose likely next key/scale moves when confidence drops.

Checklist:
- [ ] F7. ARC hook for “hypothesis proposals” API.
- [ ] F8. Use proposals only as soft priors (never hard override).

#### HOPE (scale hierarchy/ontology)
Use case:
- enforce hierarchy:
  - parent family (major/minor/modal),
  - child niche scales.

Checklist:
- [ ] F9. Integrate HOPE hierarchy graph in candidate filtering.
- [ ] F10. Prevent low-evidence jumps across distant families.

#### STM (short-term memory)
Use case:
- stabilize decisions over recent phrase memory.

Checklist:
- [ ] F11. Add STM buffer for last N bars decisions and note histograms.
- [ ] F12. Use STM consensus to reduce flip rate.

#### Eval Agent (feedback loop)
Use case:
- automatic quality scoring and tuning suggestions.

Checklist:
- [ ] F13. Emit session metrics to Eval agent.
- [ ] F14. Receive threshold recommendations as non-breaking config patches.

Done Criteria for Phase F:
- Pulse can read/write memory signals through defined contracts.
- Memory improves stability metrics on repeated user sessions.

---

### Phase G — Packaging, Ops, and Release Gates
Checklist:
- [ ] G1. Add release gate script:
  - benchmark minimum thresholds must pass.
- [ ] G2. Add runtime health panel:
  - deterministic engine status,
  - JEPA status,
  - memory connectors status.
- [ ] G3. Add rollback-safe config versioning.
- [ ] G4. Define support matrix for standalone Pulse vs embedded VETKA mode.

Done Criteria:
- Every release has metric report + pass/fail gate decision.

---

### Phase H — UI Productization (One Circle + Dev Panel)
Objective: split performative instrument UI from engineering diagnostics.

Checklist:
- [ ] H1. Deliver performance-first default window (One Circle).
- [ ] H2. Move all engineering controls/diagnostics to Dev Panel.
- [ ] H3. Add 10-line teletype process log in Dev Panel.
- [ ] H4. Hide raw camera feed in performance mode (skeleton-only option).
- [ ] H5. Keep visual language consistent with Itten/Camelot mapping.

Done Criteria:
- Default UI is stage-friendly and minimal.
- Dev Panel retains full tuning/debug capability.

## 4) Immediate Next Sprint (Start Here)
Sprint target: Phase A + B foundation.

Execution checklist:
- [ ] S1. Implement telemetry JSONL for scale decisions.
- [ ] S2. Build benchmark runner skeleton (CLI).
- [ ] S3. Create minimal labeled clip set (synthetic first).
- [ ] S4. Add anti-generic commit rule (`Spanish/Chromatic/Ionian` delay).
- [ ] S5. Generate first baseline report.

## 5) Risks and Mitigations
- Risk: model overfitting to synthetic MIDI.
  - Mitigation: mixed eval set (synthetic + real mic sessions).
- Risk: JEPA latency harms playability.
  - Mitigation: strict timeout + circuit-breaker + asynchronous fallback.
- Risk: memory priors overpower live evidence.
  - Mitigation: priors only as soft weights; confidence gates remain primary.

## 6) Definition of Success
- BPM stable under real-room noise.
- Scale commit aligns with top candidates and audible output.
- Reduced fallback-scale lock-in.
- Pulse gains measurable improvement from VETKA memory connectors.
