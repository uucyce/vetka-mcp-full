# HOSTESS BACKGROUND TASKS - IMPLEMENTATION GUIDE
## Quick Start for Scenarios 1-7

**Phase**: 80.50+ Implementation Ready
**Status**: Reference Implementation
**Author**: Architecture Team
**Date**: 2026-01-23

---

## QUICK SETUP (30 minutes)

### 1. Create Base Infrastructure

**File**: `/src/orchestration/hostess_background_tasks.py`

```python
"""
Hostess Background Task Manager
Handles non-blocking async execution of local Hostess tasks.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Callable, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class BackgroundTask:
    task_id: str
    name: str
    coroutine: asyncio.coroutine
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = None
    started_at: float = None
    completed_at: float = None
    result: Any = None
    error: str = None
    timeout: float = 3.0  # Default 3 seconds
    task_obj: Optional[asyncio.Task] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

    def duration_ms(self) -> float:
        """Get task duration in milliseconds."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at) * 1000
        return 0

    def to_dict(self) -> dict:
        return {
            'task_id': self.task_id,
            'name': self.name,
            'status': self.status.value,
            'duration_ms': self.duration_ms(),
            'error': self.error,
            'created_at': datetime.fromtimestamp(self.created_at).isoformat()
        }


class HostessBackgroundQueue:
    """
    Manages background tasks for Hostess without blocking main thread.

    Usage:
        queue = HostessBackgroundQueue()
        await queue.schedule_task('summary_123', summarize_coroutine())
        result = await queue.wait_for_task('summary_123', timeout=2.0)
    """

    def __init__(self, max_concurrent: int = 5):
        self.tasks: Dict[str, BackgroundTask] = {}
        self.max_concurrent = max_concurrent
        self.active_count = 0
        self.stats = {
            'total': 0,
            'completed': 0,
            'errors': 0,
            'timeouts': 0,
            'total_time_ms': 0
        }

    async def schedule_task(
        self,
        task_id: str,
        coroutine: asyncio.coroutine,
        timeout: float = 3.0,
        task_name: str = "background_task"
    ) -> str:
        """
        Schedule a background task.

        Args:
            task_id: Unique identifier for this task
            coroutine: Async function to execute
            timeout: Max time in seconds (default: 3.0)
            task_name: Human-readable name for logging

        Returns:
            task_id if scheduled successfully

        Raises:
            RuntimeError if too many concurrent tasks
        """
        if self.active_count >= self.max_concurrent:
            raise RuntimeError(f"Max concurrent tasks ({self.max_concurrent}) reached")

        if task_id in self.tasks and self.tasks[task_id].status == TaskStatus.RUNNING:
            raise RuntimeError(f"Task {task_id} already running")

        # Create background task
        task = BackgroundTask(
            task_id=task_id,
            name=task_name,
            coroutine=coroutine,
            timeout=timeout
        )

        # Wrap with timeout
        async def run_with_timeout():
            try:
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()
                self.active_count += 1

                result = await asyncio.wait_for(
                    task.coroutine,
                    timeout=timeout
                )

                task.result = result
                task.status = TaskStatus.COMPLETED
                self.stats['completed'] += 1

                logger.debug(
                    f"[Hostess] ✅ {task.name} completed "
                    f"({task.duration_ms():.0f}ms)"
                )

            except asyncio.TimeoutError:
                task.status = TaskStatus.TIMEOUT
                task.error = f"Timeout after {timeout}s"
                self.stats['timeouts'] += 1

                logger.warning(
                    f"[Hostess] ⏱️  {task.name} timeout "
                    f"({timeout}s)"
                )

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                self.stats['errors'] += 1

                logger.error(
                    f"[Hostess] ❌ {task.name} failed: {e}"
                )

            finally:
                task.completed_at = time.time()
                self.active_count -= 1
                self.stats['total_time_ms'] += task.duration_ms()

        # Schedule task
        task.task_obj = asyncio.create_task(run_with_timeout())
        self.tasks[task_id] = task
        self.stats['total'] += 1

        logger.debug(f"[Hostess] 📋 Scheduled: {task_name}")
        return task_id

    async def wait_for_task(
        self,
        task_id: str,
        timeout: Optional[float] = None
    ) -> Optional[Any]:
        """
        Wait for a task to complete.

        Args:
            task_id: ID of task to wait for
            timeout: Max time to wait (uses task's timeout if None)

        Returns:
            Task result if completed successfully
            None if timeout or error
        """
        if task_id not in self.tasks:
            logger.warning(f"[Hostess] Task {task_id} not found")
            return None

        task = self.tasks[task_id]

        if task.status == TaskStatus.COMPLETED:
            return task.result

        if task.status in [TaskStatus.FAILED, TaskStatus.TIMEOUT]:
            logger.warning(
                f"[Hostess] Task {task_id} failed: {task.error}"
            )
            return None

        # Wait for completion
        max_wait = timeout or task.timeout
        try:
            await asyncio.wait_for(task.task_obj, timeout=max_wait)
            return task.result if task.status == TaskStatus.COMPLETED else None
        except asyncio.TimeoutError:
            return None

    async def get_task_result(self, task_id: str) -> Dict:
        """Get task status and result (non-blocking)."""
        if task_id not in self.tasks:
            return {'error': 'Task not found'}

        task = self.tasks[task_id]
        result = task.to_dict()

        if task.status == TaskStatus.COMPLETED:
            result['result'] = task.result

        return result

    async def cleanup(self, age_seconds: float = 300):
        """Remove completed tasks older than age_seconds."""
        now = time.time()
        to_remove = []

        for task_id, task in self.tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                age = now - task.completed_at
                if age > age_seconds:
                    to_remove.append(task_id)

        for task_id in to_remove:
            del self.tasks[task_id]
            logger.debug(f"[Hostess] 🗑️  Cleaned up task {task_id}")

    def get_stats(self) -> Dict:
        """Get statistics."""
        avg_time = (
            self.stats['total_time_ms'] / self.stats['completed']
            if self.stats['completed'] > 0 else 0
        )

        return {
            **self.stats,
            'active_tasks': self.active_count,
            'pending_tasks': len([t for t in self.tasks.values()
                                   if t.status == TaskStatus.PENDING]),
            'avg_time_ms': avg_time,
            'error_rate': (
                self.stats['errors'] / self.stats['total']
                if self.stats['total'] > 0 else 0
            )
        }


# Global instance
_hostess_queue: Optional[HostessBackgroundQueue] = None


def get_hostess_queue() -> HostessBackgroundQueue:
    """Get or create global Hostess queue."""
    global _hostess_queue
    if _hostess_queue is None:
        _hostess_queue = HostessBackgroundQueue(max_concurrent=5)
    return _hostess_queue


async def schedule_hostess_task(
    task_id: str,
    coroutine: asyncio.coroutine,
    timeout: float = 3.0,
    task_name: str = "background_task"
) -> str:
    """Convenience function to schedule a task."""
    queue = get_hostess_queue()
    return await queue.schedule_task(task_id, coroutine, timeout, task_name)


async def wait_for_hostess_task(
    task_id: str,
    timeout: Optional[float] = None
) -> Optional[Any]:
    """Convenience function to wait for a task."""
    queue = get_hostess_queue()
    return await queue.wait_for_task(task_id, timeout)
```

