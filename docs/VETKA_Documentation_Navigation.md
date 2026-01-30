# VETKA DOCUMENTATION - NAVIGATION & PRIORITY GUIDE
**Дата:** 19 декабря 2025  
**Версия:** 1.0

---

## 📚 ГЛАВНЫЙ ПОРЯДОК ДОКУМЕНТОВ

### 🔴 КРИТИЧЕСКИЙ ПРИОРИТЕТ (читать ПЕРВЫМ)

#### 1. Вложенные в проект (из `/mnt/project/`)
**Эти документы — источник истины. Остальное — вспомогательное.**

| Документ | Что там | Время | Когда читать |
|----------|---------|-------|-------------|
| **VETKA_Sugiyama_Hybrid_Analysis.md** | 4 фазы алгоритма + гибридный подход | 30 мин | ПЕРВЫЙ |
| **VETKA_Visualization_Specification.md** | Спецификация визуализации + философия | 25 мин | ВТОРОЙ |
| **position_calculator.py** | Python реализация Sugiyama (Phase 1-4) | 15 мин (читать код) | Для деталей |
| **sugiyama_layout.js** | JS реализация (аналогично Python) | 15 мин (читать код) | Для деталей |

**🎯 Минимум для понимания:**
- Прочитай **VETKA_Sugiyama_Hybrid_Analysis.md** полностью (особенно Часть 2-3)
- Изучи диаграммы в **VETKA_Visualization_Specification.md** (Часть 1-2)
- Это даст 95% понимания

---

### 🟢 ВЫСОКИЙ ПРИОРИТЕТ (читать ВТОРЫМ)

| Документ | Назначение |
|----------|-----------|
| **VETKA_Master_Instructions_v2.md** (этот проект) | Полная инструкция (я создал) |
| **VETKA_Phase12K_Diagnostics.md** (этот проект) | Диагностика текущих проблем |
| **Research: Knowledge Graph embeddings** | Дополнение для Y/X/Z осей |

**⏱️ Время:** 30 мин  
**Когда читать:** После вложенных документов

---

### 🟡 НИЗКИЙ ПРИОРИТЕТ (справочник)

| Документ | Назначение |
|----------|-----------|
| Старые заметки Opus | Архив (только если нужна история) |
| API документация | Только если интегрируешь новый провайдер |
| Git history | Только если нужно восстанавливать файлы |

---

## 🗺️ НАВИГАЦИЯ ПО ВЛОЖЕННЫМ ДОКУМЕНТАМ

### VETKA_Sugiyama_Hybrid_Analysis.md

```
✅ Резюме (5 мин)
   └─ Таблица отличий исследования от твоей концепции

✅ Часть 1: Sugiyama Framework (10 мин)
   └─ 4 фазы классического алгоритма Sugiyama
   └─ Почему исследование НЕ следует Sugiyama

✅ Часть 2: ТВОЯ КОНЦЕПЦИЯ (15 мин) ← ГЛАВНАЯ
   ├─ Y-ось: Многомерная (directory + time + semantic)
   ├─ X-ось: Угловое распределение
   └─ Z-ось: Дубликаты + лес

✅ Часть 3: Гибридный алгоритм (20 мин)
   ├─ Phase 1: Layer Assignment
   ├─ Phase 2: Angular Crossing Reduction
   ├─ Phase 3: Semantic Clustering (UMAP)
   └─ Phase 4: 3D Coordinate Assignment

✅ Часть 4: Knowledge Graph (10 мин)
   └─ PageRank-подобная метрика для иерархии

✅ Части 5-7: Forest + Архитектура + Что взять (10 мин)
   └─ Завершение
```

**Как использовать:**
1. Скопировать код из Phase 1-4 если нужна реализация
2. Использовать примеры для тестирования
3. Обращаться к формулам если что-то не работает

### VETKA_Visualization_Specification.md

