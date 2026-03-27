/**
 * MARKER_GAMMA-LAYERUI-ALIGN: Layer Stack & Depth Inspector Panel
 *
 * NLE-style layer compositor panel for explicit parallax layers.
 * Mental model: After Effects layer panel + DaVinci Resolve Depth Map inspector.
 *
 * CONTRACT SOURCE OF TRUTH:
 *   docs/190_ph_CUT_WORKFLOW_ARCH/HANDOFF_LAYERFX_MANIFEST_CONTRACT_2026-03-27.md
 *
 * Read path:
 *   clip.layer_manifest?.manifest_path  → async fetch full manifest
 *   clip.layer_manifest?.layer_count    → header badge (no fetch needed)
 *   clip.layer_manifest?.sample_id      → header label (no fetch needed)
 *
 * JSON wire format: camelCase (sampleId, depthPriority, parallaxStrength)
 * Layer roles on disk: kebab-case (foreground-subject, environment-mid)
 *
 * @phase 200
 * @owner Gamma
 */
import { useState, useMemo, useEffect, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../../store/useCutEditorStore';
import { useSelectionStore } from '../../../store/useSelectionStore';
import { API_BASE } from '../../../config/api.config';

// ─── Types: Beta canonical contract (camelCase = JSON wire format) ────

/** Stored on clip as clip.layer_manifest (lightweight meta, no async needed) */
export interface LayerManifestMeta {
  manifest_path: string;
  format: string;           // "layer_space" | "plate_export"
  layer_count: number;
  has_foreground: boolean;
  has_background: boolean;
  sample_id: string;
}

/**
 * Full manifest loaded via GET /cut/layers/manifest?path=...
 * Response: { success: true, manifest: LayerManifestResponse }
 *
 * IMPORTANT: Beta to_dict() = asdict() → snake_case field names.
 * These types match the ACTUAL API wire format, not the spec's camelCase suggestion.
 */
export interface LayerManifestResponse {
  contract_version: string;
  sample_id: string;
  source_path: string;
  source_width: number;
  source_height: number;
  layers: LayerEntry[];
  camera: CameraContract;
  depth_path: string;
  background_rgba_path: string;
  format: string;
  provenance: Record<string, string>;
}

export interface LayerEntry {
  layer_id: string;
  role: string;                // normalized to underscore by Beta: "foreground_subject"
  label: string;
  order: number;               // compositing index (0 = back)
  depth_priority: number;      // 0-1 float, SEPARATE from order
  z: number;
  visible: boolean;
  rgba_path: string;           // absolute path (resolved by Beta on ingest)
  mask_path: string;
  depth_path: string;
  clean_path: string;
  clean_variant: string;
  coverage: number;
  parallax_strength: number;
  motion_damping: number;
}

export interface CameraContract {
  focal_length_mm: number;
  film_width_mm: number;
  z_near: number;
  z_far: number;
  motion_type: string;
  duration_sec: number;
  travel_x_pct: number;
  travel_y_pct: number;
  zoom: number;
  overscan_pct: number;
}

// ─── Role normalization (kebab-case on disk → display labels) ────────
const ROLE_DISPLAY: Record<string, string> = {
  'foreground-subject': 'FG Subject',
  'secondary-subject': 'FG Secondary',
  'environment-mid': 'Mid Env',
  'background-far': 'Background',
  'special-clean': 'Clean Plate',
  // Python-normalized forms (underscore) as fallback
  'foreground_subject': 'FG Subject',
  'secondary_subject': 'FG Secondary',
  'mid_environment': 'Mid Env',
  'background': 'Background',
  'special_clean': 'Clean Plate',
};

function roleLabel(role: string): string {
  return ROLE_DISPLAY[role] ?? role;
}

// ─── UI State ────────────────────────────────────────────────────────
interface LayerUIState {
  visible: boolean;
  solo: boolean;
  locked: boolean;
}

// ─── Styles ──────────────────────────────────────────────────────────
const PANEL: CSSProperties = {
  background: '#0d0d0d',
  color: '#ccc',
  height: '100%',
  overflow: 'auto',
  fontFamily: "'SF Mono', 'Fira Code', monospace",
  fontSize: 11,
  userSelect: 'none',
};

const HEADER: CSSProperties = {
  padding: '8px 10px',
  borderBottom: '1px solid #1a1a1a',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  fontSize: 10,
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  color: '#888',
};

const EMPTY: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100%',
  color: '#555',
  fontSize: 11,
  gap: 6,
  padding: 20,
  textAlign: 'center',
};

