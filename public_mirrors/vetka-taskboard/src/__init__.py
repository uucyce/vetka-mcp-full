"""
vetka-taskboard — Multi-Agent Task Queue with REST Gateway

A lightweight, SQLite-backed task board for coordinating work between
AI agents (Gemini, Claude, GPT, local models) via a REST API.

Features:
  - Task CRUD with priority queue
  - Agent registration with API key auth
  - Claim/complete lifecycle
  - Audit logging
  - Rate limiting
  - SSE real-time stream
  - Admin endpoints

@license MIT
@version 1.0.0
"""

__version__ = "1.0.0"
