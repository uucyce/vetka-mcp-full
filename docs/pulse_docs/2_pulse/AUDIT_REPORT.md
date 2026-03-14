# Pulse — AUDIT REPORT (Real Codebase)

**Date:** 2026-02-24  
**App path audited:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/pulse`  
**Audit mode:** static code audit + existing test run

## 0) Update (2026-02-24 evening) — fast implementation check
- `ARP patterns` expanded in code: now supports `up/down/upDown/downUp/random/randomOnce/randomWalk/ordered/chord` in [`pulse/src/audio/Arpeggiator.ts`](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/pulse/src/audio/Arpeggiator.ts).
- `ARP auto-selection` is now heuristic-driven by note count + BPM + scale family in [`pulse/src/App.tsx`](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/pulse/src/App.tsx).
- `Genre -> VST suggestions` moved to open-source oriented names (`Surge XT`, `Helm`, `Dexed`, etc.) in [`pulse/src/music/GenreDetector.ts`](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/pulse/src/music/GenreDetector.ts).
- `VST rack dedupe / non-playing FX issue` fixed: VST scanner now filters effect-only entries like `Surge XT Effects`, so rack focuses on playable synths in [`pulse/src-tauri/src/lib.rs`](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/pulse/src-tauri/src/lib.rs).
- `Manual internal sound switching` confirmed in UI (`Internal Rack: Prev Sound / Next Sound / Hold`) and wired to synth presets in [`pulse/src/audio/SynthEngine.ts`](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/pulse/src/audio/SynthEngine.ts) + [`pulse/src/App.tsx`](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/pulse/src/App.tsx).
- `UI duplicate confusion` reduced: external MIDI/VST controls are hidden while `Audio Layer = Internal`, so internal sound switching is now explicit.

## 1) Что подтверждено по коду
- React + TypeScript + Tauri структура есть и рабочая.
- Hand tracking (MediaPipe), synth, key/BPM анализ, Camelot wheel и quantizer подключены.
- Базовый `Scale -> Genre -> VST` UI уже отображается (`App.tsx` + `GenreDetector.ts`).
- Тесты проходят: `65/65` (`npm test` в `pulse`).

## 2) Findings (по приоритету)

### MARKER_PULSE_AUDIT_P0_001 — Key event flood
**Files:** `pulse/src/audio/SmartAudioEngine.ts:155-162`  
`onKey` может вызываться почти каждый цикл после стабилизации, без hard throttle.

### MARKER_PULSE_AUDIT_P0_002 — Beat sync logic partially dead
**Files:** `pulse/src/App.tsx:69`, `pulse/src/App.tsx:355`, `pulse/src/App.tsx:398`  
`isBPMTrackingRef` не синхронизируется, ветки beat-sync не работают как задумано.

### MARKER_PULSE_AUDIT_P0_003 — Invalid state model for scale
**Files:** `pulse/src/App.tsx:31`, `pulse/src/App.tsx:375-401`, `pulse/src/music/theory.ts:183-191`  
В одном поле смешаны Camelot key и name scale, из-за этого периодически ломается привязка к `CAMELOT_WHEEL`.

### MARKER_PULSE_AUDIT_P0_004 — Arpeggiator lifecycle bug
**Files:** `pulse/src/audio/Arpeggiator.ts:60-90`  
`start()` создаёт новый `Tone.Loop` без гарантированного cleanup старого перед перезапуском.

### MARKER_PULSE_AUDIT_P1_005 — Arp pattern incomplete
**Files:** `pulse/src/audio/Arpeggiator.ts:3`, `73-78`  
`updown` объявлен в типе, но не реализован.

### MARKER_PULSE_AUDIT_P1_006 — Base note ignored in arp
**Files:** `pulse/src/audio/Arpeggiator.ts:42-43`, `pulse/src/App.tsx:149-151`  
`setBaseNote()` пустой, хотя App передаёт base note.

### MARKER_PULSE_AUDIT_P1_007 — Harsh gesture switching
**Files:** `pulse/src/vision/HandTracker.ts:107-112`, `pulse/src/App.tsx:104-111`  
Нет hysteresis/debounce для pinch и Y-mode границ.

### MARKER_PULSE_AUDIT_P1_008 — BPM robustness gap
**Files:** `pulse/src/audio/SmartAudioEngine.ts:111-133`, `262-280`  
На живом микрофоне текущий onset-подход легко даёт ложные пики BPM.

### MARKER_PULSE_AUDIT_P2_009 — Excessive realtime logging
**Files:** `pulse/src/App.tsx:83`, `102`, `142`, `366+`  
Плотные логи в горячем цикле ухудшают UX/latency на слабых машинах.

### MARKER_PULSE_AUDIT_P2_010 — Test gap for stability
**Files:** `pulse/src/__tests__/*`  
Нет regression-тестов на rate-limit key events и consistency состояния scale/camelot.

## 3) Реалистичный roadmap реализации (4 спринта)

### Sprint 0 (1 день) — Stabilization Hotfix
1. Разделить `selectedCamelotKey` и `selectedScaleName`.
2. Починить `isBPMTrackingRef` или убрать ref-модель.
3. Ввести `lastEmittedKey + minEmitIntervalMs` в `SmartAudioEngine`.
4. Добавить feature-flag `PULSE_STABILITY_V1`.

### Sprint 1 (1-2 дня) — Smart Refinement
1. Hysteresis для pinch/mode.
2. Freeze/hold политики: `minKeyHoldMs`, `minScaleHoldMs`.
3. Refinement через окно N кадров + confidence gating.
4. Тесты: стабильность key/scale под шумом.

### Sprint 2 (2 дня) — Intelligent Arpeggio
1. Починить lifecycle `Arpeggiator` (single loop ownership).
2. Реализовать `updown`, `pingpong`, `random-no-repeat`.
3. Реализовать `setBaseNote` и контекстную генерацию нот вокруг base note.
4. Мягкие envelopes/velocity curves для "не резкого" арпа.

### Sprint 3 (2-3 дня) — Genre/VST + расширение для VETKA
1. Перевести `GenreDetector` на JSON-конфиг матрицы с версиями.
2. Ввести confidence-aware suggestion (не только top-1).
3. Подготовить адаптер-контракт для будущей интеграции в VETKA (`PulseEngineAdapter`).
4. Интеграционные тесты API-контракта (standalone и embedded mode).

## 4) Что запросить в исследования (недостающее)

### RESEARCH_REQ_001 — Live Key Detection for noisy mic
Нужны сравнения подходов для realtime browser: chroma+KS vs HPCP vs lightweight ML, с latency/CPU метриками и рекомендацией порогов confidence/hysteresis.

### RESEARCH_REQ_002 — Realtime BPM robustness
Нужна практичная схема onset extraction для живого входа (bandpass + spectral flux + median/MAD), плюс рецепты против half/double-time drift.

### RESEARCH_REQ_003 — Arp musicality model
Нужны правила выбора паттерна по gesture + scale context (legato->arp morph), включая anti-chaos ограничения и smoothing-функции.

### RESEARCH_REQ_004 — Browser-safe synth expansion
Нужен shortlist synth-движков/архитектур (WebAudio/Tone stack) с оценкой CPU, polyphony и качества для Tauri desktop.

### RESEARCH_REQ_005 — Scale→Genre→VST dataset governance
Нужен формат матрицы с confidence, provenance и механизмом обновления без перекомпиляции (JSON schema + versioning).

## 5) Порядок внедрения (рекомендовано)
1. Сначала стабилизация state/event модели (Sprint 0).
2. Потом муз-логика и UX-гладкость (Sprint 1-2).
3. Потом расширения genre/vst и интеграционный слой в VETKA (Sprint 3).

## 6) Статус
**Audit complete.**  
Документ `SCALE_STABILITY_AUDIT.md` содержит детальные маркеры по стабилизации scale/key.
