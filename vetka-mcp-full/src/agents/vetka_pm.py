"""
VETKA PM Agent - Project Manager for task analysis and strategic planning.

@status: active
@phase: 96
@depends: base_agent.BaseAgent
@used_by: orchestrator, workflow agents
"""
from .base_agent import BaseAgent

class VETKAPMAgent(BaseAgent):
    def __init__(self):
        super().__init__("VETKA-PM")
        self.model = "ollama/deepseek-coder:6.7b"
        self.token_budget = 3000  # MEDIUM complexity budget
        
    def execute(self, task: str, context_section: str = "") -> dict:
        """Execute task with optional learning context"""
        system_prompt = """You are VETKA-PM Agent. Your role is to:
1. Analyze task complexity and requirements
2. Create strategic plan with timeline and dependencies
3. Identify risks and mitigations
4. Deliver clear, actionable plan

Output format:
- Plan Overview (1-2 sentences)
- Key Steps (numbered list)
- Timeline estimate
- Risks & Mitigations
- Success Criteria"""
        
        if context_section:
            system_prompt += f"\n\n{context_section}"
            system_prompt += "\n\nIncorporate learnings from past tasks into this plan. Avoid previous mistakes."
        
        prompt = f"{system_prompt}\n\nTask: {task}\n\nProvide detailed plan:"
        
        response = self.call_llm(prompt, max_tokens=self.token_budget)
        
        return {
            "agent": "PM",
            "task": task,
            "plan": response,
            "tokens_used": self.tokens_used,
            "token_budget": self.token_budget
        }
    
    def plan_feature(self, feature_request: str) -> str:
        role_prompt = "You are PM. Plan features clearly."
        prompt = f"{role_prompt}\nFeature: {feature_request}\n\nCreate plan:"
        return self.call_llm(prompt)
