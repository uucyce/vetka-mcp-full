"""
VETKA Architect Agent - Solution design and architecture optimization.

@status: active
@phase: 96
@depends: base_agent.BaseAgent
@used_by: orchestrator, workflow agents
"""
from .base_agent import BaseAgent

class VETKAArchitectAgent(BaseAgent):
    def __init__(self):
        super().__init__("VETKA-Architect")
        self.model = "ollama/deepseek-coder:6.7b"
        
    def design_solution(self, problem: str) -> str:
        prompt = f"You are Solution Architect. Design architecture for: {problem}\n\nArchitecture:"
        return self.call_llm(prompt)
    
    def optimize_design(self, design: str) -> str:
        prompt = f"Review and optimize this design:\n{design}\n\nOptimizations:"
        return self.call_llm(prompt)
