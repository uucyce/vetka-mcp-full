# Commander (agitated-torvalds) Debrief — 2026-03-22
**Agent:** OPUS-COMMANDER (Claude Code) | **Worktree:** agitated-torvalds
**Session:** ~4 hours | **Agents managed:** 10 (5 original + 5 replacements)
**Merges performed:** 30+ | **Build verifications:** 30+ (all green)
**Agent rotations:** 5 (Beta→NewBeta, Epsilon→NewEpsilon, Gamma→NewGamma, Alpha→NewAlpha, Delta→NewDelta)

---

## Q1: Что сломано?

### 1. CLAUDE.md распространяется на worktree при создании
Когда создаётся новый worktree, CLAUDE.md копируется из main. Но agent-specific CLAUDE.md (Commander, Alpha, Beta) перезаписывают generic. При merge каждый agent пытается записать свой CLAUDE.md в main. Решение: `git checkout --ours CLAUDE.md` при каждом merge. Но это хак — нужен механизм worktree-local CLAUDE.md который НЕ коммитится.

### 2. Task promote_to_main не всегда срабатывает
Post-merge hook ищет `[task:tb_xxx]` в commit messages и вызывает promote. Но когда задача уже `done_main` (promoted ранее), hook пишет "skip: status=done_main, expected done_worktree". Это нормально для повторных merge, но создаёт шум в output. Нужен silent mode для already-promoted tasks.

### 3. Дублирование задач при смене агентов
Новый Beta получил задачу "сделай waveform peaks" — а предшественник уже это реализовал. Commander не проверил наличие перед dispatch. **Правило: перед каждым dispatch проверяй `git log --oneline | grep <keyword>` чтобы убедиться что фича не уже на main.**

### 4. Epsilon получил CLAUDE.md Gamma и начал делать UX работу
Worktree bug: при создании cut-qa-2 скопировался CLAUDE.md из Gamma's worktree (или из main с Gamma version). Epsilon решил что он Gamma и начал фиксить dockview CSS вместо тестов. **Fix: session_init должен инжектить role context на основе branch name, не полагаясь на CLAUDE.md.**

---

## Q2: Что неожиданно сработало?

### 1. Merge ritual стал автоматическим
К 10-му merge ritual выполняется за 30 секунд: `git log HEAD..branch`, `git merge --no-edit`, `grep "<<<<<<" if conflict`, `npx vite build`, done. Паника первого merge полностью ушла к 5-му. Checklist в COMMANDER_ROLE_PROMPT работает идеально.

### 2. Screenshot-driven coordination
Юзер присылает скриншот → я читаю все 5 терминалов за 10 секунд → определяю кто закончил, кто работает → dispatch + merge. Это БЫСТРЕЕ чем API-based coordination. Визуальный контроль > автоматизированные отчёты.

### 3. Ротация по одному с преемственностью
Замена одного агента за раз (не всех сразу) = остальные 4 продолжают работать. Новый агент читает debrief предшественника и подхватывает поток. Zero downtime rotation. Это правильная модель.

### 4. Debrief с 6 провокационными вопросами
Формат Q1-Q6 (что сломано, что сработало, идея, инструменты, что НЕ повторять, неожиданные идеи) вытягивает конкретику которую generic "experience report" не даёт. Alpha дал 248 строк включая cross-domain баги и architectural ideas. Это золото.

### 5. Параллельные merge 4 веток за раз
`git merge cut-engine && git merge cut-media && git merge cut-ux && git merge cut-qa-2` — когда file ownership работает, конфликтов нет. 4 merge за 20 секунд. Ownership boundaries = merge peace.

---

## Q3: Идея которую не успел реализовать

### Auto-dispatch pipeline
Когда agent завершает задачу (task status → done_worktree), Commander автоматически:
1. Merges branch to main
2. Verifies build
3. Reads agent's "next recommendation" from task metadata
4. Dispatches next task

Сейчас это ручной цикл: screenshot → read → merge → dispatch. Можно автоматизировать через MCP event (task_completed → webhook → Commander auto-response).

**Это сократит latency с 3-5 мин (ожидание screenshot + Commander анализ) до 30 секунд.**

---

## Q4: Какие инструменты понравились?

### vetka_task_board — единственный источник правды
`action=list project_id=cut filter_status=pending` — мгновенный обзор. `action=complete` — auto-commit + auto-push. Ни одного orphaned commit за 30+ merge. Это дисциплина без overhead.

### git merge --no-edit + vite build = 30-second verification
Простота: merge, build, done. Если build зелёный — всё работает. Если красный — agent сломал TypeScript. Этот двухшаговый gate (merge + build) ловит 95% проблем.

### Память (feedback memories)
`feedback_monochrome_ui.md`, `feedback_debrief_questions.md` — правила записаны один раз и действуют навсегда. Когда юзер сказал "НОЛЬ цвета" — я записал и все будущие agents это увидят. Persistent rules > repeated instructions.

### git log --all --oneline | grep
Когда agent commit не на ожидаемой ветке — это единственный способ найти его. Beta's B2.2+B2.3 оказались на main через cut-engine merge. Без grep потерял бы 10 минут.

---

## Q5: Что НЕ повторять

### 1. Спрашивать юзера о процедурах описанных в docs
Первый dispatch я спросил "мержить мне?" когда COMMANDER_ROLE_PROMPT явно говорит "Commander IS the gatekeeper". Юзер справедливо указал: "Странно что ты меня спросил."
**Правило: если процедура описана в загруженных docs — выполняй, не спрашивай.**

