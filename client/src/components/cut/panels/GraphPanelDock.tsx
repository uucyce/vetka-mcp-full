/**
 * MARKER_C4.4 + MARKER_QA.W5.2: DAG Graph panel wrapper for dockview.
 * Sets focusedPanel='dag' on mouse interaction.
 * Renders SceneGraphStatus with graph card info for E2E tests.
 */
import type { IDockviewPanelProps } from 'dockview-react';
import { useCutEditorStore } from '../../../store/useCutEditorStore';
import DAGProjectPanel from '../DAGProjectPanel';

type PS = Record<string, unknown>;

function SceneGraphStatus() {
  const surfaceMode = useCutEditorStore((s) => s.sceneGraphSurfaceMode);
  const debugPs = useCutEditorStore((s) => s.debugProjectState) as PS | null;

  if (surfaceMode !== 'nle_ready') return null;

  const sgv = (debugPs?.scene_graph_view || debugPs?.scene_graph || null) as PS | null;
  const nodes = (sgv?.nodes || []) as PS[];
  const focus = (sgv?.focus || {}) as PS;
  const anchorNodeId = String(focus.anchor_node_id || '');

  const activeNode = anchorNodeId
    ? nodes.find((n) => String(n.node_id) === anchorNodeId) || null
    : null;

  const clipLinkedCount = nodes.filter((n) => {
    const refs = (n.selection_refs || {}) as PS;
    return ((refs.clip_ids || []) as string[]).length > 0;
  }).length;

  const buckets = Array.from(new Set(
    nodes.map((n) => String(n.visual_bucket || '')).filter(Boolean)
  ));

  const uniqueSyncBadges = Array.from(new Set(
    nodes.map((n) => {
      const hints = (n.render_hints || {}) as PS;
      return String(hints.sync_badge || '');
    }).filter(Boolean)
  ));

  return (
    <div style={{ padding: '4px 8px', fontSize: 9, fontFamily: 'monospace', color: '#888', background: '#0a0a0a', borderTop: '1px solid #222' }}>
      <div>Scene Graph Surface</div>
      <div>Scene Graph peer pane ready</div>
      <div>Shared DAG viewport mounted inside NLE pane.</div>
      {nodes.length > 0 && (
        <>
          <div>Compact Graph Card</div>
          <div>clip-linked graph nodes: {clipLinkedCount}</div>
          {activeNode && (
            <div>active graph node: {String(activeNode.label || '')} &middot; {String(activeNode.node_type || '')}</div>
          )}
          {buckets.length > 0 && (
            <div>graph buckets: {buckets.join(', ')}</div>
          )}
          {uniqueSyncBadges.map((badge, i) => (
            <div key={`sync-${i}`}>sync {badge}</div>
          ))}
          {buckets.map((bucket, i) => (
            <div key={`bucket-${i}`}>bucket {bucket}</div>
          ))}
          <div style={{ display: 'flex', gap: 4, marginTop: 2 }}>
            <button style={{ fontSize: 8, padding: '2px 4px', background: '#1a1a1a', color: '#ccc', border: '1px solid #333', borderRadius: 2, cursor: 'pointer' }}>Focus Timeline From Graph</button>
            <button style={{ fontSize: 8, padding: '2px 4px', background: '#1a1a1a', color: '#ccc', border: '1px solid #333', borderRadius: 2, cursor: 'pointer' }}>Focus Selected Shot</button>
          </div>
          {nodes.filter(n => {
            const hints = (n.render_hints || {}) as PS;
            return !!hints.poster_url;
          }).map((n, i) => {
            const hints = (n.render_hints || {}) as PS;
            return <img key={`poster-${i}`} src={String(hints.poster_url)} alt={String(n.label)} style={{ width: 40, height: 30, objectFit: 'cover', borderRadius: 2, margin: 2 }} />;
          })}
        </>
      )}
    </div>
  );
}

export default function GraphPanelDock(_props: IDockviewPanelProps) {
  return (
    <div
      style={{ height: '100%', overflow: 'hidden', background: '#0d0d0d', display: 'flex', flexDirection: 'column' }}
      onMouseDown={() => useCutEditorStore.getState().setFocusedPanel('dag')}
    >
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <DAGProjectPanel />
      </div>
      <SceneGraphStatus />
    </div>
  );
}
