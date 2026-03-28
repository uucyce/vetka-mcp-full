/**
 * MARKER_W4.5: Project Settings dialog — framerate, timecode, audio settings.
 * MARKER_B3: Sequence Settings — resolution, color space, proxy mode.
 * Modal overlay triggered by hotkey or menu. Stores settings in useCutEditorStore.
 */
import { useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { useOverlayEscapeClose } from '../../hooks/useOverlayEscapeClose';

const OVERLAY: CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0,0,0,0.6)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 9999,
};

const DIALOG: CSSProperties = {
  background: '#111',
  border: '1px solid #2a2a2a',
  borderRadius: 8,
  width: 380,
  maxHeight: '80vh',
  overflow: 'auto',
  boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
  fontFamily: 'system-ui',
  fontSize: 12,
  color: '#ccc',
};

const HEADER: CSSProperties = {
  padding: '14px 16px 10px',
  borderBottom: '1px solid #1e1e1e',
  fontWeight: 600,
  fontSize: 13,
};

const SECTION: CSSProperties = {
  padding: '10px 16px',
  borderBottom: '1px solid #1a1a1a',
};

const SECTION_TITLE: CSSProperties = {
  color: '#666',
  fontSize: 10,
  textTransform: 'uppercase' as const,
  letterSpacing: 1,
  marginBottom: 8,
};

const ROW: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: 8,
};

const LABEL: CSSProperties = {
  color: '#888',
  fontSize: 11,
};

const SELECT: CSSProperties = {
  background: '#1a1a1a',
  color: '#ccc',
  border: '1px solid #333',
  borderRadius: 4,
  padding: '4px 8px',
  fontSize: 11,
  fontFamily: 'system-ui',
  cursor: 'pointer',
};

const INPUT: CSSProperties = {
  ...SELECT,
  width: 120,
  cursor: 'text',
};

const FOOTER: CSSProperties = {
  padding: '10px 16px',
  display: 'flex',
  justifyContent: 'flex-end',
  gap: 8,
};

const BTN: CSSProperties = {
  background: '#1a1a1a',
  color: '#ccc',
  border: '1px solid #333',
  borderRadius: 4,
  padding: '6px 16px',
  fontSize: 11,
  cursor: 'pointer',
  fontFamily: 'system-ui',
};

const FRAMERATES = [23.976, 24, 25, 29.97, 30, 50, 59.94, 60];

