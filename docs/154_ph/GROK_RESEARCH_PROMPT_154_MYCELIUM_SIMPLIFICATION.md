# Grok Research Prompt — Phase 154: Mycelium Simplification

**Для:** @x-ai/grok-4.1-fast
**Контекст:** Pinned файл `MYCELIUM_VISION.md` (docs/152_ph/) — обязательно прочитай целиком.
**Цель:** UX research для радикального упрощения Mycelium Command Center.

---

## Задача

Мы переделываем Mycelium из "20 кнопок на экране" в "максимум 3 действия за раз". Ключевая идея — DAG-в-DAG (Матрёшка): один и тот же экран показывает разный уровень вложенности. Как файловый менеджер — кликнул внутрь, кнопка назад — вышел.

Нужен детальный research по 5 направлениям.

---

## 1. Wireframes для 5 состояний Матрёшки

Для каждого состояния нарисуй ASCII wireframe (или подробно опиши layout):

### Состояние: FIRST RUN
- Чистый экран, выбор проекта
- 3 действия: Папка / URL / Текстом
- Прогресс: сканирование → roadmap generation

### Состояние: ROADMAP
- DAG задач (корень внизу, новое вверху)
- Подсветка: ready / recommended / blocked
- 3 действия: Запустить / Спросить Архитектора / Добавить задачу
- Мини-окна: чат, задачи, статистика (compact, в углах)
- Breadcrumb: "Проект > Roadmap"

### Состояние: ЗАДАЧА
- Workflow DAG (Scout → Researcher → Architect → Coder → Verifier)
- Информация: команда, файлы, template
- 3 действия: Запустить / Изменить / Назад
- Breadcrumb: "Проект > Roadmap > Task: add dark mode"

### Состояние: ИСПОЛНЕНИЕ
- Тот же workflow DAG, ноды оживают
- Лог внизу, таймер, токены
- 3 действия: Пауза / Отмена / Назад
- Breadcrumb: "Проект > Roadmap > Task > Running..."

### Состояние: РЕЗУЛЬТАТ
- Статистика + табы (Код | Diff | Лог)
- Вердикт Verifier'а
- 3 действия: Принять / Переделать / Назад
- Breadcrumb: "Проект > Roadmap > Task > Result"

**Формат:** Для каждого — ASCII layout + список элементов + где что стоит.

---

## 2. UX Patterns: Drill-Down в одном экране

Исследуй как лучшие продукты решают "DAG-в-DAG" / "zoom into node" / "drill-down navigation":

- **Google Maps** — zoom levels, level of detail меняется плавно
- **macOS Finder** — column view, drill-in/out
- **Figma** — frames внутри frames, double-click = вход
- **n8n / ComfyUI** — workflow editor, subflows, groups
- **GitHub Projects** — board → issue → timeline
- **Notion** — page внутри page
- **Kubernetes Dashboard** — cluster → namespace → pod → container

Для каждого:
- Как они показывают "ты внутри чего-то" (breadcrumb? zoom? анимация?)
- Как работает "назад" (кнопка? gesture? breadcrumb click?)
- Сколько действий видно за раз
- Что скрыто и как достаётся (context menu? settings gear? long-press?)

**Вывод:** Какой паттерн лучше всего подходит для нашей Матрёшки и почему.

---

## 3. Свёртка 20+ кнопок в 3 действия per level

Текущие кнопки MCC (все, что есть сейчас):

```
HEADER:     MCC | Team▾ | Sandbox▾ | Heartbeat▾ | Key▾ | ●LIVE | stats | ▶Execute
TOOLBAR:    ✎edit | name | New | Save | Load▾ | ↩↪ | Validate | ✦Generate | ↓Import | ↑Export▾
CAPTAIN:    "Рекомендую: task X" [Go]
RAILS:      ▶Execute | ✏Edit | ←Back
FILTERS:    Status▾ | Phase▾ | Preset▾ | Agent▾ | Date From | Date To
TASK LIST:  + Add task | Dispatch | Filter toggle
```

Задача: **для каждого из 5 состояний определить ровно 3 primary actions + куда убрать остальное.**

Формат ответа — таблица:

| Состояние | Action 1 | Action 2 | Action 3 | Скрыто в ⚙ | Скрыто/автоматически | Убрано совсем |
|-----------|----------|----------|----------|------------|---------------------|---------------|

Для "Скрыто в ⚙" — конкретно: popup? dropdown? modal? keyboard shortcut?

---

## 4. Playground: один на проект

Текущая реализация: PlaygroundManager создаёт git worktree с рандомными именами (vibrant-wright), можно создать несколько, нельзя удалить через UI, непонятная связь с задачами.

Нужно:
- **Один playground на проект** — как это реализовать поверх git worktree?
- **Имя** = имя проекта + "-playground" (vetka-playground)
- **Quota:** пользователь задаёт лимит (N ГБ), система мониторит, сигнализирует
- **Удаление:** через UI, с подтверждением, очищает worktree
- **Remote:** пользователь указывает адрес сервера — как синхронизировать? rsync? git push to remote?
- **Lifecycle:** создание при onboarding → агенты работают внутри → review → merge → (опционально) очистка

Конкретные вопросы:
- Как мониторить размер git worktree в реальном времени? (`du` слишком медленный для больших проектов)
- Как ограничить запись агентов если лимит превышен?
- Лучшие практики для git worktree cleanup (prune, gc, repack)?

---

## 5. Transition Animation: уровень → уровень

Когда пользователь кликает на ноду Roadmap и "проваливается" в задачу — что происходит визуально?

Варианты:
- **Zoom in** — камера приближается к ноде, нода раскрывается в workflow DAG
- **Slide** — текущий DAG уезжает влево, новый приезжает справа
- **Fade** — текущий тает, новый появляется
- **Expand** — нода расширяется на весь экран, внутри появляется содержимое
- **Replace** — мгновенная замена, только breadcrumb меняется

Для каждого:
- Плюсы/минусы
- Примеры продуктов которые так делают
- Сложность реализации (у нас React + ReactFlow)
- Рекомендация: что лучше для нашего случая (DAG-в-DAG, 4 уровня)

---

## Что НЕ нужно

- Не нужен код. Только research + wireframes + рекомендации.
- Не нужен multi-project. У нас один проект.
- Не нужен offline mode. Всегда онлайн.
- Не нужен mobile. Desktop only.

---

## Формат ответа

Пожалуйста, структурируй по 5 разделам. Для wireframes — ASCII art. Для паттернов — таблицы. Для рекомендаций — одно конкретное решение + почему.

Объём: столько сколько нужно, не экономь.
