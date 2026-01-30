"""
VETKA Dependency Verification Module.

Checks and verifies all required and optional dependencies for the application.
Supports graceful degradation when optional dependencies are missing.

Usage:
    from src.initialization.dependency_check import verify_dependencies
    status = verify_dependencies()
    if not status['all_ok']:
        print("Some dependencies are missing")

@status: active
@phase: 96
@depends: logging_setup, os, socket
@used_by: components_init, main.py
"""

import os
import socket
from typing import Dict, List, Tuple, Any, Optional
from .logging_setup import LOGGER


# ============ REQUIRED PACKAGES ============
REQUIRED_PACKAGES = {
    'qdrant_client': 'pip install qdrant-client',
    'requests': 'pip install requests',
    'ollama': 'pip install ollama',
}

# ============ OPTIONAL PACKAGES (graceful degradation) ============
OPTIONAL_PACKAGES = {
    'dotenv': 'pip install python-dotenv',
    'numpy': 'pip install numpy',
    'sklearn': 'pip install scikit-learn',
    'PIL': 'pip install pillow',
}


def check_package(pkg_name: str) -> bool:
    """
    Check if a Python package is installed.

    Args:
        pkg_name: The package name to check

    Returns:
        True if package is installed, False otherwise
    """
    try:
        __import__(pkg_name)
        return True
    except ImportError:
        return False


def verify_required_packages() -> Tuple[List[str], List[Tuple[str, str]]]:
    """
    Verify all required packages are installed.

    Returns:
        Tuple of (installed_packages, missing_packages)
        where missing_packages is list of (pkg_name, install_cmd)
    """
    installed = []
    missing = []

    for pkg_name, install_cmd in REQUIRED_PACKAGES.items():
        if check_package(pkg_name):
            installed.append(pkg_name)
            print(f"✅ {pkg_name}")
        else:
            missing.append((pkg_name, install_cmd))
            print(f"⚠️  {pkg_name} - {install_cmd}")

    return installed, missing


def verify_optional_packages() -> Dict[str, bool]:
    """
    Verify optional packages (no error if missing).

    Returns:
        Dict mapping package name to availability status
    """
    status = {}
    for pkg_name in OPTIONAL_PACKAGES:
        status[pkg_name] = check_package(pkg_name)
    return status


def check_available_providers() -> Dict[str, bool]:
    """
    Check which AI/ML providers are available.

    Returns:
        Dict with provider availability status
    """
    providers = {}

    # Check Ollama
    try:
        import ollama
        providers['ollama'] = True
    except ImportError:
        providers['ollama'] = False

    # Check OpenAI
    try:
        import openai
        providers['openai'] = True
    except ImportError:
        providers['openai'] = False

    # Check Anthropic
    try:
        import anthropic
        providers['anthropic'] = True
    except ImportError:
        providers['anthropic'] = False

    # Check Google (Gemini)
    try:
        import google.generativeai
        providers['google'] = True
    except ImportError:
        providers['google'] = False

    return providers


def get_qdrant_host() -> str:
    """
    Auto-detect Qdrant host based on environment.

    Returns:
        Best available Qdrant host address
    """
    # Try environment variable first
    env_host = os.getenv('QDRANT_HOST')
    if env_host:
        return env_host

    # Try localhost
    try:
        socket.gethostbyname('127.0.0.1')
        return '127.0.0.1'
    except Exception:
        pass

    # Fallback for Mac Docker
    try:
        socket.gethostbyname('host.docker.internal')
        return 'host.docker.internal'
    except Exception:
        return '127.0.0.1'


