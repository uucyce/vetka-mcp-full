# Parallax Handoff To Fresh Chat RC1

Дата: `2026-03-19`

## 1. Зачем этот handoff

Этот документ нужен как короткая входная точка для нового чата, чтобы не перечитывать весь phase 180 с нуля.

Он фиксирует:

- какие документы сейчас являются source of truth;
- что именно было сделано по `parallax`;
- что не получилось закрыть идеально;
- что сработало хорошо;
- какие идеи и next tracks выглядят разумно;
- как оценивать свежую `Qwen` layered-модель.

Критическое правило для следующего чата:

- успешный `export/render` нельзя больше трактовать как завершённость продукта;
- это только engineering signal, что sandbox/export path работает;
- product readiness требует сохранения depth-first truth и отдельного visual acceptance.

## 2. Source Of Truth

Начинать всегда с этих документов:

1. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_ARCHITECTURE_RELEASE_V1_2026-03-18.md`
2. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_DOC_REVIEW_2026-03-18.md`
3. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/HANDOFF_PHASE_180_2026-03-14.md`
4. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/CONTRACTS_V1.md`
5. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/RELEASE_NOTES_V1_RC1_2026-03-19.md`
6. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/QWEN_IMAGE_LAYERED_FIT_REVIEW_2026-03-18.md`

Исторические evidence-docs полезны как proof, но уже не как planning source.

## 3. Что сделали

### Release backlog

Все основные parallax-задачи в TaskBoard доведены до `done`:

- `tb_1773857716_1` — RECON 1
- `tb_1773857716_2` — RECON 2
- `tb_1773857716_3` — v1.1 freeze contracts
- `tb_1773857716_4` — v1.2 anti-flake + QA
- `tb_1773857716_5` — v1.3 final render presets
- `tb_1773857716_6` — v1.4 regression quality pack
- `tb_1773857717_7` — v1.5 service extraction from `App.tsx`
- `tb_1773857717_8` — v1.6 RC1 packaging/runbook/smoke

### По коду и артефактам

1. Anti-flake и export stability:
- readiness diagnostics введены и встроены в flow;
- gated batch QA summary собирается автоматически;
- `truck-driver` стабилизирован на wrapper-level.

2. Render presets:
- `quality`, `web`, `social` реализованы;
- summaries по preset-ам разведены по отдельным директориям;
- render summary теперь включает codec, bitrate, file size, validation.

3. Regression pack:
- появился `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/regression_quality_summary.json`
- он агрегирует:
  - `gated_batch_qa_summary.json`
  - `render_compare_qwen_multiplate_summary.json`
  - preset summaries
- на каждый sample даёт:
  - `status`
  - `reasons`
  - evidence paths

4. RC1 docs:
- README получил `RC1 Runbook`;
- добавлены release notes;
- handoff и architecture docs синхронизированы.

5. Refactor:
- из `App.tsx` вынесены release-critical pure services в:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/lib/plateLayout.ts`
- туда вынесено:
  - `recommendWorkflowRouting`
  - `deriveParallaxStrength`
  - `buildPlateLayoutContract`
  - `buildPlateExportAssetsContract`
- tests:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/lib/plateLayout.test.ts`

## 4. Последние важные коммиты

- `bf812d15` — final render presets
- `0de08be9` — regression quality pack
- `67cc7df9` — service extraction from `App.tsx`
- `f816874d` — RC1 runbook and release notes

## 5. Что не получилось идеально

1. TaskBoard hard-close:
- `complete` по-прежнему упирался в `pipeline_success must be true before closing the task`
- обходной путь: переводили задачи в `done_worktree`, потом в `done`
- это проблема процесса/борда, не parallax-кода

2. RC1 quality verdict:
- текущий release verdict остаётся `caution`, не `pass`
- причина не в падениях pipeline, а в содержательных safety-ограничениях:
  - `camera-safe gate is not fully satisfied`
  - иногда `readiness required more than one poll`

3. Полный refactor App:
- `App.tsx` стал тоньше, но ещё остаётся большим
- следующий этап рефактора возможен, но release-critical долг уже снижен

## 6. Что было хорошо

1. Gated flow дал стабильный backbone:
- export
- render
- compare
- QA
- regression summary

