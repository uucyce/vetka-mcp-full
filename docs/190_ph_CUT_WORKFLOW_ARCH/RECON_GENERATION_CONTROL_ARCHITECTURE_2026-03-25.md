# RECON: Generation Control Architecture
**Replaces:** FCP7 Deck Control (Ch.50-51)
**Author:** Epsilon (QA-2) + Sonnet research agent
**Date:** 2026-03-25
**Task:** tb_1774430835_1
**Status:** DRAFT — ready for implementation task creation

---

## 1. Executive Summary

FCP7's Deck Control is a state machine for commanding external VTR hardware. CUT's Generation Control mirrors this exact architectural pattern, substituting AI generation APIs for VTR hardware.

| FCP7 Deck Control | CUT Generation Control |
|---|---|
| Serial/RS-422 device connection | REST/WebSocket API key validation |
| Device presets (deck model, timecode) | Provider presets (model version, resolution, duration) |
| Timecode display (HH:MM:SS:FF) | Job progress (%, ETA, cost) |
| Record → capture tape to disk | Generate → call AI API, poll, download |
| Batch Capture list | Generation Queue |
| Log and Capture window | Provider Settings panel |
| Accept clip into Bin | Accept job → import GeneratedMediaNode into DAG |

---

## 2. File Layout

### Frontend
```
client/src/
  store/useGenerationControlStore.ts        # Zustand store (MARKER_GEN-STORE)
  components/cut/
    GenerationControlPanel.tsx              # Root panel (MARKER_GEN-PANEL)
    GenerationTransportBar.tsx             # Transport controls (MARKER_GEN-TRANSPORT)
    GenerationQueueList.tsx                # Batch queue (MARKER_GEN-QUEUE)
    GenerationProviderSettings.tsx         # Device settings equiv (MARKER_GEN-SETTINGS)
    GenerationPreviewThumb.tsx             # Preview in PREVIEWING state
    GenerationPromptInput.tsx              # Prompt + params
    GenerationCostBadge.tsx                # Cost display
  panels/GenerationControlPanelDock.tsx    # Dockview wrapper (MARKER_GEN-DOCK)
  config/generation.config.ts              # Provider metadata (MARKER_GEN-CONFIG)
  hooks/
    useGenerationPolling.ts                # SSE/polling hook
    useGenerationHotkeys.ts                # Transport hotkeys
```

### Backend
```
src/api/routes/cut_routes_generation.py     # /api/cut/generate/* endpoints
src/services/
  cut_generation_service.py                # Orchestration: submit, poll, cancel
  cut_generation_providers/
    base_provider.py                       # Abstract base class
    runway_provider.py                     # Runway Gen-3 Alpha Turbo
    sora_provider.py                       # OpenAI Sora
    kling_provider.py                      # Kling
    flux_provider.py                       # FLUX.1 via ComfyUI
    sdxl_provider.py                       # SDXL via A1111/ComfyUI
    suno_provider.py                       # Suno music
    udio_provider.py                       # Udio music
    elevenlabs_provider.py                 # ElevenLabs TTS
    realesrgan_provider.py                 # Real-ESRGAN upscale
    topaz_provider.py                      # Topaz Video AI CLI
  cut_generation_job_store.py              # In-memory job registry
  cut_generation_budget.py                 # Spend tracking + alerts
```

---

## 3. Formal State Machine

```
DISCONNECTED → CONNECTING → IDLE → CONFIGURING → QUEUED → GENERATING → PREVIEWING → ACCEPTED → IMPORTING → IDLE
                                       ↓              ↓                    ↓
                                    IDLE          CANCELLED            REJECTED → CONFIGURING
                                                                     (prompt preserved)
```

### State Entry Actions

| State | Entry Actions |
|---|---|
| DISCONNECTED | Clear job context. Show "No Provider Connected". Disable transport. |
| CONNECTING | Show spinner. POST /test-connection. |
| IDLE | Clear progress/preview. Enable prompt input. Show queue. |
| CONFIGURING | Enable param controls. Show live cost estimate (debounced 500ms). |
| QUEUED | Add job to queue. Show position badge. Disable prompt. |
| GENERATING | Start polling (2s interval). Show progress bar. Enable Cancel (K). |
| PREVIEWING | Set preview URL. Enable Space/Escape/Enter. Show accept/reject. |
| ACCEPTED | Flash confirmation. Trigger import. |
| IMPORTING | Call /accept/{job_id}. Add GeneratedMediaNode to DAG. |
| REJECTED | Restore prompt+params. Auto-transition to CONFIGURING. |

