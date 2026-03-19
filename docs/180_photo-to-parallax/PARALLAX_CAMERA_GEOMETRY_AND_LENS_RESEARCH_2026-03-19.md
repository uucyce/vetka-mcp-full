# Parallax Camera Geometry And Lens Research

Дата фиксации: `2026-03-19`

## 1. Purpose

Этот документ фиксирует camera-based baseline для `photo-to-parallax` render path.

Он нужен, чтобы:

- перестать держать final parallax motion на эвристиках `parallaxStrength / motionDamping`;
- связать renderer с pinhole camera geometry;
- отдельно зафиксировать, что именно дают `Zoom`, `FOV`, `focal length (mm)` и `depth -> Z`;
- привязать все задачи по расстояниям, линзам и camera motion к одному canonical reference.

Связанные задачи:

- `tb_1773892185_4` — `PARALLAX: Introduce camera-based parallax model`
- `tb_1773892186_5` — `PARALLAX: Calibrate focal length and lens behavior against AE reference`

## 2. Why This Matters

На `2026-03-19` подтверждено следующее:

- `smart depth` path в sandbox существует и даёт осмысленные depth maps;
- export path уже умеет сохранять `plate_depth.png`;
- текущий multiplate renderer долгое время почти игнорировал per-plate depth в самом motion path;
- поэтому финальный mp4 выглядел как flat cutout / oval proxy drift, даже когда upstream depth truth была хорошей.

Вывод:

- проблема не в отсутствии depth;
- проблема в том, что parallax motion до сих пор не привязан к camera geometry как source of truth.

## 3. Confirmed AE Reference Signals

Референсный проект Паши:

- `/Users/danilagulin/Downloads/camera motion folder/camera motion.aep`
- `/Users/danilagulin/Downloads/camera motion folder/camera motionReport.txt`

Из recon подтверждено:

- проект использует `Classic 3D`;
- есть AE camera properties:
  - `ADBE Camera Zoom`
  - `ADBE Camera Focus Distance`
  - `ADBE Camera Aperture`
  - `ADBE Position`
  - `ADBE Point of Interest`
- в проекте используются depth maps как отдельные assets;
- в expressions фигурирует `Depth Map Controll` slider;
- таймлайн и panel usage подтверждают camera-driven workflow, а не чисто heuristic plate drift.

Связанный документ:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PAVEL_AE_REFERENCE_WORKFLOW_2026-03-13.md`

## 4. Current Gap In Our Stack

Сейчас в нашем коде исторически использовались:

- `parallaxStrength`
- `motionDamping`
- `travelXPct / travelYPct`
- whole-plate translate/scale

Это полезно как temporary heuristic, но не как final spatial model.

Ключевой gap:

- в current renderer отсутствует явная camera model с `Zoom` / `FOV` / `depth -> Z`;
- следовательно “расстояние” считается не как projection geometry, а как tuned multiplier.

Первый depth-aware шаг уже сделан:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview_multiplate.py`

Теперь renderer умеет использовать `plate_depth.png` через depth-band split.
Но это ещё промежуточное состояние:

- оно лучше flat whole-plate motion;
- но ещё не равно continuous camera-space warp.

## 5. Pinhole Baseline

Используем стандартную pinhole camera model.

Проекция точки `(X, Y, Z)` в camera coordinates:

```text
x' = f * X / Z
y' = f * Y / Z
```

Где:

- `f` — focal length в пикселях;
- в AE это ближе всего к `Zoom`.

При lateral camera shift по `X` на `Tx`:

```text
X_new = X - Tx
Z_new = Z
x'_new = f * (X - Tx) / Z
```

Экранное смещение:

```text
delta_x = x'_new - x' = -(f * Tx) / Z
delta_y = -(f * Ty) / Z
```

Это и есть canonical parallax rule:

- ближние точки двигаются сильнее;
- дальние слабее;
- зависимость обратно пропорциональна глубине `Z`.

