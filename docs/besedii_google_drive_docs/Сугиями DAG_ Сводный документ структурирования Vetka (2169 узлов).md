  
📊 СВОДНЫЙ ДОКУМЕНТ ПО СУГИЯМИ: Структурирование DAG (Ацикличный Граф Направленных Зависимостей)

Статус: Исследование и консолидация из 23+ документов  
Цель: Навести порядок в 2169 узлах, применить принципы Sugiyama Layout K для правильной иерархической визуализации

═══════════════════════════════════════════════════════════════════════════════

## 📋 ЧАСТЬ 1: КЛЮЧЕВАЯ ПРОБЛЕМА И РЕШЕНИЕ

\#\#\# Текущее состояние:

- 2169 узлов в системе VETKA  
- \- Данные слиплись и логика хаотична  
- \- Дерево не растет вверх (антигравити формулы не работают)  
- \- Отсутствует правильная структура иерархии

\#\#\# Решение (из раздела 17.6 Knowledge Mode=Directory Mode):

Knowledge Mode должно строить ДЕРЕВО как Directory Mode, но с семантической иерархией вместо путей\!

Этапы решения:  
1️⃣ ШАГ 1: Построить ИЕРАРХИЮ ТЕГОВ (как папки)

- ROOT\_TAG \= “VETKA Documentation” или из данных  
-    \- Вложенность: Architecture → Backend → File → Code  
-    \- Алгоритм: Hierarchical Agglomerative Clustering или LCA (Lowest Common Ancestor) на основе similarity

2️⃣ ШАГ 2: Применить Directory Mode Sugiyama K К ЭТОМУ ДЕРЕВУ

- Y \= depth в иерархии тегов (НЕ knowledge\_level файла\!)  
-    \- tag\_y \= TAG\_BASE\_Y \+ tag\_depth \* LAYER\_HEIGHT  
-    \- X \= barycenter от родителей \+ смещение среди siblings  
-    \- X координата \= parent\_x \+ angular\_offset (как в Directory Mode fan\_layout.py)

3️⃣ ШАГ 3: Файлы распределяются ПОД своим тегом

- File\_y \= parent\_tag\_y \+ CHAIN\_STEP\_Y \* position\_in\_chain  
-    \- file\_x \= parent\_tag\_x \+ small\_fan\_offset (не большой веер под тегом)

═══════════════════════════════════════════════════════════════════════════════

\#\# 🔧 ЧАСТЬ 2: DIRECTED MODE vs KNOWLEDGE MODE \- КАК ИСПОЛЬЗОВАТЬ ВМЕСТЕ?

\#\#\# Вариант А: ОТДЕЛЬНО (Простой подход)

- \*\*Directed Mode\*\*: для логических схем, потоков управления, dependencies  
- \- \*\*Knowledge Mode\*\*: для организации информации по значимости и сложности  
- → Используй ОБА, но в разных визуализациях и разных контекстах

\#\#\# Вариант Б: ВМЕСТЕ (Рекомендуемый подход для вашей задачи)

- \*\*Knowledge Mode\*\* обеспечивает ОСНОВНУЮ иерархию (папки/теги)  
- \- \*\*Directed Mode\*\* обеспечивает РЁБРА внутри этой иерархии  
- \- Комбинация: Иерархия от Knowledge Mode \+ Edges от Directed Mode

