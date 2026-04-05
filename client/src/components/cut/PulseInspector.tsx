/**
 * MARKER_180.18: PulseInspector — shows PULSE data for selected scene/asset.
 *
 * Architecture doc §2.7:
 * "Inspector panel: metadata display for selected asset or scene.
 *  Shows Camelot key, energy, pendulum, McKee position, scale.
 *  Includes mini Camelot wheel showing harmonic context."
 *
 * Located in right_bottom dock position (below Source Monitor).
 * Updates reactively via usePanelSyncStore.
 */
import { useMemo, type CSSProperties } from 'react';
import { usePanelSyncStore, type SyncSceneContext } from '../../store/usePanelSyncStore';
import CamelotWheel from './CamelotWheel';

// ─── Types ───

export interface PulseData {
  camelot_key: string;
  energy: number;
  pendulum: number;
  triangle: { arch: number; mini: number; anti: number };
  dramatic_function: string;
  scale: string;
  confidence: number;
}

// ─── Styles (§11 compliant) ───

const PANEL: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  width: '100%',
  height: '100%',
  background: '#1A1A1A',
  overflow: 'hidden',
  fontFamily: 'Inter, system-ui, sans-serif',
  fontSize: 11,
  color: '#888',
};

const HEADER: CSSProperties = {
  padding: '6px 8px',
  borderBottom: '0.5px solid #333',
  fontSize: 10,
  color: '#E0E0E0',
  fontWeight: 500,
  flexShrink: 0,
  background: '#141414',
};

const CONTENT: CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  padding: '8px',
};

const ROW: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '3px 0',
  borderBottom: '0.5px solid #252525',
};

const LABEL: CSSProperties = {
  fontSize: 9,
  color: '#555',
  textTransform: 'uppercase',
  letterSpacing: '0.3px',
};

const VALUE: CSSProperties = {
  fontSize: 11,
  color: '#E0E0E0',
  fontFamily: '"JetBrains Mono", monospace',
};

const SECTION_TITLE: CSSProperties = {
  fontSize: 9,
  color: '#555',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  padding: '8px 0 4px 0',
};

const BAR_BG: CSSProperties = {
  width: 60,
  height: 4,
  background: '#252525',
  borderRadius: 2,
  overflow: 'hidden',
};

// ─── Helper: pendulum label ───

function pendulumLabel(v: number): string {
  if (v <= -0.6) return 'Deep Minor';
  if (v <= -0.2) return 'Minor';
  if (v <= 0.2) return 'Neutral';
  if (v <= 0.6) return 'Major';
  return 'Bright Major';
}

// ─── Helper: dramatic function icon ───

function functionIcon(fn: string): string {
  switch (fn) {
    case 'exposition': return '📖';
    case 'rising_action': return '📈';
    case 'climax': return '⚡';
    case 'falling_action': return '📉';
    case 'resolution': return '🏁';
    case 'turning_point': return '🔄';
    default: return '●';
  }
}

// ─── Component ───

interface PulseInspectorProps {
  /** Override scene context (normally reads from sync store) */
  sceneContext?: SyncSceneContext | null;
}

