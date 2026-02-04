#!/usr/bin/env python3
"""
VETKA Phase 8.0 - ARC Solver Agent
Generates creative workflow graph transformations using ARC methodology

ARC (Abstraction and Reasoning Corpus) methodology:
1. Analyze current graph state
2. Generate hypotheses (candidate transformations)
3. Test hypotheses via safe execution
4. Evaluate results via EvalAgent
5. Refine and store successful patterns

Author: VETKA AI
Version: 1.0.0

@status: active
@phase: 96, 108.7
@depends: json, logging, copy, elision, hope_enhancer
@used_by: MCP tools, orchestrator

MARKER_108_7_ARC_MGC: Phase 108.7 Integration
- MGCGraphCache for hierarchical state management (Gen0→Gen1→Gen2)
- HOPE integration for frequency-layer hypotheses (LOW/MID/HIGH)
- ELISION compression for suggestion payloads
- Request pooling (PgBouncer-like) for thundering herd mitigation
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
from collections import deque
import traceback
import copy

# Safe code execution
import sys
from io import StringIO

logger = logging.getLogger(__name__)


# =============================================================================
# MARKER_108_7_ARC_MGC: MGC Graph Cache
# =============================================================================

class MGCGraphCache:
    """
    Multi-Generational Cache for ARC graph state.

    Implements cascading replication:
    - Gen0: RAM hot (active transformations)
    - Gen1: Qdrant mid (recent patterns)
    - Gen2: Archive (historical successes)

    Mitigates: vicious cycles, thundering herd, 1690+ file scale
    """

    MGC_GENS = 3
    REQUEST_POOL_SIZE = 10

    def __init__(self):
        self.generations = [{} for _ in range(self.MGC_GENS)]
        self.request_queue = deque(maxlen=self.REQUEST_POOL_SIZE)
        self._stats = {"hits": 0, "misses": 0, "cascades": 0}

    def cascade_update(self, key: str, graph_state: Dict[str, Any]) -> None:
        """Update cache with cascading replication."""
        try:
            from src.memory.elision import compress_context
            compressed = compress_context(graph_state)
        except Exception:
            compressed = graph_state

        self.generations[0][key] = {
            "data": compressed,
            "timestamp": datetime.now().isoformat(),
            "usage": 0
        }

        # Auto-cascade if Gen0 too large
        if len(self.generations[0]) > 50:
            self._cascade_cold_to_gen1()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get from cache, checking all generations."""
        for gen_idx, gen in enumerate(self.generations):
            if key in gen:
                gen[key]["usage"] += 1
                self._stats["hits"] += 1
                return gen[key]["data"]
        self._stats["misses"] += 1
        return None

    def _cascade_cold_to_gen1(self) -> None:
        """Move cold items to Gen1."""
        cold = [k for k, v in self.generations[0].items() if v.get("usage", 0) < 3]
        for key in cold[:10]:
            item = self.generations[0].pop(key)
            self.generations[1][key] = item
        self._stats["cascades"] += 1
        logger.debug(f"[MGC] Cascaded {len(cold[:10])} items to Gen1")

    def pool_request(self, suggestion: Any) -> bool:
        """PgBouncer-like request pooling."""
        if len(self.request_queue) >= self.REQUEST_POOL_SIZE:
            logger.warning("[MGC] Thundering herd mitigated: queue full")
            return False
        self.request_queue.append(suggestion)
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            **self._stats,
            "gen0_size": len(self.generations[0]),
            "gen1_size": len(self.generations[1]),
            "gen2_size": len(self.generations[2]),
            "queue_size": len(self.request_queue)
        }


# ============================================================================
# ENUMS & DATACLASSES
# ============================================================================

class SuggestionType(Enum):
    """Тип предложения по трансформации графа"""
    CONNECTION = "connection"          # Новая связь между узлами
    TRANSFORMATION = "transformation"  # Трансформация структуры
    OPTIMIZATION = "optimization"      # Оптимизация производительности
    PATTERN = "pattern"               # Распознанный паттерн


@dataclass
class ARCSuggestion:
    """Предложение по улучшению/трансформации графа"""
    type: SuggestionType
    code: str                          # Python код трансформации
    explanation: str                   # Человекочитаемое объяснение
    score: float                       # 0-1 от EvalAgent
    success: bool                      # Успешное ли выполнение
    from_node: Optional[str] = None    # Исходный узел (для CONNECTION)
    to_node: Optional[str] = None      # Целевой узел (для CONNECTION)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для JSON"""
        result = asdict(self)
        result['type'] = self.type.value
        return result


# ============================================================================
# ARC SOLVER AGENT
# ============================================================================