### 2. Create Hostess Helper Functions

**File**: `/src/agents/hostess_utils.py`

```python
"""
Hostess utility functions for background tasks.
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class HostessModel:
    """Wrapper for local Hostess model calls."""

    def __init__(self, model_name: str = "qwen:0.5b", ollama_url: str = None):
        self.model = model_name
        self.ollama_url = ollama_url or "http://localhost:11434"
        self._check_available()

    def _check_available(self) -> bool:
        """Check if model is available in Ollama."""
        try:
            import httpx
            client = httpx.Client(timeout=2.0)
            response = client.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '').split(':')[0] for m in models]
                if any(self.model.startswith(m) for m in model_names):
                    logger.info(f"[Hostess] Model {self.model} available")
                    return True
        except Exception as e:
            logger.warning(f"[Hostess] Model check failed: {e}")
        return False

    async def call(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 500,
        timeout: float = 3.0
    ) -> Dict[str, Any]:
        """
        Call local Hostess model.

        Returns:
            {'text': response, 'tokens': count, 'error': None}
        """
        try:
            import httpx

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "stream": False
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        'text': data.get('response', '').strip(),
                        'tokens': data.get('eval_count', 0),
                        'error': None
                    }
                else:
                    return {
                        'text': '',
                        'tokens': 0,
                        'error': f"HTTP {response.status_code}"
                    }

        except asyncio.TimeoutError:
            return {
                'text': '',
                'tokens': 0,
                'error': f"Timeout after {timeout}s"
            }
        except Exception as e:
            logger.error(f"[Hostess] Model call failed: {e}")
            return {
                'text': '',
                'tokens': 0,
                'error': str(e)
            }


def extract_json_from_response(text: str) -> Optional[Dict]:
    """Extract JSON from LLM response."""
    try:
        # Try direct JSON parse
        return json.loads(text)
    except:
        pass

    # Try extracting JSON from markdown
    match = re.search(r'```(?:json)?\n?([\s\S]*?)\n?```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass

    # Try finding JSON object
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass

    return None


def extract_list_from_response(text: str, marker: str = None) -> List[str]:
    """Extract list items from LLM response."""
    if marker:
        # Find section with marker
        match = re.search(rf"{marker}:?\s*([\s\S]*?)(?:\n[A-Z]|$)", text)
        if match:
            text = match.group(1)

    # Extract list items
    items = re.findall(r"^[\s]*[-•*]\s+(.+?)$", text, re.MULTILINE)
    return [item.strip() for item in items]


def extract_key_value_from_response(text: str, key: str) -> Optional[str]:
    """Extract key-value from LLM response."""
    pattern = rf"{key}:?\s*(.+?)(?:\n|$)"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None


# Async versions for background tasks
async def call_hostess_model(
    prompt: str,
    model: str = "qwen:0.5b",
    temperature: float = 0.3,
    max_tokens: int = 500,
    timeout: float = 2.5
) -> Dict[str, Any]:
    """Async wrapper for Hostess model calls."""
    hostess = HostessModel(model_name=model)
    return await hostess.call(
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )


async def hostess_extract_keywords(text: str, count: int = 5) -> List[str]:
    """Use Hostess to extract keywords."""
    prompt = f"""Extract {count} important keywords from this text:

{text[:500]}

Format: KEYWORDS: keyword1, keyword2, keyword3...
"""

    result = await call_hostess_model(
        prompt=prompt,
        temperature=0.0,
        max_tokens=100
    )

    keywords = extract_list_from_response(result['text'], 'KEYWORDS')
    return keywords[:count]


async def hostess_classify_message(message: str) -> str:
    """Classify message type."""
    prompt = f"""Classify this message as one of: QUESTION, TASK, BUG_REPORT, FEATURE_REQUEST, FEEDBACK, OTHER

Message: "{message}"

Response format: CLASSIFICATION: [type]"""

    result = await call_hostess_model(
        prompt=prompt,
        temperature=0.0,
        max_tokens=50
    )

    classification = extract_key_value_from_response(result['text'], 'CLASSIFICATION')
    return classification or 'OTHER'


async def hostess_rate_message(message: str, criteria: str = "importance") -> float:
    """Rate message on a scale of 0-1."""
    prompt = f"""Rate this message on {criteria} (0.0-1.0):

Message: "{message}"

Response format: RATING: [0.0-1.0]"""

    result = await call_hostess_model(
        prompt=prompt,
        temperature=0.0,
        max_tokens=50
    )

    rating_str = extract_key_value_from_response(result['text'], 'RATING')
    try:
        return float(rating_str)
    except:
        return 0.5
```

