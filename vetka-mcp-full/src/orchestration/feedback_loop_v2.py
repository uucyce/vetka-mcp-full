"""
FEEDBACK LOOP v2 for PHASE 7.4.

Self-learning system: use feedback to improve future performance.

@status: active
@phase: 96
@depends: weaviate, dataclasses, threading
@used_by: src.orchestration.orchestrator_with_elisya
"""

import time
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import threading
from datetime import datetime

try:
    import weaviate
    from weaviate.classes.query import MetadataQuery
    WEAVIATE_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False


@dataclass
class FeedbackRecord:
    """User feedback on evaluation result"""
    eval_id: str
    task: str
    output: str
    rating: str  # "good", "poor", "retry"
    score: float  # 0.0-1.0
    correction: Optional[str] = None
    agent: str = "unknown"
    complexity: str = "MEDIUM"
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self):
        return asdict(self)


class FeedbackLoopV2:
    """
    Self-learning feedback system for VETKA
    
    Features:
    - Collect user feedback on evaluations
    - Store feedback in Weaviate with semantic embeddings
    - Retrieve similar high-scoring examples (few-shot)
    - Track improvement metrics
    - Auto-suggest corrections for low scores
    """
    
    def __init__(self, weaviate_client=None, embedding_model: str = "gemma:embedding"):
        """
        Initialize feedback loop
        
        Args:
            weaviate_client: Weaviate client instance
            embedding_model: Model for semantic embeddings
        """
        self.weaviate = weaviate_client
        self.embedding_model = embedding_model
        self.lock = threading.RLock()
        
        # In-memory feedback cache
        self.feedback_cache = []
        self.improvement_tracker = {}
        
        # Setup Weaviate collection if available
        if self.weaviate:
            self._ensure_feedback_collection()
    
    def _ensure_feedback_collection(self):
        """Ensure Weaviate has feedback collection"""
        try:
            # Check if VetkaFeedback collection exists
            collections = self.weaviate.collections.list_all()
            collection_names = [c.name for c in collections]
            
            if 'VetkaFeedback' not in collection_names:
                # Create collection
                self.weaviate.collections.create(
                    name='VetkaFeedback',
                    description='User feedback on workflow evaluations',
                    vectorizer_config={
                        'vectorizer': 'text2vec-transformers',
                        'model': self.embedding_model
                    },
                    properties=[
                        {'name': 'eval_id', 'dataType': ['string']},
                        {'name': 'task', 'dataType': ['text']},
                        {'name': 'output', 'dataType': ['text']},
                        {'name': 'rating', 'dataType': ['string']},
                        {'name': 'score', 'dataType': ['number']},
                        {'name': 'correction', 'dataType': ['text']},
                        {'name': 'agent', 'dataType': ['string']},
                        {'name': 'complexity', 'dataType': ['string']},
                        {'name': 'improvement_delta', 'dataType': ['number']},
                        {'name': 'timestamp', 'dataType': ['date']},
                    ]
                )
                print("✅ VetkaFeedback collection created")
        except Exception as e:
            print(f"⚠️  Could not ensure feedback collection: {e}")
    
    def submit_feedback(self, 
                       eval_id: str,
                       task: str,
                       output: str,
                       rating: str,
                       score: float,
                       correction: Optional[str] = None,
                       agent: str = "unknown",
                       complexity: str = "MEDIUM") -> bool:
        """
        Submit user feedback on evaluation
        
        Args:
            eval_id: Evaluation ID
            task: Original task/prompt
            output: Agent output
            rating: User rating (good/poor/retry)
            score: Score from EvalAgent (0.0-1.0)
            correction: Optional user correction
            agent: Which agent (PM, Dev, QA, Architect)
            complexity: Task complexity (LOW/MEDIUM/HIGH)
        
        Returns:
            True if successfully saved
        """
        with self.lock:
            feedback = FeedbackRecord(
                eval_id=eval_id,
                task=task,
                output=output,
                rating=rating,
                score=score,
                correction=correction,
                agent=agent,
                complexity=complexity
            )
            
            # Save to in-memory cache
            self.feedback_cache.append(feedback)
            
            # Save to Weaviate if available
            if self.weaviate:
                try:
                    collection = self.weaviate.collections.get('VetkaFeedback')
                    
                    # Create combined text for embedding
                    combined_text = f"{agent}: {task}\n{output}"
                    if correction:
                        combined_text += f"\nCorrection: {correction}"
                    
                    collection.data.create(
                        properties={
                            'eval_id': eval_id,
                            'task': task,
                            'output': output,
                            'rating': rating,
                            'score': score,
                            'correction': correction or '',
                            'agent': agent,
                            'complexity': complexity,
                            'timestamp': datetime.fromtimestamp(feedback.timestamp).isoformat(),
                        }
                    )
                    
                    print(f"✅ Feedback saved: {eval_id} → {rating}")
                    return True
                except Exception as e:
                    print(f"⚠️  Failed to save feedback to Weaviate: {e}")
            
            return True
    
    def get_similar_examples(self, 
                            task: str,
                            agent: str,
                            complexity: str = "MEDIUM",
                            limit: int = 3,
                            min_score: float = 0.8) -> List[Dict]:
        """
        Retrieve similar high-scoring examples for few-shot learning
        
        Args:
            task: Current task/prompt
            agent: Agent type (PM, Dev, QA, Architect)
            complexity: Task complexity
            limit: Number of examples to return
            min_score: Minimum score threshold
        
        Returns:
            List of similar high-scoring examples
        """
        if not self.weaviate:
            print("⚠️  Weaviate not available, using in-memory cache")
            return self._get_similar_from_cache(task, agent, limit, min_score)
        
        try:
            collection = self.weaviate.collections.get('VetkaFeedback')
            
            # Search with filters (similarity search via Weaviate)
            results = collection.query.fetch_objects(
                limit=limit * 3,  # Fetch more to filter
                where={
                    'operator': 'And',
                    'operands': [
                        {'path': ['agent'], 'operator': 'Equal', 'valueString': agent},
                        {'path': ['score'], 'operator': 'GreaterOrEqual', 'valueNumber': min_score},
                        {'path': ['rating'], 'operator': 'Equal', 'valueString': 'good'},
                    ]
                }
            )
            
            examples = []
            for obj in results.objects[:limit]:
                examples.append({
                    'task': obj.properties.get('task'),
                    'output': obj.properties.get('output'),
                    'correction': obj.properties.get('correction'),
                    'score': obj.properties.get('score'),
                    'complexity': obj.properties.get('complexity')
                })
            
            if examples:
                print(f"📚 Found {len(examples)} similar high-scoring examples for {agent}")
            
            return examples
        
        except Exception as e:
            print(f"⚠️  Error retrieving similar examples: {e}")
            return self._get_similar_from_cache(task, agent, limit, min_score)
    
    def _get_similar_from_cache(self, task: str, agent: str, 
                               limit: int, min_score: float) -> List[Dict]:
        """Get similar examples from in-memory cache (fallback)"""
        with self.lock:
            # Filter by agent, score, and rating
            similar = [
                {
                    'task': f.task,
                    'output': f.output,
                    'correction': f.correction,
                    'score': f.score,
                    'complexity': f.complexity
                }
                for f in self.feedback_cache
                if f.agent == agent and f.score >= min_score and f.rating == 'good'
            ]
            return similar[:limit]
    
    def track_improvement(self, 
                         eval_id: str,
                         before_score: float,
                         after_score: float,
                         feedback_applied: str = "manual_correction") -> Dict:
        """
        Track if feedback improved performance
        
        Args:
            eval_id: Evaluation ID
            before_score: Score before feedback
            after_score: Score after feedback
            feedback_applied: Type of feedback (manual_correction, few_shot, retry)
        
        Returns:
            Improvement metrics
        """
        delta = after_score - before_score
        improvement_pct = (delta / before_score * 100) if before_score > 0 else 0
        
        with self.lock:
            self.improvement_tracker[eval_id] = {
                'before_score': before_score,
                'after_score': after_score,
                'delta': delta,
                'improvement_pct': improvement_pct,
                'feedback_type': feedback_applied,
                'timestamp': time.time()
            }
        
        if delta > 0:
            print(f"📈 Improvement detected: {delta:.3f} (+{improvement_pct:.1f}%)")
        elif delta < 0:
            print(f"📉 Regression: {delta:.3f} ({improvement_pct:.1f}%)")
        
        return {
            'improvement': delta > 0,
            'delta': delta,
            'improvement_pct': improvement_pct
        }
    
    def get_improvement_stats(self) -> Dict:
        """Get aggregate improvement statistics"""
        with self.lock:
            if not self.improvement_tracker:
                return {'total_improvements': 0, 'avg_delta': 0}
            
            deltas = [v['delta'] for v in self.improvement_tracker.values()]
            positive = sum(1 for d in deltas if d > 0)
            
            return {
                'total_tracked': len(self.improvement_tracker),
                'improvements': positive,
                'regressions': len(deltas) - positive,
                'improvement_rate': positive / len(deltas) if deltas else 0,
                'avg_delta': sum(deltas) / len(deltas) if deltas else 0,
                'max_improvement': max(deltas) if deltas else 0
            }
    
    def get_feedback_summary(self) -> Dict:
        """Get summary of all feedback"""
        with self.lock:
            if not self.feedback_cache:
                return {'total_feedback': 0}
            
            ratings = {}
            for f in self.feedback_cache:
                ratings[f.rating] = ratings.get(f.rating, 0) + 1
            
            scores = [f.score for f in self.feedback_cache]
            
            return {
                'total_feedback': len(self.feedback_cache),
                'ratings_breakdown': ratings,
                'avg_score': sum(scores) / len(scores) if scores else 0,
                'score_distribution': {
                    'high': sum(1 for s in scores if s >= 0.8),
                    'medium': sum(1 for s in scores if 0.6 <= s < 0.8),
                    'low': sum(1 for s in scores if s < 0.6)
                },
                'improvement_stats': self.get_improvement_stats()
            }
    
    def export_feedback(self, format: str = 'json') -> str:
        """Export feedback for analysis"""
        summary = self.get_feedback_summary()
        
        if format == 'json':
            return json.dumps(summary, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def clear_feedback(self):
        """Clear feedback cache (use with caution)"""
        with self.lock:
            self.feedback_cache.clear()
            self.improvement_tracker.clear()
        print("🗑️  Feedback cache cleared")


# Singleton instance
_feedback_loop = None


def init_feedback_loop(weaviate_client=None) -> FeedbackLoopV2:
    """Initialize global feedback loop"""
    global _feedback_loop
    _feedback_loop = FeedbackLoopV2(weaviate_client=weaviate_client)
    return _feedback_loop


def get_feedback_loop() -> Optional[FeedbackLoopV2]:
    """Get global feedback loop"""
    return _feedback_loop


# ============ INTEGRATION EXAMPLE ============
"""
# In orchestrator, after EvalAgent scores:

from src.orchestration.feedback_loop_v2 import init_feedback_loop, get_feedback_loop

# Initialize (usually once on startup)
feedback_loop = init_feedback_loop(weaviate_client=memory_manager.weaviate)

# After evaluation
if eval_score < 0.7:
    # Get few-shot examples
    similar_examples = feedback_loop.get_similar_examples(
        task=original_task,
        agent=agent_name,
        complexity=complexity,
        min_score=0.85
    )
    
    # Inject into agent prompt
    if similar_examples:
        few_shot_context = "Here are similar high-scoring examples:\n"
        for ex in similar_examples[:2]:
            few_shot_context += f"- Task: {ex['task']}\n"
            few_shot_context += f"  Good output: {ex['output']}\n"
        
        # Retry agent with few-shot context
        retry_prompt = f"{few_shot_context}\nNow handle: {original_task}"
        # ... call agent again ...

# Store feedback from user
feedback_loop.submit_feedback(
    eval_id=eval_id,
    task=task,
    output=output,
    rating='good' | 'poor' | 'retry',
    score=eval_score,
    correction=user_correction,  # if provided
    agent=agent_name
)

# Track improvement
improvement = feedback_loop.track_improvement(
    eval_id=eval_id,
    before_score=before,
    after_score=after,
    feedback_applied='few_shot' | 'manual_correction'
)
"""
