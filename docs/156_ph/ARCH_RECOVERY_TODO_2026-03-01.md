# VETKA Architecture Recovery TODO (2026-03-01)

## Goal
Align runtime architecture after environment/cache loss and remove drift introduced by mixed virtual environments and auto-fixes.

## TODO (execution order)
1. Define canonical runtime path for backend startup (`main.py`/FastAPI + uvicorn behavior) and freeze one launch contract.
2. Unify Python environment policy: keep only one project venv (`.venv`) and remove accidental secondary `venv` references from operational scripts.
3. Validate dependency reality from imports + runtime paths (code-first inventory), not from stale package lists.
4. Run architecture smoke checks on canonical env: API boot, Qdrant connectivity over HTTP (`:6333`), critical routes, and memory/triple-write init.
5. Normalize Qdrant client usage to explicit URL-style init everywhere and verify no gRPC-only assumptions remain.
6. Update operational docs/runbooks to `.venv`-only commands and FastAPI terminology (remove old Flask-era instructions in active docs).
7. Create a minimal reproducible bootstrap script for clean machine recovery (single command path).
8. Only after architecture is stabilized: rebuild and update `requirements.txt` from actual canonical environment (last step).
