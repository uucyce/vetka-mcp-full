"""
VETKA Agents Package - Core agent implementations and exports.

@status: active
@phase: 96
@depends: base_agent, vetka_pm, vetka_dev, vetka_qa, vetka_architect
@used_by: app/main.py, orchestrator
"""
from .base_agent import BaseAgent
from .vetka_pm import VETKAPMAgent
from .vetka_dev import VETKADevAgent
from .vetka_qa import VETKAQAAgent
from .vetka_architect import VETKAArchitectAgent

# Aliases for app/main.py compatibility
VetkaPM = VETKAPMAgent
VetkaArchitect = VETKAArchitectAgent
VetkaDev = VETKADevAgent
VetkaQA = VETKAQAAgent
VetkaOps = VETKAPMAgent  # Placeholder - use PM for now
VetkaVisual = VETKAPMAgent  # Placeholder - use PM for now

__all__ = [
    "BaseAgent",
    "VETKAPMAgent", "VETKADevAgent", "VETKAQAAgent", "VETKAArchitectAgent",
    "VetkaPM", "VetkaArchitect", "VetkaDev", "VetkaQA", "VetkaOps", "VetkaVisual"
]
