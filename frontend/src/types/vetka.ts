/**
 * VETKA-JSON v1.3 TypeScript Types
 * =================================
 *
 * TypeScript type definitions for VETKA Phase 10 3D visualization.
 * These types match the Python output from Phase10Transformer.
 *
 * Principle: "ПРИРАСТАЕТ, НЕ ЛОМАЕТСЯ"
 *
 * Author: AI Council + Opus 4.5
 * Date: December 13, 2025
 */

// ═══════════════════════════════════════════════════════════════════════════════
// ENUMS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Agent types for VETKA nodes.
 * IMPORTANT: Elisya is middleware, NOT an agent!
 */
export type AgentType = 'PM' | 'Dev' | 'QA' | 'ARC' | 'Human' | 'System';

/** Branch types for tree structure */
export type BranchType = 'memory' | 'task' | 'data' | 'control';

/** Node types in the tree */
export type NodeType = 'root' | 'branch' | 'leaf';

/** Edge semantic types (6 types) */
export type EdgeSemantics = 'informs' | 'influences' | 'creates' | 'depends' | 'supersedes' | 'references';

/** Physical edge types */
export type EdgeType = 'liana' | 'root' | 'control';

/** Animation types for Three.js */
export type AnimationType = 'static' | 'pulse' | 'glow' | 'flicker';

/** Content types for node data */
export type ContentType = 'text' | 'code' | 'image' | 'diagram' | 'metrics';

/** Edge line styles */
export type EdgeStyle = 'solid' | 'dashed' | 'dotted';

/** Arrow types for edges */
export type ArrowType = 'triangle' | 'diamond' | null;

/** Edge direction */
export type EdgeDirection = 'forward' | 'backward' | 'bidirectional';

/** Origin source types */
export type OriginSource = 'phase9' | 'import' | 'human';

/** Context source types */
export type ContextSourceType = 'elisya' | 'direct' | 'manual';

/** Position calculation method */
export type PositionCalculation = 'phylotaxis' | 'manual' | 'auto';

/** Promote event types */
export type PromoteEventType = 'seed_detached' | 'roots_spread' | 'tree_grows';

// ═══════════════════════════════════════════════════════════════════════════════
// TOP-LEVEL STRUCTURE
// ═══════════════════════════════════════════════════════════════════════════════

/** Main VETKA-JSON v1.3 structure */
export interface VetkaJSON {
  $schema: string;
  format: 'vetka-v1.3';
  version: '1.3';
  compatibility: Compatibility;
  origin: Origin;
  created_at: string;
  tree: VetkaTree;
}

export interface Compatibility {
  reads: string[];
  writes: string[];
}

export interface Origin {
  source: OriginSource;
  workflow_id: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// TREE STRUCTURE
// ═══════════════════════════════════════════════════════════════════════════════

export interface VetkaTree {
  id: string;
  name: string;
  root_node_id: string;
  nodes: VetkaNode[];
  edges: VetkaEdge[];
  promote_history: PromoteEvent[];
  metadata: TreeMetadata;
}

export interface TreeMetadata {
  phase: string;
  total_nodes: number;
  total_edges: number;
  max_depth: number;
  completion_rate: number;
  cost_optimization?: CostOptimization;
}

export interface CostOptimization {
  total_tokens_used: number;
  total_cost_usd: number;
  baseline_cost_if_gpt4: number;
  savings_usd: number;
  savings_percent: number;
  cost_by_agent: Record<string, AgentCost>;
  routing_summary: RoutingSummary;
}

export interface AgentCost {
  tokens: number;
  cost: number;
  model: string;
}

export interface RoutingSummary {
  local_model_used: number;
  api_model_used: number;
  fallback_triggered: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// NODE STRUCTURE
// ═══════════════════════════════════════════════════════════════════════════════

export interface VetkaNode {
  // Identification
  id: string;
  parent_id: string | null;

  // Type
  type: NodeType;
  branch_type: BranchType;

  // Content
  name: string;
  content: NodeContent;

  // Metadata
  metadata: NodeMetadata;

  // Visual
  visual_hints: NodeVisualHints;
  lod_hints: LODHints;

  // History
  version_history: string[];

  // Children
  children_ids: string[];

  // Promote
  promote_triggers: PromoteTriggers | null;
  promoted_to: PromotedTo | null;
}

export interface NodeContent {
  type: ContentType;
  data: Record<string, unknown>;
  preview?: string;
  download_url?: string | null;
}

export interface NodeMetadata {
  // Core (always required)
  agent: AgentType;
  eval_score: number;
  entropy: number;
  completion_rate: number;
  timestamp: string;
  student_level?: number;
  version?: string;
  tags?: string[];

