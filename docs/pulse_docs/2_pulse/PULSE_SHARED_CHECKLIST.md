# Pulse Shared Checklist (Architect + Terminal)

Date: 2026-02-27  
Purpose: единый координационный лог до финала.

## 0) Rules of Engagement
- Перед каждой существенной имплементацией: `AUDIT marker`.
- После имплементации: `IMPL marker`.
- После проверки: `TEST marker`.
- Нет теста -> задача не считается завершённой.
- Любой конфликт/отклонение -> `BLOCKER marker` + короткое сообщение другому агенту.

## 1) Global Definition of Done (Final)
- [ ] Scale/key drift в live заметно снижен (по agreed метрикам).
- [ ] BPM стабилен и не прыгает от одиночных всплесков.
- [ ] ARP/legato воспринимается как единый voice chain.
- [ ] Personalization loop: feedback -> ENGRAM profile -> rerank работает стабильно.
- [ ] UI разделен: clean performance + functional dev panel.
- [ ] VST workflow минимум ручного трения (manual control + predictable switching).
- [ ] Все критичные сценарии покрыты тестами.
- [ ] Build/bench scripts воспроизводимы одной командой.

## 2) Current Status Snapshot
- UI split: done.
- JEPA data pipeline: done (base).
- Feedback loop + ENGRAM rebuild: done (base).
- Bias sweep for personalization defaults: done (base).
- Full audio-JEPA training/inference pipeline: not done.
- Production packaging guarantees (python/runtime scripts): partial (transitional, migration risk controlled).

## 3) Open Work Packages

### WP-A (Architect) — Core intelligence
- [x] `MARKER_AUDIT_A1` Audit arbitration thresholds and commit logic.
- [x] `MARKER_IMPL_A1` Centralized policy config for key/scale commit.
- [x] `MARKER_TEST_A1` Unit+integration for policy invariants.

- [x] `MARKER_AUDIT_A2` Audit BPM->Scale coupling side effects.
- [x] `MARKER_IMPL_A2` Robust BPM lock contract for inference windows.
- [x] `MARKER_TEST_A2` Synthetic stress tests for BPM spikes.

- [x] `MARKER_AUDIT_A3` Audit JEPA fallback quality on ambiguous scales.
- [x] `MARKER_IMPL_A3` Improve rerank arbitration and reject low-value JEPA calls.
- [x] `MARKER_TEST_A3` A/B report with confidence intervals.

- [x] `MARKER_AUDIT_A4` Audit teletype contract consistency (machine-readable reasons).
- [x] `MARKER_IMPL_A4` Introduce unified telemetry formatter and normalized reason payloads.
- [x] `MARKER_TEST_A4` Add telemetry contract tests.

- [x] `MARKER_AUDIT_A5` Audit packaged ENGRAM rebuild dependency chain (python/script/runtime paths).
- [x] `MARKER_IMPL_A5` Implement dual-engine rebuild strategy: python primary + native fallback.
- [x] `MARKER_TEST_A5` Add native rebuild tests and keep app integration green.
- [x] `MARKER_AUDIT_A6` Audit spectral feature ingress for JEPA rerank context.
- [x] `MARKER_IMPL_A6` Add `SpectralScaleFeatures` module + SmartAudio snapshot wiring into JEPA rerank.
- [x] `MARKER_TEST_A6` Add `spectral_scale_features` tests and ensure green build.
- [x] `MARKER_AUDIT_A7` Audit ARP callback contract for legacy morph leakage.
- [x] `MARKER_IMPL_A7` Remove `morph` from ARP step callback and keep ADSR-only pulse path.
- [x] `MARKER_TEST_A7` Add ADSR contract tests and verify no regressions in compile.
- [x] `MARKER_AUDIT_A8` Audit self-serve operation gap (user required terminal for JEPA cycle).
- [x] `MARKER_IMPL_A8` Add DevPanel JEPA Ops buttons + Tauri pipeline commands + dashboard snapshot command.
- [x] `MARKER_TEST_A8` Build/tests green after UI+Tauri integration for no-terminal operation.

