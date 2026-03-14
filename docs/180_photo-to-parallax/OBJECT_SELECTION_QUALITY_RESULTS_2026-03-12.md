# Object Selection Quality Results

Дата: `2026-03-12`

## Зачем добавлен этот этап

До этого sandbox хорошо видел локальные улучшения по краю:

- `edge delta`
- `contour snap`
- `feather cleanup`

Но это не отвечало на главный продуктовый вопрос:

`выделен ли целый смысловой объект как единый слой`

Для этого добавлен отдельный internal scorer:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_object_selection_review.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_object_selection_review.sh`

## Что сравнивается

На каждой сцене оцениваются три варианта маски:

- `before-ai`
- `after-ai`
- `internal-final`

Скоринг смотрит не только на покрытие, но и на object cohesion:

- покрыты ли ключевые target-boxes одного объекта;
- не развалился ли объект на слабые куски;
- не тянет ли маска лишний фон;
- насколько равномерно покрыты части одного объекта.

## Текущий результат

Summary:

- entries: `6`
- winner counts:
  - `before-ai = 6`
- winner decisions:
  - `coherent = 3`
  - `partial = 3`
- `fragmented = 0`
- avg winner score: `4.67553`

Главный вывод:

- текущий `contour snap` полезен для локального cleanup края, но не улучшает `whole object as one layer`;
- на этих сценах лучший вариант по object cohesion сейчас не `after-ai` и не `internal-final`, а именно `before-ai`;
- значит следующий engineering focus должен смещаться с edge cleanup на `object grouping quality`.

## По сценам

### cassette-closeup

- winner: `before-ai`
- decision: `coherent`
- смысл:
  - обе руки и кассета уже попадают в один usable foreground layer;
  - contour cleanup слегка ухудшает coverage, но не решает objectness-проблему.

### keyboard-hands

- winner: `before-ai`
- decision: `partial`
- проблема:
  - объектный слой usable, но есть сильный фоновой spill;
  - `after-ai` и `internal-final` не улучшают object cohesion.

### hover-politsia

- winner: `before-ai`
- decision: `partial`
- проблема:
  - hovercar ещё не отделён как чистый единый объект;
  - `internal-final` уже падает до `fragmented`, потому что часть нижней области объекта теряется.

### drone-portrait

- winner: `before-ai`
- decision: `coherent`
- смысл:
  - портретный субъект и бинокль уже держатся как единый foreground object;
  - contour cleanup здесь не нужен и корректно отсекается internal gate.

### punk-rooftop

- winner: `before-ai`
- decision: `coherent`
- смысл:
  - одиночная человеческая фигура на сложном wide background уже держится как единый объект;
  - это ещё один признак, что single-subject scenes у текущего proxy pipeline получаются заметно лучше.

### truck-driver

- winner: `before-ai`
- decision: `partial`
- проблема:
  - человек и руль собираются вместе, но маска слишком охотно тащит кабину и задний борт;
  - framed-subject кейсы остаются промежуточным классом между `coherent portrait` и `сложный wide scene`.

## Практический вывод

- нужно перестать считать `edge cleanup` главным quality focus;
- `group lock + object-level selection` важнее, чем ещё один postprocess по краю;
- `AI Assist` и `contour snap` должны подчиняться objectness-gate, а не только своим локальным метрикам.

## Следующий шаг

Следующий правильный этап:

- добавить отдельный internal `objectness gate`
- выбирать лучший mask variant сначала по `whole object cohesion`
- и только потом уже применять `edge cleanup` как secondary refinement

Этот шаг уже собран:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_objectness_gate.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_objectness_gate.sh`

Текущий gate summary:

- `before-ai = 6`
- `coherent = 3`
- `partial = 3`

То есть objectness-first gate сейчас везде выбирает `before-ai`.

## Артефакты

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/object_selection_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/objectness_gate_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/object_selection_batch_sheet.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/cassette-closeup/object_selection_compare_sheet.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/keyboard-hands/object_selection_compare_sheet.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/hover-politsia/object_selection_compare_sheet.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/drone-portrait/object_selection_compare_sheet.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/punk-rooftop/object_selection_compare_sheet.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/truck-driver/object_selection_compare_sheet.png`

## Команда проверки

```bash
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_object_selection_review.sh
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_objectness_gate.sh
```
