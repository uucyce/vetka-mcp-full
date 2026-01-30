# VETKA Phase 22-MCP-6: Analytics & Self-Improvement (Phoenix)

## 🎯 ЗАДАЧА
Интегрировать Phoenix (Arize) для observability LLM операций:
- Трейсинг всех LLM вызовов
- Метрики качества агентов
- Self-improvement feedback loop
- Dashboard для мониторинга

## 📋 ШАГ 1: АНАЛИЗ

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

# Проверить зависимости
pip show arize-phoenix 2>/dev/null || echo "Phoenix not installed"
pip show opentelemetry-api 2>/dev/null || echo "OpenTelemetry not installed"

# Проверить текущие метрики
ls -la data/mcp_audit/ 2>/dev/null || echo "No audit logs yet"
wc -l data/mcp_audit/*.jsonl 2>/dev/null || echo "No audit entries"

# Порты
lsof -i :6006 2>/dev/null || echo "Port 6006 (Phoenix default) free"
```

## 📋 ШАГ 2: УСТАНОВКА

```bash
# Phoenix (self-hosted LLM observability)
pip install arize-phoenix

# OpenTelemetry для трейсинга
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp

# Phoenix instrumentation для разных провайдеров
pip install openinference-instrumentation-openai
pip install openinference-instrumentation-langchain  # если используем
```

## 📋 ШАГ 3: PHOENIX SERVER

### 3.1 Phoenix Runner (src/analytics/phoenix_server.py)

```python
"""Phoenix observability server for VETKA"""
import os
import threading
from typing import Optional
from pathlib import Path

# Phoenix configuration
PHOENIX_PORT = 6006
PHOENIX_HOST = "127.0.0.1"

class PhoenixServer:
    """Manages Phoenix observability server"""
    
    _instance: Optional['PhoenixServer'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._server = None
        self._thread = None
        self.project_root = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")
        self.data_dir = self.project_root / "data" / "phoenix"
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def start(self, background: bool = True) -> bool:
        """Start Phoenix server"""
        if self._server is not None:
            return True  # Already running
        
        try:
            import phoenix as px
            
            # Set storage path
            os.environ["PHOENIX_WORKING_DIR"] = str(self.data_dir)
            
            if background:
                # Launch in background thread
                self._server = px.launch_app(
                    host=PHOENIX_HOST,
                    port=PHOENIX_PORT
                )
                return True
            else:
                # Blocking mode (for standalone server)
                px.launch_app(
                    host=PHOENIX_HOST,
                    port=PHOENIX_PORT
                )
                return True
                
        except Exception as e:
            print(f"[Phoenix] Failed to start: {e}")
            return False
    
    def stop(self):
        """Stop Phoenix server"""
        if self._server is not None:
            try:
                self._server.stop()
            except:
                pass
            self._server = None
    
    def is_running(self) -> bool:
        """Check if Phoenix is running"""
        import requests
        try:
            response = requests.get(f"http://{PHOENIX_HOST}:{PHOENIX_PORT}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def get_url(self) -> str:
        """Get Phoenix UI URL"""
        return f"http://{PHOENIX_HOST}:{PHOENIX_PORT}"


def get_phoenix_server() -> PhoenixServer:
    """Get Phoenix server singleton"""
    return PhoenixServer()


def start_phoenix():
    """Convenience function to start Phoenix"""
    server = get_phoenix_server()
    return server.start()


if __name__ == "__main__":
    # Run Phoenix standalone
    server = PhoenixServer()
    print(f"Starting Phoenix on {server.get_url()}...")
    server.start(background=False)
```

### 3.2 Tracer для LLM вызовов (src/analytics/tracer.py)

```python
"""OpenTelemetry tracer for VETKA LLM operations"""
import time
import json
from datetime import datetime
from typing import Any, Dict, Optional, Callable
from functools import wraps
from pathlib import Path
import threading

# Trace storage
class TraceStorage:
    """Simple file-based trace storage"""
    
    def __init__(self, storage_dir: str = "data/traces"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
    
    def save_trace(self, trace: Dict[str, Any]):
        """Save trace to daily file"""
        today = datetime.now().strftime("%Y-%m-%d")
        trace_file = self.storage_dir / f"traces_{today}.jsonl"
        
        with self._lock:
            with open(trace_file, 'a') as f:
                f.write(json.dumps(trace) + '\n')
    
    def get_traces(self, date: Optional[str] = None, limit: int = 100) -> list:
        """Get traces for a date"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        trace_file = self.storage_dir / f"traces_{date}.jsonl"
        if not trace_file.exists():
            return []
        
        traces = []
        with open(trace_file, 'r') as f:
            for line in f:
                if line.strip():
                    traces.append(json.loads(line))
        
        return traces[-limit:]


# Global storage
_trace_storage: Optional[TraceStorage] = None

def get_trace_storage() -> TraceStorage:
    global _trace_storage
    if _trace_storage is None:
        _trace_storage = TraceStorage()
    return _trace_storage


class LLMTracer:
    """Tracer for LLM operations"""
    
    def __init__(self):
        self.storage = get_trace_storage()
        self._current_trace_id = None
    
    def trace_llm_call(
        self,
        provider: str,
        model: str,
        prompt: str,
        response: str,
        duration_ms: float,
        tokens_in: int = 0,
        tokens_out: int = 0,
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Record an LLM call trace"""
        trace = {
            "timestamp": datetime.now().isoformat(),
            "type": "llm_call",
            "provider": provider,
            "model": model,
            "prompt_preview": prompt[:500] if prompt else "",
            "prompt_length": len(prompt) if prompt else 0,
            "response_preview": response[:500] if response else "",
            "response_length": len(response) if response else 0,
            "duration_ms": duration_ms,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "tokens_total": tokens_in + tokens_out,
            "success": success,
            "error": error,
            "metadata": metadata or {}
        }
        
        self.storage.save_trace(trace)
        return trace
    
    def trace_tool_call(
        self,
        tool_name: str,
        arguments: Dict,
        result: Any,
        duration_ms: float,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Record a tool call trace"""
        trace = {
            "timestamp": datetime.now().isoformat(),
            "type": "tool_call",
            "tool_name": tool_name,
            "arguments": self._sanitize_args(arguments),
            "result_preview": str(result)[:500] if result else "",
            "duration_ms": duration_ms,
            "success": success,
            "error": error
        }
        
        self.storage.save_trace(trace)
        return trace
    
    def trace_agent_step(
        self,
        agent_type: str,
        action: str,
        input_data: str,
        output_data: str,
        duration_ms: float,
        quality_score: Optional[float] = None
    ):
        """Record an agent step trace"""
        trace = {
            "timestamp": datetime.now().isoformat(),
            "type": "agent_step",
            "agent_type": agent_type,
            "action": action,
            "input_preview": input_data[:300] if input_data else "",
            "output_preview": output_data[:300] if output_data else "",
            "duration_ms": duration_ms,
            "quality_score": quality_score
        }
        
        self.storage.save_trace(trace)
        return trace
    
    def _sanitize_args(self, args: Dict) -> Dict:
        """Remove sensitive data from arguments"""
        sanitized = {}
        sensitive_keys = {'password', 'token', 'key', 'secret', 'content'}
        
        for k, v in args.items():
            if any(s in k.lower() for s in sensitive_keys):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, str) and len(v) > 200:
                sanitized[k] = v[:200] + "..."
            else:
                sanitized[k] = v
        
        return sanitized


# Global tracer
_tracer: Optional[LLMTracer] = None

def get_tracer() -> LLMTracer:
    global _tracer
    if _tracer is None:
        _tracer = LLMTracer()
    return _tracer


# Decorator for tracing functions
def trace_llm(provider: str, model: str):
    """Decorator to trace LLM calls"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            start = time.time()
            error = None
            result = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                error = str(e)
                raise
            finally:
                duration_ms = (time.time() - start) * 1000
                prompt = kwargs.get('prompt', args[0] if args else '')
                response = result if isinstance(result, str) else str(result)[:500]
                
                tracer.trace_llm_call(
                    provider=provider,
                    model=model,
                    prompt=str(prompt)[:500],
                    response=response,
                    duration_ms=duration_ms,
                    success=error is None,
                    error=error
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            start = time.time()
            error = None
            result = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = str(e)
                raise
            finally:
                duration_ms = (time.time() - start) * 1000
                prompt = kwargs.get('prompt', args[0] if args else '')
                response = result if isinstance(result, str) else str(result)[:500]
                
                tracer.trace_llm_call(
                    provider=provider,
                    model=model,
                    prompt=str(prompt)[:500],
                    response=response,
                    duration_ms=duration_ms,
                    success=error is None,
                    error=error
                )
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def trace_tool(func: Callable):
    """Decorator to trace tool calls"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        tracer = get_tracer()
        start = time.time()
        error = None
        result = None
        
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            error = str(e)
            raise
        finally:
            duration_ms = (time.time() - start) * 1000
            tool_name = func.__name__
            
            tracer.trace_tool_call(
                tool_name=tool_name,
                arguments=kwargs or {},
                result=result,
                duration_ms=duration_ms,
                success=error is None,
                error=error
            )
    
    return wrapper
```

### 3.3 Metrics Aggregator (src/analytics/metrics.py)

```python
"""Metrics aggregation for VETKA analytics"""
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path
from collections import defaultdict

class MetricsAggregator:
    """Aggregate and analyze traces"""
    
    def __init__(self, traces_dir: str = "data/traces", audit_dir: str = "data/mcp_audit"):
        self.traces_dir = Path(traces_dir)
        self.audit_dir = Path(audit_dir)
    
    def get_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get summary metrics for the last N days"""
        traces = self._load_traces(days)
        audit = self._load_audit(days)
        
        return {
            "period_days": days,
            "generated_at": datetime.now().isoformat(),
            "llm_calls": self._summarize_llm_calls(traces),
            "tool_calls": self._summarize_tool_calls(traces, audit),
            "agent_performance": self._summarize_agents(traces),
            "errors": self._summarize_errors(traces, audit),
            "daily_breakdown": self._daily_breakdown(traces, audit)
        }
    
    def _load_traces(self, days: int) -> List[Dict]:
        """Load traces for the last N days"""
        traces = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            trace_file = self.traces_dir / f"traces_{date}.jsonl"
            
            if trace_file.exists():
                with open(trace_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            traces.append(json.loads(line))
        
        return traces
    
    def _load_audit(self, days: int) -> List[Dict]:
        """Load audit logs for the last N days"""
        entries = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            audit_file = self.audit_dir / f"mcp_audit_{date}.jsonl"
            
            if audit_file.exists():
                with open(audit_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            entries.append(json.loads(line))
        
        return entries
    
    def _summarize_llm_calls(self, traces: List[Dict]) -> Dict:
        """Summarize LLM call metrics"""
        llm_traces = [t for t in traces if t.get("type") == "llm_call"]
        
        if not llm_traces:
            return {"total": 0}
        
        by_provider = defaultdict(lambda: {"count": 0, "total_ms": 0, "total_tokens": 0, "errors": 0})
        by_model = defaultdict(lambda: {"count": 0, "total_ms": 0, "total_tokens": 0})
        
        for trace in llm_traces:
            provider = trace.get("provider", "unknown")
            model = trace.get("model", "unknown")
            
            by_provider[provider]["count"] += 1
            by_provider[provider]["total_ms"] += trace.get("duration_ms", 0)
            by_provider[provider]["total_tokens"] += trace.get("tokens_total", 0)
            if not trace.get("success", True):
                by_provider[provider]["errors"] += 1
            
            by_model[model]["count"] += 1
            by_model[model]["total_ms"] += trace.get("duration_ms", 0)
            by_model[model]["total_tokens"] += trace.get("tokens_total", 0)
        
        # Calculate averages
        for stats in by_provider.values():
            if stats["count"] > 0:
                stats["avg_ms"] = stats["total_ms"] / stats["count"]
                stats["avg_tokens"] = stats["total_tokens"] / stats["count"]
        
        for stats in by_model.values():
            if stats["count"] > 0:
                stats["avg_ms"] = stats["total_ms"] / stats["count"]
        
        total_duration = sum(t.get("duration_ms", 0) for t in llm_traces)
        total_tokens = sum(t.get("tokens_total", 0) for t in llm_traces)
        
        return {
            "total": len(llm_traces),
            "total_duration_ms": total_duration,
            "total_tokens": total_tokens,
            "avg_duration_ms": total_duration / len(llm_traces) if llm_traces else 0,
            "by_provider": dict(by_provider),
            "by_model": dict(by_model),
            "success_rate": sum(1 for t in llm_traces if t.get("success", True)) / len(llm_traces)
        }
    
    def _summarize_tool_calls(self, traces: List[Dict], audit: List[Dict]) -> Dict:
        """Summarize tool call metrics"""
        tool_traces = [t for t in traces if t.get("type") == "tool_call"]
        
        # Combine with audit data
        by_tool = defaultdict(lambda: {"count": 0, "total_ms": 0, "errors": 0})
        
        for trace in tool_traces:
            tool = trace.get("tool_name", "unknown")
            by_tool[tool]["count"] += 1
            by_tool[tool]["total_ms"] += trace.get("duration_ms", 0)
            if not trace.get("success", True):
                by_tool[tool]["errors"] += 1
        
        for entry in audit:
            tool = entry.get("tool", "unknown")
            if tool not in by_tool:
                by_tool[tool] = {"count": 0, "total_ms": 0, "errors": 0}
            by_tool[tool]["count"] += 1
            by_tool[tool]["total_ms"] += entry.get("duration_ms", 0)
            if not entry.get("success", True):
                by_tool[tool]["errors"] += 1
        
        # Calculate averages
        for stats in by_tool.values():
            if stats["count"] > 0:
                stats["avg_ms"] = stats["total_ms"] / stats["count"]
                stats["error_rate"] = stats["errors"] / stats["count"]
        
        return {
            "total": sum(s["count"] for s in by_tool.values()),
            "by_tool": dict(by_tool),
            "most_used": sorted(by_tool.items(), key=lambda x: x[1]["count"], reverse=True)[:5]
        }
    
    def _summarize_agents(self, traces: List[Dict]) -> Dict:
        """Summarize agent performance"""
        agent_traces = [t for t in traces if t.get("type") == "agent_step"]
        
        by_agent = defaultdict(lambda: {
            "steps": 0,
            "total_ms": 0,
            "quality_scores": []
        })
        
        for trace in agent_traces:
            agent = trace.get("agent_type", "unknown")
            by_agent[agent]["steps"] += 1
            by_agent[agent]["total_ms"] += trace.get("duration_ms", 0)
            if trace.get("quality_score") is not None:
                by_agent[agent]["quality_scores"].append(trace["quality_score"])
        
        # Calculate averages
        for stats in by_agent.values():
            if stats["steps"] > 0:
                stats["avg_ms"] = stats["total_ms"] / stats["steps"]
            if stats["quality_scores"]:
                stats["avg_quality"] = sum(stats["quality_scores"]) / len(stats["quality_scores"])
            del stats["quality_scores"]  # Don't return raw list
        
        return {
            "total_steps": sum(s["steps"] for s in by_agent.values()),
            "by_agent": dict(by_agent)
        }
    
    def _summarize_errors(self, traces: List[Dict], audit: List[Dict]) -> Dict:
        """Summarize errors"""
        errors = []
        
        for trace in traces:
            if not trace.get("success", True) and trace.get("error"):
                errors.append({
                    "timestamp": trace.get("timestamp"),
                    "type": trace.get("type"),
                    "error": trace.get("error")[:200]
                })
        
        for entry in audit:
            if not entry.get("success", True) and entry.get("error"):
                errors.append({
                    "timestamp": entry.get("timestamp"),
                    "type": "mcp_tool",
                    "tool": entry.get("tool"),
                    "error": entry.get("error")[:200]
                })
        
        # Sort by timestamp, most recent first
        errors.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return {
            "total": len(errors),
            "recent": errors[:10]
        }
    
    def _daily_breakdown(self, traces: List[Dict], audit: List[Dict]) -> Dict:
        """Get daily breakdown of activity"""
        by_date = defaultdict(lambda: {
            "llm_calls": 0,
            "tool_calls": 0,
            "agent_steps": 0,
            "errors": 0
        })
        
        for trace in traces:
            date = trace.get("timestamp", "")[:10]
            trace_type = trace.get("type", "")
            
            if trace_type == "llm_call":
                by_date[date]["llm_calls"] += 1
            elif trace_type == "tool_call":
                by_date[date]["tool_calls"] += 1
            elif trace_type == "agent_step":
                by_date[date]["agent_steps"] += 1
            
            if not trace.get("success", True):
                by_date[date]["errors"] += 1
        
        for entry in audit:
            date = entry.get("timestamp", "")[:10]
            by_date[date]["tool_calls"] += 1
            if not entry.get("success", True):
                by_date[date]["errors"] += 1
        
        return dict(sorted(by_date.items(), reverse=True))


# Singleton
_aggregator: Optional[MetricsAggregator] = None

def get_metrics_aggregator() -> MetricsAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = MetricsAggregator()
    return _aggregator
```

### 3.4 Self-Improvement Engine (src/analytics/self_improve.py)

```python
"""Self-improvement engine for VETKA agents"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

class SelfImprovementEngine:
    """Analyze performance and suggest improvements"""
    
    def __init__(self, data_dir: str = "data/analytics"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.feedback_file = self.data_dir / "feedback.jsonl"
        self.improvements_file = self.data_dir / "improvements.json"
    
    def record_feedback(
        self,
        trace_id: str,
        feedback_type: str,  # "positive", "negative", "correction"
        feedback_text: str,
        corrected_output: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Record user feedback on an output"""
        feedback = {
            "timestamp": datetime.now().isoformat(),
            "trace_id": trace_id,
            "feedback_type": feedback_type,
            "feedback_text": feedback_text,
            "corrected_output": corrected_output,
            "metadata": metadata or {}
        }
        
        with open(self.feedback_file, 'a') as f:
            f.write(json.dumps(feedback) + '\n')
        
        return feedback
    
    def get_feedback_summary(self) -> Dict[str, Any]:
        """Get summary of all feedback"""
        if not self.feedback_file.exists():
            return {"total": 0, "positive": 0, "negative": 0, "corrections": 0}
        
        feedback_list = []
        with open(self.feedback_file, 'r') as f:
            for line in f:
                if line.strip():
                    feedback_list.append(json.loads(line))
        
        positive = sum(1 for f in feedback_list if f.get("feedback_type") == "positive")
        negative = sum(1 for f in feedback_list if f.get("feedback_type") == "negative")
        corrections = sum(1 for f in feedback_list if f.get("feedback_type") == "correction")
        
        return {
            "total": len(feedback_list),
            "positive": positive,
            "negative": negative,
            "corrections": corrections,
            "positive_rate": positive / len(feedback_list) if feedback_list else 0,
            "recent": feedback_list[-10:]
        }
    
    def analyze_and_suggest(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze metrics and suggest improvements"""
        suggestions = []
        
        # Check LLM performance
        llm_metrics = metrics.get("llm_calls", {})
        if llm_metrics.get("success_rate", 1) < 0.95:
            suggestions.append({
                "type": "llm_reliability",
                "severity": "high",
                "message": f"LLM success rate is {llm_metrics.get('success_rate', 0):.1%}. Consider adding retry logic or fallback providers.",
                "action": "review_llm_errors"
            })
        
        avg_duration = llm_metrics.get("avg_duration_ms", 0)
        if avg_duration > 5000:
            suggestions.append({
                "type": "llm_performance",
                "severity": "medium",
                "message": f"Average LLM response time is {avg_duration:.0f}ms. Consider using smaller models for simple tasks.",
                "action": "optimize_model_selection"
            })
        
        # Check tool usage
        tool_metrics = metrics.get("tool_calls", {})
        for tool_name, stats in tool_metrics.get("by_tool", {}).items():
            error_rate = stats.get("error_rate", 0)
            if error_rate > 0.1:
                suggestions.append({
                    "type": "tool_reliability",
                    "severity": "medium",
                    "message": f"Tool '{tool_name}' has {error_rate:.1%} error rate. Review error logs.",
                    "action": f"review_tool_{tool_name}"
                })
        
        # Check agent performance
        agent_metrics = metrics.get("agent_performance", {})
        for agent_type, stats in agent_metrics.get("by_agent", {}).items():
            avg_quality = stats.get("avg_quality")
            if avg_quality is not None and avg_quality < 0.7:
                suggestions.append({
                    "type": "agent_quality",
                    "severity": "high",
                    "message": f"Agent '{agent_type}' average quality is {avg_quality:.2f}. Consider prompt improvements.",
                    "action": f"improve_agent_{agent_type}"
                })
        
        # Check error trends
        errors = metrics.get("errors", {})
        if errors.get("total", 0) > 10:
            suggestions.append({
                "type": "error_volume",
                "severity": "medium",
                "message": f"{errors.get('total')} errors in the period. Review common error patterns.",
                "action": "review_error_patterns"
            })
        
        # Get feedback insights
        feedback_summary = self.get_feedback_summary()
        if feedback_summary.get("negative", 0) > feedback_summary.get("positive", 0):
            suggestions.append({
                "type": "user_satisfaction",
                "severity": "high",
                "message": "More negative feedback than positive. Review recent negative feedback for patterns.",
                "action": "review_negative_feedback"
            })
        
        # Save suggestions
        self._save_suggestions(suggestions)
        
        return suggestions
    
    def _save_suggestions(self, suggestions: List[Dict]):
        """Save current suggestions"""
        data = {
            "generated_at": datetime.now().isoformat(),
            "suggestions": suggestions
        }
        
        with open(self.improvements_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_improvement_plan(self) -> Dict[str, Any]:
        """Get the current improvement plan"""
        if not self.improvements_file.exists():
            return {"suggestions": []}
        
        with open(self.improvements_file, 'r') as f:
            return json.load(f)


# Singleton
_engine: Optional[SelfImprovementEngine] = None

def get_improvement_engine() -> SelfImprovementEngine:
    global _engine
    if _engine is None:
        _engine = SelfImprovementEngine()
    return _engine
```

## 📋 ШАГ 4: REST ENDPOINTS

Добавить в main.py:

```python
# Analytics endpoints
@app.route('/api/analytics/summary', methods=['GET'])
def analytics_summary():
    """Get analytics summary"""
    from src.analytics.metrics import get_metrics_aggregator
    
    days = int(request.args.get('days', 7))
    aggregator = get_metrics_aggregator()
    
    return jsonify(aggregator.get_summary(days))


@app.route('/api/analytics/traces', methods=['GET'])
def analytics_traces():
    """Get recent traces"""
    from src.analytics.tracer import get_trace_storage
    
    date = request.args.get('date')
    limit = int(request.args.get('limit', 100))
    
    storage = get_trace_storage()
    traces = storage.get_traces(date, limit)
    
    return jsonify({
        "count": len(traces),
        "traces": traces
    })


@app.route('/api/analytics/feedback', methods=['POST'])
def analytics_feedback():
    """Record feedback on an output"""
    from src.analytics.self_improve import get_improvement_engine
    
    data = request.json or {}
    
    if not data.get('trace_id') or not data.get('feedback_type'):
        return jsonify({"error": "trace_id and feedback_type required"}), 400
    
    engine = get_improvement_engine()
    feedback = engine.record_feedback(
        trace_id=data['trace_id'],
        feedback_type=data['feedback_type'],
        feedback_text=data.get('feedback_text', ''),
        corrected_output=data.get('corrected_output'),
        metadata=data.get('metadata')
    )
    
    return jsonify({"success": True, "feedback": feedback})


@app.route('/api/analytics/feedback/summary', methods=['GET'])
def analytics_feedback_summary():
    """Get feedback summary"""
    from src.analytics.self_improve import get_improvement_engine
    
    engine = get_improvement_engine()
    return jsonify(engine.get_feedback_summary())


@app.route('/api/analytics/suggestions', methods=['GET'])
def analytics_suggestions():
    """Get improvement suggestions"""
    from src.analytics.metrics import get_metrics_aggregator
    from src.analytics.self_improve import get_improvement_engine
    
    days = int(request.args.get('days', 7))
    
    aggregator = get_metrics_aggregator()
    metrics = aggregator.get_summary(days)
    
    engine = get_improvement_engine()
    suggestions = engine.analyze_and_suggest(metrics)
    
    return jsonify({
        "period_days": days,
        "suggestions_count": len(suggestions),
        "suggestions": suggestions
    })


@app.route('/api/analytics/phoenix/status', methods=['GET'])
def phoenix_status():
    """Get Phoenix server status"""
    from src.analytics.phoenix_server import get_phoenix_server
    
    server = get_phoenix_server()
    
    return jsonify({
        "running": server.is_running(),
        "url": server.get_url() if server.is_running() else None
    })


@app.route('/api/analytics/phoenix/start', methods=['POST'])
def phoenix_start():
    """Start Phoenix server"""
    from src.analytics.phoenix_server import get_phoenix_server
    
    server = get_phoenix_server()
    success = server.start()
    
    return jsonify({
        "success": success,
        "url": server.get_url() if success else None
    })
```

## 📋 ШАГ 5: ТЕСТЫ

Добавить в tests/test_mcp_server.py:

```python
# ============================================================
# PHASE 22-MCP-6 TESTS
# ============================================================

def test_39_trace_storage():
    """Test trace storage"""
    from src.analytics.tracer import TraceStorage
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = TraceStorage(storage_dir=tmpdir)
        
        # Save trace
        storage.save_trace({
            "type": "test",
            "timestamp": "2025-01-01T00:00:00",
            "data": "test_data"
        })
        
        # Get traces
        traces = storage.get_traces(limit=10)
        assert len(traces) >= 1
        assert traces[-1]["type"] == "test"
    
    print("✅ Test 39: Trace storage works")

def test_40_llm_tracer():
    """Test LLM tracer"""
    from src.analytics.tracer import LLMTracer
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        from src.analytics import tracer
        old_storage = tracer._trace_storage
        tracer._trace_storage = tracer.TraceStorage(storage_dir=tmpdir)
        
        try:
            t = LLMTracer()
            t.trace_llm_call(
                provider="test",
                model="test-model",
                prompt="Hello",
                response="World",
                duration_ms=100,
                success=True
            )
            
            traces = t.storage.get_traces()
            assert len(traces) >= 1
            assert traces[-1]["provider"] == "test"
        finally:
            tracer._trace_storage = old_storage
    
    print("✅ Test 40: LLM tracer works")

def test_41_metrics_aggregator():
    """Test metrics aggregator"""
    from src.analytics.metrics import MetricsAggregator
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        aggregator = MetricsAggregator(
            traces_dir=tmpdir,
            audit_dir=tmpdir
        )
        
        summary = aggregator.get_summary(days=1)
        
        assert "llm_calls" in summary
        assert "tool_calls" in summary
        assert "agent_performance" in summary
        assert "errors" in summary
    
    print("✅ Test 41: Metrics aggregator works")

def test_42_self_improvement():
    """Test self-improvement engine"""
    from src.analytics.self_improve import SelfImprovementEngine
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = SelfImprovementEngine(data_dir=tmpdir)
        
        # Record feedback
        engine.record_feedback(
            trace_id="test123",
            feedback_type="positive",
            feedback_text="Great response!"
        )
        
        summary = engine.get_feedback_summary()
        assert summary["total"] >= 1
        assert summary["positive"] >= 1
    
    print("✅ Test 42: Self-improvement engine works")

def test_43_analytics_summary_endpoint():
    """Test analytics summary endpoint"""
    response = requests.get(f"{BASE_URL}/api/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "llm_calls" in data
    assert "tool_calls" in data
    print("✅ Test 43: Analytics summary endpoint works")

def test_44_analytics_traces_endpoint():
    """Test analytics traces endpoint"""
    response = requests.get(f"{BASE_URL}/api/analytics/traces?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "traces" in data
    print("✅ Test 44: Analytics traces endpoint works")

def test_45_feedback_endpoint():
    """Test feedback endpoint"""
    response = requests.post(
        f"{BASE_URL}/api/analytics/feedback",
        json={
            "trace_id": "test123",
            "feedback_type": "positive",
            "feedback_text": "Test feedback"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") == True
    print("✅ Test 45: Feedback endpoint works")

def test_46_suggestions_endpoint():
    """Test suggestions endpoint"""
    response = requests.get(f"{BASE_URL}/api/analytics/suggestions")
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    print("✅ Test 46: Suggestions endpoint works")
```

## 📋 ШАГ 6: Структура модуля

```python
# src/analytics/__init__.py
from .phoenix_server import PhoenixServer, get_phoenix_server, start_phoenix
from .tracer import (
    LLMTracer, TraceStorage,
    get_tracer, get_trace_storage,
    trace_llm, trace_tool
)
from .metrics import MetricsAggregator, get_metrics_aggregator
from .self_improve import SelfImprovementEngine, get_improvement_engine

__all__ = [
    'PhoenixServer', 'get_phoenix_server', 'start_phoenix',
    'LLMTracer', 'TraceStorage', 'get_tracer', 'get_trace_storage',
    'trace_llm', 'trace_tool',
    'MetricsAggregator', 'get_metrics_aggregator',
    'SelfImprovementEngine', 'get_improvement_engine'
]
```

## ✅ КРИТЕРИИ УСПЕХА

- [ ] Phoenix server запускается (port 6006)
- [ ] Tracer записывает LLM вызовы
- [ ] Tracer записывает tool вызовы
- [ ] MetricsAggregator агрегирует данные
- [ ] SelfImprovementEngine предлагает улучшения
- [ ] REST endpoints: /api/analytics/*
- [ ] 8 новых тестов (39-46)

## 📁 НОВЫЕ ФАЙЛЫ

```
src/analytics/          (NEW DIRECTORY)
├── __init__.py
├── phoenix_server.py   (Phoenix management)
├── tracer.py           (LLM/tool tracing)
├── metrics.py          (metrics aggregation)
└── self_improve.py     (improvement suggestions)

data/
├── traces/             (NEW)
│   └── traces_YYYY-MM-DD.jsonl
├── analytics/          (NEW)
│   ├── feedback.jsonl
│   └── improvements.json
└── phoenix/            (NEW)
    └── (Phoenix data)
```

## 🔗 ИНТЕГРАЦИЯ С СУЩЕСТВУЮЩИМ КОДОМ

### Добавить трейсинг в orchestrator (src/orchestration/orchestrator_with_elisya.py):

```python
# В начале файла:
from src.analytics.tracer import get_tracer

# В методе _call_llm (примерно):
async def _call_llm(self, prompt, model, ...):
    tracer = get_tracer()
    start = time.time()
    
    try:
        response = await self._actual_llm_call(prompt, model, ...)
        
        tracer.trace_llm_call(
            provider=self._get_provider(model),
            model=model,
            prompt=prompt[:500],
            response=response[:500] if response else "",
            duration_ms=(time.time() - start) * 1000,
            success=True
        )
        
        return response
    except Exception as e:
        tracer.trace_llm_call(
            provider=self._get_provider(model),
            model=model,
            prompt=prompt[:500],
            response="",
            duration_ms=(time.time() - start) * 1000,
            success=False,
            error=str(e)
        )
        raise
```

## 🔄 ПОСЛЕ ЗАВЕРШЕНИЯ

1. Установи зависимости:
   ```bash
   pip install arize-phoenix opentelemetry-api opentelemetry-sdk
   ```

2. Запусти тесты: `python tests/test_mcp_server.py`

3. Запусти Phoenix:
   ```bash
   curl -X POST http://localhost:5001/api/analytics/phoenix/start
   ```

4. Проверь метрики:
   ```bash
   curl http://localhost:5001/api/analytics/summary
   curl http://localhost:5001/api/analytics/suggestions
   ```

5. Открой Phoenix UI: http://localhost:6006

6. Сообщи результаты!
