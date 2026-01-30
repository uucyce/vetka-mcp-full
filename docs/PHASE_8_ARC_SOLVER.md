# ✅ VETKA Phase 8.0 - ARC Solver Agent Complete

## 🎯 Что создано

### ARC Solver Agent - Creative Graph Transformation Engine

**Файл**: `src/agents/arc_solver_agent.py` (950+ строк)

Агент генерирует креативные трансформации workflow-графов используя методологию ARC (Abstraction and Reasoning Corpus).

## 🧠 Методология ARC

```
1. ANALYZE    → Анализ текущего состояния графа
2. HYPOTHESIZE → Генерация 5-20 кандидатов-трансформаций
3. IMPLEMENT  → Безопасное выполнение Python кода
4. EVALUATE   → Оценка через EvalAgent (0-1)
5. REFINE     → Сохранение успешных в few-shot
```

## 📊 Типы предложений

```python
class SuggestionType(Enum):
    CONNECTION = "connection"          # Новая связь между узлами
    TRANSFORMATION = "transformation"  # Трансформация структуры
    OPTIMIZATION = "optimization"      # Оптимизация производительности
    PATTERN = "pattern"               # Распознанный паттерн
```

## 🚀 Основной API

### 1. Создание агента

```python
from src.agents.arc_solver_agent import create_arc_solver

# API mode (Grok/Claude через OpenRouter)
arc_solver = create_arc_solver(
    memory_manager=memory,
    eval_agent=eval,
    prefer_api=True
)

# Ollama mode (local DeepSeek/HOPE)
arc_solver = create_arc_solver(
    memory_manager=memory,
    eval_agent=eval,
    prefer_api=False
)
```

### 2. Генерация предложений

```python
result = arc_solver.suggest_connections(
    workflow_id="my_workflow",
    graph_data={
        'nodes': [
            {'id': 'auth', 'type': 'feature'},
            {'id': 'user_db', 'type': 'data'},
            {'id': 'session', 'type': 'service'}
        ],
        'edges': [
            {'source': 'auth', 'target': 'user_db'}
        ]
    },
    task_context="Authentication system with user database",
    num_candidates=10,  # Генерировать 10 гипотез
    min_score=0.5       # Минимальный score для few-shot
)

# Результат:
{
    'suggestions': [...],        # Все предложения
    'top_suggestions': [...],    # Top-3 по score
    'stats': {
        'total_generated': 10,
        'total_tested': 10,
        'total_successful': 7,
        'avg_score': 0.72
    },
    'workflow_id': 'my_workflow'
}
```

### 3. Работа с предложениями

```python
# Top-3 предложения
for suggestion in result['top_suggestions']:
    print(f"Type: {suggestion['type']}")
    print(f"Score: {suggestion['score']:.2f}")
    print(f"Explanation: {suggestion['explanation']}")
    print(f"Code:\n{suggestion['code']}")
```

## 🔧 Архитектура

### ARCSolverAgent класс

```python
class ARCSolverAgent:
    def __init__(
        self,
        memory_manager: Optional[Any] = None,
        eval_agent: Optional[Any] = None,
        use_api: bool = False,
        api_aggregator: Optional[Any] = None,
        learner: Optional[Any] = None
    )
```

**Основные методы**:

#### `suggest_connections()`
```python
def suggest_connections(
    self,
    workflow_id: str,
    graph_data: Optional[Dict] = None,
    image_path: Optional[str] = None,
    task_context: Optional[str] = None,
    num_candidates: int = 10,
    min_score: float = 0.5
) -> Dict[str, Any]
```

Главный метод - полный цикл ARC.

#### `_generate_candidates()`
```python
def _generate_candidates(
    self,
    graph_data: Dict,
    image_path: Optional[str],
    task_context: str,
    num_candidates: int = 10
) -> List[str]
```

Генерация Python функций-трансформаций через API/Ollama.

#### `_evaluate_candidates()`
```python
def _evaluate_candidates(
    self,
    candidates: List[str],
    graph_data: Dict,
    graph_context: str
) -> List[ARCSuggestion]
```

Тестирование и оценка каждого кандидата.

