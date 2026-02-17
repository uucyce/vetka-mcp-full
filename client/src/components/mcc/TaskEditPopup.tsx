/**
 * MARKER_154.8A: TaskEditPopup — inline task editor overlay.
 *
 * Opens when user clicks "Edit" on task-level FooterActionBar.
 * Allows editing: team preset, description, workflow template.
 * Dispatches task on save.
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

interface TaskEditPopupProps {
  taskId: string;
  title: string;
  description?: string;
  preset?: string;
  phaseType?: string;
  onSave: (updates: { description: string; preset: string; phaseType: string }) => void;
  onDispatch: () => void;
  onClose: () => void;
}

export function TaskEditPopup({
  taskId,
  title,
  description: initialDesc = '',
  preset: initialPreset = 'dragon_silver',
  phaseType: initialPhaseType = 'build',
  onSave,
  onDispatch,
  onClose,
}: TaskEditPopupProps) {
  const [description, setDescription] = useState(initialDesc);
  const [preset, setPreset] = useState(initialPreset);
  const [phaseType, setPhaseType] = useState(initialPhaseType);
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
    onSave({ description, preset, phaseType });
    onClose();
  }, [description, preset, phaseType, onSave, onClose]);

  const handleDispatch = useCallback(() => {
    onSave({ description, preset, phaseType });
    onDispatch();
    onClose();
  }, [description, preset, phaseType, onSave, onDispatch, onClose]);

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
          width: 360,
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
