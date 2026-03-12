# MARKER_157_6_FAST_C3PO_TTS_ROADMAP_2026-03-07

## Context
Этот roadmap продолжает Phase 157 (Jarvis/VETKA voice stage-machine) и фиксирует отдельную ветку по голосу:
- цель: быстрый, узнаваемый, стабильный голос VETKA в стиле sci-fi robot ("C-3PO-like"),
- приоритет: скорость и консистентность (один голос),
- память: строго ENGRAM/STM/CAM-first, без обхода ENGRAM.

## Current Baseline (по последним trace)
- `first_response_ms`: ~1.4s-3.4s (хорошо/средне).
- `total_turn_ms`: до ~25-26s (плохо, stage3/4 иногда затягивает).
- `tts_provider`: `fast_tts` (Edge), `tts_duration_ms` часто 1.2-4.0s.
- STT нестабилен на отдельных ходах (`stt_retry`), confidence падает до ~0.2-0.3.
- Языковой drift (RU -> EN) встречается.

## Product Goal
Сделать голос VETKA:
1. Быстрым (реактивным для диалога),
2. Консистентным (один голос на сессию),
3. Узнаваемым (sci-fi robotic style),
4. Поддерживающим RU/EN,
5. Не разрывающим ENGRAM/STM memory contract.

## Architecture Decision
### Decision A (now): Dual-provider with stable default
- Default: Edge-TTS (уже быстрый и доступный).
- Backup/experiment path: eSpeak-ng (local robotic) для ultra-fast fallback и C-3PO mode.

### Decision B (memory contract): ENGRAM-first only
- Language/style preferences и user identity идут через ENGRAM keys.
- Никаких "independent memory bypass" для имени/предпочтений.

### Decision C (voice routing)
- Voice-profile routing на backend (сделано), позже вывести в UI.
- На сессию фиксируется один профиль, без random переключений.

## Phase 157.6 Workstream

### 157.6.1 Voice Profile Contract (Backend complete + hardening)
Status: in_progress

Scope:
- Закрепить профиль голоса для всех TTS-путей в рамках сессии:
  - main response,
  - plan-b filler,
  - fallback TTS on provider error.
- Добавить trace-поля:
  - `voice_profile`,
  - `tts_voice_engine` (`edge` / `espeak`),
  - `filler_audio_emitted`.

Acceptance:
- В рамках одного разговора не происходит незапланированного прыжка между male/female.

### 157.6.2 eSpeak-ng C-3PO Fast Path (new)
Status: planned

Scope:
- Интегрировать `espeak-ng` backend как опциональный TTS provider.
- Добавить пресет(ы):
  - `c3po_ru` (robotic RU),
  - `c3po_en` (robotic EN).
- Формат выдачи: WAV/PCM -> `jarvis_audio`.
- Ограничить pipeline так, чтобы eSpeak мог работать как:
  - fallback при Edge 503/timeout,
  - force mode для bench (`JARVIS_TTS_PROVIDER=espeak`).

Config flags (proposed):
- `JARVIS_TTS_PROVIDER=edge|espeak|auto`
- `JARVIS_TTS_FALLBACK_PROVIDER=espeak`
- `JARVIS_ESPEAK_VOICE_RU=ru`
- `JARVIS_ESPEAK_VOICE_EN=en`
- `JARVIS_ESPEAK_PRESET=c3po`
- `JARVIS_ESPEAK_RATE=155`
- `JARVIS_ESPEAK_PITCH=70`
- `JARVIS_ESPEAK_AMPLITUDE=130`

Acceptance:
- `ttfa_audio` < 900ms на коротких репликах в режиме `espeak`.
- При Edge 503 автоматически есть слышимый fallback без тишины.

### 157.6.3 C-3PO Preset Tuning
Status: planned

Scope:
- Собрать 3 пресета и сравнить:
  - `c3po_clean` (легкий robotic),
  - `c3po_classic` (более metallic),
  - `c3po_chip` (8-bit/chiptune-like).
- Для Edge path сделать "style prompt constraints" (без hard rewrite текста).

Bench metrics:
- MOS-like internal score (subjective team rating 1-5),
- intelligibility RU/EN,
- `tts_duration_ms`,
- `ttfa_audio`.

Acceptance:
- Выбран ровно 1 дефолтный preset VETKA voice.

### 157.6.3b JEPA/PULSE Prosody Layer (new)
Status: planned

Scope:
- Подключить JEPA/PULSE как надстройку управления ритмом/интонацией, а не генератор текста.
- Для `espeak-ng` и `edge` path применять lightweight prosody hints:
  - паузы,
  - акцентные ударения,
  - темп фразы,
  - контур эмоции (calm/alert/excited/uncertain).
- Включать только если не ухудшает `ttfa_audio`.

Config flags (proposed):
- `JARVIS_PROSODY_ENGINE=none|pulse|jepa_pulse`
- `JARVIS_PROSODY_BUDGET_MS=120`
- `JARVIS_PROSODY_STYLE=neutral|c3po|chip`

Acceptance:
- С prosody-layer сохраняется p50 `ttfa_audio` <= 1.0s.
- Рост разборчивости (RU/EN) при равной latency или лучше.

### 157.6.4 ENGRAM Language/Identity Reliability
Status: in_progress

Scope:
- Зафиксировать schema keys в ENGRAM:
  - `communication_style.preferred_language`,
  - `communication_style.last_assistant_language`,
  - `communication_style.prefers_russian`,
  - `communication_style.user_name`.
- Убрать invalid-key warnings полностью.
- Прописать read/update policy для voice turn lifecycle.

