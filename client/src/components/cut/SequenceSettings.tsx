/**
 * MARKER_B3 — Sequence Settings Panel
 *
 * Project resolution, color space, proxy mode settings for NLE timeline.
 * Persists to backend POST /cut/project-state.
 *
 * FCP7 equivalent: File → Project Settings
 */
import { useMemo, useCallback, useState } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { API_BASE } from '../../config/api.config';
import type { CSSProperties } from 'react';

type Resolution = '4k' | '1080p' | '720p' | 'custom';
type ColorSpace = 'rec709' | 'dci_p3' | 'rec2020';

interface SequenceSettingsState {
  resolution: Resolution;
  customWidth?: number;
  customHeight?: number;
  colorSpace: ColorSpace;
  proxyMode: boolean;
  proxyResolution?: '480p' | '720p';
}

/**
 * Resolution presets (width x height)
 */
const RESOLUTION_PRESETS: Record<string, { label: string; width: number; height: number }> = {
  '4k': { label: '4K (3840×2160)', width: 3840, height: 2160 },
  '1080p': { label: '1080p (1920×1080)', width: 1920, height: 1080 },
  '720p': { label: '720p (1280×720)', width: 1280, height: 720 },
};

const COLOR_SPACES: Record<ColorSpace, string> = {
  rec709: 'Rec. 709 (Standard)',
  dci_p3: 'DCI-P3 (Cinema)',
  rec2020: 'Rec. 2020 (HDR)',
};

