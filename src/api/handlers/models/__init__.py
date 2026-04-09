"""
VETKA Model Clients Module.

Exports model client utilities for Ollama and OpenRouter calls.

@status: active
@phase: 96
@depends: model_client
@used_by: di_container
"""

from .model_client import ModelClient, create_model_client

__all__ = ['ModelClient', 'create_model_client']