  // Source tracking
  phase9_source?: Phase9Source;
  context_source?: ContextSource;

  // Optional: Infrastructure tracking
  learning_context?: LearningContext;
  model_provenance?: ModelProvenance;
  learning_feedback?: LearningFeedback;
  storage_status?: StorageStatus;
  arc_execution?: ARCExecution;
}

export interface Phase9Source {
  field: string;
  index: number | null;
  confidence: number;
}

export interface ContextSource {
  type: ContextSourceType;
  reframe_applied: boolean;
  query_sources: string[];
  elisya_details?: ElisyaDetails;
}

export interface ElisyaDetails {
  elisya_version: string;
  lod_level_requested: string;
  lod_level_applied: string;
  weaviate_queries: Record<string, unknown>;
  qdrant_queries: Record<string, unknown>;
  total_assembly_time_ms: number;
  reframe_operations: string[];
  degradation_occurred: boolean;
}

export interface LearningContext {
  created_by_learner?: string;
  learner_model_version?: string;
  is_training_exemplar?: boolean;
  learner_confidence?: number;
  exemplar_portfolio_id?: string;
  models_improved_by_this?: ModelImprovement[];
}

export interface ModelImprovement {
  learner: string;
  lesson_id: string;
  confidence_before: number;
  confidence_after: number;
  improvement_delta: number;
  learned_at: string;
}

export interface ModelProvenance {
  primary_model: string;
  model_version?: string;
  api_provider?: string;
  api_key_index?: number;
  fallback_used?: boolean;
  local_model_fallback?: string | null;
  tokens_input?: number;
  tokens_output?: number;
  tokens_total?: number;
  estimated_cost_usd?: number;
  execution_time_ms?: number;
  routing_decision?: RoutingDecision;
}

export interface RoutingDecision {
  task_complexity?: string;
  routing_reason?: string;
  alternative_considered?: string;
  cost_savings_vs_alternative?: number;
}

export interface LearningFeedback {
  eval_score?: number;
  eval_agent_model?: string;
  eval_timestamp?: string;
  qualifies_for_training?: boolean;
  training_decision?: string;
  retry_info?: RetryInfo;
  saved_examples?: SavedExample[];
  feedback_source?: string;
}

export interface RetryInfo {
  retry_occurred: boolean;
  retry_count: number;
  original_score?: number | null;
  improvement_delta?: number | null;
  prompt_adjustments: string[];
}

export interface SavedExample {
  example_id: string;
  example_type: string;
  saved_at: string;
  target_learner: string;
  quality_score: number;
}

export interface StorageStatus {
  changelog: StorageResult;
  weaviate: StorageResult;
  qdrant: StorageResult;
  overall_status: string;
  degradation_mode: boolean;
}

export interface StorageResult {
  status: string;
  entry_id?: string;
  node_uuid?: string;
  point_id?: number;
  collection?: string;
  file_path?: string;
  timestamp?: string;
  retries?: number;
  error_message?: string | null;
}

export interface ARCExecution {
  solver_model?: string;
  solver_model_version?: string;
  prompt_template_version?: string;
  candidates?: ARCCandidates;
  best_candidate?: BestCandidate;
  code_fixes_applied?: CodeFix[];
  training_examples_saved?: TrainingExamples;
  timing?: ARCTiming;
}

export interface ARCCandidates {
  requested: number;
  generated: number;
  passed_syntax_check: number;
  passed_validation: number;
  passed_testing: number;
  final_candidates: number;
}

export interface BestCandidate {
  index: number;
  score: number;
  transformation_type: string;
  description: string;
}

export interface CodeFix {
  fix_type: string;
  original_error: string;
  lines_affected: number[];
  fixed: boolean;
}

export interface TrainingExamples {
  count: number;
  example_ids: string[];
  target_learner: string;
  saved_at: string;
}

export interface ARCTiming {
  generation_time_ms: number;
  parsing_time_ms: number;
  validation_time_ms: number;
  fixing_time_ms: number;
  total_time_ms: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// VISUAL HINTS
// ═══════════════════════════════════════════════════════════════════════════════

export interface NodeVisualHints {
  size_multiplier: number;
  color: string;
  opacity: number;
  animation: AnimationType;
  animation_params?: AnimationParams;
  icon: string;
  position_hint?: PositionHint;
}

export interface AnimationParams {
  scale: [number, number];
  opacity: [number, number];
  period_ms: number;
}

export interface PositionHint {
  x: number;
  y: number;
  z: number;
  calculation: PositionCalculation;
}

export interface LODHints {
  forest: { visible: boolean };
  tree: { show_label: boolean };
  branch: { show_content: boolean };
}

// ═══════════════════════════════════════════════════════════════════════════════
// PROMOTE STRUCTURE
// ═══════════════════════════════════════════════════════════════════════════════

export interface PromoteTriggers {
  node_count?: number;
  entropy?: number;
  user_action?: string | null;
  threshold_reached: boolean;
}

export interface PromotedTo {
  event: PromoteEventType;
  new_tree_id: string;
  root_edge_id: string;
  timestamp: string;
  animation_duration_ms: number;
  animation_type: PromoteEventType;
}

export interface PromoteEvent {
  id: string;
  source_node_id: string;
  event: PromoteEventType;
  timestamp: string;
  new_tree_id: string;
  root_edge_id: string;
  triggers: PromoteTriggers;
  animation_duration_ms: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// EDGE STRUCTURE
// ═══════════════════════════════════════════════════════════════════════════════

export interface VetkaEdge {
  // Identification
  id: string;
  from: string;
  to: string;

