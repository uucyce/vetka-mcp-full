"""
VETKA Metrics Collector.

Simple performance monitoring for agents - latency, status, tokens.

@status: active
@phase: 96
@depends: dataclasses, logging
@used_by: orchestrator_with_elisya.py, agents
"""

import logging
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class MetricSnapshot:
    """Снимок метрики в момент времени"""
    timestamp: str
    agent_name: str
    latency_ms: float
    status: str  # success, timeout, error
    tokens: int = 0
    error_msg: str = ""

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'agent_name': self.agent_name,
            'latency_ms': self.latency_ms,
            'status': self.status,
            'tokens': self.tokens,
            'error_msg': self.error_msg,
        }


@dataclass
class MetricsCollector:
    """
    Собирает метрики выполнения агентов.

    Features:
    - Запись latency, status, tokens для каждого вызова
    - Агрегация по агентам
    - Summary с avg latency и success rate
    """

    snapshots: List[MetricSnapshot] = field(default_factory=list)
    max_snapshots: int = 1000  # Ограничение на количество снимков в памяти

    def record(
        self,
        agent_name: str,
        latency_ms: float,
        status: str,
        tokens: int = 0,
        error_msg: str = ""
    ):
        """
        Записать метрику выполнения агента.

        Args:
            agent_name: Имя агента (pm, architect, dev, qa, arc_solver, etc.)
            latency_ms: Время выполнения в миллисекундах
            status: success, timeout, error
            tokens: Количество использованных токенов (если известно)
            error_msg: Сообщение об ошибке (если status != success)
        """
        snapshot = MetricSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent_name=agent_name,
            latency_ms=latency_ms,
            status=status,
            tokens=tokens,
            error_msg=error_msg[:200] if error_msg else ""
        )

        self.snapshots.append(snapshot)

        # Ограничиваем размер списка
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots = self.snapshots[-self.max_snapshots:]

        # Логируем
        status_emoji = "✅" if status == "success" else "⚠️" if status == "timeout" else "❌"
        logger.debug(
            f"{status_emoji} [{agent_name}] latency={latency_ms:.1f}ms "
            f"tokens={tokens} status={status}"
        )

    def record_success(self, agent_name: str, latency_ms: float, tokens: int = 0):
        """Shortcut для записи успешного выполнения"""
        self.record(agent_name, latency_ms, "success", tokens)

    def record_error(self, agent_name: str, latency_ms: float, error_msg: str):
        """Shortcut для записи ошибки"""
        self.record(agent_name, latency_ms, "error", error_msg=error_msg)

    def record_timeout(self, agent_name: str, latency_ms: float):
        """Shortcut для записи timeout"""
        self.record(agent_name, latency_ms, "timeout")

    def get_summary(self) -> Dict:
        """
        Получить сводку метрик по агентам.

        Returns:
            {
                'agent_name': {
                    'avg_latency_ms': float,
                    'success_rate': float (0-100),
                    'executions': int,
                    'total_tokens': int
                }
            }
        """
        by_agent: Dict[str, Dict] = {}

        for snapshot in self.snapshots:
            if snapshot.agent_name not in by_agent:
                by_agent[snapshot.agent_name] = {
                    'count': 0,
                    'total_latency': 0.0,
                    'success_count': 0,
                    'error_count': 0,
                    'timeout_count': 0,
                    'total_tokens': 0
                }

            stats = by_agent[snapshot.agent_name]
            stats['count'] += 1
            stats['total_latency'] += snapshot.latency_ms
            stats['total_tokens'] += snapshot.tokens

            if snapshot.status == 'success':
                stats['success_count'] += 1
            elif snapshot.status == 'timeout':
                stats['timeout_count'] += 1
            else:
                stats['error_count'] += 1

        # Вычисляем средние значения
        summary = {}
        for agent_name, stats in by_agent.items():
            summary[agent_name] = {
                'avg_latency_ms': stats['total_latency'] / stats['count'] if stats['count'] > 0 else 0,
                'success_rate': stats['success_count'] / stats['count'] * 100 if stats['count'] > 0 else 0,
                'executions': stats['count'],
                'total_tokens': stats['total_tokens'],
                'errors': stats['error_count'],
                'timeouts': stats['timeout_count'],
            }

        return summary

    def get_recent(self, limit: int = 10) -> List[Dict]:
        """Получить последние N снимков"""
        return [s.to_dict() for s in self.snapshots[-limit:]]

    def log_summary(self):
        """Вывести сводку метрик в лог"""
        summary = self.get_summary()

        if not summary:
            logger.info("📊 No metrics collected yet")
            return

        logger.info("=" * 60)
        logger.info("📊 METRICS SUMMARY:")
        for agent_name, metrics in sorted(summary.items()):
            logger.info(
                f"  {agent_name}: "
                f"avg={metrics['avg_latency_ms']:.1f}ms, "
                f"success={metrics['success_rate']:.0f}%, "
                f"runs={metrics['executions']}, "
                f"tokens={metrics['total_tokens']}"
            )
        logger.info("=" * 60)

    def clear(self):
        """Очистить все снимки"""
        self.snapshots.clear()
        logger.debug("Metrics cleared")


# Global instance
_metrics: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """
    Получить глобальный экземпляр MetricsCollector (singleton).

    Returns:
        MetricsCollector instance
    """
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


class MetricsTimer:
    """
    Context manager для автоматического измерения времени выполнения.

    Usage:
        metrics = get_metrics_collector()
        with MetricsTimer(metrics, 'pm_agent') as timer:
            result = pm_agent.execute(...)
            timer.tokens = result.tokens  # Опционально
    """

    def __init__(self, collector: MetricsCollector, agent_name: str):
        self.collector = collector
        self.agent_name = agent_name
        self.start_time: float = 0
        self.tokens: int = 0
        self._error: Optional[str] = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        latency_ms = (time.time() - self.start_time) * 1000

        if exc_type is not None:
            # Была ошибка
            self.collector.record_error(
                self.agent_name,
                latency_ms,
                str(exc_val)[:200] if exc_val else "Unknown error"
            )
        elif self._error:
            self.collector.record_error(self.agent_name, latency_ms, self._error)
        else:
            self.collector.record_success(self.agent_name, latency_ms, self.tokens)

        return False  # Не подавляем исключения

    def set_error(self, error_msg: str):
        """Установить ошибку (для случаев когда исключение не выбрасывается)"""
        self._error = error_msg
