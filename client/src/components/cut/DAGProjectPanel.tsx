/**
 * MARKER_180.16: DAGProjectPanel — ReactFlow DAG view of project assets.
 *
 * Architecture doc §2.2:
 * "DAG Project panel: material organized by clusters (Characters, Locations,
 *  Takes, Music, SFX, Graphics). Nodes linked to active script line glow blue."
 *
 * Architecture doc §8:
 * "DAG as universal view mode — everything is a DAG: project assets, scene graph,
 *  workflow steps, timeline structure."
 *
 * Shares left column with ScriptPanel as tab (controlled by parent).
 * Fetches from GET /api/cut/project/dag/{timeline_id}.
 */
import { useCallback, useEffect, useMemo, useState, type CSSProperties } from 'react';
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

// ─── Types ───

interface DAGAssetNodeData extends Record<string, unknown> {
  node_id: string;
  label: string;
  node_type: string;
  cluster: string;
  source_path: string;
  duration_sec?: number;
  camelot_key: string;
  pendulum: number;
  energy: number;
  dramatic_function: string;
  linked_scene_ids: string[];
}

type AssetNodeType = Node<DAGAssetNodeData, 'asset'>;

interface DAGEdge {
  source: string;
  target: string;
  edge_type: string;
  label: string;
}

interface DAGData {
  nodes: DAGAssetNodeData[];
  edges: DAGEdge[];
  clusters: Record<string, string[]>;
}

// ─── Cluster visual config (§11 compliant: monochrome with subtle accent) ───

const CLUSTER_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  character: { label: 'Characters', color: '#E24B4A', icon: '👤' },
  location:  { label: 'Locations',  color: '#5DCAA5', icon: '📍' },
  take:      { label: 'Takes',      color: '#4a9eff', icon: '🎬' },
  dub:       { label: 'Dub',        color: '#EFA830', icon: '🎙' },
  music:     { label: 'Music',      color: '#85B7EB', icon: '♩' },
  sfx:       { label: 'SFX',        color: '#7F77DD', icon: '🔊' },
  graphics:  { label: 'Graphics',   color: '#D94B8D', icon: '🖼' },
  other:     { label: 'Other',      color: '#888',    icon: '●' },
};

// ─── Custom Node Component ───

function AssetNode({ data, selected }: NodeProps<AssetNodeType>) {
  const activeSceneId = usePanelSyncStore((s) => s.activeSceneId);

  // Blue glow if linked to active script scene
  const isLinked = useMemo(() => {
    if (!activeSceneId || !data.linked_scene_ids) return false;
    return data.linked_scene_ids.includes(activeSceneId);
  }, [activeSceneId, data.linked_scene_ids]);

  const clusterCfg = CLUSTER_CONFIG[data.cluster] || CLUSTER_CONFIG.other;

  return (
    <div
      style={{
        background: '#1A1A1A',
        border: `1px solid ${isLinked ? '#4a9eff' : selected ? '#E0E0E0' : '#333'}`,
        borderRadius: 4,
        padding: '6px 10px',
        minWidth: 100,
        maxWidth: 160,
        fontSize: 10,
        fontFamily: 'Inter, system-ui, sans-serif',
        color: '#E0E0E0',
        cursor: 'pointer',
        boxShadow: isLinked ? '0 0 8px rgba(74, 158, 255, 0.3)' : 'none',
        transition: 'border-color 0.2s, box-shadow 0.2s',
      }}
    >
      {/* Handles */}
      <Handle type="target" position={Position.Top} style={{ background: '#555', width: 4, height: 4 }} />
      <Handle type="source" position={Position.Bottom} style={{ background: '#555', width: 4, height: 4 }} />

      {/* Cluster badge */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          marginBottom: 3,
        }}
      >
        <span style={{ fontSize: 8, color: clusterCfg.color }}>{clusterCfg.icon}</span>
        <span
          style={{
            fontSize: 7,
            color: clusterCfg.color,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            fontWeight: 600,
          }}
        >
          {clusterCfg.label}
        </span>
      </div>

      {/* Label */}
      <div
        style={{
          fontSize: 10,
          color: '#E0E0E0',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {data.label}
      </div>

      {/* PULSE mini-bar */}
      {data.camelot_key && (
        <div
          style={{
            display: 'flex',
            gap: 6,
            marginTop: 4,
            fontSize: 8,
            color: '#555',
            fontFamily: '"JetBrains Mono", monospace',
          }}
        >
          <span style={{ color: '#5DCAA5' }}>{data.camelot_key}</span>
          <span>E:{((data.energy || 0) * 100).toFixed(0)}%</span>
        </div>
      )}
    </div>
  );
}

const NODE_TYPES: NodeTypes = {
  asset: AssetNode,
};

// ─── Layout: arrange nodes by cluster in columns ───

function layoutNodes(dagData: DAGData): { nodes: Node[]; edges: Edge[] } {
  const clusterOrder = ['character', 'location', 'take', 'dub', 'music', 'sfx', 'graphics', 'other'];
  const COL_WIDTH = 180;
  const ROW_HEIGHT = 70;
  const CLUSTER_GAP = 30;

  const nodes: Node[] = [];
  let colX = 0;

  for (const cluster of clusterOrder) {
    const clusterNodes = dagData.nodes.filter((n) => n.cluster === cluster);
    if (clusterNodes.length === 0) continue;

    for (let i = 0; i < clusterNodes.length; i++) {
      const n = clusterNodes[i];
      nodes.push({
        id: n.node_id,
        type: 'asset',
        position: { x: colX, y: i * ROW_HEIGHT + 10 },
        data: {
          label: n.label,
          cluster: n.cluster,
          camelot_key: n.camelot_key,
          energy: n.energy,
          pendulum: n.pendulum,
          linked_scene_ids: n.linked_scene_ids,
          source_path: n.source_path,
          node_id: n.node_id,
        },
      });
    }

    colX += COL_WIDTH + CLUSTER_GAP;
  }

  // Edges
  const edges: Edge[] = dagData.edges.map((e, i) => ({
    id: `e_${i}`,
    source: e.source,
    target: e.target,
    type: 'default',
    style: { stroke: '#333', strokeWidth: 1 },
    animated: e.edge_type === 'sync',
    label: undefined,
  }));

  return { nodes, edges };
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

export default function DAGProjectPanel({ timelineId = 'main' }: DAGProjectPanelProps) {
  const [dagData, setDagData] = useState<DAGData | null>(null);
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState([] as Node[]);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState([] as Edge[]);

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
          const data: DAGData = {
            nodes: json.nodes || [],
            edges: json.edges || [],
            clusters: json.clusters || {},
          };
          setDagData(data);

          const { nodes, edges } = layoutNodes(data);
          setRfNodes(nodes);
          setRfEdges(edges);
        }
      } catch {
        // non-critical
      }
    }

    fetchDAG();
    return () => { cancelled = true; };
  }, [timelineId, setRfNodes, setRfEdges]);

  // ─── Node click → sync store ───
  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const data = node.data as any;
      syncFromDAG(data.node_id, data.source_path || '');
    },
    [syncFromDAG],
  );

  return (
    <div style={PANEL}>
      {(!dagData || dagData.nodes.length === 0) ? (
        <div
          style={{
            width: '100%',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#444',
            fontSize: 11,
            fontFamily: 'Inter, system-ui, sans-serif',
            textAlign: 'center',
            padding: 16,
          }}
        >
          No assets in DAG. Import media to build project graph.
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
          minZoom={0.3}
          maxZoom={2}
        >
          <Background color="#1A1A1A" gap={20} size={1} />
        </ReactFlow>
      )}
    </div>
  );
}