---

## 4. Transport Controls (FCP7 Deck → AI Generation)

| FCP7 Deck | Generation Control | Hotkey | Condition |
|---|---|---|---|
| Play | Preview result | Space | PREVIEWING |
| Stop | Cancel generation | K | GENERATING/QUEUED |
| Record | Start generation | Cmd+R | IDLE/CONFIGURING + non-empty prompt |
| FF | Next completed job | L | IDLE/PREVIEWING |
| RW | Previous completed job | J | IDLE/PREVIEWING |
| Eject | Reject result | Escape | PREVIEWING |
| — | Accept → import to DAG | Enter | PREVIEWING |
| — | Capture reference frame | Cmd+F | IDLE/CONFIGURING |
| — | Provider settings | Cmd+, | any |

---

## 5. Generation Providers (10 total)

### Video
| Provider | API | Cost | Local |
|----------|-----|------|-------|
| Runway Gen-3 | REST, async poll | ~$0.50/gen | No |
| Sora | OpenAI API | ~$1.00/gen | No |
| Kling | REST, async poll | ~$0.35/gen | No |

### Image
| Provider | API | Cost | Local |
|----------|-----|------|-------|
| FLUX.1 | ComfyUI HTTP queue | Free | Yes |
| SDXL | A1111/ComfyUI API | Free | Yes |

### Audio
| Provider | API | Cost | Local |
|----------|-----|------|-------|
| Suno | REST | ~$0.10/gen | No |
| Udio | REST | ~$0.10/gen | No |
| ElevenLabs | REST TTS | ~$0.0003/char | No |

### Enhancement
| Provider | API | Cost | Local |
|----------|-----|------|-------|
| Real-ESRGAN | CLI subprocess | Free | Yes |
| Topaz Video AI | CLI interface | Free | Yes |

---

## 6. TypeScript Types (Key Interfaces)

```typescript
export type ProviderId =
  | 'runway' | 'sora' | 'kling' | 'flux' | 'sdxl'
  | 'suno' | 'udio' | 'elevenlabs' | 'realesrgan' | 'topaz';

export type GenerationState =
  | 'DISCONNECTED' | 'CONNECTING' | 'IDLE' | 'CONFIGURING'
  | 'QUEUED' | 'GENERATING' | 'PREVIEWING' | 'ACCEPTED'
  | 'IMPORTING' | 'CANCELLED' | 'REJECTED';

export interface GenerationJob {
  job_id: string;
  provider: ProviderId;
  prompt: string;
  params: Record<string, unknown>;
  reference_frame_source?: string;
  status: 'queued' | 'generating' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  cost_estimate: number;
  cost_actual?: number;
  result_url?: string;
  result_path?: string;
  seed?: number;
  model_version: string;
  created_at: number;
}

export interface GeneratedMediaNode {
  type: 'generated_media';
  node_id: string;
  provider: ProviderId;
  prompt: string;
  params: Record<string, unknown>;
  cost: number;
  generation_time_ms: number;
  seed?: number;
  model_version: string;
  file_path: string;
  duration: number;
  resolution: { w: number; h: number };
  codec: string;
}

export interface BudgetState {
  dailySpend: number;
  monthlySpend: number;
  budgetLimit: number;
  monthlyBudgetLimit: number;
  alertThreshold: number;  // default 0.8
}
```

---

## 7. API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/cut/generate/submit | Submit generation job |
| GET | /api/cut/generate/status/{job_id} | Poll job status |
| POST | /api/cut/generate/cancel/{job_id} | Cancel job |
| POST | /api/cut/generate/accept/{job_id} | Accept + import to DAG |
| POST | /api/cut/generate/reject/{job_id} | Reject result |
| GET | /api/cut/generate/queue | List all jobs |
| GET | /api/cut/generate/history | Completed jobs |
| GET | /api/cut/generate/providers | List configured providers |
| POST | /api/cut/generate/test-connection | Test provider API key |
| GET | /api/cut/generate/budget | Current spend tracking |

### Budget Guard
Submit endpoint checks budget before accepting: if `daily_spend + cost_estimate > daily_limit`, returns HTTP 402.

---

## 8. UI Component Tree