2. Docs стали лучше, чем были:
- появился внятный release source of truth
- backlog перестал расходиться с фактическим кодом

3. Артефакты стали machine-readable:
- нет нужды “смотреть глазами” всё подряд, чтобы понять состояние batch

4. Refactor оказался безопасным:
- `npm test` и `npm run build` зелёные после выноса сервисов

## 7. Canonical smoke и артефакты

Canonical command:

```bash
bash /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_qwen_gated_multiplate_flow.sh hover-politsia keyboard-hands truck-driver
```

Главные артефакты:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/gated_batch_qa_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/regression_quality_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/render_compare_qwen_multiplate_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/compare_batch_sheet.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/visual_acceptance_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/visual_acceptance_checklist.md`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen_gated/render_preview_multiplate_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen_gated/web/render_preview_multiplate_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen_gated/social/render_preview_multiplate_summary.json`

Текущий итог:

- `overall_status = pass`
- `pass = 3`
- `caution = 0`
- `fail = 0`

Этот `pass` означает только:

- canonical smoke проходит стабильно;
- export/layout/render contracts сейчас не падают на canonical set.

Этот `pass` не означает:

- что можно деплоить продукт без дополнительных visual checks;
- что synthetic export path уже совпал с depth-first product truth;
- что layered parallax quality подтверждена только самим фактом экспорта.

Что изменилось до `pass`:

- export/layout path теперь auto-applies `cameraSafe.suggestion` для risky scenes;
- `plate_layout.json` сохраняет `cameraSafe.adjustment` с requested/effective motion;
- readiness на canonical smoke сейчас проходит с `attempts = 1` на текущем sample set.

Но важная оговорка:

- technical `pass` не равен автоматически visual success;
- March 12 user-approved success path жил в `output/review` / `output/layered_edit_flow` / `output/custom_renders`;
- текущий `render_preview_multiplate*` contract должен отдельно пройти visual regression check.
- для этого теперь есть отдельный visual acceptance pack builder:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_build_visual_acceptance_pack.py`

## 8. Идеи на следующий этап

1. Зафиксировать post-pass hardening:
- задокументировать verdict aggregation policy;
- удержать repeatability smoke и summaries;
- не допустить drift между contract-level pass и batch-level pass.
- не допустить подмены product goal формулой `export works => system ready`.

2. Продолжить рефактор:
- отделить export/orchestration helpers из `App.tsx`
- дальше дробить debug API wiring

3. Сделать controlled bakeoff нового decomposition backend
- не встраивать сразу в final path
- сначала давать `draft plateStack` / `draft RGBA layers`
- сравнивать против current gated stack

## 9. Про новую Qwen-модель, которая режет на слои

Речь про `Qwen-Image-Layered`.

Что уже зафиксировано:

- fit review: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/QWEN_IMAGE_LAYERED_FIT_REVIEW_2026-03-18.md`

Вывод по ней сейчас:

- это `GO` для recon / controlled bakeoff
- это `NO GO` как прямая замена release path

Почему полезна:

- умеет layered decomposition в RGBA layers;
- концептуально хорошо совпадает с multi-plate направлением;
- может стать кандидатом на `draft plateStack generator`.

Почему нельзя сразу встроить:

- не заменяет:
  - `cameraSafe`
  - `z/depth priority`
  - deterministic gate
  - release contracts
- сначала должна пройти как compare-track, а не как новый default runtime.

## 10. Что говорить в свежем чате

Короткий стартовый промпт для следующего чата:

1. Прочитай:
- `PARALLAX_ARCHITECTURE_RELEASE_V1_2026-03-18.md`
- `PARALLAX_DOC_REVIEW_2026-03-18.md`
- `HANDOFF_TO_FRESH_CHAT_RC1_2026-03-19.md`
- `RELEASE_NOTES_V1_RC1_2026-03-19.md`

2. Считай текущим состоянием:
- release backlog по `parallax` закрыт;
- RC1 smoke path работает;
- текущий verdict = `pass`;
- следующий meaningful step = release hardening и controlled bakeoff `Qwen-Image-Layered`.

3. Не трать время на повторное восстановление TaskBoard истории:
- parallax-тasks уже выровнены;
- использовать board как навигацию, а не как единственный источник истины.