  // Type
  type: EdgeType;
  semantics: EdgeSemantics;

  // Weight & Metadata
  flow_weight: number;
  age?: string;
  direction?: EdgeDirection;

  // Visual hints
  visual_hints: EdgeVisualHints;

  // Metadata
  metadata?: EdgeMetadata;

  // Optional: Parallel execution
  parallel_execution?: ParallelExecution;
}

export interface EdgeVisualHints {
  thickness: number;
  color: string;
  style: EdgeStyle;
  curvature?: number;
  arrow_type?: ArrowType;
}

export interface EdgeMetadata {
  created_at: string;
  description?: string;
}

export interface ParallelExecution {
  executed_concurrently: boolean;
  dev_start_time?: string;
  dev_end_time?: string;
  qa_start_time?: string;
  qa_end_time?: string;
  overlap_ms?: number;
  elisya_reframe_occurred?: boolean;
  reframe_timestamp?: string;
  reframe_trigger?: string;
  reframe_impact?: string;
  shared_context_tokens?: number;
  context_updates_during_execution?: number;
  elisya_recommendations?: string[];
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS (Re-exported for consistency)
// ═══════════════════════════════════════════════════════════════════════════════

export const AGENT_COLORS: Record<AgentType, string> = {
  PM: '#FFB347',       // warm orange
  Dev: '#6495ED',      // cold blue
  QA: '#9370DB',       // purple
  ARC: '#32CD32',      // green
  Human: '#FFD700',    // gold
  System: '#A9A9A9',   // gray
};

export const EDGE_STYLES: Record<EdgeSemantics, {
  color: string;
  thickness: number;
  style: EdgeStyle;
  arrow_type: ArrowType;
}> = {
  informs: {
    color: '#FFB347',
    thickness: 1.0,
    style: 'dashed',
    arrow_type: null,
  },
  influences: {
    color: '#DC143C',
    thickness: 2.0,
    style: 'solid',
    arrow_type: null,
  },
  creates: {
    color: '#8B4513',
    thickness: 3.0,
    style: 'solid',
    arrow_type: null,
  },
  depends: {
    color: '#4169E1',
    thickness: 1.5,
    style: 'solid',
    arrow_type: 'triangle',
  },
  supersedes: {
    color: '#808080',
    thickness: 1.0,
    style: 'dotted',
    arrow_type: null,
  },
  references: {
    color: '#9370DB',
    thickness: 0.5,
    style: 'dashed',
    arrow_type: null,
  },
};

export const ANIMATION_PARAMS: Record<AnimationType, AnimationParams> = {
  static: { scale: [1.0, 1.0], opacity: [1.0, 1.0], period_ms: 0 },
  pulse: { scale: [1.0, 1.1], opacity: [1.0, 1.0], period_ms: 2000 },
  glow: { scale: [1.0, 1.0], opacity: [0.7, 1.0], period_ms: 1500 },
  flicker: { scale: [1.0, 1.0], opacity: [0.3, 1.0], period_ms: 500 },
};

// ═══════════════════════════════════════════════════════════════════════════════
// UTILITY TYPES
// ═══════════════════════════════════════════════════════════════════════════════

/** Type guard for VetkaNode */
export function isVetkaNode(obj: unknown): obj is VetkaNode {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'id' in obj &&
    'type' in obj &&
    'branch_type' in obj &&
    'metadata' in obj
  );
}

/** Type guard for VetkaEdge */
export function isVetkaEdge(obj: unknown): obj is VetkaEdge {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'id' in obj &&
    'from' in obj &&
    'to' in obj &&
    'semantics' in obj
  );
}

/** Type guard for VetkaJSON */
export function isVetkaJSON(obj: unknown): obj is VetkaJSON {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'format' in obj &&
    (obj as VetkaJSON).format === 'vetka-v1.3' &&
    'tree' in obj
  );
}
