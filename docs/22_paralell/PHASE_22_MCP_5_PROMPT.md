# VETKA Phase 22-MCP-5: Universal Content Intake

## 🎯 ЗАДАЧА
Создать универсальный парсер для intake контента из разных источников:
- YouTube видео → транскрипт + метаданные
- Веб-страницы → текст + структура
- (Опционально) Telegram каналы → сообщения

## 📋 ШАГ 1: АНАЛИЗ

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

# Проверить зависимости
pip show yt-dlp 2>/dev/null || echo "yt-dlp not installed"
pip show beautifulsoup4 2>/dev/null || echo "bs4 not installed"
pip show trafilatura 2>/dev/null || echo "trafilatura not installed"

# Проверить whisper (для транскрипции)
which whisper 2>/dev/null || echo "whisper CLI not found"
ollama list | grep whisper || echo "No whisper model in Ollama"
```

## 📋 ШАГ 2: УСТАНОВКА ЗАВИСИМОСТЕЙ

```bash
# YouTube download
pip install yt-dlp

# Web scraping
pip install beautifulsoup4 trafilatura requests

# Транскрипция (опционально - можно использовать Ollama или API)
# pip install openai-whisper  # Тяжёлый, лучше API
```

## 📋 ШАГ 3: CONTENT INTAKE MODULE

### 3.1 Базовый интерфейс (src/intake/base.py)

```python
"""Base interface for content intake"""
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
```

### 3.2 YouTube Intake (src/intake/youtube.py)

```python
"""YouTube content intake using yt-dlp"""
import asyncio
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import ContentIntake, IntakeResult, ContentType

