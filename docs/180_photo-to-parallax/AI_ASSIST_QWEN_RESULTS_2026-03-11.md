# AI Assist Qwen Results

Date: 2026-03-11

## Goal

Подключить локальный `qwen2.5vl:3b` как первый `AI Assist` semantic suggester для sandbox, не делая его обязательной частью deterministic base pipeline.

## Implemented

- Добавлен runner:
  - `scripts/photo_parallax_semantic_group_suggest.py`
  - `scripts/photo_parallax_semantic_group_suggest.sh`
- Источник модели:
  - локальный `ollama`
  - модель `qwen2.5vl:3b`
- Runner анализирует sample image и color hint overlay, затем сохраняет:
  - `photo_parallax_playground/public/ai_assist_suggestions/<sample>.json`
  - `photo_parallax_playground/public/ai_assist_suggestions/manifest.json`
  - mirror-копии в `photo_parallax_playground/output/ai_assist_suggestions`
- Введён sanitizing gate:
  - reject full-frame boxes
  - reject corner-anchored oversized boxes
  - reject midground boxes, которые фактически дублируют foreground
  - fallback к focus-derived box при слабой геометрии ответа
- Sandbox UI теперь умеет:
  - автоматически подгружать suggestion JSON для текущего sample
  - показывать AI overlay
  - применять accepted AI groups в `Merge Groups`
- Browser API расширен:
  - `toggleAiAssistOverlay()`
  - `applyAiAssistSuggestion()`

## Batch result

Текущий batch summary по `qwen2.5vl:3b`:

- `cassette-closeup`: `confidence 0.58`
  - raw semantics полезна
  - geometry rejected
  - used `focus fallback`
- `keyboard-hands`: `confidence 0.64`
  - raw semantics partially useful
  - foreground geometry rejected как corner-anchored
  - used `focus fallback` + `midground fallback`
- `hover-politsia`: `confidence 0.64`
  - semantics noisy
  - geometry largely rejected
  - used `focus fallback` + `midground fallback`
- `drone-portrait`: `confidence 0.86`
  - best current case
  - accepted boxes survived sanitation

## Conclusion

`Qwen2.5-VL` уже полезен как semantic suggester, но пока не как box locator. Правильная роль на текущем этапе:

- semantic hint source
- candidate generator
- compare/accept layer for Manual Pro

Неправильная роль на текущем этапе:

- direct mask source
- auto-final layer assignment without gate

## Verification

- `python3 -m py_compile scripts/photo_parallax_semantic_group_suggest.py`
- `./scripts/photo_parallax_semantic_group_suggest.sh`
- `npm test`
- `npm run build`
- `./scripts/photo_parallax_review.sh`

Artifacts:

- `photo_parallax_playground/public/ai_assist_suggestions/manifest.json`
- `photo_parallax_playground/output/ai_assist_suggestions/manifest.json`
- `photo_parallax_playground/output/review/latest-parallax-review.png`
- `photo_parallax_playground/output/review/latest-parallax-review.json`

## Next step

Следующий шаг не в более тяжёлой модели, а в product gate:

1. Compare `manual merge groups` vs `AI suggested groups`.
2. Ввести `accept / reject / blend` workflow.
3. Только потом думать о richer semantic contract или другой vision model.
