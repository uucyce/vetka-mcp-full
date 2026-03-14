# Recon & Handoff: Photo-to-Parallax (2026-03-11)

## 1. Mission snapshot
- Цель: single-image photo-to-parallax pipeline, который из одного кадра выпускает структурированные depth/mask/plate ассеты и детерминированный preview, сохраняя исследовательский sandbox рядом с базовым треком.
- Базовый поток: `depth -> coarse mask -> conditional SAM 2 -> subject_rgba -> clean_plate -> overscan -> render`, с заделом на assisted и luxury расширения (mask hints, optional pre-depth upscale, semantic judge, future video-consistency). См. архитектуру в `PHOTO_TO_PARALLAX_ARCHITECTURE_V1_2026-03-10.md`.

## 2. Текущий статус
### Depth & mask track
- Сформирован кастомный sample set из четырёх сцен (крупный объект, руки/ретро-клавиатура, летающий автомобиль, квадратный портрет) и зафиксирован readiness report (`sample_analysis_2026-03-10.json`).
- Depth bake-off прошёл для `Depth Anything V2 Small` и `Depth Pro`, выходы живут в `photo_parallax_playground/output/depth_bakeoff`; runtime-преимущество у Depth Anything (~24× быстрее).
- Mask bake-off + refinement через `SAM 2` довели стратегию до `coarse -> candidates -> compare with passthrough -> choose winner`, и маска + plate теперь экспортируются как `subject_rgba`, `subject_trimap`, `foreground_rgba`, `background_rgba`, `clean_plate`, `hole_mask`, `hole_overlay`.
- Guided hints (mask_hint.png + scribbles) генерятся в `photo_parallax_playground/public/sample_hints`, используются в экспериментальных подсказках и UI-guided overlay mode.

### Plate track
- `OpenCV inpaint` работает как baseline / fallback, но качество видно ограниченным, особенно на `drone-portrait` и крупных foreground slabs.
- `LaMa` bake-off завершён и дал `8/8` улучшений против baseline на текущем sample set.
- Canonical split теперь такой:
  - `OpenCV inpaint` = fallback / base
  - `LaMa` = quality-target `clean_plate`
- `overscan_plate` тоже уже материализован:
  - строится поверх `LaMa clean_plate`;
  - сохраняет `layout.json`;
  - готов для первого render step.
- `ffmpeg` preview renderer теперь тоже есть:
  - выпускает `preview.mp4`
  - сохраняет `render_report.json`
  - работает batch-ом на всём sample set.
- visual gate поверх renderer тоже уже есть:
  - `render_review_sheet.png`
  - `debug_side_by_side.mp4`
  - `render_review_batch_sheet.png`
  - heuristic status `two_layer_ok / caution / needs_3_layer`

### Upscale bake-off (Real-ESRGAN x2)
- Real-ESRGAN x2 тестировался против native depth -> mask на четырёх сценах и двух бекендах; результаты закодированы в `upscale_depth_bakeoff_summary.json`.
- `avg_mask_delta` у обоих бекендов отрицательный (`Depth Anything V2 Small`: −0.13889, `Depth Pro`: −0.12129), mask_improved = 0/4, поэтому upscale не улучшает coarse mask и остаётся manual luxury опцией.
- Отмечены частичное улучшение depth edges и повышенная стоимость `Depth Pro + upscaled full-res mask search`, а Real-ESRGAN на MPS нестабилен для крупных кадров; включение в default path не рекомендовано.

## 3. Артефакты и логи
- Sample root: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/public/samples`.
- Depth bake-off outputs: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/depth_bakeoff`.
- Mask bake-off outputs: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mask_bakeoff`.
- Upscale bake-off outputs + summary: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/upscale_depth_bakeoff` (см. `upscale_depth_bakeoff_summary.json`).
- Protocol log и TODO list: `docs/180_photo-to-parallax/PHOTO_TO_PARALLAX_PROTOCOL_LOG_2026-03-10.md`.
- Sample hints: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/public/sample_hints`.

## 4. Immediate next workstreams
1. **3-layer planner** – для кейсов `needs_3_layer` ввести раннее разбиение не только на `FG/BG`, а хотя бы `FG / mid / BG`.
2. **Safer preset reducer** – для кейсов `caution` автоматически срезать motion amplitude или zoom без ручного вмешательства.
3. **Guided-to-LaMa coupling** – проверить, улучшают ли guided masks качество `clean_plate` ещё до стадии overscan и стоит ли связывать `mask_hint.png` с quality mode жёстче.

## 5. How to pick up
- Подготовить виртуальную среду через `./scripts/photo_parallax_depth_bootstrap.sh` (устанавливает Depth Anything/Depth Pro зависимости и `torchvision`).
- Если нужно refinement-окружение, запустить `./scripts/photo_parallax_mask_refine_bootstrap.sh`.
- Depth/mask bake-offs запускаются через `scripts/photo_parallax_depth_bakeoff.py` и `scripts/photo_parallax_mask_bakeoff.py` (есть toplevel `.sh` обёртки).
- Для upscale runs: `./scripts/photo_parallax_realesrgan_bootstrap.sh` (устанавливает `basicsr`/`realesrgan`, скачивает `RealESRGAN_x2plus.pth`, ставит shim `torchvision.transforms.functional_tensor`) и затем `./scripts/photo_parallax_upscale_depth_bakeoff.sh`.
- Upscale runner автоматически подставляет `upscaled_inputs` в depth/mask bake-offs и сохраняет результат в `output/upscale_depth_bakeoff`.

## 6. Reference docs
- `PHOTO_TO_PARALLAX_ARCHITECTURE_V1_2026-03-10.md` – описывает декомпозицию stages и assisted/luxury пути.
- `PHOTO_TO_PARALLAX_PROTOCOL_LOG_2026-03-10.md` – хронология P-шагов, runtime-заметки (Real-ESRGAN MPS нестабилен, Depth Pro дорогой, mask hints контракт) и TODO.
- `MASK_BAKEOFF_RESULTS_2026-03-11.md`, `MASK_REFINE_RESULTS_2026-03-11.md`, `GUIDED_MASK_RESULTS_2026-03-11.md`, `SUBJECT_PLATE_BASELINE_RESULTS_2026-03-11.md` – свежие метрики по mask/plate.
- `UPSCALE_DEPTH_BAKEOFF_RESULTS_2026-03-11.md` + `upscale_depth_bakeoff_summary.json` – выводы по Real-ESRGAN vs native, confirmed “не включать всегда”.
- `sample_analysis_2026-03-10.json` – quantitative readiness для четырёх сцен.

## 7. Questions / risks
- Для `LaMa` вопрос по самому `clean_plate` закрыт; дальше остаётся только renderer quality и границы двухслойного motion.
- Real-ESRGAN пока нестабилен (mps) и дорог в сочетании с Depth Pro; запускать только в оффлайн batch path.
- Canonical `ffmpeg` graph уже есть, и heuristic visual gate тоже собран; теперь главный риск сместился в отсутствие `3-layer` planner для сложных сцен.