#### `_safe_execute()`
```python
def _safe_execute(
    self,
    code: str,
    graph_data: Dict
) -> Tuple[bool, Any]
```

Безопасное выполнение Python кода в изолированном namespace.

## 🛡️ Безопасность

### Isolated Namespace

```python
namespace = {
    '__builtins__': {},  # ✅ Отключены встроенные функции
    'Dict': Dict,        # ✅ Только типы
    'List': List,
    'len': len,          # ✅ Безопасные функции
    'str': str,
    # ... только safe функции
}

exec(code, namespace)  # Выполнение в изолированной среде
```

**Запрещено**:
- ❌ `import` - нет доступа к модулям
- ❌ `exec`, `eval` - нет метапрограммирования
- ❌ `open`, `file` - нет файловой системы
- ❌ `__import__` - нет динамического импорта

**Разрешено**:
- ✅ Стандартные типы данных
- ✅ Математические операции
- ✅ Работа со списками/словарями
- ✅ `copy.deepcopy` для клонирования

## 🎓 Few-Shot Learning

### Автоматическое хранение

```python
# Успешные примеры (score >= min_score) автоматически сохраняются
def _store_few_shot_example(self, suggestion: ARCSuggestion):
    # In-memory cache (последние 20)
    self.few_shot_examples.append(suggestion)

    # MemoryManager (persistent)
    if self.memory:
        self.memory.save_arc_example({
            'type': suggestion.type.value,
            'code': suggestion.code,
            'score': suggestion.score,
            ...
        })
```

### Использование в промптах

```python
# Few-shot примеры добавляются в промпт автоматически
if self.few_shot_examples:
    prompt = "## ПРИМЕРЫ УСПЕШНЫХ ТРАНСФОРМАЦИЙ:\n\n"
    for example in self.few_shot_examples[-5:]:  # Last 5
        prompt += f"```python\n{example.code}\n```\n"
        prompt += f"Score: {example.score:.2f}\n\n"
```

### Загрузка из памяти

```python
# Загрузить ранее сохранённые примеры
arc_solver.load_few_shot_examples(limit=20)
```

## 📈 Оценка предложений

### Через EvalAgent

```python
def _evaluate_with_eval_agent(
    self,
    code: str,
    explanation: str,
    result: Any,
    graph_context: str
) -> float:
    """
    Оценка через EvalAgent:
    - 0.0-0.3: Бесполезная
    - 0.3-0.5: Слабо полезная
    - 0.5-0.7: Умеренно полезная
    - 0.7-0.9: Очень полезная
    - 0.9-1.0: Исключительная
    """
```

### Эвристическая (fallback)

```python
def _heuristic_score(self, code: str, result: Any) -> float:
    """
    Если EvalAgent недоступен:
    - +0.1 за короткий код
    - +0.1 за docstring
    - +0.2 за результат != None
    - -0.1 за пустой результат
    """
```

## 🔄 Интеграция с VETKA

### 1. Orchestrator Integration

```python
# src/agents/orchestrator_with_elisya.py

from src.agents.arc_solver_agent import create_arc_solver

class ElysiaOrchestrator:
    def __init__(self):
        # ... existing init
        self.arc_solver = create_arc_solver(
            memory_manager=self.memory_manager,
            eval_agent=self.eval_agent,
            prefer_api=True
        )

    async def handle_workflow_complete(self, workflow_id: str):
        """После завершения workflow - запросить ARC предложения"""

        # Получить граф из памяти
        graph_data = await self.get_workflow_graph(workflow_id)

        # Сгенерировать предложения
        suggestions = self.arc_solver.suggest_connections(
            workflow_id=workflow_id,
            graph_data=graph_data,
            task_context="Workflow completed, suggest improvements",
            num_candidates=5
        )

        # Отправить в UI через Socket.IO
        await self.socketio.emit('arc_suggestions', {
            'workflow_id': workflow_id,
            'suggestions': suggestions['top_suggestions']
        })
```

### 2. REST API Endpoints

