# @status: active
# @phase: B98
# @task: tb_1774432033_1
# MARKER_B98 — Abstract base for AI generation providers.

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class GenerationResult:
    success: bool
    job_id: str
    status: str  # "pending"|"processing"|"completed"|"failed"|"cancelled"
    progress: float  # 0-100
    output_url: Optional[str] = None
    output_path: Optional[str] = None
    error: Optional[str] = None
    cost_usd: float = 0.0
    metadata: dict = None  # provider-specific data

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseGenerationProvider(ABC):
    name: str = "base"
    supports_text_to_video: bool = False
    supports_image_to_video: bool = False
    supports_text_to_image: bool = False
    supports_text_to_audio: bool = False

    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    async def test_connection(self) -> bool: ...

    @abstractmethod
    async def estimate_cost(self, params: dict) -> float: ...

    @abstractmethod
    async def submit(self, params: dict) -> GenerationResult: ...

    @abstractmethod
    async def poll_status(self, job_id: str) -> GenerationResult: ...

    @abstractmethod
    async def cancel(self, job_id: str) -> bool: ...

    @abstractmethod
    async def download_result(self, job_id: str, output_dir: str) -> str: ...

    def get_capabilities(self) -> dict:
        return {
            "name": self.name,
            "text_to_video": self.supports_text_to_video,
            "image_to_video": self.supports_image_to_video,
            "text_to_image": self.supports_text_to_image,
            "text_to_audio": self.supports_text_to_audio,
        }
