"""
Web page content intake.

Extracts article text from web pages using trafilatura or BeautifulSoup fallback.

@status: active
@phase: 96
@depends: base, re, urllib.parse, trafilatura, beautifulsoup4
@used_by: manager, src.intake
"""
import re
from typing import Any, Dict, List, Optional
from datetime import datetime
from urllib.parse import urlparse

from .base import ContentIntake, IntakeResult, ContentType


class WebIntake(ContentIntake):
    """Process web pages - extract article text"""

    @property
    def source_type(self) -> str:
        return "web"

    @property
    def supported_patterns(self) -> List[str]:
        return [r"https?://"]  # Any HTTP URL

    def can_process(self, url: str) -> bool:
        # Process any URL that's not handled by specialized processors
        parsed = urlparse(url)
        # Exclude known video/social platforms
        excluded = ['youtube.com', 'youtu.be', 't.me', 'twitter.com', 'x.com']
        return not any(exc in parsed.netloc for exc in excluded)

    async def process(self, url: str, options: Dict[str, Any] = None) -> IntakeResult:
        options = options or {}

        try:
            # Try trafilatura first (best for articles)
            import trafilatura

            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                # Extract with metadata
                result = trafilatura.extract(
                    downloaded,
                    include_comments=False,
                    include_tables=True,
                    output_format='txt',
                    with_metadata=True
                )

                metadata = trafilatura.extract_metadata(downloaded)

                return IntakeResult(
                    source_url=url,
                    source_type=self.source_type,
                    content_type=ContentType.ARTICLE,
                    title=metadata.title if metadata else urlparse(url).path,
                    text=result or "",
                    metadata={
                        "sitename": metadata.sitename if metadata else None,
                        "hostname": metadata.hostname if metadata else urlparse(url).netloc,
                        "categories": list(metadata.categories) if metadata and metadata.categories else [],
                    },
                    author=metadata.author if metadata else None,
                    published_at=self._parse_date(metadata.date if metadata else None),
                    language=metadata.language if metadata else None,
                    tags=list(metadata.tags) if metadata and metadata.tags else []
                )
        except ImportError:
            pass
        except Exception:
            pass

        # Fallback to BeautifulSoup
        return await self._process_with_bs4(url)

    async def _process_with_bs4(self, url: str) -> IntakeResult:
        """Fallback extraction with BeautifulSoup"""
        import requests
        from bs4 import BeautifulSoup

        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; VETKABot/1.0)'
        })
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove scripts and styles
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()

        # Get title
        title = soup.title.string if soup.title else urlparse(url).path

        # Get main content
        main = soup.find('main') or soup.find('article') or soup.find('body')
        text = main.get_text(separator='\n', strip=True) if main else ""

        # Clean up text
        text = re.sub(r'\n{3,}', '\n\n', text)

        return IntakeResult(
            source_url=url,
            source_type=self.source_type,
            content_type=ContentType.ARTICLE,
            title=title or "Unknown",
            text=text[:50000],  # Limit size
            metadata={
                "hostname": urlparse(url).netloc
            }
        )

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception:
            return None
