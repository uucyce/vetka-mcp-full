"""
METRICS ENGINE for PHASE 7.4.

Real-time collection, aggregation, and streaming of workflow metrics.
Provides per-agent latency tracking, workflow timeline visualization,
model usage analytics, score distribution analysis, and retry rate tracking.

@status: active
@phase: 96
@depends: time, json, typing, collections, dataclasses, enum, threading, statistics
@used_by: orchestration, api.routes.health_routes
"""

import time
import json
from typing import Dict, List, Optional, Tuple
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import statistics


class FeedbackType(Enum):
    """User feedback classification"""
    GOOD = "good"
    POOR = "poor"
    RETRY = "retry"
    UNKNOWN = "unknown"


@dataclass
class AgentMetrics:
    """Per-agent performance metrics"""
    name: str
    duration: float
    status: str  # "success", "error", "timeout"
    model: str
    tokens_used: int = 0
    cost: float = 0.0
    
    def to_dict(self):
        return asdict(self)


@dataclass
class WorkflowMetrics:
    """Complete workflow metrics"""
    workflow_id: str
    feature: str
    start_time: float
    end_time: Optional[float] = None
    agents: List[AgentMetrics] = None
    eval_score: float = 0.0
    feedback_type: Optional[str] = None
    retry_count: int = 0
    total_duration: float = 0.0
    success: bool = False
    
    def __post_init__(self):
        if self.agents is None:
            self.agents = []
    
    def to_dict(self):
        return {
            'workflow_id': self.workflow_id,
            'feature': self.feature,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'agents': [a.to_dict() for a in self.agents],
            'eval_score': self.eval_score,
            'feedback_type': self.feedback_type,
            'retry_count': self.retry_count,
            'total_duration': self.total_duration,
            'success': self.success
        }


