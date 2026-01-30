# ========================================
# MARKER: Phase 72.2 Test Fixture
# File: tests/scanners/fixtures/python/package_imports.py
# Purpose: Test package vs module distinction
# ========================================
"""
Test fixture: Package imports.

From VETKA audit:
- 302 local project imports (189 unique)
- Pattern: from src.X import Y

Key distinction:
- Package: directory with __init__.py (import package -> __init__.py)
- Module: single .py file (import module -> module.py)
"""

# Package imports (directory with __init__.py)
# import src.agents  # -> src/agents/__init__.py
# from src.agents import LearnerAgent  # -> src/agents/__init__.py exports

# Module imports (single .py file)
# from src.agents.learner_factory import LearnerFactory  # -> learner_factory.py

# Nested package/module patterns from VETKA:
# from src.orchestration.cam_engine import CAMEngine
# from src.orchestration.langgraph_state import VETKAState
# from src.orchestration.langgraph_nodes import VETKANodes
# from src.orchestration.services.memory_service import MemoryService
# from src.orchestration.services.routing_service import RoutingService

# Common patterns:
LOCAL_PROJECT_IMPORT_PATTERNS = [
    "src.agents",                              # Package
    "src.agents.learner_factory",              # Module in package
    "src.agents.LearnerAgent",                 # Class from package __init__
    "src.orchestration.cam_engine",            # Deep module
    "src.orchestration.services.memory_service", # Very deep module
    "src.utils.quiet_logger",                  # Utility module
    "src.memory.qdrant_client",                # Client module
]
