"""VETKA Configuration"""
import os
from dotenv import load_dotenv

load_dotenv()

WEAVIATE_URL = os.getenv('WEAVIATE_URL', 'http://localhost:8080')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
FLASK_PORT = int(os.getenv('FLASK_PORT', '5001'))  # Changed from 5000 to 5001 to match frontend

EMBEDDING_MODEL = 'embeddinggemma:300m'
VECTOR_SIZE = 768

COLLECTIONS = {
    'shared': 'VetkaSharedMemory',
    'agents': 'VetkaAgentsMemory', 
    'changelog': 'VetkaChangeLog',
    'global': 'VetkaGlobal',
    'tree': 'VetkaTree',
    'leaf': 'VetkaLeaf'
}

# DEPRECATED: These hardcoded keys should be migrated to environment variables
# Use SecureKeyManager from src/utils/secure_key_manager.py instead
# Set OPENROUTER_KEY_1 through OPENROUTER_KEY_9 in your .env file
OPENROUTER_KEYS = [
    os.getenv('OPENROUTER_KEY_1', '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'),
    os.getenv('OPENROUTER_KEY_2', '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'),
    os.getenv('OPENROUTER_KEY_3', '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'),
    os.getenv('OPENROUTER_KEY_4', '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'),
    os.getenv('OPENROUTER_KEY_5', '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'),
    os.getenv('OPENROUTER_KEY_6', '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'),
    os.getenv('OPENROUTER_KEY_7', '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'),
    os.getenv('OPENROUTER_KEY_8', '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'),
    os.getenv('OPENROUTER_KEY_9', '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'),
]

MODEL_TIERS = {
    'premium': [
        {'name': 'anthropic/claude-3.5-sonnet', 'provider': 'openrouter', 'context': 200000},
        {'name': 'openai/gpt-4-turbo', 'provider': 'openrouter', 'context': 128000},
    ],
    'mid': [
        {'name': 'deepseek/deepseek-chat', 'provider': 'openrouter', 'context': 64000},
        {'name': 'meta-llama/llama-3.1-70b-instruct', 'provider': 'openrouter', 'context': 131072},
    ],
    'local': [
        {'name': 'deepseek-coder:6.7b', 'provider': 'ollama', 'context': 4096},
        {'name': 'llama3.1:8b', 'provider': 'ollama', 'context': 8192},
    ]
}

AGENT_MODELS = {
    'VETKA-PM': 'ollama/llama3.1:8b',
    'VETKA-Architect': 'ollama/qwen2:7b',
    'VETKA-Dev': 'ollama/deepseek-coder:6.7b',
    'VETKA-QA': 'ollama/llama3.1:8b',
    'VETKA-Ops': 'ollama/llama3.1:8b',
    'VETKA-Visual': 'ollama/llama3.1:8b',
}

CONTEXT_LIMITS = {
    'default': 1024,
    'VETKA-Dev': 2048,
}

ZOOM_LEVELS = {
    'global': {'min': 0.0, 'max': 1.0, 'tokens': 256, 'lod': 'low', 'collection': 'global'},
    'tree': {'min': 1.0, 'max': 2.0, 'tokens': 512, 'lod': 'medium', 'collection': 'tree'},
    'leaf': {'min': 2.0, 'max': 5.0, 'tokens': 1024, 'lod': 'high', 'collection': 'leaf'},
}

# =============================================================================
# PHASE CONFIGURATION (Phase 9.0+)
# =============================================================================

PHASE_ENABLED = {
    'phase_8': True,      # ModelRouter, API Aggregator
    'phase_9': True,      # Student System, SimPO, ARC Solver
    'phase_10': False,    # UI Dashboard (in preparation)
}

# UI Configuration for Phase 10
UI_CONFIG = {
    'enable_3d_tree': True,
    'enable_arc_visualization': True,
    'enable_metrics_dashboard': True,
    'theme': 'dark',
    'agents_visible': ['PM', 'Architect', 'Dev', 'QA', 'ARC'],
}

# Agent Performance Monitoring
MONITORING_CONFIG = {
    'enable_metrics': True,
    'max_snapshots': 1000,
    'log_level': 'INFO',
}

# ARC Solver Configuration
ARC_CONFIG = {
    'timeout_seconds': 180,
    'max_candidates': 5,
    'enable_learning': True,
    'sanitize_unicode': True,
}
