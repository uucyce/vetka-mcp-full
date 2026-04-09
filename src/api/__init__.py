"""
VETKA API Package - FastAPI Routes and Dependencies

@file api/__init__.py
@status ACTIVE
@phase Phase 39.2
@lastAudit 2026-01-05

This package contains FastAPI routes migrated from Flask blueprints.
"""


def get_all_routers():
    from .routes import get_all_routers as _get_all_routers

    return _get_all_routers()



def register_all_routers(app):
    from .routes import register_all_routers as _register_all_routers

    return _register_all_routers(app)


__all__ = [
    "register_all_routers",
    "get_all_routers",
]
