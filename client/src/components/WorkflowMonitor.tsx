/**
 * Real-time workflow progress monitor
 * Phase 60.2: Visualizes LangGraph workflow execution
 *
 * @file WorkflowMonitor.tsx
 * @status ACTIVE
 * @phase Phase 60.2
 */

import React, { useEffect } from 'react';
import { useWorkflowSocket, WorkflowStatus } from '../hooks/useWorkflowSocket';

// Node names in order
const NODES = ['hostess', 'architect', 'pm', 'dev_qa_parallel', 'eval', 'learner', 'approval'];

// Node display configuration
const NODE_CONFIG: Record<string, { icon: string; label: string }> = {
  hostess: { icon: '🎀', label: 'Hostess' },
  architect: { icon: '🏗️', label: 'Architect' },
  pm: { icon: '📋', label: 'PM' },
  dev_qa_parallel: { icon: '👨‍💻', label: 'Dev+QA' },
  eval: { icon: '⭐', label: 'Eval' },
  learner: { icon: '🧠', label: 'Learner' },
  approval: { icon: '✅', label: 'Approval' },
};

interface WorkflowMonitorProps {
  workflowId?: string;
  compact?: boolean;
  className?: string;
}

export const WorkflowMonitor: React.FC<WorkflowMonitorProps> = ({
  workflowId,
  compact = false,
  className = '',
}) => {
  const { status, connected, subscribeToWorkflow, resetStatus } = useWorkflowSocket();

  useEffect(() => {
    if (workflowId) {
      resetStatus();
      subscribeToWorkflow(workflowId);
    }
  }, [workflowId, subscribeToWorkflow, resetStatus]);

  if (compact) {
    return <CompactMonitor status={status} connected={connected} className={className} />;
  }

  return (
    <div className={`workflow-monitor p-4 bg-gray-900 rounded-lg ${className}`}>
      {/* Connection Status */}
      <div className="flex items-center gap-2 mb-4">
        <div
          className={`w-2 h-2 rounded-full ${
            connected ? 'bg-green-500' : 'bg-red-500'
          }`}
        />
        <span className="text-sm text-gray-400">
          {connected ? 'Connected' : 'Disconnected'}
        </span>
        {status.workflow_id && (
          <span className="text-xs text-gray-500 ml-auto font-mono">
            ID: {status.workflow_id.slice(0, 8)}...
          </span>
        )}
      </div>

      {/* Node Progress */}
      <div className="space-y-2 mb-4">
        {NODES.map((node) => (
          <NodeProgressBar
            key={node}
            node={node}
            isCompleted={status.completed_nodes.includes(node)}
            isCurrent={status.current_node === node}
            isRetrying={node === 'dev_qa_parallel' && status.will_retry}
          />
        ))}
      </div>

      {/* Eval Score */}
      {status.eval_score !== null && (
        <div
          className={`p-3 rounded mb-4 ${
            status.eval_passed ? 'bg-green-900/30 border border-green-800' : 'bg-red-900/30 border border-red-800'
          }`}
        >
          <div className="flex justify-between items-center">
            <span className="font-medium text-white">
              Score: {(status.eval_score * 100).toFixed(0)}%
            </span>
            <span className={status.eval_passed ? 'text-green-400' : 'text-red-400'}>
              {status.eval_passed ? '✅ PASSED' : '❌ RETRY'}
            </span>
          </div>
          {status.eval_feedback && (
            <p className="text-sm text-gray-400 mt-2 line-clamp-2">{status.eval_feedback}</p>
          )}
        </div>
      )}

      {/* Retry Info */}
      {status.retry_count > 0 && (
        <div className="p-3 bg-yellow-900/30 border border-yellow-800 rounded mb-4">
          <span className="text-yellow-400">
            🔄 Retry {status.retry_count}/3
          </span>
          {status.learner_suggestion && (
            <p className="text-sm text-gray-400 mt-2 line-clamp-2">
              💡 {status.learner_suggestion}
            </p>
          )}
        </div>
      )}

      {/* Error */}
      {status.error_message && (
        <div className="p-3 bg-red-900/30 border border-red-800 rounded mb-4">
          <span className="text-red-400">❌ Error: {status.error_message}</span>
        </div>
      )}

      {/* Duration & Status */}
      <div className="flex justify-between items-center text-sm text-gray-500">
        <span className="capitalize">
          Status: {status.status}
        </span>
        {status.duration_ms > 0 && (
          <span>
            Duration: {(status.duration_ms / 1000).toFixed(1)}s
          </span>
        )}
      </div>
    </div>
  );
};

// Helper component for node progress
const NodeProgressBar: React.FC<{
  node: string;
  isCompleted: boolean;
  isCurrent: boolean;
  isRetrying: boolean;
}> = ({ node, isCompleted, isCurrent, isRetrying }) => {
  const config = NODE_CONFIG[node] || { icon: '📦', label: node };

  const getBackgroundClass = () => {
    if (isCompleted) return 'bg-green-900/20 border-green-800';
    if (isCurrent) return 'bg-blue-900/30 border-blue-700 animate-pulse';
    if (isRetrying) return 'bg-yellow-900/20 border-yellow-800';
    return 'bg-gray-800/50 border-gray-700';
  };

  return (
    <div
      className={`flex items-center gap-3 p-2 rounded border ${getBackgroundClass()}`}
    >
      <span className="text-lg">{config.icon}</span>
      <span className="text-gray-300 flex-1">{config.label}</span>
      {isCompleted && <span className="text-green-400">✓</span>}
      {isCurrent && !isCompleted && (
        <span className="text-blue-400 animate-bounce">...</span>
      )}
      {isRetrying && <span className="text-yellow-400">↻</span>}
    </div>
  );
};

// Compact version for sidebar
const CompactMonitor: React.FC<{
  status: WorkflowStatus;
  connected: boolean;
  className?: string;
}> = ({ status, connected, className = '' }) => {
  const progress = (status.completed_nodes.length / NODES.length) * 100;
  const config = NODE_CONFIG[status.current_node] || { icon: '⏸️', label: 'idle' };

  return (
    <div className={`compact-monitor p-2 bg-gray-800 rounded ${className}`}>
      <div className="flex items-center gap-2">
        {/* Connection indicator */}
        <div
          className={`w-2 h-2 rounded-full flex-shrink-0 ${
            connected ? 'bg-green-500' : 'bg-red-500'
          }`}
        />

        {/* Progress bar */}
        <div className="flex-1 h-2 bg-gray-700 rounded overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${
              status.status === 'error' ? 'bg-red-500' :
              status.status === 'completed' ? 'bg-green-500' : 'bg-blue-500'
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Current node */}
        <span className="text-xs text-gray-400 flex-shrink-0">
          {status.status === 'idle' ? '⏸️' : config.icon}
        </span>
      </div>

      {/* Score badge (if available) */}
      {status.eval_score !== null && (
        <div className="mt-1 flex justify-end">
          <span
            className={`text-xs px-1 rounded ${
              status.eval_passed ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
            }`}
          >
            {(status.eval_score * 100).toFixed(0)}%
          </span>
        </div>
      )}
    </div>
  );
};

export default WorkflowMonitor;
