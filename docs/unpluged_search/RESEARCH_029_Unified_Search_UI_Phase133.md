# Unified Search & Address Bar (Browser-style)
**Рекомендуемая фаза:** 133
**Статус:** UI research
**Приоритет:** СРЕДНИЙ
**Источник:** todo_dream_117, беседы агентов

## Описание
Единая строка поиска = address bar (как в браузере). vetka/query создаёт новый context tree. Объединение social + web + file search + JARVIS chat.

## Текущее состояние
- Отдельные поля поиска
- Нет unified search
- Нет address-bar metaphor
- Нет context tree creation по поиску

## Технические детали
- Address-based navigation: vetka/path/query
- Automatic context assembly
- Dark theme (Nolan Batman style)
- Glow effects на результатах
- Social + web + file + semantic search в одном input
- Auto-detect query type (file path / search / command)

## Шаги имплементации
1. Создать UnifiedSearchBar компонент
2. Реализовать query type detection
3. Интегрировать все типы поиска
4. Добавить context tree creation по результатам
5. Стилизация: dark theme с glow effects

## Ожидаемый результат
Единая точка входа для всех поисковых и навигационных задач