export function SequenceSettings() {
  const projectId = useCutEditorStore((s) => s.projectId);
  const sandboxRoot = useCutEditorStore((s) => s.sandboxRoot);

  // Load settings from project store or defaults
  const [settings, setSettings] = useState<SequenceSettingsState>({
    resolution: '1080p',
    colorSpace: 'rec709',
    proxyMode: false,
    proxyResolution: '720p',
  });

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  /**
   * Save settings to backend via POST /sequence-settings
   */
  const saveSettings = useCallback(async () => {
    if (!projectId) return;
    setSaving(true);
    setSaveError(null);

    try {
      // Map resolution setting to width/height
      let width = 1920;
      let height = 1080;
      if (settings.resolution === '4k') {
        width = 3840;
        height = 2160;
      } else if (settings.resolution === '720p') {
        width = 1280;
        height = 720;
      } else if (settings.resolution === 'custom' && settings.customWidth && settings.customHeight) {
        width = settings.customWidth;
        height = settings.customHeight;
      }

      const res = await fetch(`${API_BASE}/sequence-settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot || '',
          project_id: projectId,
          resolution: settings.resolution === 'custom' ? 'custom' : settings.resolution,
          width,
          height,
          color_space: settings.colorSpace === 'rec709' ? 'Rec.709' :
                       settings.colorSpace === 'dci_p3' ? 'DCI-P3' : 'Rec.2020',
          proxy_mode: settings.proxyMode ? (settings.proxyResolution || '720p') : 'full',
          framerate: 25,  // Default, could be made configurable
          timecode_format: 'smpte',
          drop_frame: false,
          start_timecode: '00:00:00:00',
          audio_sample_rate: 48000,
          audio_bit_depth: 24,
        }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();
      if (!data.success) {
        throw new Error(data.error || 'Save failed');
      }
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  }, [projectId, sandboxRoot, settings]);

  const resLabel = useMemo(() => {
    if (settings.resolution === 'custom') {
      return `${settings.customWidth}×${settings.customHeight}`;
    }
    return RESOLUTION_PRESETS[settings.resolution]?.label || 'Unknown';
  }, [settings.resolution, settings.customWidth, settings.customHeight]);

  const styles: Record<string, CSSProperties> = {
    container: {
      display: 'flex',
      flexDirection: 'column',
      gap: '1.5rem',
      padding: '1rem',
      fontSize: '13px',
      color: '#ccc',
    },
    section: {
      display: 'flex',
      flexDirection: 'column',
      gap: '0.75rem',
    },
    label: {
      fontWeight: '600',
      color: '#fff',
      fontSize: '12px',
      textTransform: 'uppercase',
      letterSpacing: '0.05em',
    },
    select: {
      padding: '6px 8px',
      backgroundColor: '#2a2a2a',
      color: '#ccc',
      border: '1px solid #444',
      borderRadius: '3px',
      fontSize: '12px',
      cursor: 'pointer',
    },
    input: {
      padding: '6px 8px',
      backgroundColor: '#2a2a2a',
      color: '#ccc',
      border: '1px solid #444',
      borderRadius: '3px',
      fontSize: '12px',
    },
    checkbox: {
      cursor: 'pointer',
      marginRight: '0.5rem',
    },
    buttonGroup: {
      display: 'flex',
      gap: '0.75rem',
      marginTop: '0.5rem',
    },
    button: {
      padding: '8px 12px',
      backgroundColor: '#3a5a8a',
      color: '#fff',
      border: 'none',
      borderRadius: '3px',
      fontSize: '12px',
      cursor: 'pointer',
      fontWeight: '600',
    },
    buttonDisabled: {
      backgroundColor: '#444',
      cursor: 'not-allowed',
      opacity: 0.5,
    },
    error: {
      color: '#ff6b6b',
      fontSize: '11px',
      marginTop: '0.5rem',
    },
    hint: {
      fontSize: '11px',
      color: '#999',
      marginTop: '0.25rem',
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.section}>
        <label style={styles.label}>Video Resolution</label>
        <select
          value={settings.resolution}
          onChange={(e) =>
            setSettings((prev) => ({
              ...prev,
              resolution: e.target.value as Resolution,
            }))
          }
          style={styles.select}
        >
          {Object.entries(RESOLUTION_PRESETS).map(([key, { label }]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
          <option value="custom">Custom</option>
        </select>
        {settings.resolution === 'custom' && (
          <div
            style={{
              display: 'flex',
              gap: '0.5rem',
              marginTop: '0.5rem',
            }}
          >
            <input
              type="number"
              placeholder="Width"
              value={settings.customWidth || ''}
              onChange={(e) =>
                setSettings((prev) => ({
                  ...prev,
                  customWidth: e.target.value ? parseInt(e.target.value) : undefined,
                }))
              }
              style={{ ...styles.input, flex: 1 }}
            />
            <input
              type="number"
              placeholder="Height"
              value={settings.customHeight || ''}
              onChange={(e) =>
                setSettings((prev) => ({
                  ...prev,
                  customHeight: e.target.value ? parseInt(e.target.value) : undefined,
                }))
              }
              style={{ ...styles.input, flex: 1 }}
            />
          </div>
        )}
        <div style={styles.hint}>Current: {resLabel}</div>
      </div>

      <div style={styles.section}>
        <label style={styles.label}>Color Space</label>
        <select
          value={settings.colorSpace}
          onChange={(e) =>
            setSettings((prev) => ({
              ...prev,
              colorSpace: e.target.value as ColorSpace,
            }))
          }
          style={styles.select}
        >
          {Object.entries(COLOR_SPACES).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
        <div style={styles.hint}>
          {settings.colorSpace === 'rec709'
            ? 'Standard for broadcast and web'
            : settings.colorSpace === 'dci_p3'
              ? 'Cinema DCI standard'
              : 'HDR wide gamut'}
        </div>
      </div>

      <div style={styles.section}>
        <label style={{ ...styles.label, display: 'flex', alignItems: 'center' }}>
          <input
            type="checkbox"
            checked={settings.proxyMode}
            onChange={(e) =>
              setSettings((prev) => ({
                ...prev,
                proxyMode: e.target.checked,
              }))
            }
            style={styles.checkbox}
          />
          Enable Proxy Mode
        </label>
        <div style={styles.hint}>Create lower-resolution proxies for faster playback</div>
        {settings.proxyMode && (
          <select
            value={settings.proxyResolution || '720p'}
            onChange={(e) =>
              setSettings((prev) => ({
                ...prev,
                proxyResolution: e.target.value as '480p' | '720p',
              }))
            }
            style={{ ...styles.select, marginTop: '0.5rem' }}
          >
            <option value="480p">480p</option>
            <option value="720p">720p</option>
          </select>
        )}
      </div>

      <div style={styles.buttonGroup}>
        <button
          onClick={saveSettings}
          disabled={saving}
          style={{
            ...styles.button,
            ...(saving ? styles.buttonDisabled : {}),
          }}
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>

      {saveError && <div style={styles.error}>{saveError}</div>}
    </div>
  );
}

export default SequenceSettings;
