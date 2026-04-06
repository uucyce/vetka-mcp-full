/**
 * MARKER_GAMMA-MATCH: Match Sequence Settings popup.
 *
 * Appears when first video clip is dropped on empty timeline.
 * Probes clip via /cut/probe/streams, offers to match sequence settings.
 * Monochrome FCP7 style. No emoji.
 *
 * @task tb_1774260584_15
 */
import { useState, useEffect, useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { API_BASE } from '../../config/api.config';
import { useOverlayEscapeClose } from '../../hooks/useOverlayEscapeClose';

// --- Styles (monochrome, consistent with SequenceSettingsDialog) ---

const OVERLAY: CSSProperties = {
  position: 'fixed', inset: 0, zIndex: 9999,
  background: 'rgba(0,0,0,0.7)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
};

const DIALOG: CSSProperties = {
  background: '#1a1a1a', border: '1px solid #333', borderRadius: 4,
  padding: 20, width: 380, fontFamily: 'system-ui, sans-serif', color: '#ccc',
};

const ROW: CSSProperties = {
  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  marginBottom: 6,
};

const LABEL: CSSProperties = { fontSize: 11, color: '#888' };
const VALUE: CSSProperties = { fontSize: 11, color: '#ccc', fontFamily: 'monospace' };

const BTN: CSSProperties = {
  background: '#333', color: '#ccc', border: '1px solid #444',
  borderRadius: 3, padding: '6px 16px', fontSize: 11, cursor: 'pointer',
};

const BTN_PRIMARY: CSSProperties = {
  ...BTN, background: '#555', color: '#fff',
};

const CHECKBOX_ROW: CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 6, marginTop: 12,
  fontSize: 10, color: '#666',
};

// --- Resolution matching ---

type ResPreset = '4K' | '1080p' | '720p' | 'custom';

function matchResolution(w: number, h: number): { preset: ResPreset; w: number; h: number } {
  if (w === 3840 && h === 2160) return { preset: '4K', w, h };
  if (w === 1920 && h === 1080) return { preset: '1080p', w, h };
  if (w === 1280 && h === 720) return { preset: '720p', w, h };
  return { preset: 'custom', w, h };
}

function matchFps(fps: number): number {
  const options = [23.976, 24, 25, 29.97, 30, 48, 50, 59.94, 60];
  let best = options[0];
  let bestDist = Math.abs(fps - best);
  for (const opt of options) {
    const dist = Math.abs(fps - opt);
    if (dist < bestDist) { best = opt; bestDist = dist; }
  }
  return best;
}

// --- Probe data types ---

interface ProbeStream {
  type: 'video' | 'audio' | 'subtitle';
  codec: string;
  width?: number;
  height?: number;
  fps?: number;
  pix_fmt?: string;
  sample_rate?: number;
  channels?: number;
}

interface ProbeResult {
  success: boolean;
  streams: ProbeStream[];
}

// --- Component ---

