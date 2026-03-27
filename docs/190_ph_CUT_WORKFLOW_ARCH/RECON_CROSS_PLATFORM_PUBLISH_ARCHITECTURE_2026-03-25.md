# RECON: Cross-Platform Publish Architecture
**Replaces:** FCP7 DVD Export (Ch.87-89)
**Author:** Epsilon (QA-2) + Sonnet research agent
**Date:** 2026-03-25
**Task:** tb_1774430825_1
**Status:** DRAFT — ready for implementation task creation

---

## 1. Context & Scope

FCP7's DVD Export pipeline (format selection → menu design → chapter markers → MPEG-2 encode → disc burn → batch) served physical distribution. In 2026 that maps 1:1 to social media cross-posting: format selection → thumbnail/cover design → timeline markers as chapters → platform-specific encode → API upload → batch queue.

File Export (ProRes/DNxHR/OTIO) is an enhanced variant of the same pipeline and shares the same encode worker.

---

## 2. File & Directory Layout

```
client/src/
  components/
    publish/
      PublishDialog.tsx            # root dialog, multi-step
      PublishPlatformCard.tsx      # per-platform collapsible section
      PublishPreviewCanvas.tsx     # aspect-ratio overlay preview
      PublishReframeControls.tsx   # center / ai-track / manual
      PublishMetadataForm.tsx      # title, description, tags
      PublishScheduler.tsx         # date-time picker
      PublishQueue.tsx             # live encode+upload status
      PublishAnalytics.tsx         # post-publish metrics table
      PlatformCheckbox.tsx         # platform selector row
  store/
    publishStore.ts                # Zustand slice
    publishSelectors.ts
  services/
    publish/
      encodeWorker.ts              # FFmpeg server-side encode job
      youtubeApi.ts
      instagramApi.ts
      tiktokApi.ts
      xApi.ts
      telegramApi.ts
      fileExportApi.ts
      publishOrchestrator.ts       # parallel encode, sequential upload
  types/
    publish.ts                     # all TypeScript interfaces
src/api/routes/
  cut_publish_routes.py            # FastAPI endpoints
tests/
  test_publish_store.py
  test_publish_encode.py
  test_publish_orchestrator.py
client/e2e/
  cut_publish_dialog.spec.cjs
  cut_publish_batch.spec.cjs
```

---

## 3. TypeScript Types

```typescript
// client/src/types/publish.ts

export type Platform =
  | 'youtube'
  | 'instagram'
  | 'tiktok'
  | 'x'
  | 'telegram'
  | 'file';

export type ReframeMode = 'center' | 'ai-track' | 'manual';

export type PublishJobStatus =
  | 'pending'
  | 'encoding'
  | 'uploading'
  | 'scheduled'
  | 'done'
  | 'error';

export interface PlatformConstraints {
  platform: Platform;
  codec: string[];
  aspectRatios: string[];
  maxDurationSeconds: number;
  maxFileSizeBytes: number;
  maxResolutionW: number;
  maxResolutionH: number;
  requiresAspectRatio?: string;
}

export interface PlatformMetadata {
  title: string;
  description: string;
  tags: string[];
  coverImageTimecode?: string;
  hashtags?: string[];
  location?: string;
  isShorts?: boolean;              // YouTube
  isDocument?: boolean;            // Telegram send as document
  scheduleAt?: Date | null;
}

export interface PlatformTarget {
  platform: Platform;
  enabled: boolean;
  authToken?: string;
  constraints: PlatformConstraints;
  metadata: PlatformMetadata;
  reframeMode: ReframeMode;
  reframeKeyframes?: ReframeKeyframe[];
  ffmpegPreset?: FFmpegPreset;
}

export interface ReframeKeyframe {
  timecodeSeconds: number;
  cropX: number;  // 0-1 normalised
  cropY: number;
  cropW: number;
  cropH: number;
}

export interface FFmpegPreset {
  codec: string;
  videoBitrate: string;
  audioBitrate: string;
  resolution: string;
  fps: number;
  extraFlags: string[];
}

export interface PublishJob {
  id: string;
  platform: Platform;
  status: PublishJobStatus;
  encodeProgress: number;
  uploadProgress: number;
  outputUrl?: string;
  errorMessage?: string;
  startedAt: Date;
  completedAt?: Date;
}

export interface PublishResult {
  jobId: string;
  platform: Platform;
  publishedUrl: string;
  publishedAt: Date;
  analytics?: PlatformAnalytics;
}

export interface PlatformAnalytics {
  platform: Platform;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  fetchedAt: Date;
}
```

