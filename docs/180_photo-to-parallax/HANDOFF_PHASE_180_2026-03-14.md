# Handoff Phase 180 (2026-03-14)

## 1) Где мы были -> куда идем

### Откуда пришли

- Стартовали как `depth-first` инструмент (в духе Resolve):  
  `photo -> depth map -> isolate -> clean plate -> overscan -> render`.
- На портретах и простых сценах этот путь уже рабочий (`Portrait Base`).
- На сложных сценах выяснили, что одной глобальной depth-маски недостаточно.

### Куда идем

- Основной следующий трек: `Multi-Plate Authoring` (по референсу AE workflow).
- Цель: осознанные независимые plate-слои со своим `z`, `depth priority`, `clean variant`, и безопасным camera layout.
- Режимы:
  - `Portrait Base` для простых/портретных сцен;
  - `Multi-Plate` для сложных сцен.

## 2) Архитектура (текущее состояние)

Главный документ:  
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PHOTO_TO_PARALLAX_ARCHITECTURE_V1_2026-03-10.md`

Актуальный operational release-документ с `2026-03-18`:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_ARCHITECTURE_RELEASE_V1_2026-03-18.md`

Ключевые сущности:

- `plateStack` (UI + export contract)
- `plate_layout.json` (camera/layout contract)
- `plate_export_manifest.json` (файловый export contract)
- `qwen_plate_plan.json` (semantic proposal)
- `qwen_plate_gate.json` (deterministic gate)

Текущая продуктовая политика:

- raw `Qwen` proposal напрямую в финальный render не идет.
- В финальный path идет только `gated_plate_stack`.
- `Qwen` используется как `enrichment layer`, не как unconditional replacement.

## 3) Roadmap (что уже закрыто / что следующее)

Чек-лист:  
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PHOTO_TO_PARALLAX_ROADMAP_CHECKLIST_2026-03-10.md`

Уже закрыто в последних шагах:

- `Qwen Plate Planner`
- `Qwen Plate Gate`
- `gate-aware qwen flow` (`manual -> gate -> export -> render -> compare`) на `3/3` complex scenes
- `routing rule` (`Portrait Base` vs `Multi-Plate`)
- `camera-safe` + `per-plate overscan risk` + `transition risk`

Следующий практический шаг:

- На основе `cameraSafe` ввести auto-warning + motion suggestion:
  - safe overscan
  - safe travel x/y
  - warning reason

Статус обновление (`2026-03-14`, codex/cut):

- ✅ Реализовано в playground (`src/App.tsx`):
  - `plate_layout.cameraSafe.suggestion` теперь экспортирует:
    - `overscanPct`
    - `travelXPct`
    - `travelYPct`
    - `reason`
  - `cameraSafe.warning` и `cameraSafe.suggestion` выведены в существующую `Camera` карточку и Debug snapshot.
  - Добавлены state-поля для headless/debug API:
    - `cameraSafeSuggestedOverscanPct`
    - `cameraSafeSuggestedTravelXPct`
    - `cameraSafeSuggestedTravelYPct`
    - `cameraSafeSuggestionReason`

Следующий практический шаг после этого:

- Ввести auto-remediation хелпер (без расширения UI):
  - apply suggested overscan/travel в один вызов debug API/CLI;
  - зафиксировать это в e2e export flow как опциональный pre-render шаг.

Статус обновление (`2026-03-14`, anti-flake export hardening):

- ✅ Укреплен Playwright plate export readiness gate:
  - детерминированные env-настройки poll/retry;
  - многошаговый hydrate (`stage` + `asset` fallback);
  - bounded final retries для `sourceRasterReady`.
- ✅ Добавлен единый диагностика-контракт:
  - `plate_export_readiness_diagnostics.json`
  - включен в `plate_export_manifest.json` (`files.readinessDiagnostics`)
  - выводится marker в wrapper:
    - `MARKER_180.PARALLAX.PLATE_EXPORT.READINESS=<path>`

Назначение для multi-agent/REFLEX:

- Любой агент, запускающий `photo_parallax_plate_export.sh` или `photo_parallax_qwen_gated_multiplate_flow.sh`,
  получает одинаковый readiness-лог и может быстро различить:
  - инфраструктурный MCP issue;
  - headless export readiness issue.

Статус обновление (`2026-03-15`, truck-driver stability check):

- ✅ Выполнен `10x` прогон `truck-driver` через gated export wrapper.
- ✅ Результат: `10/10` успешных прогонов на уровне wrapper (после встроенных retries).
- ✅ Диагностика сохранена по каждому прогону:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports_qwen_gated/truck-driver/readiness_runs_2026-03-15/run_*.json`
- Профиль readiness:
  - `ready=true`: `10/10`
  - `attempts>1`: `4/10` (first-poll race)
  - `assetHydrateCalls>0`: `0/10`
  - main recovery path: `stageHydrate` (не asset fallback)
  - wrapper-level retry (`WARN_180...RETRY`): `3/10`

Статус обновление (`2026-03-18`, gated batch QA summary):

- ✅ Добавлен единый machine-readable batch QA artifact:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/gated_batch_qa_summary.json`
- QA summary агрегирует:
  - readiness diagnostics
  - gated render summary
  - compare summary
- Текущий итог по `hover-politsia`, `keyboard-hands`, `truck-driver`:
  - `overall_status = caution`
  - `pass = 0`
  - `caution = 3`
  - `fail = 0`
- Текущие причины caution:
  - `camera-safe gate is not fully satisfied`
  - для `truck-driver`: ещё и `readiness required more than one poll`

## 4) Playwright песочница: как работает

Песочница:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground`

