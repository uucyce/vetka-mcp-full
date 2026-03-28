/**
 * MARKER_GEN-TRANSPORT: Generation Transport Bar — state machine controls.
 *
 * FCP7 Deck Control transport mapped to AI generation:
 *   J = preview previous result (not impl — stub)
 *   K = stop / cancel (while GENERATING or QUEUED)
 *   L = play preview (while PREVIEWING)
 *   Space = toggle generate/stop
 *   Escape = cancel / reject
 *   Enter = accept (while PREVIEWING)
 *   Cmd+R = generate (while IDLE/CONFIGURING)
 *
 * Hotkeys handled by useGenerationHotkeys hook, mounted in GenerationControlPanel.
 * This component only renders the visual transport bar.
 *
 * @phase GENERATION_CONTROL
 * @task tb_1774432024_1
 */
import type { CSSProperties } from 'react';
import { useGenerationControlStore, type GenMachineState } from '../../store/useGenerationControlStore';
import { API_BASE } from '../../config/api.config';

// ─── Styles ───

const BAR: CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 6,
  padding: '6px 10px', borderTop: '1px solid #1a1a1a',
  background: '#0a0a0a', flexShrink: 0,
};

const BTN: CSSProperties = {
  padding: '4px 10px', border: '1px solid #333', borderRadius: 3,
  background: '#111', color: '#aaa', fontSize: 9, cursor: 'pointer',
  fontFamily: 'system-ui', transition: 'none',
};

const BTN_PRIMARY: CSSProperties = {
  ...BTN, background: '#1a1a1a', color: '#ccc', border: '1px solid #444',
};

const BTN_DISABLED: CSSProperties = {
  ...BTN, opacity: 0.3, cursor: 'default',
};

const STATE_BADGE: CSSProperties = {
  flex: 1, textAlign: 'right',
  fontSize: 8, fontFamily: 'monospace', color: '#444',
  textTransform: 'uppercase', letterSpacing: 1,
};

const PROGRESS_BG: CSSProperties = {
  flex: 1, height: 3, background: '#1a1a1a', borderRadius: 2, overflow: 'hidden',
};

// ─── State helpers ───

function stateBadgeText(state: GenMachineState): string {
  switch (state) {
    case 'DISCONNECTED': return 'NO PROVIDER';
    case 'CONNECTING':   return 'CONNECTING…';
    case 'IDLE':         return 'IDLE';
    case 'CONFIGURING':  return 'CONFIGURING';
    case 'QUEUED':       return 'QUEUED';
    case 'GENERATING':   return 'GENERATING';
    case 'PREVIEWING':   return 'PREVIEWING';
    case 'ACCEPTED':     return 'ACCEPTED';
    case 'IMPORTING':    return 'IMPORTING…';
    case 'CANCELLED':    return 'CANCELLED';
    case 'REJECTED':     return 'REJECTED';
  }
}

// ─── Component ───