const LAYER_ROW: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  padding: '4px 8px',
  borderBottom: '1px solid #141414',
  gap: 6,
  minHeight: 36,
};

const ICON_BTN: CSSProperties = {
  background: 'none',
  border: 'none',
  color: '#666',
  cursor: 'pointer',
  fontSize: 11,
  padding: '2px 3px',
  borderRadius: 2,
  lineHeight: 1,
};

const DEPTH_BAR_CONTAINER: CSSProperties = {
  width: 40,
  height: 8,
  background: '#1a1a1a',
  borderRadius: 2,
  overflow: 'hidden',
  flexShrink: 0,
};

const ROLE_BADGE: CSSProperties = {
  fontSize: 9,
  color: '#555',
  textTransform: 'uppercase',
  letterSpacing: '0.3px',
};

const INFO_SECTION: CSSProperties = {
  padding: '8px 10px',
  borderTop: '1px solid #1a1a1a',
  borderBottom: '1px solid #1a1a1a',
};

const STAT_ROW: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  padding: '2px 0',
  fontSize: 10,
};

// ─── Component ───────────────────────────────────────────────────────
export default function LayerStackPanel() {
  const selectedClipId = useSelectionStore((s) => s.selectedClipId);
  const lanes = useCutEditorStore((s) => s.lanes);

  // Extract clip-level meta (lightweight, no fetch)
  const { clip, meta } = useMemo(() => {
    if (!selectedClipId) return { clip: null, meta: null };
    for (const lane of lanes) {
      const found = lane.clips.find((c) => c.clip_id === selectedClipId);
      if (found) {
        const m = (found as any).layer_manifest as LayerManifestMeta | undefined;
        return { clip: found, meta: m ?? null };
      }
    }
    return { clip: null, meta: null };
  }, [selectedClipId, lanes]);

  // Async-loaded full manifest (fetched when meta.manifest_path changes)
  // Beta response: { success: true, manifest: LayerManifestResponse }
  const [manifest, setManifest] = useState<LayerManifestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setManifest(null);
    setError(null);
    if (!meta?.manifest_path) return;

    let cancelled = false;
    setLoading(true);

    fetch(`${API_BASE}/cut/layers/manifest?path=${encodeURIComponent(meta.manifest_path)}`)
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        return r.json();
      })
      .then((resp: { success: boolean; manifest?: LayerManifestResponse; error?: string }) => {
        if (cancelled) return;
        if (!resp.success || !resp.manifest) {
          setError(resp.error ?? 'Empty manifest response');
          setLoading(false);
          return;
        }
        setManifest(resp.manifest);
        setLoading(false);
      })
      .catch((err) => {
        if (!cancelled) { setError(String(err)); setLoading(false); }
      });

    return () => { cancelled = true; };
  }, [meta?.manifest_path]);

  // Per-layer UI state (visibility override, solo, lock)
  const [layerState, setLayerState] = useState<Record<string, LayerUIState>>({});

  const getState = (id: string): LayerUIState =>
    layerState[id] ?? { visible: true, solo: false, locked: false };

  const toggleVisible = (id: string) => {
    const cur = getState(id);
    setLayerState((prev) => ({ ...prev, [id]: { ...cur, visible: !cur.visible } }));
  };

  const toggleSolo = (id: string) => {
    const cur = getState(id);
    setLayerState((prev) => ({ ...prev, [id]: { ...cur, solo: !cur.solo } }));
  };

  const toggleLock = (id: string) => {
    const cur = getState(id);
    setLayerState((prev) => ({ ...prev, [id]: { ...cur, locked: !cur.locked } }));
  };

  const hasSolo = manifest?.layers.some((l) => getState(l.layer_id).solo) ?? false;

  // ─── No clip selected ──────────────────────────────────────────────
  if (!selectedClipId || !clip) {
    return (
      <div style={PANEL}>
        <div style={EMPTY}>
          <span style={{ fontSize: 16 }}>Layers</span>
          <span>Select a clip to inspect layers</span>
        </div>
      </div>
    );
  }

  // ─── No manifest meta on clip ──────────────────────────────────────
  if (!meta) {
    return (
      <div style={PANEL}>
        <div style={HEADER}>
          <span>Layers</span>
          <span style={{ color: '#444' }}>{clip.clip_id.slice(0, 12)}</span>
        </div>
        <div style={EMPTY}>
          <span>No layer manifest</span>
          <span style={{ fontSize: 10, color: '#444' }}>
            Generate depth layers via Effects &gt; Depth Map
            or import a layer pack to populate this panel.
          </span>
        </div>
      </div>
    );
  }

  // ─── Meta present but manifest still loading ───────────────────────
  if (loading) {
    return (
      <div style={PANEL}>
        <div style={HEADER}>
          <span>Layers ({meta.layer_count})</span>
          <span style={{ color: '#444' }}>{meta.sample_id}</span>
        </div>
        <div style={EMPTY}>
          <span>Loading manifest...</span>
        </div>
      </div>
    );
  }

  // ─── Fetch error ───────────────────────────────────────────────────
  if (error) {
    return (
      <div style={PANEL}>
        <div style={HEADER}>
          <span>Layers ({meta.layer_count})</span>
          <span style={{ color: '#444' }}>{meta.sample_id}</span>
        </div>
        <div style={EMPTY}>
          <span>Failed to load manifest</span>
          <span style={{ fontSize: 9, color: '#444', wordBreak: 'break-all' }}>{error}</span>
        </div>
      </div>
    );
  }

  // ─── No full manifest (meta exists but endpoint not available yet) ─
  if (!manifest) {
    return (
      <div style={PANEL}>
        <div style={HEADER}>
          <span>Layers ({meta.layer_count})</span>
          <span style={{ color: '#444' }}>{meta.sample_id}</span>
        </div>
        <div style={{ ...INFO_SECTION, borderTop: 'none' }}>
          <div style={STAT_ROW}>
            <span style={{ color: '#666' }}>Format</span>
            <span style={{ color: '#888' }}>{meta.format}</span>
          </div>
          <div style={STAT_ROW}>
            <span style={{ color: '#666' }}>Foreground</span>
            <span style={{ color: '#888' }}>{meta.has_foreground ? 'Yes' : 'No'}</span>
          </div>
          <div style={STAT_ROW}>
            <span style={{ color: '#666' }}>Background</span>
            <span style={{ color: '#888' }}>{meta.has_background ? 'Yes' : 'No'}</span>
          </div>
        </div>
        <div style={EMPTY}>
          <span style={{ fontSize: 10, color: '#444' }}>
            Full manifest pending — endpoint /cut/layers/manifest not yet available.
          </span>
        </div>
      </div>
    );
  }

  // ─── Full manifest loaded — render layer stack + camera info ───────
  const layers = manifest.layers;
  // Sort by order descending (highest order = frontmost = top of stack)
  const sorted = [...layers].sort((a, b) => b.order - a.order);
  const cam = manifest.camera;

  return (
    <div style={PANEL} data-testid="cut-layer-stack-panel">
      {/* Header */}
      <div style={HEADER}>
        <span>Layers ({layers.length})</span>
        <span style={{ color: '#444' }}>{manifest.sample_id}</span>
      </div>

      {/* Camera Inspector Section */}
      <div style={INFO_SECTION}>
        <div style={{ ...STAT_ROW, color: '#888', marginBottom: 4 }}>
          <span>Camera</span>
          <span>{cam.motion_type}</span>
        </div>
        <div style={STAT_ROW}>
          <span style={{ color: '#666' }}>Focal</span>
          <span style={{ color: '#888' }}>{cam.focal_length_mm}mm</span>
        </div>
        <div style={STAT_ROW}>
          <span style={{ color: '#666' }}>Duration</span>
          <span style={{ color: '#888' }}>{cam.duration_sec}s</span>
        </div>
        <div style={STAT_ROW}>
          <span style={{ color: '#666' }}>Travel</span>
          <span style={{ color: '#888' }}>X {cam.travel_x_pct}% Y {cam.travel_y_pct}%</span>
        </div>
        <div style={STAT_ROW}>
          <span style={{ color: '#666' }}>Depth Range</span>
          <span style={{ color: '#888' }}>{cam.z_near.toFixed(2)} – {cam.z_far.toFixed(2)}</span>
        </div>
        <div style={STAT_ROW}>
          <span style={{ color: '#666' }}>Contract</span>
          <span style={{ color: '#888' }}>v{manifest.contract_version}</span>
        </div>
        {manifest.provenance?.depth_backend && (
          <div style={STAT_ROW}>
            <span style={{ color: '#666' }}>Provenance</span>
            <span style={{ color: '#888' }}>{manifest.provenance.depth_backend}</span>
          </div>
        )}

        {/* Depth range bar — near (white) to far (dark), layers positioned by depth_priority */}
        <div style={{ marginTop: 6 }}>
          <div style={{
            width: '100%',
            height: 12,
            borderRadius: 2,
            background: 'linear-gradient(to right, #ccc, #333)',
            position: 'relative',
          }}>
            {sorted.map((layer) => {
              const st = getState(layer.layer_id);
              const isActive = !hasSolo || st.solo;
              const pos = layer.depth_priority;
              const barWidth = Math.max(4, (layer.coverage || 0.1) * 30);
              return (
                <div
                  key={layer.layer_id}
                  title={`${layer.label}: dp=${pos.toFixed(2)} z=${layer.z} coverage=${((layer.coverage || 0) * 100).toFixed(0)}%`}
                  style={{
                    position: 'absolute',
                    left: `${(1 - pos) * 100 - barWidth / 2}%`,
                    width: `${barWidth}%`,
                    top: 0,
                    height: '100%',
                    background: isActive ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.05)',
                    borderLeft: '1px solid rgba(255,255,255,0.3)',
                    borderRight: '1px solid rgba(255,255,255,0.3)',
                  }}
                />
              );
            })}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: '#555', marginTop: 2 }}>
            <span>Near</span>
            <span>Far</span>
          </div>
        </div>
      </div>

      {/* Layer Stack List */}
      <div>
        {sorted.map((layer, idx) => {
          const st = getState(layer.layer_id);
          const isEffectivelyVisible = layer.visible && st.visible && (!hasSolo || st.solo);
          const dimmed = !isEffectivelyVisible;

          return (
            <div
              key={layer.layer_id}
              style={{
                ...LAYER_ROW,
                opacity: dimmed ? 0.35 : 1,
                background: idx % 2 === 0 ? '#0d0d0d' : '#0f0f0f',
              }}
              data-testid={`cut-layer-row-${layer.layer_id}`}
            >
              {/* RGBA thumbnail */}
              {layer.rgba_path && (
                <img
                  src={`${API_BASE}/cut/media/file?path=${encodeURIComponent(layer.rgba_path)}`}
                  alt={layer.label}
                  style={{
                    width: 28,
                    height: 28,
                    objectFit: 'cover',
                    borderRadius: 2,
                    background: '#1a1a1a',
                    flexShrink: 0,
                    filter: 'grayscale(100%)',
                  }}
                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                />
              )}

              {/* Visibility toggle */}
              <button
                style={{
                  ...ICON_BTN,
                  color: st.visible ? '#999' : '#333',
                }}
                title={st.visible ? 'Hide layer' : 'Show layer'}
                onClick={() => toggleVisible(layer.layer_id)}
                data-testid={`cut-layer-visibility-${layer.layer_id}`}
              >
                {st.visible ? '\u25C9' : '\u25CB'}
              </button>

              {/* Solo toggle */}
              <button
                style={{
                  ...ICON_BTN,
                  color: st.solo ? '#ccc' : '#333',
                  fontWeight: st.solo ? 700 : 400,
                }}
                title={st.solo ? 'Unsolo' : 'Solo layer'}
                onClick={() => toggleSolo(layer.layer_id)}
              >
                S
              </button>

              {/* Lock toggle */}
              <button
                style={{
                  ...ICON_BTN,
                  color: st.locked ? '#999' : '#333',
                }}
                title={st.locked ? 'Unlock' : 'Lock layer'}
                onClick={() => toggleLock(layer.layer_id)}
              >
                L
              </button>

              {/* Depth priority mini bar */}
              <div style={DEPTH_BAR_CONTAINER} title={`dp=${layer.depth_priority.toFixed(2)}`}>
                <div style={{
                  marginLeft: `${(1 - layer.depth_priority) * 100}%`,
                  width: `${Math.max(10, (layer.coverage || 0.1) * 100)}%`,
                  height: '100%',
                  background: '#888',
                  borderRadius: 2,
                }} />
              </div>

              {/* Layer info */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  color: dimmed ? '#555' : '#ccc',
                  fontSize: 11,
                }}>
                  {layer.label}
                </div>
                <div style={ROLE_BADGE}>
                  {roleLabel(layer.role)}
                  {(layer.coverage || 0) > 0 && ` \u2022 ${((layer.coverage || 0) * 100).toFixed(0)}%`}
                </div>
              </div>

              {/* Order */}
              <span style={{ color: '#555', fontSize: 10, flexShrink: 0, width: 32, textAlign: 'right' }}>
                #{layer.order}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
