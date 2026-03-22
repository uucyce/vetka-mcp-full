/**
 * MARKER_B33: Mixer View Presets — 4 bank buttons for track visibility.
 *
 * FCP7 Ch.55 (p.885): Audio Mixer has 4 View buttons that store
 * which tracks are visible in the mixer panel. Click a view button
 * to switch between track banks (useful with 12+ tracks).
 *
 * @phase B33
 * @task tb_1773996025_9
 */
import { useState, useCallback, type CSSProperties } from 'react';

interface MixerViewPresetsProps {
  /** All lane IDs available */
  allLaneIds: string[];
  /** Currently visible lane IDs (controlled) */
  visibleLaneIds: Set<string>;
  /** Called when visibility changes */
  onVisibilityChange: (visibleIds: Set<string>) => void;
}

type ViewPreset = {
  label: string;
  laneIds: Set<string> | null; // null = "all" (not yet configured)
};

const BTN_STYLE = (active: boolean): CSSProperties => ({
  width: 16,
  height: 14,
  border: active ? '1px solid #666' : '1px solid #333',
  borderRadius: 2,
  background: active ? '#222' : '#111',
  color: active ? '#ccc' : '#555',
  fontSize: 8,
  fontFamily: 'monospace',
  fontWeight: active ? 700 : 400,
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 0,
});

const BAR_STYLE: CSSProperties = {
  display: 'flex',
  gap: 2,
  padding: '2px 4px',
  alignItems: 'center',
  flexShrink: 0,
};

export default function MixerViewPresets({
  allLaneIds,
  visibleLaneIds,
  onVisibilityChange,
}: MixerViewPresetsProps) {
  const [presets, setPresets] = useState<ViewPreset[]>([
    { label: '1', laneIds: null },
    { label: '2', laneIds: null },
    { label: '3', laneIds: null },
    { label: '4', laneIds: null },
  ]);
  const [activePreset, setActivePreset] = useState(-1); // -1 = no preset active

  const handleClick = useCallback((index: number) => {
    const preset = presets[index];
    if (preset.laneIds) {
      // Recall preset
      onVisibilityChange(new Set(preset.laneIds));
      setActivePreset(index);
    } else {
      // First click on unconfigured preset = store current visibility
      const updated = [...presets];
      updated[index] = { ...preset, laneIds: new Set(visibleLaneIds) };
      setPresets(updated);
      setActivePreset(index);
    }
  }, [presets, visibleLaneIds, onVisibilityChange]);

  // Option+Click = store current visibility into preset
  const handleOptionClick = useCallback((index: number, e: React.MouseEvent) => {
    if (e.altKey) {
      e.preventDefault();
      const updated = [...presets];
      updated[index] = { ...presets[index], laneIds: new Set(visibleLaneIds) };
      setPresets(updated);
      setActivePreset(index);
    } else {
      handleClick(index);
    }
  }, [presets, visibleLaneIds, handleClick]);

  // "All" button — show all tracks
  const handleShowAll = useCallback(() => {
    onVisibilityChange(new Set(allLaneIds));
    setActivePreset(-1);
  }, [allLaneIds, onVisibilityChange]);

  return (
    <div style={BAR_STYLE} data-testid="mixer-view-presets">
      <button
        style={BTN_STYLE(activePreset === -1)}
        onClick={handleShowAll}
        title="Show all tracks"
      >
        A
      </button>
      {presets.map((preset, i) => (
        <button
          key={i}
          style={BTN_STYLE(activePreset === i)}
          onClick={(e) => handleOptionClick(i, e)}
          title={preset.laneIds ? `View ${preset.label} (${preset.laneIds.size} tracks) — Option+click to overwrite` : `View ${preset.label} — click to store current`}
        >
          {preset.label}
        </button>
      ))}
    </div>
  );
}