---

## 4. Platform Constraints Registry

| Platform | Codec | Aspect Ratio | Max Duration | Max Resolution | Max File Size |
|----------|-------|-------------|-------------|---------------|--------------|
| YouTube | H.264, VP9, AV1 | 16:9, 9:16, 1:1 | 12h | 7680x4320 | unlimited |
| Instagram | H.264 | 9:16 (required) | 90s | 1080x1920 | ~4GB |
| TikTok | H.264 | 9:16 (required) | 10min | 1080x1920 | ~4GB |
| X/Twitter | H.264 | 16:9, 1:1, 9:16 | 2:20 (std) | 1920x1080 | 512MB |
| Telegram | H.264 | any | unlimited | unlimited | 2GB |
| File | ProRes/DNxHR/H.264/H.265/VP9/AV1 | any | unlimited | unlimited | unlimited |

---

## 5. Codec Matrix & FFmpeg Commands

### Key Templates

**YouTube H.264 1080p (`yt_h264_1080`)**
```bash
ffmpeg -i {INPUT} \
  -vf "{VFILTER},scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" \
  -c:v libx264 -preset slow -crf 18 -b:v 8M -maxrate 10M -bufsize 20M \
  -c:a aac -b:a 192k -ar 48000 -movflags +faststart -y {OUTPUT}
```

**Instagram/TikTok 9:16 (`ig_h264_reels` / `tt_h264`)**
```bash
ffmpeg -i {INPUT} \
  -vf "{VFILTER},scale=1080:1920,setsar=1" \
  -c:v libx264 -preset slow -crf 20 -b:v 6M -maxrate 8M -bufsize 16M \
  -c:a aac -b:a 128k -ar 44100 -movflags +faststart -t {MAX_DURATION} -y {OUTPUT}
```

**Center Crop 16:9 → 9:16 (VFILTER)**
```
crop=ih*9/16:ih:(iw-ih*9/16)/2:0
```

**ProRes 422 (`file_prores422`)**
```bash
ffmpeg -i {INPUT} -c:v prores_ks -profile:v 2 -c:a pcm_s16le -y {OUTPUT}
```

**X Standard (`x_h264_1080`)**
```bash
ffmpeg -i {INPUT} -vf "{VFILTER},scale=1920:1080" \
  -c:v libx264 -preset medium -b:v 5M -maxrate 6M -bufsize 12M \
  -c:a aac -b:a 128k -t 140 -movflags +faststart -fs 512M -y {OUTPUT}
```

---

## 6. Auto-Reframe Logic

### Center Crop (default)
Source 1920x1080 → 1080x1920: `crop=608:1080:656:0,scale=1080:1920,setsar=1`

### AI Subject Tracking
1. Run Apple Vision `VNDetectFaceRectanglesRequest` (macOS) or MediaPipe WASM fallback
2. Per-frame bounding boxes smoothed with Gaussian kernel (sigma=15 frames)
3. Crop center placed at smoothed subject centroid, clamped to frame edges
4. Output: `ReframeKeyframe[]` array, persisted for user review/adjustment

### Manual Keyframed Crop
User scrubs timeline in preview canvas, drags crop rectangle at keyframe points. Linear interpolation between keyframes generates per-frame crop params for FFmpeg.

---

## 7. Publish Dialog UI

```
PublishDialog (data-testid="publish-dialog")
├── PlatformSelector (data-testid="platform-selector")
│   ├── PlatformCheckbox (data-testid="platform-checkbox-{platform}")  x6
├── GlobalMetadataForm (data-testid="global-metadata-form")
│   ├── Input (data-testid="global-title-input")
│   ├── Textarea (data-testid="global-description-input")
│   └── TagInput (data-testid="global-tags-input")
├── PlatformSections
│   └── PublishPlatformCard (data-testid="platform-card-{platform}")
│       ├── PublishPreviewCanvas (data-testid="preview-canvas-{platform}")
│       ├── PublishReframeControls (data-testid="reframe-controls-{platform}")
│       ├── DurationWarning (data-testid="duration-warning-{platform}")
│       └── PublishMetadataForm (data-testid="metadata-form-{platform}")
├── PublishScheduler (data-testid="publish-scheduler")
├── Button "Publish" (data-testid="publish-submit-btn")
└── PublishQueue (data-testid="publish-queue")
    └── PublishJobRow (data-testid="publish-job-row-{jobId}")
```

