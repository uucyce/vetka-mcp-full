/**
 * MARKER_144.2: DAG Editor Hook — encapsulates workflow editing state.
 *
 * Provides:
 * - addNode / removeNode / updateNodeData
 * - addEdge / removeEdge
 * - undo / redo (history stack, max 50)
 * - save / load (workflow persistence via API)
 * - validate (client calls server validation)
 *
 * ADDITIVE: Does NOT modify existing DAGView behavior.
 * Only active when editMode=true in MCC store.
 *
 * @phase 144
 * @status active
 */

import { useCallback, useRef, useState } from 'react';
import type { Connection } from '@xyflow/react';
import type { DAGNode, DAGEdge, DAGNodeType, EdgeType, Workflow, WorkflowSummary } from '../types/dag';
import { BACKEND_ORIGIN } from '../config/api.config';

const PIPELINE_API = BACKEND_ORIGIN;
const MAX_HISTORY = 50;

interface DAGSnapshot {
  nodes: DAGNode[];
  edges: DAGEdge[];
}

interface UseDAGEditorReturn {
  // State
  workflowId: string | null;
  workflowName: string;
  isDirty: boolean;
  canUndo: boolean;
  canRedo: boolean;

  // Node operations
  addNode: (type: DAGNodeType, position: { x: number; y: number }, label?: string) => DAGNode;
  removeNode: (nodeId: string) => void;
  updateNodeData: (nodeId: string, data: Partial<DAGNode>) => void;

  // Edge operations
  addEdge: (source: string, target: string, type?: EdgeType, label?: string) => DAGEdge | null;
  handleConnect: (connection: Connection) => void;
  removeEdge: (edgeId: string) => void;

  // History
  undo: () => void;
  redo: () => void;
  pushSnapshot: (nodes: DAGNode[], edges: DAGEdge[]) => void;

  // Persistence
  save: (name?: string) => Promise<string | null>;
  load: (workflowId: string) => Promise<boolean>;
  listWorkflows: () => Promise<WorkflowSummary[]>;
  validate: () => Promise<{ valid: boolean; errors: any[]; warnings: any[] }>;

  // Reset
  newWorkflow: () => void;
  setWorkflowName: (name: string) => void;
}

let _nodeCounter = 0;
let _edgeCounter = 0;

