# Phase 22-MCP-5: Universal Content Intake

**Date:** 2024-12-30
**Status:** COMPLETE
**Tests:** 38/38 passed

---

## Overview

Phase 22-MCP-5 implements a universal content intake system for VETKA. This enables:
1. YouTube video processing (metadata + subtitles/transcripts)
2. Web page article extraction
3. Unified storage and retrieval of processed content

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/intake/__init__.py` | 36 | Module exports |
| `src/intake/base.py` | 77 | Base classes: ContentIntake, IntakeResult, ContentType |
| `src/intake/youtube.py` | 193 | YouTube processor (yt-dlp + whisper) |
| `src/intake/web.py` | 97 | Web page processor (trafilatura + bs4) |
| `src/intake/manager.py` | 131 | IntakeManager singleton |
| `src/intake/tools.py` | 116 | 3 MCP tools for intake |

## Files Modified

| File | Changes |
|------|---------|
| `main.py` | +4 REST endpoints for content intake |
| `tests/test_mcp_server.py` | +6 tests (33-38) |

---

## Dependencies Installed

```bash
pip install yt-dlp beautifulsoup4 trafilatura
```

| Package | Version | Purpose |
|---------|---------|---------|
| `yt-dlp` | 2025.12.8 | YouTube download & metadata |
| `beautifulsoup4` | 4.14.3 | HTML parsing fallback |
| `trafilatura` | 2.0.0 | Article text extraction |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    IntakeManager                            │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ YouTubeIntake   │  │ WebIntake       │  ... (extensible) │
│  │ - metadata      │  │ - trafilatura   │                   │
│  │ - subtitles     │  │ - bs4 fallback  │                   │
│  │ - transcription │  │                 │                   │
│  └─────────────────┘  └─────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    IntakeResult                             │
│  - source_url, source_type, content_type                    │
│  - title, text, metadata                                    │
│  - author, published_at, duration_seconds                   │
│  - language, tags                                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                data/intake/*.json                           │
│  youtube_abc123_20241230_120000.json                        │
│  web_def456_20241230_120500.json                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. Base Classes (`base.py`)

```python
from src.intake import ContentType, IntakeResult, ContentIntake

# Content types
ContentType.VIDEO    # video
ContentType.AUDIO    # audio
ContentType.ARTICLE  # article
ContentType.POST     # post
ContentType.DOCUMENT # document
ContentType.IMAGE    # image

# Result dataclass
result = IntakeResult(
    source_url="https://...",
    source_type="youtube",
    content_type=ContentType.VIDEO,
    title="Video Title",
    text="Transcript...",
    metadata={...},
    author="Channel Name",
    duration_seconds=300
)

# Serialize
data = result.to_dict()
```

### 2. YouTube Processor (`youtube.py`)

Extracts metadata and subtitles/transcripts from YouTube videos.

```python
from src.intake import YouTubeIntake

intake = YouTubeIntake(whisper_model="base", use_api=False)

# Check if URL is supported
intake.can_process("https://youtube.com/watch?v=abc")  # True

# Process video
result = await intake.process(url, options={"transcribe": False})
```

**Features:**
- URL patterns: `youtube.com/watch`, `youtu.be/`, `youtube.com/shorts/`
- Metadata extraction via `yt-dlp --dump-json`
- Auto-subtitles (en, ru) via `yt-dlp --write-auto-sub`
- Optional Whisper transcription for videos without subtitles

**Extracted Data:**
- `video_id`, `channel`, `channel_id`
- `view_count`, `like_count`, `thumbnail`
- `description` (first 500 chars)
- `duration`, `language`, `tags`
- `text` - full subtitle/transcript

### 3. Web Page Processor (`web.py`)

Extracts article text from web pages.

```python
from src.intake import WebIntake

intake = WebIntake()

# Process any non-video URL
result = await intake.process("https://example.com/article")
```

**Features:**
- Primary: `trafilatura` (best for articles)
- Fallback: `BeautifulSoup` (for complex pages)
- Excluded platforms: youtube, youtu.be, t.me, twitter, x.com

**Extracted Data:**
- `title`, `author`, `language`
- `sitename`, `hostname`, `categories`
- `published_at`, `tags`
- `text` - clean article text (up to 50KB)

### 4. Intake Manager (`manager.py`)

Singleton manager for URL processing.

```python
from src.intake import get_intake_manager

manager = get_intake_manager()

# Process single URL
result = await manager.process_url(url, options={"transcribe": False})

# Process batch
results = await manager.process_batch(urls, options)

# List recent intakes
intakes = manager.list_intakes(source_type="youtube", limit=20)

