"""
VETKA Phase 7.9 - Learner Factory
Registry-based factory for pluggable LLM models - add any model with @register decorator

@status: active
@phase: 96
@depends: base_learner.BaseLearner
@used_by: learner_initializer, pixtral_learner, qwen_learner
"""

from typing import Dict, Type, List
from .base_learner import BaseLearner


class LearnerFactory:
    """
    Factory for creating and managing learner instances

    Usage:
        @LearnerFactory.register("my_model")
        class MyLearner(BaseLearner):
            ...

        learner = LearnerFactory.create("my_model", **config)
    """

    _learners: Dict[str, Type[BaseLearner]] = {}
    _failed_attempts: Dict[str, int] = {}
    _max_attempts_per_type: int = 2

    @classmethod
    def register(cls, name: str):
        """
        Decorator to register a learner type

        Args:
            name: Unique identifier for the learner

        Returns:
            Decorator function

        Example:
            @LearnerFactory.register("pixtral")
            class PixtralLearner(BaseLearner):
                ...
        """
        def decorator(learner_class: Type[BaseLearner]):
            if name in cls._learners:
                print(f"⚠️  Learner '{name}' already registered, overwriting")

            cls._learners[name] = learner_class
            print(f"✅ Registered learner: {name} ({learner_class.__name__})")
            return learner_class
        return decorator

    @classmethod
    def create(cls, learner_type: str, **kwargs) -> BaseLearner:
        """
        Create learner instance by type with attempt tracking

        Args:
            learner_type: Registered learner name
            **kwargs: Arguments to pass to learner constructor

        Returns:
            Initialized BaseLearner instance

        Raises:
            ValueError: If learner_type not registered or max attempts exceeded
        """
        # Check if max attempts exceeded
        if cls._failed_attempts.get(learner_type, 0) >= cls._max_attempts_per_type:
            raise ValueError(
                f"⏹️  Skipping {learner_type}: max attempts ({cls._max_attempts_per_type}) exceeded"
            )

        if learner_type not in cls._learners:
            available = list(cls._learners.keys())
            raise ValueError(
                f"❌ Unknown learner type: '{learner_type}'\n"
                f"   Available learners: {available}\n"
                f"   Register with: @LearnerFactory.register('{learner_type}')"
            )

        learner_class = cls._learners[learner_type]
        attempt = cls._failed_attempts.get(learner_type, 0) + 1
        print(f"🔨 Creating {learner_type} learner (attempt {attempt}/{cls._max_attempts_per_type})...")

        try:
            instance = learner_class(**kwargs)
            # Reset on success
            cls._failed_attempts[learner_type] = 0
            print(f"✅ {learner_type} learner created successfully")
            return instance
        except Exception as e:
            # Track failure
            cls._failed_attempts[learner_type] = attempt
            print(f"❌ Failed to create {learner_type} learner (attempt {attempt}): {e}")
            raise

    @classmethod
    def list_available(cls) -> Dict[str, str]:
        """
        List all registered learner types with descriptions

        Returns:
            Dictionary mapping learner names to descriptions
        """
        return {
            name: cls._learners[name].__doc__ or "No description available"
            for name in cls._learners.keys()
        }

    @classmethod
    def is_registered(cls, learner_type: str) -> bool:
        """
        Check if learner type is registered

        Args:
            learner_type: Learner name to check

        Returns:
            bool: True if registered
        """
        return learner_type in cls._learners

    @classmethod
    def get_registered_names(cls) -> List[str]:
        """
        Get list of all registered learner names

        Returns:
            List of learner names
        """
        return list(cls._learners.keys())
