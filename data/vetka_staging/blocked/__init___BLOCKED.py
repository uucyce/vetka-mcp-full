# file: src/api/handlers/__init__.py
# MARKER_102.2_REGISTER_START
"""
API handlers initialization.
Registers all route handlers with the FastAPI application.
"""

from .web_search_handler import register_web_search_routes

__all__ = [
    "register_web_search_routes",
]

# MARKER_102.2_REGISTER_END