class YouTubeIntake(ContentIntake):
    """Process YouTube videos - extract metadata and transcript"""
    
    source_type = "youtube"
    supported_patterns = [
        r"youtube\.com/watch\?v=",
        r"youtu\.be/",
        r"youtube\.com/shorts/"
    ]
    
    def __init__(self, whisper_model: str = "base", use_api: bool = False):
        """
        Args:
            whisper_model: Whisper model size (tiny, base, small, medium, large)
            use_api: Use OpenAI API for transcription instead of local
        """
        self.whisper_model = whisper_model
        self.use_api = use_api
    
    def can_process(self, url: str) -> bool:
        return any(re.search(pattern, url) for pattern in self.supported_patterns)
    
    async def process(self, url: str, options: Dict[str, Any] = None) -> IntakeResult:
        options = options or {}
        
        # 1. Get video metadata
        metadata = await self._get_metadata(url)
        
        # 2. Try to get existing subtitles first
        transcript = await self._get_subtitles(url, metadata.get("id"))
        
        # 3. If no subtitles, download audio and transcribe
        if not transcript and options.get("transcribe", True):
            transcript = await self._transcribe_audio(url, metadata.get("id"))
        
        return IntakeResult(
            source_url=url,
            source_type=self.source_type,
            content_type=ContentType.VIDEO,
            title=metadata.get("title", "Unknown"),
            text=transcript or "",
            metadata={
                "video_id": metadata.get("id"),
                "channel": metadata.get("channel"),
                "channel_id": metadata.get("channel_id"),
                "view_count": metadata.get("view_count"),
                "like_count": metadata.get("like_count"),
                "thumbnail": metadata.get("thumbnail"),
                "description": metadata.get("description", "")[:500]
            },
            author=metadata.get("channel"),
            published_at=self._parse_date(metadata.get("upload_date")),
            duration_seconds=metadata.get("duration"),
            language=metadata.get("language"),
            tags=metadata.get("tags", [])[:10]
        )
    
    async def _get_metadata(self, url: str) -> Dict[str, Any]:
        """Get video metadata using yt-dlp"""
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-download",
            url
        ]
        
        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                return json.loads(stdout.decode())
            else:
                return {"error": stderr.decode()}
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_subtitles(self, url: str, video_id: str) -> Optional[str]:
        """Try to get existing subtitles"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                "yt-dlp",
                "--write-auto-sub",
                "--write-sub",
                "--sub-lang", "en,ru",
                "--sub-format", "vtt",
                "--skip-download",
                "-o", f"{tmpdir}/%(id)s.%(ext)s",
                url
            ]
            
            try:
                result = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                # Find subtitle file
                for ext in ["en.vtt", "ru.vtt", "vtt"]:
                    sub_file = Path(tmpdir) / f"{video_id}.{ext}"
                    if sub_file.exists():
                        return self._parse_vtt(sub_file.read_text())
                
                return None
            except Exception:
                return None
    
    def _parse_vtt(self, vtt_content: str) -> str:
        """Parse VTT subtitles to plain text"""
        lines = []
        for line in vtt_content.split('\n'):
            # Skip timestamps and metadata
            if '-->' in line or line.startswith('WEBVTT') or not line.strip():
                continue
            # Skip position tags
            if line.strip().startswith('<'):
                continue
            # Remove HTML tags
            clean = re.sub(r'<[^>]+>', '', line)
            if clean.strip():
                lines.append(clean.strip())
        
        # Deduplicate consecutive lines (subtitles often repeat)
        result = []
        prev = None
        for line in lines:
            if line != prev:
                result.append(line)
                prev = line
        
        return ' '.join(result)
    
    async def _transcribe_audio(self, url: str, video_id: str) -> Optional[str]:
        """Download audio and transcribe with Whisper"""
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / f"{video_id}.mp3"
            
            # Download audio only
            cmd = [
                "yt-dlp",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "5",  # Lower quality for faster processing
                "-o", str(audio_path),
                url
            ]
            
            try:
                result = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if not audio_path.exists():
                    # yt-dlp adds extension
                    audio_path = Path(tmpdir) / f"{video_id}.mp3"
                    if not audio_path.exists():
                        return None
                
                # Transcribe with Whisper
                if self.use_api:
                    return await self._transcribe_api(audio_path)
                else:
                    return await self._transcribe_local(audio_path)
                    
            except Exception as e:
                return f"[Transcription error: {e}]"
    
    async def _transcribe_local(self, audio_path: Path) -> str:
        """Transcribe using local Whisper"""
        cmd = [
            "whisper",
            str(audio_path),
            "--model", self.whisper_model,
            "--output_format", "txt",
            "--output_dir", str(audio_path.parent)
        ]
        
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await result.communicate()
        
        txt_path = audio_path.with_suffix('.txt')
        if txt_path.exists():
            return txt_path.read_text()
        return ""
    
    async def _transcribe_api(self, audio_path: Path) -> str:
        """Transcribe using OpenAI API"""
        # Placeholder - would need OpenAI API key
        return "[API transcription not implemented]"
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y%m%d")
        except:
            return None
```

### 3.3 Web Page Intake (src/intake/web.py)

```python
"""Web page content intake"""
import asyncio
import re
from typing import Any, Dict, List, Optional
from datetime import datetime
from urllib.parse import urlparse

from .base import ContentIntake, IntakeResult, ContentType

class WebIntake(ContentIntake):
    """Process web pages - extract article text"""
    
    source_type = "web"
    supported_patterns = [r"https?://"]  # Any HTTP URL
    
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
                        "categories": metadata.categories if metadata else [],
                    },
                    author=metadata.author if metadata else None,
                    published_at=self._parse_date(metadata.date if metadata else None),
                    language=metadata.language if metadata else None,
                    tags=metadata.tags if metadata else []
                )
        except ImportError:
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
        except:
            return None
```

### 3.4 Universal Intake Manager (src/intake/manager.py)

```python
"""Universal content intake manager"""
import asyncio
from typing import Any, Dict, List, Optional, Type
from pathlib import Path
import json
from datetime import datetime

from .base import ContentIntake, IntakeResult
from .youtube import YouTubeIntake
from .web import WebIntake

class IntakeManager:
    """Manages content intake from various sources"""
    
    def __init__(self, project_root: str = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"):
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
        import hashlib
        url_hash = hashlib.md5(result.source_url.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{result.source_type}_{url_hash}_{timestamp}.json"
        
        output_path = self.intake_dir / filename
        with open(output_path, 'w') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def list_intakes(self, source_type: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """List recent intakes"""
        files = sorted(self.intake_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        
        results = []
        for f in files[:limit * 2]:  # Get more to filter
            try:
                with open(f, 'r') as file:
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
            except:
                continue
        
        return results
    
    def get_intake(self, filename: str) -> Optional[Dict]:
        """Get specific intake by filename"""
        file_path = self.intake_dir / filename
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return None


# Singleton instance
_manager: Optional[IntakeManager] = None

def get_intake_manager() -> IntakeManager:
    global _manager
    if _manager is None:
        _manager = IntakeManager()
    return _manager
```

### 3.5 MCP Tools для Intake (src/intake/tools.py)

```python
"""MCP Tools for content intake"""
from typing import Any, Dict
import asyncio

from src.mcp.mcp_server import MCPTool, mcp_tool
from .manager import get_intake_manager

@mcp_tool
class IntakeURLTool(MCPTool):
    """Process URL and extract content (YouTube, web pages)"""
    
    name = "vetka_intake_url"
    description = "Extract content from URL (YouTube video transcript, web article text)"
    schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to process (YouTube, web page)"
            },
            "transcribe": {
                "type": "boolean",
                "description": "For YouTube: transcribe if no subtitles (slower)",
                "default": False
            }
        },
        "required": ["url"]
    }
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        url = arguments.get("url", "")
        options = {
            "transcribe": arguments.get("transcribe", False)
        }
        
        manager = get_intake_manager()
        
        # Run async in sync context
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(manager.process_url(url, options))
            return {
                "success": True,
                "source_type": result.source_type,
                "title": result.title,
                "text_preview": result.text[:2000] if result.text else "",
                "text_length": len(result.text),
                "author": result.author,
                "duration_seconds": result.duration_seconds,
                "metadata": result.metadata
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            loop.close()


@mcp_tool
class ListIntakesTool(MCPTool):
    """List processed content intakes"""
    
    name = "vetka_list_intakes"
    description = "List recent content intakes (YouTube, web pages)"
    schema = {
        "type": "object",
        "properties": {
            "source_type": {
                "type": "string",
                "description": "Filter by source (youtube, web)",
                "enum": ["youtube", "web"]
            },
            "limit": {
                "type": "integer",
                "description": "Number of results",
                "default": 10
            }
        }
    }
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        manager = get_intake_manager()
        
        intakes = manager.list_intakes(
            source_type=arguments.get("source_type"),
            limit=arguments.get("limit", 10)
        )
        
        return {
            "count": len(intakes),
            "intakes": intakes
        }


@mcp_tool
class GetIntakeTool(MCPTool):
    """Get full content of an intake"""
    
    name = "vetka_get_intake"
    description = "Get full text content of a processed intake"
    schema = {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Intake filename from list_intakes"
            }
        },
        "required": ["filename"]
    }
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        manager = get_intake_manager()
        
        intake = manager.get_intake(arguments.get("filename", ""))
        if intake:
            return {
                "success": True,
                **intake
            }
        return {
            "success": False,
            "error": "Intake not found"
        }
```

## 📋 ШАГ 4: REST ENDPOINTS

Добавить в main.py:

```python
# Content Intake endpoints
@app.route('/api/intake/process', methods=['POST'])
async def intake_process():
    """Process URL and extract content"""
    from src.intake.manager import get_intake_manager
    
    data = request.json or {}
    url = data.get('url')
    
    if not url:
        return jsonify({"success": False, "error": "URL required"}), 400
    
    options = {
        "transcribe": data.get("transcribe", False)
    }
    
    manager = get_intake_manager()
    
    try:
        result = await manager.process_url(url, options)
        return jsonify({
            "success": True,
            "source_type": result.source_type,
            "title": result.title,
            "text_preview": result.text[:2000],
            "text_length": len(result.text),
            "author": result.author,
            "metadata": result.metadata
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/intake/list', methods=['GET'])
def intake_list():
    """List processed intakes"""
    from src.intake.manager import get_intake_manager
    
    source_type = request.args.get('source_type')
    limit = int(request.args.get('limit', 20))
    
    manager = get_intake_manager()
    intakes = manager.list_intakes(source_type, limit)
    
    return jsonify({
        "count": len(intakes),
        "intakes": intakes
    })


@app.route('/api/intake/<filename>', methods=['GET'])
def intake_get(filename):
    """Get specific intake"""
    from src.intake.manager import get_intake_manager
    
    manager = get_intake_manager()
    intake = manager.get_intake(filename)
    
    if intake:
        return jsonify(intake)
    return jsonify({"error": "Not found"}), 404
```

## 📋 ШАГ 5: ТЕСТЫ

Добавить в tests/test_mcp_server.py:

```python
# ============================================================
# PHASE 22-MCP-5 TESTS
# ============================================================

def test_33_youtube_intake_metadata():
    """Test YouTube metadata extraction"""
    from src.intake.youtube import YouTubeIntake
    
    intake = YouTubeIntake()
    
    # Test pattern matching
    assert intake.can_process("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert intake.can_process("https://youtu.be/dQw4w9WgXcQ")
    assert not intake.can_process("https://example.com/video")
    
    print("✅ Test 33: YouTube intake pattern matching works")

def test_34_web_intake():
    """Test web page intake"""
    from src.intake.web import WebIntake
    
    intake = WebIntake()
    
    # Test pattern matching
    assert intake.can_process("https://example.com/article")
    assert not intake.can_process("https://youtube.com/watch?v=123")
    
    print("✅ Test 34: Web intake pattern matching works")

def test_35_intake_manager():
    """Test intake manager"""
    from src.intake.manager import IntakeManager
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = IntakeManager(project_root=tmpdir)
        
        # Test processor selection
        processor = manager.get_processor("https://youtube.com/watch?v=abc")
        assert processor is not None
        assert processor.source_type == "youtube"
        
        processor = manager.get_processor("https://example.com/article")
        assert processor is not None
        assert processor.source_type == "web"
    
    print("✅ Test 35: Intake manager processor selection works")

def test_36_intake_list_endpoint():
    """Test intake list endpoint"""
    response = requests.get(f"{BASE_URL}/api/intake/list")
    assert response.status_code == 200
    data = response.json()
    assert "intakes" in data
    print("✅ Test 36: Intake list endpoint works")

def test_37_intake_tools_import():
    """Test intake tools can be imported"""
    try:
        from src.intake.tools import IntakeURLTool, ListIntakesTool, GetIntakeTool
        
        assert IntakeURLTool.name == "vetka_intake_url"
        assert ListIntakesTool.name == "vetka_list_intakes"
        print("✅ Test 37: Intake tools import correctly")
    except ImportError as e:
        print(f"⚠️ Test 37: Import issue: {e}")

def test_38_intake_result_format():
    """Test IntakeResult dataclass"""
    from src.intake.base import IntakeResult, ContentType
    
    result = IntakeResult(
        source_url="https://example.com",
        source_type="web",
        content_type=ContentType.ARTICLE,
        title="Test Article",
        text="This is test content"
    )
    
    data = result.to_dict()
    assert data["source_url"] == "https://example.com"
    assert data["content_type"] == "article"
    assert data["text_length"] == len("This is test content")
    
    print("✅ Test 38: IntakeResult format works")
```

## 📋 ШАГ 6: Структура модуля

```python
# src/intake/__init__.py
from .base import ContentIntake, IntakeResult, ContentType
from .youtube import YouTubeIntake
from .web import WebIntake
from .manager import IntakeManager, get_intake_manager
from .tools import IntakeURLTool, ListIntakesTool, GetIntakeTool

__all__ = [
    'ContentIntake', 'IntakeResult', 'ContentType',
    'YouTubeIntake', 'WebIntake',
    'IntakeManager', 'get_intake_manager',
    'IntakeURLTool', 'ListIntakesTool', 'GetIntakeTool'
]
```

## ✅ КРИТЕРИИ УСПЕХА

- [ ] YouTube: извлекает метаданные и субтитры (если есть)
- [ ] Web: извлекает текст статей через trafilatura
- [ ] MCP tools: vetka_intake_url, vetka_list_intakes, vetka_get_intake
- [ ] REST endpoints: /api/intake/process, /api/intake/list, /api/intake/<filename>
- [ ] 6 новых тестов (33-38)
- [ ] Файлы сохраняются в data/intake/

## 📁 НОВЫЕ ФАЙЛЫ

```
src/intake/           (NEW DIRECTORY)
├── __init__.py
├── base.py          (base classes)
├── youtube.py       (YouTube processor)
├── web.py           (web page processor)
├── manager.py       (intake manager)
└── tools.py         (MCP tools)

data/intake/         (NEW DIRECTORY)
└── youtube_*.json
└── web_*.json
```

## 🔄 ПОСЛЕ ЗАВЕРШЕНИЯ

1. Установи зависимости:
   ```bash
   pip install yt-dlp beautifulsoup4 trafilatura
   ```

2. Запусти тесты: `python tests/test_mcp_server.py`

3. Тест YouTube (без транскрипции):
   ```bash
   curl -X POST http://localhost:5001/api/intake/process \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
   ```

4. Тест веб-страницы:
   ```bash
   curl -X POST http://localhost:5001/api/intake/process \
     -H "Content-Type: application/json" \
     -d '{"url": "https://en.wikipedia.org/wiki/Knowledge_graph"}'
   ```

5. Список intakes:
   ```bash
   curl http://localhost:5001/api/intake/list
   ```

6. Сообщи результаты!
