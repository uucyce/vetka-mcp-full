# Chat as Tree: Визуализация Чатов как Дерево
**Рекомендуемая фаза:** 133
**Статус:** Не имплементировано
**Приоритет:** СРЕДНИЙ
**Источник:** Беседы агентов

## Описание
Визуализация истории разговоров как Sugiyama DAG: chat trunk + artifact branches. User messages как cloud bubbles, AI artifacts как ветки.

## Текущее состояние
- Чат отображается линейно
- 3D viewport показывает файлы, не чаты
- Sugiyama layout существует для file tree

## Технические детали
- User messages → cloud bubbles (main trunk)
- AI artifacts → branches от соответствующего сообщения
- knowledge_level scoring: 0.5*inputs + 0.3*time + 0.2*semantic
- Gray-blue edges (alpha=0.3)
- Directed mode: хронологический порядок
- Knowledge mode: семантическая группировка

## Шаги имплементации
1. Создать ChatTreeBuilder из chat history
2. Адаптировать Sugiyama layout для chat nodes
3. Добавить node types: user_message, ai_response, artifact
4. Интегрировать с 3D viewport как отдельный режим
5. UI: toggle между file tree и chat tree

## Ожидаемый результат
Новый способ навигации по истории проекта через визуальное дерево чатов

---
