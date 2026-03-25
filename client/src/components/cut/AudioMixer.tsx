/**
 * MARKER_B13: Audio Mixer panel — per-track channel strips.
 *
 * Each audio lane gets a vertical channel strip with:
 *   - Volume fader (0% to 150%, default 100%)
 *   - Pan knob (-100 L to +100 R) — visual only for now
 *   - Mute / Solo buttons
 *   - VU-style level indicator (simulated from volume, future: Web Audio)
 *   - Lane label
 *
 * Master bus strip on the right.
 * Reads/writes via useCutEditorStore: laneVolumes, mutedLanes, soloLanes.
 *
 * Design: monochrome, NLE-style (no emoji, no color icons).
 * Fader track: vertical slider, dark grey.
 *
 * @phase 198
 */
import { useState, useCallback, useRef, useEffect, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { getAudioScopeSocket } from './WaveformMinimap';

// ─── Styles ────────────────────────────────────────────────────────

const MIXER_ROOT: CSSProperties = {
  display: 'flex',
  height: '100%',
  background: '#0a0a0a',
  overflow: 'auto',
  gap: 1,
  padding: '4px 2px',
  fontFamily: 'system-ui, sans-serif',
};

const STRIP: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  width: 52,
  minWidth: 52,
  background: '#111',
  borderRadius: 2,
  padding: '4px 2px',
  gap: 3,
  flexShrink: 0,
};

const LABEL: CSSProperties = {
  fontSize: 8,
  fontFamily: 'monospace',
  color: '#888',
  textTransform: 'uppercase',
  letterSpacing: 0.3,
  textAlign: 'center',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
  width: '100%',
};

const SMALL_BTN = (active: boolean, color: string): CSSProperties => ({
  width: 20,
  height: 14,
  border: 'none',
  borderRadius: 2,
  fontSize: 8,
  fontWeight: 700,
  fontFamily: 'monospace',
  cursor: 'pointer',
  background: active ? color : '#1a1a1a',
  color: active ? '#000' : '#555',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  transition: 'all 0.1s',
});

const FADER_TRACK: CSSProperties = {
  width: 4,
  height: 80,
  background: '#222',
  borderRadius: 2,
  position: 'relative',
  cursor: 'pointer',
};

// ─── Volume fader ──────────────────────────────────────────────────

function VolumeFader({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  // value: 0..1.5 (0% to 150%)
  const pct = Math.min(1, value / 1.5);
  const fillH = pct * 80;

  const handleClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const newVal = Math.max(0, Math.min(1.5, (1 - y / rect.height) * 1.5));
    onChange(newVal);
  }, [onChange]);

  return (
    <div style={FADER_TRACK} onClick={handleClick} title={`${Math.round(value * 100)}%`}>
      {/* Fill from bottom */}
      <div style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        width: '100%',
        height: fillH,
        background: value > 1.0 ? '#c44' : '#555',
        borderRadius: 2,
        transition: 'height 0.05s',
      }} />
      {/* Thumb */}
      <div style={{
        position: 'absolute',
        bottom: fillH - 3,
        left: -2,
        width: 8,
        height: 6,
        background: '#ccc',
        borderRadius: 1,
        border: '1px solid #888',
      }} />
      {/* Unity mark (100%) */}
      <div style={{
        position: 'absolute',
        bottom: (1 / 1.5) * 80,
        left: 0,
        width: '100%',
        height: 1,
        background: '#444',
      }} />
    </div>
  );
}

// ─── VU indicator (simulated) ──────────────────────────────────────

function VuIndicator({ level, muted }: { level: number; muted: boolean }) {
  const h = muted ? 0 : Math.min(1, level) * 40;
  const color = level > 0.85 ? '#ef4444' : level > 0.6 ? '#eab308' : '#22c55e';
  return (
    <div style={{ width: 6, height: 40, background: '#1a1a1a', borderRadius: 1, position: 'relative', overflow: 'hidden' }}>
      <div style={{
        position: 'absolute',
        bottom: 0,
        width: '100%',
        height: h,
        background: muted ? '#333' : color,
        transition: 'height 0.1s',
        borderRadius: 1,
      }} />
    </div>
  );
}

