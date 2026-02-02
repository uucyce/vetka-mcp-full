# Маркеры Scroll-to-Bottom/Top Кнопка в ChatPanel

**Дата:** 2026-02-02
**Статус:** МАРКЕРЫ ПРОСТАВЛЕНЫ ✓
**Файл:** `client/src/components/chat/ChatPanel.tsx`

---

## Состояние Кнопки

### ✓ Кнопка УЖЕ СУЩЕСТВУЕТ

Кнопка scroll-to-bottom уже реализована в ChatPanel.tsx и полностью функциональна.

---

## Маркеры Проставлены

### 1. MARKER_SCROLL_STATE (строка 72)
**Назначение:** State переменная для отслеживания позиции скролла

```typescript
// MARKER_SCROLL_STATE: State tracking if user is at bottom of chat
// Phase 107.3: Scroll-to-bottom button state
// true = at bottom (hide button), false = scrolled up (show down arrow button)
const [isAtBottom, setIsAtBottom] = useState(true);
```

**Логика:**
- `true` = пользователь внизу сообщений → кнопка СКРЫТА
- `false` = пользователь скроллнул выше → кнопка ВИДНА (стрелка вниз)

---

### 2. MARKER_SCROLL_STATE (строка 1070-1084)
**Назначение:** Функция-обработчик скролла с отслеживанием позиции

```typescript
// MARKER_SCROLL_STATE: Track if user is at bottom of message list
// Formula: scrollHeight - scrollTop - clientHeight < 50px threshold
const handleScroll = useCallback(() => {
  const container = messagesContainerRef.current;
  if (!container) return;

  const { scrollTop, scrollHeight, clientHeight } = container;
  // When near bottom (within 50px), isAtBottom = true, hide scroll button
  // When scrolled up, isAtBottom = false, show scroll button with down arrow
  const atBottom = scrollHeight - scrollTop - clientHeight < 50;
  setIsAtBottom(atBottom);
}, []);
```

**Формула:**
- Если `scrollHeight - scrollTop - clientHeight < 50px` → пользователь внизу
- Пороговое значение: **50 пикселей** (мягкий порог)

---

### 3. MARKER_SCROLL_BTN_LOCATION (строка 2258)
**Назначение:** Местоположение кнопки в разметке

**Структура:**
```
<div style={{ flex: 1, position: 'relative', minHeight: 0 }}>
  <div ref={messagesContainerRef} style={{ height: '100%', overflow: 'auto' }}>
    <MessageList ... />
    <div ref={messagesEndRef} />  ← конец списка (целевая позиция)
  </div>

  {/* MARKER_SCROLL_BTN_LOCATION: над input полем */}
  <button>↓ Scroll to Bottom</button>  ← кнопка ЗДЕСЬ
</div>
```

**Позиционирование:**
- `position: 'absolute'` (над контейнером сообщений)
- `bottom: 20px` (над полем ввода)
- `right: 20px` (справа)
- `z-index: 10` (выше сообщений, но ниже попапов)

---

### 4. MARKER_SCROLL_FUNCTION (строка 2262)
**Назначение:** Функция скролла к концу чата

```typescript
onClick={() => {
  // MARKER_SCROLL_FUNCTION: scrollToBottom - smooth scroll to end
  messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
}}
```

**Действие:**
- Прокручивает к `messagesEndRef` с плавной анимацией
- `behavior: 'smooth'` = 200-300ms анимация (CSS пришельец)

---

## Стили и Поведение

### Кнопка (when `!isAtBottom`)

| Свойство | Значение | Назначение |
|----------|----------|-----------|
| Размер | 36×36px | Маленькая, минималистичная |
| Форма | Круглая (borderRadius 50%) | Soft UI (Nolan style) |
| Фон | #333 (grey) | Neutral color |
| Граница | 1px solid #444 | Subtle border |
| Икона | SVG ↓ (6 9 12 15 18 9) | Стрелка вниз |
| Цвет икон | #fff (white) | High contrast |
| Тень | 0 2px 8px rgba(0,0,0,0.3) | Depth effect |
| Transition | all 0.2s ease | Smooth changes |

### Hover эффект

```typescript
onMouseEnter: background #444 + scale(1.05)  // 5% увеличение
onMouseLeave: background #333 + scale(1)     // обратно
```

---

## Текущая Реализация

### ✓ Что уже работает

1. **State управление** (`isAtBottom`)
   - Инициализация: `true` (внизу по умолчанию)
   - Обновление: на каждый scroll event

2. **Scroll отслеживание** (`handleScroll`)
   - Подписка на `scroll` event контейнера
   - Отписка при unmount компонента

3. **Кнопка UI**
   - Условный рендеринг: `{!isAtBottom && (...)}`
   - SVG иконка: стрелка вниз ↓
   - Smooth scroll анимация

4. **Auto-scroll при новых сообщениях**
   - При добавлении сообщения → автоматический scroll
   - Зависимость: `[chatMessages.length]`

---

## TODO: Функции для будущего расширения

### 1. Toggle: Scroll-to-Top (когда пользователь внизу)
```typescript
// TODO: Когда isAtBottom = true, показать стрелку ↑
// Клик → scroll к первому сообщению
const scrollToTop = () => {
  messagesContainerRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
};
```

### 2. Keyboard Shortcut
```typescript
// TODO: Shift+End → scroll to bottom
// TODO: Shift+Home → scroll to top
```

### 3. Button Counter (опционально)
```typescript
// TODO: Показать количество новых сообщений
// !isAtBottom && chatMessages.length > visibleCount
// → badge с числом (как Slack, Discord)
```

---

## Файл Изменен

```bash
client/src/components/chat/ChatPanel.tsx
```

**Добавлено маркеров:**
- MARKER_SCROLL_STATE (2 места)
- MARKER_SCROLL_BTN_LOCATION (1 место)
- MARKER_SCROLL_FUNCTION (1 место)

---

## Проверка Компонентов

### MessageInput.tsx
- **Статус:** ✓ Не требует изменений
- **Причина:** Scroll-to-bottom находится над полем ввода
- **Расположение:** В ChatPanel, не в MessageInput

### MessageList.tsx
- **Статус:** ✓ Не требует изменений
- **Причина:** Просто отрисовывает сообщения
- **Ref:** Управляется из ChatPanel (messagesEndRef)

### Refs используются

```typescript
messagesContainerRef      // Контейнер с overflow:auto
messagesEndRef            // Целевая позиция (конец)
```

---

## Резюме

| Параметр | Значение |
|----------|----------|
| **Кнопка существует?** | ✓ ДА |
| **isAtBottom state?** | ✓ ДА (строка 72) |
| **scrollToBottom функция?** | ✓ ДА (messagesEndRef.scrollIntoView) |
| **Позиция кнопки** | ✓ Над полем ввода (absolute, bottom: 20px) |
| **Маркеры проставлены?** | ✓ 4 маркера в 5 местах |

### Архитектура
```
ChatPanel
├── State: isAtBottom (boolean)
├── Handler: handleScroll (callback)
├── Refs:
│   ├── messagesContainerRef (div overflow:auto)
│   └── messagesEndRef (div sentinel)
├── Listener: addEventListener('scroll', handleScroll)
└── Button: position absolute, bottom 20px, right 20px
    └── Icon: ↓ (SVG polyline)
    └── Action: messagesEndRef.scrollIntoView({ smooth })
```

---

**Готово к использованию!** ✓

Кнопка полностью функциональна и задокументирована через маркеры.