export default function MatchSequencePopup() {
  const show = useCutEditorStore((s) => s.showMatchSequencePopup);
  const clipPath = useCutEditorStore((s) => s.pendingMatchClipPath);
  const sandboxRoot = useCutEditorStore((s) => s.sandboxRoot);
  const projectId = useCutEditorStore((s) => s.projectId);

  const [probeData, setProbeData] = useState<{
    resolution: string;
    fps: number;
    sampleRate: number;
    width: number;
    height: number;
    codec: string;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [dontAsk, setDontAsk] = useState(false);

  // Probe clip on show
  useEffect(() => {
    if (!show || !clipPath) return;
    setLoading(true);
    setProbeData(null);

    fetch(`${API_BASE}/cut/probe/streams?source_path=${encodeURIComponent(clipPath)}`)
      .then((r) => r.json())
      .then((data: ProbeResult) => {
        if (!data.success || !data.streams?.length) {
          setLoading(false);
          return;
        }
        const video = data.streams.find((s) => s.type === 'video');
        const audio = data.streams.find((s) => s.type === 'audio');
        const w = video?.width ?? 1920;
        const h = video?.height ?? 1080;
        const fps = video?.fps ?? 25;
        const sr = audio?.sample_rate ?? 48000;
        setProbeData({
          resolution: `${w}x${h}`,
          fps,
          sampleRate: sr,
          width: w,
          height: h,
          codec: video?.codec ?? 'unknown',
        });
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [show, clipPath]);

  const close = useCallback(() => {
    if (dontAsk) {
      localStorage.setItem('cut_suppress_match_popup', 'true');
    }
    useCutEditorStore.getState().setShowMatchSequencePopup(false);
  }, [dontAsk]);
  // MARKER_GAMMA-ESC-HOOK: Escape closes overlay + data-overlay prevents escapeContext from firing
  useOverlayEscapeClose(close);

  const handleMatch = useCallback(async () => {
    if (!probeData) { close(); return; }

    const s = useCutEditorStore.getState();
    const res = matchResolution(probeData.width, probeData.height);
    const fps = matchFps(probeData.fps);

    // Update store
    s.setSequenceResolution(res.preset);
    if (res.preset === 'custom') {
      s.setSequenceWidth(res.w);
      s.setSequenceHeight(res.h);
    }
    s.setProjectFramerate(fps);

    // Persist to backend
    try {
      await fetch(`${API_BASE}/cut/sequence-settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          framerate: fps,
          resolution: res.preset,
          width: res.preset === 'custom' ? res.w : undefined,
          height: res.preset === 'custom' ? res.h : undefined,
        }),
      });
    } catch {
      // Best effort — store already updated
    }

    close();
  }, [probeData, sandboxRoot, projectId, close]);

  if (!show) return null;

  const fileName = clipPath?.split('/').pop() ?? 'Unknown';

  return (
    <div style={OVERLAY} data-overlay="1" onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div style={DIALOG} data-testid="match-sequence-popup">
        <div style={{ fontSize: 14, fontWeight: 600, color: '#fff', marginBottom: 12 }}>
          Match Sequence Settings
        </div>

        <div style={{ fontSize: 11, color: '#999', marginBottom: 16, lineHeight: 1.5 }}>
          First clip detected: <span style={{ color: '#ccc' }}>{fileName}</span>
        </div>

        {loading && (
          <div style={{ fontSize: 11, color: '#666', marginBottom: 16 }}>
            Probing clip...
          </div>
        )}

        {probeData && (
          <div style={{ marginBottom: 16, background: '#111', borderRadius: 3, padding: 10 }}>
            <div style={ROW}>
              <span style={LABEL}>Resolution</span>
              <span style={VALUE}>{probeData.resolution}</span>
            </div>
            <div style={ROW}>
              <span style={LABEL}>Frame Rate</span>
              <span style={VALUE}>{probeData.fps} fps</span>
            </div>
            <div style={ROW}>
              <span style={LABEL}>Codec</span>
              <span style={VALUE}>{probeData.codec}</span>
            </div>
            <div style={{ ...ROW, marginBottom: 0 }}>
              <span style={LABEL}>Audio Sample Rate</span>
              <span style={VALUE}>{(probeData.sampleRate / 1000).toFixed(1)} kHz</span>
            </div>
          </div>
        )}

        <label style={CHECKBOX_ROW}>
          <input
            type="checkbox"
            checked={dontAsk}
            onChange={(e) => setDontAsk(e.target.checked)}
            style={{ accentColor: '#666' }}
          />
          Don't ask again for this project
        </label>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
          <button style={BTN} onClick={close}>Keep Current</button>
          <button
            style={BTN_PRIMARY}
            onClick={handleMatch}
            disabled={loading || !probeData}
          >
            Match Clip
          </button>
        </div>
      </div>
    </div>
  );
}