export default function PulseInspector({ sceneContext: contextProp }: PulseInspectorProps) {
  const activeSceneId = usePanelSyncStore((s) => s.activeSceneId);
  const activeSceneContext = usePanelSyncStore((s) => s.activeSceneContext);
  const selectedAssetId = usePanelSyncStore((s) => s.selectedAssetId);
  const selectedAssetPath = usePanelSyncStore((s) => s.selectedAssetPath);
  const playheadSec = usePanelSyncStore((s) => s.playheadSec);

  const context = contextProp || activeSceneContext;

  // Format timecode
  const timecode = useMemo(() => {
    const m = Math.floor(playheadSec / 60);
    const s = Math.floor(playheadSec % 60);
    const f = Math.floor((playheadSec % 1) * 24); // 24fps frames
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}:${f.toString().padStart(2, '0')}`;
  }, [playheadSec]);

  // No context = empty state
  if (!context && !selectedAssetId) {
    return (
      <div style={PANEL}>
        <div style={HEADER}>Inspector</div>
        <div
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#444',
            fontSize: 10,
            textAlign: 'center',
            padding: 16,
          }}
        >
          Select a scene or asset to inspect PULSE data
        </div>
      </div>
    );
  }

  return (
    <div style={PANEL}>
      <div style={HEADER}>
        {context?.label || activeSceneId || selectedAssetId || 'Inspector'}
      </div>

      <div style={CONTENT}>
        {/* ─── Scene Info ─── */}
        {activeSceneId && (
          <>
            <div style={ROW}>
              <span style={LABEL}>Scene</span>
              <span style={VALUE}>{activeSceneId}</span>
            </div>
            <div style={ROW}>
              <span style={LABEL}>Timecode</span>
              <span style={VALUE}>{timecode}</span>
            </div>
          </>
        )}

        {/* ─── Asset Info ─── */}
        {selectedAssetId && (
          <>
            <div style={ROW}>
              <span style={LABEL}>Asset</span>
              <span style={{ ...VALUE, fontSize: 9, maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {selectedAssetPath?.split('/').pop() || selectedAssetId}
              </span>
            </div>
          </>
        )}

        {/* ─── PULSE Data (from scene context) ─── */}
        {context && (
          <>
            <div style={SECTION_TITLE}>PULSE Analysis</div>

            {/* Camelot Key */}
            {context.camelot_key && (
              <div style={ROW}>
                <span style={LABEL}>Camelot</span>
                <span style={{ ...VALUE, color: '#5DCAA5' }}>{context.camelot_key}</span>
              </div>
            )}

            {/* Energy bar */}
            {context.energy !== undefined && (
              <div style={ROW}>
                <span style={LABEL}>Energy</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={BAR_BG}>
                    <div
                      style={{
                        width: `${(context.energy ?? 0) * 100}%`,
                        height: '100%',
                        background: '#5DCAA5',
                        borderRadius: 2,
                        transition: 'width 0.3s',
                      }}
                    />
                  </div>
                  <span style={{ ...VALUE, fontSize: 9 }}>{((context.energy ?? 0) * 100).toFixed(0)}%</span>
                </div>
              </div>
            )}

            {/* Pendulum */}
            {context.pendulum !== undefined && (
              <div style={ROW}>
                <span style={LABEL}>Pendulum</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div
                    style={{
                      ...BAR_BG,
                      position: 'relative',
                    }}
                  >
                    {/* Center mark */}
                    <div
                      style={{
                        position: 'absolute',
                        left: '50%',
                        top: 0,
                        width: 1,
                        height: '100%',
                        background: '#555',
                      }}
                    />
                    {/* Pendulum indicator */}
                    <div
                      style={{
                        position: 'absolute',
                        left: `${50 + (context.pendulum ?? 0) * 50}%`,
                        top: -1,
                        width: 6,
                        height: 6,
                        borderRadius: '50%',
                        background: (context.pendulum ?? 0) >= 0 ? '#EFA830' : '#378ADD',
                        transform: 'translateX(-50%)',
                        transition: 'left 0.3s',
                      }}
                    />
                  </div>
                  <span style={{ ...VALUE, fontSize: 9 }}>
                    {pendulumLabel(context.pendulum ?? 0)}
                  </span>
                </div>
              </div>
            )}

            {/* Dramatic Function */}
            {context.dramatic_function && (
              <div style={ROW}>
                <span style={LABEL}>Function</span>
                <span style={VALUE}>
                  {functionIcon(context.dramatic_function)} {context.dramatic_function.replace(/_/g, ' ')}
                </span>
              </div>
            )}

            {/* McKee Triangle */}
            {context.triangle_pos && (
              <>
                <div style={SECTION_TITLE}>McKee Triangle</div>
                <div style={ROW}>
                  <span style={LABEL}>Archplot</span>
                  <span style={{ ...VALUE, color: '#E24B4A' }}>
                    {((context.triangle_pos.arch ?? 0) * 100).toFixed(0)}%
                  </span>
                </div>
                <div style={ROW}>
                  <span style={LABEL}>Miniplot</span>
                  <span style={{ ...VALUE, color: '#378ADD' }}>
                    {((context.triangle_pos.mini ?? 0) * 100).toFixed(0)}%
                  </span>
                </div>
                <div style={ROW}>
                  <span style={LABEL}>Antiplot</span>
                  <span style={{ ...VALUE, color: '#7F77DD' }}>
                    {((context.triangle_pos.anti ?? 0) * 100).toFixed(0)}%
                  </span>
                </div>
              </>
            )}

            {/* Mini Camelot Wheel */}
            {context.camelot_key && (
              <>
                <div style={SECTION_TITLE}>Harmonic Context</div>
                <div style={{ display: 'flex', justifyContent: 'center', padding: '4px 0' }}>
                  <CamelotWheel
                    activeKey={context.camelot_key}
                    size={120}
                  />
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
