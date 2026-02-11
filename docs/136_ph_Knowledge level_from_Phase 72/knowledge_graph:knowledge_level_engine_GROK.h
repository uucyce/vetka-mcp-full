**Отлично!** Вот **полный готовый код**, который ты просил.

Я сделал всё в твоём стиле: чисто, серьёзно, минималистично, с комментариями и готово к интеграции.

---

### 1. Новый файл: `src/knowledge_graph/knowledge_level_engine.py`

Создай этот файл:

```python
"""
KnowledgeLevelEngine — Универсальный расчёт уровня знаний (Knowledge Level)

Phase 72.5
Y = f(время + knowledge_level)
0.0 = фундаментальный первоисточник
1.0 = продвинутый, производный, поздний концепт

Поддерживает все типы данных: код, документы, видео, книги, сценарии.
"""

import math
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeLevelConfig:
    """Настраиваемые веса для разных типов контента"""
    temporal: float = 0.35      # Время создания (новее = выше)
    dependency: float = 0.30    # Сколько от узла зависит (входящие связи)
    complexity: float = 0.20    # Сложность (размер, embedding norm, loc и т.д.)
    rrf: float = 0.15           # RRF из гибридного поиска
    type_multiplier: Dict[str, float] = None  # Специфика для типа контента

    def __post_init__(self):
        if self.type_multiplier is None:
            self.type_multiplier = {
                "code": 1.0,
                "doc": 0.9,
                "media": 0.85,
                "book": 0.95,
                "script": 0.88
            }


class KnowledgeLevelEngine:
    """
    Универсальный движок расчёта Knowledge Level
    Работает для любого типа контента
    """

    def __init__(self, config: Optional[KnowledgeLevelConfig] = None):
        self.config = config or KnowledgeLevelConfig()
        logger.info("[KnowledgeLevelEngine] Initialized with weights: "
                   f"T={self.config.temporal:.2f}, D={self.config.dependency:.2f}, "
                   f"C={self.config.complexity:.2f}, R={self.config.rrf:.2f}")

    def calculate(self, node: Dict[str, Any]) -> float:
        """
        Основной метод: возвращает Knowledge Level [0.0 — 1.0]
        
        node должен содержать:
        - created_at / created_time (timestamp)
        - in_degree (кол-во входящих prerequisite)
        - embedding_norm (норма эмбеддинга)
        - loc / size / section_count (опционально)
        - rrf_score (из гибридного поиска)
        - type: 'code', 'doc', 'media' и т.д.
        """
        score = 0.0

        # 1. Temporal (новее = выше)
        created = node.get("created_at") or node.get("created_time") or 0
        age_score = self._normalize_time(created)
        score += self.config.temporal * age_score

        # 2. Dependency (сколько от него зависит)
        in_degree = node.get("in_degree", 0)
        dep_score = min(1.0, in_degree / 15.0)          # насыщение после 15 зависимостей
        score += self.config.dependency * dep_score

        # 3. Complexity
        embedding_norm = node.get("embedding_norm", 0)
        complexity = min(1.0, embedding_norm / 50.0)

        # Дополнительные сигналы сложности
        if node.get("type") == "code":
            complexity += min(0.4, node.get("loc", 0) / 1500)
        elif node.get("type") == "doc":
            complexity += min(0.35, node.get("section_count", 0) / 25)

        score += self.config.complexity * min(1.0, complexity)

        # 4. RRF boost
        rrf = node.get("rrf_score", 0.0)
        score += self.config.rrf * rrf

        # Типовой множитель
        node_type = node.get("type", "unknown")
        multiplier = self.config.type_multiplier.get(node_type, 1.0)
        score *= multiplier

        # Финальная нормализация + мягкий sigmoid
        final_kl = 0.08 + 0.92 * (1 / (1 + math.exp(-9 * (score - 0.48))))

        return round(final_kl, 4)

    def _normalize_time(self, timestamp: Any) -> float:
        """Нормализует время создания в [0, 1] (новее = ближе к 1)"""
        if not timestamp:
            return 0.5

        try:
            ts = float(timestamp)
            # Здесь можно добавить глобальный min/max из всей базы
            # Пока простая нормализация по разумному диапазону
            normalized = (ts % 1_000_000_000) / 1_000_000_000
            return min(1.0, max(0.0, normalized))
        except:
            return 0.5

    def batch_calculate(self, nodes: Dict[str, Dict]) -> Dict[str, float]:
        """Массовый расчёт для всех узлов"""
        return {node_id: self.calculate(node_data) for node_id, node_data in nodes.items()}

    def get_stats(self, knowledge_levels: Dict[str, float]) -> Dict:
        """Статистика распределения KL"""
        values = list(knowledge_levels.values())
        return {
            "count": len(values),
            "min": round(min(values), 3),
            "max": round(max(values), 3),
            "mean": round(sum(values) / len(values), 3),
            "foundational": sum(1 for v in values if v < 0.35),
            "advanced": sum(1 for v in values if v > 0.75)
        }
```

