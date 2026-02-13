/**
 * MARKER_135.3A: Detail Panel — right sidebar with node info.
 * MARKER_141.DETAIL_PANEL: Added model selector + prompt viewer/editor for agent nodes.
 * Shows selected node details, stats, and action buttons.
 * When an agent node is selected, allows changing the model and viewing/editing the prompt.
 *
 * @phase 141
 * @status active
 */

import { useState, useEffect, useCallback } from 'react';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import type { DAGNode, DAGStats } from '../../types/dag';

const PIPELINE_API = 'http://localhost:5001/api/pipeline';

interface DetailPanelProps {
  node: DAGNode | null;
  stats: DAGStats | null;
  onAction: (action: string) => void;
}

// MARKER_141.ROLE_EDITOR: Agent role editing sub-component
function RoleEditor({ role }: { role: string }) {
  const [presets, setPresets] = useState<Record<string, any>>({});
  const [defaultPreset, setDefaultPreset] = useState('');
  const [prompt, setPrompt] = useState('');
  const [temperature, setTemperature] = useState(0.3);
  const [loading, setLoading] = useState(true);
  const [editingPrompt, setEditingPrompt] = useState(false);
  const [editedPrompt, setEditedPrompt] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');

  // Fetch presets and prompt for this role
  useEffect(() => {
    setLoading(true);
    setSaveMsg('');
    setEditingPrompt(false);

    Promise.all([
      fetch(`${PIPELINE_API}/presets`).then(r => r.json()).catch(() => ({ success: false })),
      fetch(`${PIPELINE_API}/prompts/${role}`).then(r => r.json()).catch(() => ({ success: false })),
    ]).then(([presetsData, promptData]) => {
      if (presetsData.success) {
        setPresets(presetsData.presets || {});
        setDefaultPreset(presetsData.default_preset || 'dragon_silver');
      }
      if (promptData.success && promptData.prompt) {
        setPrompt(promptData.prompt.system || '');
        setTemperature(promptData.prompt.temperature ?? 0.3);
        setEditedPrompt(promptData.prompt.system || '');
      }
      setLoading(false);
    });
  }, [role]);

  // MARKER_141.CHANGE_MODEL: Save model change for a role in a preset
  const handleModelChange = useCallback(async (presetName: string, newModel: string) => {
    setSaving(true);
    setSaveMsg('');
    try {
      const res = await fetch(`${PIPELINE_API}/presets/update-role`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preset_name: presetName, role, model: newModel }),
      });
      const data = await res.json();
      if (data.success) {
        setSaveMsg(`saved: ${newModel.split('/').pop()}`);
        // Refresh presets
        const fresh = await fetch(`${PIPELINE_API}/presets`).then(r => r.json());
        if (fresh.success) setPresets(fresh.presets || {});
      } else {
        setSaveMsg(`error: ${data.detail || 'unknown'}`);
      }
    } catch (e) {
      setSaveMsg('network error');
    }
    setSaving(false);
    setTimeout(() => setSaveMsg(''), 3000);
  }, [role]);

  // MARKER_141.SAVE_PROMPT: Save prompt changes
  const handleSavePrompt = useCallback(async () => {
    setSaving(true);
    setSaveMsg('');
    try {
      const res = await fetch(`${PIPELINE_API}/prompts/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role, system: editedPrompt, temperature }),
      });
      const data = await res.json();
      if (data.success) {
        setPrompt(editedPrompt);
        setEditingPrompt(false);
        setSaveMsg('prompt saved');
      } else {
        setSaveMsg(`error: ${data.detail || 'unknown'}`);
      }
    } catch (e) {
      setSaveMsg('network error');
    }
    setSaving(false);
    setTimeout(() => setSaveMsg(''), 3000);
  }, [role, editedPrompt, temperature]);

  if (loading) {
    return (
      <div style={{ color: NOLAN_PALETTE.textDim, fontSize: 10, padding: 8 }}>
        loading config...
      </div>
    );
  }

  // Get current model for this role across presets
  const currentPreset = presets[defaultPreset];
  const currentRoles = currentPreset?.roles || currentPreset || {};
  const currentModel = currentRoles[role] || '';

  return (
    <div style={{ marginTop: 12 }}>
      {/* Section header */}
      <div style={{
        fontSize: 9,
        color: NOLAN_PALETTE.textDim,
        textTransform: 'uppercase',
        letterSpacing: 1,
        marginBottom: 8,
        borderTop: `1px solid ${NOLAN_PALETTE.borderDim}`,
        paddingTop: 8,
      }}>
        role config
      </div>

      {/* Current model display */}
      <div style={{ marginBottom: 8 }}>
        <div style={{ fontSize: 8, color: NOLAN_PALETTE.textDim, textTransform: 'uppercase' }}>
          model ({defaultPreset})
        </div>
        <div style={{ fontSize: 11, color: NOLAN_PALETTE.textAccent, marginTop: 2 }}>
          {currentModel || 'not set'}
        </div>
      </div>

      {/* Model per preset — editable */}
      <div style={{ marginBottom: 10 }}>
        <div style={{
          fontSize: 8,
          color: NOLAN_PALETTE.textDim,
          textTransform: 'uppercase',
          marginBottom: 4,
        }}>
          model in each preset
        </div>
        {Object.entries(presets).map(([presetName, preset]: [string, any]) => {
          const roles = preset.roles || preset;
          const model = roles[role] || '';
          const isDefault = presetName === defaultPreset;

          return (
            <div key={presetName} style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              marginBottom: 4,
              padding: '3px 6px',
              background: isDefault ? 'rgba(255,255,255,0.04)' : 'transparent',
              borderRadius: 3,
              border: isDefault ? `1px solid ${NOLAN_PALETTE.borderDim}` : '1px solid transparent',
            }}>
              <span style={{
                fontSize: 9,
                color: isDefault ? NOLAN_PALETTE.text : NOLAN_PALETTE.textDim,
                minWidth: 80,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
                title={presetName}
              >
                {isDefault ? '● ' : '  '}{presetName.replace('dragon_', 'd_')}
              </span>
              <input
                type="text"
                value={model}
                onChange={(e) => {
                  // Optimistic update in local state
                  const updated = { ...presets };
                  const r = updated[presetName].roles || updated[presetName];
                  r[role] = e.target.value;
                  setPresets(updated);
                }}
                onBlur={(e) => {
                  if (e.target.value !== model) {
                    handleModelChange(presetName, e.target.value);
                  }
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    (e.target as HTMLInputElement).blur();
                  }
                }}
                disabled={saving}
                style={{
                  flex: 1,
                  background: 'rgba(0,0,0,0.3)',
                  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  borderRadius: 2,
                  padding: '2px 4px',
                  color: NOLAN_PALETTE.text,
                  fontSize: 9,
                  fontFamily: 'monospace',
                  outline: 'none',
                }}
              />
            </div>
          );
        })}
      </div>

      {/* Save message */}
      {saveMsg && (
        <div style={{
          fontSize: 9,
          color: saveMsg.startsWith('error') ? '#8a6a6a' : '#6a8a6a',
          marginBottom: 6,
        }}>
          {saveMsg}
        </div>
      )}

      {/* Prompt section */}
      <div style={{
        fontSize: 8,
        color: NOLAN_PALETTE.textDim,
        textTransform: 'uppercase',
        letterSpacing: 1,
        marginBottom: 4,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span>system prompt</span>
        <span style={{ fontSize: 9, color: NOLAN_PALETTE.textDim }}>
          temp: {temperature}
        </span>
      </div>

      {editingPrompt ? (
        <>
          {/* Temperature slider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
            <span style={{ fontSize: 8, color: NOLAN_PALETTE.textDim }}>0.0</span>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              style={{ flex: 1, accentColor: '#888' }}
            />
            <span style={{ fontSize: 8, color: NOLAN_PALETTE.textDim }}>{temperature}</span>
          </div>

          <textarea
            value={editedPrompt}
            onChange={(e) => setEditedPrompt(e.target.value)}
            style={{
              width: '100%',
              minHeight: 120,
              maxHeight: 250,
              background: '#181818',
              color: '#d0d0d0',
              border: `1px solid ${NOLAN_PALETTE.borderDim}`,
              borderRadius: 3,
              padding: '6px 8px',
              fontSize: 9,
              fontFamily: 'monospace',
              lineHeight: 1.4,
              resize: 'vertical',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
          <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
            <ActionButton
              label={saving ? '...' : 'Save'}
              onClick={handleSavePrompt}
            />
            <ActionButton
              label="Cancel"
              onClick={() => {
                setEditingPrompt(false);
                setEditedPrompt(prompt);
              }}
              variant="danger"
            />
          </div>
        </>
      ) : (
        <>
          <pre style={{
            background: '#181818',
            color: '#b0b0b0',
            padding: '6px 8px',
            borderRadius: 3,
            fontSize: 9,
            fontFamily: 'monospace',
            overflow: 'auto',
            maxHeight: 120,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            margin: 0,
            border: `1px solid ${NOLAN_PALETTE.borderDim}`,
            cursor: 'pointer',
          }}
            onClick={() => {
              setEditingPrompt(true);
              setEditedPrompt(prompt);
            }}
            title="Click to edit"
          >
            {prompt.slice(0, 500)}
            {prompt.length > 500 && '\n... (click to edit)'}
          </pre>
          <button
            onClick={() => {
              setEditingPrompt(true);
              setEditedPrompt(prompt);
            }}
            style={{
              marginTop: 4,
              background: 'transparent',
              border: `1px solid ${NOLAN_PALETTE.borderDim}`,
              borderRadius: 2,
              padding: '2px 8px',
              color: NOLAN_PALETTE.textNormal,
              fontSize: 9,
              cursor: 'pointer',
              fontFamily: 'monospace',
            }}
          >
            edit prompt
          </button>
        </>
      )}
    </div>
  );
}


export function DetailPanel({ node, stats, onAction }: DetailPanelProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        padding: 12,
        background: NOLAN_PALETTE.bgDim,
        overflow: 'auto',
      }}
    >
      {/* Selected Node Info */}
      {node ? (
        <div style={{ marginBottom: 16 }}>
          <div
            style={{
              fontSize: 9,
              color: NOLAN_PALETTE.textDim,
              textTransform: 'uppercase',
              letterSpacing: 1,
              marginBottom: 8,
            }}
          >
            selected
          </div>

          {/* Node type badge */}
          <div
            style={{
              display: 'inline-block',
              padding: '2px 6px',
              background: NOLAN_PALETTE.bgLight,
              border: `1px solid ${NOLAN_PALETTE.border}`,
              borderRadius: 3,
              fontSize: 9,
              color: NOLAN_PALETTE.textNormal,
              textTransform: 'uppercase',
              marginBottom: 8,
            }}
          >
            {node.type}
          </div>

          {/* Node label */}
          <div
            style={{
              fontSize: 12,
              color: NOLAN_PALETTE.textAccent,
              fontWeight: 500,
              marginBottom: 12,
              lineHeight: 1.4,
            }}
          >
            {node.label}
          </div>

          {/* Metadata grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 8,
              marginBottom: 12,
            }}
          >
            <MetaItem label="Status" value={node.status} />
            <MetaItem label="Layer" value={node.layer} />
            {node.durationS && <MetaItem label="Duration" value={`${node.durationS}s`} />}
            {node.tokens && <MetaItem label="Tokens" value={node.tokens} />}
            {node.model && <MetaItem label="Model" value={node.model} />}
            {node.role && <MetaItem label="Role" value={node.role} />}
            {node.confidence !== undefined && (
              <MetaItem label="Confidence" value={`${Math.round(node.confidence * 100)}%`} />
            )}
          </div>

          {/* Actions */}
          {node.type === 'proposal' && (
            <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
              <ActionButton label="Approve" onClick={() => onAction('approve')} />
              <ActionButton label="Reject" onClick={() => onAction('reject')} variant="danger" />
            </div>
          )}

          {node.type === 'task' && node.status === 'failed' && (
            <ActionButton label="Retry" onClick={() => onAction('retry')} />
          )}

          {/* MARKER_141.ROLE_EDITOR: Show role editor for agent nodes */}
          {node.type === 'agent' && node.role && (
            <RoleEditor role={node.role} />
          )}
        </div>
      ) : (
        <div
          style={{
            color: NOLAN_PALETTE.textDim,
            fontSize: 11,
            textAlign: 'center',
            padding: 20,
          }}
        >
          Click a node to see details
        </div>
      )}

      {/* Stats Summary */}
      {stats && (
        <div style={{ marginTop: 'auto', paddingTop: 12, borderTop: `1px solid ${NOLAN_PALETTE.borderDim}` }}>
          <div
            style={{
              fontSize: 9,
              color: NOLAN_PALETTE.textDim,
              textTransform: 'uppercase',
              letterSpacing: 1,
              marginBottom: 8,
            }}
          >
            overview
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <StatRow label="Total Tasks" value={stats.totalTasks} />
            <StatRow label="Running" value={stats.runningTasks} color={NOLAN_PALETTE.statusRunning} />
            <StatRow label="Completed" value={stats.completedTasks} color={NOLAN_PALETTE.statusDone} />
            <StatRow label="Failed" value={stats.failedTasks} color={NOLAN_PALETTE.statusFailed} />
            <StatRow label="Success Rate" value={`${stats.successRate}%`} />
          </div>
        </div>
      )}
    </div>
  );
}

function MetaItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div style={{ fontSize: 8, color: NOLAN_PALETTE.textDim, textTransform: 'uppercase' }}>
        {label}
      </div>
      <div style={{ fontSize: 11, color: NOLAN_PALETTE.text }}>
        {value}
      </div>
    </div>
  );
}

function StatRow({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10 }}>
      <span style={{ color: NOLAN_PALETTE.textNormal }}>{label}</span>
      <span style={{ color: color || NOLAN_PALETTE.text }}>{value}</span>
    </div>
  );
}

function ActionButton({
  label,
  onClick,
  variant = 'default',
}: {
  label: string;
  onClick: () => void;
  variant?: 'default' | 'danger';
}) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1,
        padding: '6px 10px',
        background: variant === 'danger' ? 'rgba(138,106,106,0.2)' : 'rgba(255,255,255,0.05)',
        border: `1px solid ${variant === 'danger' ? NOLAN_PALETTE.statusFailed : NOLAN_PALETTE.borderDim}`,
        borderRadius: 3,
        color: variant === 'danger' ? NOLAN_PALETTE.statusFailed : NOLAN_PALETTE.textNormal,
        fontSize: 10,
        cursor: 'pointer',
        transition: 'all 0.15s',
      }}
    >
      {label}
    </button>
  );
}
