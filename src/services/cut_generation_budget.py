"""
MARKER_B98 — Generation budget tracker.
Tracks AI generation spend with daily/monthly limits and 80% alert threshold.

@status: active
@phase: B98
@task: tb_1774432033_1
"""
import json
import logging
import time
from pathlib import Path
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

class GenerationBudget:
    """Track AI generation spending with daily and monthly limits."""

    _instance = None

    @classmethod
    def get_instance(cls, persist_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = cls(persist_path)
        return cls._instance

    def __init__(self, persist_path: Optional[str] = None):
        self._lock = Lock()
        self.daily_limit_usd: float = 10.0  # configurable
        self.monthly_limit_usd: float = 200.0
        self.alert_threshold: float = 0.8  # 80%
        self._spends: list = []  # list of {timestamp, amount, provider, job_id}
        self._persist_path = Path(persist_path) if persist_path else None
        if self._persist_path and self._persist_path.exists():
            self._load()

    def record_spend(self, amount: float, provider: str, job_id: str):
        with self._lock:
            self._spends.append({
                "timestamp": time.time(),
                "amount": amount,
                "provider": provider,
                "job_id": job_id,
            })
            self._persist()
            daily = self.get_daily_spend()
            monthly = self.get_monthly_spend()
            if daily >= self.daily_limit_usd * self.alert_threshold:
                logger.warning("Budget alert: daily spend $%.2f / $%.2f (%.0f%%)",
                             daily, self.daily_limit_usd, daily/self.daily_limit_usd*100)
            if monthly >= self.monthly_limit_usd * self.alert_threshold:
                logger.warning("Budget alert: monthly spend $%.2f / $%.2f (%.0f%%)",
                             monthly, self.monthly_limit_usd, monthly/self.monthly_limit_usd*100)

    def can_spend(self, estimated_cost: float) -> tuple[bool, str]:
        """Check if estimated_cost would exceed limits. Returns (allowed, reason)."""
        with self._lock:
            daily = self.get_daily_spend()
            monthly = self.get_monthly_spend()
            if daily + estimated_cost > self.daily_limit_usd:
                return False, f"Daily limit exceeded: ${daily:.2f} + ${estimated_cost:.2f} > ${self.daily_limit_usd:.2f}"
            if monthly + estimated_cost > self.monthly_limit_usd:
                return False, f"Monthly limit exceeded: ${monthly:.2f} + ${estimated_cost:.2f} > ${self.monthly_limit_usd:.2f}"
            return True, "ok"

    def get_daily_spend(self) -> float:
        """Total spend in last 24 hours (no lock — caller must hold lock or call is safe for reads)."""
        cutoff = time.time() - 86400
        return sum(s["amount"] for s in self._spends if s["timestamp"] >= cutoff)

    def get_monthly_spend(self) -> float:
        cutoff = time.time() - 86400 * 30
        return sum(s["amount"] for s in self._spends if s["timestamp"] >= cutoff)

    def get_summary(self) -> dict:
        with self._lock:
            daily = self.get_daily_spend()
            monthly = self.get_monthly_spend()
            return {
                "daily_spend_usd": round(daily, 2),
                "daily_limit_usd": self.daily_limit_usd,
                "daily_remaining_usd": round(max(0, self.daily_limit_usd - daily), 2),
                "monthly_spend_usd": round(monthly, 2),
                "monthly_limit_usd": self.monthly_limit_usd,
                "monthly_remaining_usd": round(max(0, self.monthly_limit_usd - monthly), 2),
                "alert_threshold": self.alert_threshold,
                "total_jobs": len(self._spends),
            }

    def set_limits(self, daily: Optional[float] = None, monthly: Optional[float] = None):
        with self._lock:
            if daily is not None:
                self.daily_limit_usd = daily
            if monthly is not None:
                self.monthly_limit_usd = monthly
            self._persist()

    def _persist(self):
        if not self._persist_path:
            return
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "daily_limit": self.daily_limit_usd,
                "monthly_limit": self.monthly_limit_usd,
                "spends": self._spends[-1000:],  # keep last 1000
            }
            self._persist_path.write_text(json.dumps(data))
        except Exception as e:
            logger.warning("Budget persist failed: %s", e)

    def _load(self):
        try:
            data = json.loads(self._persist_path.read_text())
            self.daily_limit_usd = data.get("daily_limit", 10.0)
            self.monthly_limit_usd = data.get("monthly_limit", 200.0)
            self._spends = data.get("spends", [])
        except Exception as e:
            logger.warning("Budget load failed: %s", e)
