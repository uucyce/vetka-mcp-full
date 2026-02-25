# Pulse — SCALE STABILITY AUDIT (Code-Based)

**Date:** 2026-02-24  
**Scope:** real code audit in `pulse/src` (no assumptions from old notes)

## Status update (2026-02-24 evening)
- Scale drift is reduced by stronger gating already present in `App.tsx`, but fully reliable niche-scale detection is still **not solved**.
- Current practical status: BPM became more stable, while scale can still collapse to sticky defaults in noisy sessions.
- Next high-impact implementation: confidence window with temporal decay + penalties for broad/default scales (`Chromatic`, `Ionian`, `Spanish`) when evidence is weak.

## MARKER_PULSE_STAB_001 (P0): Key/Scale event flood from SmartAudioEngine
**Evidence:** `pulse/src/audio/SmartAudioEngine.ts:155-162`  
После первого срабатывания `frameCount` принудительно ставится `STABLE_FRAMES + 1`, а условие остаётся `>= STABLE_FRAMES`, из-за чего `onKey` летит почти каждый цикл детектора.

**Impact:** дрожание scale/genre UI, лишние пересчёты, нестабильное поведение при игре.

**Fix:**
1. Ввести `lastEmittedKey` + `minEmitIntervalMs` (например, 800-1500мс).
2. Эмитить только на `key change` ИЛИ на существенный рост confidence.
3. Сброс `frameCount` после эмита, а не принудительный `+1`.

---

## MARKER_PULSE_STAB_002 (P0): Broken beat-sync path due to stale refs
**Evidence:** `pulse/src/App.tsx:69`, `pulse/src/App.tsx:355`, `pulse/src/App.tsx:398`  
`isBPMTrackingRef` объявлен, но нигде не синхронизируется с состоянием `setIsBPMTracking(true)`. В результате ветки `if (isBPMTrackingRef.current)` практически не работают.

**Impact:** beat-synced смена ключа не активируется, поведение расходится с UI и ожиданиями.

**Fix:**
1. Добавить `useEffect(() => { isBPMTrackingRef.current = _isBPMTracking; }, [_isBPMTracking])`.
2. Либо убрать ref и использовать единый `analysisStateRef`.

---

## MARKER_PULSE_STAB_003 (P0): Camelot key and scale-name are mixed
**Evidence:** `pulse/src/App.tsx:375-401`  
`selectedScale` используется как Camelot key (`8B`, `9A`), но при refine записывается `refined.name` (`Ionian (Major)`, `Dorian`...). Это ломает доступ к `CAMELOT_WHEEL[selectedScale]` и даёт fallback/скачки.

**Impact:** квантайзер и wheel получают неконсистентное состояние, музыкальная логика дергается.

**Fix:**
1. Разделить состояния: `selectedCamelotKey` и `selectedScaleName`.
2. Добавить mapping `camelot -> scaleName` и обратный safe mapping.
3. Никогда не писать scale name в state Camelot key.

---

## MARKER_PULSE_STAB_004 (P1): No hysteresis for hand pinch/mode switching
**Evidence:** `pulse/src/vision/HandTracker.ts:107-112`, `pulse/src/App.tsx:104-111`  
Pinch threshold фиксированный (`< 0.25`), без deadband/hysteresis; mode по Y-порогам `0.4/0.6` без фильтра переключений.

**Impact:** дребезг between legato/normal/arpeggio, «резкое» ощущение игры.

**Fix:**
1. Порог pinch: `engage < 0.20`, `release > 0.24`.
2. Для mode добавить hysteresis zone + debounce 80-120мс.
3. EMA-сглаживание Y отдельно для mode control.

---

## MARKER_PULSE_STAB_005 (P1): BPM detector is too naive for live mic
**Evidence:** `pulse/src/audio/SmartAudioEngine.ts:111-133`, `262-280`  
Onset строится только на RMS/energy + cooldown 100мс, без bandpass/spectral flux.

**Impact:** BPM прыгает на шуме/гармониках, confidence часто не отражает реальную метрику.

**Fix:**
1. Добавить spectral flux или band-limited onset envelope.
2. Держать rolling median + MAD filtering.
3. Ввести freeze BPM при низкой уверенности.

---

## MARKER_PULSE_STAB_006 (P1): Refine logic is over-biased to minimal scales
**Evidence:** `pulse/src/music/scales_db.ts:280-305`  
Скоринг даёт бонус за меньшее число нот (`sizeBonus`), поэтому система системно уходит в пентатоники/узкие лады даже при неустойчивом наборе нот.

**Impact:** scale «уточняется» не по музыкальному контексту, а по размеру лада.

**Fix:**
1. Ввести penalty за частые смены scale.
2. Добавить temporal memory (N последних окон) до смены scale.
3. Снизить вес `sizeBonus` и учитывать coverage/entropy.

---

## MARKER_PULSE_STAB_007 (P0): Current tests do not guard stability regressions
**Evidence:** `pulse/src/__tests__` (все тесты проходят, но нет сценариев на hysteresis/emit throttling/state consistency).  

**Impact:** баги стабильности легко возвращаются после рефакторинга.

**Fix:**
1. Добавить тесты на event-rate (`onKey` не чаще X/сек).
2. Тест на consistency: `selectedCamelotKey` всегда из `CAMELOT_WHEEL`.
3. Тест на beat-sync queue применяемость при BPM tracking.

---

## Мини-план стабилизации (реально выполнимый)
1. Починить state model (`selectedCamelotKey` vs `selectedScaleName`) и `isBPMTrackingRef`.
2. Ограничить эмит key-events в `SmartAudioEngine`.
3. Добавить hysteresis для pinch/mode и freeze-логику для BPM.
4. Покрыть это интеграционными тестами до новых фич.