---

### 2. Патч для `semantic_dag_builder.py`

В классе `SemanticDAGBuilder` добавь в конец метода `build_semantic_tree()` (перед `return`):

```python
        # MARKER_72.5_KNOWLEDGE_LEVEL: Calculate universal Knowledge Level
        logger.info("[SemanticDAG] Step 6: Calculating Knowledge Levels (Phase 72.5)...")
        from src.knowledge_graph.knowledge_level_engine import KnowledgeLevelEngine
        
        engine = KnowledgeLevelEngine()
        
        # Подготавливаем данные для engine
        node_data_for_kl = {}
        for node_id, node in self.semantic_nodes.items():
            node_data_for_kl[node_id] = {
                "type": node.type,
                "created_at": node.metadata.get("created_at", 0) if hasattr(node, "metadata") else 0,
                "in_degree": self._get_in_degree(node_id),
                "embedding_norm": float(np.linalg.norm(node.embedding)) if node.embedding is not None else 0,
                "loc": node.metadata.get("loc", 0) if hasattr(node, "metadata") else 0,
                "section_count": node.metadata.get("section_count", 0) if hasattr(node, "metadata") else 0,
                "rrf_score": node.metadata.get("rrf_score", 0.0) if hasattr(node, "metadata") else 0.0,
            }
        
        knowledge_levels = engine.batch_calculate(node_data_for_kl)
        
        # Применяем KL к узлам
        for node_id, kl in knowledge_levels.items():
            if node_id in self.semantic_nodes:
                self.semantic_nodes[node_id].knowledge_level = kl
        
        # Логируем статистику
        stats = engine.get_stats(knowledge_levels)
        logger.info(f"[SemanticDAG] Knowledge Levels: {stats}")
        
        return self.semantic_nodes, self.semantic_edges
```

Также добавь вспомогательный метод в класс (можно в конец):

```python
    def _get_in_degree(self, node_id: str) -> int:
        """Считает количество входящих prerequisite ребёр"""
        count = 0
        for edge in self.semantic_edges:
            if edge.target == node_id and edge.type == 'prerequisite':
                count += 1
        return count
```

---

### 3. Как красиво показать KL в DevPanel

**Рекомендую** добавить мини-визуализацию **вкладки "Statistics"** или новую вкладку **"Knowledge Map"**.

Вот готовый компонент `KnowledgeLevelChart.tsx` (добавь в `src/components/dev/`):

```tsx
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';

const KL_COLORS = ['#4a6', '#6a8', '#8aa', '#aab', '#ccd']; // от низкого к высокому KL

export function KnowledgeLevelChart({ knowledgeLevels }: { knowledgeLevels: Record<string, number> }) {
  // Группируем по уровням (0.0-0.2, 0.2-0.4, ...)
  const buckets = Array.from({ length: 5 }, (_, i) => ({
    range: `${(i * 0.2).toFixed(1)}–${((i + 1) * 0.2).toFixed(1)}`,
    count: 0,
    color: KL_COLORS[i]
  }));

  Object.values(knowledgeLevels).forEach(kl => {
    const bucketIndex = Math.min(4, Math.floor(kl / 0.2));
    buckets[bucketIndex].count++;
  });

  return (
    <div style={{ padding: '12px 16px' }}>
      <div style={{ color: '#aaa', fontSize: 12, marginBottom: 8 }}>
        Knowledge Level Distribution
      </div>

      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={buckets} layout="vertical">
          <XAxis type="number" stroke="#555" />
          <YAxis type="category" dataKey="range" stroke="#555" width={60} />
          <Tooltip 
            formatter={(value) => [`${value} nodes`, 'Count']}
            labelFormatter={(label) => `KL ${label}`}
          />
          <Bar dataKey="count" radius={[0, 4, 4, 0]}>
            {buckets.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 11, color: '#666' }}>
        <span>Foundational</span>
        <span>Advanced</span>
      </div>
    </div>
  );
}
```

**Как подключить в DevPanel:**

В `DevPanel.tsx` добавь в `activeTab === 'stats'`:

```tsx
{activeTab === 'stats' && (
  <>
    <PipelineStatsChart tasks={tasks} />
    {knowledgeLevels && <KnowledgeLevelChart knowledgeLevels={knowledgeLevels} />}
  </>
)}
```

(передавай `knowledgeLevels` из бэкенда через API `/api/debug/knowledge-levels`)

---

Готово!

Хочешь, я сейчас добавлю:
- Полный endpoint для `/api/debug/knowledge-levels`
- Или улучшенный вариант визуализации (sparkline + средний KL)

Просто скажи. Мы на очень хорошем ходу.