def check_vetka_modules() -> Dict[str, Dict[str, Any]]:
    """
    Check availability of VETKA-specific modules.

    Returns:
        Dict mapping module name to status info
    """
    modules = {}

    # Orchestrator with Elisya
    try:
        from src.orchestration.orchestrator_with_elisya import OrchestratorWithElisya
        modules['orchestrator_elisya'] = {
            'available': True,
            'class': OrchestratorWithElisya,
            'parallel': True
        }
        print("✅ Sprint 1.5: Orchestrator with Elisya Integration loaded")
    except ImportError as e:
        print(f"⚠️  Elisya orchestrator not available: {e}")
        # Try parallel orchestrator fallback
        try:
            from src.orchestration.agent_orchestrator_parallel import AgentOrchestrator
            modules['orchestrator_elisya'] = {
                'available': True,
                'class': AgentOrchestrator,
                'parallel': True,
                'fallback': 'parallel'
            }
            print("✅ Phase 7 Parallel Orchestrator loaded (fallback)")
        except ImportError:
            try:
                from src.orchestration.agent_orchestrator import AgentOrchestrator
                modules['orchestrator_elisya'] = {
                    'available': True,
                    'class': AgentOrchestrator,
                    'parallel': False,
                    'fallback': 'sequential'
                }
                print("⚠️  Sequential orchestrator loaded (fallback)")
            except ImportError as e2:
                modules['orchestrator_elisya'] = {
                    'available': False,
                    'error': str(e2)
                }

    # Memory Manager
    try:
        from src.orchestration.memory_manager import MemoryManager
        modules['memory_manager'] = {'available': True, 'class': MemoryManager}
    except ImportError as e:
        modules['memory_manager'] = {'available': False, 'error': str(e)}

    # Eval Agent
    try:
        from src.agents.eval_agent import EvalAgent
        modules['eval_agent'] = {'available': True, 'class': EvalAgent}
    except ImportError as e:
        modules['eval_agent'] = {'available': False, 'error': str(e)}

    # Metrics Engine
    try:
        from src.monitoring.metrics_engine import init_metrics_engine, get_metrics_engine
        modules['metrics_engine'] = {
            'available': True,
            'init': init_metrics_engine,
            'get': get_metrics_engine
        }
        print("✅ Metrics Engine module found")
    except ImportError as e:
        modules['metrics_engine'] = {'available': False, 'error': str(e)}
        print(f"⚠️  Metrics Engine not available: {e}")

    # Model Router v2
    try:
        from src.elisya.model_router_v2 import init_model_router, get_model_router
        modules['model_router'] = {
            'available': True,
            'init': init_model_router,
            'get': get_model_router
        }
        print("✅ Model Router v2 module found")
    except ImportError as e:
        modules['model_router'] = {'available': False, 'error': str(e)}
        print(f"⚠️  Model Router v2 not available: {e}")

    # API Gateway v2 (DEPRECATED - replaced by APIAggregator)
    # Note: api_gateway module is deprecated in favor of APIAggregator v3
    modules['api_gateway'] = {
        'available': False,
        'note': 'Deprecated - use APIAggregator v3 instead'
    }

    # Qdrant Auto-Retry
    try:
        from src.memory.qdrant_auto_retry import init_qdrant_auto_retry, get_qdrant_auto_retry
        modules['qdrant_auto_retry'] = {
            'available': True,
            'init': init_qdrant_auto_retry,
            'get': get_qdrant_auto_retry
        }
        print("✅ Qdrant Auto-Retry module found")
    except ImportError as e:
        modules['qdrant_auto_retry'] = {'available': False, 'error': str(e)}
        print(f"⚠️  Qdrant Auto-Retry not available: {e}")

    # Feedback Loop v2
    try:
        from src.orchestration.feedback_loop_v2 import init_feedback_loop, get_feedback_loop
        modules['feedback_loop'] = {
            'available': True,
            'init': init_feedback_loop,
            'get': get_feedback_loop
        }
        print("✅ Feedback Loop v2 module found")
    except ImportError as e:
        modules['feedback_loop'] = {'available': False, 'error': str(e)}
        print(f"⚠️  Feedback Loop v2 not available: {e}")

    # Learner Factory (Phase 7.9)
    try:
        from src.agents.learner_factory import LearnerFactory
        from src.agents.learner_initializer import LearnerInitializer, TaskComplexity
        # Phase 44.8: Import learner classes to trigger @register decorators
        from src.agents.pixtral_learner import PixtralLearner  # noqa: F401
        from src.agents.qwen_learner import QwenLearner  # noqa: F401
        modules['learner_factory'] = {
            'available': True,
            'factory': LearnerFactory,
            'initializer': LearnerInitializer,
            'task_complexity': TaskComplexity
        }
        print("✅ Learner Factory loaded (Phase 7.9)")
    except ImportError as e:
        modules['learner_factory'] = {'available': False, 'error': str(e)}
        print(f"⚠️  Learner Factory not available: {e}")

    # SmartLearner (Phase 8.0)
    try:
        from src.agents.smart_learner import SmartLearner, TaskCategory, smart_learner_factory
        modules['smart_learner'] = {
            'available': True,
            'class': SmartLearner,
            'task_category': TaskCategory,
            'factory': smart_learner_factory
        }
        print("✅ SmartLearner loaded (Phase 8.0)")
    except ImportError as e:
        modules['smart_learner'] = {'available': False, 'error': str(e)}
        print(f"⚠️  SmartLearner not available: {e}")

    # HOPEEnhancer (Phase 8.0)
    try:
        from src.agents.hope_enhancer import HOPEEnhancer, FrequencyLayer, hope_enhancer_factory
        modules['hope_enhancer'] = {
            'available': True,
            'class': HOPEEnhancer,
            'frequency_layer': FrequencyLayer,
            'factory': hope_enhancer_factory
        }
        print("✅ HOPEEnhancer loaded (Phase 8.0)")
    except ImportError as e:
        modules['hope_enhancer'] = {'available': False, 'error': str(e)}
        print(f"⚠️  HOPEEnhancer not available: {e}")

    # EmbeddingsProjector (Phase 8.0)
    try:
        from src.agents.embeddings_projector import EmbeddingsProjector, ProjectionMethod, embeddings_projector_factory
        modules['embeddings_projector'] = {
            'available': True,
            'class': EmbeddingsProjector,
            'projection_method': ProjectionMethod,
            'factory': embeddings_projector_factory
        }
        print("✅ EmbeddingsProjector loaded (Phase 8.0)")
    except ImportError as e:
        modules['embeddings_projector'] = {'available': False, 'error': str(e)}
        print(f"⚠️  EmbeddingsProjector not available: {e}")

    # Student System (Phase 9.0)
    try:
        from src.agents.student_level_system import StudentLevelSystem, StudentLevel, student_level_system_factory
        from src.agents.student_portfolio import StudentPortfolio, student_portfolio_factory
        from src.orchestration.student_promotion_engine import StudentPromotionEngine, student_promotion_engine_factory
        from src.orchestration.simpo_training_loop import SimPOTrainingLoop, simpo_training_loop_factory
        modules['student_system'] = {
            'available': True,
            'level_system': StudentLevelSystem,
            'student_level': StudentLevel,
            'portfolio': StudentPortfolio,
            'promotion_engine': StudentPromotionEngine,
            'simpo_loop': SimPOTrainingLoop
        }
        print("✅ Phase 9.0 Student System loaded")
    except ImportError as e:
        modules['student_system'] = {'available': False, 'error': str(e)}
        print(f"⚠️  Phase 9.0 Student System not available: {e}")

    return modules


