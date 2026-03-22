/**
 * MARKER_CUT_2.2: DAGProjectPanel — ReactFlow DAG with Y = film chronology.
 *
 * Script Spine = central vertical chain of scene_chunk nodes.
 * Media nodes: video left, audio right of linked scene.
 * Y-axis = start_sec * PX_PER_SEC (chronological, top-to-bottom by default).
 *
 * Fetches from GET /api/cut/project/dag/{timeline_id}.
 * Scene chunks created by POST /api/cut/project/apply-script (CUT-2.1).
 *
 * Ref: CUT_TARGET_ARCHITECTURE.md §2.2, CUT_DATA_MODEL.md
 */
import { useCallback, useEffect, useState, type CSSProperties } from 'react';
import {
  ReactFlow,
  Background,
  type Node,
  type Edge,
  type NodeTypes,
  type NodeProps,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { API_BASE } from '../../config/api.config';
import { usePanelSyncStore } from '../../store/usePanelSyncStore';
import { useCutEditorStore } from '../../store/useCutEditorStore';

// ─── Types ───

interface DAGNodeData extends Record<string, unknown> {
  node_id: string;
  label: string;
  node_type: string;
  scene_heading?: string;
  start_sec?: number;
  duration_sec?: number;
  cluster?: string;
  source_path?: string;
  camelot_key?: string;
  energy?: number;
  linked_scene_ids?: string[];
}

// ─── Layout constants ───

const PX_PER_SEC = 3; // pixels per second of film time
const SPINE_X = 150;   // center X for spine nodes (will be adjusted by container)
const MEDIA_OFFSET = 160; // horizontal offset for media nodes

// ─── Custom Node: Scene Chunk (spine) ───

function SceneChunkNode({ data }: NodeProps<Node<DAGNodeData>>) {
  const activeSceneId = usePanelSyncStore((s) => s.activeSceneId);
  const isActive = activeSceneId === data.node_id;

  return (
    <div style={{
      background: isActive ? '#1a2a3a' : '#141414',
      border: `1px solid ${isActive ? '#4a9eff' : '#333'}`,
      borderRadius: 4,
      padding: '4px 8px',
      minWidth: 100,
      maxWidth: 140,
      fontSize: 9,
      fontFamily: 'Inter, system-ui, sans-serif',
      color: '#ccc',
      boxShadow: isActive ? '0 0 8px rgba(74, 158, 255, 0.3)' : 'none',
    }}>
      <Handle type="target" position={Position.Top} style={{ background: '#555', width: 4, height: 4 }} />
      <Handle type="source" position={Position.Bottom} style={{ background: '#555', width: 4, height: 4 }} />

      <div style={{ fontSize: 7, color: '#555', fontFamily: 'monospace', marginBottom: 2 }}>
        {data.node_id}
      </div>
      {data.scene_heading && (
        <div style={{ fontWeight: 600, fontSize: 8, color: '#ccc', textTransform: 'uppercase', letterSpacing: 0.3 }}>
          {data.scene_heading}
        </div>
      )}
      {data.start_sec != null && (
        <div style={{ fontSize: 7, color: '#444', fontFamily: 'monospace', marginTop: 2 }}>
          {formatTC(data.start_sec)}
        </div>
      )}
    </div>
  );
}

// ─── Custom Node: Media asset ───

function MediaAssetNode({ data }: NodeProps<Node<DAGNodeData>>) {
  const activeSceneId = usePanelSyncStore((s) => s.activeSceneId);
  const isLinked = data.linked_scene_ids?.includes(activeSceneId || '') ?? false;

  return (
    <div style={{
      background: '#1A1A1A',
      border: `1px solid ${isLinked ? '#4a9eff' : '#2a2a2a'}`,
      borderRadius: 3,
      padding: '3px 6px',
      minWidth: 80,
      maxWidth: 120,
      fontSize: 8,
      color: '#888',
      boxShadow: isLinked ? '0 0 6px rgba(74, 158, 255, 0.2)' : 'none',
    }}>
      <Handle type="target" position={Position.Left} style={{ background: '#555', width: 3, height: 3 }} />
      <Handle type="source" position={Position.Right} style={{ background: '#555', width: 3, height: 3 }} />

      <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {data.label}
      </div>
      {data.camelot_key && (
        <div style={{ fontSize: 7, color: '#5DCAA5', fontFamily: 'monospace', marginTop: 1 }}>
          {data.camelot_key}
        </div>
      )}
    </div>
  );
}

const NODE_TYPES: NodeTypes = {
  scene_chunk: SceneChunkNode,
  asset: MediaAssetNode,
};

// ─── Layout: Y = chronology, spine center ───
// MARKER_C8.1: flipY=false → START at top, END at bottom (natural reading order)
// flipY=true → inverted (START bottom, END top) — available via toggle button

function layoutNodes(nodes: DAGNodeData[], edges: { source: string; target: string; edge_type: string }[], flipY = false): { rfNodes: Node[]; rfEdges: Edge[] } {
  const rfNodes: Node[] = [];

  // Separate spine nodes from media nodes
  const spineNodes = nodes.filter((n) => n.node_type === 'scene_chunk');
  const mediaNodes = nodes.filter((n) => n.node_type !== 'scene_chunk');

  // Find max time for Y inversion
  const maxSec = spineNodes.reduce((mx, n) => Math.max(mx, (n.start_sec ?? 0) + (n.duration_sec ?? 0)), 0);

  // MARKER_C8.1: Y direction — flipY false = START top, END bottom (positive Y = down in ReactFlow)
  const yPos = (sec: number) => flipY ? -(sec * PX_PER_SEC) : sec * PX_PER_SEC;

  // Place spine nodes: center X, Y = chronological position
  for (const n of spineNodes) {
    rfNodes.push({
      id: n.node_id,
      type: 'scene_chunk',
      position: {
        x: SPINE_X,
        y: yPos(n.start_sec ?? 0),
      },
      data: { ...n },
    });
  }

  // Place media nodes: left (video) or right (audio) of linked scene
  const mediaByScene: Record<string, { left: DAGNodeData[]; right: DAGNodeData[] }> = {};

  for (const m of mediaNodes) {
    // Find linked scene via edges
    const linkedEdge = edges.find(
      (e) => (e.source === m.node_id || e.target === m.node_id) &&
             (e.edge_type === 'has_media' || e.edge_type === 'contains'),
    );
    const sceneId = linkedEdge
      ? (linkedEdge.source === m.node_id ? linkedEdge.target : linkedEdge.source)
      : null;

    if (sceneId) {
      if (!mediaByScene[sceneId]) mediaByScene[sceneId] = { left: [], right: [] };
      const cluster = m.cluster || '';
      if (['music', 'sfx', 'dub'].includes(cluster)) {
        mediaByScene[sceneId].right.push(m);
      } else {
        mediaByScene[sceneId].left.push(m);
      }
    } else {
      // Unlinked media — place after all spine nodes
      const lastSpine = spineNodes[spineNodes.length - 1];
      const baseSec = lastSpine ? (lastSpine.start_sec ?? 0) + (lastSpine.duration_sec ?? 0) : 0;
      const offsetY = flipY ? -(baseSec * PX_PER_SEC + 80 + rfNodes.length * 40) : baseSec * PX_PER_SEC + 80 + rfNodes.length * 40;
      rfNodes.push({
        id: m.node_id,
        type: 'asset',
        position: { x: SPINE_X + MEDIA_OFFSET, y: offsetY },
        data: { ...m },
      });
    }
  }

  // Place linked media around their scene nodes
  for (const [sceneId, sides] of Object.entries(mediaByScene)) {
    const sceneNode = spineNodes.find((n) => n.node_id === sceneId);
    if (!sceneNode) continue;
    const sceneY = yPos(sceneNode.start_sec ?? 0);
    const stepY = flipY ? -35 : 35;

    // Left side (video/takes)
    for (let i = 0; i < sides.left.length; i++) {
      const m = sides.left[i];
      rfNodes.push({
        id: m.node_id,
        type: 'asset',
        position: { x: SPINE_X - MEDIA_OFFSET, y: sceneY + i * stepY },
        data: { ...m },
      });
    }

    // Right side (audio/music/sfx)
    for (let i = 0; i < sides.right.length; i++) {
      const m = sides.right[i];
      rfNodes.push({
        id: m.node_id,
        type: 'asset',
        position: { x: SPINE_X + MEDIA_OFFSET, y: sceneY + i * stepY },
        data: { ...m },
      });
    }
  }

  // Edges
  const rfEdges: Edge[] = edges.map((e, i) => ({
    id: `e_${i}`,
    source: e.source,
    target: e.target,
    type: e.edge_type === 'next_scene' ? 'default' : 'default',
    style: {
      stroke: e.edge_type === 'next_scene' ? '#4a9eff' : '#333',
      strokeWidth: e.edge_type === 'next_scene' ? 2 : 1,
    },
    animated: false,
  }));

  return { rfNodes, rfEdges };
}

// ─── Helpers ───

function formatTC(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

// ─── Styles ───

const PANEL: CSSProperties = {
  width: '100%',
  height: '100%',
  background: '#0D0D0D',
  position: 'relative',
};

// ─── Component ───

interface DAGProjectPanelProps {
  timelineId?: string;
}

export default function DAGProjectPanel({ timelineId: timelineIdProp }: DAGProjectPanelProps) {
  // MARKER_C8.2: Read timelineId from store if not provided via prop
  const storeTimelineId = useCutEditorStore((s) => s.timelineId);
  const timelineId = timelineIdProp ?? storeTimelineId ?? 'main';

  const [dagNodes, setDagNodes] = useState<DAGNodeData[]>([]);
  const [dagEdges, setDagEdges] = useState<{ source: string; target: string; edge_type: string }[]>([]);
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState([] as Node[]);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState([] as Edge[]);
  // MARKER_C8.1: Flip Y toggle — START top (false, default) or START bottom (true)
  const [flipY, setFlipY] = useState(false);

  const syncFromDAG = usePanelSyncStore((s) => s.syncFromDAG);

  // ─── Fetch DAG data ───
  useEffect(() => {
    let cancelled = false;

    async function fetchDAG() {
      try {
        const res = await fetch(`${API_BASE}/cut/project/dag/${timelineId}`);
        if (!res.ok) return;
        const json = await res.json();
        if (!cancelled && json.success !== false) {
          const nodes: DAGNodeData[] = json.nodes || [];
          const edges = json.edges || [];
          setDagNodes(nodes);
          setDagEdges(edges);

          const { rfNodes: rn, rfEdges: re } = layoutNodes(nodes, edges, flipY);
          setRfNodes(rn);
          setRfEdges(re);
        }
      } catch {
        // non-critical
      }
    }

    fetchDAG();
    return () => { cancelled = true; };
  }, [timelineId, setRfNodes, setRfEdges]);

  // MARKER_C8.1: Re-layout when flipY changes (no re-fetch needed)
  useEffect(() => {
    if (dagNodes.length === 0) return;
    const { rfNodes: rn, rfEdges: re } = layoutNodes(dagNodes, dagEdges, flipY);
    setRfNodes(rn);
    setRfEdges(re);
  }, [flipY]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Node click → sync store ───
  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const data = node.data as DAGNodeData;
      syncFromDAG(data.node_id, data.source_path || '');
    },
    [syncFromDAG],
  );

  return (
    <div style={PANEL}>
      {/* MARKER_C8.1: Flip Y toggle */}
      <button
        onClick={() => setFlipY((v) => !v)}
        style={{
          position: 'absolute',
          top: 4,
          right: 4,
          zIndex: 10,
          background: '#1a1a1a',
          border: '1px solid #333',
          borderRadius: 3,
          color: '#888',
          fontSize: 8,
          fontFamily: 'monospace',
          padding: '2px 6px',
          cursor: 'pointer',
        }}
        title={flipY ? 'START at bottom — click for top-down' : 'START at top — click for bottom-up'}
      >
        {flipY ? '↑ START' : '↓ START'}
      </button>
      {dagNodes.length === 0 ? (
        <div style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#444',
          fontSize: 11,
          textAlign: 'center',
          padding: 16,
        }}>
          No assets in DAG. Import script to build spine.
        </div>
      ) : (
        <ReactFlow
          nodes={rfNodes}
          edges={rfEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          nodeTypes={NODE_TYPES}
          fitView
          proOptions={{ hideAttribution: true }}
          style={{ background: '#0D0D0D' }}
          minZoom={0.2}
          maxZoom={3}
        >
          <Background color="#1A1A1A" gap={20} size={1} />
        </ReactFlow>
      )}
    </div>
  );
}