## 6. Focal Length, FOV And Zoom

Для связи `mm`, `sensor / film size` и `Zoom`:

```text
AOV = 2 * atan(film_width_mm / (2 * focal_length_mm))
zoom_px = frame_width_px / (2 * tan(AOV / 2))
```

Практический смысл:

- `focal_length_mm` и `film_width_mm` задают `AOV`;
- `AOV` задаёт `zoom_px`;
- именно `zoom_px` напрямую участвует в projection formulas renderer-а.

Что важно для продукта:

- при fixed camera position смена `mm` меняет framing/FOV, но не создаёт parallax сама по себе;
- parallax рождается от camera motion относительно depth;
- при same framing длинная линза обычно требует большей distance до сцены, из-за чего perspective compression растёт и ощущаемый parallax уменьшается.

## 7. Practical Depth Mapping

Если depth map нормализована как:

- `D = 0` => far
- `D = 1` => near

то рабочее преобразование в `Z` можно начинать с:

```text
Z = Z_near + (1 - D) * (Z_far - Z_near)
```

Где:

- `Z_near`
- `Z_far`

задаются как camera-space calibration parameters.

Стартовая practical recommendation:

- хранить `camera_zoom_px`
- хранить `z_near`
- хранить `z_far`
- сначала калибровать against AE reference, а не пытаться сразу угадывать “реальные метры”.

## 8. Renderer Formula For Our Stack

Минимальный camera-based motion для нашего renderer:

```text
delta_x = -(camera_zoom_px * camera_tx) / Z
delta_y = -(camera_zoom_px * camera_ty) / Z
```

Для `Tz`:

- можно использовать dolly-scale approximation;
- затем перейти к full camera pose / projection update.

Практические уровни реализации:

1. `Per-layer Z`
- быстро;
- даёт cardboard effect.

2. `Per-band depth`
- уже реализовано как first recovery slice;
- полезно как intermediate path.

3. `Continuous depth warp`
- целевое production направление;
- depth map участвует в per-pixel displacement, а не только в plate-level multiplier.

## 9. Recommended Recovery Sequence

### Stage 1. Camera Parameters In Contracts

Добавить explicit render inputs:

- `camera_zoom_px`
- `camera_tx`
- `camera_ty`
- `camera_tz`
- `z_near`
- `z_far`

И связать их с current motion presets вместо чистых эвристик.

### Stage 2. Camera-Based Per-Band Motion

Заменить heuristic band multipliers на camera-derived motion:

- сначала по representative `Z_band`;
- сохранить current banded renderer как bridge stage.

### Stage 3. Continuous Depth Warp

Перейти от banded split к continuous depth warp:

- per-pixel displacement from `depth -> Z`;
- overscan and hole-handling как отдельная quality layer.

### Stage 4. AE Calibration

Сверить renderer против AE reference:

- одинаковый `Zoom`
- одинаковые `Tx / Ty`
- controlled sample
- visual diff / motion sanity

Done criteria:

- final parallax больше не ощущается как oval proxy drift;
- motion читается как camera-space parallax;
- lens/FOV behavior объясняется документированными параметрами, а не тюнингом на глаз.

## 10. Roadmap Binding

Все следующие задачи про:

- camera model
- focal length / lens behavior
- distance calculation
- AE calibration
- continuous depth warp

должны ссылаться на этот документ как на canonical geometry reference.

Он дополняет:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_SMART_DEPTH_RECON_2026-03-19.md`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_LAYER_SPACE_RECOVERY_PLAN_2026-03-19.md`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PAVEL_AE_REFERENCE_WORKFLOW_2026-03-13.md`

## 11. Current Status

На момент фиксации:

- research baseline сформулирован;
- AE reference signals собраны;
- first depth-aware renderer slice уже внедрён;
- camera-based model ещё не стала default render truth.

То есть:

- этот документ закрывает research ambiguity;
- но implementation track ещё открыт.
