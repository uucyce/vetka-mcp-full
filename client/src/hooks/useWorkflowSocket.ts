/**
 * Hook for subscribing to workflow events via Socket.IO.
 * Provides real-time workflow status, node progress, and evaluation scores.
 *
 * @status active
 * @phase 96
 * @depends socket.io-client, react
 * @used_by WorkflowPanel, ChatPanel
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';

// Event types matching backend event_types.py
export interface WorkflowEvent {
  workflow_id: string;
  timestamp: string;
}

export interface NodeStartedEvent extends WorkflowEvent {
  node: string;
  input_preview?: string;
  retry_attempt?: number;
}

export interface NodeCompletedEvent extends WorkflowEvent {
  node: string;
  duration_ms: number;
  output_preview?: string;
  next_node?: string;
  artifacts_created?: number;
}

export interface NodeErrorEvent extends WorkflowEvent {
  node: string;
  error_message: string;
  error_type?: string;
  recoverable?: boolean;
}

export interface ScoreComputedEvent extends WorkflowEvent {
  score: number;
  threshold: number;
  passed: boolean;
  feedback_preview?: string;
}

export interface RetryDecisionEvent extends WorkflowEvent {
  will_retry: boolean;
  retry_count: number;
  max_retries: number;
  reason?: string;
}

export interface LearnerSuggestionEvent extends WorkflowEvent {
  failure_category: string;
  suggestion_preview: string;
  confidence: number;
  similar_failures_found?: number;
}

export interface WorkflowCompletedEvent extends WorkflowEvent {
  final_score: number;
  total_retries: number;
  duration_ms: number;
  artifacts_count: number;
  status: 'success' | 'failed' | 'max_retries';
}

// Workflow status state
export interface WorkflowStatus {
  workflow_id: string;
  status: 'idle' | 'running' | 'completed' | 'error';
  current_node: string;
  completed_nodes: string[];
  eval_score: number | null;
  eval_passed: boolean | null;
  eval_feedback: string;
  retry_count: number;
  will_retry: boolean;
  learner_suggestion: string;
  duration_ms: number;
  error_message: string | null;
}

const initialStatus: WorkflowStatus = {
  workflow_id: '',
  status: 'idle',
  current_node: '',
  completed_nodes: [],
  eval_score: null,
  eval_passed: null,
  eval_feedback: '',
  retry_count: 0,
  will_retry: false,
  learner_suggestion: '',
  duration_ms: 0,
  error_message: null,
};

export interface UseWorkflowSocketOptions {
  serverUrl?: string;
  autoConnect?: boolean;
}

export const useWorkflowSocket = (options: UseWorkflowSocketOptions = {}) => {
  const { serverUrl = '', autoConnect = true } = options;

  const [socket, setSocket] = useState<Socket | null>(null);
  const [status, setStatus] = useState<WorkflowStatus>(initialStatus);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<Socket | null>(null);

  // Connect to workflow namespace
  useEffect(() => {
    if (!autoConnect) return;

    const url = serverUrl || window.location.origin;
    const newSocket = io(`${url}/workflow`, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    newSocket.on('connect', () => {
      // console.log('[WorkflowSocket] Connected');
      setConnected(true);
    });

    newSocket.on('disconnect', () => {
      // console.log('[WorkflowSocket] Disconnected');
      setConnected(false);
    });

    newSocket.on('connect_error', (error) => {
      console.error('[WorkflowSocket] Connection error:', error);
    });

    // Connection status acknowledgment
    newSocket.on('connection_status', (data: { status: string }) => {
      // console.log('[WorkflowSocket] Status:', data.status);
    });

    // Node events
    newSocket.on('node_started', (data: NodeStartedEvent) => {
      // console.log(`[Workflow] 📍 Node started: ${data.node}`);
      setStatus(prev => ({
        ...prev,
        current_node: data.node,
        status: 'running',
      }));
    });

    newSocket.on('node_completed', (data: NodeCompletedEvent) => {
      // console.log(`[Workflow] ✅ Node completed: ${data.node} (${data.duration_ms}ms)`);
      setStatus(prev => ({
        ...prev,
        completed_nodes: [...prev.completed_nodes, data.node],
        duration_ms: prev.duration_ms + data.duration_ms,
      }));
    });

    newSocket.on('node_error', (data: NodeErrorEvent) => {
      console.error(`[Workflow] ❌ Node error: ${data.node}`, data.error_message);
      setStatus(prev => ({
        ...prev,
        status: 'error',
        error_message: data.error_message,
      }));
    });

    // Evaluation events (Phase 29)
    newSocket.on('score_computed', (data: ScoreComputedEvent) => {
      // console.log(`[Workflow] 📊 Score: ${data.score.toFixed(2)} (${data.passed ? 'PASS' : 'FAIL'})`);
      setStatus(prev => ({
        ...prev,
        eval_score: data.score,
        eval_passed: data.passed,
        eval_feedback: data.feedback_preview || '',
      }));
    });

    newSocket.on('retry_decision', (data: RetryDecisionEvent) => {
      // console.log(`[Workflow] 🔄 Retry: ${data.will_retry} (${data.retry_count}/${data.max_retries})`);
      setStatus(prev => ({
        ...prev,
        retry_count: data.retry_count,
        will_retry: data.will_retry,
      }));
    });

    // Learner events (Phase 29)
    newSocket.on('learner_suggestion', (data: LearnerSuggestionEvent) => {
      // console.log(`[Workflow] 🧠 Learner: ${data.failure_category}`);
      setStatus(prev => ({
        ...prev,
        learner_suggestion: data.suggestion_preview,
      }));
    });

    // Workflow lifecycle
    newSocket.on('workflow_started', (data: WorkflowEvent) => {
      // console.log(`[Workflow] 🚀 Started: ${data.workflow_id}`);
      setStatus({
        ...initialStatus,
        workflow_id: data.workflow_id,
        status: 'running',
      });
    });

    newSocket.on('workflow_completed', (data: WorkflowCompletedEvent) => {
      // console.log(`[Workflow] 🎉 Completed: ${data.workflow_id}`);
      setStatus(prev => ({
        ...prev,
        status: 'completed',
        eval_score: data.final_score,
        retry_count: data.total_retries,
        duration_ms: data.duration_ms,
      }));
    });

    // Room events
    newSocket.on('joined_workflow', (data: { workflow_id: string; status: string }) => {
      // console.log(`[WorkflowSocket] Joined workflow: ${data.workflow_id}`);
    });

    newSocket.on('left_workflow', (data: { workflow_id: string; status: string }) => {
      // console.log(`[WorkflowSocket] Left workflow: ${data.workflow_id}`);
    });

    socketRef.current = newSocket;
    setSocket(newSocket);

    return () => {
      newSocket.close();
      socketRef.current = null;
    };
  }, [serverUrl, autoConnect]);

  // Subscribe to specific workflow
  const subscribeToWorkflow = useCallback((workflowId: string) => {
    if (socketRef.current) {
      socketRef.current.emit('join_workflow', { workflow_id: workflowId });
      setStatus(prev => ({ ...prev, workflow_id: workflowId }));
    }
  }, []);

  // Unsubscribe from workflow
  const unsubscribeFromWorkflow = useCallback((workflowId: string) => {
    if (socketRef.current) {
      socketRef.current.emit('leave_workflow', { workflow_id: workflowId });
    }
  }, []);

  // Reset status
  const resetStatus = useCallback(() => {
    setStatus(initialStatus);
  }, []);

  // Ping test
  const ping = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.emit('ping_workflow', { timestamp: Date.now() });
    }
  }, []);

  return {
    socket,
    connected,
    status,
    subscribeToWorkflow,
    unsubscribeFromWorkflow,
    resetStatus,
    ping,
  };
};

export default useWorkflowSocket;
