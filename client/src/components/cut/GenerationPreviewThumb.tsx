/**
 * MARKER_GEN-PREVIEW: Generation Preview Thumb — shows result in PREVIEWING state.
 * Accept/Reject buttons. Monochrome.
 *
 * @phase GENERATION_CONTROL
 * @task tb_1774432024_1
 */
import type { CSSProperties } from 'react';
import { useGenerationControlStore } from '../../store/useGenerationControlStore';

const CONTAINER: CSSProperties = {
  display: 'flex', flexDirection: 'column', alignItems: 'stretch',
  padding: '8px 10px', borderBottom: '1px solid #1a1a1a',
};

const THUMB: CSSProperties = {
  width: '100%', aspectRatio: '16/9',
  background: '#111', borderRadius: 3,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  overflow: 'hidden', marginBottom: 6,
};

const BTN_ROW: CSSProperties = {
  display: 'flex', gap: 6,
};

const BTN_ACCEPT: CSSProperties = {
  flex: 1, padding: '5px 0',
  background: '#1a1a1a', border: '1px solid #444',
  borderRadius: 3, color: '#ccc', fontSize: 10, cursor: 'pointer',
  fontFamily: 'system-ui',
};

const BTN_REJECT: CSSProperties = {
  flex: 1, padding: '5px 0',
  background: '#111', border: '1px solid #222',
  borderRadius: 3, color: '#666', fontSize: 10, cursor: 'pointer',
  fontFamily: 'system-ui',
};

const LABEL: CSSProperties = {
  fontSize: 8, textTransform: 'uppercase', letterSpacing: 0.5,
  color: '#555', marginBottom: 4,
};

export default function GenerationPreviewThumb() {
  const machineState = useGenerationControlStore((s) => s.machineState);
  const previewUrl = useGenerationControlStore((s) => s.previewUrl);
  const acceptPreview = useGenerationControlStore((s) => s.acceptPreview);
  const rejectPreview = useGenerationControlStore((s) => s.rejectPreview);

  if (machineState !== 'PREVIEWING' || !previewUrl) return null;

  return (
    <div style={CONTAINER} data-testid="generation-preview-thumb">
      <div style={LABEL}>Preview</div>
      <div style={THUMB}>
        {/* Try video first, fallback to img for static frames */}
        {previewUrl.match(/\.(mp4|webm|mov)$/i) ? (
          <video
            src={previewUrl}
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            controls={false}
            autoPlay
            loop
            muted
            data-testid="preview-video"
          />
        ) : (
          <img
            src={previewUrl}
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            alt="Generated preview"
            data-testid="preview-img"
          />
        )}
      </div>
      <div style={BTN_ROW}>
        <button
          style={BTN_ACCEPT}
          onClick={acceptPreview}
          data-testid="btn-accept-preview"
        >
          Accept ↵
        </button>
        <button
          style={BTN_REJECT}
          onClick={rejectPreview}
          data-testid="btn-reject-preview"
        >
          Reject ⎋
        </button>
      </div>
    </div>
  );
}
