"""
VETKA Initialization Package - Setup logging, dependencies, and components.

@status: active
@phase: 96
@depends: logging_setup, dependency_check, components_init
@used_by: main.py, src.api
"""

from .logging_setup import setup_logging, LOGGER, SmartDuplicateFilter
from .dependency_check import verify_dependencies, check_available_providers
from .components_init import initialize_all_components

__all__ = [
    'setup_logging',
    'LOGGER',
    'SmartDuplicateFilter',
    'verify_dependencies',
    'check_available_providers',
    'initialize_all_components',
]
