/**
 * MARKER_153.6C: useToast — lightweight toast notification system.
 *
 * Toast types: info (blue), warning (amber), error (red), success (green).
 * Auto-dismiss: 5s for info/success, sticky for errors.
 * Uses CustomEvents for cross-component communication.
 *
 * Listens to pipeline events and shows toasts for:
 * - LLM failures
 * - Pipeline errors
 * - Task board updates
 * - Sandbox errors
 *
 * @phase 153
 * @wave 6
 * @status active
 */

import { useState, useCallback, useEffect, useRef } from 'react';

export type ToastType = 'info' | 'warning' | 'error' | 'success';

export interface Toast {
  id: string;
  type: ToastType;
  message: string;
  timestamp: number;
  sticky?: boolean;      // errors are sticky by default
  dismissed?: boolean;
}

// Auto-dismiss timeouts per type (ms)
const AUTO_DISMISS: Record<ToastType, number> = {
  info: 5000,
  success: 5000,
  warning: 8000,
  error: 0,  // 0 = sticky (no auto-dismiss)
};

const MAX_TOASTS = 5;

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const addToast = useCallback((type: ToastType, message: string, sticky?: boolean) => {
    const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
    const toast: Toast = {
      id,
      type,
      message,
      timestamp: Date.now(),
      sticky: sticky ?? type === 'error',
    };

    setToasts(prev => [toast, ...prev].slice(0, MAX_TOASTS));

    // Set auto-dismiss timer
    const timeout = AUTO_DISMISS[type];
    if (timeout > 0 && !toast.sticky) {
      const timer = setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id));
        timersRef.current.delete(id);
      }, timeout);
      timersRef.current.set(id, timer);
    }

    return id;
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  const dismissAll = useCallback(() => {
    setToasts([]);
    timersRef.current.forEach(timer => clearTimeout(timer));
    timersRef.current.clear();
  }, []);

  // MARKER_153.6C: Listen for pipeline and system events → auto-toast
  useEffect(() => {
    const handlePipelineActivity = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      const status = detail.status || detail.event || '';
      const message = detail.message || '';

      // Detect errors
      if (status === 'error' || status === 'failed' || message.includes('error') || message.includes('failed')) {
        addToast('error', `Pipeline: ${message || status}`);
      }
    };

    const handleTaskBoardUpdate = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      const status = detail.status || '';
      const taskId = detail.task_id || detail.taskId || '';

      if (status === 'failed') {
        addToast('error', `Task ${taskId.slice(0, 12)} failed`);
      } else if (status === 'done' || status === 'completed') {
        addToast('success', `Task ${taskId.slice(0, 12)} completed`);
      }
    };

    window.addEventListener('pipeline-activity', handlePipelineActivity as EventListener);
    window.addEventListener('task-board-updated', handleTaskBoardUpdate as EventListener);

    return () => {
      window.removeEventListener('pipeline-activity', handlePipelineActivity as EventListener);
      window.removeEventListener('task-board-updated', handleTaskBoardUpdate as EventListener);
    };
  }, [addToast]);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      timersRef.current.forEach(timer => clearTimeout(timer));
    };
  }, []);

  return { toasts, addToast, dismissToast, dismissAll };
}

/**
 * Toast color palette (Nolan dark style).
 */
export const TOAST_COLORS: Record<ToastType, { bg: string; border: string; text: string }> = {
  info: { bg: 'rgba(59,130,246,0.12)', border: 'rgba(59,130,246,0.3)', text: '#93c5fd' },
  success: { bg: 'rgba(34,197,94,0.12)', border: 'rgba(34,197,94,0.3)', text: '#86efac' },
  warning: { bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.3)', text: '#fcd34d' },
  error: { bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.3)', text: '#fca5a5' },
};