```python
# main.py

from src.agents.arc_solver_agent import create_arc_solver

# Initialize ARC Solver
arc_solver = create_arc_solver(
    memory_manager=memory_manager,
    eval_agent=eval_agent,
    prefer_api=True
)

@app.post("/api/arc/suggest")
async def arc_suggest(request: dict):
    """
    Генерация ARC предложений

    Body:
    {
        "workflow_id": "str",
        "graph_data": {...},
        "task_context": "str",
        "num_candidates": 10
    }
    """
    workflow_id = request.get('workflow_id')
    graph_data = request.get('graph_data')
    task_context = request.get('task_context', '')
    num_candidates = request.get('num_candidates', 10)

    result = arc_solver.suggest_connections(
        workflow_id=workflow_id,
        graph_data=graph_data,
        task_context=task_context,
        num_candidates=num_candidates
    )

    return result

@app.get("/api/arc/status")
async def arc_status():
    """Получить статистику ARC агента"""
    return arc_solver.get_stats()
```

### 3. Socket.IO Events

```python
# Socket.IO handler

@socketio.on('request_arc_suggestions')
async def handle_arc_request(data):
    """
    Real-time ARC suggestions

    Client sends:
    {
        "workflow_id": "str",
        "graph_data": {...}
    }
    """
    workflow_id = data.get('workflow_id')
    graph_data = data.get('graph_data')

    # Генерация в фоне
    result = await asyncio.create_task(
        arc_solver.suggest_connections(
            workflow_id=workflow_id,
            graph_data=graph_data,
            num_candidates=5
        )
    )

    # Отправить обратно клиенту
    await emit('arc_suggestions_ready', {
        'workflow_id': workflow_id,
        'suggestions': result['top_suggestions']
    })
```

## 📝 Примеры сгенерированных трансформаций

### 1. CONNECTION (новая связь)

```python
def suggest_auth_to_session_connection(graph_data: Dict) -> Optional[Dict]:
    """Предлагает связь между auth и session узлами"""
    nodes = graph_data.get('nodes', [])
    edges = graph_data.get('edges', [])

    # Найти auth и session узлы
    auth_node = next((n for n in nodes if 'auth' in n['id'].lower()), None)
    session_node = next((n for n in nodes if 'session' in n['id'].lower()), None)

    if auth_node and session_node:
        # Проверить, что связь не существует
        edge_exists = any(
            e['source'] == auth_node['id'] and e['target'] == session_node['id']
            for e in edges
        )

        if not edge_exists:
            # Добавить новую связь
            new_edge = {
                'source': auth_node['id'],
                'target': session_node['id'],
                'type': 'suggested_connection',
                'reason': 'Auth typically creates sessions'
            }
            edges.append(new_edge)

            return {
                'nodes': nodes,
                'edges': edges,
                'change': f"Added connection: {auth_node['id']} → {session_node['id']}"
            }

    return None
```

### 2. OPTIMIZATION (кэширование)

```python
def add_caching_layer(graph_data: Dict) -> Optional[Dict]:
    """Добавляет кэширующий слой между API и DB"""
    nodes = graph_data.get('nodes', [])
    edges = graph_data.get('edges', [])

    # Найти API и DB узлы
    api_nodes = [n for n in nodes if n.get('type') == 'api']
    db_nodes = [n for n in nodes if n.get('type') == 'data']

    if api_nodes and db_nodes:
        # Добавить cache узел
        cache_node = {
            'id': 'cache_layer',
            'type': 'cache',
            'name': 'Redis Cache'
        }
        nodes.append(cache_node)

        # Переподключить связи через cache
        for api in api_nodes:
            for db in db_nodes:
                # Найти прямую связь API → DB
                direct_edge = next((
                    e for e in edges
                    if e['source'] == api['id'] and e['target'] == db['id']
                ), None)

                if direct_edge:
                    # Удалить прямую связь
                    edges.remove(direct_edge)

                    # Добавить API → Cache → DB
                    edges.append({'source': api['id'], 'target': 'cache_layer'})
                    edges.append({'source': 'cache_layer', 'target': db['id']})

        return {'nodes': nodes, 'edges': edges}

    return None
```

### 3. PATTERN (распознавание)

