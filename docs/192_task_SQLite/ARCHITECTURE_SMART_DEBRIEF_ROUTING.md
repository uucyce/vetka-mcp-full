# Architecture: Smart Debrief — Trigger Routing + Auto-Task Creation
**Phase:** 195+ (Agent Infrastructure — Zeta)
**Date:** 2026-03-22
**Author:** Opus (Zeta)
**Status:** ARCHITECTURE

---

## Problem Statement

Текущий debrief:
- Protocol Guard: `"Completed 3 task(s) but no experience report submitted."` — сухо, игнорируется
- Auto-hook: собирает метрики, но не качественные инсайты
- D5 (Sigma): structured questions при закрытии фазы — правильная идея, но вопросы слишком generic

**Что теряется:**
- Баги, найденные случайно в чужой зоне ("хлам мимо которого все ходят")
- Идеи, которые пришли в процессе работы и о которых никто не спросил
- Workarounds, которые должны стать стандартом
- Наблюдения про инструменты, процесс, UX

**Что нужно:**
1. Конкретные провокационные вопросы (не "напиши отчёт")
2. Автоматическое создание задач из ответов (баг → research task)
3. Маршрутизация ответов в правильные подсистемы памяти (CORTEX, ENGRAM, AURA, REFLEX, MGC)

---

## Design: Three Layers

### Layer 1: Smart Questions (вместо generic debrief)

```
┌────────────────────────────────────────────────────────┐
│  SMART DEBRIEF — Перед выходом, 3 вопроса (2-3 строки) │
│                                                        │
│  Q1: БАГИ И ХЛАМ                                       │
│  "Что сломано или мешает? Может заметил проблемы       │
│  за пределами своей зоны — баг в чужом файле,          │
│  устаревший код, неработающий tool, кривой процесс?"   │
│                                                        │
│  Q2: ЧТО СРАБОТАЛО НЕОЖИДАННО                          │
│  "Какой workaround, паттерн или подход неожиданно      │
│  оказался эффективным? Что стоит сделать стандартом?"  │
│                                                        │
│  Q3: ИДЕЯ, О КОТОРОЙ НЕ СПРАШИВАЛИ                     │
│  "Какая идея пришла в процессе работы, которую         │
│  никто не просил и ты не успел реализовать?            │
│  Что бы ты сделал, если бы было ещё 2 часа?"          │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### Layer 2: Auto-Task Creation (ответ → задача)

```
Q1 answer (баг/хлам):
  → vetka_task_board action=add
    title="[DEBRIEF-BUG] {краткое описание}"
    phase_type=research
    priority=3
    tags=["debrief-auto", "architect-review"]
    force_no_docs=true  ← research, без дока
    description="Обнаружено агентом {callsign} при работе над {task_title}.
                 Не в зоне ответственности агента — нужен ревью архитектора.
                 Контекст: {полный ответ Q1}"

Q3 answer (идея):
  → vetka_task_board action=add
    title="[DEBRIEF-IDEA] {краткое описание}"
    phase_type=research
    priority=4
    tags=["debrief-auto", "architect-review", "idea"]
    force_no_docs=true
    description="Идея от агента {callsign}: {полный ответ Q3}"
```

Q2 (что сработало) → НЕ создаёт задачу, а маршрутизируется в память.

### Layer 3: Memory Routing (ответ → подсистема памяти)

```
┌─────────────────────────────────────────────────────────────┐
│               TRIGGER-BASED MEMORY ROUTING                   │
│                                                             │
│  Ответ агента проходит через серию "мышеловок":             │
│                                                             │
│  ┌──────────┐                                               │
│  │ REFLEX   │  Триггер: упоминание tool name                │
│  │          │  "vetka_read_file сломан" → CORTEX feedback    │
│  │          │  "Read работает лучше" → CORTEX positive       │
│  │          │  Паттерн: /vetka_\w+|Read|Edit|Grep|Bash/     │
│  └──────────┘                                               │
│                                                             │
│  ┌──────────┐                                               │
│  │ AURA     │  Триггер: "пользователь", "user", "юзер"     │
│  │          │  "пользователь не видит warnings" → AURA UX   │
│  │          │  Паттерн: /user|пользовател|юзер|UI|UX/i      │
│  └──────────┘                                               │
│                                                             │
│  ┌──────────┐                                               │
│  │ MGC      │  Триггер: упоминание file path                │
│  │          │  "task_board.py:847 — branch detection"        │
│  │          │  → MGC hot file marker                         │
│  │          │  Паттерн: /\w+\.(py|ts|tsx|js|yaml|json)/     │
│  └──────────┘                                               │
│                                                             │
│  ┌──────────┐                                               │
│  │ ENGRAM   │  Триггер: паттерн/рецепт/принцип              │
│  │          │  "effective* variable pattern enables..."      │
│  │          │  → ENGRAM learning entry                       │
│  │          │  Паттерн: /паттерн|pattern|принцип|always|     │
│  │          │   never|лучше|хуже|эффективн/i                │
│  └──────────┘                                               │
│                                                             │
│  ┌──────────┐                                               │
│  │ CORTEX   │  Всё остальное → general feedback entry       │
│  │          │  Fallback: если ни один триггер не сработал    │
│  └──────────┘                                               │
│                                                             │
│  Маршрутизация детерминированная (regex), без LLM calls.    │
│  Один ответ может триггерить НЕСКОЛЬКО подсистем.           │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation

### Where It Triggers

