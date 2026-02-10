/**
 * MARKER_135.1A_TYPES: DAG data types for Mycelium Command Center.
 * Defines nodes, edges, and API response structures.
 *
 * @phase 135.1
 * @status active
 */

// Node types in the DAG
export type DAGNodeType = 'task' | 'agent' | 'subtask' | 'proposal';

// Agent roles in the pipeline
export type AgentRole = 'scout' | 'architect' | 'researcher' | 'coder' | 'verifier';

// Node status
export type NodeStatus = 'pending' | 'running' | 'done' | 'failed';

// Edge types for different relationships
export type EdgeType = 'structural' | 'dataflow' | 'temporal';

/**
 * DAG Node — represents any entity in the graph.
 * ID format:
 *   task: "task_{uuid}"
 *   agent: "agent_{task_id}_{role}"
 *   subtask: "sub_{task_id}_{idx}"
 *   proposal: "prop_{task_id}"
 */
export interface DAGNode {
  id: string;
  type: DAGNodeType;
  label: string;
  status: NodeStatus;
  layer: number;              // 0=task, 1=agents, 2-3=subtasks, 4=proposals

  // Tree structure
  parentId?: string;
  taskId: string;             // Root task reference

  // Metadata (optional, for Detail Panel)
  startedAt?: string;
  completedAt?: string;
  durationS?: number;
  tokens?: number;
  model?: string;             // "kimi-k2.5", "qwen3-coder", etc.
  confidence?: number;        // For proposals only (0-1)
  role?: AgentRole;           // For agent nodes
  description?: string;       // Full description for detail view
  code?: string;              // Code preview for subtasks
}

/**
 * DAG Edge — represents relationship between nodes.
 */
export interface DAGEdge {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
  strength: number;           // 0.0-1.0
  animated?: boolean;
}

/**
 * DAG Response from API.
 */
export interface DAGResponse {
  nodes: DAGNode[];
  edges: DAGEdge[];
  rootIds: string[];          // Task node IDs at layer 0
  stats: DAGStats;
}

/**
 * Aggregate statistics for the DAG.
 */
export interface DAGStats {
  totalTasks: number;
  runningTasks: number;
  completedTasks: number;
  failedTasks: number;
  successRate: number;        // 0-100
  totalAgents: number;
  totalSubtasks: number;
}

/**
 * Filters for DAG API request.
 */
export interface DAGFilters {
  status?: NodeStatus | 'all';
  timeRange?: '1h' | '6h' | '24h' | 'all';
  taskId?: string;
  type?: DAGNodeType | 'all';
}

/**
 * Real-time DAG update event.
 */
export interface DAGUpdateEvent {
  updateType: 'node_added' | 'node_status' | 'node_removed' | 'edge_added';
  node?: DAGNode;
  edge?: DAGEdge;
}

/**
 * Node detail response (expanded metadata).
 */
export interface DAGNodeDetail extends DAGNode {
  // Extended fields for detail panel
  preset?: string;
  llmCalls?: number;
  tokensIn?: number;
  tokensOut?: number;
  error?: string;
  result?: unknown;
}
