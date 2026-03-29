# Handoff To Fresh Chat After UI Reset Planning

Дата фиксации: `2026-03-29`
Статус: `ready for fresh chat`

## 1. Current Branch And Worktree

- worktree root:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex`
- app root:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex/photo_parallax_playground`
- branch:
  - `codex/parallax`

## 2. Canonical Docs To Read First

Новый чат должен начинаться с этих документов:

1. `PARALLAX_PRODUCT_UI_RESET_PROJECT_2026-03-29.md`
2. `PARALLAX_ROADMAP_RC1_COMPLETION_AND_LAYERED_BAKEOFF_2026-03-19.md`
3. `PARALLAX_PLAYGROUND_CONTROL_RECON_2026-03-29.md`
4. `PARALLAX_OBJECT_CENTRIC_PARALLAX_ARCHITECTURE_2026-03-28.md`
5. `PARALLAX_PLAYGROUND_UI_REFACTOR_PROJECT_2026-03-28.md`

## 3. Factual Product Reset

На `2026-03-29` операторский review подтвердил:

- current UI still speaks prototype language instead of pro-app language;
- `Import` должен быть ближе к `Media Pool / Project`;
- `Depth` должен быть ближе к `DaVinci Resolve AI Depth Map`;
- `Scene Plan` должен быть коротким list/checklist;
- нижний `Inspector` не должен занимать большой экранный вес, если он не даёт понятных edits;
- `Advanced Cleanup`, `Guided Hints`, `Hint Brushes`, `Layer Guides`, `AI Assist`, `Debug Snapshot` не должны жить как always-open default surface;
- portrait / non-16:9 sources должны целиком помещаться по умолчанию.

## 4. Verified Current UI State

Последний свежий live check шёл через:

- `http://127.0.0.1:14350/?sample=hover-politsia&debug=1&fresh=1`

Важно:

- пользователь часто смотрел stale ports `14348` и `14349`;
- если экран кажется "почти не меняется", сначала проверить, что открыт именно `14350` или новый свежий port текущего worktree.

## 5. Completed Waves Before Reset

До product reset уже были сделаны:

- viewer-first shell
- four-step flow
- advanced cleanup demotion
- draft plate path for missing objects
- first draft fit refinement
- semantic compression for `Depth / Extract / Camera`
- semantic compression for `Inspector / Scene Plan`
- wording cleanup for operator language

Эти шаги остаются полезными, но теперь должны переоцениваться через новый product reset.

## 6. Next Ordered Waves

Следующие задачи уже созданы и должны идти строго по порядку:

1. `PARALLAX-UIR7`
   - remove default-screen prototype noise
2. `PARALLAX-UIR8`
   - rebuild `Depth` around Resolve-like mental model
3. `PARALLAX-UIR9`
   - simplify `Import` into source-list mental model
4. `PARALLAX-UIR10`
   - demote or convert `Inspector`
5. `PARALLAX-UIR11`
   - shrink `Scene Plan` into concise list
6. `PARALLAX-UIR12`
   - fix portrait-safe stage fit
7. `PARALLAX-UIR13`
   - rebuild `Advanced Cleanup` as collapsible tool stack

## 7. Critical Constraint

Все следующие UI waves пересекаются по:

- `photo_parallax_playground/src/App.tsx`
- `photo_parallax_playground/src/index.css`

Следовательно:

- эти задачи нельзя безопасно гнать параллельно;
- выполнять их нужно `волна за волной`, последовательно.

## 8. Recommended Next Step In Fresh Chat

Первый task в новом чате:

- `PARALLAX-UIR7`

Почему:

- он расчистит default screen;
- после него будет проще и безопаснее перестроить `Depth`, `Import`, `Scene Plan` и `Advanced Cleanup` уже в новом продуктовом языке.
