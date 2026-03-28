# Experience Report: Epsilon-4 (QA-2) — 2026-03-25
**Agent:** Epsilon | **Branch:** claude/cut-qa-2 | **Session:** ~3 hours
**Role:** QA Engineer #2, Contract Tests, Architecture Audit, Sonnet Delegation
**Tasks closed:** 12 (9 Opus + 3 Sonnet) | **Commits:** 15 | **Specs written:** 327

---

## Q1: Что сломано? (включая чужие зоны)

### P1 — EFFECT_APPLY_MAP не экспортирован
**Файл:** `EffectsPanel.tsx:404` — `const EFFECT_APPLY_MAP` вместо `export const`.
**TimelineTrackView.tsx:25** делает `import { EFFECT_APPLY_MAP } from './EffectsPanel'`.
**Vite build проходит** (tree-shaking?), но runtime drag-drop эффектов на клипы сломан.
**Статус:** Задача `tb_1774310508_1` создана для Alpha. Alpha уже зафиксил в текущей сессии.

### P1 — Bootstrap POST /cut/bootstrap возвращает 500
Корректные параметры `source_path` + `sandbox_root` → 500 Internal Server Error.
Beta написал B54-B60 fix cascade на ветке `claude/cut-media`, но **бэкенд запущен со старого кода**.
Нужен merge + restart сервера. Живой тест подтвердил crash.

### P2 — ACTION_SCOPE пропущены 2 действия
`fiveFrameStepForward` и `addDefaultTransition` есть в CutHotkeyAction type и обоих пресетах, но **отсутствуют в ACTION_SCOPE**. Хоткеи срабатывают без panel scoping — могут стрелять в неправильном контексте.
**Статус:** Задача `tb_1774310498_1` создана для Alpha. Alpha уже зафиксил.

### P2 — 3 backend op handlers отсутствуют
Frontend корректно шлёт `set_effects`, `add_keyframe`, `remove_keyframe` через `applyTimelineOps`, но `_apply_timeline_ops()` в `cut_routes.py` не имеет обработчиков → `ValueError("unsupported timeline op")`.
**Статус:** Задача `tb_1774324550_1` создана для Beta.

### P3 — Playhead белый (#fff), а не красный (#cc3333)
GAMMA-POLISH1 задача требовала красный playhead. `playheadStyle()` в TimelineTrackView.tsx:123 возвращает `background: '#fff'`. Задача не выполнена.

---

## Q2: Что неожиданно сработало?

### Source-parsing contract tests — 327 спеков за 2.17 секунды
Парсинг TypeScript/CSS через regex вместо запуска браузера. Паттерн:
```python
def _find_impl(source, pattern): return bool(re.search(pattern, source))
def _find_near(source, anchor, target, window=60):  # target within N lines of anchor
```
**327 спеков покрывают**: хоткеи (82), layout (20+29), 5-point editing (39), bootstrap (13), visual regression (18), media pipeline (13), monochrome (94), tier markers (5), Playwright setup (14).

### `_find_near()` — proximity assertion
Проверяет что target появляется в пределах N строк от anchor. Ловит баги типа "handler существует, но никогда не вызывает applyTimelineOps". Сильнее чем просто проверка наличия функции.

### Sonnet-делегирование — 3 агента параллельно
Monochrome enforcement (94 specs), Test tier markers (5 specs), Playwright globalSetup (14 specs) — все три отработали корректно за ~2-4 минуты каждый. Zero false positives у monochrome scanner. Comment-stripping перед извлечением цветов = ключ.

### Двухуровневая стратегия тестирования
Source-parsing (всегда работает) + Live API (ловит реальные баги). Bootstrap source-parsing = 10 PASS (код корректен), Live API = 1 FAIL (сервер крашится). Оба уровня нужны.

---

## Q3: Идея которую не успел реализовать?

### Compliance Matrix как CI gate
```bash
pytest tests/test_fcp7_compliance_*.py | grep FAIL | wc -l
```
Число = количество открытых FCP7 gaps. Если число растёт между коммитами — блокировать merge. Dashboard прогресса к 100% compliance.

### Machine-readable compliance matrix
Вместо markdown таблицы — JSON/YAML файл с полями: `chapter`, `feature`, `status`, `test_file`, `test_name`. Тесты автоматически обновляют статус при прохождении. Один source of truth, не два (doc + тесты).

### Preset-as-contract
`presetBuilders.ts` мог бы экспортировать статический `PANEL_MANIFEST` объект — тесты проверяют без парсинга. Как JSON schema для workspace layouts.

---

## Q4: Какие инструменты понравились?

### Agent subagent_type=Explore
Быстрый рекон codebase за 30-60 секунд. Для 5-point editing pipeline и undo bypass audit — незаменим. Даёт полную картину: file:line, function name, call chain.

### Sonnet agents (model=sonnet) для параллельной работы
3 Sonnet-агента одновременно пишут тесты = 3x throughput. Каждый получает чёткий prompt с expected output format. Ключ: **не дублировать работу** — я делаю recon, Sonnet пишет implementation.

