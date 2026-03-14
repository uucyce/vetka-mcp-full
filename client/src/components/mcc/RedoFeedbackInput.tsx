/**
 * MARKER_154.10A: RedoFeedbackInput — inline feedback form for redo action.
 *
 * Shows at result level when user clicks "Redo".
 * User types what's wrong → submit → PATCH task to pending + re-dispatch with feedback.
 *
 * @phase 154
 * @wave 3
 * @status active
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

interface RedoFeedbackInputProps {
  taskId: string;
  taskTitle: string;
  onSubmit: (feedback: string) => void;
  onCancel: () => void;
}

export function RedoFeedbackInput({ taskId, taskTitle, onSubmit, onCancel }: RedoFeedbackInputProps) {
  const [feedback, setFeedback] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-focus
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Escape to cancel
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onCancel]);

  const handleSubmit = useCallback(() => {
    if (!feedback.trim()) return;
    onSubmit(feedback.trim());
  }, [feedback, onSubmit]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 56,
        left: '50%',
        transform: 'translateX(-50%)',
        width: 340,
        background: NOLAN_PALETTE.bgDim,
        border: `1px solid ${NOLAN_PALETTE.border}`,
        borderRadius: 8,
        padding: '12px 14px',
        fontFamily: 'monospace',
        zIndex: 90,
        boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <div style={{ color: NOLAN_PALETTE.textAccent, fontSize: 11, fontWeight: 600 }}>
          ↻ Redo: {taskTitle}
        </div>
        <button
          onClick={onCancel}
          style={{
            background: 'none',
            border: 'none',
            color: NOLAN_PALETTE.textMuted,
            cursor: 'pointer',
            fontSize: 12,
            padding: 0,
          }}
        >
          ✕
        </button>
      </div>

      {/* Feedback input */}
      <textarea
        ref={inputRef}
        value={feedback}
        onChange={e => setFeedback(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="What needs to be fixed?"
        rows={3}
        style={{
          width: '100%',
          background: NOLAN_PALETTE.bg,
          border: `1px solid ${NOLAN_PALETTE.border}`,
          borderRadius: 4,
          color: NOLAN_PALETTE.text,
          fontFamily: 'monospace',
          fontSize: 10,
          padding: '6px 8px',
          resize: 'none',
          outline: 'none',
        }}
      />

      {/* Hint + Submit */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
        <span style={{ color: '#444', fontSize: 8 }}>
          ⌘+Enter to submit
        </span>
        <button
          onClick={handleSubmit}
          disabled={!feedback.trim()}
          style={{
            padding: '4px 14px',
            background: feedback.trim() ? '#1a1a1a' : NOLAN_PALETTE.bg,
            border: `1px solid ${feedback.trim() ? NOLAN_PALETTE.text : NOLAN_PALETTE.border}`,
            borderRadius: 4,
            color: feedback.trim() ? NOLAN_PALETTE.text : NOLAN_PALETTE.textMuted,
            fontSize: 10,
            cursor: feedback.trim() ? 'pointer' : 'default',
            fontFamily: 'monospace',
          }}
        >
          ↻ Redo
        </button>
      </div>
    </div>
  );
}
