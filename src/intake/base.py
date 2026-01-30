"""
Base interface for content intake.

Defines abstract ContentIntake class and IntakeResult dataclass
for processing various content sources.

@status: active
@phase: 96
@depends: abc, dataclasses, datetime, typing, enum
@used_by: youtube, web, manager
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class ContentType(Enum):
    VIDEO = "video"
    AUDIO = "audio"
    ARTICLE = "article"
    POST = "post"
    DOCUMENT = "document"
    IMAGE = "image"


@dataclass
class IntakeResult:
    """Result of content intake"""
    source_url: str
    source_type: str  # youtube, telegram, web, etc.
    content_type: ContentType
    title: str
    text: str  # Main text content (transcript or article)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Optional fields
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    language: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # Processing info
    processed_at: datetime = field(default_factory=datetime.now)
    processor_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_url": self.source_url,
            "source_type": self.source_type,
            "content_type": self.content_type.value,
            "title": self.title,
            "text": self.text,
            "text_length": len(self.text),
            "metadata": self.metadata,
            "author": self.author,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "duration_seconds": self.duration_seconds,
            "language": self.language,
            "tags": self.tags,
            "processed_at": self.processed_at.isoformat(),
            "processor_version": self.processor_version
        }


class ContentIntake(ABC):
    """Base class for content intake processors"""

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return source type identifier"""
        pass

    @property
    @abstractmethod
    def supported_patterns(self) -> List[str]:
        """Return list of URL patterns this processor handles"""
        pass

    @abstractmethod
    def can_process(self, url: str) -> bool:
        """Check if this processor can handle the URL"""
        pass

    @abstractmethod
    async def process(self, url: str, options: Dict[str, Any] = None) -> IntakeResult:
        """Process URL and return structured content"""
        pass
