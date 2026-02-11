# Ralf-Loop: Цикл Самоулучшения Кода

**Рекомендуемая фаза:** 130
**Статус:** Частично (EvalAgent 70-80%)
**Приоритет:** ВЫСОКИЙ
**Источник:** Беседы агентов

## Описание

Строгий цикл самокритики: generate → critique → fix → iterate (3-5 раундов). EvalAgent даёт оценки, но полный цикл перезаписи кода не завершён.

## Текущее состояние

- EvalAgent scoring существует
- Iteration control НЕ полный
- "Code is perfect" termination check отсутствует
- LearnerAgent НЕ реализован

## Технические детали

- 3-5 итераций максимум
- Терминация: score > 0.9 ИЛИ "Code is perfect"
- LearnerAgent: анализ ошибок → улучшение промптов
- Failure pattern analysis
- Prompt optimization loop

## Шаги имплементации

1. Усилить EvalAgent: добавить конкретные fix-инструкции
2. Реализовать iteration controller с termination conditions
3. Создать LearnerAgent для prompt learning
4. Интегрировать с Mycelium pipeline
5. Метрики: tracking improvement per iteration

## Ожидаемый результат

+30-50% качество генерируемого кода