Acceptance:
- Нет warning `Invalid key` в runtime.
- На вопрос про имя и язык ответ согласован с ENGRAM.

### 157.6.5 Stage Latency Guardrails
Status: in_progress

Scope:
- Жесткие timeout guardrails для stage2/3/4.
- Если stage3/4 не успевают, отдавать stage2 + optional follow-up.
- Не допускать `total_turn_ms` > 10s в типичном вопросе.

Acceptance:
- p95 `total_turn_ms` <= 8s на short/medium prompts.
- Нет 20-30s хвостов из-за долгих refinement stages.

### 157.6.6 VETKA Sing Prototype (optional R&D)
Status: planned

Scope:
- Добавить экспериментальный режим `sing` (не для дефолтного диалога).
- Триггер командами: `спой ...` / `sing ...`.
- Pipeline:
  - text intent -> melody/rhythm template (PULSE),
  - render via `espeak-ng` robotic voice,
  - optional post-fx (chip/echo) в offline-pass.

Acceptance:
- Не влияет на latency и стабильность обычного voice-dialog.
- Артефакты тестов сохраняются в `data/audio/sing_trials/`.

### 157.6.7 Personal RAG for VETKA Voice (MYCO-style)
Status: planned

Scope:
- Сделать персональный обновляемый RAG для VETKA-диалога (по аналогии с MYCO в MYCELIUM).
- Источники:
  - ENGRAM (долгосрочные предпочтения, стиль, user facts),
  - STM/session_summary (локальная краткосрочная память),
  - viewport + pinned files + open chat context,
  - curated instruction docs \"как пользоваться VETKA\".
- Режим обновления:
  - инкрементальная индексация по изменениям файлов,
  - приоритет свежих инструкций и личных предпочтений,
  - ограничение контекста по бюджету токенов (ELISION-first).

Contracts:
- Voice path не должен обходить ENGRAM.
- RAG facts включаются как явные блоки:
  - `identity_facts`
  - `usage_instructions`
  - `viewport_facts`
  - `pinned_facts`
- Каждый блок имеет max-budget и score threshold.

Acceptance:
- Ответы на \"что я вижу\" и \"как пользоваться\" содержат конкретные факты, а не общие фразы.
- На 10-turn сессии нет деградации релевантности.
- p95 `first_response_ms` не деградирует >15% относительно baseline edge-path.

## Test Matrix (required)

### A. Voice Engine Bench
1. `edge` only
2. `espeak` only
3. `auto` (edge + espeak fallback)
4. `espeak + jepa_pulse` (prosody on)

Metrics:
- `first_response_ms`
- `ttfa_audio`
- `tts_duration_ms`
- `total_turn_ms`
- failure rate (TTS errors / silence incidents)
- style consistency score (single-voice continuity)

### B. Memory/Context Correctness
Scenarios:
1. "Как меня зовут?"
2. "На что я сейчас смотрю?"
3. "Ответь на русском"
4. "Switch to English"
5. "Как сделать X в VETKA?" (проверка personal RAG instruction layer)

Checks:
- language consistency
- identity recall from ENGRAM

### 157.6.8 MBROLA Feasibility (macOS M4)
Status: in_progress

Findings:
- MBROLA binary can be compiled locally on macOS.
- MBROLA voice databases can be downloaded (`en1/us1/us2`) and discovered by `espeak-ng`.
- `espeak-ng` MBROLA bridge (`mbrowrap`) currently fails on macOS with `/proc is unaccessible`, causing `mb-*` voices to fail.

Decision:
- Keep `Edge` as primary provider.
- Keep MBROLA as experimental path only.
- Add safe runtime fallback from `mb-*` voice to plain `espeak` voice to avoid silent turns.

Acceptance:
- Selecting MBROLA profile never causes silence/crash.
- Voice turn always returns audio (either MBROLA if available or auto-fallback `espeak`).
- viewport mention relevance (not generic)
- instruction-grounded response quality (with citations/path mentions where applicable)

### C. Long Dialogue Stability
- 10-turn continuous voice session.
- Проверить рост latency и деградацию качества.
- Проверить что voice profile не прыгает.

## Observability Additions
Добавить в trace payload:
- `voice_profile`
- `tts_engine`
- `filler_audio_emitted`
- `stage_timeout_flags`
- `engram_keys_applied`
- `prosody_engine`
- `prosody_budget_ms`
- `prosody_applied`

## Risks
1. eSpeak качество RU может быть слишком synthetic.
Mitigation: keep Edge as default, eSpeak as fallback/robot mode.

2. Stage3/4 still too slow on local models.
Mitigation: stricter timeouts + deep-query gate.

3. STT low confidence blocks turns.
Mitigation: transcript hint priority + tuned thresholds.

## Go / No-Go Criteria
Go to default C-3PO mode only if:
- `ttfa_audio` p50 <= 1.0s
- `total_turn_ms` p95 <= 8.0s
- language drift < 5%
- no-session voice switching incidents in 10-turn runs

Otherwise:
- keep Edge default,
- expose C-3PO as optional profile until quality passes gate.

## Implementation Order
1. 157.6.1 hardening + trace fields
2. 157.6.2 eSpeak provider integration
3. 157.6.3 preset tuning + bench
4. 157.6.3b JEPA/PULSE prosody layer bench
5. 157.6.4 ENGRAM reliability closure
6. 157.6.5 stage latency guardrail finalization
7. 157.6.7 personal RAG (MYCO-style) implementation + eval
8. 157.6.6 sing prototype (optional)

## Notes
- Naming for user remains `VETKA`.
- `Jarvis` is internal codename only.
- UI voice/model chooser deferred by design; backend profiles must be stable first.
