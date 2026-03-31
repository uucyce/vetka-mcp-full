# Browser Agent Adapters
"""
Adapters for AI chat services (Gemini, Kimi, Grok, Perplexity, Mistral).
Each adapter implements the BaseAdapter interface for browser automation.
"""

from src.services.adapters.base_adapter import BaseAdapter, AdapterResult

__all__ = ["BaseAdapter", "AdapterResult"]
