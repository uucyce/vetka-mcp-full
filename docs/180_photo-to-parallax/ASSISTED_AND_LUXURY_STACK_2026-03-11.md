# Assisted and Luxury Stack

Дата фиксации: `2026-03-11`

## 1. Зачем это нужно

Базовый Resolve-like путь уже даёт рабочий результат:

- `depth`
- coarse/refined mask
- `subject_rgba`
- `clean_plate`
- mild parallax render

Но для тяжёлых сцен этого мало:

- волосы и тонкие контуры;
- несколько depth planes;
- ambiguous foreground/background ordering;
- large holes после удаления объекта;
- future video flicker/temporal inconsistency.

Поэтому архитектура расширяется не новой "магической" моделью, а тремя продуктовыми режимами:

- `Auto Base`
- `Manual Pro`
- `AI Assist`

## 2. Auto Base

Что уже принято:

- `Depth Pro` как quality-first coarse depth;
- `Depth Anything V2 Small` как fallback/comparison backend;
- `polarity-aware seed-grow` как canonical coarse mask;
- `conditional SAM 2` как refine stage;
- `OpenCV inpaint` как baseline `clean_plate`;
- `LaMa` как следующий quality target.

Для пользователя это режим "одна кнопка", близкий к Resolve mental model.

## 3. Manual Pro

Цель:

- дать пользователю минимальный, но осознанный контроль;
- улучшить separation там, где automatics сомневаются;
- исправлять object grouping, а не только mask edges.

### 3.1 Пользовательский контракт

Простой вариант:

- `mask_hint.png`
- красный = ближе
- синий = дальше
- зелёный = не трогать / защитить

Возможные расширения:

- точки;
- box;
- scribbles;
- trimap seed.

### 3.2 Как это встраивается

- подсказки конвертируются в prompts для `SAM 2`;
- в подсказанных регионах можно локально переоценить depth polarity;
- итог выбирается сравнением:
  - base result
  - hinted result
  - coarse passthrough
- следующий обязательный шаг:
  - `Same Layer / Merge Group`
  - region-level grouping вместо только pixel split

### 3.3 Почему это имеет смысл

- это самый дешёвый путь к росту качества;
- пользователь даёт именно тот тип знания, которого не хватает depth-only пайплайну;
- это хорошо ложится на знакомую Resolve-like UX модель.

## 4. AI Assist

`AI Assist` не должен заменять `Auto Base` или `Manual Pro`. Он нужен для сложных сцен как semantic helper.

### 4.1 Semantic judge / refiner

Кандидат:

- `Qwen2.5-VL-7B`

Роль:

- интерпретировать цветовые hints;
- перечислять объекты и их относительный depth order;
- проверять, не перепутан ли foreground/background;
- предлагать grouping вроде:
  - "обе руки и кассета должны быть в одном ближнем слое"
  - "клавиатуру не делить по диагонали на две глубины"
- выпускать JSON guidance для refinement.

Чего он не делает:

- не является depth backend;
- не заменяет segmentation;
- не должен сам решать final mask без compare gate.

### 4.2 Optional pre-depth upscale

Кандидат:

- `Real-ESRGAN`

Назначение:

- увеличить локальные детали до depth inference;
- потенциально улучшить контуры и separation на мелких объектах.

Ограничение:

- upscale не бесплатен по качеству;
- он может дорисовать текстуру и сделать края менее честными;
- значит его надо тестировать как `optional A/B stage`, а не включать всегда.

### 4.3 Что делать с `V-JEPA 2`

Кандидат:

- `V-JEPA 2`

Текущая позиция:

- для нашего программно заданного motion он сейчас не нужен;
- он не решает главную текущую проблему:
  - semantic grouping
  - object boundaries
  - keep-object-together logic

Чего он не делает:

- не является direct depth predictor;
- не нужен в core single-image MVP;
- не нужен до тех пор, пока не появится реальный sequence/video mode.

## 5. Практический вывод

Ближайший quality path:

1. `Manual Pro UI`
2. `SAM 2 + user color hints`
3. `Same Layer / Merge Group`
4. `LaMa` для clean plate

Следующий исследовательский слой:

1. `Qwen2.5-VL` как semantic judge
2. `Real-ESRGAN` как optional A/B stage
3. `V-JEPA 2` только после появления sequence/video mode

## 6. Что не надо делать

- не объявлять `Qwen2.5-VL` depth-моделью;
- не объявлять `V-JEPA 2` решением depth map или object grouping;
- не включать upscale always-on;
- не смешивать user-guided quality path с простым one-click mode.

## 7. Источники

- `SAM 2`: [github.com/facebookresearch/sam2](https://github.com/facebookresearch/sam2)
- `Real-ESRGAN`: [github.com/xinntao/Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)
- `Qwen2.5-VL` repo: [github.com/QwenLM/Qwen2.5-VL](https://github.com/QwenLM/Qwen2.5-VL)
- `Qwen2.5-VL-7B-Instruct` model card: [huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct)
- `V-JEPA 2`: [github.com/facebookresearch/vjepa2](https://github.com/facebookresearch/vjepa2)