export default function GenerationTransportBar() {
  const machineState = useGenerationControlStore((s) => s.machineState);
  const activeProviderId = useGenerationControlStore((s) => s.activeProviderId);
  const prompt = useGenerationControlStore((s) => s.prompt);
  const params = useGenerationControlStore((s) => s.params);
  const jobId = useGenerationControlStore((s) => s.jobId);
  const progress = useGenerationControlStore((s) => s.progress);
  const referenceFrameDataUrl = useGenerationControlStore((s) => s.referenceFrameDataUrl);
  const submitJob = useGenerationControlStore((s) => s.submitJob);
  const jobQueued = useGenerationControlStore((s) => s.jobQueued);
  const jobStarted = useGenerationControlStore((s) => s.jobStarted);
  const setProgress = useGenerationControlStore((s) => s.setProgress);
  const setPreviewUrl = useGenerationControlStore((s) => s.setPreviewUrl);
  const cancelJob = useGenerationControlStore((s) => s.cancelJob);
  const acceptPreview = useGenerationControlStore((s) => s.acceptPreview);
  const rejectPreview = useGenerationControlStore((s) => s.rejectPreview);
  const addSpend = useGenerationControlStore((s) => s.addSpend);
  const importComplete = useGenerationControlStore((s) => s.importComplete);

  const canGenerate = ['IDLE', 'CONFIGURING', 'REJECTED'].includes(machineState) && !!activeProviderId && !!prompt.trim();
  const canCancel = ['QUEUED', 'GENERATING'].includes(machineState);
  const canAccept = machineState === 'PREVIEWING';

  const handleGenerate = async () => {
    if (!canGenerate || !activeProviderId) return;
    submitJob();
    try {
      const res = await fetch(`${API_BASE}/cut/generate/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider_id: activeProviderId,
          prompt,
          params,
          reference_frame: referenceFrameDataUrl ?? undefined,
        }),
      });
      const data = await res.json() as { job_id: string };
      jobQueued(data.job_id);
      jobStarted();

      // Poll progress
      const pollInterval = setInterval(async () => {
        try {
          const pr = await fetch(`${API_BASE}/cut/generate/status/${data.job_id}`);
          const pd = await pr.json() as {
            status: string; progress: number; eta?: string;
            preview_url?: string; cost_usd?: number;
          };

          if (pd.status === 'generating') {
            setProgress(pd.progress, pd.eta);
          } else if (pd.status === 'completed' && pd.preview_url) {
            clearInterval(pollInterval);
            if (pd.cost_usd) addSpend(pd.cost_usd);
            setPreviewUrl(pd.preview_url);
          } else if (pd.status === 'failed' || pd.status === 'cancelled') {
            clearInterval(pollInterval);
            cancelJob();
          }
        } catch {
          clearInterval(pollInterval);
          cancelJob();
        }
      }, 2000);
    } catch {
      cancelJob();
    }
  };

  const handleCancelledIdle = () => {
    useGenerationControlStore.getState().forceState('IDLE');
  };

  // After IMPORTING, auto-complete
  if (machineState === 'IMPORTING' && jobId) {
    fetch(`${API_BASE}/cut/generate/accept/${jobId}`, { method: 'POST' })
      .then(() => importComplete())
      .catch(() => importComplete());
  }

  return (
    <div style={BAR} data-testid="generation-transport-bar">
      {/* Generate / Cancel / Accept / Reject buttons */}
      {canGenerate && (
        <button
          style={BTN_PRIMARY}
          onClick={handleGenerate}
          title="Generate (⌘R)"
          data-testid="btn-generate"
        >
          ⌘R Generate
        </button>
      )}

      {canCancel && (
        <button
          style={BTN}
          onClick={cancelJob}
          title="Cancel (K / ⎋)"
          data-testid="btn-cancel"
        >
          K Cancel
        </button>
      )}

      {canAccept && (
        <>
          <button
            style={BTN_PRIMARY}
            onClick={acceptPreview}
            title="Accept (↵)"
            data-testid="btn-accept"
          >
            ↵ Accept
          </button>
          <button
            style={BTN}
            onClick={rejectPreview}
            title="Reject (⎋)"
            data-testid="btn-reject"
          >
            ⎋ Reject
          </button>
        </>
      )}

      {(machineState === 'CANCELLED' || machineState === 'REJECTED') && (
        <button
          style={BTN}
          onClick={handleCancelledIdle}
          data-testid="btn-reset"
        >
          Reset
        </button>
      )}

      {(machineState === 'IDLE' || machineState === 'DISCONNECTED') && !canGenerate && (
        <button style={BTN_DISABLED} disabled data-testid="btn-generate-disabled">
          ⌘R Generate
        </button>
      )}

      {/* Progress bar */}
      {machineState === 'GENERATING' && (
        <div style={PROGRESS_BG}>
          <div style={{
            height: '100%',
            width: `${progress * 100}%`,
            background: '#fff',
            borderRadius: 2,
            transition: 'width 0.3s ease',
          }} />
        </div>
      )}

      {/* State badge */}
      <div style={STATE_BADGE} data-testid="gen-state-badge">
        {stateBadgeText(machineState)}
      </div>
    </div>
  );
}