```python
def detect_microservice_pattern(graph_data: Dict) -> Optional[Dict]:
    """Распознаёт паттерн микросервисов и группирует узлы"""
    nodes = graph_data.get('nodes', [])
    edges = graph_data.get('edges', [])

    # Найти узлы с похожими prefixes (auth_, user_, payment_)
    services = {}
    for node in nodes:
        node_id = node.get('id', '')
        prefix = node_id.split('_')[0] if '_' in node_id else node_id

        if prefix not in services:
            services[prefix] = []
        services[prefix].append(node)

    # Создать группы для микросервисов (3+ узла с одним prefix)
    microservices = {k: v for k, v in services.items() if len(v) >= 3}

    if microservices:
        # Добавить metadata о группировке
        for service_name, service_nodes in microservices.items():
            for node in service_nodes:
                if 'metadata' not in node:
                    node['metadata'] = {}
                node['metadata']['microservice'] = service_name

        return {
            'nodes': nodes,
            'edges': edges,
            'detected_patterns': {
                'microservices': list(microservices.keys())
            }
        }

    return None
```

## 📊 Статистика

```python
# Получить статистику работы
stats = arc_solver.get_stats()

{
    'total_generated': 150,      # Всего сгенерировано гипотез
    'total_tested': 150,          # Всего протестировано
    'total_successful': 108,      # Успешно выполнено (72%)
    'avg_score': 0.68,           # Средний score
    'few_shot_examples_count': 20,  # Примеров в кэше
    'mode': 'API'                 # API или Ollama
}
```

## ✅ Проверка

```bash
# Синтаксис
python3 -m py_compile src/agents/arc_solver_agent.py
✅ Syntax check passed

# Импорт
python3 -c "from src.agents.arc_solver_agent import ARCSolverAgent, create_arc_solver"
✅ Import successful
✅ SuggestionTypes: ['connection', 'transformation', 'optimization', 'pattern']

# Standalone тест
python3 src/agents/arc_solver_agent.py
✅ ARCSolverAgent created
✅ Test suggestions generated
```

## 🎯 Преимущества

✅ **Креативность** - Генерация новых идей, которые не очевидны из правил
✅ **Безопасность** - Изолированное выполнение без доступа к системе
✅ **Few-shot** - Обучение на успешных примерах
✅ **Гибридность** - API (качество) или Ollama (скорость/бесплатно)
✅ **Оценка** - EvalAgent + эвристики для валидации
✅ **Интеграция** - REST + Socket.IO + Orchestrator

## 🚀 Использование

### Быстрый старт

```python
from src.agents.arc_solver_agent import create_arc_solver

# 1. Создать агент
arc = create_arc_solver(
    memory_manager=memory,
    eval_agent=eval,
    prefer_api=True  # Grok/Claude
)

# 2. Сгенерировать предложения
result = arc.suggest_connections(
    workflow_id="my_workflow",
    graph_data=my_graph,
    task_context="E-commerce checkout flow",
    num_candidates=10
)

# 3. Использовать top-3
for suggestion in result['top_suggestions']:
    print(f"💡 {suggestion['explanation']}")
    print(f"   Score: {suggestion['score']:.2f}")

    # Применить трансформацию
    # exec(suggestion['code']) or integrate manually
```

### Production Integration

```python
# В orchestrator_with_elisya.py
self.arc_solver = create_arc_solver(
    memory_manager=self.memory_manager,
    eval_agent=self.eval_agent,
    prefer_api=True
)

# Вызывать после завершения workflow
suggestions = self.arc_solver.suggest_connections(
    workflow_id=workflow_id,
    graph_data=graph_data,
    num_candidates=5,
    min_score=0.7  # Только качественные
)

# Показать пользователю через UI
await self.send_suggestions_to_ui(suggestions)
```

## 🎉 Итог

✅ **ARC Solver Agent** - генерация креативных трансформаций
✅ **Безопасное выполнение** - isolated namespace
✅ **Few-shot learning** - обучение на успехах
✅ **API + Ollama** - гибридный режим
✅ **EvalAgent оценка** - 0-1 scoring
✅ **4 типа предложений** - connection, transformation, optimization, pattern
✅ **REST + Socket.IO** - готов к интеграции

---

**VETKA Phase 8.0** - ARC Solver: Creative Intelligence for Graph Transformations 🚀
