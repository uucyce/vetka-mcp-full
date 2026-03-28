/**
 * PasteAttributesDialog — Selective attribute paste modal for VETKA CUT.
 * Inspired by DaVinci Resolve Paste Attributes window.
 *
 * Allows pasting video/audio attributes from one clip to one or more target clips.
 * All state is local. Calls onApply(config) with selected attributes.
 */
import { useState, useEffect, useCallback, type CSSProperties } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface PasteAttributesConfig {
  // Video Attributes
  effects: boolean;
  colorCorrection: boolean;
  motion: boolean;
  speed: boolean;
  transition: boolean;
  // Audio Attributes
  volume: boolean;
  // Keyframes
  keyframes: boolean;
  keyframeMode: 'maintain' | 'stretch';
}

interface PasteAttributesDialogProps {
  onClose: () => void;
  onApply: (config: PasteAttributesConfig) => void;
  sourceClipName: string;
  targetClipNames: string[];
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const VIDEO_ATTRS: { key: keyof PasteAttributesConfig; label: string; hint: string }[] = [
  { key: 'effects',         label: 'Effects',           hint: 'brightness, contrast, saturation, blur, opacity' },
  { key: 'colorCorrection', label: 'Color Correction',  hint: 'exposure, temperature, tint, lift/mid/gain, curves' },
  { key: 'motion',          label: 'Motion',             hint: 'position, scale, rotation, anchor, crop' },
  { key: 'speed',           label: 'Speed / Retime',    hint: 'speed, reverse, maintain pitch' },
  { key: 'transition',      label: 'Transition',         hint: 'type + duration' },
];

const AUDIO_ATTRS: { key: keyof PasteAttributesConfig; label: string; hint: string }[] = [
  { key: 'volume', label: 'Volume', hint: 'clip volume keyframes' },
];

const DEFAULT_CONFIG: PasteAttributesConfig = {
  effects: false,
  colorCorrection: false,
  motion: false,
  speed: false,
  transition: false,
  volume: false,
  keyframes: false,
  keyframeMode: 'maintain',
};

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles: Record<string, CSSProperties> = {
  overlay: {
    position: 'fixed',
    inset: 0,
    zIndex: 9999,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(0,0,0,0.6)',
  },
  dialog: {
    background: '#1a1a1a',
    border: '1px solid #333',
    borderRadius: 4,
    padding: 0,
    width: 360,
    maxHeight: '80vh',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    boxSizing: 'border-box',
  },
  header: {
    padding: '12px 16px',
    borderBottom: '1px solid #333',
    fontSize: 13,
    fontWeight: 600,
    color: '#ccc',
    userSelect: 'none',
  },
  metaBlock: {
    padding: '8px 16px',
    borderBottom: '1px solid #333',
  },
  metaLabel: {
    fontSize: 11,
    color: '#888',
    lineHeight: '20px',
  },
  metaValue: {
    fontSize: 12,
    color: '#bbb',
    marginLeft: 4,
  },
  keyframesSection: {
    padding: '10px 16px',
    borderBottom: '1px solid #282828',
  },
  keyframesTitle: {
    fontSize: 12,
    fontWeight: 500,
    color: '#aaa',
    marginBottom: 8,
    userSelect: 'none',
  },
  radioRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 20,
  },
  radioLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 12,
    color: '#999',
    cursor: 'pointer',
    userSelect: 'none',
  },
  section: {
    borderBottom: '1px solid #282828',
  },
  sectionHeader: {
    padding: '8px 16px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    color: '#aaa',
    fontSize: 12,
    fontWeight: 500,
    userSelect: 'none',
  },
  sectionArrow: {
    fontSize: 10,
    color: '#666',
    width: 10,
    flexShrink: 0,
  },
  sectionMasterCheckbox: {
    marginLeft: 'auto',
    accentColor: '#888',
    cursor: 'pointer',
  },
  sectionBody: {
    paddingBottom: 4,
  },
  checkboxRow: {
    padding: '4px 16px 4px 36px',
    display: 'flex',
    alignItems: 'flex-start',
    gap: 8,
    fontSize: 12,
    color: '#999',
  },
  checkboxLabel: {
    display: 'flex',
    flexDirection: 'column',
    gap: 1,
  },
  hintText: {
    fontSize: 10,
    color: '#666',
  },
  buttons: {
    padding: '12px 16px',
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 8,
  },
  cancelBtn: {
    background: '#333',
    border: 'none',
    color: '#999',
    padding: '6px 16px',
    borderRadius: 3,
    fontSize: 12,
    cursor: 'pointer',
  },
  applyBtn: {
    background: '#555',
    border: 'none',
    color: '#ccc',
    padding: '6px 16px',
    borderRadius: 3,
    fontSize: 12,
    cursor: 'pointer',
  },
  applyBtnDisabled: {
    background: '#555',
    border: 'none',
    color: '#ccc',
    padding: '6px 16px',
    borderRadius: 3,
    fontSize: 12,
    cursor: 'not-allowed',
    opacity: 0.4,
  },
};

// ─── Component ────────────────────────────────────────────────────────────────

