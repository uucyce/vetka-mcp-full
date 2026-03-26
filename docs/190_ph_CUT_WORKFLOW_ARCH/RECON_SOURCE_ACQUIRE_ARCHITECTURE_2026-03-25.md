# RECON: Source Acquire Architecture
**Replaces:** FCP7 Log & Capture (Ch.14-15)
**Author:** Epsilon (QA-2) + Sonnet research agent
**Date:** 2026-03-25
**Task:** tb_1774430815_1
**Status:** DRAFT — ready for implementation task creation

---

## 1. Overview

The Source Acquire panel is the modern equivalent of FCP7's Log & Capture workflow. Where FCP7 captured from tape decks via serial timecode, Source Acquire handles four modern ingest pathways: web video fetching, local AI generation, remote AI generation, and enhanced local import.

The panel maintains FCP7's core mental model — preview before commit, mark in/out segments, batch queue, import to project — while adapting to async network operations and generative workflows.

Accessible via **Cmd+8** (mirroring FCP7's Cmd+8 for Log & Capture).

---

## 2. File Structure

```
client/src/
  components/panels/SourceAcquirePanel/
    index.tsx                          — panel root, tab routing
    tabs/
      YouTubeFetchTab.tsx
      AILocalTab.tsx
      AIRemoteTab.tsx
      LocalImportTab.tsx
    components/
      AcquireQueue.tsx                 — shared queue widget
      SegmentMarker.tsx               — I/O mark widget
      PreviewPlayer.tsx               — embedded preview
      MetadataFields.tsx              — read-only metadata
      CostTracker.tsx                 — remote AI credits
      TranscodeProgress.tsx           — proxy transcode progress
    hooks/
      useYouTubeFetch.ts
      useAILocalGenerate.ts
      useAIRemoteGenerate.ts
      useLocalImport.ts
      useAcquireQueue.ts
  store/
    sourceAcquireStore.ts
  types/
    sourceAcquire.ts
src/api/routes/
  cut_acquire_routes.py               — FastAPI router
src/services/
  youtube_service.py                  — yt-dlp wrapper, oEmbed
  ai_local_service.py                 — Stable Diffusion / Whisper TTS
  ai_remote_service.py                — Runway/Sora/Kling API clients
  import_service.py                   — FFmpeg metadata, scene detect
  dag_import_service.py               — MediaNode creation
```

---

## 3. Source Types & State Machine

### Universal State Machine

```
idle → configuring → [fetching|generating|importing] → previewing → accepted → importing_to_dag → done
                                                           ↓
                                                      rejected → idle
                          ↓ (cancel/error)
                     cancelled/failed → configuring (retry)
```

### 3.1 YouTube Fetch
- URL input → oEmbed preview → I/O segment marking → batch download → preview → accept → DAG
- Uses yt-dlp for download, YouTube IFrame API for preview/time queries
- Quality selection: best / 1080p / 720p / 480p / audio-only

### 3.2 Local AI Generation
- Prompt input + params → Stable Diffusion / Whisper TTS → progressive preview → accept/reject
- Images: ComfyUI or Automatic1111 WebUI API
- Audio: Coqui TTS or Whisper TTS CLI

### 3.3 Remote AI Generation
- Provider select (Runway/Sora/Kling) → prompt + optional reference frame → async generation → preview → accept/reject
- API key management, cost tracking, credits balance display
- Polling status every 5s

### 3.4 Enhanced Local Import
- Batch drag-and-drop → auto metadata extraction (FFmpeg/FFprobe) → optional proxy transcode → optional scene detection → import to DAG

---

## 4. TypeScript Types

```typescript
export type AcquireTab = 'youtube' | 'ai-local' | 'ai-remote' | 'import';

export type AcquireJobStatus =
  | 'idle' | 'configuring' | 'fetching' | 'generating'
  | 'previewing' | 'accepted' | 'importing_to_dag'
  | 'rejected' | 'failed' | 'cancelled';

export type RemoteProvider = 'runway' | 'sora' | 'kling';
export type VideoQuality = 'best' | '1080p' | '720p' | '480p' | 'audio-only';

export interface YouTubeMetadata {
  videoId: string;
  title: string;
  description: string;
  channelName: string;
  durationSeconds: number;
  thumbnailUrl: string;
  tags: string[];
  oEmbedHtml: string;
}

export interface YouTubeSegment {
  id: string;
  inTime: number;
  outTime: number;
  label: string;
}

export interface GenerationParams {
  steps: number;
  cfgScale: number;
  seed: number;
  width: number;
  height: number;
  model: string;
  sampler: string;
  negativePrompt: string;
}

export interface TTSParams {
  voice: string;
  speed: number;
  pitch: number;
  outputFormat: 'wav' | 'mp3' | 'flac';
}

export interface AcquireJob {
  id: string;
  type: 'youtube' | 'ai-local' | 'ai-remote' | 'import';
  status: AcquireJobStatus;
  label: string;
  progress: number;
  outputFilePath: string | null;
  outputPreviewUrl: string | null;
  dagNodeId: string | null;
  // source-specific metadata fields...
}

export interface AcquireSourceMeta {
  sourceType: 'youtube' | 'ai_generated_local' | 'ai_generated_remote' | 'local_import';
  originalUrl: string | null;
  prompt: string | null;
  generationParams: GenerationParams | null;
  remoteProvider: RemoteProvider | null;
  youtubeVideoId: string | null;
  youtubeSegmentIn: number | null;
  youtubeSegmentOut: number | null;
  acquireJobId: string;
  acquiredAt: number;
}
```

---

## 5. Panel Layout

```
+------------------------------------------+
| SOURCE ACQUIRE              [x] [detach]  |  32px header
+--[YOUTUBE]--[AI LOCAL]--[AI REMOTE]--[IMPORT]--+  36px tab bar
|                                            |
|  [tab-specific content area]               |  flex-grow, scrollable
|                                            |
+--------------------------------------------+
|  ACQUIRE QUEUE  [N pending]  [Clear done]  |  collapsible footer
|  [job row]                                 |
|  [job row]                                 |
+--------------------------------------------+
```

### data-testid Convention
- Panel: `source-acquire-panel`
- Tabs: `acquire-tab-youtube`, `acquire-tab-ai-local`, `acquire-tab-ai-remote`, `acquire-tab-import`
- YouTube: `youtube-url-input`, `youtube-fetch-metadata-btn`, `youtube-preview-embed`, `youtube-segments-list`, `youtube-download-btn`
- AI Local: `ai-local-prompt-input`, `ai-local-generate-btn`, `ai-local-accept-btn`, `ai-local-reject-btn`
- AI Remote: `ai-remote-provider-select`, `ai-remote-prompt-input`, `ai-remote-submit-btn`, `ai-remote-accept-btn`
- Import: `import-drop-zone`, `import-all-btn`
- Queue: `acquire-queue-section`, `acquire-job-row-{id}`

### Monochrome Rules (absolute)
- Panel bg: `#1a1a1a`, Tab bg: `#222222`, Active tab: `#2d2d2d`
- Input bg: `#2a2a2a`, Input border: `#3a3a3a`, Focus border: `#666666`
- Progress bar: `#888888` fill on `#333333` track
- No color accents. Error = italic grey text. Success = grey checkmark.

---

## 6. API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/cut/acquire/youtube/metadata | Fetch oEmbed + Data API metadata |
| POST | /api/cut/acquire/youtube/download | Start download job (returns job_id) |
| GET | /api/cut/acquire/events/{job_id} | SSE progress stream |
| POST | /api/cut/acquire/ai/local/generate | Start local AI generation |
| POST | /api/cut/acquire/ai/remote/submit | Submit remote AI job |
| GET | /api/cut/acquire/ai/remote/status/{job_id} | Poll remote status |
| GET | /api/cut/acquire/queue | List all jobs |
| DELETE | /api/cut/acquire/queue/{job_id} | Cancel job |
| POST | /api/cut/acquire/accept/{job_id} | Accept + import to DAG |
| POST | /api/cut/acquire/import/local | Start local file import |
| GET | /api/cut/acquire/ai/local/models | List SD model checkpoints |

---

## 7. Hotkey Mappings

| Key | Action | Context |
|-----|--------|---------|
| I | Mark In | YouTube: marks inTime at current preview time |
| O | Mark Out | YouTube: marks outTime |
| Space | Play/Pause | Preview player in any tab |
| Escape | Cancel operation | Cancels active fetch/generate |
| Return | Accept preview | Accepts when in previewing state |
| Delete | Reject preview | Rejects when in previewing state |
| Cmd+Enter | Submit/Download | Triggers primary action of active tab |
| Cmd+8 | Open Source Acquire | Global — mirrors FCP7 Cmd+8 |

Hotkeys only fire when panel has focus. I/O suppressed when typing in input/textarea fields.

---

## 8. DAG Integration

Each acquired source becomes a DAG MediaNode with `acquireMeta` field preserving:
- Source type, original URL, prompt, generation params
- YouTube video ID + segment In/Out for re-download
- Remote provider + job ID for audit trail
- Seed + model version for AI reproducibility

---

## 9. Remote AI Provider Abstraction

```python
class RemoteAIProvider(Protocol):
    async def submit(self, request) -> str:          # returns provider_job_id
    async def poll_status(self, job_id) -> dict:     # progress, output_url
    async def cancel(self, job_id) -> bool:
    async def get_credits_balance(self) -> int | None:

# Implementations: RunwayProvider, KlingProvider, SoraProvider
# Initialized at startup if API key present in environment
```

---

## 10. Backend Worker Architecture

In-memory asyncio workers for MVP. Each job type runs as asyncio.create_task:
- YouTube: yt-dlp subprocess with stderr progress parsing
- AI Local: POST to SD WebUI API + progress polling
- AI Remote: submit + periodic status polling
- Import: ffprobe + optional ffmpeg proxy + optional scene detect

SSE events streamed per-job for real-time progress.

---

## 11. Implementation Tasks (for dispatch)

| # | Task | Agent | Priority | Complexity |
|---|------|-------|----------|-----------|
| 1 | SourceAcquirePanel shell + tab routing + store | Alpha | P2 | Medium |
| 2 | YouTubeFetchTab + yt-dlp service + oEmbed preview | Beta | P2 | High |
| 3 | AILocalTab + SD WebUI integration | Beta | P3 | High |
| 4 | AIRemoteTab + provider abstraction (Runway/Kling/Sora) | Beta | P3 | High |
| 5 | LocalImportTab + enhanced metadata/proxy/scene detect | Beta | P2 | Medium |
| 6 | AcquireQueue widget + SSE progress hook | Gamma | P2 | Low |
| 7 | DAG import service (create MediaNode from job) | Alpha | P2 | Medium |
| 8 | Hotkey registration (I/O/Space/Escape/Return) | Alpha | P2 | Low |
| 9 | E2E tests for Source Acquire flow | Epsilon | P3 | Medium |

---

## 12. Open Questions

1. **SD video generation** — AnimateDiff vs SVD vs ComfyUI. Stub for MVP.
2. **Sora API** — limited beta. Gate behind `SORA_ENABLED=true` env flag.
3. **YouTube API key** — optional. oEmbed works without key. Duration via yt-dlp fallback.
4. **Queue persistence** — in-memory for MVP. SQLite for production.
5. **Reference frame export** — needs Source Monitor `captureFrame()` API (coordinate with Alpha).
6. **Proxy storage** — `{project_dir}/.cut/proxies/`, excluded from version control.