def verify_dependencies(verbose: bool = True) -> Dict[str, Any]:
    """
    Main function to verify all dependencies.

    Args:
        verbose: If True, print status messages

    Returns:
        Dict containing:
        - all_ok: bool - True if all required dependencies are present
        - critical: bool - True if critical dependencies are missing
        - required: list - Status of required packages
        - optional: dict - Status of optional packages
        - providers: dict - Status of AI providers
        - modules: dict - Status of VETKA modules
        - qdrant_host: str - Detected Qdrant host
    """
    if verbose:
        print("\n" + "=" * 70)
        print("🚀 PHASE 7.8: DEPENDENCY VERIFICATION")
        print("=" * 70)

    # Check required packages
    installed, missing = verify_required_packages()

    if missing and verbose:
        print(f"\n⚠️  MISSING PACKAGES: Install with:")
        for pkg_name, install_cmd in missing:
            print(f"   {install_cmd}")
        print("\n(System will run in degraded mode)")

    if verbose:
        print("=" * 70 + "\n")
        print("🚀 PHASE 7.8 INITIALIZATION (Graceful Degradation)...")

    # Check optional packages
    optional_status = verify_optional_packages()

    # Check AI providers
    providers = check_available_providers()

    # Check VETKA modules
    modules = check_vetka_modules()

    # Detect Qdrant host
    qdrant_host = get_qdrant_host()

    # Determine overall status
    all_ok = len(missing) == 0
    critical = not modules.get('orchestrator_elisya', {}).get('available', False)

    return {
        'all_ok': all_ok,
        'critical': critical,
        'required': {
            'installed': installed,
            'missing': missing
        },
        'optional': optional_status,
        'providers': providers,
        'modules': modules,
        'qdrant_host': qdrant_host
    }


def get_module_status_summary(modules: Dict[str, Dict]) -> str:
    """
    Generate a summary string of module availability.

    Args:
        modules: Module status dict from check_vetka_modules()

    Returns:
        Formatted summary string
    """
    available = sum(1 for m in modules.values() if m.get('available', False))
    total = len(modules)

    lines = [f"Module Status: {available}/{total} available"]
    for name, status in modules.items():
        icon = "✅" if status.get('available', False) else "❌"
        lines.append(f"  {icon} {name}")

    return "\n".join(lines)
