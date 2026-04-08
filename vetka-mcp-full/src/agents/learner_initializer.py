"""
VETKA Phase 8.0 - Hybrid Learner Initializer
Local models for inference + API models for teaching/distillation

Architecture:
- LOCAL (inference): DeepSeek-LLM-7B, Llama3.1-8B, Qwen2-7B via Ollama
- LOCAL (vision): Pixtral-12B via HuggingFace (~pixtral-12b/)
- API (teaching): Claude 3.5, GPT-4o-mini, Gemini-2.0 via OpenRouter (9 rotating keys)
- Routing: By task complexity + availability
- Distillation: API teaches local via few-shot + periodic LoRA

REAL MODELS (all loaded and working):
- deepseek-llm:7b (Ollama) - main reasoning/code
- llama3.1:8b (Ollama) - vision fallback, HOPE pattern
- qwen2:7b (Ollama) - fast fallback
- embeddinggemma:300m (Ollama) - embeddings
- pixtral-12b (HuggingFace ~/pixtral-12b/) - advanced multimodal

@status: active
@phase: 96
@depends: learner_factory, os, logging
@used_by: orchestrator, arc_solver_agent
"""

import os
import logging
from typing import Optional, Dict, Any, List, Literal
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Task complexity levels for intelligent routing"""
    SIMPLE = "simple"      # < 10 words, quick queries → Qwen
    MEDIUM = "medium"      # 10-30 words, moderate tasks → DeepSeek
    COMPLEX = "complex"    # > 30 words, graphs/analysis → DeepSeek + sparse attention
    EXPERT = "expert"      # Visual/hierarchical → API Grok-4 or HOPE


class ModelBackend(Enum):
    """Model backend types"""
    LOCAL_OLLAMA = "ollama"
    API_OPENROUTER = "openrouter"  # All API models via OpenRouter proxy


@dataclass
class LearnerConfig:
    """Configuration for a learner model"""
    name: str
    backend: ModelBackend
    model_id: str
    memory_gb: int
    tokens_per_sec: int
    supports_vision: bool
    supports_sparse_attention: bool = False
    supports_self_modifying: bool = False
    best_for: List[TaskComplexity] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)
    description: str = ""
    init_params: Dict[str, Any] = field(default_factory=dict)


class LearnerInitializer:
    """
    Universal initializer supporting hybrid (local + OpenRouter API) learners
    Local: DeepSeek-LLM-7B, Llama3.1-8B, Qwen2-7B via Ollama
    Vision: Pixtral-12B via HuggingFace
    API: Claude 3.5, GPT-4o-mini, Gemini-2.0 via OpenRouter proxy (9 rotating keys)
    Intelligent routing, fallback chains, distillation support

    Usage:
        # Simple routing
        learner = LearnerInitializer.create_with_intelligent_routing(
            TaskComplexity.COMPLEX,
            memory_manager=memory,
            eval_agent=eval
        )

        # Hybrid pair for distillation
        pair = LearnerInitializer.create_hybrid_pair(
            memory_manager=memory,
            eval_agent=eval
        )
        local = pair['local']        # DeepSeek-LLM for inference
        teacher = pair['api_teacher']  # Claude/GPT-4o-mini via OpenRouter
    """

    # ============ LOCAL LEARNERS (Ollama) ============
    LOCAL_CONFIGS = {
        'deepseek': LearnerConfig(
            name='DeepSeek-LLM-7B',
            backend=ModelBackend.LOCAL_OLLAMA,
            model_id='deepseek-llm:7b',
            memory_gb=6,
            tokens_per_sec=30,
            supports_vision=False,
            supports_sparse_attention=True,
            best_for=[TaskComplexity.SIMPLE, TaskComplexity.MEDIUM, TaskComplexity.COMPLEX],
            requires=['ollama'],
            description='DeepSeek-LLM-7B: Main local model. Excellent for code/reasoning.',
            init_params={
                'model': os.getenv('DEEPSEEK_MODEL', 'deepseek-llm:7b'),
                'temperature': 0.7,
                'top_p': 0.9
            }
        ),
        'llama': LearnerConfig(
            name='Llama3.1-8B',
            backend=ModelBackend.LOCAL_OLLAMA,
            model_id='llama3.1:8b',
            memory_gb=8,
            tokens_per_sec=25,
            supports_vision=True,
            supports_self_modifying=False,
            best_for=[TaskComplexity.COMPLEX, TaskComplexity.EXPERT],
            requires=['ollama'],
            description='Llama3.1-8B: HOPE pattern implementation. For hierarchical multi-level analysis.',
            init_params={
                'model': os.getenv('LLAMA_MODEL', 'llama3.1:8b'),
                'temperature': 0.7,
                'top_p': 0.85
            }
        ),
        'qwen': LearnerConfig(
            name='Qwen2-7B',
            backend=ModelBackend.LOCAL_OLLAMA,
            model_id='qwen2:7b',
            memory_gb=4,
            tokens_per_sec=25,
            supports_vision=False,
            best_for=[TaskComplexity.SIMPLE, TaskComplexity.MEDIUM],
            requires=['ollama'],
            description='Qwen2-7B: Fast fallback. Reliable for simple tasks.',
            init_params={
                'model': os.getenv('QWEN_MODEL', 'qwen2:7b'),
                'temperature': 0.7,
                'top_p': 0.9
            }
        ),
        'pixtral': LearnerConfig(
            name='Pixtral-12B',
            backend=ModelBackend.LOCAL_OLLAMA,  # Actually HuggingFace but using same backend enum
            model_id='pixtral-12b',
            memory_gb=12,
            tokens_per_sec=15,
            supports_vision=True,
            supports_self_modifying=False,
            best_for=[TaskComplexity.EXPERT],
            requires=['transformers', 'torch'],
            description='Pixtral-12B: Advanced multimodal from HuggingFace. Best for vision tasks.',
            init_params={
                'model_path': os.path.expanduser(os.getenv('PIXTRAL_PATH', '~/pixtral-12b')),
                'temperature': 0.7,
                'top_p': 0.9
            }
        )
    }

    # ============ API LEARNERS (OpenRouter) ============
    API_CONFIGS = {
        'claude': LearnerConfig(
            name='Claude 3.5 Sonnet',
            backend=ModelBackend.API_OPENROUTER,
            model_id='anthropic/claude-3.5-sonnet',  # OpenRouter ID
            memory_gb=0,
            tokens_per_sec=50,
            supports_vision=True,
            best_for=[TaskComplexity.EXPERT],
            requires=['requests'],  # Using requests instead of anthropic SDK
            description='Claude 3.5 via OpenRouter: Best for code/structures.',
            init_params={
                'model': 'anthropic/claude-3.5-sonnet',
                'proxy_url': 'http://localhost:8000/v1',  # API Gateway
                'api_key_source': 'openrouter_rotate'  # Auto-rotation of 9 keys
            }
        ),
        'gpt4o_mini': LearnerConfig(
            name='GPT-4o-mini',
            backend=ModelBackend.API_OPENROUTER,
            model_id='openai/gpt-4o-mini',  # OpenRouter ID
            memory_gb=0,
            tokens_per_sec=80,
            supports_vision=True,
            best_for=[TaskComplexity.MEDIUM, TaskComplexity.COMPLEX],
            requires=['requests'],
            description='GPT-4o-mini via OpenRouter: Fast, cheap distillation.',
            init_params={
                'model': 'openai/gpt-4o-mini',
                'proxy_url': 'http://localhost:8000/v1',
                'api_key_source': 'openrouter_rotate'
            }
        ),
        'gemini': LearnerConfig(
            name='Gemini-2.0-Flash',
            backend=ModelBackend.API_OPENROUTER,
            model_id='google/gemini-2.0-flash-exp',  # OpenRouter ID
            memory_gb=0,
            tokens_per_sec=100,
            supports_vision=True,
            best_for=[TaskComplexity.COMPLEX, TaskComplexity.EXPERT],
            requires=['requests'],
            description='Gemini-2.0 via OpenRouter: Fast multimodal.',
            init_params={
                'model': 'google/gemini-2.0-flash-exp',
                'proxy_url': 'http://localhost:8000/v1',
                'api_key_source': 'openrouter_rotate'
            }
        )
    }

    # Combined registry
    ALL_CONFIGS = {**LOCAL_CONFIGS, **API_CONFIGS}

    # ============ ROUTING LOGIC ============
    ROUTING_RULES = {
        TaskComplexity.SIMPLE: {
            'primary': 'qwen',      # Fast local
            'fallback': ['deepseek']
        },
        TaskComplexity.MEDIUM: {
            'primary': 'deepseek',  # Local first (cheaper)
            'fallback': ['qwen', 'claude']  # API only if local fails
        },
        TaskComplexity.COMPLEX: {
            'primary': 'deepseek',  # Main reasoning model
            'fallback': ['llama', 'gemini']  # Llama3.1 for HOPE pattern, Gemini via OpenRouter
        },
        TaskComplexity.EXPERT: {
            'primary': 'pixtral',   # Advanced multimodal from HuggingFace
            'fallback': ['llama', 'gemini', 'claude']  # Llama3.1 for vision, then API
        }
    }

    @classmethod
    def create_learner(
        cls,
        learner_type: str,
        memory_manager: Optional[Any] = None,
        eval_agent: Optional[Any] = None,
        **override_params
    ) -> Optional[Any]:
        """
        Create learner instance with dependency checking

        Args:
            learner_type: Type of learner (e.g., 'deepseek', 'grok')
            memory_manager: MemoryManager instance
            eval_agent: EvalAgent instance
            **override_params: Override parameters

        Returns:
            Learner instance or None
        """

        if learner_type not in cls.ALL_CONFIGS:
            available = list(cls.ALL_CONFIGS.keys())
            logger.error(f"❌ Unknown learner: {learner_type}")
            logger.info(f"   Available: {', '.join(available)}")
            return None

        config = cls.ALL_CONFIGS[learner_type]

        # Check dependencies
        if not cls._check_dependencies(config.requires):
            logger.warning(f"⚠️  Missing dependencies for {learner_type}: {config.requires}")
            return None

        # Build init params
        init_params = config.init_params.copy()
        init_params.update(override_params)

        # Handle OpenRouter API keys (rotate through 9 keys)
        if config.backend == ModelBackend.API_OPENROUTER:
            api_key = OpenRouterAPIKeyRotator.get_next_key()
            if not api_key:
                logger.error(f"❌ No OpenRouter API keys available")
                return None
            init_params['api_key'] = api_key
            init_params['api_key_source'] = 'openrouter_rotate'
            logger.info(f"   Using OpenRouter proxy: {init_params.get('proxy_url')}")

        # Add managers
        if memory_manager:
            init_params['memory_manager'] = memory_manager
        if eval_agent:
            init_params['eval_agent'] = eval_agent

        # Create learner
        try:
            from src.agents.learner_factory import LearnerFactory

            logger.info(f"🔨 Creating {learner_type} learner...")
            logger.info(f"   {config.description}")
            logger.info(f"   Backend: {config.backend.value} | Memory: {config.memory_gb}GB | Speed: {config.tokens_per_sec} tok/s")

            # Map to factory-registered types
            factory_mapping = {
                'deepseek': 'qwen',       # DeepSeek uses Qwen learner (Ollama)
                'llama': 'qwen',          # Llama3.1 uses Qwen learner (Ollama)
                'pixtral': 'pixtral',     # Pixtral uses Pixtral learner (HuggingFace)
                'qwen': 'qwen',
                'claude': 'claude',       # API learners via OpenRouter
                'gpt4o_mini': 'gpt4o_mini',
                'gemini': 'gemini'
            }

            factory_type = factory_mapping.get(learner_type, learner_type)

            learner = LearnerFactory.create(factory_type, **init_params)

            if learner:
                logger.info(f"✅ {learner_type.upper()} initialized successfully")
                return learner
            else:
                logger.error(f"❌ Failed to create {learner_type}")
                return None

        except Exception as e:
            logger.error(f"❌ Creation failed for {learner_type}: {e}")
            import traceback
            traceback.print_exc()
            return None

    @classmethod
    def create_with_intelligent_routing(
        cls,
        complexity: TaskComplexity,
        memory_manager: Optional[Any] = None,
        eval_agent: Optional[Any] = None,
        prefer_api: bool = False
    ) -> Optional[Any]:
        """
        Create learner with intelligent routing by complexity
        Tries primary, then fallback chain

        Args:
            complexity: Task complexity level
            memory_manager: MemoryManager instance
            eval_agent: EvalAgent instance
            prefer_api: Force API if available

        Returns:
            Learner instance (or None if all failed)
        """

        rules = cls.ROUTING_RULES.get(complexity, cls.ROUTING_RULES[TaskComplexity.MEDIUM])

        primary = rules['primary']
        fallback = rules['fallback']

        # If API preferred and available
        if prefer_api:
            # Move API options to front
            fallback = [f for f in fallback if f in cls.API_CONFIGS] + \
                      [f for f in fallback if f not in cls.API_CONFIGS]

        chain = [primary] + fallback

        logger.info(f"🔄 Routing for {complexity.value}: {' → '.join(chain)}")

        for learner_type in chain:
            logger.info(f"   Trying: {learner_type}...")

            learner = cls.create_learner(
                learner_type,
                memory_manager=memory_manager,
                eval_agent=eval_agent
            )

            if learner:
                logger.info(f"✅ Using: {learner_type}")
                return learner

            logger.warning(f"⚠️  Failed, trying next...")

        logger.error(f"❌ All learners failed: {chain}")
        return None

    @classmethod
    def create_hybrid_pair(
        cls,
        memory_manager: Optional[Any] = None,
        eval_agent: Optional[Any] = None,
        local_model: str = 'deepseek',
        api_teacher: str = 'claude'
    ) -> Dict[str, Optional[Any]]:
        """
        Create hybrid pair: local + API teacher
        For distillation: API teaches local

        Args:
            memory_manager: MemoryManager instance
            eval_agent: EvalAgent instance
            local_model: Local model to use (default: 'deepseek')
            api_teacher: API teacher to use (default: 'claude' via OpenRouter)

        Returns:
            Dict with 'local' and 'api_teacher' learners
        """

        logger.info("🔗 Creating hybrid learner pair (local + API)...")

        local = cls.create_learner(
            local_model,
            memory_manager=memory_manager,
            eval_agent=eval_agent
        )

        teacher = cls.create_learner(
            api_teacher,
            memory_manager=memory_manager,
            eval_agent=eval_agent
        )

        if not local:
            logger.error(f"❌ Failed to create local learner: {local_model}")

        if not teacher:
            logger.warning(f"⚠️  API teacher unavailable: {api_teacher}")

        logger.info(f"✅ Hybrid pair: {local_model} (local) + {api_teacher if teacher else 'No API teacher'}")

        return {
            'local': local,
            'api_teacher': teacher
        }

    @staticmethod
    def _check_dependencies(requirements: List[str]) -> bool:
        """Check if all required packages available"""

        missing = []
        for package in requirements:
            try:
                __import__(package)
            except ImportError:
                missing.append(package)

        if missing:
            logger.warning(f"⚠️  Missing: {', '.join(missing)}")
            return False

        return True

    @classmethod
    def list_available(cls) -> Dict[str, Dict[str, Any]]:
        """List all available learners with details"""

        result = {}

        logger.info("\n" + "="*70)
        logger.info("📋 AVAILABLE LEARNERS")
        logger.info("="*70)

        logger.info("\n🖥️  LOCAL MODELS (Ollama):")
        for name, config in cls.LOCAL_CONFIGS.items():
            result[name] = {
                'name': config.name,
                'backend': config.backend.value,
                'description': config.description,
                'memory_gb': config.memory_gb,
                'tokens_per_sec': config.tokens_per_sec,
                'supports_vision': config.supports_vision,
                'best_for': [c.value for c in config.best_for],
                'requires': config.requires
            }
            logger.info(f"   • {config.name} ({name})")
            logger.info(f"     {config.description}")
            logger.info(f"     {config.memory_gb}GB RAM | {config.tokens_per_sec} tok/s")

        logger.info("\n☁️  API MODELS (Cloud):")
        for name, config in cls.API_CONFIGS.items():
            result[name] = {
                'name': config.name,
                'backend': config.backend.value,
                'description': config.description,
                'memory_gb': config.memory_gb,
                'tokens_per_sec': config.tokens_per_sec,
                'supports_vision': config.supports_vision,
                'best_for': [c.value for c in config.best_for],
                'requires': config.requires
            }
            logger.info(f"   • {config.name} ({name})")
            logger.info(f"     {config.description}")
            logger.info(f"     {config.tokens_per_sec} tok/s")

        logger.info("="*70 + "\n")

        return result

    @classmethod
    def get_context_template(
        cls,
        graph_state: Optional[Dict[str, Any]] = None,
        node_details: Optional[str] = None,
        relationships: Optional[str] = None,
        depth: int = 0,
        num_children: int = 0,
        num_dependencies: int = 0,
        semantic_similarity: Optional[str] = None
    ) -> str:
        """
        Template for passing graph context to models (local + API)

        Args:
            graph_state: Current graph state summary
            node_details: Detailed node information
            relationships: Semantic relationships
            depth: Depth in hierarchy
            num_children: Number of child nodes
            num_dependencies: Number of dependencies
            semantic_similarity: Similarity to other nodes

        Returns:
            Formatted context string
        """

        return f"""
