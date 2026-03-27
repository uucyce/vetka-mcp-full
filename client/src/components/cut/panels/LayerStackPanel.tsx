/**
 * MARKER_GAMMA-LAYERUI: Layer Stack & Depth Inspector Panel
 *
 * NLE-style layer compositor panel for explicit parallax layers.
 * Mental model: After Effects layer panel + DaVinci Resolve Depth Map inspector.
 *
 * Reads layer manifest from the selected clip's `layerManifest` property.
 * Manifest contract: docs/180_photo-to-parallax/PARALLAX_EXPLICIT_LAYER_EXTRACTION_ARCHITECTURE_2026-03-27.md §3
 *
 * Features:
 * - Layer list with visibility/solo/lock per layer
 * - Depth band visualization (gradient bar per layer)
 * - Layer thumbnail preview (rgba asset)
 * - Depth inspector: depth map thumbnail + near/far stats
 * - Reorder layers via drag (future: wired to render order)
 * - Empty state when no manifest attached
 *
 * @phase 200
 * @owner Gamma
 */
import { useState, useMemo, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../../store/useCutEditorStore';
import { useSelectionStore } from '../../../store/useSelectionStore';

// ─── Layer Manifest Types (from architecture doc §3) ─────────────────
export type LayerRole =
  | 'foreground_subject'
  | 'secondary_subject'
  | 'mid_environment'
  | 'background'
  | 'special_clean';

export interface LayerEntry {
  id: string;
  role: LayerRole;
  semantic_label: string;
  z: number;
  depth_band: [number, number]; // [near, far] normalized 0-1
  distance_hint?: 'near' | 'mid' | 'far';
  rgba: string;   // path to rgba asset
  alpha: string;  // path to alpha asset
  depth?: string;  // path to per-layer depth
  hole_filled?: boolean;
}

export interface LayerManifest {
  contract_version: string;
  sample_id: string;
  depth_source: {
    kind: string;
    polarity: string;
  };
  layers: LayerEntry[];
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

const DEPTH_SECTION: CSSProperties = {
  padding: '8px 10px',
  borderTop: '1px solid #1a1a1a',
  borderBottom: '1px solid #1a1a1a',
};

const DEPTH_STAT_ROW: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  padding: '2px 0',
  fontSize: 10,
};

// ─── Role display labels ─────────────────────────────────────────────
const ROLE_LABELS: Record<LayerRole, string> = {
  foreground_subject: 'FG Subject',
  secondary_subject: 'FG Secondary',
  mid_environment: 'Mid Env',
  background: 'Background',
  special_clean: 'Clean Plate',
};

// ─── Component ───────────────────────────────────────────────────────
export default function LayerStackPanel() {
  const selectedClipId = useSelectionStore((s) => s.selectedClipId);
  const lanes = useCutEditorStore((s) => s.lanes);

  // Find selected clip and its layer manifest
  const { clip, manifest } = useMemo(() => {
    if (!selectedClipId) return { clip: null, manifest: null };
    for (const lane of lanes) {
      const found = lane.clips.find((c) => c.clip_id === selectedClipId);
      if (found) {
        const m = (found as any).layerManifest as LayerManifest | undefined;
        return { clip: found, manifest: m ?? null };
      }
    }
    return { clip: null, manifest: null };
  }, [selectedClipId, lanes]);

  // Per-layer UI state (visibility, solo, lock)
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

  // Check if any layer is soloed
  const hasSolo = manifest?.layers.some((l) => getState(l.id).solo) ?? false;

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

  // ─── No manifest on clip ───────────────────────────────────────────
  if (!manifest) {
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

  // ─── Manifest present — render layer stack ─────────────────────────
  const layers = manifest.layers;
  // Sort by z (near first = top of stack, like AE/Nuke)
  const sorted = [...layers].sort((a, b) => b.z - a.z);

  return (
    <div style={PANEL} data-testid="cut-layer-stack-panel">
      {/* Header */}
      <div style={HEADER}>
        <span>Layers ({layers.length})</span>
        <span style={{ color: '#444' }}>{manifest.sample_id}</span>
      </div>

      {/* Depth Inspector Section */}
      <div style={DEPTH_SECTION}>
        <div style={{ ...DEPTH_STAT_ROW, color: '#888', marginBottom: 4 }}>
          <span>Depth Source</span>
          <span>{manifest.depth_source.kind === 'real_depth_raster' ? 'Real Depth' : manifest.depth_source.kind}</span>
        </div>
        <div style={DEPTH_STAT_ROW}>
          <span style={{ color: '#666' }}>Polarity</span>
          <span style={{ color: '#888' }}>{manifest.depth_source.polarity === 'white_near_black_far' ? 'White = Near' : manifest.depth_source.polarity}</span>
        </div>
        <div style={DEPTH_STAT_ROW}>
          <span style={{ color: '#666' }}>Contract</span>
          <span style={{ color: '#888' }}>v{manifest.contract_version}</span>
        </div>
        {/* Depth range bar — full gradient from near (white) to far (dark) */}
        <div style={{ marginTop: 6 }}>
          <div style={{
            width: '100%',
            height: 12,
            borderRadius: 2,
            background: 'linear-gradient(to right, #ccc, #333)',
            position: 'relative',
          }}>
            {/* Layer band markers overlaid on gradient */}
            {sorted.map((layer) => {
              const st = getState(layer.id);
              const isActive = !hasSolo || st.solo;
              return (
                <div
                  key={layer.id}
                  title={`${layer.semantic_label}: z=${layer.z} [${layer.depth_band[0].toFixed(2)}–${layer.depth_band[1].toFixed(2)}]`}
                  style={{
                    position: 'absolute',
                    left: `${(1 - layer.depth_band[1]) * 100}%`,
                    width: `${(layer.depth_band[1] - layer.depth_band[0]) * 100}%`,
                    top: 0,
                    height: '100%',
                    background: isActive ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.05)',
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
          const st = getState(layer.id);
          const isEffectivelyVisible = st.visible && (!hasSolo || st.solo);
          const dimmed = !isEffectivelyVisible;

          return (
            <div
              key={layer.id}
              style={{
                ...LAYER_ROW,
                opacity: dimmed ? 0.35 : 1,
                background: idx % 2 === 0 ? '#0d0d0d' : '#0f0f0f',
              }}
              data-testid={`cut-layer-row-${layer.id}`}
            >
              {/* Visibility toggle */}
              <button
                style={{
                  ...ICON_BTN,
                  color: st.visible ? '#999' : '#333',
                }}
                title={st.visible ? 'Hide layer' : 'Show layer'}
                onClick={() => toggleVisible(layer.id)}
                data-testid={`cut-layer-visibility-${layer.id}`}
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
                onClick={() => toggleSolo(layer.id)}
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
                onClick={() => toggleLock(layer.id)}
              >
L
              </button>

              {/* Depth band mini bar */}
              <div style={DEPTH_BAR_CONTAINER} title={`z=${layer.z}`}>
                <div style={{
                  marginLeft: `${(1 - layer.depth_band[1]) * 100}%`,
                  width: `${(layer.depth_band[1] - layer.depth_band[0]) * 100}%`,
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
                  {layer.semantic_label}
                </div>
                <div style={ROLE_BADGE}>
                  {ROLE_LABELS[layer.role] ?? layer.role}
                  {layer.hole_filled && ' \u2022 filled'}
                </div>
              </div>

              {/* Z value */}
              <span style={{ color: '#555', fontSize: 10, flexShrink: 0, width: 24, textAlign: 'right' }}>
                z{layer.z}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