**Primary:** При вызове `vetka_task_board action=complete` — если `should_trigger_debrief()`:
- Последний таск фазы (0 remaining pending для этого project_id + assigned_to)
- Или сессия длинная (>2 часов)
- Или много friction (≥3 fallback patterns)

**Response includes:**
```json
{
  "success": true,
  "task_id": "tb_xxx",
  "status": "done",
  "debrief_requested": true,
  "debrief_questions": {
    "q1_bugs": "Что сломано или мешает? Баги за пределами твоей зоны — устаревший код, неработающий tool, кривой процесс?",
    "q2_worked": "Какой workaround или подход неожиданно оказался эффективным? Что стоит сделать стандартом?",
    "q3_idea": "Какая идея пришла в процессе, о которой никто не спрашивал? Что бы ты сделал, если бы было ещё 2 часа?"
  }
}
```

**Agent answers via:**
```
vetka_submit_experience_report
  lessons_learned=["Q1: ...", "Q2: ..."]
  recommendations=["Q3: ..."]
```

### Processing Pipeline

```python
def process_smart_debrief(report: ExperienceReport, task_board):
    """Route debrief answers to memory + auto-create tasks."""

    for lesson in report.lessons_learned:
        # Q1: Bug/mess → auto-create research task
        if _is_bug_report(lesson):
            task_board.add_task(
                title=f"[DEBRIEF-BUG] {_extract_summary(lesson, 60)}",
                description=f"Обнаружено агентом {report.agent_callsign}.\n\n{lesson}",
                phase_type="research",
                priority=3,
                tags=["debrief-auto", "architect-review"],
                force_no_docs=True,
            )

        # Route to memory subsystems
        _route_to_memory(lesson, report)

    for rec in report.recommendations:
        # Q3: Idea → auto-create research task
        task_board.add_task(
            title=f"[DEBRIEF-IDEA] {_extract_summary(rec, 60)}",
            description=f"Идея от {report.agent_callsign}.\n\n{rec}",
            phase_type="research",
            priority=4,
            tags=["debrief-auto", "architect-review", "idea"],
            force_no_docs=True,
        )

        _route_to_memory(rec, report)


def _route_to_memory(text: str, report: ExperienceReport):
    """Trigger-based routing to memory subsystems."""
    import re

    # REFLEX: tool mentions → CORTEX feedback
    tool_matches = re.findall(r'vetka_\w+|Read|Edit|Grep|Bash|Write', text)
    if tool_matches:
        for tool in set(tool_matches):
            _record_cortex_feedback(tool, text, report)

    # AURA: user/UX mentions
    if re.search(r'user|пользовател|юзер|UI|UX', text, re.IGNORECASE):
        _record_aura_insight(text, report)

    # MGC: file path mentions → hot file marker
    file_matches = re.findall(r'[\w/]+\.(py|ts|tsx|js|yaml|json|md)', text)
    if file_matches:
        for file_path in set(file_matches):
            _mark_mgc_hot_file(file_path, text)

    # ENGRAM: pattern/principle mentions
    if re.search(r'паттерн|pattern|принцип|always|never|лучше|хуже|эффективн', text, re.IGNORECASE):
        _record_engram_learning(text, report)
```

---

## Example: What Would Zeta's Debrief Look Like?

If this system existed when I (Zeta) was asked "что заметил?":

**Q1 (баги):**
```
1. task_board.py:847 _detect_current_branch() использует cwd=PROJECT_ROOT,
   что всегда возвращает main из worktree. Агенты вынуждены передавать
   branch= вручную. Это системный баг, а не feature.

2. API тесты (test_phase121) пишут в prod task_board.db — каждый pytest
   создаёт 5-6 мусорных задач. conftest.py нужен tmpdir override.
```

→ **Auto-creates:**
- `[DEBRIEF-BUG] _detect_current_branch() returns main from worktree` (P3, research)
- `[DEBRIEF-BUG] API tests pollute prod task_board.db` (P3, research)

→ **Routes to:**
- MGC: `task_board.py` → hot file marker
- REFLEX/CORTEX: negative feedback for `_detect_current_branch`
- ENGRAM: "worktree agents must pass branch= explicitly"

**Q2 (что сработало):**
```
Handoff docs между агентами (Zeta↔Sigma) через markdown файлы + task board
оказались достаточными для полной координации без UI. Sigma принял мой API
без единого конфликта. Ключ: ExperienceReportStore.submit() как единый контракт.
```

→ **No task** (это learning, не bug/idea)
→ **Routes to:**
- ENGRAM: "handoff через markdown + task board = работающий паттерн координации"
- AURA: (нет user mentions)

**Q3 (идея):**
```
active_agents можно обогатить из AgentRegistry — добавить role, domain,
owned_paths в ответ. Одна строчка lookup. Даст полную карту "кто где что
трогает" для Commander перед merge.
```

→ **Auto-creates:**
- `[DEBRIEF-IDEA] Enrich active_agents with registry role/domain/owned_paths` (P4, research)

→ **Routes to:**
- MGC: `agent_registry.py` → hot file
- REFLEX: positive signal for `active_agents` tool

---

## Constraints

1. **Memory routing — regex only, zero LLM.** Детерминированный, <5ms
2. **Auto-tasks — research only, force_no_docs=true.** Не build, не fix — только ресерч
3. **Tags: `debrief-auto` + `architect-review`.** Commander видит и решает
4. **Не блокирует exit.** Debrief requested, но agent может выйти без ответа
5. **Q2 НЕ создаёт задачу.** Только routing в память. Задачи — из багов и идей

---

*"Лучший feedback — тот, который сам превращается в действие."*