```
GenerationControlPanelDock (data-testid="cut-panel-generation")
  GenerationControlPanel (data-testid="gen-panel-root")
    TabBar: [generate] [queue] [settings]
    ProviderStatusBar (data-testid="gen-provider-status")
    --- generate tab ---
    PromptInput (data-testid="gen-prompt-textarea")
    ReferenceFrameCapture (data-testid="gen-ref-frame-btn")
    ParamGrid (data-testid="gen-param-grid")
    CostBadge (data-testid="gen-cost-badge")
    ProgressBar (data-testid="gen-progress-bar")
    PreviewThumb (data-testid="gen-preview-thumb")
    TransportBar (data-testid="gen-transport-bar")
    --- queue tab ---
    QueueList (data-testid="gen-queue-list")
      QueueJob (data-testid="gen-queue-job-{job_id}")
    --- settings tab ---
    ProviderSettings (data-testid="gen-settings-root")
      ProviderRow (data-testid="gen-settings-provider-{id}")
      BudgetSection (data-testid="gen-settings-budget")
```

### Monochrome Rules
- Background: `#0a0a0a` (panel), `#1a1a1a` (interactive)
- Text: `#ffffff` primary, `#ccc` secondary, `#888` disabled
- Progress bar: `#ffffff` fill on `#1a1a1a` track
- Provider status: `#888` = disconnected, `#fff` = connected
- Generated media previews can be full color (content, not UI chrome)
- Cost badge: white text only, no green/red color

---

## 9. Backend Provider Abstraction

```python
class BaseGenerationProvider(ABC):
    @abstractmethod
    async def test_connection(self, api_key, base_url, local_path) -> tuple[bool, str]: ...
    @abstractmethod
    async def estimate_cost(self, params) -> float: ...
    @abstractmethod
    async def submit(self, prompt, params, api_key, reference_frame_path) -> str: ...
    @abstractmethod
    async def poll_status(self, provider_job_id, api_key) -> tuple[int, Optional[str]]: ...
    @abstractmethod
    async def cancel(self, provider_job_id, api_key) -> bool: ...
```

Polling loop: 2s interval, max 900 attempts (30min timeout). Downloads result on completion. Updates budget on success.

---

## 10. DAG Integration

Accepted generation → `GeneratedMediaNode` in DAG with full reproducibility metadata:
- `prompt`, `params`, `seed`, `model_version` preserved
- `insert_mode`: `source_monitor` (load for preview), `timeline_cursor` (insert at playhead), `project_bin` (add to bin only)

`focusedPanel` type in useCutEditorStore must be extended: add `'generation'` to the union.

---

## 11. Reference Frame Capture

Cmd+F in Generate tab:
1. Read `sourceMediaPath` from store
2. Seek source video to `sourceCurrentTime`
3. Draw to offscreen canvas → `toDataURL('image/jpeg', 0.85)`
4. Store base64 in `currentReferenceFrameUrl`
5. Show thumbnail with X to clear
6. On submit: base64 sent to backend, saved to disk, passed to provider

---

## 12. Implementation Tasks (for dispatch)

| # | Task | Agent | Priority | Complexity |
|---|------|-------|----------|-----------|
| 1 | GenerationControlPanel + store + state machine | Alpha | P2 | High |
| 2 | TransportBar + hotkeys (J/K/L/Space/Escape/Enter/Cmd+R) | Alpha | P2 | Medium |
| 3 | Provider abstraction (base_provider.py) + Runway + Kling providers | Beta | P2 | High |
| 4 | FLUX/SDXL local providers (ComfyUI/A1111 integration) | Beta | P3 | Medium |
| 5 | ElevenLabs + Suno + Udio audio providers | Beta | P3 | Medium |
| 6 | Real-ESRGAN + Topaz enhancement providers | Beta | P3 | Low |
| 7 | ProviderSettings panel + API key management | Gamma | P2 | Medium |
| 8 | GenerationQueueList + context menu | Gamma | P2 | Low |
| 9 | Budget service + alerts + daily reset | Alpha | P2 | Low |
| 10 | DAG integration (accept → import GeneratedMediaNode) | Alpha | P2 | Medium |
| 11 | Reference frame capture from Source Monitor | Alpha | P3 | Low |
| 12 | E2E tests for Generation Control | Epsilon | P3 | Medium |

---

## 13. Open Questions

1. **API key storage**: Backend-only in `{sandbox_root}/.generation_config.json` with 0600 perms. Never sent back to frontend.
2. **ComfyUI WebSocket vs HTTP**: Start with HTTP queue polling; WebSocket optimization later.
3. **Suno/Udio API stability**: Unofficial APIs — fail gracefully, show "beta" badge.
4. **Multi-job parallelism**: One active job per provider, multiple providers concurrent. `focusedJobId` separate from active jobs.
5. **Sora availability**: Gate behind `SORA_ENABLED=true` env flag.
