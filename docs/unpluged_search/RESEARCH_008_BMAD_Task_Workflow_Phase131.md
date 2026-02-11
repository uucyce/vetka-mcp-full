# BMAD: Task Node Git Workflow
**Рекомендуемая фаза:** 131
**Статус:** Не имплементировано (research proposal)
**Приоритет:** СРЕДНИЙ
**Источник:** Беседы агентов, Phase 58+ proposal

## Описание
Каждая задача = отдельная git ветка. Auto-PR creation, EvalAgent review, merge по quality threshold.

## Текущее состояние
- Git operations существуют (commit, push)
- Branch management НЕ автоматизирован
- PR creation НЕ реализовано
- Изолированная работа агентов НЕ обеспечена

## Технические детали
- Один task = один git branch
- Auto-PR generation после Dev phase
- EvalAgent review scoring (threshold > 0.8)
- LangGraph integration для branch decisions
- Conflict prevention через isolation

## Шаги имплементации
1. Добавить auto-branch creation в pipeline start
2. Реализовать auto-PR через gh CLI
3. Интегрировать EvalAgent scoring с merge decisions
4. Добавить branch cleanup после merge
5. UI: показать active branches в DevPanel

## Ожидаемый результат
Изоляция изменений агентов, параллельная работа без конфликтов
