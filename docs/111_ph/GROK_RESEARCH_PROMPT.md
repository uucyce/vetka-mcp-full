# 🔬 GROK RESEARCH PROMPT: VETKA Position Bug Investigation

## 🎯 ЗАДАЧА

Найти **реальную причину** бага "7 нод → старое дерево" (позиции сбрасываются/теряются).

**ВАЖНО:** Предыдущие гипотезы Kimi K2.5 были ОПРОВЕРГНУТЫ нашей верификацией:
- ❌ `recalculate_depth()` после layout — НЕВЕРНО (порядок правильный)
- ❌ Legacy path `response.nodes` → fallback — НЕВЕРНО (мёртвый код, недостижим)
- ❌ `calculateSimpleLayout()` перезаписывает позиции — НЕВЕРНО (отключен в Phase 111)

---

## 📁 ФАЙЛЫ ДЛЯ АНАЛИЗА

### Backend (Python):
```
src/layout/fan_layout.py          — основной layout алгоритм
src/api/routes/tree_routes.py     — API endpoint /api/tree/data
```

### Frontend (TypeScript):
```
client/src/hooks/useTreeData.ts   — загрузка и обработка данных
client/src/utils/apiConverter.ts  — конвертация API → TreeNode
client/src/utils/layout.ts        — fallback layout (ОТКЛЮЧЕН)
client/src/store/useStore.ts      — Zustand store
client/src/hooks/useSocket.ts     — WebSocket handlers
```

---

## ✅ ВЕРИФИЦИРОВАННЫЕ ФАКТЫ

1. **Backend ВСЕГДА возвращает `response.tree`** (формат v1.4), никогда `response.nodes`
2. **Fallback layout ОТКЛЮЧЕН** в Phase 111 (строка 161-163 useTreeData.ts)
3. **apiConverter ПРАВИЛЬНО копирует** `layoutHint.expected_y → position.y`
4. **Порядок вызовов корректный:** `recalculate_depth()` → `calculate_fan_layout()`

---

## ❓ НОВЫЕ ГИПОТЕЗЫ ДЛЯ ПРОВЕРКИ

### H1: Backend не отправляет visual_hints для некоторых нод
```
Проверить: tree_routes.py — все ли ноды получают visual_hints.layout_hint?
Особенно: browser:// папки, chat nodes, artifact nodes
```

### H2: WebSocket `layout_changed` перезаписывает позиции неверными данными
```
Проверить: useSocket.ts строка 633-638
socket.on('layout_changed', (data) => {
  Object.entries(data.positions).forEach(...)
})
Откуда приходят data.positions? Правильные ли они?
```

### H3: Zustand store сбрасывается при re-render
```
Проверить: useStore.ts — есть ли места где nodes обнуляются?
React StrictMode double-render? HMR?
```

### H4: Race condition между API и WebSocket
```
Проверить: Может ли WebSocket обновление прийти ДО завершения API fetch?
И перезаписать позиции старыми данными?
```

### H5: DevPanel Apply триггерит неправильный refresh
```
Проверить: layout_socket_handler.py — что происходит при emit('tree_refresh_needed')?
Возвращаются ли старые закешированные позиции?
```

---

## 🔍 КОНКРЕТНЫЕ ВОПРОСЫ

1. **fan_layout.py**: Все ли типы нод (folder, file, chat, artifact, browser://) получают позиции?

2. **tree_routes.py**:
   - Строки где формируются visual_hints для КАЖДОГО типа ноды
   - Есть ли случаи когда visual_hints = undefined?

3. **useSocket.ts**:
   - Какие события могут перезаписать позиции ПОСЛЕ загрузки дерева?
   - Порядок обработки событий

4. **apiConverter.ts**:
   - При каких условиях `layoutHint` будет undefined?
   - Логирование при fallback на (0,0,0)

5. **Кеширование**:
   - Есть ли кеш позиций на backend или frontend?
   - Может ли кеш вернуть устаревшие позиции?

---

## 📊 ОЖИДАЕМЫЙ OUTPUT

1. **Список ВСЕХ мест** где position может стать (0,0,0) или неверным
2. **Точные условия** при которых это происходит
3. **Цепочка вызовов** от триггера до потери позиций
4. **Конкретный фикс** с указанием файла и строки

---

## 🚫 НЕ НУЖНО

- Повторять анализ fallback layout (уже проверено - отключен)
- Анализировать legacy path response.nodes (мёртвый код)
- Предлагать "добавить логирование" без конкретной гипотезы

---

## 📎 КОНТЕКСТ

Симптом: После изменений в DevPanel или refresh, 7 нод показываются в "старом" расположении (горизонтально Y=depth*20) вместо вертикального fan layout (Y=parent_y + Y_PER_DEPTH).

Это происходит НЕСМОТРЯ на то, что:
- Backend правильно считает позиции в fan_layout.py
- Frontend fallback отключен
- apiConverter правильно копирует visual_hints

**Где-то между backend расчётом и frontend рендером позиции ТЕРЯЮТСЯ или ПЕРЕЗАПИСЫВАЮТСЯ.**

Найди это место.
