/**
 * MARKER_170.8.SCENE_GRAPH_MARKERS
 * Music-sync marker node for Scene Graph DAG visualization.
 * Color-coded by source: purple (transcript), pink (energy), amber (hybrid).
 */
import { memo, type CSSProperties } from 'react';

export type MarkerNodeData = {
  markerId: string;
  label: string;
  startSec: number;
  endSec: number;
  source: 'transcript_pause' | 'energy_pause' | 'hybrid';
  confidence: number;
};

const SOURCE_COLORS: Record<string, string> = {
  transcript_pause: '#8b5cf6', // purple
  energy_pause: '#ec4899',     // pink
  hybrid: '#f59e0b',            // amber
};

const MarkerNode = memo(({ data }: { data: MarkerNodeData }) => {
  const durationSec = Math.max(0.1, data.endSec - data.startSec);
  const width = Math.max(48, Math.min(200, durationSec * 40));
  const sourceColor = SOURCE_COLORS[data.source] || '#6b7280';

  const style: CSSProperties = {
    width: `${width}px`,
    padding: '6px 8px',
    borderRadius: 4,
    background: sourceColor,
    border: `1.5px solid ${sourceColor}`,
    opacity: Math.max(0.4, data.confidence),
    fontSize: 11,
    fontWeight: 600,
    color: 'white',
    textAlign: 'center',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    cursor: 'pointer',
    userSelect: 'none',
    transition: 'opacity 0.15s',
  };

  return (
    <div
      style={style}
      data-testid="marker-node"
      data-marker-id={data.markerId}
      data-marker-label={data.label}
      data-marker-source={data.source}
      title={`${data.label} (${data.source}) — ${data.startSec.toFixed(1)}s–${data.endSec.toFixed(1)}s`}
    >
      {data.label}
    </div>
  );
});

MarkerNode.displayName = 'MarkerNode';

export default MarkerNode;
