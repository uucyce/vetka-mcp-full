"""
Multimodal extraction contracts for ingestion pipeline.

MARKER_153.IMPL.CONTRACTS_MULTIMODAL
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class OCRResult:
    text: str
    confidence: float
    boxes: List[Dict[str, Any]]
    source_path: str
    extractor: str
    timestamp_sec: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MediaChunk:
    start_sec: float
    end_sec: float
    text: str
    confidence: float = 0.0
    speaker: Optional[str] = None
    frame_ref: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