export default function ProjectSettings() {
  const show = useCutEditorStore((s) => s.showProjectSettings);
  const framerate = useCutEditorStore((s) => s.projectFramerate);
  const tcFormat = useCutEditorStore((s) => s.timecodeFormat);
  const dropFrame = useCutEditorStore((s) => s.dropFrame);
  const startTC = useCutEditorStore((s) => s.startTimecode);
  const sampleRate = useCutEditorStore((s) => s.audioSampleRate);
  const bitDepth = useCutEditorStore((s) => s.audioBitDepth);

  const setFramerate = useCutEditorStore((s) => s.setProjectFramerate);
  const setTcFormat = useCutEditorStore((s) => s.setTimecodeFormat);
  const setDropFrame = useCutEditorStore((s) => s.setDropFrame);
  const setStartTC = useCutEditorStore((s) => s.setStartTimecode);
  const setSampleRate = useCutEditorStore((s) => s.setAudioSampleRate);
  const setBitDepth = useCutEditorStore((s) => s.setAudioBitDepth);
  const setShow = useCutEditorStore((s) => s.setShowProjectSettings);

  // MARKER_B3: Sequence Settings
  const resolution = useCutEditorStore((s) => s.sequenceResolution);
  const seqWidth = useCutEditorStore((s) => s.sequenceWidth);
  const seqHeight = useCutEditorStore((s) => s.sequenceHeight);
  const colorSpace = useCutEditorStore((s) => s.sequenceColorSpace);
  const proxyMode = useCutEditorStore((s) => s.proxyMode);

  const setResolution = useCutEditorStore((s) => s.setSequenceResolution);
  const setSeqWidth = useCutEditorStore((s) => s.setSequenceWidth);
  const setSeqHeight = useCutEditorStore((s) => s.setSequenceHeight);
  const setColorSpace = useCutEditorStore((s) => s.setSequenceColorSpace);
  const setProxyMode = useCutEditorStore((s) => s.setProxyMode);

  const close = useCallback(() => setShow(false), [setShow]);
  // MARKER_GAMMA-ESC-HOOK: Escape closes overlay + data-overlay prevents escapeContext from firing
  useOverlayEscapeClose(close);

  if (!show) return null;

  // Drop frame only relevant for 29.97 and 59.94
  const dropFrameRelevant = framerate === 29.97 || framerate === 59.94;

  return (
    <div style={OVERLAY} data-overlay="1" onClick={close}>
      <div style={DIALOG} onClick={(e) => e.stopPropagation()}>
        <div style={HEADER}>Project Settings</div>

        {/* Video section */}
        <div style={SECTION}>
          <div style={SECTION_TITLE}>Video</div>
          <div style={ROW}>
            <span style={LABEL}>Framerate</span>
            <select
              style={SELECT}
              value={framerate}
              onChange={(e) => setFramerate(Number(e.target.value))}
            >
              {FRAMERATES.map((fps) => (
                <option key={fps} value={fps}>{fps} fps</option>
              ))}
            </select>
          </div>
          <div style={ROW}>
            <span style={LABEL}>Timecode Format</span>
            <select
              style={SELECT}
              value={tcFormat}
              onChange={(e) => setTcFormat(e.target.value as 'smpte' | 'milliseconds')}
            >
              <option value="smpte">SMPTE (HH:MM:SS:FF)</option>
              <option value="milliseconds">Milliseconds (HH:MM:SS.mmm)</option>
            </select>
          </div>
          {dropFrameRelevant && (
            <div style={ROW}>
              <span style={LABEL}>Drop Frame</span>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={dropFrame}
                  onChange={(e) => setDropFrame(e.target.checked)}
                />
                <span style={{ color: '#888', fontSize: 10 }}>{dropFrame ? 'ON' : 'OFF'}</span>
              </label>
            </div>
          )}
          <div style={ROW}>
            <span style={LABEL}>Start Timecode</span>
            <input
              type="text"
              style={INPUT}
              value={startTC}
              onChange={(e) => setStartTC(e.target.value)}
              placeholder="01:00:00:00"
            />
          </div>
        </div>

        {/* MARKER_B3: Sequence Settings */}
        <div style={SECTION}>
          <div style={SECTION_TITLE}>Sequence</div>
          <div style={ROW}>
            <span style={LABEL}>Resolution</span>
            <select
              style={SELECT}
              value={resolution}
              onChange={(e) => setResolution(e.target.value as '4K' | '1080p' | '720p' | 'custom')}
            >
              <option value="4K">4K (3840×2160)</option>
              <option value="1080p">1080p (1920×1080)</option>
              <option value="720p">720p (1280×720)</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          {resolution === 'custom' && (
            <div style={ROW}>
              <span style={LABEL}>Width × Height</span>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                <input
                  type="number"
                  style={{ ...INPUT, width: 56 }}
                  value={seqWidth}
                  onChange={(e) => setSeqWidth(Number(e.target.value))}
                  min={1}
                />
                <span style={{ color: '#555' }}>×</span>
                <input
                  type="number"
                  style={{ ...INPUT, width: 56 }}
                  value={seqHeight}
                  onChange={(e) => setSeqHeight(Number(e.target.value))}
                  min={1}
                />
              </div>
            </div>
          )}
          <div style={ROW}>
            <span style={LABEL}>Color Space</span>
            <select
              style={SELECT}
              value={colorSpace}
              onChange={(e) => setColorSpace(e.target.value as 'Rec.709' | 'Rec.2020' | 'DCI-P3')}
            >
              <option value="Rec.709">Rec.709 (SDR)</option>
              <option value="Rec.2020">Rec.2020 (HDR)</option>
              <option value="DCI-P3">DCI-P3 (Cinema)</option>
            </select>
          </div>
          <div style={ROW}>
            <span style={LABEL}>Proxy Mode</span>
            <select
              style={SELECT}
              value={proxyMode}
              onChange={(e) => setProxyMode(e.target.value as 'full' | 'proxy' | 'auto')}
            >
              <option value="full">Full Resolution</option>
              <option value="proxy">Proxy Only</option>
              <option value="auto">Auto (proxy when available)</option>
            </select>
          </div>
        </div>

        {/* Audio section */}
        <div style={SECTION}>
          <div style={SECTION_TITLE}>Audio</div>
          <div style={ROW}>
            <span style={LABEL}>Sample Rate</span>
            <select
              style={SELECT}
              value={sampleRate}
              onChange={(e) => setSampleRate(Number(e.target.value) as 48000 | 44100 | 96000)}
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
              onChange={(e) => setBitDepth(Number(e.target.value) as 16 | 24 | 32)}
            >
              <option value={16}>16-bit</option>
              <option value={24}>24-bit</option>
              <option value={32}>32-bit float</option>
            </select>
          </div>
        </div>

        <div style={FOOTER}>
          <button style={BTN} onClick={close}>Close</button>
        </div>
      </div>
    </div>
  );
}