Формула комбинирования:  
\`\`\`  
For node in nodes:  
    \# Knowledge Mode: определи его место в иерархии  
    Node.layer \= knowledge\_mode\_layer(node)  
    Node.position\_x \= knowledge\_mode\_x\_position(node)  
      
    \# Directed Mode: учти его входящие/исходящие связи  
    Node.incoming\_edges \= get\_edges\_in(node)  
    Node.outgoing\_edges \= get\_edges\_out(node)  
      
    \# При рендеринге: покажи оба аспекта  
    render(node, layer=node.layer, x=node.position\_x, edges=node.\*\_edges)  
\`\`\`

═══════════════════════════════════════════════════════════════════════════════

\#\# 📐 ЧАСТЬ 3: КЛЮЧЕВЫЕ ФОРМУЛЫ SUGIYAMA LAYOUT K

Источник: раздел “17.6\_Knowledge Mode=Directory Mode” из документа “беседы агентов о ветке”

\#\#\# Проблема 1: Нет иерархии тегов  
Решение:  
\`\`\`python  
Def build\_tag\_hierarchy(tags, files, embeddings):  
    \# Строит ДЕРЕВО тегов по семантическому сходству  
      
    \# 1\. Найти корневой тег (самый общий \- центроид всех)  
    Root \= find\_most\_central\_tag(tags, embeddings)  
      
    \# 2\. Кластеризовать оставшиеся теги вокруг него  
    \# Алгоритм: Hierarchical Agglomerative Clustering  
    \# или: LCA (Lowest Common Ancestor) на основе similarity  
      
    For tag in tags:  
        If tag \== root:  
            Tag.parent \= None  
            Tag.depth \= 0  
        Else:  
            \# Найти блиоажайшего “родителя” по similarity  
            Tag.parent \= find\_semantic\_parent(tag, tags, embeddings)  
            Tag.depth \= tag.parent.depth \+ 1  
      
    Return tags  
\`\`\`

\#\#\# Проблема 2: X не расходится (нет angular spread от родителя)  
Решение:  
\`\`\`python  
Def calculate\_tag\_x(tag, parent, siblings):  
    \# X координата тега \= позиция родителя \+ угловое смещение  
      
    If parent is None:  
        Return 0  \# Корень в центре  
      
    Sibling\_index \= siblings.index(tag)  
    Num\_siblings \= len(siblings)  
      
    \# Угловое распределение среди siblings  
    If num\_siblings \> 1:  
        \# \-0.5 to \+0.5 → умножаем на spread  
        Normalized \= (sibling\_index / (num\_siblings \- 1)) \- 0.5  
        Angular\_offset \= normalized \* SIBLING\_SPREAD  
    Else:  
        Angular\_offset \= 0  
      
    \# X \= родитель \+ смещение (расходится от родителя\!)  
    Return parent.x \+ angular\_offset  
\`\`\`

\#\#\# Проблема 3: Адаптивный градиент отсутствует  
Решение:  
\`\`\`python  
Def adaptive\_spread(files\_in\_branch, embeddings):  
    \# Идея: Где много похожих файлов → плотнее, где разные → шире  
      
    Avg\_similarity \= compute\_avg\_pairwise\_similarity(files\_in\_branch, embeddings)  
      
    \# Инверируем: высокая similarity → малый spread  
    \# similarity 0.95 → spread 0.2  
    \# similarity 0.50 → spread 1.0  
    Spread\_factor \= 1.0 \* (avg\_similarity \- 0.5) ^ 2  \# Нормализация  
    Spread\_factor \= max(0.2, min(1.0, spread\_factor))  
      
    Return BASE\_SPREAD \* spread\_factor  
\`\`\`

═══════════════════════════════════════════════════════════════════════════════

\#\# 📊 ЧАСТЬ 4: МАТРИЦА INPUTS / OUTPUTS

Структура для каждого узла:

\`\`\`json  
{  
  “Node\_id”: “file\_py\_1”,  
  “Type”: “file | tag | artifact | concept”,  
  “Name”: “[agents.py](http://agents.py)”,  
    
  “Knowledge\_metadata”: {  
    “Knowledge\_level”: 0.75,  
    “Time\_to\_understand”: 45,  // в минутах  
    “Complexity\_score”: 0.65,  
    “Depth\_in\_hierarchy”: 3  
  },  
    
  “Inputs”: {  
    “Depends\_on\_files”: \[“[handlers.py](http://handlers.py)”, “[memory.py](http://memory.py)”\],  
    “Depends\_on\_concepts”: \[“async-dispatch”, “state-machine”\],  
    “Requires\_knowledge”: \[“Python 3.10+”, “asyncio”, “SQLAlchemy”\],  
    “Input\_matrix”: \[  
      {“source”: “[handlers.py](http://handlers.py)”, “data\_type”: “function\_def”, “count”: 5},  
      {“source”: “[memory.py](http://memory.py)”, “data\_type”: “class\_def”, “count”: 2}  
    \]  
  },  
    
  “Outputs”: {  
    “Provides\_to\_files”: \[“[orchestrator.py](http://orchestrator.py)”, “[service.py](http://service.py)”\],  
    “Provides\_concepts”: \[“async-agent”, “message-dispatcher”\],  
    “Output\_matrix”: \[  
      {“target”: “[orchestrator.py](http://orchestrator.py)”, “exported”: \[“Agent”, “TaskQueue”\], “count”: 2}  
    \]  
  },  
    
  “Semantic\_attributes”: {  
    “Tags”: \[“backend”, “async”, “state-machine”\],  
    “Category”: “core-logic”,  
    “Related\_concepts”: \[“agents”, “dispatch”, “communication”\]  
  },  
    
  “Visualization\_coords”: {  
    “Layer”: 3,  
    “X”: 450,  
    “Y”: 300,  
    “Color”: “\#4CAF50”,  
    “Size”: 1.5  
  }  
}  
\`\`\`

═══════════════════════════════════════════════════════════════════════════════

\#\# 🧠 ЧАСТЬ 5: MGC (MATERIALIZED GRAPH CACHE) И CAM ИНТЕГРАЦИЯ

Источник: раздел “MGC Hierarchical Memory Integration”

\#\#\# MGC (Materialized Graph Cache / Multi-Generational Consistency):

- Иерархический кеш графа данных на разных уровнях  
- \- Gen 0: свежие узлы (ненужно кешировать)  
- \- Gen 1: intermediate (кешируются результаты)  
- \- Gen 2: archived (холодный стор)

Применение к Vetka:  
\`\`\`  
NODES CACHE (PG bouncer \+ Engram):  
├─ Gen 0: Hot nodes (часто обновляются) → RAM/In-memory  
├─ Gen 1: Warm nodes (периодические апдейты) → Redis/Intermediate  
└─ Gen 2: Cold nodes (архив) → Postgres/Disk/JSON

EDGES CACHE:  
├─ Primary: WAL-репликация для consistency  
├─ Intermediate: Gdrant (vector DB) для semantic edges  
└─ Read Replicas: Для масштабирования запросов  
\`\`\`

\#\#\# CAM (Cascading Aggregation Model):

- Логическая репликация с каскадными изменениями  
- \- Write-Ahead Logs (WAL) для гарантии consistency  
- \- Cascading → Hot Spots (overload, retries)  
- \- Vicious Cycle Mitigation: Materialized Views \+ MGC

═══════════════════════════════════════════════════════════════════════════════

\#\# 🏗️ ЧАСТЬ 6: ДВУСЛОЙНАЯ ВИЗУАЛИЗАЦИЯ

\#\#\# Слой 1: ОБЗОР (High Level)

- Только ROOT теги и главные категории  
- \- Показать распределение узлов по категориям  
- \- Highlight: какие ветки переполнены (перекульпированы)  
- \- Используется для принятия стратегических решений о рефакторинге

Метрики слоя 1:  
\`\`\`  
ROOT  
├─ Architecture (428 узлов)  
├─ Backend (612 узлов) ⚠️ ПЕРЕПОЛНЕНА  
├─ Frontend (325 узлов)  
├─ Utils (402 узлов)  
└─ Concepts (402 узлов)  
\`\`\`

\#\#\# Слой 2: ДЕТАЛИ (Low Level)

- Full DAG со всеми 2169 узлами  
- \- Показать edges (зависимости)  
- \- Цветовая кодировка по Knowledge Level  
- \- Размер узла по Importance Score  
- \- Используется для локальных рефакторингов и анализа

───────────────────────────────────────────────────────────────────────────────

\#\# 📚 ЧАСТЬ 7: УКАЗАНИЕ ИСТОЧНИКОВ

Все приведенные выше материалы собраны из следующих разделов исходного документа “беседы агентов о ветке”:

1. \*\*”17.6\_Knowledge Mode=Directory Mode”\*\* (вкладка)  
2.    → Ключевая архитектура, формулы Sugiyama, решение проблем 1-3

2\. \*\*”MGC Hierarchical Memory Integration”\*\* (вкладка)  
   → Архитектура многоуровневого кеша, интеграция с Vetka

3. \*\*”АРХИТЕКТУРНЫЕ КОМПОНЕНТЫ”\*\* (разделы)  
4.    → Directory Mode fan\_layout.py, координирование, распределение

4\. \*\*”Refactoring after 22 phase”\*\* (вкладка)  
   → Применение Knowledge Level к структуре

5. \*\*”Cam OCR планы”\*\* \+ \*\*”VETKA\_MCP tools”\*\* (вкладки)  
6.    → Инструменты для анализа и организации данных

═══════════════════════════════════════════════════════════════════════════════

\#\# 🎯 ЧАСТЬ 8: РЕКОМЕНДУЕМАЯ СТРАТЕГИЯ ВНЕДРЕНИЯ

\#\#\# Этап 1 (СЕЙЧАС): Информационный аудит

- Распарсить все 2169 узлов  
- \- Классифицировать по типам: file, tag, concept, artifact  
- \- Вычислить Knowledge Level и Time for each node

\#\#\# Этап 2 (1-2 недели): Построение иерархии

- Применить Hierarchical Agglomerative Clustering к тегам  
- \- Создать ROOT\_TAG структуру  
- \- Вычислить layer (depth) для каждого узла

\#\#\# Этап 3 (2-3 недели): Применение Sugiyama Layout

- Реализовать формулы Y (layer-based)  
- \- Реализовать формулы X (angular spread)  
- \- Реализовать adaptive\_spread (similarity-based)

\#\#\# Этап 4 (3-4 недели): Интеграция с MGC/CAM

- Настроить кеширование по gen (0, 1, 2\)  
- \- Настроить WAL-репликацию  
- \- Интегрировать с Gdrant для semantic search

\#\#\# Этап 5: Визуализация и двухслойный обзор

- Реализовать Layer 1 (обзор)  
- \- Реализовать Layer 2 (детали)  
- \- Добавить interactive filters

═══════════════════════════════════════════════════════════════════════════════

\#\# ✅ ОТВЕТЫ НА ГЛАВНЫЕ ВОПРОСЫ

❓ Делать ли Directed Mode и Knowledge Mode отдельно или вместе?  
✅ \*\*ВМЕСТЕ\*\* — Knowledge Mode обеспечивает иерархию, Directed Mode обеспечивает рёбра

❓ Как сделать чтоб дерево росло вверх?  
✅ Применить формулы Sugiyama Y \= TAG\_BASE\_Y \+ depth \* LAYER\_HEIGHT

❓ Как происходит рефакторинг деревьев и группирование по папкам?  
✅ Hierarchical Agglomerative Clustering \+ семантические ключи из embeddings

❓ Как отделить зёрна от плевел?  
✅ Классифицировать узлы по type \+ фильтровать по Knowledge Level threshold

═══════════════════════════════════════════════════════════════════════════════

Документ создан: 2026-02-02  
Версия: 1.0 (Исследовательская версия)