### `_parse_preset()` и `_extract_panels()` regex helpers
Переиспользуемые парсеры для TypeScript объектов. Работают на 100+ файлах. Паттерн nested regex: `(?:[^{}]|\{[^{}]*\})` для одного уровня вложенности.

### Live API testing с urllib.request
Без зависимости от `requests`. Thumbnail diff test (t=0 vs t=5) проверяет реальную экстракцию кадров, не просто наличие endpoint.

---

## Q5: Что НЕ повторять?

### Не верь FCP7 Compliance Matrix слепо
Матрица говорила "5 actions bypass applyTimelineOps". Реальность: Alpha уже зафиксил все 5 на фронтенде. Проблема была только в backend (3 missing ops). **Всегда проверяй код перед тем как верить документации.**

### Regex для backslash в pytest parametrize
`r"Ctrl+\\"` в Python string vs `Ctrl+\\` в TypeScript source — двойное экранирование. Потерял 5 минут на 2 теста. **Всегда проверяй raw string escaping** при тестировании строк с backslash.

### Не пиши docs в worktree
Первый раз написал RECON doc в main repo (правильно по memory rule), но closure_files не нашёл его в worktree. Пришлось `cp` в worktree для auto-commit. **Правило: docs → main, но closure_files нужен путь в worktree.**

### Import checker слишком наивный
Первая версия проверяла `resolved.with_suffix(ext).exists()` — не работало для `../../config/api.config` (имя файла уже содержит `.config`). Fix: `Path(str(resolved) + ext).exists()`. **Всегда тестируй path resolution на реальных import paths.**

---

## Q6: Неожиданные идеи не по теме?

### CUT как CI/CD для видео
Если compliance matrix + contract tests + monochrome enforcement запускаются автоматически — CUT становится первым NLE с continuous quality pipeline. Каждый коммит проходит:
1. Vite build (7.85s)
2. 327 contract tests (2.17s)
3. Monochrome scan (0.12s)
4. Live API smoke (1.16s)

**Total: 11s per commit.** Ни один NLE этого не имеет.

### "Debrief-as-test" автоматизация
Вместо 6 вопросов агенту — Playwright скрипт: после каждого merge проверяет console errors, color violations, dead imports, empty src attributes, seek boundary violations. Delta-2 это предлагал — но никто не реализовал. Мой monochrome scanner — первый шаг.

### Op-type registry как контракт
`_apply_timeline_ops()` в cut_routes.py — это фактически RPC dispatcher. Список поддерживаемых op_type должен быть **объявлен как enum**, а не разбросан по if/elif. Frontend и backend расходятся (frontend шлёт ops которые backend не понимает). **Shared op-type registry** (один JSON/enum файл, оба стека импортируют) решил бы это навсегда.

---

## Session Stats

| Metric | Value |
|--------|-------|
| Tasks closed | 12 (9 Opus + 3 Sonnet) |
| Test files created | 9 |
| Total specs written | 327 |
| GREEN specs | 308 (final regression) |
| FAIL (real bugs) | 2 (ACTION_SCOPE + EFFECT_APPLY_MAP) |
| XFAIL (documented) | 4 (undo bypass + N collision + playhead) |
| Recon docs | 3 (FCP7 Timeline Display, Undo Bypass Audit, Compliance Matrix) |
| Bug tasks created | 3 (Alpha x2, Beta x1) |
| Vite build | SUCCESS (7.85s) |
| Pytest baseline | 3741 PASS / 25 FAIL (pre-existing) |
| Live API tests | Thumbnail PASS, Waveform PASS, Audio PASS, Bootstrap FAIL (500) |
| Sonnet agents used | 3 (monochrome, tiers, Playwright globalSetup) |

## Commits (15 total on claude/cut-qa-2)

1. `3318fa0d` — Hotkey regression suite (82 specs)
2. `079f9531` — Gamma layout audit verification (20 specs)
3. `94f6539e` — Workspace preset builders contract (29 specs)
4. `afad67c9` — 5-point editing pipeline (39 specs)
5. `7ed5441b` — Bootstrap graceful recovery (13 specs)
6. `5af6accb` — GAMMA-POLISH1 visual regression (18 specs)
7. `9e396c4a` — Playback backend live MOV (13 specs)
8. `11a07437` — FCP7 Timeline Display Options recon doc
9. `0e5b451b` — Undo bypass audit recon doc
10. `47617696` — Monochrome enforcement scanner (94 specs, Sonnet)
11. `2ed3904e` — Test tier markers (5 specs, Sonnet)
12. `f1ce8d9a` — Shared Playwright globalSetup (14 specs, Sonnet)

## Recommendations for Next Epsilon

1. **Run `vite build` + full pytest BEFORE any work** — baseline shifts constantly
2. **Use `_find_near()` pattern** — proximity checks catch wiring bugs that existence checks miss
3. **Delegate to Sonnet** for mechanical tasks (scanning, infra) — save Opus context for analysis
4. **Check code before trusting docs** — compliance matrix was stale for 5 actions
5. **Two-tier tests** — source-parsing always + live API when backend available
6. **Path resolution for imports** — use `str(resolved) + ext` not `resolved.with_suffix(ext)`

---

*"Test the contract, not the implementation. But verify the implementation matches the contract."*
