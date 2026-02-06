"""
VETKA Streaming Agent - Token-by-token streaming for real-time UI updates.

@status: active
@phase: 96
@depends: requests, json
@used_by: Flask handlers, Socket.IO
"""
import json
import time
from typing import Callable, Optional

class StreamingAgent:
    """Wraps any agent with token-by-token streaming capability"""
    
    def __init__(self, agent, socketio=None):
        """
        Args:
            agent: BaseAgent instance to wrap
            socketio: python-socketio AsyncServer for real-time updates
        """
        self.agent = agent
        self.socketio = socketio
    
    def call_llm_streaming(
        self, 
        prompt: str,
        on_token: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Call Ollama with streaming enabled
        Emits each token via Socket.IO
        """
        import requests
        
        url = f"{self.agent.ollama_base_url}/api/generate"
        full_response = ""
        
        try:
            response = requests.post(
                url,
                json={
                    "model": self.agent.model.replace("ollama/", ""),
                    "prompt": prompt,
                    "stream": True,
                    "temperature": 0.3
                },
                stream=True,
                timeout=300
            )
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        token = data.get("response", "")
                        full_response += token
                        
                        # Call token callback if provided
                        if on_token:
                            on_token(token)
                        
                        # Emit to Socket.IO clients
                        if self.socketio:
                            self.socketio.emit('token_stream', {
                                'token': token,
                                'agent': self.agent.name,
                                'timestamp': time.time()
                            }, skip_sid=None)
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"Streaming error: {e}")
            raise
        
        return full_response
    
    def plan_feature_streaming(self, feature: str) -> str:
        """Stream PM planning"""
        prompt = f"""You are an experienced PM. Plan this feature:
{feature}

Create a detailed 3-point plan including:
1. Requirements and scope
2. Complexity level (Low/Medium/High)
3. Dependencies and blockers

Plan:"""
        return self.call_llm_streaming(prompt)
    
    def design_solution_streaming(self, feature: str) -> str:
        """Stream Architect design"""
        prompt = f"""You are a senior architect. Design a solution for:
{feature}

Include:
1. System architecture
2. Technology choices
3. Scalability considerations

Design:"""
        return self.call_llm_streaming(prompt)
    
    def implement_feature_streaming(self, plan: str) -> str:
        """Stream Dev implementation"""
        prompt = f"""You are a senior developer. Implement based on plan:
{plan}

Write clean, production-ready code with:
1. Proper error handling
2. Type hints
3. Comments for complex logic

Implementation:"""
        return self.call_llm_streaming(prompt)
    
    def test_feature_streaming(self, feature: str) -> str:
        """Stream QA testing"""
        prompt = f"""You are a QA engineer. Create comprehensive tests for:
{feature}

Include:
1. Unit tests
2. Integration tests
3. Edge cases

Tests:"""
        return self.call_llm_streaming(prompt)


# Example usage in Flask handler
def streaming_example(feature: str, socketio):
    """Example of how to use StreamingAgent in Flask"""
    from vetka_live_03.src.agents.vetka_pm import VETKAPMAgent
    
    pm_agent = VETKAPMAgent()
    streaming = StreamingAgent(pm_agent, socketio)
    
    # This will emit tokens in real-time
    result = streaming.plan_feature_streaming(feature)
    return result
