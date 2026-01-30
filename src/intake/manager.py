"""
Universal content intake manager.

Coordinates content processors (YouTube, Web) and manages intake storage.
Provides singleton access via get_intake_manager().

@status: active
@phase: 96
@depends: base, youtube, web, asyncio, hashlib, json, pathlib
@used_by: src.intake, tools
"""
import asyncio
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import ContentIntake, IntakeResult
from .youtube import YouTubeIntake
from .web import WebIntake


class IntakeManager:
    """Manages content intake from various sources"""

    def __init__(self, project_root: str = None):
        if project_root is None:
            project_root = str(Path(__file__).parent.parent.parent)
        self.project_root = Path(project_root)
        self.intake_dir = self.project_root / "data" / "intake"
        self.intake_dir.mkdir(parents=True, exist_ok=True)

        # Register processors
        self.processors: List[ContentIntake] = [
            YouTubeIntake(),
            WebIntake(),  # Should be last (catches all)
        ]

    def get_processor(self, url: str) -> Optional[ContentIntake]:
        """Find appropriate processor for URL"""
        for processor in self.processors:
            if processor.can_process(url):
                return processor
        return None

    async def process_url(self, url: str, options: Dict[str, Any] = None) -> IntakeResult:
        """Process URL and return structured content"""
        processor = self.get_processor(url)
        if not processor:
            raise ValueError(f"No processor found for URL: {url}")

        result = await processor.process(url, options)

        # Save to intake directory
        await self._save_result(result)

        return result

    async def process_batch(self, urls: List[str], options: Dict[str, Any] = None) -> List[IntakeResult]:
        """Process multiple URLs"""
        tasks = [self.process_url(url, options) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Error processing {urls[i]}: {result}")
            else:
                valid_results.append(result)

        return valid_results

    async def _save_result(self, result: IntakeResult) -> Path:
        """Save intake result to file"""
        # Create safe filename
        url_hash = hashlib.md5(result.source_url.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{result.source_type}_{url_hash}_{timestamp}.json"

        output_path = self.intake_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

        return output_path

    def list_intakes(self, source_type: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """List recent intakes"""
        files = sorted(
            self.intake_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        results = []
        for f in files[:limit * 2]:  # Get more to filter
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)

                if source_type and data.get("source_type") != source_type:
                    continue

                results.append({
                    "filename": f.name,
                    "source_type": data.get("source_type"),
                    "title": data.get("title", "")[:100],
                    "text_length": data.get("text_length", 0),
                    "processed_at": data.get("processed_at"),
                    "source_url": data.get("source_url")
                })

                if len(results) >= limit:
                    break
            except Exception:
                continue

        return results

    def get_intake(self, filename: str) -> Optional[Dict]:
        """Get specific intake by filename"""
        # Security: ensure filename doesn't contain path traversal
        if '/' in filename or '\\' in filename or '..' in filename:
            return None

        file_path = self.intake_dir / filename
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def delete_intake(self, filename: str) -> bool:
        """Delete an intake file"""
        # Security: ensure filename doesn't contain path traversal
        if '/' in filename or '\\' in filename or '..' in filename:
            return False

        file_path = self.intake_dir / filename
        if file_path.exists():
            file_path.unlink()
            return True
        return False


# Singleton instance
_manager: Optional[IntakeManager] = None


def get_intake_manager() -> IntakeManager:
    global _manager
    if _manager is None:
        _manager = IntakeManager()
    return _manager
