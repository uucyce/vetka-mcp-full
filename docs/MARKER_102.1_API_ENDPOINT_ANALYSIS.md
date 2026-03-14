# MARKER_102.1: API Endpoint Analysis for New Feature

## Directory Structure Analysis

### Primary Location: `src/api/routes/`
The VETKA FastAPI structure uses a centralized router registration system:
- **Router files**: `src/api/routes/{feature}_routes.py`
- **Registration**: `src/api/routes/__init__.py` imports and registers all routers
- **Main entry**: `src/api/__init__.py` exports `register_all_routers` and `get_all_routers`

### Existing Router Count
Currently **25+ routers** with **75+ endpoints** registered, including:
- Core: config, metrics, files, tree, chat, knowledge
- Advanced: workflow, embeddings, semantic, unified_search
- Specialized: mcc, task, feedback, analytics, architect_chat
- Monitoring: health, watcher, debug, activity

## Router Pattern Analysis

### Standard Router Structure (from existing routes)