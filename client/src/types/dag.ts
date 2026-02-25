/**
 * MARKER_135.1A_TYPES: DAG data types for Mycelium Command Center.
 * Defines nodes, edges, and API response structures.
 *
 * @phase 135.1
 * @status active
 */

// Node types in the DAG
// MARKER_144.4: Extended with workflow editor node types
// MARKER_154.6A: Added 'roadmap_task' for Phase 154 Matryoshka roadmap level
export type DAGNodeType = 'task' | 'agent' | 'subtask' | 'proposal'
  | 'condition' | 'parallel' | 'loop' | 'transform' | 'group'
  | 'roadmap_task';

// Agent roles in the pipeline
export type AgentRole = 'scout' | 'architect' | 'researcher' | 'coder' | 'verifier';

// Node status
export type NodeStatus = 'pending' | 'running' | 'done' | 'failed';

// Edge types for different relationships
// MARKER_144.4: Extended with workflow editor edge types
// MARKER_154.6A: Added 'dependency' for roadmap-level inter-task relationships
export type EdgeType = 'structural' | 'dataflow' | 'temporal'
  | 'conditional' | 'parallel_fork' | 'parallel_join' | 'feedback'
  | 'dependency' | 'predicted';

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

  // MARKER_155.1A: Extra fields for RoadmapTaskNode at tasks level
  preset?: string;            // Team preset (dragon_bronze/silver/gold) for badge
  subtasksDone?: number;      // Completed subtasks for progress bar
  subtasksTotal?: number;     // Total subtasks for progress bar

  // MARKER_155A.P1.GRAPH_SCHEMA: Unified graph contract metadata (adapter-friendly)
  graphKind?: 'project_root' | 'project_dir' | 'project_file' | 'project_task'
    | 'workflow_agent' | 'workflow_artifact' | 'workflow_message';
  projectNodeId?: string;
  workflowId?: string;
  agentNodeId?: string;
  sourceMessageId?: string;
  primaryNodeId?: string;
  affectedNodes?: string[];
  integrationTaskOf?: string[];

  // MARKER_155.ARCH_LAYOUT.METADATA_BRIDGE.V1:
  // Keep backend layout metadata (parent/cluster/buckets) for architecture tree renderer.
  metadata?: {
    parent?: string;
    cluster_id?: number;
    rank_bucket?: number;
    bucket_count?: number;
    layer_index?: number;
    is_branch?: boolean;
    [key: string]: any;
  };
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

  // MARKER_155A.P1.GRAPH_SCHEMA: Unified edge relation metadata
  relationKind?: 'contains' | 'depends_on' | 'affects' | 'executes' | 'passes' | 'produces' | 'predicted';
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

// ============================================================
// MARKER_144.1: Workflow Template Types
// ============================================================

/**
 * A node in a workflow template (user-created).
 */
export interface WorkflowNode {
  id: string;
  type: DAGNodeType;
  label: string;
  position: { x: number; y: number };
  data: Record<string, any>;
}

/**
 * An edge in a workflow template.
 */
export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
  label?: string;
  data?: Record<string, any>;
}

/**
 * Complete workflow template.
 */
export interface Workflow {
  id: string;
  name: string;
  description?: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  metadata: {
    created_at: string;
    updated_at: string;
    author?: string;
    preset?: string;
    version: number;
  };
}

/**
 * Workflow summary (from list endpoint — no nodes/edges).
 */
export interface WorkflowSummary {
  id: string;
  name: string;
  description?: string;
  node_count: number;
  edge_count: number;
  metadata: Record<string, any>;
}
