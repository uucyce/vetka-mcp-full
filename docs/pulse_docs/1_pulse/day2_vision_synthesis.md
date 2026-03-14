# Pulse — День 2: Vision + Synthesis ✅ (Updated)

**Date:** 2026-02-22  
**Status:** ✅ Complete + Tests Added

## Выполнено

### 2.1 MediaPipe Hands Integration ✅
- Установлены `@mediapipe/hands`, `@mediapipe/camera_utils`, `@mediapipe/drawing_utils`
- Компонент `HandTracker` в `src/vision/HandTracker.ts`
- Рендеринг видео на canvas + оверлей скелета рук

### 2.2 Gesture Mapping Engine ✅
- **EMA Smoothing** (factor = 0.3)
- Left Hand Y → Pitch
- Right Hand Pinch → Volume/Gate
- Left Hand X → Filter Cutoff

### 2.3 Simulation Mode ✅ (NEW!)
- Кнопка "Simulation Mode" для тестирования без камеры
- Sliders для ручного управления:
  - Pitch (Y): 0.0 - 1.0
  - Filter (X): 0.0 - 1.0
  - Pinch ON/OFF кнопка
- Позволяет тестировать звук без реальной камеры

### 2.4 Tests ✅ (NEW!)
- 13 тестов проходят успешно:
  - `synth.test.ts` - Frequency calculation, filter cutoff, EMA smoothing
  - `handtracker.test.ts` - Pinch detection, coordinate parsing
  - `integration.test.ts` - Gesture → Synth mapping

## Acceptance Criteria

| AC | Status |
|---|---|
| Скелет рук поверх видео | ✅ |
| EMA smoothing (0.3) | ✅ |
| Right Y → Frequency | ✅ |
| Right pinch → Gate | ✅ |
| Left X → Filter Cutoff | ✅ |
| Simulation Mode для тестирования | ✅ |
| Unit tests | ✅ 13/13 passed |

## Как Тестировать

### Без камеры (Simulation Mode):
1. Запустить Pulse.app
2. Нажать "Simulation Mode"
3. Использовать слайдеры для управления звуком
4. Нажимать ON/OFF для включения/выключения звука

### С камерой:
1. Нажать "Start Camera"
2. Показать руку в камеру
3. Right hand pinch → звук включается
4. Двигать руку вверх/вниз → меняется pitch

## Build Output

```
Pulse.app         → target/release/bundle/macos/Pulse.app
Pulse_0.1.0.dmg   → target/release/bundle/dmg/
```

## Следующий Шаг

**День 3:** Scale Quantizer — добавить маппинг на ноты выбранной гаммы (Camelot Wheel)

---

*Pulse — Gesture Synthesizer*
