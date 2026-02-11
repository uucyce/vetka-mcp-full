# User Memory System (Персонализация)
**Рекомендуемая фаза:** 132
**Статус:** Не имплементировано
**Приоритет:** СРЕДНИЙ
**Источник:** Беседы агентов

## Описание
Хранение и вызов истории взаимодействий пользователя, предпочтений, личностных особенностей. Интеграция с Engram.

## Текущее состояние
- Engram user_preferences endpoint существует (но пустой)
- Профили пользователей НЕ сохраняются
- Нет истории взаимодействий cross-session

## Технические детали
- User profile storage в Qdrant collection
- Memory encoding из чат-истории
- Preference learning (language, style, topics)
- Cross-session persistence
- Integration с Engram hot/cold memory

## Шаги имплементации
1. Создать user_profile schema в Qdrant
2. Реализовать preference extraction из чатов
3. Добавить cross-session memory persistence
4. Интегрировать с prompt enrichment
5. UI: показать user profile в settings

## Ожидаемый результат
Персонализированные ответы агентов, учёт стиля пользователя

---