# Get specific intake
intake = manager.get_intake("youtube_abc123_20241230.json")

# Delete intake
manager.delete_intake("youtube_abc123_20241230.json")
```

**Storage:**
- Files saved to `data/intake/`
- Naming: `{source_type}_{url_hash}_{timestamp}.json`
- Path traversal protection on get/delete

---

## MCP Tools

### 1. vetka_intake_url

Process URL and extract content.

```json
{
  "name": "vetka_intake_url",
  "arguments": {
    "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "transcribe": false
  }
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "source_type": "youtube",
    "title": "Rick Astley - Never Gonna Give You Up",
    "text_preview": "We're no strangers to love...",
    "text_length": 2500,
    "author": "Rick Astley",
    "duration_seconds": 213,
    "metadata": {...}
  }
}
```

### 2. vetka_list_intakes

List processed intakes.

```json
{
  "name": "vetka_list_intakes",
  "arguments": {
    "source_type": "youtube",
    "limit": 10
  }
}
```

### 3. vetka_get_intake

Get full intake content.

```json
{
  "name": "vetka_get_intake",
  "arguments": {
    "filename": "youtube_abc123_20241230.json"
  }
}
```

---

## REST API Endpoints

### Process URL
```http
POST /api/intake/process
Content-Type: application/json

{
  "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
  "transcribe": false
}
```

**Response:**
```json
{
  "success": true,
  "source_type": "youtube",
  "title": "Video Title",
  "text_preview": "First 2000 chars...",
  "text_length": 5000,
  "author": "Channel",
  "duration_seconds": 300,
  "metadata": {...}
}
```

### List Intakes
```http
GET /api/intake/list?source_type=youtube&limit=20
```

### Get Intake
```http
GET /api/intake/<filename>
```

### Delete Intake
```http
DELETE /api/intake/<filename>
```

---

## Tests Added (33-38)

| # | Test | Description |
|---|------|-------------|
| 33 | `test_youtube_intake_patterns` | YouTube URL pattern matching |
| 34 | `test_web_intake_patterns` | Web URL pattern matching (excludes video platforms) |
| 35 | `test_intake_manager_processor_selection` | Manager selects correct processor |
| 36 | `test_intake_result_format` | IntakeResult serialization |
| 37 | `test_intake_tools_schema` | MCP tools have valid schemas |
| 38 | `test_intake_manager_list` | List/get/delete operations |

---

## Usage Examples

### YouTube Video
```bash
curl -X POST http://localhost:5001/api/intake/process \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

### Web Article
```bash
curl -X POST http://localhost:5001/api/intake/process \
  -H "Content-Type: application/json" \
  -d '{"url": "https://en.wikipedia.org/wiki/Knowledge_graph"}'
```

### List All Intakes
```bash
curl http://localhost:5001/api/intake/list
```

### Get Specific Intake
```bash
curl http://localhost:5001/api/intake/youtube_abc123_20241230.json
```

---

## Data Directory

```
data/
└── intake/                    # Processed content
    ├── youtube_abc123_20241230_120000.json
    ├── youtube_def456_20241230_120500.json
    ├── web_ghi789_20241230_121000.json
    └── ...
```

---

## Extensibility

To add a new content source:

1. Create processor class inheriting from `ContentIntake`:

```python
class TelegramIntake(ContentIntake):
    @property
    def source_type(self) -> str:
        return "telegram"

    @property
    def supported_patterns(self) -> List[str]:
        return [r"t\.me/"]

    def can_process(self, url: str) -> bool:
        return any(re.search(p, url) for p in self.supported_patterns)

    async def process(self, url: str, options: Dict = None) -> IntakeResult:
        # Implementation
        ...
```

2. Register in `IntakeManager.__init__`:

```python
self.processors = [
    YouTubeIntake(),
    TelegramIntake(),  # NEW
    WebIntake(),       # Keep last (catches all)
]
```

---

## Summary

Phase 22-MCP-5 adds universal content intake to VETKA:

- **YouTube**: Full metadata + subtitles extraction via yt-dlp
- **Web Pages**: Clean article text via trafilatura
- **Storage**: JSON files with searchable metadata
- **API**: REST endpoints + MCP tools
- **Extensible**: Easy to add new sources (Telegram, etc.)

All 38 tests pass. VETKA can now ingest and process content from YouTube videos and web articles.

---

## Next Steps (Potential)

1. **Telegram Intake**: Add channel/chat message extraction
2. **PDF Intake**: Document text extraction
3. **Audio Intake**: Podcast transcription
4. **Image Intake**: OCR + description
5. **Batch Processing**: UI for bulk URL import
6. **Knowledge Integration**: Auto-add intakes to VETKA tree
