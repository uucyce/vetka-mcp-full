"""
VETKA Query Dispatcher - Phase B.

Classifies queries and determines optimal routing strategy:
- Simple queries -> Dev only (fast)
- Complex queries -> PM -> Dev -> QA (full chain)
- QA questions -> QA only
- Planning tasks -> PM only

@status: active
@phase: 96
@depends: ollama, dataclasses
@used_by: src.orchestration.router, src.api.handlers
"""

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

logger = logging.getLogger(__name__)


class RouteStrategy(Enum):
    """Routing strategies"""
    DEV_ONLY = "dev_only"           # Fast: just code/tech
    QA_ONLY = "qa_only"             # Testing/QA focus
    PM_ONLY = "pm_only"             # Planning/architecture
    FULL_CHAIN = "full_chain"       # PM → Dev → QA (safe default)


@dataclass
class DispatcherResult:
    """Result from query dispatcher"""
    strategy: RouteStrategy
    confidence: float  # 0.0-1.0
    reasoning: str
    agent_chain: list  # Which agents to call


class QueryDispatcher:
    """Classifies queries and routes to appropriate agents"""
    
    def __init__(self, model: str = "llama3.2:1b", base_url: str = "http://localhost:11434"):
        """
        Initialize dispatcher
        
        Args:
            model: Ollama model to use for classification (llama3.2:1b is light!)
            base_url: Ollama API URL
        """
        self.model = model
        self.base_url = base_url
        self.ollama_available = OLLAMA_AVAILABLE
        
        # Quick heuristics (no LLM needed)
        self.simple_keywords = {
            'write', 'create', 'code', 'function', 'class', 'method',
            'implement', 'fix', 'bug', 'error', 'debug', 'syntax',
            'import', 'library', 'package', 'variable', 'type'
        }
        
        self.qa_keywords = {
            'test', 'unit test', 'test case', 'coverage', 'assert',
            'mock', 'stub', 'integration test', 'e2e', 'qa', 'verify',
            'check', 'validate', 'correct', 'wrong', 'broken'
        }
        
        self.planning_keywords = {
            'plan', 'architecture', 'design', 'structure', 'organize',
            'refactor', 'module', 'pattern', 'best practice', 'strategy',
            'approach', 'workflow', 'pipeline', 'system'
        }
        
        logger.info(f'[DISPATCHER] Initialized with model: {model}')
    
    def classify(self, query: str) -> DispatcherResult:
        """
        Classify query and determine routing
        
        Args:
            query: User query/request
            
        Returns:
            DispatcherResult with routing decision
        """
        query_lower = query.lower()
        
        # ===== HEURISTICS (No LLM needed) =====
        
        # Check for QA keywords
        qa_score = sum(1 for kw in self.qa_keywords if kw in query_lower)
        if qa_score >= 2:
            return DispatcherResult(
                strategy=RouteStrategy.QA_ONLY,
                confidence=0.9,
                reasoning=f"Detected QA/testing keywords ({qa_score}): {query[:50]}...",
                agent_chain=['QA']
            )
        
        # Check for planning keywords
        planning_score = sum(1 for kw in self.planning_keywords if kw in query_lower)
        if planning_score >= 2:
            return DispatcherResult(
                strategy=RouteStrategy.PM_ONLY,
                confidence=0.85,
                reasoning=f"Detected planning/architecture keywords ({planning_score}): {query[:50]}...",
                agent_chain=['PM']
            )
        
        # Check for simple code keywords
        simple_score = sum(1 for kw in self.simple_keywords if kw in query_lower)
        if simple_score >= 2 and qa_score == 0 and planning_score == 0:
            return DispatcherResult(
                strategy=RouteStrategy.DEV_ONLY,
                confidence=0.85,
                reasoning=f"Detected simple coding keywords ({simple_score}): {query[:50]}...",
                agent_chain=['Dev']
            )
        
        # ===== LLM CLASSIFICATION (for ambiguous cases) =====
        if self.ollama_available and len(query) > 20:
            return self._classify_with_llm(query)
        
        # ===== FALLBACK =====
        return DispatcherResult(
            strategy=RouteStrategy.FULL_CHAIN,
            confidence=0.6,
            reasoning="Ambiguous query, using full chain for safety",
            agent_chain=['PM', 'Dev', 'QA']
        )
    
    def _classify_with_llm(self, query: str) -> DispatcherResult:
        """
        Use lightweight LLM to classify query
        Uses llama3.2:1b (1.3GB, very fast)
        """
        try:
            prompt = f"""Classify this query into ONE category:
            
Query: {query}

Categories:
- DEV: Simple code implementation, bug fix, write function (→ Dev only)
- QA: Testing, verification, quality check (→ QA only)
- PLAN: Architecture, design, refactoring, structure (→ PM only)
- COMPLEX: Requires design + implementation + testing (→ PM → Dev → QA)

Respond with ONE word: DEV, QA, PLAN, or COMPLEX"""
            
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={'num_predict': 10}  # Short response only
            )
            
            result = response['response'].strip().upper()
            
            # Map to strategy
            mapping = {
                'DEV': (RouteStrategy.DEV_ONLY, ['Dev']),
                'QA': (RouteStrategy.QA_ONLY, ['QA']),
                'PLAN': (RouteStrategy.PM_ONLY, ['PM']),
                'COMPLEX': (RouteStrategy.FULL_CHAIN, ['PM', 'Dev', 'QA'])
            }
            
            if result in mapping:
                strategy, chain = mapping[result]
                logger.info(f'[DISPATCHER-LLM] Classified as {strategy.value}')
                return DispatcherResult(
                    strategy=strategy,
                    confidence=0.8,
                    reasoning=f"LLM classified as {result}: {query[:50]}...",
                    agent_chain=chain
                )
        except Exception as e:
            logger.warning(f'[DISPATCHER-LLM] Error: {e}, falling back to heuristics')
        
        # Fallback to full chain
        return DispatcherResult(
            strategy=RouteStrategy.FULL_CHAIN,
            confidence=0.6,
            reasoning="LLM classification failed, using full chain",
            agent_chain=['PM', 'Dev', 'QA']
        )


# Singleton instance
_dispatcher_instance: Optional[QueryDispatcher] = None


def get_dispatcher(model: str = "llama3.2:1b") -> QueryDispatcher:
    """Get or create dispatcher singleton"""
    global _dispatcher_instance
    if _dispatcher_instance is None:
        _dispatcher_instance = QueryDispatcher(model=model)
    return _dispatcher_instance


def classify_query(query: str) -> DispatcherResult:
    """Convenience function to classify query"""
    dispatcher = get_dispatcher()
    return dispatcher.classify(query)


if __name__ == '__main__':
    # Test dispatcher
    dispatcher = QueryDispatcher()
    
    test_queries = [
        "write a function to parse JSON",
        "test this endpoint with different inputs",
        "design a microservices architecture",
        "fix the bug in line 42",
        "how do I refactor this module?",
        "verify the API response is correct"
    ]
    
    print("🔀 DISPATCHER TEST")
    print("=" * 60)
    for query in test_queries:
        result = dispatcher.classify(query)
        print(f"\n📝 Query: {query}")
        print(f"   Strategy: {result.strategy.value}")
        print(f"   Confidence: {result.confidence:.0%}")
        print(f"   Agents: {' → '.join(result.agent_chain)}")
        print(f"   Reason: {result.reasoning}")