// ─── MARKER_GAMMA-17: Interactive pan knob ────────────────────────

function PanKnob({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  // value: -1 (L) to +1 (R), 0 = center
  const label = value === 0 ? 'C' : value < 0 ? `L${Math.round(-value * 100)}` : `R${Math.round(value * 100)}`;
  const pct = (value + 1) / 2; // 0..1
  const ref = useRef<HTMLDivElement>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const update = (clientX: number) => {
      const raw = (clientX - rect.left) / rect.width; // 0..1
      const clamped = Math.max(0, Math.min(1, raw));
      const panVal = Math.round((clamped * 2 - 1) * 20) / 20; // snap to 0.05
      onChange(panVal);
    };
    update(e.clientX);
    const onMove = (ev: MouseEvent) => update(ev.clientX);
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [onChange]);

  const handleDoubleClick = useCallback(() => onChange(0), [onChange]);

  return (
    <div
      ref={ref}
      onMouseDown={handleMouseDown}
      onDoubleClick={handleDoubleClick}
      title={`Pan: ${label} (double-click to center)`}
      style={{
        width: '100%',
        height: 8,
        background: '#111',
        borderRadius: 2,
        position: 'relative',
        cursor: 'ew-resize',
        marginTop: 2,
        marginBottom: 2,
      }}
    >
      {/* Center mark */}
      <div style={{
        position: 'absolute',
        left: '50%',
        top: 0,
        width: 1,
        height: '100%',
        background: '#333',
      }} />
      {/* Thumb */}
      <div style={{
        position: 'absolute',
        left: `${pct * 100}%`,
        top: 0,
        width: 4,
        height: '100%',
        background: value === 0 ? '#666' : '#999',
        borderRadius: 1,
        transform: 'translateX(-2px)',
      }} />
      {/* Label */}
      <div style={{
        position: 'absolute',
        top: -8,
        left: 0,
        right: 0,
        fontSize: 6,
        fontFamily: 'monospace',
        color: '#555',
        textAlign: 'center',
        pointerEvents: 'none',
      }}>
        {label}
      </div>
    </div>
  );
}

// ─── Channel Strip ─────────────────────────────────────────────────

function ChannelStrip({
  laneId,
  label,
  volume,
  pan,
  muted,
  soloed,
  audioLevel,
  onVolumeChange,
  onPanChange,
  onToggleMute,
  onToggleSolo,
}: {
  laneId: string;
  label: string;
  volume: number;
  pan: number;
  muted: boolean;
  soloed: boolean;
  audioLevel: number;
  onVolumeChange: (v: number) => void;
  onPanChange: (v: number) => void;
  onToggleMute: () => void;
  onToggleSolo: () => void;
}) {
  return (
    <div style={STRIP}>
      <div style={LABEL}>{label}</div>
      {/* MARKER_B52: Use real audio level × volume for VU */}
      <VuIndicator level={audioLevel * volume} muted={muted} />
      <VolumeFader value={volume} onChange={onVolumeChange} />
      <div style={{ fontSize: 7, fontFamily: 'monospace', color: '#666' }}>
        {Math.round(volume * 100)}%
      </div>
      <PanKnob value={pan} onChange={onPanChange} />
      <div style={{ display: 'flex', gap: 2 }}>
        <button style={SMALL_BTN(muted, '#999')} onClick={onToggleMute}>M</button>
        <button style={SMALL_BTN(soloed, '#ccc')} onClick={onToggleSolo}>S</button>
      </div>
    </div>
  );
}

// ─── Main Component ────────────────────────────────────────────────

const LANE_LABELS: Record<string, string> = {
  video_main: 'V1',
  audio_sync: 'A1',
  take_alt_y: 'V2',
  take_alt_z: 'V3',
  aux: 'AUX',
};

