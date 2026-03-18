# Qwen-Image-Layered Fit Review

Дата ревизии: `2026-03-18`

## 1. Scope

Оценить модель `Qwen-Image-Layered` как кандидата для следующего parallax-track.

Речь не про прямую замену текущего pipeline, а про:

- candidate layered decomposition backend;
- candidate draft generator для `plateStack`;
- потенциальный source of RGBA layers для complex scenes.

Источник:

- `QwenLM/Qwen-Image-Layered`: [GitHub](https://github.com/QwenLM/Qwen-Image-Layered)

## 2. What The Model Actually Gives

По README модель умеет:

- decomposing one image into multiple RGBA layers;
- variable number of layers;
- recursive decomposition;
- independent layer editing workflows;
- export/use cases around PSD/PPTX/editable layer stacks.

Ключевая польза для нас:

- это ближе к `Multi-Plate Authoring`, чем обычный depth-first path;
- модель работает в пространстве `RGBA layers`, а не только `depth + mask`;
- это совпадает с нашей целью перейти от одной глобальной маски к осмысленным plate-слоям.

## 3. Why It Is Relevant For Parallax

Наш текущий pain point:

- на complex scenes одна depth-derived маска недостаточна;
- нам нужен осознанный `plate decomposition`;
- мы уже построили contracts вокруг `plateStack`, `qwen gate`, `plate-aware layout`, `multiplate render`.

`Qwen-Image-Layered` потенциально полезен потому что:

- может дать richer RGBA decomposition для foreground / mid / background;
- может улучшить object-level separation без ручного box/group authoring;
- может стать upstream источником для `plateStack draft`.

## 4. What It Does Not Replace

Модель не заменяет наши release-critical компоненты:

- `cameraSafe`
- `plate z`
- `depth priority`
- routing `Portrait Base` vs `Multi-Plate`
- deterministic `Qwen Gate`
- export contracts
- render quality gates

Вывод:

- модель нельзя рассматривать как direct final-path replacement;
- правильное место для неё это `candidate decomposition backend` под compare/gate.

## 5. Integration Risks

### Risk A. Runtime cost

README показывает запуск через `diffusers`, `transformers`, `torch`, `cuda`, `bfloat16`.

Inference profile похож на GPU-oriented path, а не на лёгкий локальный baseline.

Следствие:

- это не похоже на дешёвый always-on backend для sandbox по умолчанию.

### Risk B. Layer semantics vs parallax semantics

RGBA layers модели не гарантируют автоматически:

- правильный parallax order;
- safe z spacing;
- controllable motion;
- stable special-clean strategy.

Следствие:

- нужен adapter layer между model output и нашим `plateStack`.

### Risk C. Fragmentation

Переменное число слоёв полезно, но может приводить к слишком мелкой fragmentation.

Для parallax это плохо, потому что:

- мелкие слои увеличивают layout risk;
- сложнее собирать stable plate families;
- сложнее делать predictable render gating.

## 6. Recommended Integration Shape

Если брать модель, то только по схеме:

### Stage 1. Bakeoff-only

- взять `3-6` complex scenes;
- получить layered RGBA output;
- сравнить против текущего `manual/gated stack`.

### Stage 2. Adapter

Сделать adapter:

- `model layers -> normalized layer candidates -> plate families -> draft plateStack`

Примерный adapter output:

- `draft_plate_stack.json`
- `layer_rgba/*.png`
- optional `layer_coverages.json`
- optional `layer_order_candidates.json`

### Stage 3. Gate

Draft stack не идёт напрямую в final render.

Он должен проходить через:

- structural validation;
- overlap / visibility sanity checks;
- optional merge/downsample logic;
- compare against current deterministic stack.

## 7. Proposed Bakeoff Questions

На bakeoff нужно отвечать на конкретные вопросы:

- Улучшается ли whole-object separation?
- Улучшается ли сложная многоплановая сцена относительно depth-first path?
- Не становится ли layer stack слишком фрагментированным?
- Насколько удобно маппить model layers в наши plate families?
- Можно ли использовать результат как `plateStack draft`, а не только как visual demo?

## 8. Recommendation

Рекомендация: `GO`, но только как `controlled bakeoff`.

Не рекомендую:

- интегрировать модель сразу в release path;
- заменять ею `Qwen Plate Planner` или `Qwen Gate`;
- строить на ней release-v1 dependency.

Рекомендую:

- открыть отдельный recon/bakeoff lane;
- проверить fit на complex scenes;
- строить adapter в `draft plateStack`, а не в final stack.

## 9. Decision

Текущее решение:

- `GO for recon and bakeoff`
- `NO GO for direct release integration`

Это согласуется с:

- `PARALLAX_ARCHITECTURE_RELEASE_V1_2026-03-18.md`
- текущей release-v1 политикой `gate first, deterministic final path`
