#!/usr/bin/env python3
"""
VETKA Phase 8.0 - SmartLearner
Intelligent model selection based on task category

REAL MODELS (all loaded and working):
- deepseek-llm:7b (Ollama) - main reasoning/code
- llama3.1:8b (Ollama) - vision fallback, HOPE pattern
- qwen2:7b (Ollama) - fast fallback
- embeddinggemma:300m (Ollama) - embeddings
- pixtral-12b (HuggingFace ~/pixtral-12b/) - advanced multimodal

@status: active
@phase: 96
@depends: logging, enum
@used_by: learner_initializer, orchestrator
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum, auto

logger = logging.getLogger(__name__)


class TaskCategory(Enum):
    """Task categories for model routing"""
    REASONING = auto()    # Complex reasoning, planning
    CODE = auto()         # Code generation, analysis
    VISION = auto()       # Image understanding
    EMBEDDINGS = auto()   # Vector embeddings
    FAST = auto()         # Quick responses
    GENERAL = auto()      # General assistant


class SmartLearner:
    """
    Smart model selection based on task category and complexity.

    Phase 8.0: Routes tasks to optimal models based on:
    - Task category (CODE, REASONING, VISION, etc.)
    - Complexity level
    - Model availability
    - Fallback strategies
    """

    # Default model configuration - REAL MODELS
    DEFAULT_MODEL_CONFIG = {
        TaskCategory.REASONING: {
            'primary': 'deepseek-llm:7b',
            'fallback': 'qwen2:7b',
            'api_fallback': 'anthropic/claude-3.5-sonnet',  # via OpenRouter
        },
        TaskCategory.CODE: {
            'primary': 'deepseek-llm:7b',
            'fallback': 'deepseek-coder:6.7b',
            'api_fallback': 'anthropic/claude-3.5-sonnet',  # via OpenRouter
        },
        TaskCategory.VISION: {
            'primary': 'pixtral-12b',           # HuggingFace ~/pixtral-12b/
            'fallback': 'llama3.1:8b',          # Ollama fallback
            'api_fallback': 'google/gemini-2.0-flash-exp',  # via OpenRouter
        },
        TaskCategory.EMBEDDINGS: {
            'primary': 'embeddinggemma:300m',
            'fallback': 'nomic-embed-text',
            'api_fallback': 'openai/text-embedding-3-small',
        },
        TaskCategory.FAST: {
            'primary': 'qwen2:7b',
            'fallback': 'deepseek-llm:7b',
            'api_fallback': 'anthropic/claude-3.5-haiku',  # via OpenRouter
        },
        TaskCategory.GENERAL: {
            'primary': 'qwen2:7b',
            'fallback': 'deepseek-llm:7b',
            'api_fallback': 'anthropic/claude-3.5-sonnet',  # via OpenRouter
        },
    }

    # Task classification keywords
    CATEGORY_KEYWORDS = {
        TaskCategory.REASONING: [
            'analyze', 'explain', 'why', 'how does', 'reason',
            'plan', 'strategy', 'think', 'solve', 'compare'
        ],
        TaskCategory.CODE: [
            'code', 'function', 'class', 'implement', 'fix bug',
            'refactor', 'python', 'javascript', 'typescript', 'debug',
            'algorithm', 'api', 'database', 'sql'
        ],
        TaskCategory.VISION: [
            'image', 'picture', 'photo', 'screenshot', 'diagram',
            'visual', 'see', 'look at', 'describe image'
        ],
        TaskCategory.EMBEDDINGS: [
            'embed', 'vector', 'similarity', 'search', 'semantic',
            'cluster', 'encode'
        ],
        TaskCategory.FAST: [
            'quick', 'simple', 'short', 'one word', 'yes or no',
            'brief', 'summarize'
        ],
    }

    def __init__(
        self,
        model_config: Optional[Dict] = None,
        available_models: Optional[List[str]] = None,
        use_api_fallback: bool = True
    ):
        """
        Initialize SmartLearner.

        Args:
            model_config: Custom model configuration (overrides defaults)
            available_models: List of currently available Ollama models
            use_api_fallback: Whether to use API models as last resort
        """
        self.model_config = model_config or self.DEFAULT_MODEL_CONFIG.copy()
        self.available_models = available_models or []
        self.use_api_fallback = use_api_fallback
        self._model_usage_stats = {}

    def classify_task(self, task: str) -> TaskCategory:
        """
        Classify task into a category based on keywords.

        Args:
            task: The task description

        Returns:
            TaskCategory enum value
        """
        task_lower = task.lower()

        # Score each category
        scores = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in task_lower)
            scores[category] = score

        # Find best match
        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]

        # If no strong match, default to GENERAL
        if best_score == 0:
            return TaskCategory.GENERAL

        return best_category

    def select_model(
        self,
        task: str,
        category: Optional[TaskCategory] = None,
        complexity: str = "MEDIUM",
        require_local: bool = False
    ) -> Dict[str, Any]:
        """
        Select optimal model for a task.

        Args:
            task: Task description
            category: Optional pre-classified category
            complexity: MICRO/SMALL/MEDIUM/LARGE/EPIC
            require_local: If True, never use API fallback

        Returns:
            {
                'model': 'model_name',
                'category': TaskCategory,
                'is_local': True/False,
                'fallback_chain': ['model1', 'model2', ...]
            }
        """
        # Classify task if not provided
        if category is None:
            category = self.classify_task(task)

        # Get model config for category
        config = self.model_config.get(category, self.model_config[TaskCategory.GENERAL])

        # Build fallback chain
        fallback_chain = []

        # Try primary model
        primary = config.get('primary')
        if primary and self._is_model_available(primary):
            selected_model = primary
            is_local = True
        # Try fallback model
        elif config.get('fallback') and self._is_model_available(config['fallback']):
            selected_model = config['fallback']
            is_local = True
            fallback_chain.append(primary)
        # Try API fallback
        elif self.use_api_fallback and not require_local and config.get('api_fallback'):
            selected_model = config['api_fallback']
            is_local = False
            fallback_chain.extend([primary, config.get('fallback')])
        # Last resort: use primary anyway (Ollama will handle error)
        else:
            selected_model = primary
            is_local = True
            logger.warning(f"No available model found for {category}, using {primary}")

        # Complexity adjustment
        if complexity in ['LARGE', 'EPIC'] and not is_local:
            # For complex tasks, prefer more capable API models
            if 'haiku' in selected_model:
                selected_model = selected_model.replace('haiku', 'sonnet')

        # Track usage
        self._track_usage(selected_model, category)

        result = {
            'model': selected_model,
            'category': category.name,
            'is_local': is_local,
            'fallback_chain': fallback_chain,
            'complexity': complexity,
        }

        logger.debug(f"SmartLearner selected: {selected_model} for {category.name}")
        return result

    def _is_model_available(self, model_name: str) -> bool:
        """Check if a model is available locally."""
        if not self.available_models:
            return True  # Assume available if no list provided

        # Check exact match or base name match
        base_name = model_name.split(':')[0]
        return any(
            model_name in m or base_name in m
            for m in self.available_models
        )

    def _track_usage(self, model: str, category: TaskCategory):
        """Track model usage statistics."""
        key = f"{model}_{category.name}"
        self._model_usage_stats[key] = self._model_usage_stats.get(key, 0) + 1

    def update_available_models(self, models: List[str]):
        """Update list of available models."""
        self.available_models = models
        logger.info(f"SmartLearner: Updated available models ({len(models)} total)")

    def get_usage_stats(self) -> Dict[str, int]:
        """Get model usage statistics."""
        return self._model_usage_stats.copy()

    def get_model_for_category(self, category: TaskCategory) -> str:
        """Direct access to primary model for a category."""
        config = self.model_config.get(category, self.model_config[TaskCategory.GENERAL])
        return config.get('primary', 'qwen2:7b')

    def batch_classify(self, tasks: List[str]) -> List[Dict[str, Any]]:
        """
        Classify and select models for multiple tasks.

        Args:
            tasks: List of task descriptions

        Returns:
            List of selection results
        """
        return [self.select_model(task) for task in tasks]


def smart_learner_factory(
    available_models: Optional[List[str]] = None,
    use_api_fallback: bool = True
) -> SmartLearner:
    """Factory for creating SmartLearner instance."""
    return SmartLearner(
        available_models=available_models,
        use_api_fallback=use_api_fallback
    )


# Convenience function for quick model selection
def select_model_for_task(task: str, **kwargs) -> str:
    """Quick helper to get model name for a task."""
    learner = SmartLearner(**kwargs)
    result = learner.select_model(task)
    return result['model']
