"""
VETKA QA Agent - Quality Assurance for testing and verification.

@status: active
@phase: 96
@depends: base_agent.BaseAgent
@used_by: orchestrator, workflow agents
"""
from .base_agent import BaseAgent

class VETKAQAAgent(BaseAgent):
    def __init__(self):
        super().__init__("VETKA-QA")
        self.model = "ollama/deepseek-coder:6.7b"
        self.token_budget = 3000  # MEDIUM complexity budget
        
    def execute(self, implementation: str, context_section: str = "") -> dict:
        """Execute task with optional learning context"""
        system_prompt = """You are VETKA-QA Agent. Your role is to:
1. Design comprehensive test cases
2. Identify edge cases and potential bugs
3. Verify implementation against requirements
4. Provide quality assurance checklist

Output format:
- Test scenarios (happy path + edge cases)
- Bug findings if any
- Quality checklist
- Recommendations"""
        
        if context_section:
            system_prompt += f"\n\n{context_section}"
            system_prompt += "\n\nUse past test scenarios as reference. Apply learned best practices."
        
        prompt = f"{system_prompt}\n\nImplementation:\n{implementation}\n\nProvide test plan:"
        
        response = self.call_llm(prompt, max_tokens=self.token_budget)
        
        return {
            "agent": "QA",
            "implementation": implementation,
            "test_plan": response,
            "tokens_used": self.tokens_used,
            "token_budget": self.token_budget
        }
    
    def test_feature(self, feature: str) -> str:
        prompt = f"You are QA Engineer. Create comprehensive test cases for: {feature}\n\nTest plan:"
        return self.call_llm(prompt)
    
    def find_bugs(self, code: str) -> str:
        prompt = f"Review for bugs and edge cases:\n{code}\n\nBug report:"
        return self.call_llm(prompt)
