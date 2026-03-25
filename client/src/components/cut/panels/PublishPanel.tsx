/**
 * MARKER_GAMMA-W6.3: Social Crosspost / Publish Panel.
 *
 * Platform picker (YouTube, Instagram, TikTok, Telegram, VK, X),
 * auto-reformat options, batch export trigger.
 * Backend: GET /export/social-presets, POST /export/batch
 * Monochrome FCP7 style. No emoji.
 *
 * @task tb_1773874824_27
 */
import { useState, useEffect, useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../../store/useCutEditorStore';
import { API_BASE } from '../../../config/api.config';

// --- Styles ---

const PANEL: CSSProperties = {
  height: '100%', overflow: 'auto', padding: 10,
  fontFamily: 'system-ui, sans-serif', color: '#ccc', fontSize: 11,
  background: '#111',
};

const SECTION_TITLE: CSSProperties = {
  fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 8,
  textTransform: 'uppercase' as const, letterSpacing: 1,
};

const PLATFORM_ROW: CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 8, padding: '5px 6px',
  borderRadius: 3, cursor: 'pointer', userSelect: 'none' as const,
  marginBottom: 2,
};

const BADGE: CSSProperties = {
  fontSize: 9, color: '#666', fontFamily: 'monospace',
  marginLeft: 'auto',
};

const BTN: CSSProperties = {
  background: '#333', color: '#ccc', border: '1px solid #444',
  borderRadius: 3, padding: '6px 14px', fontSize: 11, cursor: 'pointer',
  width: '100%', marginTop: 8,
};

const BTN_PRIMARY: CSSProperties = {
  ...BTN, background: '#555', color: '#fff',
};

const CHECKBOX: CSSProperties = {
  accentColor: '#666',
};

// --- Platform display names ---

const PLATFORM_LABELS: Record<string, string> = {
  youtube: 'YouTube',
  instagram_reels: 'Instagram Reels',
  instagram_feed_1x1: 'Instagram Feed (1:1)',
  instagram_feed_4x5: 'Instagram Feed (4:5)',
  tiktok: 'TikTok',
  telegram: 'Telegram',
  vk: 'VK',
  x: 'X (Twitter)',
};

const PLATFORM_ORDER = [
  'youtube', 'instagram_reels', 'instagram_feed_1x1',
  'instagram_feed_4x5', 'tiktok', 'telegram', 'vk', 'x',
];

// --- Types ---

interface SocialPreset {
  aspect_ratio: string;
  recommended: { codec: string; resolution: string };
  extras?: string[];
}

type PresetsMap = Record<string, SocialPreset>;

// --- Component ---

export default function PublishPanel() {
  const sandboxRoot = useCutEditorStore((s) => s.sandboxRoot);
  const projectId = useCutEditorStore((s) => s.projectId);
  const fps = useCutEditorStore((s) => s.projectFramerate);

  const [presets, setPresets] = useState<PresetsMap>({});
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  // Fetch presets on mount
  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/export/social-presets`)
      .then((r) => r.json())
      .then((data) => {
        if (data.success && data.presets) {
          setPresets(data.presets);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const toggle = useCallback((id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelected(new Set(Object.keys(presets)));
  }, [presets]);

  const selectNone = useCallback(() => {
    setSelected(new Set());
  }, []);

  const handleExport = useCallback(async () => {
    if (!selected.size || !sandboxRoot || !projectId) return;
    setExporting(true);
    setResult(null);
    try {
      const resp = await fetch(`${API_BASE}/export/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          sequence_name: `${projectId}_export`,
          fps,
          formats: ['premiere_xml'],
          social_targets: [...selected],
        }),
      });
      const data = await resp.json();
      if (data.success) {
        setResult(`Exported ${Object.keys(data.exports || {}).length} format(s) + ${Object.keys(data.social_targets || {}).length} platform(s)`);
      } else {
        setResult('Export failed');
      }
    } catch {
      setResult('Export error — check backend');
    }
    setExporting(false);
  }, [selected, sandboxRoot, projectId, fps]);

  const platformIds = PLATFORM_ORDER.filter((id) => id in presets);

  return (
    <div style={PANEL} data-testid="publish-panel">
      <div style={SECTION_TITLE}>Publish / Crosspost</div>

      {loading && (
        <div style={{ color: '#666', marginBottom: 12 }}>Loading presets...</div>
      )}

      {!loading && platformIds.length === 0 && (
        <div style={{ color: '#666' }}>No social presets available</div>
      )}

      {platformIds.length > 0 && (
        <>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <span
              style={{ color: '#666', cursor: 'pointer', fontSize: 10, textDecoration: 'underline' }}
              onClick={selectAll}
            >
              Select All
            </span>
            <span
              style={{ color: '#666', cursor: 'pointer', fontSize: 10, textDecoration: 'underline' }}
              onClick={selectNone}
            >
              None
            </span>
          </div>

          {platformIds.map((id) => {
            const preset = presets[id];
            const isOn = selected.has(id);
            return (
              <div
                key={id}
                style={{
                  ...PLATFORM_ROW,
                  background: isOn ? '#1a1a1a' : 'transparent',
                }}
                onClick={() => toggle(id)}
              >
                <input
                  type="checkbox"
                  checked={isOn}
                  readOnly
                  style={CHECKBOX}
                />
                <span style={{ color: isOn ? '#fff' : '#999' }}>
                  {PLATFORM_LABELS[id] || id}
                </span>
                <span style={BADGE}>
                  {preset.aspect_ratio} / {preset.recommended.resolution}
                </span>
              </div>
            );
          })}

          <div style={{ marginTop: 12, padding: '8px 0', borderTop: '1px solid #222' }}>
            <div style={SECTION_TITLE}>Export Settings</div>
            <div style={{ fontSize: 10, color: '#666', marginBottom: 4 }}>
              Codec: H.264 | Container: MP4 | FPS: {fps}
            </div>
            <div style={{ fontSize: 10, color: '#666', marginBottom: 8 }}>
              Resolution auto-adjusted per platform preset
            </div>
          </div>

          <button
            style={selected.size > 0 ? BTN_PRIMARY : BTN}
            onClick={handleExport}
            disabled={exporting || selected.size === 0}
          >
            {exporting
              ? 'Exporting...'
              : `Export to ${selected.size} Platform${selected.size !== 1 ? 's' : ''}`}
          </button>

          {result && (
            <div style={{
              marginTop: 8, padding: '6px 8px', background: '#1a1a1a',
              borderRadius: 3, fontSize: 10, color: '#999',
            }}>
              {result}
            </div>
          )}
        </>
      )}
    </div>
  );
}
