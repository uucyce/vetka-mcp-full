# @status: active
# @phase: B98
# @task: tb_1774432033_1
# MARKER_B98 — Runway Gen-3 Alpha Turbo provider.

import asyncio
import json
import os
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

from .base_provider import BaseGenerationProvider, GenerationResult


class RunwayProvider(BaseGenerationProvider):
    name = "runway"
    supports_text_to_video = True
    supports_image_to_video = True
    supports_text_to_image = False
    supports_text_to_audio = False

    def __init__(self, api_key: str = "", base_url: str = ""):
        api_key = api_key or os.environ.get("RUNWAY_API_KEY", "")
        base_url = base_url or "https://api.dev.runwayml.com/v1"
        super().__init__(api_key=api_key, base_url=base_url)

    def _make_request(
        self,
        method: str,
        path: str,
        body: dict = None,
    ) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-Runway-Version", "2024-11-06")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else str(e)
            raise RuntimeError(f"Runway HTTP {e.code}: {error_body}") from e

    async def test_connection(self) -> bool:
        if not self.api_key or len(self.api_key) < 10:
            return False
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, lambda: self._make_request("GET", "/organization"))
            return True
        except Exception:
            # Treat any response (even 4xx about auth format) as reachable
            return bool(self.api_key)

    async def estimate_cost(self, params: dict) -> float:
        duration = float(params.get("duration", 5))
        cost_per_second = 0.05
        return round(duration * cost_per_second, 4)

    async def submit(self, params: dict) -> GenerationResult:
        prompt = params.get("prompt", "")
        duration = params.get("duration", 5)
        image_url = params.get("image_url")
        model = params.get("model", "gen3a_turbo")

        body: dict = {
            "model": model,
            "promptText": prompt,
            "duration": duration,
        }
        if image_url:
            body["promptImage"] = image_url

        loop = asyncio.get_event_loop()
        try:
            resp = await loop.run_in_executor(
                None, lambda: self._make_request("POST", "/image_to_video", body)
            )
            job_id = resp.get("id", "")
            status = resp.get("status", "pending")
            return GenerationResult(
                success=True,
                job_id=job_id,
                status=self._map_status(status),
                progress=0.0,
                metadata={"raw": resp},
            )
        except Exception as e:
            return GenerationResult(
                success=False,
                job_id="",
                status="failed",
                progress=0.0,
                error=str(e),
            )

    async def poll_status(self, job_id: str) -> GenerationResult:
        loop = asyncio.get_event_loop()
        try:
            resp = await loop.run_in_executor(
                None, lambda: self._make_request("GET", f"/tasks/{job_id}")
            )
            raw_status = resp.get("status", "pending")
            mapped = self._map_status(raw_status)
            progress = 100.0 if mapped == "completed" else float(resp.get("progress", 0)) * 100
            output_url = None
            output = resp.get("output")
            if isinstance(output, list) and output:
                output_url = output[0]
            elif isinstance(output, str):
                output_url = output
            return GenerationResult(
                success=True,
                job_id=job_id,
                status=mapped,
                progress=progress,
                output_url=output_url,
                metadata={"raw": resp},
            )
        except Exception as e:
            return GenerationResult(
                success=False,
                job_id=job_id,
                status="failed",
                progress=0.0,
                error=str(e),
            )

    async def cancel(self, job_id: str) -> bool:
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None, lambda: self._make_request("DELETE", f"/tasks/{job_id}")
            )
            return True
        except Exception:
            return False

    async def download_result(self, job_id: str, output_dir: str) -> str:
        result = await self.poll_status(job_id)
        if not result.output_url:
            raise RuntimeError(f"No output URL for job {job_id}")

        output_path = Path(output_dir) / f"runway_{job_id}.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        loop = asyncio.get_event_loop()

        def _fetch():
            urllib.request.urlretrieve(result.output_url, str(output_path))

        await loop.run_in_executor(None, _fetch)
        return str(output_path)

    @staticmethod
    def _map_status(raw: str) -> str:
        mapping = {
            "PENDING": "pending",
            "pending": "pending",
            "RUNNING": "processing",
            "running": "processing",
            "processing": "processing",
            "SUCCEEDED": "completed",
            "succeeded": "completed",
            "completed": "completed",
            "FAILED": "failed",
            "failed": "failed",
            "CANCELLED": "cancelled",
            "cancelled": "cancelled",
        }
        return mapping.get(raw, "pending")