### 3. Integrate into Main App

**File**: `main.py` (modify lifespan)

```python
# In the lifespan context manager, add:

async def lifespan(app: FastAPI):
    """Initialize components on startup."""

    # ... existing code ...

    # === PHASE 80.50: HOSTESS BACKGROUND QUEUE ===
    try:
        from src.orchestration.hostess_background_tasks import (
            get_hostess_queue,
            HostessBackgroundQueue
        )

        queue = get_hostess_queue()
        app.state.hostess_queue = queue

        # Start periodic cleanup task
        async def periodic_hostess_cleanup():
            """Clean up old completed tasks every 5 minutes."""
            while True:
                try:
                    await asyncio.sleep(300)  # 5 minutes
                    await queue.cleanup(age_seconds=600)  # Remove after 10 min
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"[Hostess] Cleanup failed: {e}")

        hostess_cleanup_task = asyncio.create_task(periodic_hostess_cleanup())
        app.state.hostess_cleanup_task = hostess_cleanup_task

        logger.info("[Startup] Hostess background queue initialized")

    except Exception as e:
        logger.error(f"[Startup] Hostess queue init failed: {e}")
        app.state.hostess_queue = None

    yield  # App running

    # Cleanup
    if hasattr(app.state, 'hostess_cleanup_task'):
        app.state.hostess_cleanup_task.cancel()
```

