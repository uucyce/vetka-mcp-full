"""
LLM Executor Bridge - Connects ModelRouter v2 with APIGateway for actual LLM calls.

@status: active
@phase: 96
@depends: typing, logging
@used_by: orchestrator, agents
"""

from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class LLMExecutorBridge:
    """
    Bridge between ModelRouter (which selects models) and APIGateway (which calls LLMs)
    
    Usage:
        executor = LLMExecutorBridge(model_router, api_gateway)
        response = executor.call(prompt, task_type="dev_coding", complexity="MEDIUM")
    """
    
    def __init__(self, model_router_v2=None, api_gateway=None):
        """
        Initialize the bridge
        
        Args:
            model_router_v2: ModelRouterV2 instance for model selection
            api_gateway: APIGateway instance for actual API calls
        """
        self.router = model_router_v2
        self.gateway = api_gateway
        self.call_history = []
    
    def call(self, 
             prompt: str, 
             task_type: str = "unknown",
             complexity: str = "MEDIUM",
             timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Call LLM through APIGateway with ModelRouter selection
        
        Args:
            prompt: The actual prompt to send
            task_type: Task type for ModelRouter routing
            complexity: Complexity level (LOW, MEDIUM, HIGH)
            timeout: Override default timeout
        
        Returns:
            Dict with response, model, provider, duration, etc.
        """
        
        # If APIGateway not available, return error
        if not self.gateway:
            logger.warning("⚠️  APIGateway not available, cannot call LLM")
            return {
                'success': False,
                'error': 'APIGateway not initialized',
                'model': None,
                'provider': None,
                'response': None
            }
        
        try:
            # Call through APIGateway with automatic failover
            result = self.gateway.call_model(
                task_type=task_type,
                prompt=prompt,
                complexity=complexity,
                timeout=timeout
            )
            
            # Log the call
            self.call_history.append({
                'prompt': prompt[:100],  # Log first 100 chars
                'task_type': task_type,
                'model': result.model,
                'provider': result.provider,
                'success': result.success
            })
            
            return {
                'success': result.success,
                'response': result.response if result.success else None,
                'error': result.error if not result.success else None,
                'model': result.model,
                'provider': result.provider,
                'duration': result.duration,
                'attempt': result.attempt,
                'total_attempts': result.total_attempts,
                'status_code': result.status_code
            }
            
        except Exception as e:
            logger.error(f"❌ LLMExecutorBridge error: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': None,
                'model': None,
                'provider': None,
                'duration': 0.0
            }
    
    def get_call_history(self, limit: int = 10) -> list:
        """Get recent call history"""
        return self.call_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about calls made"""
        if not self.call_history:
            return {'total_calls': 0}
        
        total = len(self.call_history)
        successful = sum(1 for call in self.call_history if call.get('success'))
        failed = total - successful
        
        return {
            'total_calls': total,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / total if total > 0 else 0,
            'recent_calls': self.get_call_history(5)
        }


# Singleton instance
_llm_executor_bridge = None


def init_llm_executor_bridge(model_router_v2=None, api_gateway=None) -> LLMExecutorBridge:
    """Initialize global LLM executor bridge"""
    global _llm_executor_bridge
    _llm_executor_bridge = LLMExecutorBridge(model_router_v2, api_gateway)
    return _llm_executor_bridge


def get_llm_executor_bridge() -> Optional[LLMExecutorBridge]:
    """Get global LLM executor bridge"""
    return _llm_executor_bridge
