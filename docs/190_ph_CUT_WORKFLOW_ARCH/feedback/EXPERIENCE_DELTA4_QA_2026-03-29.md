# Q6 Debrief — Delta-4 (QA)
**Date:** 2026-03-29
**Session:** worktree-cut-qa
**Tasks verified:** 25 (19 backlog + 5 new wave + 1 DOC_GATE_LAZY)
**Branches cleared:** claude/harness-eta, claude/harness, claude/cut-engine, claude/cut-ux, claude/cut-media, claude/cut-qa-2

---

## Q1 — Какие баги заметил? (включая чужие зоны)

**tb_1774675395 (DELTABUG)** — поле `merge_result: {success: false, error: "Merge failed: "}`
стоит на задаче как stale данные от предыдущей неудачной попытки cherry-pick.
Код на ветке цел, задача verified — но Капитану нужно знать при запуске merge_request на cut-engine:
если cherry-pick повторно упрётся в этот же конфликт, смотреть туда.

**test_include_untracked_never_in_task_board** — мой тест-гвард ложно срабатывал на
комментарий Эты `# no --include-untracked`. Исправил: фильтр по строкам не начинающимся с `#`.
Правило: assertion `not in source` для security-critical флагов нужно делать через
построчный фильтр, не грубым `in`.

**DOC_GATE_LAZY** — 2496 syscall на action=add из-за `stat().st_mtime` sort по всем .md файлам.
OpenCode получал MCP timeout -32001 три раза подряд. Эта зафиксил cap=400 + убрал sort.
Риск: если у кого-то в docs/ >400 файлов в нужной папке — важный файл может не попасть в glob.
Нужен более умный приоритет (по дате в имени файла, не по mtime).

**claude/cut-engine** содержит cut-ux коммиты в истории — ветка была ребазирована поверх
мёржа cut-ux. Хорошо что хеши коммитов в task board не совпадают с git log (это нормально
после rebase), но может путать при ручной отладке.

---

## Q2 — Что неожиданно сработало?

Git plumbing fixture для DOC_GUARD теста: `GIT_INDEX_FILE` + `commit-tree` создаёт
реальный fixture-коммит с удалением доков без единого `git checkout` и без касания
рабочего дерева. Ноль побочных эффектов. Это паттерн стоит задокументировать —
идеален для любых тестов где нужен "ветка с плохим состоянием" без риска испортить репо.

Epsilon во второй попытке правильно разделил: "xfail уже убран, вот доказательство +
33 новых contract теста вместо него". Нормальная реакция агента на QA reject.

---

## Q3 — Какая идея пришла, о которой никто не просил?

**CI step для test_phase201_stash_isolation.py** — запускать на каждый merge_request
в claude/harness-eta. Сейчас тесты лежат в tests/ но не прикреплены к pipeline.
Parallax incident случился потому что защита существовала только в виде конвенции,
не в виде автоматики. 29 тестов = 29 строк в CI — это дёшево.

**DOC_GATE smart priority**: вместо cap=400 по порядку файловой системы, приоритизировать
по номеру фазы в имени файла (`190_`, `200_` → свежее) и по длине совпадения с query.
Тогда cap не теряет важные новые доки.

---

## Q4 — Что сделал бы ещё с 2 часами?

Прогнал бы `python3 -m pytest tests/ -x -q` на main после всех мёржей этой волны —
проверить что 24 задачи не сломали ничего в тестовой пирамиде. Особенно:
- MARK-UNIFY (удалены поля store) может сломать тесты которые явно проверяют markIn/markOut
- MIXER_STATE добавляет новые timeline ops — стоит проверить что VALID_TIMELINE_OPS обновлён

---

## Q5 — Какие анти-паттерны увидел?

**"Phantom fix"** (Epsilon round 1): агент обновил текст xfail reason не прочитав
задачу до конца. QA reject → пересдача → правильный fix. Паттерн: когда задача говорит
"remove decorator" — нужно grep по файлу ПОСЛЕ изменения, не только смотреть diff.

**Commit hash drift**: task board хранит хеш в момент первого коммита, но ветка
потом ребазируется → хеши расходятся. Это нормально технически, но Delta при верификации
всегда должна делать `git log branch --oneline` а не доверять полю commit_hash в таске.

---

## Q6 — Самый большой риск прямо сейчас?

**claude/cut-engine** — ветка содержит 7+ задач включая MARK-UNIFY (удаление store fields)
и KF-BEZIER (новый canvas компонент). При мёрже возможен конфликт с cut-ux
(оба трогают useCutEditorStore.ts + CutEditorLayoutV2.tsx). Капитану рекомендую:
мёрж cut-ux → main ПЕРВЫМ, потом cut-engine (он уже ребазирован поверх cut-ux,
конфликтов должно быть меньше).

`tb_1774675395` (DELTABUG) имеет стоящий `merge_result: {success: false}` —
возможно предыдущий cherry-pick падал из-за конфликта в cut_routes.py.
Если merge_request снова упадёт — Alpha должен смотреть этот конфликт.
