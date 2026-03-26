"""Async orchestrator for AI generation jobs.

@status: active
@phase: B98
@task: tb_1774432033_1
"""
import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from src.services.cut_generation_budget import GenerationBudget
from src.services.cut_generation_job_store import GenerationJobStore
from src.services.cut_generation_providers import (
    BaseGenerationProvider,
    KlingProvider,
    RunwayProvider,
)

logger = logging.getLogger(__name__)

# Maximum polling duration: 30 minutes
_MAX_POLL_SECONDS = 30 * 60
_POLL_INTERVAL_SECONDS = 2.0


class GenerationService:
    """Async orchestrator for AI generation jobs."""

    def __init__(self) -> None:
        self._providers: Dict[str, BaseGenerationProvider] = {
            "runway": RunwayProvider(),
            "kling": KlingProvider(),
        }
        self._job_store: GenerationJobStore = GenerationJobStore.get_instance()
        self._budget: GenerationBudget = GenerationBudget.get_instance()

    @property
    def budget(self) -> GenerationBudget:
        return self._budget

    # ------------------------------------------------------------------
    # Provider registry
    # ------------------------------------------------------------------

    def get_provider(self, name: str) -> BaseGenerationProvider:
        """Return provider by name, raise KeyError if not found."""
        provider = self._providers.get(name)
        if provider is None:
            raise KeyError(f"Unknown generation provider: {name!r}")
        return provider

    def list_providers(self) -> List[dict]:
        """Return list of provider capability dicts."""
        result: List[dict] = []
        for name, provider in self._providers.items():
            caps: Dict[str, Any] = {"name": name}
            if hasattr(provider, "capabilities"):
                caps.update(provider.capabilities())
            result.append(caps)
        return result

    def get_job_status(self, job_id: str) -> Optional[dict]:
        """Return current status of a generation job, or None if not found."""
        return self._job_store.get(job_id)

    def get_active_jobs(self) -> List[dict]:
        """Return all active (non-terminal) jobs."""
        return self._job_store.get_active()

    # ------------------------------------------------------------------
    # Job lifecycle
    # ------------------------------------------------------------------

    async def submit_job(self, provider_name: str, params: dict) -> dict:
        """Submit a new generation job.

        Steps:
        1. Resolve provider.
        2. Check budget (estimated cost).
        3. Create job record in store.
        4. Call provider.submit(params).
        5. Update store with provider_job_id.
        6. Start background polling task.
        7. Return job dict.
        """
        provider = self.get_provider(provider_name)

        # Estimate cost (provider may return 0.0 if unknown)
        estimated_cost: float = 0.0
        if hasattr(provider, "estimate_cost"):
            estimated_cost = provider.estimate_cost(params)

        if not self._budget.can_spend(estimated_cost):
            raise RuntimeError(
                f"Budget exceeded: cannot spend ${estimated_cost:.4f} for {provider_name!r}"
            )

        job_id = str(uuid.uuid4())
        job = self._job_store.create(job_id, provider_name, params)
        logger.info("GenerationService: created job %s via %s", job_id, provider_name)

        try:
            provider_job_id: str = await provider.submit(params)
        except Exception as exc:
            self._job_store.update(job_id, status="failed", error=str(exc))
            logger.error("GenerationService: submit failed for job %s: %s", job_id, exc)
            raise

        self._job_store.update(job_id, provider_job_id=provider_job_id, status="generating")

        # Fire-and-forget background polling
        asyncio.create_task(
            self._poll_loop(job_id, provider, provider_job_id),
            name=f"poll-{job_id}",
        )

        return self._job_store.get(job_id)

    async def _poll_loop(
        self,
        job_id: str,
        provider: BaseGenerationProvider,
        provider_job_id: str,
    ) -> None:
        """Background loop: poll provider every 2 s until terminal state or timeout."""
        deadline = time.monotonic() + _MAX_POLL_SECONDS

        while time.monotonic() < deadline:
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)

            job = self._job_store.get(job_id)
            if job is None:
                logger.warning("GenerationService: job %s disappeared from store", job_id)
                return

            # Cancelled externally (e.g. cancel_job was called)
            if job["status"] == "cancelled":
                logger.info("GenerationService: job %s already cancelled", job_id)
                return

            try:
                status_payload: dict = await provider.poll_status(provider_job_id)
            except Exception as exc:
                logger.error(
                    "GenerationService: poll error for job %s: %s", job_id, exc
                )
                # Transient error — keep polling
                continue

            status: str = status_payload.get("status", "generating")
            progress: float = float(status_payload.get("progress", job["progress"]))

            self._job_store.update(job_id, status=status, progress=progress)

            if status == "completed":
                output_url: Optional[str] = status_payload.get("output_url")
                output_path: Optional[str] = None
                cost_usd: float = float(status_payload.get("cost_usd", 0.0))

                # Download result if provider supplies a URL
                if output_url and hasattr(provider, "download_result"):
                    try:
                        output_path = await provider.download_result(
                            output_url, job_id
                        )
                    except Exception as exc:
                        logger.error(
                            "GenerationService: download failed for job %s: %s",
                            job_id,
                            exc,
                        )

                self._job_store.update(
                    job_id,
                    status="completed",
                    progress=1.0,
                    output_url=output_url,
                    output_path=output_path,
                    cost_usd=cost_usd,
                )

                if cost_usd > 0.0:
                    self._budget.record_spend(cost_usd)

                logger.info(
                    "GenerationService: job %s completed (cost $%.4f)", job_id, cost_usd
                )
                return

            if status in ("failed", "cancelled"):
                error_msg: str = status_payload.get("error", "")
                self._job_store.update(job_id, status=status, error=error_msg)
                logger.warning(
                    "GenerationService: job %s terminal status=%s error=%s",
                    job_id,
                    status,
                    error_msg,
                )
                return

        # Timeout
        self._job_store.update(
            job_id,
            status="failed",
            error="Polling timeout after 30 minutes",
        )
        logger.error("GenerationService: job %s timed out", job_id)

    async def cancel_job(self, job_id: str) -> bool:
        """Request cancellation of a job.

        Returns True if the job was found and marked for cancellation.
        """
        job = self._job_store.get(job_id)
        if job is None:
            return False

        if job["status"] in ("completed", "failed", "cancelled"):
            return False

        provider_name: str = job["provider"]
        provider_job_id: Optional[str] = job.get("provider_job_id")

        # Best-effort remote cancellation
        if provider_job_id:
            try:
                provider = self.get_provider(provider_name)
                if hasattr(provider, "cancel"):
                    await provider.cancel(provider_job_id)
            except Exception as exc:
                logger.warning(
                    "GenerationService: remote cancel failed for job %s: %s",
                    job_id,
                    exc,
                )

        self._job_store.update(job_id, status="cancelled")
        logger.info("GenerationService: job %s cancelled", job_id)
        return True

    async def accept_job(self, job_id: str) -> dict:
        """Mark a completed job as accepted and return its output_path.

        Raises ValueError if job is not in 'completed' state.
        """
        job = self._job_store.get(job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id!r}")

        if job["status"] != "completed":
            raise ValueError(
                f"Cannot accept job {job_id!r}: status is {job['status']!r}, expected 'completed'"
            )

        updated = self._job_store.update(job_id, status="accepted")
        logger.info("GenerationService: job %s accepted", job_id)
        return updated