### WP-T (Terminal) — Runtime plumbing & UI operations
- [x] `MARKER_AUDIT_T1` Audit teletype signal quality/noise.
- [x] `MARKER_IMPL_T1` Dedupe/rate-limit for noisy events.
- [x] `MARKER_TEST_T1` Burst event integration test.

- [x] `MARKER_AUDIT_T2` Audit packaged runtime dependencies.
- [x] `MARKER_IMPL_T2` Path and script diagnostics (explicit fallback messages).
- [x] `MARKER_TEST_T2` Dev vs packaged path resolver tests.

- [x] `MARKER_AUDIT_T3` Audit feedback schema evolution.
- [x] `MARKER_IMPL_T3` Add schema_version and migration safety.
- [x] `MARKER_TEST_T3` Backward compatibility tests.

- [x] `MARKER_AUDIT_T4` Audit python-sidecar dependency surface for packaged runtime.
- [x] `MARKER_IMPL_T4` Define migration task-map to native/JS ENGRAM rebuild path (no behavior change now).
- [x] `MARKER_TEST_T4` Add acceptance checklist/tests for sidecar-free rebuild readiness.

- [x] `MARKER_AUDIT_B1` Audit spectral telemetry persistence gaps.
- [x] `MARKER_IMPL_B1` Add durable spectral telemetry JSONL persistence.
- [x] `MARKER_TEST_B1` Persistence/schema tests + app test/build checks.

- [x] `MARKER_AUDIT_B2` Audit one-shot quality gate command/report gap.
- [x] `MARKER_IMPL_B2` Add quality gate command with md/csv output and strict exit code.
- [x] `MARKER_TEST_B2` Run gate end-to-end + tests for pass/fail exit behavior.

- [x] `MARKER_AUDIT_B3` Audit pulse_spectral_telemetry ingestion needs.
- [x] `MARKER_IMPL_B3` Add ingestion/aggregation tool + reports for `pulse_spectral_telemetry.jsonl`.
- [x] `MARKER_TEST_B3` Add ingestion tests and rerun quality gate.

## 4) Message Board (short handoff notes)
Format:
- `[FROM][UTC][MARKER] message`