export default function PasteAttributesDialog({
  onClose,
  onApply,
  sourceClipName,
  targetClipNames,
}: PasteAttributesDialogProps) {
  const [config, setConfig] = useState<PasteAttributesConfig>(DEFAULT_CONFIG);
  const [videoOpen, setVideoOpen] = useState(true);
  const [audioOpen, setAudioOpen] = useState(true);

  // Escape key closes
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    },
    [onClose]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Toggle single attribute
  const toggleAttr = (key: keyof PasteAttributesConfig) => {
    setConfig((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // Master toggle for video section
  const videoAllChecked = VIDEO_ATTRS.every((a) => config[a.key] as boolean);
  const videoSomeChecked = VIDEO_ATTRS.some((a) => config[a.key] as boolean);
  const toggleVideoAll = (e: React.MouseEvent) => {
    e.stopPropagation();
    const next = !videoAllChecked;
    const update: Partial<PasteAttributesConfig> = {};
    VIDEO_ATTRS.forEach((a) => { (update as Record<string, boolean>)[a.key] = next; });
    setConfig((prev) => ({ ...prev, ...update }));
  };

  // Master toggle for audio section
  const audioAllChecked = AUDIO_ATTRS.every((a) => config[a.key] as boolean);
  const toggleAudioAll = (e: React.MouseEvent) => {
    e.stopPropagation();
    const next = !audioAllChecked;
    const update: Partial<PasteAttributesConfig> = {};
    AUDIO_ATTRS.forEach((a) => { (update as Record<string, boolean>)[a.key] = next; });
    setConfig((prev) => ({ ...prev, ...update }));
  };

  // Is anything checked?
  const anyChecked =
    VIDEO_ATTRS.some((a) => config[a.key] as boolean) ||
    AUDIO_ATTRS.some((a) => config[a.key] as boolean);

  // Target label
  const targetLabel =
    targetClipNames.length === 0
      ? '—'
      : targetClipNames.length === 1
      ? targetClipNames[0]
      : `${targetClipNames[0]} (+ ${targetClipNames.length - 1} more)`;

  const handleApply = () => {
    if (anyChecked) onApply(config);
  };

  return (
    <div style={styles.overlay} onClick={onClose} data-overlay="1">{/* MARKER_GAMMA-ESC-GUARD: guard escapeContext when dialog open */}
      <div
        data-testid="paste-attributes-dialog"
        style={styles.dialog}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={styles.header}>Paste Attributes</div>

        {/* Source / Target meta */}
        <div style={styles.metaBlock}>
          <div style={styles.metaLabel}>
            From:<span style={styles.metaValue}>{sourceClipName}</span>
          </div>
          <div style={styles.metaLabel}>
            To:<span style={styles.metaValue}>{targetLabel}</span>
          </div>
        </div>

        {/* Keyframes section */}
        <div style={styles.keyframesSection}>
          <div style={styles.keyframesTitle}>Keyframes</div>
          <div style={styles.radioRow}>
            <label style={styles.radioLabel}>
              <input
                type="radio"
                name="keyframeMode"
                value="maintain"
                checked={config.keyframeMode === 'maintain'}
                onChange={() => setConfig((prev) => ({ ...prev, keyframeMode: 'maintain' }))}
                style={{ accentColor: '#888' }}
              />
              Maintain Timing
            </label>
            <label style={styles.radioLabel}>
              <input
                type="radio"
                name="keyframeMode"
                value="stretch"
                checked={config.keyframeMode === 'stretch'}
                onChange={() => setConfig((prev) => ({ ...prev, keyframeMode: 'stretch' }))}
                style={{ accentColor: '#888' }}
              />
              Stretch to Fit
            </label>
          </div>
        </div>

        {/* Video Attributes section */}
        <div style={styles.section}>
          <div
            style={styles.sectionHeader}
            onClick={() => setVideoOpen((v) => !v)}
          >
            <span style={styles.sectionArrow}>{videoOpen ? '▼' : '▶'}</span>
            Video Attributes
            <input
              type="checkbox"
              checked={videoAllChecked}
              ref={(el) => {
                if (el) el.indeterminate = !videoAllChecked && videoSomeChecked;
              }}
              onChange={() => {}}
              onClick={toggleVideoAll}
              style={styles.sectionMasterCheckbox as React.CSSProperties}
              title="Toggle all video attributes"
            />
          </div>
          {videoOpen && (
            <div style={styles.sectionBody}>
              {VIDEO_ATTRS.map((attr) => (
                <label key={attr.key} style={{ ...styles.checkboxRow, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={config[attr.key] as boolean}
                    onChange={() => toggleAttr(attr.key)}
                    style={{ accentColor: '#888', flexShrink: 0, marginTop: 2 }}
                  />
                  <span style={styles.checkboxLabel}>
                    {attr.label}
                    <span style={styles.hintText}>{attr.hint}</span>
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Audio Attributes section */}
        <div style={styles.section}>
          <div
            style={styles.sectionHeader}
            onClick={() => setAudioOpen((v) => !v)}
          >
            <span style={styles.sectionArrow}>{audioOpen ? '▼' : '▶'}</span>
            Audio Attributes
            <input
              type="checkbox"
              checked={audioAllChecked}
              onChange={() => {}}
              onClick={toggleAudioAll}
              style={styles.sectionMasterCheckbox as React.CSSProperties}
              title="Toggle all audio attributes"
            />
          </div>
          {audioOpen && (
            <div style={styles.sectionBody}>
              {AUDIO_ATTRS.map((attr) => (
                <label key={attr.key} style={{ ...styles.checkboxRow, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={config[attr.key] as boolean}
                    onChange={() => toggleAttr(attr.key)}
                    style={{ accentColor: '#888', flexShrink: 0, marginTop: 2 }}
                  />
                  <span style={styles.checkboxLabel}>
                    {attr.label}
                    <span style={styles.hintText}>{attr.hint}</span>
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Footer buttons */}
        <div style={styles.buttons}>
          <button style={styles.cancelBtn} onClick={onClose}>
            Cancel
          </button>
          <button
            style={anyChecked ? styles.applyBtn : styles.applyBtnDisabled}
            onClick={handleApply}
            disabled={!anyChecked}
          >
            Apply
          </button>
        </div>
      </div>
    </div>
  );
}
