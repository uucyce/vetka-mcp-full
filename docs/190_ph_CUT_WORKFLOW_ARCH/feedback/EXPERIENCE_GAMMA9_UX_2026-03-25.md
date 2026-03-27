# Gamma-9 UX/Panel Architect — Final Debrief
**Date:** 2026-03-25
**Agent:** OPUS-GAMMA-9 (claude/cut-ux)
**Session:** 14 commits, 20+ tasks processed
**Duration:** 2 sessions across 2026-03-24 → 2026-03-25

---

## Q1: Что сломано?

**EFFECT_APPLY_MAP не был экспортирован из EffectsPanel.tsx** — pre-existing build blocker. TimelineTrackView.tsx импортировал `EFFECT_APPLY_MAP` который был `const` (не `export const`). Vite build падал. Никто не заметил потому что `vite build` не запускался между сессиями. **Урок: первые 5 секунд каждой сессии = `vite build`.**

**33 CSS селектора в dockview-cut-theme.css были глобально unscoped.** `[data-tooltip]::after` создавал floating pseudo-element с z-index:100 на ЛЮБОМ элементе страницы с data-tooltip. `[data-active-tool="razor"]` менял cursor на crosshair глобально. Это не падало но создавало невидимые side-effects. **Урок: CSS без scope = бомба замедленного действия.**

**ROADMAP_A4_PULSE_INTEGRATION.md (Alpha-3) содержит устаревшую информацию.** Документ говорит "PulseInspector NOT mounted", "StorySpace3D NOT mounted", "AutoMontagePanel NO wiring" — всё это уже сделано. Документ не обновлён после работы Gamma-6/7/8. **Урок: roadmap-документы устаревают быстрее кода.**

**Чужая зона:** `dropMediaOnTimeline` использует `DEFAULT_CLIP_DURATION = 5` секунд (placeholder). Реальная duration из probe не подставляется. Клипы на таймлайне все одинаковой длины. Alpha domain.

---

## Q2: Что неожиданно сработало?

**Sonnet-субагенты для чтения файлов — 3x экономия времени.** ExportDialog.tsx (978 строк), DAGProjectPanel.tsx (435 строк), TimelineTrackView.tsx (2800+ строк) — каждый прочитан Sonnet-агентом за 15-60 секунд с полным структурированным отчётом. Я не тратил контекст на чтение гигантских файлов. **Паттерн: Opus думает, Sonnet читает.**

**withTestId HOC на уровне registry** — одна функция, 17 панелей получили data-testid. Ноль правок в отдельных файлах. `Object.entries(PANEL_COMPONENTS).map(([id, Comp]) => withTestId(id, Comp))` — самый эффективный подход для cross-cutting concerns в dockview.

**Python regex batch replace для CSS scoping** — 33 селектора за один проход:
```python
re.sub(r'^(\[data-testid)', r'.dockview-theme-dark \1', content, flags=re.MULTILINE)
```

**~50% задач были "уже сделаны"** — Gamma-8 сделал огромный рывок (31 коммит). Проверка перед кодированием (grep imports → check PANEL_COMPONENTS → verify store defaults) сэкономила часы. **Паттерн: verify-before-code.**

---

## Q3: Идея которую не успел реализовать?

**PulseInspector energy sparkline.** Миниатюрный timeline всех сцен как точки, текущая сцена highlighted. Монтажёр видит ритмический профиль фильма одним взглядом — где пики энергии, где провалы. Данные уже есть в backend (POST /pulse/energy-critics). Нужно ~50 строк SVG.

**Automated dead code detector.** Glob все .tsx → grep кто их импортирует → если 0 импортов = мёртвый код. Gamma-8 удалил 9 файлов / 39K, я удалил TransitionsPanel.tsx. Автоматизация найдёт остальное. Pre-commit hook формат.

**CSS scope linter.** Reject любой `[data-testid=` селектор без `.dockview-theme-dark` prefix в dockview-cut-theme.css. Мог бы быть pre-commit hook. Предотвращает регрессию моего CSS isolation fix.

---

## Q4: Какие инструменты понравились?