class MetricsEngine:
    """
    Real-time metrics collection and aggregation for VETKA workflows
    
    Features:
    - Per-agent latency tracking
    - Workflow timeline visualization
    - Model usage analytics
    - Score distribution analysis
    - Retry rate tracking
    - Feedback breakdown
    """
    
    def __init__(self, max_history=500, window_size=100):
        self.max_history = max_history
        self.window_size = window_size  # For rolling statistics
        
        # Current workflows
        self.workflows: Dict[str, WorkflowMetrics] = {}
        
        # Historical workflows (bounded deque)
        self.workflow_history = deque(maxlen=max_history)
        
        # Per-agent statistics
        self.agent_stats: Dict[str, Dict] = defaultdict(lambda: {
            'total_runs': 0,
            'total_duration': 0.0,
            'durations': deque(maxlen=window_size),
            'success_count': 0,
            'error_count': 0,
            'timeout_count': 0,
            'models_used': defaultdict(int),
            'total_tokens': 0,
            'total_cost': 0.0
        })
        
        # Model usage tracking
        self.model_usage: Dict[str, Dict] = defaultdict(lambda: {
            'usage_count': 0,
            'total_duration': 0.0,
            'success_count': 0,
            'error_count': 0,
            'avg_cost': 0.0
        })
        
        # Scores and feedback
        self.scores = deque(maxlen=window_size)
        self.feedback_breakdown = {
            'good': 0,
            'poor': 0,
            'retry': 0,
            'unknown': 0
        }
        
        # Retry tracking
        self.retries = deque(maxlen=window_size)
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Callbacks for real-time updates
        self.callbacks = []
    
    def register_callback(self, callback):
        """Register callback for real-time metric updates"""
        self.callbacks.append(callback)
    
    def _emit_update(self, event_type: str, data: Dict):
        """Emit metric update to all registered callbacks"""
        with self.lock:
            for callback in self.callbacks:
                try:
                    callback(event_type=event_type, data=data)
                except Exception as e:
                    print(f"⚠️  Callback error: {e}")

    def record_event(self, event_type: str, data: Dict = None):
        """Record a generic event (used for system events like qdrant_connected)"""
        self._emit_update(event_type, data or {})

    # ============ WORKFLOW LIFECYCLE ============
    
    def record_workflow_start(self, workflow_id: str, feature: str):
        """Record workflow start"""
        with self.lock:
            metrics = WorkflowMetrics(
                workflow_id=workflow_id,
                feature=feature,
                start_time=time.time()
            )
            self.workflows[workflow_id] = metrics
        
        self._emit_update('workflow_started', {
            'workflow_id': workflow_id,
            'feature': feature,
            'timestamp': time.time()
        })
    
    def record_agent_start(self, workflow_id: str, agent_name: str):
        """Record agent execution start"""
        self._emit_update('agent_started', {
            'workflow_id': workflow_id,
            'agent': agent_name,
            'timestamp': time.time()
        })
    
    def record_agent_complete(self, workflow_id: str, agent_name: str, 
                            duration: float, status: str = "success",
                            model: str = "unknown", tokens: int = 0, 
                            cost: float = 0.0):
        """Record agent completion with metrics"""
        with self.lock:
            if workflow_id not in self.workflows:
                print(f"⚠️  Workflow {workflow_id} not found")
                return
            
            workflow = self.workflows[workflow_id]
            
            # Add agent metrics
            agent_metric = AgentMetrics(
                name=agent_name,
                duration=duration,
                status=status,
                model=model,
                tokens_used=tokens,
                cost=cost
            )
            workflow.agents.append(agent_metric)
            
            # Update agent stats
            agent_stat = self.agent_stats[agent_name]
            agent_stat['total_runs'] += 1
            agent_stat['total_duration'] += duration
            agent_stat['durations'].append(duration)
            
            if status == "success":
                agent_stat['success_count'] += 1
            elif status == "error":
                agent_stat['error_count'] += 1
            elif status == "timeout":
                agent_stat['timeout_count'] += 1
            
            # Track model usage
            if model != "unknown":
                agent_stat['models_used'][model] += 1
                agent_stat['total_tokens'] += tokens
                agent_stat['total_cost'] += cost
                
                model_stat = self.model_usage[model]
                model_stat['usage_count'] += 1
                model_stat['total_duration'] += duration
                if status == "success":
                    model_stat['success_count'] += 1
                else:
                    model_stat['error_count'] += 1
                model_stat['avg_cost'] = (model_stat['avg_cost'] * 
                                         (model_stat['usage_count'] - 1) + cost) / model_stat['usage_count']
        
        self._emit_update('agent_complete', {
            'workflow_id': workflow_id,
            'agent': agent_name,
            'duration': duration,
            'status': status,
            'model': model,
            'timestamp': time.time()
        })
    
    def record_eval_score(self, workflow_id: str, score: float, 
                         feedback_type: Optional[str] = None):
        """Record evaluation score and feedback"""
        with self.lock:
            if workflow_id not in self.workflows:
                print(f"⚠️  Workflow {workflow_id} not found")
                return
            
            workflow = self.workflows[workflow_id]
            workflow.eval_score = score
            workflow.feedback_type = feedback_type or FeedbackType.UNKNOWN.value
            
            # Track score
            self.scores.append(score)
            
            # Track feedback
            if feedback_type:
                self.feedback_breakdown[feedback_type] = \
                    self.feedback_breakdown.get(feedback_type, 0) + 1
        
        self._emit_update('eval_score', {
            'workflow_id': workflow_id,
            'score': score,
            'feedback_type': feedback_type,
            'timestamp': time.time()
        })
    
    def record_retry(self, workflow_id: str, reason: str):
        """Record workflow retry"""
        with self.lock:
            if workflow_id not in self.workflows:
                return
            
            workflow = self.workflows[workflow_id]
            workflow.retry_count += 1
            self.retries.append({
                'workflow_id': workflow_id,
                'retry_count': workflow.retry_count,
                'reason': reason,
                'timestamp': time.time()
            })
        
        self._emit_update('workflow_retry', {
            'workflow_id': workflow_id,
            'retry_count': workflow.workflows[workflow_id].retry_count,
            'reason': reason,
            'timestamp': time.time()
        })
    
    def record_workflow_complete(self, workflow_id: str, success: bool = True):
        """Record workflow completion"""
        with self.lock:
            if workflow_id not in self.workflows:
                print(f"⚠️  Workflow {workflow_id} not found")
                return
            
            workflow = self.workflows[workflow_id]
            workflow.end_time = time.time()
            workflow.total_duration = workflow.end_time - workflow.start_time
            workflow.success = success
            
            # Move to history
            self.workflow_history.append(workflow)
            del self.workflows[workflow_id]
        
        self._emit_update('workflow_complete', {
            'workflow_id': workflow_id,
            'duration': workflow.total_duration,
            'success': success,
            'score': workflow.eval_score,
            'timestamp': time.time()
        })
    
    # ============ STATISTICS & AGGREGATION ============
    
    def get_agent_stats(self, agent_name: Optional[str] = None) -> Dict:
        """Get statistics for agent(s)"""
        with self.lock:
            if agent_name:
                stats = self.agent_stats.get(agent_name, {})
                if not stats.get('total_runs'):
                    return {'agent': agent_name, 'no_data': True}
                
                durations = list(stats['durations'])
                return {
                    'agent': agent_name,
                    'total_runs': stats['total_runs'],
                    'success_rate': stats['success_count'] / stats['total_runs'],
                    'avg_duration': statistics.mean(durations) if durations else 0,
                    'min_duration': min(durations) if durations else 0,
                    'max_duration': max(durations) if durations else 0,
                    'median_duration': statistics.median(durations) if durations else 0,
                    'models_used': dict(stats['models_used']),
                    'total_tokens': stats['total_tokens'],
                    'total_cost': stats['total_cost']
                }
            else:
                # Return all agents
                return {
                    name: self.get_agent_stats(name)
                    for name in self.agent_stats.keys()
                }
    
    def get_model_stats(self) -> Dict:
        """Get model usage statistics"""
        with self.lock:
            return {
                model: dict(stats)
                for model, stats in self.model_usage.items()
            }
    
    def get_score_distribution(self) -> Dict:
        """Get score distribution analysis"""
        with self.lock:
            if not self.scores:
                return {'total': 0, 'avg': 0, 'min': 0, 'max': 0}
            
            scores = list(self.scores)
            return {
                'total': len(scores),
                'avg': statistics.mean(scores),
                'median': statistics.median(scores),
                'min': min(scores),
                'max': max(scores),
                'stdev': statistics.stdev(scores) if len(scores) > 1 else 0,
                'distribution': self._score_histogram(scores)
            }
    
    def get_feedback_breakdown(self) -> Dict:
        """Get feedback category breakdown"""
        with self.lock:
            total = sum(self.feedback_breakdown.values())
            if total == 0:
                return {k: {'count': 0, 'percentage': 0} for k in self.feedback_breakdown}
            
            return {
                category: {
                    'count': count,
                    'percentage': (count / total * 100)
                }
                for category, count in self.feedback_breakdown.items()
            }
    
    def get_retry_stats(self) -> Dict:
        """Get retry analysis"""
        with self.lock:
            if not self.retries:
                return {'total_retries': 0, 'avg_per_workflow': 0}
            
            retries = list(self.retries)
            total_retries = sum(r['retry_count'] for r in retries)
            
            return {
                'total_retry_events': len(retries),
                'total_retry_count': total_retries,
                'avg_retries_per_workflow': total_retries / len(retries) if retries else 0,
                'retry_reasons': self._count_retry_reasons(retries)
            }
    
    # ============ DASHBOARD DATA ============
    
    def get_dashboard_data(self) -> Dict:
        """Get all data needed for dashboard"""
        with self.lock:
            return {
                'timestamp': time.time(),
                'workflows': {
                    'current': len(self.workflows),
                    'completed': len(self.workflow_history),
                    'total': len(self.workflows) + len(self.workflow_history)
                },
                'latency': self._get_latency_summary(),
                'scores': self.get_score_distribution(),
                'feedback': self.get_feedback_breakdown(),
                'models': self.get_model_stats(),
                'agents': self.get_agent_stats(),
                'retries': self.get_retry_stats(),
                'recent_workflows': self._get_recent_workflows(10)
            }
    
    def get_timeline_data(self, workflow_id: str) -> Dict:
        """Get timeline for specific workflow"""
        with self.lock:
            # Check current workflows
            if workflow_id in self.workflows:
                workflow = self.workflows[workflow_id]
            else:
                # Check history
                workflow = next(
                    (w for w in self.workflow_history if w.workflow_id == workflow_id),
                    None
                )
            
            if not workflow:
                return {'error': 'Workflow not found'}
            
            # Build timeline
            timeline = []
            current_time = workflow.start_time
            
            for agent in workflow.agents:
                timeline.append({
                    'agent': agent.name,
                    'start': current_time,
                    'duration': agent.duration,
                    'end': current_time + agent.duration,
                    'status': agent.status,
                    'model': agent.model
                })
                current_time += agent.duration
            
            return {
                'workflow_id': workflow_id,
                'feature': workflow.feature,
                'total_duration': workflow.total_duration,
                'timeline': timeline,
                'eval_score': workflow.eval_score,
                'feedback': workflow.feedback_type
            }
    
    # ============ HELPER METHODS ============
    
    def _score_histogram(self, scores: List[float], bins: int = 10) -> Dict:
        """Create score distribution histogram"""
        histogram = defaultdict(int)
        for score in scores:
            bin_idx = min(int(score * bins), bins - 1)
            histogram[f"{bin_idx/bins:.1f}-{(bin_idx+1)/bins:.1f}"] += 1
        return dict(histogram)
    
    def _count_retry_reasons(self, retries: List) -> Dict:
        """Count retry reasons"""
        reasons = defaultdict(int)
        for retry in retries:
            reasons[retry.get('reason', 'unknown')] += 1
        return dict(reasons)
    
    def _get_latency_summary(self) -> Dict:
        """Get latency summary per agent"""
        with self.lock:
            result = {}
            for agent_name, stats in self.agent_stats.items():
                durations = list(stats['durations'])
                if durations:
                    result[agent_name] = {
                        'avg': statistics.mean(durations),
                        'median': statistics.median(durations),
                        'min': min(durations),
                        'max': max(durations)
                    }
            return result
    
    def _get_recent_workflows(self, limit: int) -> List[Dict]:
        """Get recent completed workflows"""
        with self.lock:
            recent = list(self.workflow_history)[-limit:]
            recent.reverse()  # Most recent first
            return [w.to_dict() for w in recent]
    
    def export_metrics(self, format: str = 'json') -> str:
        """Export all metrics in specified format"""
        data = self.get_dashboard_data()
        
        if format == 'json':
            return json.dumps(data, indent=2, default=str)
        elif format == 'csv':
            # Simple CSV export of recent workflows
            workflows = data['recent_workflows']
            csv_lines = [
                "workflow_id,duration,success,score,feedback,timestamp"
            ]
            for w in workflows:
                csv_lines.append(
                    f"{w['workflow_id']},{w['total_duration']},{w['success']},"
                    f"{w['eval_score']},{w['feedback_type']},{w['start_time']}"
                )
            return '\n'.join(csv_lines)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def clear_history(self):
        """Clear workflow history (use cautiously)"""
        with self.lock:
            self.workflow_history.clear()
            self.scores.clear()
            self.retries.clear()
            self.feedback_breakdown = {k: 0 for k in self.feedback_breakdown}


# Singleton instance for global access
_metrics_engine = None


def get_metrics_engine() -> MetricsEngine:
    """Get or create global metrics engine"""
    global _metrics_engine
    if _metrics_engine is None:
        _metrics_engine = MetricsEngine()
    return _metrics_engine


def init_metrics_engine(max_history=500, window_size=100) -> MetricsEngine:
    """Initialize metrics engine with custom settings"""
    global _metrics_engine
    _metrics_engine = MetricsEngine(max_history=max_history, window_size=window_size)
    return _metrics_engine
