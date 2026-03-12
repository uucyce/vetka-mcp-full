# Plate Mask Composition Results

Дата: `2026-03-13`

## Что сделано

Live preview в sandbox переведён с `rectangular proxy plates` на `mask-based plate composition`.

До этого `plate-aware` preview уже умел:

- читать `plateStack`;
- читать `exportPlateLayout()`;
- двигать plate-ы с учётом `order`, `z`, `parallaxStrength`, `motionDamping`.

Но сами plate-ы показывались через `clipPath` по прямоугольным box-ам, что годилось только как debug-bridge.

Теперь preview использует:

- `backgroundMaskUrl`
- `plateMaskUrls[]`
- `plateCoverage[]`

из `buildPlateCompositeMaps(...)`.

## Как теперь устроен preview

### Background

Фон остаётся базовым plane, но при наличии видимых renderable plate-ов теперь маскируется inverse-union маской:

- `backgroundMaskUrl`
- `maskImage / WebkitMaskImage`

Это убирает старую ситуацию, когда background plane продолжал светиться поверх pseudo-plate split.

### Plate planes

Каждый renderable plate теперь:

- получает свою alpha mask из `plateMaskUrls[plate.id]`;
- больше не зависит от `clipPath` как основного user-facing split;
- двигается с прежними `z`, `parallaxStrength`, `motionDamping`.

Дополнительно введён safety filter:

- plate попадает в preview только если `plateCoverage > 0.002`.

Это убирает пустые или почти пустые planes из сцены.

## Что это означает продуктово

Это ещё не финальный `RGBA plate extraction`, но это уже важный переход:

- раньше preview был `plate-aware` только логически;
- теперь он `plate-aware` и по alpha composition.

То есть следующий продуктовый слой уже не `ещё один proxy box`, а:

- `real per-plate RGBA`
- `plate-local clean plate`
- `N-plate render/export`

## Ограничения

- маски пока строятся из:
  - `global depth`
  - `manual isolate`
  - `plate role`
  - `plate box`
- это ещё не полноценная object-accurate plate extraction;
- `special-clean` и `background-far` не рендерятся как отдельные пользовательские plate-ы в live preview;
- source image пока одна и та же для всех plate plane-ов, меняется только alpha mask и motion response.

## Вывод

Шаг `plateStack -> plate-aware layout -> mask-based preview composition` закрыт.

Следующий шаг по roadmap:

- заменить mask-only plate preview на настоящую `per-plate RGBA composition`.