1. **Sonnet Explore subagents** — делегирование чтения файлов. `model: "sonnet"` + `subagent_type: "Explore"`. Быстро, точно, не ест мой контекст. Использовал 5 раз за сессию.

2. **vetka_task_board action=complete с auto-commit** — `closure_files` + `branch` = staging + commit + close в одном вызове. Ни разу не делал `git add` / `git commit` вручную. Pipeline работает.

3. **`npx vite build`** как верификация — 5 секунд, ловит import errors, type errors, missing exports. Запускал после каждого изменения. Ни один битый коммит.

4. **PRESET_BUILDERS registry pattern** — добавить workspace = написать одну функцию + одна строка в Record. Масштабируется бесконечно.

5. **Python one-liner для batch CSS fix** — быстрее чем 33 ручных Edit вызова.

---

## Q5: Что НЕ повторять?

1. **Не claim задачу без проверки "уже сделано".** 50% задач были выполнены предшественниками. Потратил время на claim → read → verify → close as done. **Правило: grep перед claim.**

2. **Не доверять описанию задачи.** Описание tb_1774311892_1 говорит "PulseInspector NOT mounted" — это ложь, компонент давно в dockview. Описание tb_1774311976_1 говорит "no cancel button" — cancel + ETA уже реализованы. **Правило: verify code, not task description.**

3. **Не создавать задачи для чужих зон без пометки.** Мои задачи WAVE1/THUMB1 были помечены "GAMMA" но требовали TimelineTrackView.tsx (Alpha blocked). Потеря времени при claim. **Правило: allowed_paths должен совпадать с owned_paths агента.**

4. **Не запускать `npx vite build` из корня проекта** — нужен `cd client`. Из корня = "Cannot resolve entry module index.html". Потратил 30 секунд на диагностику.

5. **Не использовать `@layer` в Vite CSS.** Gamma-6 уже обжёгся — Vite не поддерживает `@import url() layer()`. `!important` + hardcoded hex = прагматичное решение.

---

## Q6: Неожиданные идеи не по теме?

**1. "Conforming panel" — visual timeline diff между двумя cuts.**
DAG-native: у нас есть multiple timeline projections (cut-00, cut-01, cut-02). Показать DIFF между ними — какие клипы добавлены/удалены/перемещены. Ни один NLE этого не делает. Git diff для видеомонтажа. Визуализация: два таймлайна stacked, совпадения серые, различия highlighted.

**2. PULSE как CI metric.**
`pytest tests/test_fcp7_tdd_red_gaps.py | grep FAIL | wc -l` = число открытых FCP7 gaps. Добавить: `pulse_compliance_score` = процент сцен с energy/camelot/pendulum заполненными. Dashboard: FCP7 coverage + PULSE coverage + build status. Merge gate: "PULSE coverage must not decrease."

**3. Store field ownership registry.**
useCutEditorStore.ts = 1419 строк, shared между Alpha/Gamma/Beta. Конфликты неизбежны. Идея: JSDoc `@owner Alpha` на каждом поле. Lint rule: agent не может менять поле с чужим `@owner`. Предотвращает cross-domain store corruption.

**4. Workspace preset auto-save.**
Пользователь двигает панели → при следующем Cmd+Q (quit) → авто-сохранение текущего layout как "custom". Без явного Save. При открытии → восстановление последнего layout. Premiere Pro так делает. Dockview уже поддерживает serialize/deserialize.

---

## Session Statistics

| Metric | Value |
|--------|-------|
| Commits | 14 |
| Tasks claimed | 20+ |
| Tasks completed (code) | 10 |
| Tasks verified (already done) | 10+ |
| New files created | 3 (MatchSequencePopup, PublishPanel, ROADMAP_PULSE_UI) |
| Files modified | 12 |
| Files deleted | 1 (TransitionsPanel.tsx) |
| CSS selectors scoped | 33 |
| Panels tagged with testid | 17 |
| Build verifications | 14 (one per commit) |
| Sonnet subagents used | 5 |
| Tasks created for other agents | 3 (Alpha PW-1, PW-2, PW-8) |

---

*"Check before you build. Half the work was already done. The other half was CSS."*
