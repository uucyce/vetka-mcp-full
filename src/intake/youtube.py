"""
YouTube content intake using yt-dlp.

Extracts video metadata and transcripts from YouTube URLs.
Supports automatic subtitles and Whisper transcription fallback.

@status: active
@phase: 96
@depends: base, asyncio, json, re, tempfile, pathlib
@used_by: manager, src.intake
"""
import asyncio
import json
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import ContentIntake, IntakeResult, ContentType


class YouTubeIntake(ContentIntake):
    """Process YouTube videos - extract metadata and transcript"""

    @property
    def source_type(self) -> str:
        return "youtube"

    @property
    def supported_patterns(self) -> List[str]:
        return [
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
            tags=metadata.get("tags", [])[:10] if metadata.get("tags") else []
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
        if not video_id:
            return None

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
                for lang in ["en", "ru"]:
                    sub_file = Path(tmpdir) / f"{video_id}.{lang}.vtt"
                    if sub_file.exists():
                        return self._parse_vtt(sub_file.read_text())

                # Try auto-generated
                for f in Path(tmpdir).glob("*.vtt"):
                    return self._parse_vtt(f.read_text())

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
        if not video_id:
            return None

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / f"{video_id}.mp3"

            # Download audio only
            cmd = [
                "yt-dlp",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "5",  # Lower quality for faster processing
                "-o", str(audio_path.with_suffix('')),  # yt-dlp adds extension
                url
            ]

            try:
                result = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()

                # Find the audio file
                audio_files = list(Path(tmpdir).glob("*.mp3"))
                if not audio_files:
                    return None

                audio_path = audio_files[0]

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

        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()

            txt_path = audio_path.with_suffix('.txt')
            if txt_path.exists():
                return txt_path.read_text()
        except Exception:
            pass
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
        except Exception:
            return None
