"""
PHASE 7.3 — Prometheus Metrics Collector.

Collects metrics from workflows and exports in Prometheus format.
Can be used with Grafana Dashboard for visualization.

Usage:
    metrics = PrometheusMetrics()
    result = orchestrator.get_workflow_result(workflow_id)
    metrics.record_workflow(result)

    # Get metrics text for /metrics endpoint
    metrics_text = metrics.export_metrics()

@status: active
@phase: 96
@depends: time, typing, dataclasses, collections
@used_by: monitoring.__init__, api.routes.health_routes
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class WorkflowMetrics:
    """Metrics for a single workflow"""
    workflow_id: str
    eval_score: float
    total_time: float
    dev_latency: float
    qa_latency: float
    memory_entries: int
    retry_rate: float
    timestamp: float
    status: str
    error: Optional[str] = None


class PrometheusMetrics:
    """Prometheus metrics collector for VETKA workflows"""
    
    def __init__(self):
        self.workflows: Dict[str, WorkflowMetrics] = {}
        self.counters = defaultdict(int)
        self.gauges = {}
    
    def record_workflow(self, result: Dict[str, Any]) -> None:
        """Record workflow execution metrics"""
        
        workflow_id = result.get('workflow_id', 'unknown')
        eval_score = result.get('eval_score', 0.0)
        total_time = result.get('total_time', 0.0)
        dev_latency = result.get('dev_latency', 0.0)
        qa_latency = result.get('qa_latency', 0.0)
        memory_entries = len(result.get('memory_entries', []))
        status = result.get('status', 'unknown')
        error = result.get('error', None)
        
        # Infer retry rate from feedback
        eval_feedback = result.get('eval_feedback', '').lower()
        retry_rate = 1.0 if 'retry' in eval_feedback else 0.0
        
        metrics = WorkflowMetrics(
            workflow_id=workflow_id,
            eval_score=eval_score,
            total_time=total_time,
            dev_latency=dev_latency,
            qa_latency=qa_latency,
            memory_entries=memory_entries,
            retry_rate=retry_rate,
            timestamp=time.time(),
            status=status,
            error=error
        )
        
        self.workflows[workflow_id] = metrics
        
        # Update counters
        self.counters['workflows_total'] += 1
        if status == 'complete':
            self.counters['workflows_complete'] += 1
        elif status == 'failed':
            self.counters['workflows_failed'] += 1
        
        # Update gauges
        self.gauges[f'eval_score_{workflow_id}'] = eval_score
        self.gauges[f'total_time_{workflow_id}'] = total_time
    
    def export_metrics(self) -> str:
        """Export metrics in Prometheus text format"""
        
        lines = []
        timestamp_ms = int(time.time() * 1000)
        
        # TYPE declarations
        lines.append("# HELP vetka_eval_score Evaluation score for workflow (0-1)")
        lines.append("# TYPE vetka_eval_score gauge")
        
        lines.append("# HELP vetka_workflow_total_time_seconds Total execution time")
        lines.append("# TYPE vetka_workflow_total_time_seconds gauge")
        
        lines.append("# HELP vetka_dev_latency_seconds Development node latency")
        lines.append("# TYPE vetka_dev_latency_seconds gauge")
        
        lines.append("# HELP vetka_qa_latency_seconds QA node latency")
        lines.append("# TYPE vetka_qa_latency_seconds gauge")
        
        lines.append("# HELP vetka_memory_entries_total Memory entries created")
        lines.append("# TYPE vetka_memory_entries_total gauge")
        
        lines.append("# HELP vetka_retry_rate Retry rate (1 if retry, 0 otherwise)")
        lines.append("# TYPE vetka_retry_rate gauge")
        
        lines.append("# HELP vetka_workflows_total Total workflows executed")
        lines.append("# TYPE vetka_workflows_total counter")
        
        lines.append("# HELP vetka_workflows_complete Successfully completed workflows")
        lines.append("# TYPE vetka_workflows_complete counter")
        
        lines.append("# HELP vetka_workflows_failed Failed workflows")
        lines.append("# TYPE vetka_workflows_failed counter")
        
        lines.append("# HELP vetka_avg_eval_score Average evaluation score")
        lines.append("# TYPE vetka_avg_eval_score gauge")
        
        lines.append("# HELP vetka_min_eval_score Minimum evaluation score")
        lines.append("# TYPE vetka_min_eval_score gauge")
        
        lines.append("# HELP vetka_max_eval_score Maximum evaluation score")
        lines.append("# TYPE vetka_max_eval_score gauge")
        
        lines.append("")
        
        # Metrics from workflows
        for workflow_id, metrics in self.workflows.items():
            lines.append(f'vetka_eval_score{{workflow_id="{workflow_id}",status="{metrics.status}"}} {metrics.eval_score:.4f} {timestamp_ms}')
            lines.append(f'vetka_workflow_total_time_seconds{{workflow_id="{workflow_id}"}} {metrics.total_time:.2f} {timestamp_ms}')
            lines.append(f'vetka_dev_latency_seconds{{workflow_id="{workflow_id}"}} {metrics.dev_latency:.2f} {timestamp_ms}')
            lines.append(f'vetka_qa_latency_seconds{{workflow_id="{workflow_id}"}} {metrics.qa_latency:.2f} {timestamp_ms}')
            lines.append(f'vetka_memory_entries_total{{workflow_id="{workflow_id}"}} {metrics.memory_entries} {timestamp_ms}')
            lines.append(f'vetka_retry_rate{{workflow_id="{workflow_id}"}} {metrics.retry_rate:.2f} {timestamp_ms}')
        
        # Counters
        lines.append(f'vetka_workflows_total {self.counters["workflows_total"]} {timestamp_ms}')
        lines.append(f'vetka_workflows_complete {self.counters["workflows_complete"]} {timestamp_ms}')
        lines.append(f'vetka_workflows_failed {self.counters["workflows_failed"]} {timestamp_ms}')
        
        # Aggregate gauges
        if self.workflows:
            scores = [m.eval_score for m in self.workflows.values() if m.status == 'complete']
            if scores:
                avg_score = sum(scores) / len(scores)
                min_score = min(scores)
                max_score = max(scores)
                lines.append(f'vetka_avg_eval_score {avg_score:.4f} {timestamp_ms}')
                lines.append(f'vetka_min_eval_score {min_score:.4f} {timestamp_ms}')
                lines.append(f'vetka_max_eval_score {max_score:.4f} {timestamp_ms}')
        
        return "\n".join(lines)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        
        if not self.workflows:
            return {
                "total": 0,
                "complete": 0,
                "failed": 0,
                "avg_score": 0,
                "min_score": 0,
                "max_score": 0,
                "avg_time": 0
            }
        
        complete_workflows = [m for m in self.workflows.values() if m.status == 'complete']
        failed_workflows = [m for m in self.workflows.values() if m.status == 'failed']
        
        scores = [m.eval_score for m in complete_workflows]
        times = [m.total_time for m in complete_workflows]
        
        return {
            "total": len(self.workflows),
            "complete": len(complete_workflows),
            "failed": len(failed_workflows),
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "avg_time": sum(times) / len(times) if times else 0,
            "recent_workflows": [
                {
                    "id": m.workflow_id,
                    "score": m.eval_score,
                    "time": m.total_time,
                    "status": m.status
                }
                for m in sorted(self.workflows.values(), key=lambda x: x.timestamp, reverse=True)[:5]
            ]
        }