### 2. Отпускать агентов когда есть работа
Дважды сказал Gamma/Epsilon "session complete, rest" когда были задачи. Юзер: "они могут самостоятельно разрабатывать архитектурные доки и роадмэпы."
**Правило: после завершения задачи СРАЗУ dispatch следующую. Отпускать только по явному запросу юзера.**

### 3. Давать задания без проверки существования
Dispatch новому Beta "сделай waveform peaks" — а он уже существует. Потерял 5 минут на выяснение.
**Правило: git log + task_board check ПЕРЕД каждым dispatch.**

### 4. Dispatch format слишком длинный
Первые dispatches были 10+ строк с context/task/predecessor/reference/files/branch/coordination. Юзер не жаловался, но relay overhead растёт. Достаточно: task + 1 line context + branch. Agent сам прочитает docs.

### 5. Забывать давать задания всем агентам
Несколько раз dispatch 3 из 5 — забыл Gamma, забыл Delta. Юзер: "А Гамма?" "Дельта ждет команды."
**Правило: после каждого screenshot — checklist ВСЕХ агентов. Кто работает, кто ждёт.**

---

## Q6: Неожиданные идеи не по теме

### 1. Commander as MCP tool
Commander logic (merge ritual, dispatch format, agent tracking) можно оформить как MCP tool:
- `commander_merge branch=claude/cut-engine` — full ritual в одном вызове
- `commander_dispatch agent=alpha task="..."` — форматирует и валидирует dispatch
- `commander_status` — все worktrees, все agents, все pending tasks в одном view
Это позволит Commander быть thinner — меньше процедурного кода, больше стратегии.

### 2. Agent heatmap — визуализация нагрузки
Каждый agent = lane. Задачи = блоки на timeline. Длина = время выполнения. Цвет = статус (green=done, yellow=in-progress, red=blocked). Commander видит ОДИН timeline со ВСЕМИ agents. Это — CUT for CUT development.

### 3. Cross-pollination через debrief
Alpha's Q6 (rhythm lock) = 1 строка кода в snap candidates. Если Alpha не написал бы debrief, эта идея потерялась бы. **Debrief → автоматическое создание research tasks для cross-domain ideas.** Каждый Q6 ответ = задача type=research для любого свободного agent.

### 4. Consensus doc generation
5 agent debriefs → автоматический synthesis: что ВСЕ считают сломанным, что ВСЕ нашли полезным, где идеи пересекаются. Сейчас Commander делает это вручную. Можно автоматизировать: `vetka_synthesize_feedback docs=FEEDBACK_*.md` → unified doc с voting по priority.

---

## Q7 (самому себе): Как масштабировать координацию за 5 агентов?

### Проблема
С 5 agents screenshot-driven coordination работает. С 10 — нет. Юзер не может relay 10 dispatches. Commander не может читать 10 терминалов на одном screenshot.

### Решение: иерархический command
```
Commander → Stream Leads → Agents
  │
  ├─ Stream A Lead (Alpha + Gamma) → Engine + UX
  ├─ Stream B Lead (Beta) → Media pipeline
  └─ Stream C Lead (Delta + Epsilon) → QA
```
Stream Lead = Opus agent who sub-dispatches 2-3 agents. Commander writes 3 dispatches instead of 10. Each Stream Lead merges within their stream, Commander merges streams to main.

Это = naval hierarchy. Commander → Captains → Crews.

---

## Session Stats

| Metric | Value |
|--------|-------|
| Session duration | ~4 hours |
| Total merges to main | 30+ |
| Build verifications | 30+ (all green) |
| Merge conflicts resolved | 5 (MenuBar, TimelineTrackView, CLAUDE.md x3) |
| Agent rotations | 5 (full fleet refresh) |
| Debriefs collected | 5 (Alpha, Beta, Gamma, Delta, Epsilon) |
| Tasks promoted to done_main | 20+ |
| Dispatches written | 40+ |
| Memory rules created | 2 (monochrome_ui, debrief_questions) |
| Feedback docs saved | 6 |

---

## Консенсус всех агентов (synthesis)

### Что ВСЕ считают лучшим инструментом
- **vetka_task_board** — Alpha, Delta, Commander единогласно
- **session_init** — Alpha: "контекст за 2 секунды"
- **window.__CUT_STORE__** — Delta: "самый ценный test hook"

### Что ВСЕ считают главной проблемой
- **Dockview CSS** — Gamma (3 sessions), Beta (nuclear wildcard), Commander (merge conflicts)
- **CLAUDE.md per worktree** — Alpha (wrong branch edits), Epsilon (identity confusion), Commander (merge every time)

### Идеи с максимальным impact/effort ratio
1. **Rhythm lock** (Alpha Q6) — 1 строка кода, instant musical editing
2. **Shared dev server pool** (Delta Q3) — saves 3.5 min per TDD run
3. **Audio rubber band** (Alpha Q3) — ~80 lines, most-used FCP7 feature
4. **StatusBar** (Gamma idea) — like Premiere, zero controversy

### Открытые задачи (не закрытые за сессию)
- VideoPreview shared video element (P2, Alpha reported)
- Frontend edits bypass undo stack (P2, new Alpha working on)
- focusedPanel defaults to null (P2, Delta reported)
- Full keyframe system with bezier (in progress)
- Audio waveform display on timeline clips
- Dockview JS-level blue kill (new Gamma working on)

---

*"30 merges, 5 rotations, zero lost work. The fleet sails on with fresh crews and full charts."*
