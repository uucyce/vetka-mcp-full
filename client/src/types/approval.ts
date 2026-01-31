/**
 * VETKA Phase 104.4 - Approval Event Types
 *
 * TypeScript types for Socket.IO approval events.
 * Used by chat UI for real-time artifact approval workflow.
 *
 * @status active
 * @phase 104.4
 * @depends none
 * @used_by ./hooks/useSocket, ./components/ApprovalModal
 */

// === Server -> Client Events ===

/**
 * Approval request sent from server when artifacts need user review.
 * Emitted after EvalAgent scores the artifacts.
 */
export interface ApprovalRequest {
  type: 'approval_request';
  request_id: string;
  workflow_id: string;
  group_id: string;
  artifacts: ArtifactPreview[];
  eval_score: number;
  eval_feedback: string;
  score_level: 'high' | 'medium' | 'low';
  actions: ApprovalAction[];
  timeout_seconds: number;
}

/**
 * Single artifact preview in approval request.
 * Contains truncated content for quick preview.
 */
export interface ArtifactPreview {
  id: string;
  filename: string;
  language: string;
  content_preview: string;
  full_content?: string;
  lines: number;
  agent: 'PM' | 'Dev' | 'QA' | 'Architect' | 'Hostess' | string;
  artifact_type: 'code' | 'config' | 'doc' | 'test';
}

/**
 * Result of approval/rejection action.
 * Sent back to UI after processing user decision.
 */
export interface ApprovalResult {
  request_id: string;
  status: 'approved' | 'rejected' | 'editing' | 'error' | 'timeout';
  message: string;
  edited_artifacts?: string[];
}

/**
 * Error during approval processing.
 */
export interface ApprovalError {
  request_id: string;
  error: string;
}

/**
 * Full approval details (response to get_approval_details).
 */
export interface ApprovalDetails {
  id: string;
  workflow_id: string;
  artifacts: ArtifactPreview[];
  eval_score: number;
  eval_feedback: string;
  status: 'pending' | 'approved' | 'rejected' | 'timeout';
  created_at: string;
  decided_at: string | null;
  decision_reason: string | null;
}

// === Client -> Server Events ===

/**
 * User action on approval request.
 * Sent when user clicks Approve/Reject/Edit buttons.
 */
export type ApprovalAction = 'approve' | 'reject' | 'edit';

export interface ApprovalResponse {
  request_id: string;
  action: ApprovalAction;
  reason?: string;
  group_id?: string;
  edited_content?: Record<string, string>;
}

/**
 * Request to get full approval details.
 */
export interface GetApprovalDetails {
  request_id: string;
}

// === UI Helper Types ===

/**
 * Score badge configuration for UI display.
 */
export interface ScoreBadgeConfig {
  level: 'high' | 'medium' | 'low';
  color: string;
  bgColor: string;
  label: string;
}

export const SCORE_BADGE_CONFIGS: Record<string, ScoreBadgeConfig> = {
  high: {
    level: 'high',
    color: '#10B981',
    bgColor: '#D1FAE5',
    label: 'High Quality',
  },
  medium: {
    level: 'medium',
    color: '#F59E0B',
    bgColor: '#FEF3C7',
    label: 'Needs Review',
  },
  low: {
    level: 'low',
    color: '#EF4444',
    bgColor: '#FEE2E2',
    label: 'Low Quality',
  },
};

/**
 * Get score badge config from eval_score.
 */
export function getScoreBadge(score: number): ScoreBadgeConfig {
  if (score >= 0.8) return SCORE_BADGE_CONFIGS.high;
  if (score >= 0.6) return SCORE_BADGE_CONFIGS.medium;
  return SCORE_BADGE_CONFIGS.low;
}

// === Socket Event Names (for type-safe event handling) ===

export const APPROVAL_EVENTS = {
  // Server -> Client
  APPROVAL_REQUEST: 'approval_request',
  APPROVAL_RESULT: 'approval_result',
  APPROVAL_ERROR: 'approval_error',
  APPROVAL_DETAILS: 'approval_details',
  // Client -> Server
  APPROVAL_RESPONSE: 'approval_response',
  GET_APPROVAL_DETAILS: 'get_approval_details',
} as const;