```
✅ Часть 1: Философия VETKA (5 мин)
   └─ Дерево как метафора

✅ Часть 2: Три оси VETKA (10 мин) ← ВАЖНО
   ├─ Y-axis: Hierarchy + Time
   ├─ X-axis: Alternatives + Angular Spread
   └─ Z-axis: Duplicates + Forest

✅ Часть 3: Алгоритм Sugiyama (15 мин)
   └─ 5 фаз (включая dummy nodes)
   └─ Коррекция на VETKA

✅ Часть 4: Knowledge Graph (10 мин)
   └─ Определение уровня знаний

✅ Части 5-10: Details (справочник)
   └─ Code examples, integration, metrics
```

---

## 🎯 ДЛЯ РАЗНЫХ ЗАДАЧ

### Задача: "Разберусь как работает VETKA"
**Читать в этом порядке:**
1. VETKA_Master_Instructions_v2.md (Часть I + II)
2. VETKA_Visualization_Specification.md (Часть 1-2)
3. VETKA_Sugiyama_Hybrid_Analysis.md (Часть 1-3)

**Время:** 60 мин  
**Результат:** Полное понимание

### Задача: "Нужно исправить визуализацию (Phase 12K)"
**Читать:**
1. VETKA_Phase12K_Diagnostics.md (полностью)
2. VETKA_Visualization_Specification.md (Часть 3 код)
3. position_calculator.py (для деталей Python)

**Время:** 45 мин  
**Результат:** Знаешь как фиксить

### Задача: "Нужно реализовать Phase 13 (Y-axis enhancement)"
**Читать:**
1. VETKA_Sugiyama_Hybrid_Analysis.md (Часть 4 Knowledge Graph)
2. position_calculator.py (class KnowledgeLevelCalculator)
3. VETKA_Visualization_Specification.md (Часть 4)

**Время:** 45 мин  
**Результат:** Знаешь как кодить