CURRENT GRAPH STATE:
{graph_state or 'No graph state provided'}

NODE DETAILS:
{node_details or 'No node details'}

SEMANTIC RELATIONSHIPS:
{relationships or 'No relationships'}

TASK CONTEXT:
- Depth in hierarchy: {depth}
- Number of children: {num_children}
- Number of dependencies: {num_dependencies}
- Semantic similarity to other nodes: {semantic_similarity or 'N/A'}

ANALYZE AND PROVIDE:
1. Relationship effectiveness
2. Potential improvements
3. New connections to suggest
4. Patterns observed

USE SPARSE ATTENTION to focus on relevant connections.
"""

    @classmethod
    def get_routing_recommendation(
        cls,
        task_description: str,
        word_count: Optional[int] = None,
        has_visual: bool = False,
        requires_hierarchy: bool = False
    ) -> TaskComplexity:
        """
        Recommend task complexity based on task characteristics

        Args:
            task_description: Description of the task
            word_count: Number of words in task (if known)
            has_visual: Task includes visual elements
            requires_hierarchy: Task requires hierarchical reasoning

        Returns:
            Recommended TaskComplexity
        """

        # Calculate word count if not provided
        if word_count is None and task_description:
            # Strip whitespace and count words
            word_count = len(task_description.strip().split())

        # Expert: visual or hierarchical
        if has_visual or requires_hierarchy:
            return TaskComplexity.EXPERT

        # Complex: > 30 words (revised for realistic thresholds)
        if word_count and word_count > 30:
            return TaskComplexity.COMPLEX

        # Medium: 10-30 words
        if word_count and word_count > 10:
            return TaskComplexity.MEDIUM

        # Simple: < 10 words
        return TaskComplexity.SIMPLE


# ============ OPENROUTER API KEY ROTATION ============

class OpenRouterAPIKeyRotator:
    """Handles rotation of OpenRouter API keys from .env"""

    _current_index = 0
    _keys = []

    @classmethod
    def load_keys(cls):
        """Load all OPENROUTER_KEY_* from environment"""
        import os
        keys = []

        for i in range(1, 10):  # Check KEY_1 to KEY_9
            key = os.getenv(f'OPENROUTER_KEY_{i}')
            if key:
                keys.append(key)

        cls._keys = keys
        logger.info(f"✅ Loaded {len(keys)} OpenRouter API keys")
        return keys

    @classmethod
    def get_next_key(cls) -> Optional[str]:
        """Get next API key in rotation"""
        if not cls._keys:
            cls.load_keys()

        if not cls._keys:
            logger.error("❌ No OpenRouter API keys found")
            return None

        key = cls._keys[cls._current_index % len(cls._keys)]
        cls._current_index += 1

        logger.debug(f"🔄 Using OpenRouter key #{(cls._current_index - 1) % len(cls._keys) + 1}")
        return key


# ============ CONVENIENCE FUNCTIONS ============

def create_learner_for_task(
    task_description: str,
    memory_manager: Optional[Any] = None,
    eval_agent: Optional[Any] = None,
    prefer_api: bool = False,
    **task_params
) -> Optional[Any]:
    """
    Convenience function: create learner based on task description

    Args:
        task_description: Task description
        memory_manager: MemoryManager instance
        eval_agent: EvalAgent instance
        prefer_api: Prefer API models
        **task_params: Additional task parameters (has_visual, requires_hierarchy, etc.)

    Returns:
        Learner instance
    """

    complexity = LearnerInitializer.get_routing_recommendation(
        task_description,
        **task_params
    )

    logger.info(f"📊 Auto-detected complexity: {complexity.value}")

    return LearnerInitializer.create_with_intelligent_routing(
        complexity,
        memory_manager=memory_manager,
        eval_agent=eval_agent,
        prefer_api=prefer_api
    )


# ============ INITIALIZATION LOGGING (DEBUG only) ============

logger.debug(f"LearnerInitializer v8.0 loaded: local={list(LearnerInitializer.LOCAL_CONFIGS.keys())}, api={list(LearnerInitializer.API_CONFIGS.keys())}")
