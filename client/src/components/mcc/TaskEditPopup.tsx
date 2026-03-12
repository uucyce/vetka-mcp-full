/**
 * MARKER_154.8A: TaskEditPopup — inline task editor overlay.
 *
 * Opens when user clicks "Edit" on task-level FooterActionBar.
 * Allows editing: team preset, description, workflow template.
 * Dispatches task on save.
 *
 * MARKER_175B: Added workflow family selector grid.
 *
 * @phase 154
 * @wave 3
 * @status active
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

const PRESETS = [
  { value: 'dragon_bronze', label: '🥉 Bronze', desc: 'Qwen+Grok+Mimo — fast, cheap' },
  { value: 'dragon_silver', label: '🥈 Silver', desc: 'Kimi+Grok+Qwen+GLM — balanced' },
  { value: 'dragon_gold', label: '🥇 Gold', desc: 'Kimi+Grok+Qwen+Qwen-235b — best quality' },
];

const PHASE_TYPES = [
  { value: 'build', label: 'Build', icon: '🔨' },
  { value: 'fix', label: 'Fix', icon: '🔧' },
  { value: 'research', label: 'Research', icon: '🔍' },
];

// MARKER_175B.WORKFLOW_TEMPLATES: 8 non-stub workflow families + Auto
const WORKFLOW_FAMILIES = [
  { value: '', label: 'Auto', icon: '🤖', desc: 'Architect heuristic selects best workflow' },
  { value: 'bmad_default', label: 'BMAD Full', icon: '📋', desc: 'Full pipeline: Scout→Architect→Coder→Verifier' },
  { value: 'ralph_loop', label: 'Ralph Solo', icon: '🔄', desc: 'Single-agent loop with self-correction' },
  { value: 'g3_critic_coder', label: 'G3 Critic+Coder', icon: '👥', desc: 'Critic reviews coder output in loop' },
  { value: 'quick_fix', label: 'Quick Fix', icon: '⚡', desc: 'Minimal pipeline for small patches' },
  { value: 'research_first', label: 'Research First', icon: '🔬', desc: 'Deep research before implementation' },
  { value: 'refactor', label: 'Refactor', icon: '🏗️', desc: 'Structural code reorganization' },
  { value: 'test_only', label: 'Tests Only', icon: '🧪', desc: 'Write and run tests exclusively' },
  { value: 'docs_update', label: 'Docs Update', icon: '📝', desc: 'Documentation generation and updates' },
];

interface TaskEditPopupProps {
  taskId: string;
  title: string;
  description?: string;
  preset?: string;
  phaseType?: string;
  workflowFamily?: string;
  onSave: (updates: { description: string; preset: string; phaseType: string; workflowFamily: string }) => void;
  onDispatch: () => void;
  onClose: () => void;
}

export function TaskEditPopup({
  taskId,
  title,
  description: initialDesc = '',
  preset: initialPreset = 'dragon_silver',
  phaseType: initialPhaseType = 'build',
  workflowFamily: initialWorkflowFamily = '',
  onSave,
  onDispatch,
  onClose,
}: TaskEditPopupProps) {
  const [description, setDescription] = useState(initialDesc);
  const [preset, setPreset] = useState(initialPreset);
  const [phaseType, setPhaseType] = useState(initialPhaseType);
  const [workflowFamily, setWorkflowFamily] = useState(initialWorkflowFamily);
  const overlayRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  // Close on click outside
  const handleOverlayClick = useCallback((e: React.MouseEvent) => {
    if (e.target === overlayRef.current) onClose();
  }, [onClose]);

  const handleSave = useCallback(() => {
    onSave({ description, preset, phaseType, workflowFamily });
    onClose();
  }, [description, preset, phaseType, workflowFamily, onSave, onClose]);

  const handleDispatch = useCallback(() => {
    onSave({ description, preset, phaseType, workflowFamily });
    onDispatch();
    onClose();
  }, [description, preset, phaseType, workflowFamily, onSave, onDispatch, onClose]);

  return (
    <div
      ref={overlayRef}
      onClick={handleOverlayClick}
      style={{
        position: 'absolute',
        inset: 0,
        background: 'rgba(0,0,0,0.6)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100,
      }}
    >
      <div
        style={{
          background: NOLAN_PALETTE.bgDim,
          border: `1px solid ${NOLAN_PALETTE.border}`,
          borderRadius: 8,
          padding: '16px 20px',
          width: 380,
          maxHeight: '80vh',
          overflow: 'auto',
          fontFamily: 'monospace',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
          <div style={{ color: NOLAN_PALETTE.text, fontSize: 13, fontWeight: 600 }}>
            Edit Task
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: NOLAN_PALETTE.textMuted,
              cursor: 'pointer',
              fontSize: 14,
              padding: 0,
            }}
          >
            ✕
          </button>
        </div>

        {/* Task title (read-only) */}
        <div style={{ color: NOLAN_PALETTE.textAccent, fontSize: 11, marginBottom: 12 }}>
          {title}
          <span style={{ color: '#444', fontSize: 8, marginLeft: 8 }}>{taskId}</span>
        </div>

        {/* Description */}
        <label style={{ color: NOLAN_PALETTE.textMuted, fontSize: 9, display: 'block', marginBottom: 4 }}>
          DESCRIPTION
        </label>
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
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
            resize: 'vertical',
            outline: 'none',
          }}
        />

        {/* Team Preset */}
        <label style={{ color: NOLAN_PALETTE.textMuted, fontSize: 9, display: 'block', marginTop: 12, marginBottom: 4 }}>
          TEAM
        </label>
        <div style={{ display: 'flex', gap: 6 }}>
          {PRESETS.map(p => (
            <button
              key={p.value}
              onClick={() => setPreset(p.value)}
              title={p.desc}
              style={{
                flex: 1,
                padding: '5px 0',
                background: preset === p.value ? NOLAN_PALETTE.bgLight : NOLAN_PALETTE.bg,
                border: `1px solid ${preset === p.value ? NOLAN_PALETTE.text : NOLAN_PALETTE.border}`,
                borderRadius: 4,
                color: preset === p.value ? NOLAN_PALETTE.text : NOLAN_PALETTE.textMuted,
                fontSize: 10,
                cursor: 'pointer',
                fontFamily: 'monospace',
                transition: 'all 0.15s',
              }}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Phase Type */}
        <label style={{ color: NOLAN_PALETTE.textMuted, fontSize: 9, display: 'block', marginTop: 12, marginBottom: 4 }}>
          PHASE
        </label>
        <div style={{ display: 'flex', gap: 6 }}>
          {PHASE_TYPES.map(p => (
            <button
              key={p.value}
              onClick={() => setPhaseType(p.value)}
              style={{
                flex: 1,
                padding: '5px 0',
                background: phaseType === p.value ? NOLAN_PALETTE.bgLight : NOLAN_PALETTE.bg,
                border: `1px solid ${phaseType === p.value ? NOLAN_PALETTE.text : NOLAN_PALETTE.border}`,
                borderRadius: 4,
                color: phaseType === p.value ? NOLAN_PALETTE.text : NOLAN_PALETTE.textMuted,
                fontSize: 10,
                cursor: 'pointer',
                fontFamily: 'monospace',
                transition: 'all 0.15s',
              }}
            >
              {p.icon} {p.label}
            </button>
          ))}
        </div>

        {/* MARKER_175B: Workflow Family Selector */}
        <label style={{ color: NOLAN_PALETTE.textMuted, fontSize: 9, display: 'block', marginTop: 12, marginBottom: 4 }}>
          WORKFLOW
        </label>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 4 }}>
          {WORKFLOW_FAMILIES.map(wf => (
            <button
              key={wf.value}
              onClick={() => setWorkflowFamily(wf.value)}
              title={wf.desc}
              style={{
                padding: '4px 2px',
                background: workflowFamily === wf.value ? NOLAN_PALETTE.bgLight : NOLAN_PALETTE.bg,
                border: `1px solid ${workflowFamily === wf.value ? NOLAN_PALETTE.text : NOLAN_PALETTE.border}`,
                borderRadius: 4,
                color: workflowFamily === wf.value ? NOLAN_PALETTE.text : NOLAN_PALETTE.textMuted,
                fontSize: 9,
                cursor: 'pointer',
                fontFamily: 'monospace',
                transition: 'all 0.15s',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {wf.icon} {wf.label}
            </button>
          ))}
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <button
            onClick={handleSave}
            style={{
              flex: 1,
              padding: '7px 0',
              background: NOLAN_PALETTE.bgLight,
              border: `1px solid ${NOLAN_PALETTE.border}`,
              borderRadius: 4,
              color: NOLAN_PALETTE.text,
              fontSize: 10,
              cursor: 'pointer',
              fontFamily: 'monospace',
            }}
          >
            Save
          </button>
          <button
            onClick={handleDispatch}
            style={{
              flex: 1,
              padding: '7px 0',
              background: '#1a1a1a',
              border: `1px solid ${NOLAN_PALETTE.text}`,
              borderRadius: 4,
              color: NOLAN_PALETTE.text,
              fontSize: 10,
              fontWeight: 600,
              cursor: 'pointer',
              fontFamily: 'monospace',
            }}
          >
            ▶ Save & Launch
          </button>
        </div>
      </div>
    </div>
  );
}