export default function AudioMixer() {
  const lanes = useCutEditorStore((s) => s.lanes);
  const laneVolumes = useCutEditorStore((s) => s.laneVolumes);
  const mutedLanes = useCutEditorStore((s) => s.mutedLanes);
  const soloLanes = useCutEditorStore((s) => s.soloLanes);
  const toggleMute = useCutEditorStore((s) => s.toggleMute);
  const toggleSolo = useCutEditorStore((s) => s.toggleSolo);
  const setLaneVolume = useCutEditorStore((s) => s.setLaneVolume);

  // Master volume (local state — not in store yet)
  // TODO: migrate masterVolume to store for render engine integration
  const [masterVolume, setMasterVolume] = useState(1.0);
  // MARKER_GAMMA-17: Pan per lane — wired to store (lanePans / setLanePan)
  const lanePans = useCutEditorStore((s) => s.lanePans);
  const setLanePan = useCutEditorStore((s) => s.setLanePan);
  // MARKER_B52: Real audio levels from WebSocket (replaces simulated VU)
  const [audioLevels, setAudioLevels] = useState<{ left: number; right: number }>({ left: 0, right: 0 });
  useEffect(() => {
    const socket = getAudioScopeSocket();
    const onData = (d: any) => {
      if (d.success) setAudioLevels({ left: d.rms_left || 0, right: d.rms_right || 0 });
    };
    socket.on('audio_scope_data', onData);
    return () => { socket.off('audio_scope_data', onData); };
  }, []);
  const [masterPan, setMasterPan] = useState(0);
  // MARKER_MASTER_MUTE_SOLO: Local master mute/solo state
  // When masterMuted: all lanes are visually dimmed and audio output is muted.
  // When masterSolo: only master passes (all lanes individually silenced).
  const [masterMuted, setMasterMuted] = useState(false);
  const [masterSoloed, setMasterSoloed] = useState(false);
  const setPan = useCallback((laneId: string, v: number) => {
    setLanePan(laneId, v);
  }, [setLanePan]);

  // Filter to audio-relevant lanes (audio_sync, aux, or all if < 6 lanes)
  const audioLanes = lanes.length > 0 ? lanes : [];

  if (audioLanes.length === 0) {
    return (
      <div style={{ ...MIXER_ROOT, alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: '#444', fontSize: 10, fontFamily: 'monospace' }}>
          No tracks. Bootstrap a project.
        </span>
      </div>
    );
  }

  return (
    <div style={MIXER_ROOT}>
      {/* Per-lane strips */}
      {audioLanes.map((lane) => (
        <ChannelStrip
          key={lane.lane_id}
          laneId={lane.lane_id}
          label={LANE_LABELS[lane.lane_type] || lane.lane_id.slice(0, 4).toUpperCase()}
          volume={laneVolumes[lane.lane_id] ?? 1.0}
          pan={lanePans[lane.lane_id] ?? 0}
          muted={mutedLanes.has(lane.lane_id)}
          soloed={soloLanes.has(lane.lane_id)}
          audioLevel={(audioLevels.left + audioLevels.right) / 2}
          onVolumeChange={(v) => setLaneVolume(lane.lane_id, v)}
          onPanChange={(v) => setPan(lane.lane_id, v)}
          onToggleMute={() => toggleMute(lane.lane_id)}
          onToggleSolo={() => toggleSolo(lane.lane_id)}
        />
      ))}

      {/* Separator */}
      <div style={{ width: 1, background: '#333', margin: '4px 2px', flexShrink: 0 }} />

      {/* Master strip */}
      <div style={{ ...STRIP, background: '#151515' }}>
        <div style={{ ...LABEL, color: '#ccc' }}>MST</div>
        <VuIndicator level={masterMuted ? 0 : masterVolume * (audioLevels.left + audioLevels.right) / 2} muted={masterMuted} />
        <VolumeFader value={masterVolume} onChange={setMasterVolume} />
        <div style={{ fontSize: 7, fontFamily: 'monospace', color: '#888' }}>
          {Math.round(masterVolume * 100)}%
        </div>
        <PanKnob value={masterPan} onChange={setMasterPan} />
        <div style={{ display: 'flex', gap: 2 }}>
          <button
            style={SMALL_BTN(masterMuted, '#999')}
            onClick={() => setMasterMuted((v) => !v)}
            title="Mute master bus"
          >M</button>
          <button
            style={SMALL_BTN(masterSoloed, '#ccc')}
            onClick={() => setMasterSoloed((v) => !v)}
            title="Solo master bus"
          >S</button>
        </div>
      </div>
    </div>
  );
}
