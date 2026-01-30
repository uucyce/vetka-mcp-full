"""
VETKA API Package - FastAPI Routes and Dependencies

@file api/__init__.py
@status ACTIVE
@phase Phase 39.2
@lastAudit 2026-01-05

This package contains FastAPI routes migrated from Flask blueprints.
"""

from .routes import register_all_routers, get_all_routers

__all__ = [
    'register_all_routers',
    'get_all_routers',
]