### Monochrome Rules
- Backgrounds: `#1a1a1a`, `#222222`, `#2a2a2a`
- Text: `#e0e0e0` (primary), `#aaaaaa` (secondary)
- Borders: `#404040`
- Progress bars: `#555555` fill on `#333333` track
- Platform logos: white monochrome SVGs only

---

## 8. API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/cut/publish/prepare | Encode for selected platforms (returns job IDs) |
| POST | /api/cut/publish/upload/{platform} | Upload to specific platform |
| GET | /api/cut/publish/status | Batch status of all publish jobs |
| POST | /api/cut/publish/schedule | Schedule future publish |
| GET | /api/cut/publish/history | Past publishes with analytics |

---

## 9. Batch Pattern (from FCP7)

One timeline → select N platforms → one click → N encodes (parallel) → N uploads (sequential per API rate limits) → unified status dashboard.

Orchestrator flow:
1. `POST /api/cut/publish/prepare` — kicks off all encodes in parallel
2. Poll `/status` every 2s until all encodes complete
3. Upload sequentially per platform (respect API rate limits)
4. Error in one upload does not abort others

---

## 10. Chapters from Timeline Markers

Timeline markers with `type: 'chapter'` → YouTube description chapters:
```
00:00 Intro
01:23 Main Topic
05:45 Conclusion
```
Auto-prepend `00:00` if missing. Requires minimum 3 chapters (YouTube rule).

---

## 11. Analytics Dashboard

Post-publish metrics table. Pull on explicit "Refresh" click only.

| Platform | API for Metrics | Available Fields |
|----------|----------------|-----------------|
| YouTube | `videos?part=statistics` | views, likes, comments |
| Instagram | `/{mediaId}/insights` | views, likes, comments, shares |
| TikTok | `/video/query` | view_count, like_count, comment_count, share_count |
| X | `/tweets/{id}?tweet.fields=public_metrics` | impressions, likes, replies, retweets |
| Telegram | N/A | no public API for bot messages |

---

## 12. Menu Integration

```
File
├── Publish...   Cmd+Shift+P    (data-testid="menu-publish")
└── Export...    Cmd+E          (data-testid="menu-export")
```

---

## 13. FCP7 Mapping Summary

| FCP7 DVD Export | CUT Cross-Platform Publish |
|---|---|
| Format selection dialog | Platform checkboxes + codec matrix |
| DVD menu design | Thumbnail/cover image picker per platform |
| Chapter markers | Timeline markers → YouTube chapters |
| MPEG-2 encoding | FFmpeg per-platform encode (H.264/VP9/ProRes) |
| Disc burn | API upload (YouTube/IG/TikTok/X/Telegram) |
| Batch export | Parallel encode → sequential upload queue |

---

## 14. Implementation Tasks (for dispatch)

| # | Task | Agent | Priority | Complexity |
|---|------|-------|----------|-----------|
| 1 | PublishDialog + PlatformCheckbox + GlobalMetadata UI | Gamma | P2 | Medium |
| 2 | PublishStore (Zustand) + types | Alpha | P2 | Low |
| 3 | FFmpeg encode worker + codec matrix presets | Beta | P2 | High |
| 4 | YouTube API integration (OAuth + resumable upload) | Beta | P2 | High |
| 5 | Instagram/TikTok/X/Telegram API integrations | Beta | P3 | Medium each |
| 6 | Auto-reframe (center crop + AI tracking) | Beta | P3 | High |
| 7 | PublishQueue + status polling UI | Gamma | P2 | Low |
| 8 | Analytics dashboard UI | Gamma | P3 | Low |
| 9 | Chapter markers → YouTube chapters mapper | Alpha | P2 | Low |
| 10 | E2E tests for publish flow | Epsilon | P2 | Medium |