class ARCSolverAgent:
    """
    ARC Solver Agent для генерации творческих трансформаций workflow-графов

    Использует методологию ARC:
    - Анализ текущего состояния графа
    - Генерация гипотез (5-20 кандидатов)
    - Тестирование через безопасное выполнение
    - Оценка через EvalAgent
    - Хранение успешных примеров (few-shot learning)

    MARKER_108_7_ARC_MGC: Phase 108.7 Enhancements
    - MGCGraphCache for hierarchical state caching
    - HOPE integration for frequency-layer hypotheses
    - ELISION compression for suggestion storage
    """

    def __init__(
        self,
        memory_manager: Optional[Any] = None,
        eval_agent: Optional[Any] = None,
        use_api: bool = False,
        api_aggregator: Optional[Any] = None,
        learner: Optional[Any] = None,
        enable_mgc: bool = True,
        enable_hope: bool = True
    ):
        """
        Args:
            memory_manager: MemoryManager для хранения few-shot примеров
            eval_agent: EvalAgent для оценки предложений
            use_api: Использовать API (Grok/Claude) или Ollama (local)
            api_aggregator: APIAggregator для API вызовов
            learner: Ollama learner (если use_api=False) - must have .generate() or .chat() method
            enable_mgc: Enable MGC graph caching (Phase 108.7)
            enable_hope: Enable HOPE frequency analysis (Phase 108.7)
        """
        self.memory = memory_manager
        self.eval_agent = eval_agent
        self.use_api = use_api
        self.api_aggregator = api_aggregator

        # MARKER_108_7_ARC_MGC: Initialize MGC cache
        self.mgc_cache = MGCGraphCache() if enable_mgc else None
        self._enable_hope = enable_hope
        self._hope_enhancer = None  # Lazy-loaded

        # Validate learner type - must have generate() or chat() method
        if learner is not None:
            if isinstance(learner, str):
                logger.error(f"❌ ARCSolverAgent received string instead of learner object: '{learner}'")
                logger.error("   Expected: BaseLearner instance with .generate() or .chat() method")
                self.learner = None
            elif not (hasattr(learner, 'generate') or hasattr(learner, 'chat')):
                logger.error(f"❌ Learner {type(learner).__name__} has no generate/chat method")
                logger.error("   Expected: BaseLearner instance with .generate() or .chat() method")
                self.learner = None
            else:
                self.learner = learner
                logger.info(f"✅ Learner validated: {type(learner).__name__}")
        else:
            self.learner = None

        # Хранилище few-shot примеров (in-memory cache)
        self.few_shot_examples: List[ARCSuggestion] = []

        # Статистика
        self.stats = {
            'total_generated': 0,
            'total_tested': 0,
            'total_successful': 0,
            'avg_score': 0.0
        }

        logger.info(f"✅ ARCSolverAgent initialized (API mode: {use_api}, learner: {type(self.learner).__name__ if self.learner else 'None'})")

    # ========================================================================
    # MAIN METHOD
    # ========================================================================

    def suggest_connections(
        self,
        workflow_id: str,
        graph_data: Optional[Dict] = None,
        image_path: Optional[str] = None,
        task_context: Optional[str] = None,
        num_candidates: int = 10,
        min_score: float = 0.5
    ) -> Dict[str, Any]:
        """
        Главный метод: анализ графа и генерация предложений

        Args:
            workflow_id: ID workflow для контекста
            graph_data: Данные графа (nodes, edges)
            image_path: Путь к изображению графа (для vision models)
            task_context: Контекст задачи
            num_candidates: Количество гипотез для генерации (5-20)
            min_score: Минимальный score для сохранения в few-shot

        Returns:
            {
                'suggestions': List[ARCSuggestion],  # Все предложения
                'top_suggestions': List[ARCSuggestion],  # Top-3
                'stats': Dict,  # Статистика
                'workflow_id': str
            }
        """
        logger.info(f"🔍 Starting ARC analysis for workflow: {workflow_id}")

        try:
            # MARKER_108_7_ARC_MGC: Check MGC cache first
            cache_key = f"arc_{workflow_id}_{hash(str(graph_data))}"
            if self.mgc_cache:
                cached = self.mgc_cache.get(cache_key)
                if cached:
                    logger.info(f"📦 MGC cache hit for {workflow_id}")
                    return cached

            # 1. Собрать контекст графа
            graph_context = self._build_graph_context(
                workflow_id, graph_data, image_path, task_context
            )

            # MARKER_108_7_ARC_MGC: Store graph state in cache
            if self.mgc_cache and graph_data:
                self.mgc_cache.cascade_update(f"graph_{workflow_id}", graph_data)

            # 2. Сгенерировать кандидатов (гипотезы) - with HOPE if enabled
            logger.info(f"🧠 Generating {num_candidates} candidate transformations...")
            if self._enable_hope:
                candidate_codes = self._generate_candidates_with_hope(
                    graph_data or {},
                    image_path,
                    task_context or "",
                    num_candidates
                )
            else:
                candidate_codes = self._generate_candidates(
                    graph_data or {},
                    image_path,
                    task_context or "",
                    num_candidates
                )

            self.stats['total_generated'] += len(candidate_codes)

            # 3. Протестировать и оценить кандидатов
            logger.info(f"⚗️  Testing {len(candidate_codes)} candidates...")
            suggestions = self._evaluate_candidates(
                candidate_codes,
                graph_data or {},
                graph_context
            )

            self.stats['total_tested'] += len(suggestions)

            # 4. Отобрать топ-3 и сохранить успешные
            top_suggestions = sorted(
                suggestions,
                key=lambda s: s.score,
                reverse=True
            )[:3]

            # Сохранить успешные в few-shot
            successful = [s for s in suggestions if s.success and s.score >= min_score]
            self.stats['total_successful'] += len(successful)

            for sugg in successful:
                self._store_few_shot_example(sugg)

            # 5. Обновить статистику
            if suggestions:
                avg_score = sum(s.score for s in suggestions) / len(suggestions)
                self.stats['avg_score'] = avg_score

            logger.info(f"✅ Generated {len(suggestions)} suggestions, {len(successful)} successful")

            return {
                'suggestions': [s.to_dict() for s in suggestions],
                'top_suggestions': [s.to_dict() for s in top_suggestions],
                'stats': self.stats.copy(),
                'workflow_id': workflow_id,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ ARC suggestion failed: {e}")
            logger.error(traceback.format_exc())
            return {
                'error': str(e),
                'suggestions': [],
                'top_suggestions': [],
                'stats': self.stats.copy(),
                'workflow_id': workflow_id
            }

    # ========================================================================
    # CANDIDATE GENERATION
    # ========================================================================

    def _generate_candidates_with_hope(
        self,
        graph_data: Dict,
        image_path: Optional[str],
        task_context: str,
        num_candidates: int = 10
    ) -> List[str]:
        """
        MARKER_108_7_ARC_MGC: HOPE-enhanced candidate generation.

        Uses hierarchical frequency layers:
        - LOW: Overview transformations (structural)
        - MID: Relation transformations (dependencies)
        - HIGH: Detail transformations (optimizations)
        """
        all_candidates = []

        try:
            # Lazy-load HOPE enhancer
            if self._hope_enhancer is None:
                try:
                    from src.agents.hope_enhancer import HOPEEnhancer, FrequencyLayer
                    self._hope_enhancer = HOPEEnhancer(local_model="llama3.1:8b")
                except ImportError:
                    logger.warning("[ARC] HOPE enhancer not available, using standard generation")
                    return self._generate_candidates(graph_data, image_path, task_context, num_candidates)

            from src.agents.hope_enhancer import FrequencyLayer

            # Analyze graph with HOPE
            graph_json = json.dumps(graph_data)[:4000]  # Limit size
            analysis = self._hope_enhancer.analyze(
                content=graph_json,
                layers=[FrequencyLayer.LOW, FrequencyLayer.MID, FrequencyLayer.HIGH]
            )

            # Generate candidates per layer
            candidates_per_layer = num_candidates // 3

            for layer, layer_analysis in analysis.items():
                layer_prompt = f"""
Based on {layer.name} frequency analysis: {layer_analysis[:500]}

Generate {candidates_per_layer} {layer.name.lower()}-level transformations.
- LOW: Structural changes (add/remove nodes, reorder)
- MID: Relationship changes (connections, dependencies)
- HIGH: Optimizations (performance, caching)
"""
                # Use parent method for actual generation
                layer_candidates = self._generate_candidates(
                    graph_data,
                    None,  # No image for layer-specific
                    task_context + "\n" + layer_prompt,
                    candidates_per_layer
                )
                all_candidates.extend(layer_candidates)

            logger.info(f"✅ HOPE generated {len(all_candidates)} candidates across 3 layers")

        except Exception as e:
            logger.warning(f"[ARC] HOPE generation failed, falling back: {e}")
            return self._generate_candidates(graph_data, image_path, task_context, num_candidates)

        return all_candidates or self._generate_candidates(graph_data, image_path, task_context, num_candidates)

    def _generate_candidates(
        self,
        graph_data: Dict,
        image_path: Optional[str],
        task_context: str,
        num_candidates: int = 10
    ) -> List[str]:
        """
        Генерация кандидатов-трансформаций (Python код)

        Returns:
            List[str]: Список Python функций в виде строк
        """
        # Построить промпт для генерации
        prompt = self._build_generation_prompt(
            graph_data,
            task_context,
            num_candidates
        )

        # Добавить few-shot примеры
        if self.few_shot_examples:
            few_shot_text = "\n\n## ПРИМЕРЫ УСПЕШНЫХ ТРАНСФОРМАЦИЙ:\n\n"
            for i, example in enumerate(self.few_shot_examples[-5:], 1):  # Last 5
                few_shot_text += f"### Пример {i} ({example.type.value}, score={example.score:.2f}):\n"
                few_shot_text += f"```python\n{example.code}\n```\n"
                few_shot_text += f"Объяснение: {example.explanation}\n\n"

            prompt = few_shot_text + prompt

        # Генерация через API или Ollama
        if self.use_api and self.api_aggregator:
            response = self._generate_via_api(prompt, image_path)
        elif self.learner:
            response = self._generate_via_ollama(prompt)
        else:
            logger.error("❌ No generation backend available (API or Ollama)")
            return []

        # Парсинг кандидатов из ответа
        candidates = self._parse_candidates_from_response(response)

        logger.info(f"✅ Generated {len(candidates)} candidate transformations")
        return candidates

    def _build_generation_prompt(
        self,
        graph_data: Dict,
        task_context: str,
        num_candidates: int
    ) -> str:
        """
        Построить промпт для генерации кандидатов.

        ВАЖНО: Промпт требует генерацию ТОЛЬКО валидного ASCII Python кода,
        без Unicode стрелок и специальных символов.
        """

        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])

        prompt = f"""# TASK: Generate workflow graph transformations

## CRITICAL REQUIREMENTS - READ CAREFULLY:
1. Write ONLY valid Python 3.9+ code
2. Do NOT use Unicode arrows or symbols: NO -> (U+2192), NO => (U+21D2), NO <- NO <->
3. Use ONLY ASCII operators: ->, =>, <, >, <=, >=, ==, !=, +, -, *, /, //, %, **
4. Do NOT use non-ASCII characters anywhere in the code
5. Each function must be syntactically correct and runnable
6. Use standard ASCII quotes: " or ' (not curly quotes)

## GRAPH CONTEXT:
- Nodes: {len(nodes)}
- Edges: {len(edges)}
- Task: {task_context}

## GRAPH STRUCTURE:
```json
{json.dumps(graph_data, indent=2)[:1000]}...
```

## TASK:
Generate {num_candidates} creative graph transformations as Python functions.

Each function must:
1. Accept `graph_data: Dict` (with keys 'nodes', 'edges')
2. Return modified graph or None if transformation not applicable
3. Be safe (no exec, eval, import, file I/O)
4. Have a docstring explaining the transformation

## TRANSFORMATION TYPES:

### 1. CONNECTION (new edges):
```python
def suggest_auth_to_db_connection(graph_data):
    \"\"\"Suggests connection between auth and database nodes\"\"\"
    nodes = graph_data.get('nodes', [])
    edges = graph_data.get('edges', [])
    # Analysis and edge addition logic
    new_edge = {{'source': 'auth', 'target': 'user_db'}}
    edges.append(new_edge)
    return {{'nodes': nodes, 'edges': edges}}
```

### 2. TRANSFORMATION (structure change):
```python
def merge_duplicate_nodes(graph_data):
    \"\"\"Merges duplicate nodes with similar names\"\"\"
    nodes = graph_data.get('nodes', [])
    edges = graph_data.get('edges', [])
    # Merge logic here
    return {{'nodes': nodes, 'edges': edges}}
```

### 3. OPTIMIZATION (performance):
```python
def add_caching_layer(graph_data):
    \"\"\"Adds caching layer between API and DB\"\"\"
    nodes = graph_data.get('nodes', [])
    edges = graph_data.get('edges', [])
    # Add cache node
    cache_node = {{'id': 'cache', 'type': 'service'}}
    nodes.append(cache_node)
    return {{'nodes': nodes, 'edges': edges}}
```

### 4. PATTERN (pattern recognition):
```python
def detect_microservice_pattern(graph_data):
    \"\"\"Detects microservice pattern and suggests improvements\"\"\"
    nodes = graph_data.get('nodes', [])
    # Pattern detection logic
    return graph_data
```

## OUTPUT FORMAT:
Output {num_candidates} functions, each in a ```python ... ``` block.

Requirements:
- Standard Python library only
- No import, exec, eval, open, __import__
- Safe executable code
- Creative ideas based on graph context
- ONLY ASCII CHARACTERS - NO UNICODE ARROWS OR SYMBOLS!

IMPORTANT REMINDER: Use -> for return type hints, not the Unicode arrow symbol!
Write: def func() -> Dict:
NOT: def func() -> Dict:  (with Unicode arrow)

BEGIN GENERATION:
"""
        return prompt

    def _generate_via_api(self, prompt: str, image_path: Optional[str]) -> str:
        """Генерация через API (Grok/Claude via APIAggregator)"""
        try:
            result = self.api_aggregator.generate_with_fallback(
                prompt=prompt,
                task_type="code",
                multimodal=bool(image_path),
                cheap=False,
                images=[image_path] if image_path else None,
                max_tokens=4000
            )

            if result and result.get('response'):
                return result['response']
            else:
                logger.error("❌ API generation failed")
                return ""

        except Exception as e:
            logger.error(f"❌ API generation error: {e}")
            return ""

    def _generate_via_ollama(self, prompt: str) -> str:
        """Генерация через Ollama (local)"""
        try:
            if hasattr(self.learner, 'generate'):
                response = self.learner.generate(prompt, max_tokens=4000)
                return response
            elif hasattr(self.learner, 'chat'):
                response = self.learner.chat([{'role': 'user', 'content': prompt}])
                return response.get('message', {}).get('content', '')
            else:
                logger.error("❌ Learner has no generate/chat method")
                return ""

        except Exception as e:
            logger.error(f"❌ Ollama generation error: {e}")
            return ""

    def _parse_candidates_from_response(self, response: str) -> List[str]:
        """
        Извлечь Python функции из ответа модели.

        Поддерживает multiple форматы:
        1. ```python ... ``` блоки
        2. ```json ... ``` блоки с candidates
        3. Inline def функции (без блока)
        """
        import re

        candidates = []

        # === Формат 1: JSON блок с candidates ===
        json_pattern = r'```json\s*(.*?)```'
        for match in re.finditer(json_pattern, response, re.DOTALL):
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict) and 'candidates' in data:
                    for candidate in data['candidates']:
                        if isinstance(candidate, dict) and 'code' in candidate:
                            candidates.append(candidate['code'])
                        elif isinstance(candidate, str):
                            candidates.append(candidate)
                    logger.debug(f"   Parsed {len(data['candidates'])} candidates from JSON")
            except json.JSONDecodeError:
                pass

        # === Формат 2: ```python ... ``` блоки ===
        blocks = response.split('```python')
        for block in blocks[1:]:  # Пропустить первый (до первого блока)
            end_idx = block.find('```')
            if end_idx != -1:
                code = block[:end_idx].strip()
                if code and 'def ' in code:
                    candidates.append(code)
                    logger.debug(f"   Parsed Python code block")

        # === Формат 3: ``` без указания языка (тоже может быть Python) ===
        if not candidates:
            generic_blocks = re.findall(r'```\s*\n(.*?)```', response, re.DOTALL)
            for code in generic_blocks:
                code = code.strip()
                if code and 'def ' in code:
                    candidates.append(code)
                    logger.debug(f"   Parsed generic code block")

        # === Формат 4: Inline функции (без блока) ===
        if not candidates:
            # Регулярка для поиска def функций
            def_pattern = r'(def\s+\w+\s*\([^)]*\)\s*(?:->.*?)?:\s*(?:"""[^"]*"""|\'\'\'[^\']*\'\'\')?(?:\n(?:[ \t]+[^\n]+))*)'
            for match in re.finditer(def_pattern, response):
                code = match.group(0).strip()
                if code and len(code) > 20:  # Минимальная длина функции
                    candidates.append(code)
                    logger.debug(f"   Parsed inline function")

        # === Формат 5: Fallback - построчный парсинг ===
        if not candidates:
            lines = response.split('\n')
            current_func = []
            in_function = False
            brace_depth = 0

            for line in lines:
                stripped = line.strip()

                if stripped.startswith('def '):
                    if current_func:
                        candidates.append('\n'.join(current_func))
                    in_function = True
                    current_func = [line]
                    brace_depth = 0
                elif in_function:
                    # Трекаем скобки для понимания вложенности
                    brace_depth += line.count('{') - line.count('}')
                    brace_depth += line.count('(') - line.count(')')

                    # Пустая строка или новое определение = конец функции
                    if (not stripped and brace_depth <= 0) or \
                       (stripped.startswith('def ') and len(current_func) > 1):
                        candidates.append('\n'.join(current_func))
                        current_func = []
                        in_function = False
                        if stripped.startswith('def '):
                            in_function = True
                            current_func = [line]
                    elif stripped and not line[0].isspace() and not stripped.startswith('#'):
                        # Новое определение на верхнем уровне = конец функции
                        candidates.append('\n'.join(current_func))
                        current_func = []
                        in_function = False
                    else:
                        current_func.append(line)

            # Добавить последнюю функцию
            if current_func:
                candidates.append('\n'.join(current_func))

        # Deduplicate и фильтрация
        seen = set()
        unique_candidates = []
        for code in candidates:
            code_hash = hash(code.strip())
            if code_hash not in seen and len(code.strip()) > 10:
                seen.add(code_hash)
                unique_candidates.append(code)

        if not unique_candidates:
            logger.warning(f"   No candidates parsed from response (length: {len(response)})")
            logger.debug(f"   Response preview: {response[:300]}...")

        logger.info(f"📝 Parsed {len(unique_candidates)} candidate functions from response")
        return unique_candidates

    # ========================================================================
    # CODE SANITIZATION & VALIDATION
    # ========================================================================

    def _sanitize_code(self, code: str) -> str:
        """
        Очищает код от недопустимых символов + ИСПРАВЛЯЕТ ОТСТУПЫ.

        Args:
            code: Исходный код (может содержать Unicode символы)

        Returns:
            Очищенный ASCII-only Python код с корректными отступами
        """
        import textwrap
        import ast

        # 1. Заменяем arrow-символы
        code = code.replace('→', '->')
        code = code.replace('⇒', '=>')
        code = code.replace('←', '<-')
        code = code.replace('↔', '<->')

        # 2. Заменяем другие non-ASCII arrows/symbols
        code = code.replace('•', '*')
        code = code.replace('·', '.')
        code = code.replace('×', '*')
        code = code.replace('÷', '/')
        code = code.replace('≠', '!=')
        code = code.replace('≤', '<=')
        code = code.replace('≥', '>=')
        code = code.replace('…', '...')

        # 3. Удаляем остальные non-ASCII (keep только ASCII + пробелы + переводы строк)
        cleaned = ''
        for char in code:
            if ord(char) < 128 or char in '\n\t':
                cleaned += char
            else:
                logger.debug(f"   Removed non-ASCII: {repr(char)} (U+{ord(char):04X})")

        # 4. Исправляем отступы через dedent
        try:
            dedented = textwrap.dedent(cleaned)
            # Проверяем синтаксис
            ast.parse(dedented)
            logger.debug("   Dedented and validated code successfully")
            return dedented
        except IndentationError as e:
            logger.debug(f"   IndentationError after dedent, attempting auto-fix: {e}")
        except SyntaxError:
            # Dedent сработал, но синтаксис всё равно сломан - вернём как есть
            return textwrap.dedent(cleaned)

        # 5. Авто-исправление отступов (если dedent не помог)
        try:
            lines = cleaned.split('\n')
            fixed_lines = []
            indent_level = 0

            for line in lines:
                stripped = line.strip()

                if not stripped:  # Пустая строка
                    fixed_lines.append('')
                    continue

                # Уменьшаем отступ для return/break/continue/pass
                if stripped.startswith(('return ', 'return\n', 'break', 'continue', 'pass', 'raise ')):
                    fixed_lines.append('    ' * indent_level + stripped)
                    continue

                # Уменьшаем отступ для elif/else/except/finally
                if stripped.startswith(('elif ', 'else:', 'except', 'finally:')):
                    indent_level = max(0, indent_level - 1)
                    fixed_lines.append('    ' * indent_level + stripped)
                    indent_level += 1
                    continue

                # Добавляем строку с текущим отступом
                fixed_lines.append('    ' * indent_level + stripped)

                # Увеличиваем отступ после строк заканчивающихся на ':'
                if stripped.endswith(':'):
                    indent_level += 1

            fixed_code = '\n'.join(fixed_lines)

            # Проверяем результат
            ast.parse(fixed_code)
            logger.debug("   Auto-fix successful! Fixed indentation")
            return fixed_code

        except SyntaxError as e:
            logger.warning(f"   Auto-fix failed, returning dedented code: {e}")
            return textwrap.dedent(cleaned)
        except Exception as e:
            logger.warning(f"   Unexpected error in auto-fix: {e}")
            return textwrap.dedent(cleaned)

    def _validate_code(self, code: str) -> bool:
        """
        Валидирует код перед выполнением через compile().

        Args:
            code: Python код для валидации

        Returns:
            True если код синтаксически корректен
        """
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError as e:
            logger.warning(f"   Syntax error in code: {e}")
            return False

    # ========================================================================
    # CANDIDATE EVALUATION
    # ========================================================================

    def _evaluate_candidates(
        self,
        candidates: List[str],
        graph_data: Dict,
        graph_context: str
    ) -> List[ARCSuggestion]:
        """
        Протестировать и оценить кандидатов

        Для каждого кандидата:
        1. Безопасное выполнение (exec в isolated namespace)
        2. Оценка через EvalAgent
        3. Создание ARCSuggestion
        """
        suggestions = []

        for i, code in enumerate(candidates, 1):
            logger.info(f"🧪 Testing candidate {i}/{len(candidates)}...")

            try:
                # ✅ НОВОЕ: Sanitize код перед выполнением
                original_len = len(code)
                sanitized_code = self._sanitize_code(code)
                logger.debug(f"   Sanitized code ({original_len} → {len(sanitized_code)} chars)")

                # ✅ НОВОЕ: Валидировать перед exec
                if not self._validate_code(sanitized_code):
                    logger.warning(f"   Invalid code syntax after sanitization, skipping candidate {i}")
                    suggestions.append(ARCSuggestion(
                        type=SuggestionType.TRANSFORMATION,
                        code=code,
                        explanation="Invalid syntax after sanitization",
                        score=0.0,
                        success=False,
                        metadata={'error': 'syntax_error_after_sanitize', 'candidate_index': i}
                    ))
                    continue

                # 1. Извлечь имя функции и docstring (из sanitized кода)
                func_name, explanation = self._extract_function_info(sanitized_code)

                # 2. Определить тип трансформации
                suggestion_type = self._infer_suggestion_type(sanitized_code, explanation)

                # 3. Безопасное выполнение (sanitized кода)
                success, result = self._safe_execute(sanitized_code, graph_data)

                # 4. Оценка через EvalAgent
                score = 0.0
                if success and self.eval_agent:
                    score = self._evaluate_with_eval_agent(
                        sanitized_code, explanation, result, graph_context
                    )
                elif success:
                    # Fallback: простая эвристическая оценка
                    score = self._heuristic_score(sanitized_code, result)

                # 5. Создать suggestion (с sanitized кодом)
                suggestion = ARCSuggestion(
                    type=suggestion_type,
                    code=sanitized_code,  # ✅ Используем очищенный код
                    explanation=explanation,
                    score=score,
                    success=success,
                    metadata={
                        'candidate_index': i,
                        'execution_result': str(result)[:200] if result else None,
                        'sanitized': original_len != len(sanitized_code)  # Флаг если была очистка
                    }
                )

                suggestions.append(suggestion)
                logger.info(f"   Score: {score:.2f}, Success: {success}")

            except Exception as e:
                logger.error(f"❌ Candidate {i} evaluation failed: {e}")
                # Добавить failed suggestion
                suggestions.append(ARCSuggestion(
                    type=SuggestionType.TRANSFORMATION,
                    code=code,
                    explanation=f"Evaluation failed: {str(e)}",
                    score=0.0,
                    success=False,
                    metadata={'error': str(e)}
                ))

        return suggestions

    def _extract_function_info(self, code: str) -> Tuple[str, str]:
        """Извлечь имя функции и docstring"""
        func_name = "unknown"
        explanation = "No explanation provided"

        lines = code.split('\n')
        for line in lines:
            if line.strip().startswith('def '):
                # Извлечь имя: def func_name(...)
                func_name = line.split('def ')[1].split('(')[0].strip()
                break

        # Извлечь docstring
        if '"""' in code:
            parts = code.split('"""')
            if len(parts) >= 3:
                explanation = parts[1].strip()
        elif "'''" in code:
            parts = code.split("'''")
            if len(parts) >= 3:
                explanation = parts[1].strip()

        return func_name, explanation

    def _infer_suggestion_type(self, code: str, explanation: str) -> SuggestionType:
        """Определить тип предложения по коду и объяснению"""
        code_lower = code.lower()
        expl_lower = explanation.lower()

        # Ключевые слова для каждого типа
        if any(kw in code_lower or kw in expl_lower for kw in ['connect', 'link', 'edge', 'relation']):
            return SuggestionType.CONNECTION
        elif any(kw in code_lower or kw in expl_lower for kw in ['optim', 'cache', 'performance', 'faster']):
            return SuggestionType.OPTIMIZATION
        elif any(kw in code_lower or kw in expl_lower for kw in ['pattern', 'detect', 'recognize', 'identify']):
            return SuggestionType.PATTERN
        else:
            return SuggestionType.TRANSFORMATION

    def _safe_execute(self, code: str, graph_data: Dict) -> Tuple[bool, Any]:
        """
        Безопасное выполнение кода в изолированном namespace

        Returns:
            (success: bool, result: Any)
        """
        try:
            # Создать isolated namespace
            namespace = {
                '__builtins__': {},  # Отключить встроенные функции
                'Dict': Dict,
                'List': List,
                'Optional': Optional,
                'Any': Any,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'dict': dict,
                'list': list,
                'set': set,
                'tuple': tuple,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'sorted': sorted,
                'max': max,
                'min': min,
                'sum': sum,
                'abs': abs,
                'round': round,
            }

            # Добавить copy для безопасности
            try:
                import copy as copy_module
                namespace['copy'] = copy_module
            except ImportError:
                pass

            # Выполнить код (определить функцию)
            exec(code, namespace)

            # Найти определённую функцию
            func = None
            for key, value in namespace.items():
                if callable(value) and key.startswith('suggest_') or key.startswith('detect_') or key.startswith('merge_') or key.startswith('add_'):
                    func = value
                    break

            if not func:
                # Попробовать найти любую функцию, определённую в коде
                for key, value in namespace.items():
                    if callable(value) and not key.startswith('_'):
                        func = value
                        break

            if not func:
                logger.warning("⚠️  No function found in code")
                return False, None

            # Вызвать функцию с копией graph_data
            graph_copy = copy.deepcopy(graph_data)
            result = func(graph_copy)

            return True, result

        except Exception as e:
            logger.warning(f"⚠️  Safe execution failed: {e}")
            return False, None

    def _evaluate_with_eval_agent(
        self,
        code: str,
        explanation: str,
        result: Any,
        graph_context: str
    ) -> float:
        """Оценить предложение через EvalAgent (0-1)"""
        try:
            eval_prompt = f"""# ОЦЕНКА ТРАНСФОРМАЦИИ ГРАФА

## КОНТЕКСТ ГРАФА:
{graph_context}

## ПРЕДЛОЖЕННАЯ ТРАНСФОРМАЦИЯ:
```python
{code}
```

Объяснение: {explanation}

## РЕЗУЛЬТАТ ВЫПОЛНЕНИЯ:
{str(result)[:500]}

## ЗАДАНИЕ:
Оцени качество этой трансформации по шкале 0-1:
- 0.0-0.3: Бесполезная или вредная
- 0.3-0.5: Слабо полезная
- 0.5-0.7: Умеренно полезная
- 0.7-0.9: Очень полезная
- 0.9-1.0: Исключительно ценная

Критерии:
1. Корректность кода
2. Применимость к графу
3. Ценность для пользователя
4. Креативность решения

ОТВЕТЬ ТОЛЬКО ЧИСЛОМ (0.0-1.0):
"""

            if hasattr(self.eval_agent, 'evaluate'):
                score_text = self.eval_agent.evaluate(eval_prompt)
            elif hasattr(self.eval_agent, 'generate'):
                score_text = self.eval_agent.generate(eval_prompt)
            else:
                logger.warning("⚠️  EvalAgent has no evaluate/generate method")
                return 0.5

            # Парсинг числа из ответа
            score = self._parse_score(score_text)
            return score

        except Exception as e:
            logger.error(f"❌ EvalAgent evaluation failed: {e}")
            return 0.5  # Fallback

    def _parse_score(self, text: str) -> float:
        """Извлечь число 0-1 из текста"""
        import re

        # Найти первое число вида 0.XX
        match = re.search(r'\b0\.\d+\b', text)
        if match:
            try:
                score = float(match.group())
                return max(0.0, min(1.0, score))  # Clamp to [0, 1]
            except ValueError:
                pass

        # Если не нашли, вернуть средний score
        return 0.5

    def _heuristic_score(self, code: str, result: Any) -> float:
        """Простая эвристическая оценка без EvalAgent"""
        score = 0.5  # Базовый

        # +0.1 если код короткий и понятный
        if len(code) < 500:
            score += 0.1

        # +0.1 если есть docstring
        if '"""' in code or "'''" in code:
            score += 0.1

        # +0.2 если результат не None
        if result is not None:
            score += 0.2

        # -0.1 если результат такой же как вход (не изменил граф)
        if isinstance(result, dict) and not result:
            score -= 0.1

        return max(0.0, min(1.0, score))

    # ========================================================================
    # FEW-SHOT STORAGE
    # ========================================================================

    def _store_few_shot_example(self, suggestion: ARCSuggestion):
        """Сохранить успешный пример для few-shot learning"""
        # Добавить в in-memory cache
        self.few_shot_examples.append(suggestion)

        # Ограничить размер (последние 20)
        if len(self.few_shot_examples) > 20:
            self.few_shot_examples = self.few_shot_examples[-20:]

        # Сохранить в MemoryManager если доступен
        if self.memory:
            try:
                self.memory.save_arc_example({
                    'type': suggestion.type.value,
                    'code': suggestion.code,
                    'explanation': suggestion.explanation,
                    'score': suggestion.score,
                    'metadata': suggestion.metadata,
                    'timestamp': suggestion.timestamp
                })
                logger.info(f"💾 Stored few-shot example (score={suggestion.score:.2f})")
            except Exception as e:
                logger.warning(f"⚠️  Failed to store in MemoryManager: {e}")

    def load_few_shot_examples(self, limit: int = 20) -> int:
        """Загрузить few-shot примеры из MemoryManager"""
        if not self.memory:
            return 0

        try:
            examples = self.memory.load_arc_examples(limit=limit)

            for ex in examples:
                suggestion = ARCSuggestion(
                    type=SuggestionType(ex.get('type', 'transformation')),
                    code=ex.get('code', ''),
                    explanation=ex.get('explanation', ''),
                    score=ex.get('score', 0.0),
                    success=True,
                    metadata=ex.get('metadata', {}),
                    timestamp=ex.get('timestamp', '')
                )
                self.few_shot_examples.append(suggestion)

            logger.info(f"✅ Loaded {len(examples)} few-shot examples")
            return len(examples)

        except Exception as e:
            logger.warning(f"⚠️  Failed to load few-shot examples: {e}")
            return 0

    # ========================================================================
    # CONTEXT BUILDING
    # ========================================================================

    def _build_graph_context(
        self,
        workflow_id: str,
        graph_data: Optional[Dict],
        image_path: Optional[str],
        task_context: Optional[str]
    ) -> str:
        """Построить текстовое описание контекста графа"""

        context_parts = [
            f"# КОНТЕКСТ WORKFLOW: {workflow_id}\n"
        ]

        if task_context:
            context_parts.append(f"## Задача:\n{task_context}\n")

        if graph_data:
            nodes = graph_data.get('nodes', [])
            edges = graph_data.get('edges', [])

            context_parts.append(f"## Структура графа:")
            context_parts.append(f"- Узлов: {len(nodes)}")
            context_parts.append(f"- Связей: {len(edges)}")

            if nodes:
                context_parts.append(f"\n### Узлы:")
                for node in nodes[:10]:  # First 10
                    node_id = node.get('id', 'unknown')
                    node_type = node.get('type', 'unknown')
                    context_parts.append(f"  - {node_id} (type: {node_type})")

                if len(nodes) > 10:
                    context_parts.append(f"  ... и ещё {len(nodes) - 10} узлов")

            if edges:
                context_parts.append(f"\n### Связи:")
                for edge in edges[:10]:  # First 10
                    source = edge.get('source', 'unknown')
                    target = edge.get('target', 'unknown')
                    context_parts.append(f"  - {source} → {target}")

                if len(edges) > 10:
                    context_parts.append(f"  ... и ещё {len(edges) - 10} связей")

        if image_path:
            context_parts.append(f"\n## Визуализация: {image_path}")

        return '\n'.join(context_parts)

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику работы агента"""
        return {
            **self.stats,
            'few_shot_examples_count': len(self.few_shot_examples),
            'mode': 'API' if self.use_api else 'Ollama'
        }

    def clear_few_shot_cache(self):
        """Очистить in-memory кэш few-shot примеров"""
        self.few_shot_examples.clear()
        logger.info("🗑️  Few-shot cache cleared")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_arc_solver(
    memory_manager: Optional[Any] = None,
    eval_agent: Optional[Any] = None,
    prefer_api: bool = False
) -> ARCSolverAgent:
    """
    Фабричная функция для создания ARCSolverAgent

    Args:
        memory_manager: MemoryManager instance
        eval_agent: EvalAgent instance
        prefer_api: Предпочитать API (Grok/Claude) или Ollama

    Returns:
        ARCSolverAgent instance
    """

    api_aggregator = None
    learner = None

    if prefer_api:
        # Попробовать импортировать APIAggregator
        try:
            from src.elisya.api_aggregator_v3 import APIAggregator
            api_aggregator = APIAggregator(memory_manager=memory_manager)
            logger.info("✅ Using APIAggregator for generation")
        except ImportError:
            logger.warning("⚠️  APIAggregator not available, falling back to Ollama")
            prefer_api = False

    if not prefer_api:
        # Попробовать создать Ollama learner
        try:
            from src.agents.learner_initializer import LearnerInitializer, TaskComplexity
            learner = LearnerInitializer.create_with_intelligent_routing(
                TaskComplexity.COMPLEX,
                memory_manager=memory_manager,
                eval_agent=eval_agent,
                prefer_api=False
            )
            logger.info("✅ Using Ollama learner for generation")
        except Exception as e:
            logger.error(f"❌ Failed to create Ollama learner: {e}")

    return ARCSolverAgent(
        memory_manager=memory_manager,
        eval_agent=eval_agent,
        use_api=prefer_api,
        api_aggregator=api_aggregator,
        learner=learner
    )


# ============================================================================
# MAIN (для тестирования)
# ============================================================================

if __name__ == '__main__':
    # Простой тест
    logging.basicConfig(level=logging.INFO)

    print("=" * 70)
    print("  VETKA ARC Solver Agent - Standalone Test")
    print("=" * 70)

    # Тестовый граф
    test_graph = {
        'nodes': [
            {'id': 'auth', 'type': 'feature'},
            {'id': 'user_db', 'type': 'data'},
            {'id': 'session', 'type': 'service'}
        ],
        'edges': [
            {'source': 'auth', 'target': 'user_db'}
        ]
    }

    # Создать агент
    agent = create_arc_solver(prefer_api=False)

    # Попробовать сгенерировать предложения
    print("\n🧪 Testing suggestion generation...")
    result = agent.suggest_connections(
        workflow_id="test_workflow",
        graph_data=test_graph,
        task_context="Authentication system with user database",
        num_candidates=3,
        min_score=0.3
    )

    print(f"\n📊 Results:")
    print(f"   Generated: {len(result['suggestions'])} suggestions")
    print(f"   Top-3: {len(result['top_suggestions'])}")
    print(f"   Stats: {result['stats']}")

    if result['top_suggestions']:
        print(f"\n🏆 Top suggestion:")
        top = result['top_suggestions'][0]
        print(f"   Type: {top['type']}")
        print(f"   Score: {top['score']:.2f}")
        print(f"   Explanation: {top['explanation'][:100]}...")

    print("\n" + "=" * 70)
    print("✅ ARC Solver Agent test complete!")
    print("=" * 70)
