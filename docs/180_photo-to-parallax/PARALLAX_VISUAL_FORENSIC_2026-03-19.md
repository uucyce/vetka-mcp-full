# Parallax Visual Forensic

Дата: `2026-03-19`

## 1. Why This Exists

После достижения batch `pass` по `RC1` появилась важная продуктовая претензия:

- текущие post-`2026-03-12` видео могут выглядеть как proxy/focus cutout;
- визуально это не обязательно воспринимается как хороший layered parallax;
- значит технический `pass` и visual acceptance разошлись.

Этот документ фиксирует, где именно произошёл drift.

## 2. Confirmed Baseline Reference

Пользовательский visual success reference:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/custom_renders`

Наиболее характерные артефакты там:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/custom_renders/depth-anything-v2-small/drone-portrait_arc_5s_v2/preview_arc_5s_v2.mp4`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/custom_renders/depth-anything-v2-small/drone-portrait_motion_pack_v4/orbit_temporal_default/orbit_temporal_default.mp4`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/custom_renders/depth-anything-v2-small/drone-portrait_motion_pack_v4/pan_temporal_default/pan_temporal_default.mp4`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/custom_renders/depth-anything-v2-small/drone-portrait_motion_pack_v4/push_in_temporal_default/push_in_temporal_default.mp4`

Это старый deterministic render path из:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview.py`

## 3. What Changed Later

Текущий `RC1`/`qwen_gated` path рендерится уже другим renderer:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview_multiplate.py`

Он читает экспортированные assets из:

- `plate_export_manifest.json`
- `plate_layout.json`

и честно собирает ffmpeg plate-aware composite.

Значит проблема не в финальном ffmpeg renderer как таковом.

## 4. Main Drift Source

Основной drift сидит раньше, в generation of exported plate assets.

Точка:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx`
- функция `buildPlateCompositeMaps(...)`

Что она делает сейчас:

- берёт `computeResolvedDepth(...)`;
- использует `smoothBoxMask(...)`;
- строит `plateMaskUrls` и `plateRgbaUrls` browser-side через canvas;
- background строит как остаток от union alpha;
- `background-far` plate вообще не экспортируется как самостоятельный RGBA layer.

Следствия:

1. plate assets получаются не из real semantic decomposition, а из:
- depth/remap;
- box-shaped plate priors;
- focus/manual controls;
- synthetic alpha composition.

2. Это может визуально выглядеть как:
- центральная/овальная/box-like вырезка;
- foreground cutout поверх почти неподвижного фона;
- слабое ощущение настоящего multi-layer space.

3. Текущий batch `pass` этого не ловит, потому что он проверяет:
- contracts;
- readiness;
- camera-safe;
- render validity;
- preset summaries.

Но не проверяет:

- visual closeness к successful `2026-03-12` baseline;
- отсутствие proxy-like oval cutout look.

## 5. Important Technical Evidence

### Old success path

Старый renderer:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview.py`

Работал по схеме:

- `overscan plate`
- `subject_rgba`
- deterministic two-layer motion

Это был более узкий path, но он дал понятный visual success на reference scenes.

### Current path

Текущий renderer:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview_multiplate.py`

формально layered, но его assets upstream синтезируются из browser-side proxy composition.

### Current export evidence

Например для `hover-politsia`:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports_qwen_gated/hover-politsia/plate_export_manifest.json`

видно, что:

- renderable plates имеют очень небольшие coverages;
- `background-far` имеет `coverage = 0`;
- special clean есть, но это не эквивалент настоящего independent background plate.

Это согласуется с ощущением “foreground cutout over derived background”.

## 6. Product Conclusion

Текущее состояние надо читать так:

- `RC1 pass` = technical release pass
- `visual acceptance against March 12 baseline` = not proven

То есть:

- release path стабилен;
- visual quality gap остаётся открытым;
- пользовательская претензия валидна.

## 7. Required Next Step

Нужен отдельный visual regression track.

Минимальные задачи:

1. Зафиксировать `2026-03-12 custom_renders` как visual gold baseline.
2. Сравнить current `qwen_gated` mp4 против baseline на тех же perceptual questions:
- layered depth feeling
- whole-object coherence
- absence of oval/proxy cutout
- background independence

3. Разделить два preview класса:
- `proxy/debug preview`
- `release render preview`

4. Не считать future `pass` достаточным без visual gate.

## 8. Actionable Engineering Hypothesis

Самый вероятный root cause:

- migration в `plate-aware export` произошла быстрее, чем migration from proxy-generated masks to truly robust layer assets.

Проще:

- renderer стал сложнее и формально правильнее;
- source layers для него остались слишком synthetic.

## 9. Decision

Решение после forensic review:

- не считать текущий `pass` окончательной победой по visual product quality;
- вернуть visual acceptance в roadmap как hard gate;
- считать `Qwen-Image-Layered` полезным не только как future backend, но и как возможный способ уйти от synthetic browser-side layer generation.