### Задача: "Хочу понять бесконечные линии"
**Читать:**
1. VETKA_Phase12K_Diagnostics.md (Проблема #3)
2. VETKA_Sugiyama_Hybrid_Analysis.md (Часть 3 Phase 4)
3. sugiyama_layout.js (calculateCoordinates функция)

**Время:** 30 мин  
**Результат:** Знаешь где ошибка

---

## 📖 КОДЫ И ПРИМЕРЫ

### Где найти рабочий код?

| Язык | Файл | Что там |
|------|------|---------|
| **Python** | position_calculator.py | Полная реализация Phase 1-4 |
| **JavaScript** | sugiyama_layout.js | Three.js интеграция |
| **Python (Backend)** | src/visualizer/tree_renderer.py | Broken (нужен fix) |

### Как использовать code snippets?

```markdown
1. VETKA_Sugiyama_Hybrid_Analysis.md содержит Python-like pseudo-code
   → Можно адаптировать для реальной реализации

2. position_calculator.py — это рефернс реализация
   → Можешь копировать функции как есть

3. sugiyama_layout.js — это для браузера
   → Используй если интегрируешь Three.js

4. src/visualizer/tree_renderer.py — сломанный код
   → Нужно исправлять, используя примеры выше
```

---

## 🔄 ВЕРСИОНИРОВАНИЕ ДОКУМЕНТОВ

### Как узнать какая версия актуальна?

**Проверка:** Смотри дату в начале документа
```markdown
**Дата обновления:** 19 декабря 2025
```

**Иерархия актуальности:**
1. Вложенные документы (`/mnt/project/`) — всегда свежие
2. Master Instructions (создал я) — свежие
3. Диагностика — пересчитывается после каждого фикса
4. Старые заметки — архив

---

## ⚠️ ЧАСТЫЕ ОШИБКИ

### ❌ Ошибка 1: Читать только один документ
**Проблема:** Вложенные документы дополняют друг друга
- VETKA_Sugiyama_Hybrid_Analysis.md — алгоритм
- VETKA_Visualization_Specification.md — философия + спецификация

**Решение:** Читай оба (или хотя бы Часть 2-3 первого)

### ❌ Ошибка 2: Игнорировать диаграммы
**Проблема:** "Я прочитал текст, но не понял"
**Решение:** ASCII диаграммы — это главная информация! Потрать 5 мин на каждую

### ❌ Ошибка 3: Копировать код без адаптации
**Проблема:** Pseudo-code из документов может не работать как есть
**Решение:** 
- VETKA_Sugiyama_Hybrid_Analysis.md — это идеи + формулы
- position_calculator.py — это рефернс реализация
- Адаптируй под твой контекст (языки, библиотеки)

### ❌ Ошибка 4: Путать Directory Mode и Semantic Mode
**Проблема:** Это две разные визуализации одного дерева!
**Решение:** 
- Directory Mode (Phase 12K) — папки → узлы
- Semantic Mode (Phase 17) — концепты → узлы
- Оба используют одинаковый Sugiyama алгоритм

---

## 🚀 БЫСТРЫЙ СТАРТ ДЛЯ НОВОГО ЧАТА

**За 5 минут:**
```
1. Открой VETKA_Master_Instructions_v2.md (Часть I)
2. Прочитай что такое VETKA
3. Посмотри диаграмму 4 фаз Sugiyama (Часть III)
4. Теперь ты готов к диагностике
```

**За 30 минут:**
```
1. VETKA_Master_Instructions_v2.md (Часть I + II)
2. VETKA_Visualization_Specification.md (Часть 1-2 + диаграммы)
3. VETKA_Sugiyama_Hybrid_Analysis.md (Часть 2-3)
4. Теперь ты готов к разработке
```

**За 1 час:**
```
1. Все вышеперечисленное
2. VETKA_Phase12K_Diagnostics.md (полностью)
3. Глубокое погружение в problem solving
```

---

## 📝 ЧЕКЛИСТ: ДОКУМЕНТЫ ПРОЧИТАНЫ

```
🎯 КРИТИЧЕСКИЙ ПРИОРИТЕТ:
  [ ] VETKA_Sugiyama_Hybrid_Analysis.md (Часть 1-3) — 40 мин
  [ ] VETKA_Visualization_Specification.md (Часть 1-2) — 20 мин
  
🎯 ВЫСОКИЙ ПРИОРИТЕТ:
  [ ] VETKA_Master_Instructions_v2.md (Часть I-III) — 30 мин
  [ ] VETKA_Phase12K_Diagnostics.md (Часть целевую) — 20 мин

🎯 СПРАВОЧНИК:
  [ ] position_calculator.py (для деталей Python)
  [ ] sugiyama_layout.js (для деталей JS)
  [ ] VETKA_Visualization_Specification.md (Часть 3-10)
```

---

## 🔗 ПЕРЕКРЁСТНЫЕ ССЫЛКИ

Если ты читаешь документ X и видишь ссылку на Y:

```
VETKA_Sugiyama_Hybrid_Analysis.md
  └─ "см. VETKA_Visualization_Specification.md Часть 4"
     → Это кроссрефы. Открой оба документа параллельно

VETKA_Phase12K_Diagnostics.md
  └─ "см. position_calculator.py функция clamp()"
     → Там есть рабочий код. Скопируй и адаптируй
```

---

## 💡 ПРИНЦИП ЧИТАНИЯ

**Документы VETKA — это не linear novel, а reference manual.**

- 🔵 Читай по задачам, не по порядку
- 🔵 Используй диаграммы как ориентиры
- 🔵 Копируй код из примеров
- 🔵 Проверяй против вложенных документов (они приоритет)
- 🔵 Используй Master Instructions как навигацию

---

**Создано:** 19 декабря 2025  
**Автор:** Claude (Haiku 4.5)  
**Статус:** Ready for distribution