Главный e2e exporter:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/e2e/parallax_plate_export.spec.ts`

Как запускать стабильный gated flow:

```bash
bash /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_qwen_gated_multiplate_flow.sh hover-politsia keyboard-hands truck-driver
```

Что делает wrapper:

1. plate export с `--apply-qwen-gate`
2. multi-plate render из экспортированных asset-ов
3. compare `manual vs gated-qwen`

Где смотреть результаты:

- exports:  
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports_qwen_gated`
- renders:  
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen_gated`
- compare:  
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate`

## 5) UI стиль и продуктовые правила

UI-референс документ:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/UI_RECON_AND_MONOCHROME_REDESIGN_2026-03-12.md`

Текущая политика:

- User-surface: минимальный depth-first pipeline (`Import -> Depth -> Isolate -> Camera -> Export`).
- Debug/research controls — только в скрытой dev panel.
- Монохромный интерфейс, без шумных акцентов.
- Не расширять основной UI новыми экспериментальными блоками без явной пользы.

Depth convention:

- Храним фиксированный внутренний язык глубины;
- `Invert` остается пользовательским инструментом;
- не делать насильственной глобальной нормализации для всех кейсов.

## 6) Ошибки, которые уже совершили (и не повторять)

1. Перепутали уровень задачи: пытались вылечить сложные сцены тюнингом одной глобальной depth-маски.
2. Раздули UI экспериментальными контролами до длинной ленты.
3. Смешивали понятия:
   - depth ordering,
   - plate decomposition,
   - inpaint.
4. Оценивали прогресс по edge-polish, когда главная проблема была object/plate structure.
5. Переоценивали raw AI proposal без gate.
6. Недооценили headless orchestration flakiness в Playwright экспорте.

Правильные коррекции уже приняты:

- `Qwen Gate`
- hidden dev controls
- retry/export hardening
- `camera-safe` contract

## 7) Текущие риски

1. `truck-driver` в manual export path иногда флапает по `sourceRasterReady`; в gated flow обычно проходит за счет retry.
2. Risk model пока first-pass (box/z-based), не full geometry graph.
3. Final render presets только что формализованы, но ещё не прогнаны как полноценный regression pack на всех sample.

## Update 2026-03-19 — PARALLAX v1.3 Final Render Presets

- В `photo_parallax_render_preview_multiplate.py` добавлены named presets:
  - `web`: `1280x720`, `25 fps`, `libx264`, `crf 24`
  - `social`: `1920x1080`, `30 fps`, `libx264`, `crf 20`
  - `quality`: `2560x1440`, `25 fps`, `libx264`, `crf 18`
- Summary/report теперь содержат:
  - `preset`
  - `render_settings`
  - `video.codec_name`
  - `video.bit_rate`
  - `file_size_bytes`
  - `validation.status/reasons`
- Для `web` и `social` summary автоматически пишется в отдельные поддиректории, чтобы не перетирать `quality`:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen_gated/web`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen_gated/social`
- Shell wrapper печатает:
  - `MARKER_180.PARALLAX.MULTIPLATE_RENDER.PRESET`
  - `MARKER_180.PARALLAX.MULTIPLATE_RENDER.DIR`
  - `MARKER_180.PARALLAX.MULTIPLATE_RENDER.SUMMARY`

## Update 2026-03-19 — PARALLAX v1.4 Regression Quality Pack

- Введён release-level aggregator:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_build_regression_quality_pack.py`
- Он агрегирует:
  - `gated_batch_qa_summary.json`
  - `render_compare_qwen_multiplate_summary.json`
  - preset summaries для `quality`, `web`, `social`
- Новый итоговый артефакт:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/regression_quality_summary.json`
- На каждый sample пишется:
  - `status = pass/caution/fail`
  - `reasons`
  - `preset_renders`
  - `evidence` с `manual vs gated-qwen` путями (`compare_sheet`, `compare_video`, mid-frames, preview paths)

## Update 2026-03-19 — PARALLAX v1.5 Service Extraction

- Из `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx` вынесены release-critical pure services:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/lib/plateLayout.ts`
- В модуле живут:
  - `recommendWorkflowRouting()`
  - `deriveParallaxStrength()`
  - `buildPlateLayoutContract()`
  - `buildPlateExportAssetsContract()`
- Добавлены unit tests:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/lib/plateLayout.test.ts`
- Проверка после выноса:
  - `cd photo_parallax_playground && npm test`
  - `cd photo_parallax_playground && npm run build`

## Update 2026-03-19 — PARALLAX v1.6 RC1 Packaging

- Добавлены release notes:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/RELEASE_NOTES_V1_RC1_2026-03-19.md`
- README теперь содержит `RC1 Runbook` и troubleshooting для:
  - readiness diagnostics
  - `cameraSafe.warning`
  - preset output layout
- RC1 smoke path остаётся canonical:
  - `bash /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_qwen_gated_multiplate_flow.sh hover-politsia keyboard-hands truck-driver`

## 8) Быстрый старт для нового чата

1. Прочитать:
   - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PHOTO_TO_PARALLAX_ROADMAP_CHECKLIST_2026-03-10.md`
   - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/HANDOFF_PHASE_180_2026-03-14.md`
2. Проверить актуальный gated compare summary:
   - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/render_compare_qwen_multiplate_summary.json`
3. Следующий implementation step:
   - auto-warning + motion suggestion из `cameraSafe`.