### 4. Add Monitoring Endpoint

**File**: `/src/api/routes/hostess_routes.py` (new file)

```python
"""
Hostess monitoring routes.
"""

from fastapi import APIRouter, Request
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/hostess", tags=["hostess"])


@router.get("/stats")
async def get_hostess_stats(request: Request):
    """Get Hostess background task statistics."""
    queue = getattr(request.app.state, 'hostess_queue', None)

    if not queue:
        return {"error": "Hostess queue not initialized"}

    return {
        "stats": queue.get_stats(),
        "queue_size": len(queue.tasks),
        "active_tasks": queue.active_count
    }


@router.get("/task/{task_id}")
async def get_task_status(request: Request, task_id: str):
    """Get specific task status."""
    queue = getattr(request.app.state, 'hostess_queue', None)

    if not queue:
        return {"error": "Hostess queue not initialized"}

    return await queue.get_task_result(task_id)
```

Then in `main.py`:

```python
# Add to routes registration section:
from src.api.routes.hostess_routes import router as hostess_router
app.include_router(hostess_router)
```

---

## TESTING SCENARIOS

### Test 1: Basic Task Scheduling

**File**: `tests/test_hostess_background.py`

```python
import pytest
import asyncio
from src.orchestration.hostess_background_tasks import (
    HostessBackgroundQueue,
    TaskStatus
)


@pytest.mark.asyncio
async def test_schedule_and_complete_task():
    """Test basic task scheduling and completion."""
    queue = HostessBackgroundQueue()

    async def simple_task():
        await asyncio.sleep(0.1)
        return "success"

    # Schedule task
    task_id = await queue.schedule_task(
        "test_1",
        simple_task(),
        timeout=1.0,
        task_name="test_simple"
    )

    assert task_id == "test_1"

    # Wait for result
    result = await queue.wait_for_task(task_id, timeout=2.0)
    assert result == "success"

    # Check stats
    stats = queue.get_stats()
    assert stats['completed'] == 1
    assert stats['errors'] == 0


@pytest.mark.asyncio
async def test_task_timeout():
    """Test task timeout handling."""
    queue = HostessBackgroundQueue()

    async def slow_task():
        await asyncio.sleep(10)  # Longer than timeout
        return "completed"

    # Schedule with short timeout
    await queue.schedule_task(
        "test_timeout",
        slow_task(),
        timeout=0.1,
        task_name="test_slow"
    )

    result = await queue.wait_for_task("test_timeout", timeout=0.5)
    assert result is None

    # Check stats
    stats = queue.get_stats()
    assert stats['timeouts'] == 1


@pytest.mark.asyncio
async def test_multiple_concurrent_tasks():
    """Test concurrent task execution."""
    queue = HostessBackgroundQueue(max_concurrent=3)

    async def dummy_task(n):
        await asyncio.sleep(0.1)
        return f"task_{n}"

    # Schedule 3 concurrent tasks
    tasks = []
    for i in range(3):
        task_id = await queue.schedule_task(
            f"test_{i}",
            dummy_task(i),
            timeout=1.0
        )
        tasks.append(task_id)

    # Verify all completed
    results = []
    for task_id in tasks:
        result = await queue.wait_for_task(task_id)
        results.append(result)

    assert len(results) == 3
    assert all(r is not None for r in results)


@pytest.mark.asyncio
async def test_max_concurrent_limit():
    """Test max concurrent task limit."""
    queue = HostessBackgroundQueue(max_concurrent=1)

    async def dummy_task():
        await asyncio.sleep(0.2)

    # Schedule first task
    await queue.schedule_task(
        "test_1",
        dummy_task(),
        timeout=1.0
    )

    # Try to schedule second - should fail
    with pytest.raises(RuntimeError):
        await queue.schedule_task(
            "test_2",
            dummy_task(),
            timeout=1.0
        )
```