export function useDAGEditor(
  nodes: DAGNode[],
  edges: DAGEdge[],
  setNodes: (updater: DAGNode[] | ((prev: DAGNode[]) => DAGNode[])) => void,
  setEdges: (updater: DAGEdge[] | ((prev: DAGEdge[]) => DAGEdge[])) => void,
): UseDAGEditorReturn {
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [workflowName, setWorkflowName] = useState('Untitled Workflow');
  const [isDirty, setIsDirty] = useState(false);

  // History stacks
  const historyRef = useRef<DAGSnapshot[]>([]);
  const futureRef = useRef<DAGSnapshot[]>([]);
  const nodesRef = useRef(nodes);
  const edgesRef = useRef(edges);
  nodesRef.current = nodes;
  edgesRef.current = edges;

  // --- Snapshot management ---
  const pushSnapshot = useCallback((snapshotNodes: DAGNode[], snapshotEdges: DAGEdge[]) => {
    historyRef.current.push({
      nodes: JSON.parse(JSON.stringify(snapshotNodes)),
      edges: JSON.parse(JSON.stringify(snapshotEdges)),
    });
    if (historyRef.current.length > MAX_HISTORY) {
      historyRef.current.shift();
    }
    futureRef.current = []; // Clear redo stack on new action
    setIsDirty(true);
  }, []);

  // --- Node operations ---
  const addNode = useCallback((
    type: DAGNodeType,
    position: { x: number; y: number },
    label?: string,
  ): DAGNode => {
    pushSnapshot(nodesRef.current, edgesRef.current);

    _nodeCounter++;
    const newNode: DAGNode = {
      id: `wf_node_${Date.now()}_${_nodeCounter}`,
      type,
      label: label || `${type} ${_nodeCounter}`,
      status: 'pending',
      layer: 0,
      taskId: workflowId || 'draft',
      // Store position in description field for layout (DAGNode doesn't have position)
      description: JSON.stringify(position),
    };

    setNodes((prev: DAGNode[]) => [...prev, newNode]);
    return newNode;
  }, [pushSnapshot, setNodes, workflowId]);

  const removeNode = useCallback((nodeId: string) => {
    pushSnapshot(nodesRef.current, edgesRef.current);
    setNodes((prev: DAGNode[]) => prev.filter(n => n.id !== nodeId));
    // Also remove connected edges
    setEdges((prev: DAGEdge[]) => prev.filter(e => e.source !== nodeId && e.target !== nodeId));
  }, [pushSnapshot, setNodes, setEdges]);

  const updateNodeData = useCallback((nodeId: string, data: Partial<DAGNode>) => {
    pushSnapshot(nodesRef.current, edgesRef.current);
    setNodes((prev: DAGNode[]) =>
      prev.map(n => n.id === nodeId ? { ...n, ...data } : n)
    );
  }, [pushSnapshot, setNodes]);

  // --- Edge operations ---
  const addEdge = useCallback((
    source: string,
    target: string,
    type: EdgeType = 'structural',
    label?: string,
  ): DAGEdge | null => {
    // Prevent duplicate edges
    const exists = edgesRef.current.some(
      e => e.source === source && e.target === target
    );
    if (exists) return null;

    pushSnapshot(nodesRef.current, edgesRef.current);

    _edgeCounter++;
    const newEdge: DAGEdge = {
      id: `wf_edge_${Date.now()}_${_edgeCounter}`,
      source,
      target,
      type,
      strength: 0.8,
    };

    setEdges((prev: DAGEdge[]) => [...prev, newEdge]);
    return newEdge;
  }, [pushSnapshot, setEdges]);

  const handleConnect = useCallback((connection: Connection) => {
    if (connection.source && connection.target) {
      addEdge(connection.source, connection.target);
    }
  }, [addEdge]);

  const removeEdge = useCallback((edgeId: string) => {
    pushSnapshot(nodesRef.current, edgesRef.current);
    setEdges((prev: DAGEdge[]) => prev.filter(e => e.id !== edgeId));
  }, [pushSnapshot, setEdges]);

  // --- History ---
  const canUndo = historyRef.current.length > 0;
  const canRedo = futureRef.current.length > 0;

  const undo = useCallback(() => {
    if (historyRef.current.length === 0) return;

    // Save current state to future
    futureRef.current.push({
      nodes: JSON.parse(JSON.stringify(nodesRef.current)),
      edges: JSON.parse(JSON.stringify(edgesRef.current)),
    });

    const snapshot = historyRef.current.pop()!;
    setNodes(snapshot.nodes);
    setEdges(snapshot.edges);
    setIsDirty(true);
  }, [setNodes, setEdges]);

  const redo = useCallback(() => {
    if (futureRef.current.length === 0) return;

    // Save current state to history
    historyRef.current.push({
      nodes: JSON.parse(JSON.stringify(nodesRef.current)),
      edges: JSON.parse(JSON.stringify(edgesRef.current)),
    });

    const snapshot = futureRef.current.pop()!;
    setNodes(snapshot.nodes);
    setEdges(snapshot.edges);
    setIsDirty(true);
  }, [setNodes, setEdges]);

  // --- Persistence ---
  const save = useCallback(async (name?: string): Promise<string | null> => {
    const saveName = name || workflowName;
    const payload = {
      id: workflowId || undefined,
      name: saveName,
      nodes: nodesRef.current.map(n => ({
        id: n.id,
        type: n.type,
        label: n.label,
        position: n.description ? (() => { try { return JSON.parse(n.description); } catch { return { x: 0, y: 0 }; } })() : { x: 0, y: 0 },
        data: {
          status: n.status,
          role: n.role,
          model: n.model,
          taskId: n.taskId,
        },
      })),
      edges: edgesRef.current.map(e => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: e.type,
        label: (e as any).label,
      })),
    };

    try {
      const method = workflowId ? 'PUT' : 'POST';
      const url = workflowId
        ? `${PIPELINE_API}/api/workflows/${workflowId}`
        : `${PIPELINE_API}/api/workflows`;

      const resp = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (data.success && data.id) {
        setWorkflowId(data.id);
        setWorkflowName(saveName);
        setIsDirty(false);
        return data.id;
      }
      return null;
    } catch (err) {
      console.error('[useDAGEditor] save error:', err);
      return null;
    }
  }, [workflowId, workflowName]);

  const load = useCallback(async (wfId: string): Promise<boolean> => {
    try {
      const resp = await fetch(`${PIPELINE_API}/api/workflows/${wfId}`);
      const data = await resp.json();
      if (!data.success || !data.workflow) return false;

      const wf: Workflow = data.workflow;
      setWorkflowId(wf.id);
      setWorkflowName(wf.name);

      // Convert workflow nodes → DAGNode
      const dagNodes: DAGNode[] = wf.nodes.map(n => ({
        id: n.id,
        type: n.type,
        label: n.label,
        status: (n.data?.status as any) || 'pending',
        layer: 0,
        taskId: wf.id,
        role: n.data?.role,
        model: n.data?.model,
        description: JSON.stringify(n.position),
      }));

      // Convert workflow edges → DAGEdge
      const dagEdges: DAGEdge[] = wf.edges.map(e => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: e.type,
        strength: 0.8,
      }));

      // Clear history on load
      historyRef.current = [];
      futureRef.current = [];

      setNodes(dagNodes);
      setEdges(dagEdges);
      setIsDirty(false);
      return true;
    } catch (err) {
      console.error('[useDAGEditor] load error:', err);
      return false;
    }
  }, [setNodes, setEdges]);

  const listWorkflows = useCallback(async (): Promise<WorkflowSummary[]> => {
    try {
      const resp = await fetch(`${PIPELINE_API}/api/workflows`);
      const data = await resp.json();
      return data.workflows || [];
    } catch {
      return [];
    }
  }, []);

  const validate = useCallback(async () => {
    const payload = {
      name: workflowName,
      nodes: nodesRef.current.map(n => ({
        id: n.id,
        type: n.type,
        label: n.label,
        position: { x: 0, y: 0 },
        data: {},
      })),
      edges: edgesRef.current.map(e => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: e.type,
      })),
    };

    try {
      const resp = await fetch(`${PIPELINE_API}/api/workflows/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      return data.validation || { valid: false, errors: [], warnings: [] };
    } catch {
      return { valid: false, errors: [{ message: 'Validation request failed' }], warnings: [] };
    }
  }, [workflowName]);

  // --- Reset ---
  const newWorkflow = useCallback(() => {
    setWorkflowId(null);
    setWorkflowName('Untitled Workflow');
    setNodes([]);
    setEdges([]);
    historyRef.current = [];
    futureRef.current = [];
    setIsDirty(false);
  }, [setNodes, setEdges]);

  return {
    workflowId,
    workflowName,
    isDirty,
    canUndo,
    canRedo,
    addNode,
    removeNode,
    updateNodeData,
    addEdge,
    handleConnect,
    removeEdge,
    undo,
    redo,
    pushSnapshot,
    save,
    load,
    listWorkflows,
    validate,
    newWorkflow,
    setWorkflowName,
  };
}
