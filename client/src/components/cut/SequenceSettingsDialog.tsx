/**
 * MARKER_B3 / B53: Sequence Settings dialog.
 *
 * Resolution, frame rate, color space, audio settings.
 * Reads/writes via useCutEditorStore. Persists via POST /cut/sequence-settings.
 * Monochrome FCP7 style, modal overlay.
 *
 * @phase B53
 * @task tb_1774258816_12
 */
import { useState, useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { API_BASE } from '../../config/api.config';
import { useOverlayEscapeClose } from '../../hooks/useOverlayEscapeClose';

type SequenceSettingsDialogProps = {
  open: boolean;
  onClose: () => void;
  sandboxRoot: string;
  projectId: string;
};

const OVERLAY: CSSProperties = {
  position: 'fixed', inset: 0, zIndex: 9999,
  background: 'rgba(0,0,0,0.7)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
};

const DIALOG: CSSProperties = {
  background: '#1a1a1a', border: '1px solid #333', borderRadius: 4,
  padding: 20, width: 380, maxHeight: '80vh', overflow: 'auto',
  fontFamily: 'system-ui, sans-serif', color: '#ccc',
};

const SECTION: CSSProperties = {
  marginBottom: 16,
};

const SECTION_TITLE: CSSProperties = {
  fontSize: 11, fontWeight: 600, color: '#999', marginBottom: 8,
  textTransform: 'uppercase' as const, letterSpacing: 1,
};

const ROW: CSSProperties = {
  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  marginBottom: 6,
};

const LABEL: CSSProperties = { fontSize: 11, color: '#888' };

const SELECT: CSSProperties = {
  background: '#111', color: '#ccc', border: '1px solid #333',
  borderRadius: 2, fontSize: 11, padding: '3px 6px', minWidth: 120,
};

const INPUT: CSSProperties = {
  ...SELECT, width: 60, textAlign: 'right' as const,
};

const BTN: CSSProperties = {
  background: '#333', color: '#ccc', border: '1px solid #444',
  borderRadius: 3, padding: '6px 16px', fontSize: 11, cursor: 'pointer',
};

const BTN_PRIMARY: CSSProperties = {
  ...BTN, background: '#555', color: '#fff',
};

const RESOLUTIONS = [
  { id: '4K', label: '4K (3840x2160)', w: 3840, h: 2160 },
  { id: '1080p', label: '1080p (1920x1080)', w: 1920, h: 1080 },
  { id: '720p', label: '720p (1280x720)', w: 1280, h: 720 },
  { id: 'custom', label: 'Custom', w: 0, h: 0 },
] as const;

const FPS_OPTIONS = [23.976, 24, 25, 29.97, 30, 48, 50, 59.94, 60];

export default function SequenceSettingsDialog({
  open, onClose, sandboxRoot, projectId,
}: SequenceSettingsDialogProps) {
  const store = useCutEditorStore.getState();

  const [resolution, setResolution] = useState(store.sequenceResolution);
  const [customW, setCustomW] = useState(store.sequenceWidth);
  const [customH, setCustomH] = useState(store.sequenceHeight);
  const [fps, setFps] = useState(store.projectFramerate);
  const [dropFrame, setDropFrame] = useState(store.dropFrame);
  const [colorSpace, setColorSpace] = useState(store.sequenceColorSpace);
  const [sampleRate, setSampleRate] = useState(store.audioSampleRate);
  const [bitDepth, setBitDepth] = useState(store.audioBitDepth);
  const [saving, setSaving] = useState(false);

  const close = useCallback(() => onClose(), [onClose]);
  // MARKER_GAMMA-ESC-HOOK: Escape closes overlay + data-overlay prevents escapeContext from firing
  useOverlayEscapeClose(close);

  const handleSave = useCallback(async () => {
    setSaving(true);

    // Update store
    const s = useCutEditorStore.getState();
    s.setSequenceResolution(resolution);
    if (resolution === 'custom') {
      s.setSequenceWidth(customW);
      s.setSequenceHeight(customH);
    }
    s.setProjectFramerate(fps);
    s.setDropFrame(dropFrame);
    s.setSequenceColorSpace(colorSpace);
    s.setAudioSampleRate(sampleRate);
    s.setAudioBitDepth(bitDepth);

    // Persist to backend
    try {
      await fetch(`${API_BASE}/cut/sequence-settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          framerate: fps,
          resolution,
          width: resolution === 'custom' ? customW : undefined,
          height: resolution === 'custom' ? customH : undefined,
          color_space: colorSpace,
          audio_sample_rate: sampleRate,
          audio_bit_depth: bitDepth,
        }),
      });
    } catch {
      // Best effort — store is already updated
    }

    setSaving(false);
    close();
  }, [resolution, customW, customH, fps, dropFrame, colorSpace, sampleRate, bitDepth, close]);

  if (!open) return null;

  return (
    <div style={OVERLAY} data-overlay="1" onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div style={DIALOG}>
        <div style={{ fontSize: 14, fontWeight: 600, color: '#fff', marginBottom: 16 }}>
          Sequence Settings
        </div>

        {/* Video */}
        <div style={SECTION}>
          <div style={SECTION_TITLE}>Video</div>

          <div style={ROW}>
            <span style={LABEL}>Resolution</span>
            <select
              style={SELECT}
              value={resolution}
              onChange={(e) => setResolution(e.target.value as typeof resolution)}
            >
              {RESOLUTIONS.map((r) => (
                <option key={r.id} value={r.id}>{r.label}</option>
              ))}
            </select>
          </div>

          {resolution === 'custom' && (
            <div style={ROW}>
              <span style={LABEL}>Custom Size</span>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                <input
                  type="number" style={INPUT} value={customW}
                  onChange={(e) => setCustomW(Math.max(1, parseInt(e.target.value) || 1))}
                />
                <span style={{ color: '#555', fontSize: 10 }}>x</span>
                <input
                  type="number" style={INPUT} value={customH}
                  onChange={(e) => setCustomH(Math.max(1, parseInt(e.target.value) || 1))}
                />
              </div>
            </div>
          )}

          <div style={ROW}>
            <span style={LABEL}>Frame Rate</span>
            <select
              style={SELECT}
              value={fps}
              onChange={(e) => setFps(parseFloat(e.target.value))}
            >
              {FPS_OPTIONS.map((f) => (
                <option key={f} value={f}>{f} fps</option>
              ))}
            </select>
          </div>

          {(fps === 29.97 || fps === 59.94) && (
            <div style={ROW}>
              <span style={LABEL}>Drop Frame Timecode</span>
              <input
                type="checkbox"
                checked={dropFrame}
                onChange={(e) => setDropFrame(e.target.checked)}
                style={{ cursor: 'pointer' }}
              />
            </div>
          )}

          <div style={ROW}>
            <span style={LABEL}>Color Space</span>
            <select
              style={SELECT}
              value={colorSpace}
              onChange={(e) => setColorSpace(e.target.value as typeof colorSpace)}
            >
              <option value="Rec.709">Rec. 709 (HD)</option>
              <option value="Rec.2020">Rec. 2020 (HDR)</option>
              <option value="DCI-P3">DCI-P3 (Cinema)</option>
            </select>
          </div>
        </div>

        {/* Audio */}
        <div style={SECTION}>
          <div style={SECTION_TITLE}>Audio</div>

          <div style={ROW}>
            <span style={LABEL}>Sample Rate</span>
            <select
              style={SELECT}
              value={sampleRate}
              onChange={(e) => setSampleRate(parseInt(e.target.value) as typeof sampleRate)}
            >
              <option value={44100}>44.1 kHz</option>
              <option value={48000}>48 kHz</option>
              <option value={96000}>96 kHz</option>
            </select>
          </div>

          <div style={ROW}>
            <span style={LABEL}>Bit Depth</span>
            <select
              style={SELECT}
              value={bitDepth}
              onChange={(e) => setBitDepth(parseInt(e.target.value) as typeof bitDepth)}
            >
              <option value={16}>16-bit</option>
              <option value={24}>24-bit</option>
              <option value={32}>32-bit float</option>
            </select>
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 8 }}>
          <button style={BTN} onClick={close}>Cancel</button>
          <button style={BTN_PRIMARY} onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}