### Run Tests

```bash
pytest tests/test_hostess_background.py -v

# With coverage
pytest tests/test_hostess_background.py -v --cov=src/orchestration/hostess_background_tasks
```

---

## SCENARIO-SPECIFIC HELPERS

### Scenario 1: Chat Summarization Helper

**File**: `/src/orchestration/hostess_scenarios.py` (new file)

```python
"""Hostess background task scenarios."""

import asyncio
import logging
from typing import List, Dict
from src.agents.hostess_utils import (
    call_hostess_model,
    extract_list_from_response,
    extract_key_value_from_response
)

logger = logging.getLogger(__name__)


async def hostess_summarize_chat(messages: List[Dict]) -> Dict:
    """
    Scenario 1: Summarize chat messages.

    Args:
        messages: List of {sender, content, timestamp}

    Returns:
        {summary: str, keywords: List[str]}
    """
    if not messages:
        return {'summary': '', 'keywords': []}

    # Format messages
    chat_text = "\n".join([
        f"{msg.get('sender', 'unknown')}: {msg.get('content', '')[:80]}"
        for msg in messages[:50]  # Limit to 50 for speed
    ])

    prompt = f"""Summarize this chat in 2-3 sentences and extract 5 keywords:

{chat_text}

Format:
SUMMARY: [text]
KEYWORDS: keyword1, keyword2, keyword3, keyword4, keyword5"""

    result = await call_hostess_model(
        prompt=prompt,
        temperature=0.3,
        max_tokens=200,
        timeout=2.0
    )

    if result.get('error'):
        logger.error(f"[Hostess] Summary failed: {result['error']}")
        return {'summary': '', 'keywords': []}

    summary = extract_key_value_from_response(result['text'], 'SUMMARY')
    keywords_str = extract_key_value_from_response(result['text'], 'KEYWORDS')

    keywords = []
    if keywords_str:
        keywords = [k.strip() for k in keywords_str.split(',')][:5]

    return {
        'summary': summary or '',
        'keywords': keywords,
        'tokens_used': result.get('tokens', 0)
    }


async def hostess_route_message(message: str) -> Dict:
    """
    Scenario 4: Route message to appropriate agent.

    Returns:
        {agent: str, confidence: float, reason: str}
    """
    prompt = f"""Analyze this message and decide which agent should respond:

"{message}"

Options:
- PM: Planning, architecture, requirements
- Dev: Coding, implementation, debugging
- QA: Testing, quality, verification
- Hostess: Simple questions, meta-questions

Response format:
AGENT: [name]
CONFIDENCE: [0.0-1.0]
REASON: [one sentence]"""

    result = await call_hostess_model(
        prompt=prompt,
        temperature=0.0,  # Deterministic
        max_tokens=100,
        timeout=1.5
    )

    if result.get('error'):
        return {'agent': 'PM', 'confidence': 0.5, 'reason': 'Default'}

    agent = extract_key_value_from_response(result['text'], 'AGENT')
    confidence_str = extract_key_value_from_response(result['text'], 'CONFIDENCE')
    reason = extract_key_value_from_response(result['text'], 'REASON')

    try:
        confidence = float(confidence_str) if confidence_str else 0.5
    except:
        confidence = 0.5

    return {
        'agent': agent or 'PM',
        'confidence': min(1.0, confidence),
        'reason': reason or 'Analysis complete'
    }


async def hostess_quick_code_review(code: str, language: str = 'python') -> Dict:
    """
    Scenario 7: Quick code review for obvious issues.

    Returns:
        {issues: List[str], suggestions: List[str], critical: bool}
    """
    # Limit code to first 1000 chars for speed
    code_preview = code[:1000] + ("..." if len(code) > 1000 else "")

    prompt = f"""Quick code quality check for obvious issues:

LANGUAGE: {language}
CODE:
{code_preview}

Check for:
- Syntax errors
- Missing error handling
- Dead code
- Typos

Format:
ISSUES:
- [issue]

SUGGESTIONS:
- [suggestion]"""

    result = await call_hostess_model(
        prompt=prompt,
        temperature=0.1,
        max_tokens=200,
        timeout=2.0
    )

    if result.get('error'):
        return {'issues': [], 'suggestions': [], 'critical': False}

    issues = extract_list_from_response(result['text'], 'ISSUES')
    suggestions = extract_list_from_response(result['text'], 'SUGGESTIONS')

    return {
        'issues': issues,
        'suggestions': suggestions,
        'critical': len(issues) > 0,
        'tokens_used': result.get('tokens', 0)
    }
```

