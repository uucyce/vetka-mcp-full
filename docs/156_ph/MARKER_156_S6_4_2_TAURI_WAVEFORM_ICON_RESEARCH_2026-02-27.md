# MARKER_156.S6_4_2_TAURI_WAVEFORM_ICON_RESEARCH

Дата: 2026-02-27  
Статус: recon shortlist

## Цель
- Реальная визуализация записи (не fake bars)
- Icon-only voice controls (white icons)
- Совместимость с Tauri/WebView + минимальный latency overhead

## Варианты waveform (recording/live)

1. `WebAudio + AnalyserNode` (native browser API)
- Плюсы: ноль внешних зависимостей, полный контроль, низкий overhead.
- Минусы: нужно вручную делать smoothing/normalization/decimation.
- Рекомендация: базовый production вариант для live recording.

2. `wavesurfer.js` (+ Record plugin)
- Плюсы: готовый UX для playback + wave, стабильный ecosystem.
- Минусы: избыточно для простого live meter, выше bundle size.
- Рекомендация: использовать для message replay waveform, если нужен богатый player.

3. `@react-audio-visualize` / похожие lightweight wrappers
- Плюсы: быстрое подключение в React.
- Минусы: меньше контроля, часто уступает в перфомансе кастомному WebAudio.
- Рекомендация: не основной вариант.

## Варианты иконок

1. `lucide-react` (уже в проекте)
- Плюсы: единый стиль, SVG, легко сделать icon-only white theme.
- Минусы: нужно доработать hover/active tokens.
- Рекомендация: основной вариант без миграции библиотеки.

2. `Iconoir` / `Phosphor`
- Плюсы: богатый набор.
- Минусы: лишняя миграция и визуальный дрейф.
- Рекомендация: не требуется сейчас.

## Tauri-специфика
- Для waveform и icon controls не нужен отдельный Rust plugin: достаточно WebAudio/Canvas/SVG в WebView.
- Критично:
  - не делать heavy redraw > 60fps,
  - decimate waveform до 40-80 точек для bubble,
  - хранить normalized waveform в metadata для replay после reload.

## Decision
1. Live recording wave: `WebAudio + AnalyserNode + RMS/peak smoothing`.
2. Replay wave: данные из backend metadata (реальные PCM-derived значения).
3. Controls: `lucide-react`, icon-only, white palette, text labels убрать.

## Интеграционный чеклист (S6.4.2 → S6.4.3)
- [ ] Убрать fake waveform fallback в `MessageBubble`.
- [ ] Привести recorder wave к normalized контракту (0..1, 64 points).
- [ ] Добавить visual state: recording/paused/sending/error иконками.
- [ ] Проверить mobile/desktop DPI и FPS.
