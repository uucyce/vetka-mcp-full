MARKER_163B1.MYCO.PERSONA.VOICE.BASELINE.REPORT.V1
LAYER: L4
DOMAIN: VOICE|PERSONA|UI|TTS
STATUS: IMPL_NARROW
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_163B1_MYCO_PERSONA_VOICE_BASELINE_REPORT_2026-03-08.md
LAST_VERIFIED: 2026-03-08

# PHASE_163B1_MYCO_PERSONA_VOICE_BASELINE_REPORT_2026-03-08

Status: IMPL NARROW complete, VERIFY TEST done for narrow scope
Owner: VETKA-JARVIS MYCO voice/runtime track
Parallel owner: Phase 163.A deterministic MYCO guide track

## MARKER_163B1.P0.SCOPE.V1
163.B1 covers only the baseline MYCO persona/voice runtime package:
- set MYCO character voice baseline to local `espeak-ng` preset `chip`
- keep `edge` only as future selectable/reference option
- disable noisy filler behavior for MYCO help path
- align runtime defaults with MYCO character direction
- reuse already prepared MYCO UI assets instead of raw source icons

## MARKER_163B1.P1.CHANGES.V1
Implemented changes:

1. Backend runtime defaults shifted to MYCO chip baseline.
- file: `src/api/handlers/jarvis_handler.py`
- added `myco_chip_ru` voice profile
- default voice profile changed from `vetka_ru_female` to `myco_chip_ru`
- strict `edge` lock default disabled for MYCO experiment path

2. Shell/runtime bootstrap defaults updated.
- file: `run.sh`
- default TTS provider: `espeak`
- fallback provider: `espeak`
- baseline preset: `chip`
- baseline tuning: `rate=190`, `pitch=96`, `amplitude=140`
- plan-b filler audio disabled by default for MYCO helper path

3. MYCO guide lane uses ready-made persona assets.
- file: `client/src/components/myco/MycoGuideLane.tsx`
- uses prepared MCC-derived assets from `client/src/assets/myco/`
- warning tone -> `myco_idle_question.png`
- regular/action tone -> `myco_ready_smile.png`
- visible label kept compact as `MYCO`

## MARKER_163B1.P2.ASSET_POLICY.V1
Asset policy for MYCO in VETKA:
- do not reprocess raw icon source packages if ready-made runtime assets already exist
- prefer prepared assets from `client/src/assets/myco/`
- raw source pack in `icons/myco_logos/png_alpha/stream` remains source material only

## MARKER_163B1.P3.VOICE_DECISION.V1
Voice decision for this narrow phase:
- primary baseline: `espeak-ng` preset `chip`
- reason: speed + character fit are prioritized over naturalism
- `edge` remains allowed only as future manual/selectable option
- `edge` is not an automatic fallback path for this MYCO baseline

## MARKER_163B1.P4.BENCHMARK_NOTES.V1
Observed local synthesis timings for short sample text:
- `c3po` preset: about `70 ms`
- `chip` preset, tuned: about `19-21 ms`
- `clean` preset: about `18 ms`

Interpretation:
- `chip` is near-best in latency while providing stronger character shape than `clean`
- this makes `chip` the preferred MYCO baseline candidate

## MARKER_163B1.P5.JEPA_POSITION.V1
JEPA is unchanged in 163.B1.
Rule for this phase:
- verify-only
- no redesign
- no forced activation hacks

## MARKER_163B1.P6.DEPENDENCY_ON_163A.V1
163.A and 163.B1 must stay separate:
- 163.A owns deterministic proactive hints and browser-verified UI behavior
- 163.B1 owns spoken/runtime persona baseline only

Handoff implication:
- `MycoGuideLane` visual persona can coexist with 163.A logic
- deterministic hint quality remains owned by the 163.A track

## MARKER_163B1.P7.VERIFICATION.V1
Verification completed for narrow scope:
- `python -m py_compile src/api/handlers/jarvis_handler.py` -> OK
- `pytest -q tests/test_phase163a_mode_a_contract.py` -> 4 passed

Note:
- pytest here verifies that the existing 163.A contract still stands after the narrow persona/voice baseline changes
- it is not a full spoken-audio end-to-end test

## MARKER_163B1.P8.KNOWN_GAPS.V1
Open gaps after 163.B1:
- no dedicated audio e2e assertion for MYCO chip runtime yet
- chunk policy (`chunk2` vs `chunk2+chunk3`) still under evaluation
- spoken MYCO answer contract is not yet tightened enough; that belongs to next runtime step
- PULSE/Transformant remains preparation only, not active MYCO voice processing
- current bottom-left MYCO card should be treated as bridge UI, not final MYCO surface
- final canonical MYCO surface should align with the unified search lane when the field is empty

## MARKER_163B1.P9.COLLEAGUE_HANDOFF.V1
Recommended acknowledgement to the 163.A owner:

`Принято. 163.A browser verify считается валидным базовым контрактом. Не расширяй пока long-tail дальше; следующий честный шаг — добить стабильный artifact/external-ingest fixture и зафиксировать его как отдельный verify slice. Мы со своей стороны держим 163.B отдельно: persona/voice/runtime, без размывания deterministic слоя.`

## MARKER_163B1.P10.CROSS_LINKS.V1
See also:
- `docs/163_ph_myco_VETKA_help/PHASE_163B_MYCO_VOICE_RUNTIME_SHORT_REPORT_2026-03-08.md`
- `docs/163_ph_myco_VETKA_help/PHASE_163A_MYCO_MODE_A_VERIFY_REPORT_2026-03-08.md`
- `docs/163_ph_myco_VETKA_help/MYCO_VETKA_MASTER_INDEX_V1.md`