---

## DEPLOYMENT CHECKLIST

- [ ] Create `/src/orchestration/hostess_background_tasks.py`
- [ ] Create `/src/agents/hostess_utils.py`
- [ ] Create `/src/orchestration/hostess_scenarios.py`
- [ ] Create `/src/api/routes/hostess_routes.py`
- [ ] Update `main.py` with queue initialization
- [ ] Create tests in `/tests/test_hostess_background.py`
- [ ] Test each scenario with real data
- [ ] Monitor token usage with `/api/hostess/stats`
- [ ] Deploy to staging, measure performance
- [ ] Enable in production with feature flags

---

## MONITORING

Once deployed, monitor:

```bash
# Check Hostess health
curl http://localhost:5001/api/hostess/stats

# Example response:
{
  "stats": {
    "total": 234,
    "completed": 231,
    "errors": 2,
    "timeouts": 1,
    "total_time_ms": 45600,
    "active_tasks": 2,
    "pending_tasks": 0,
    "avg_time_ms": 197,
    "error_rate": 0.0086
  }
}
```

Expected metrics:
- **Error Rate**: < 1% (occasional Ollama timeouts OK)
- **Avg Time**: 200-500ms depending on scenario
- **Timeouts**: < 5% (indicates good timeout settings)
- **Active Tasks**: Should stay < max_concurrent

---

## NEXT STEPS

1. **Phase 80.51**: Implement all 7 scenarios
2. **Phase 80.52**: Add feature flags per scenario
3. **Phase 80.53**: Dashboard for Hostess activity
4. **Phase 80.54**: Auto-tuning of timeouts based on real data
5. **Phase 80.55**: Integration with metrics/analytics

