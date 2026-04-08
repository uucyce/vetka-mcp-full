"""
VETKA Dev Agent - Developer for code implementation and review.

@status: active
@phase: 96
@depends: base_agent.BaseAgent
@used_by: orchestrator, workflow agents
"""
from .base_agent import BaseAgent

class VETKADevAgent(BaseAgent):
    def __init__(self):
        super().__init__("VETKA-Dev")
        self.model = "ollama/deepseek-coder:6.7b"
        self.token_budget = 3000  # MEDIUM complexity budget
        
    def execute(self, plan: str, context_section: str = "") -> dict:
        """Execute task with optional learning context"""
        system_prompt = """You are VETKA-Dev Agent. Your role is to:
1. Write clean, production-ready code
2. Follow best practices and design patterns
3. Include error handling and edge cases
4. Add clear comments and documentation

Output format:
- Code implementation with comments
- Key design decisions
- Error handling strategy
- Testing recommendations"""
        
        if context_section:
            system_prompt += f"\n\n{context_section}"
            system_prompt += "\n\nFollow patterns from high-quality examples. Avoid common mistakes."
        
        prompt = f"{system_prompt}\n\nPlan: {plan}\n\nProvide implementation:"
        
        response = self.call_llm(prompt, max_tokens=self.token_budget)
        
        return {
            "agent": "Dev",
            "plan": plan,
            "implementation": response,
            "tokens_used": self.tokens_used,
            "token_budget": self.token_budget
        }
    
    def implement_feature(self, feature_plan: str) -> str:
        prompt = "You are a Senior Developer. Implement this feature step-by-step with code examples.\nPlan:\n" + feature_plan + "\n\nProvide implementation:"
        return self.call_llm(prompt)
    
    def review_code(self, code: str) -> str:
        prompt = f"Review this code for quality and best practices:\n{code}\n\nCode review:"
        return self.call_llm(prompt)