Entries:
- `[ARCH][2026-02-27][INIT] Tracks split. Core inference/JEPA policy remains Architect-owned.`
- `[TERM][2026-02-27][ACK] Runtime feedback loop and ENGRAM rebuild wired, tests added.`
- `[ARCH][2026-02-27][MARKER_AUDIT_A1] Thresholds audited: JEPA rerank/commit and key evidence were scattered in App.tsx.`
- `[ARCH][2026-02-27][MARKER_IMPL_A1] Introduced ScaleCommitPolicy module and migrated App.tsx decisions to policy helpers.`
- `[ARCH][2026-02-27][MARKER_TEST_A1] Added scale_commit_policy tests (5) + integration sanity run + build pass.`
- `[ARCH][2026-02-27][MARKER_AUDIT_A2] BPM->inference coupling audited: inference consumed rapidly-updating BPM without lock contract.`
- `[ARCH][2026-02-27][MARKER_IMPL_A2] Introduced BpmLockPolicy and switched App realtime flow to locked BPM for inference/UI.`
- `[ARCH][2026-02-27][MARKER_TEST_A2] Added bpm_lock_policy tests (3) + policy/integration suite + build pass.`
- `[ARCH][2026-02-27][MARKER_AUDIT_A3] JEPA arbitration audited: many calls were allowed without explicit skip reasons/cooldown policy in App layer.`
- `[ARCH][2026-02-27][MARKER_IMPL_A3] Added JepaArbitrationPolicy with cooldown, low-confidence skip, deterministic-ready skip and explicit decision reasons in teletype.`
- `[ARCH][2026-02-27][MARKER_TEST_A3] Added jepa_arbitration_policy tests (4) + policy suite + build pass.`
- `[ARCH][2026-02-27][MARKER_AUDIT_A4] Teletype format audited: mixed free-text messages limited post-analysis and consistency checks.`
- `[ARCH][2026-02-27][MARKER_IMPL_A4] Added PulseTelemetry contract and migrated key runtime events (BPM/KEY/SCALE/JEPA/AUDIO_LAYER) to normalized format.`
- `[ARCH][2026-02-27][MARKER_TEST_A4] Added pulse_telemetry tests (5) + policy suite + build pass.`
- `[ARCH][2026-02-27][MARKER_AUDIT_A5] Packaged runtime risk confirmed: ENGRAM rebuild relied on python script availability.`
- `[ARCH][2026-02-27][MARKER_IMPL_A5] Added native ENGRAM rebuild engine in Tauri and wired python->native fallback with diagnostics.`
- `[ARCH][2026-02-27][MARKER_TEST_A5] Rust lib tests (4/4, incl native rebuild) + app tests/build pass.`
- `[ARCH][2026-02-28][MARKER_AUDIT_A6] Spectral JEPA context audited: no explicit chroma/onset/bpm-stability payload existed in resolver input.`
- `[ARCH][2026-02-28][MARKER_IMPL_A6] Added SpectralScaleFeatures builder + SmartAudio getSpectralScaleFeatures() + App->JEPA wiring for ambiguity rerank.`
- `[ARCH][2026-02-28][MARKER_TEST_A6] Added spectral_scale_features.test.ts and verified targeted tests/build green.`
- `[ARCH][2026-02-28][MARKER_AUDIT_A7] ARP contract audited: callback still carried legacy morph arg despite ADSR-first policy.`
- `[ARCH][2026-02-28][MARKER_IMPL_A7] Removed morph from Arpeggiator callback contract and removed legacy setMorph API usage from SynthEngine.` 
- `[ARCH][2026-02-28][MARKER_TEST_A7] Added adsr_pulse_contract.test.ts and validated ADSR monotonic mapping + compile pass.`
- `[ARCH][2026-02-28][MARKER_AUDIT_A8] Low-token ops risk confirmed: user still depended on terminal for JEPA prepare/verify/bench/gate cycle.`
- `[ARCH][2026-02-28][MARKER_IMPL_A8] Added DevPanel JEPA Control Center + run_pipeline_step/get_jepa_dashboard_snapshot commands and teletype pipeline tags.`
- `[ARCH][2026-02-28][MARKER_TEST_A8] npm build + targeted vitest + cargo test --lib all green after ops-console integration.`
- `[TERM][2026-02-27][MARKER_AUDIT_T1] Teletype emits without dedupe/rate-limit; burst noise reproducible on repeated BPM/KEY updates.`
- `[TERM][2026-02-27][MARKER_IMPL_T1] Added teletype dedupe/rate-limit policy and wired App pushTeletype to policy append.`
- `[TERM][2026-02-27][MARKER_TEST_T1] Added burst integration test for dedupe + per-tag rate window cap; test green.`
- `[TERM][2026-02-27][MARKER_AUDIT_T2] Rebuild path depended on cwd/script presence; packaged diagnostics were implicit.`
- `[TERM][2026-02-27][MARKER_IMPL_T2] Added explicit runtime path diagnostics with source enum (env/dev/app_data) and diagnostics message.`
- `[TERM][2026-02-27][MARKER_TEST_T2] Added resolver tests for env override, dev current dir, and app_data fallback; cargo test green.`
- `[TERM][2026-02-27][MARKER_AUDIT_T3] Feedback events had no schema version; migration behavior for legacy rows was implicit.`
- `[TERM][2026-02-27][MARKER_IMPL_T3] Added schema_version=1 for new events and migration-safe normalization/defaults for legacy rows.`
- `[TERM][2026-02-27][MARKER_TEST_T3] Added backward compatibility tests (legacy no-schema events + mixed JSONL rebuild).`
- `[ARCH][2026-02-27][CONFIRM] schema_version=1 approved; packaged strategy stays python-sidecar transitional with required migration task before final release.`
- `[TERM][2026-02-27][RISK] Packaged python-sidecar dependency marked controlled; migration moved to WP-T T4.`
- `[TERM][2026-02-27][MARKER_AUDIT_T4] Audited sidecar surface: runtime rebuild + npm scripts still depend on python3/build_engram_profile.py (4/4 matched).`
- `[TERM][2026-02-27][MARKER_IMPL_T4] Added migration task-map and automated sidecar dependency audit/checklist generation (no runtime behavior change).`
- `[TERM][2026-02-27][MARKER_TEST_T4] Added readiness test for audit/checklist generation; npm test/build/verify green.`
- `[TERM][2026-02-28Txx:xx:xxZ][MARKER_AUDIT_B3] Pulse_spectral telemetry ingestion absent; no reports existed.`
- `[TERM][2026-02-28Txx:xx:xxZ][MARKER_IMPL_B3] Added ingest_spectral_telemetry.py & npm spectral:ingest command to produce md/csv stats for the JSONL stream without touching inference.`
- `[TERM][2026-02-28Txx:xx:xxZ][MARKER_TEST_B3] Added vitest/JavaScript tests for spectral ingestion + executed npm run quality:gate (test/build/verify/bench) — all pass.`
- `[TERM][2026-02-27][MARKER_AUDIT_B1] Spectral telemetry existed in teletype only; no durable JSONL persistence path/command.`
- `[TERM][2026-02-27][MARKER_IMPL_B1] Added spectral telemetry event builders, Tauri append command, and App persistence hooks for BPM/KEY/SCALE_TOP3 events.`
- `[TERM][2026-02-27][MARKER_TEST_B1] Added spectral telemetry tests + Rust JSONL append/path tests; suite green.`
- `[TERM][2026-02-27][MARKER_AUDIT_B2] One-shot quality gate command/report with single exit code was missing.`
- `[TERM][2026-02-27][MARKER_IMPL_B2] Added scripts/run_quality_gate.py + npm script quality:gate writing md/csv summary reports.`
- `[TERM][2026-02-27][MARKER_TEST_B2] Added quality gate command tests (pass/fail exit code) and executed full quality:gate successfully.`
- `[TERM][2026-02-28T15:24:45Z][MARKER_AUDIT_C1] Audited PerformanceView/App split: performance used hidden video + skeleton canvas, but had no explicit UI v3/v2 fallback mode contract.`
- `[TERM][2026-02-28T15:24:45Z][MARKER_IMPL_C1] Implemented explicit performance UI variants (default v3 + v2 fallback) in UI layer only; v3 keeps only skeleton overlay on stage and moves tracking video offscreen; Dev Panel/back-end contracts untouched.`
- `[TERM][2026-02-28T15:24:45Z][MARKER_TEST_C1] Added performance_view_modes test coverage for v3/v2 rendering paths; targeted vitest pass confirmed.`
- `[TERM][2026-02-28T15:24:45Z][MARKER_AUDIT_C2] Audited performance UI: no vertical note matrix and no explicit active note hit visualization existed.`
- `[TERM][2026-02-28T15:24:45Z][MARKER_IMPL_C2] Added VerticalNoteMatrix (12 note strips, Camelot-synced palette) and wired active note highlight/pulse from currentNoteName in PerformanceView v3.`
- `[TERM][2026-02-28T15:24:45Z][MARKER_TEST_C2] Added vertical_note_matrix test coverage (12 strips + active highlight), full npm test/build + JEPA artifact verify all green.`

## 5) MCP / Coordination Channel
- If using VETKA MCP/chat rooms: create room `pulse-implementation-war-room`.
- Minimum sections in room pin:
  - `Current Marker`
  - `Active Blockers`
  - `Today Commands`
  - `Next 3 Tasks`

Fallback if MCP room unavailable:
- Use this file as single source of coordination truth.

## 6) Mandatory Commands Before Handoff
- `npm test`
- `npm run build`
- `python3 scripts/verify_jepa_artifacts.py`
- bench command for changed area (example: `npm run bench:scale:ab:offline`)
- `[TERM][2026-02-28Txx:xx:xxZ][MARKER_AUDIT_B3] Pulse spectral telemetry existed only as teletype events and had no ingestion workflow.`
- `[TERM][2026-02-28Txx:xx:xxZ][MARKER_IMPL_B3] Added ingest_spectral_telemetry.py, md/csv reporters, command + tests, and metadata docs; no inference change.`
- `[TERM][2026-02-28Txx:xx:xxZ][MARKER_TEST_B3] Test aggregator + `npm run spectral:ingest` + `npm run quality:gate` all pass (quality gate includes test/build/verify/bench).`
