/**
 * MARKER_135.3A: Detail Panel — right sidebar with node info.
 * MARKER_137.3A: Simplified to active-preset-only. No scrolling through all presets.
 * Shows selected node details, role config for active preset, prompt editor.
 * Edge info display when edge is selected.
 *
 * @phase 137
 * @status active
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import { useStore } from '../../store/useStore';
import type { DAGNode, DAGStats } from '../../types/dag';
// MARKER_176.15: Centralized MCC API config import.
import { API_BASE } from '../../config/api.config';

const PIPELINE_API = `${API_BASE}/pipeline`;
const MODELS_API = `${API_BASE}/models`;

// MARKER_137.7A: Map Balance panel key provider names → model source field values
// Balance tab uses provider names like 'polza', 'openrouter', 'xai', 'openai'
// Model API uses source field like 'polza', 'openrouter', 'direct', 'nanogpt'
const KEY_PROVIDER_TO_MODEL_SOURCE: Record<string, string[]> = {
  polza: ['polza'],
  openrouter: ['openrouter'],
  xai: ['direct'],
  openai: ['direct'],
  anthropic: ['direct'],
  google: ['gemini_direct'],
  nanogpt: ['nanogpt'],
  poe: ['poe'],
};

// MARKER_137.6A: Cached model list — fetched once, shared across all RoleEditors
interface ModelInfo {
  id: string;
  provider: string;
  source: string;
}

let _cachedModels: ModelInfo[] | null = null;
let _modelsFetching = false;
const _modelListeners: Array<(models: ModelInfo[]) => void> = [];

function fetchModelsOnce() {
  if (_cachedModels) return;
  if (_modelsFetching) return;
  _modelsFetching = true;

  fetch(MODELS_API)
    .then(r => r.json())
    .then(data => {
      const models: ModelInfo[] = (data.models || []).map((m: any) => ({
        id: m.id || '',
        provider: m.provider || '',
        source: m.source || '',
      }));
      _cachedModels = models;
      _modelListeners.forEach(cb => cb(models));
      _modelListeners.length = 0;
    })
    .catch(() => {
      _modelsFetching = false;
    });
}

function useModelList(): ModelInfo[] {
  const [models, setModels] = useState<ModelInfo[]>(_cachedModels || []);

  useEffect(() => {
    if (_cachedModels) {
      setModels(_cachedModels);
      return;
    }
    _modelListeners.push(setModels);
    fetchModelsOnce();
  }, []);

  return models;
}

interface DetailPanelProps {
  node: DAGNode | null;
  stats: DAGStats | null;
  onAction: (action: string) => void;
  activePreset: string;
  selectedEdge?: { id: string; source: string; target: string; type: string } | null;
}

// MARKER_137.3B: Role editor — shows ONLY active preset model, not all presets
// MARKER_137.6B: Model selector with searchable dropdown from /api/models
// MARKER_137.7B: Filters models by selected Balance key provider
// MARKER_143.P6C: Exported for use in RolesConfigPanel (MCCDetailPanel)
export function RoleEditor({ role, activePreset }: { role: string; activePreset: string }) {
  const [model, setModel] = useState('');
  const [prompt, setPrompt] = useState('');
  const [temperature, setTemperature] = useState(0.3);
  const [loading, setLoading] = useState(true);
  const [editingPrompt, setEditingPrompt] = useState(false);
  const [editedPrompt, setEditedPrompt] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');

  // MARKER_137.6C: Model search combobox state
  const [searchQuery, setSearchQuery] = useState('');
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [highlightIdx, setHighlightIdx] = useState(0);
  const allModels = useModelList();
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // MARKER_137.7C: Get selected key from Balance panel via Zustand store
  const selectedKey = useStore(s => s.selectedKey);
  const favoriteKeys = useStore(s => s.favoriteKeys);
  const activeSource = useMemo(() => {
    // Priority matches VETKA ModelDirectory pattern:
    // selected key provider > starred providers fallback > no source filter.
    if (selectedKey?.provider) {
      return KEY_PROVIDER_TO_MODEL_SOURCE[selectedKey.provider] || [selectedKey.provider];
    }
    const starredProviders = Array.from(new Set(
      favoriteKeys
        .map((k) => String(k || '').split(':')[0].trim().toLowerCase())
        .filter(Boolean)
    ));
    if (starredProviders.length === 0) return null;
    const mapped = starredProviders.flatMap((provider) => KEY_PROVIDER_TO_MODEL_SOURCE[provider] || [provider]);
    return Array.from(new Set(mapped));
  }, [selectedKey, favoriteKeys]);

  // MARKER_137.7D: Filter by source (selected key provider) → deduplicate by id → filter by search
  const filteredModels = useMemo(() => {
    // Step 1: Filter by source if a key is selected
    let pool = allModels;
    if (activeSource) {
      pool = allModels.filter(m => activeSource.includes(m.source));
    }

    // Step 2: Deduplicate by model id (keep first occurrence)
    const seen = new Set<string>();
    const deduped: ModelInfo[] = [];
    for (const m of pool) {
      if (!seen.has(m.id)) {
        seen.add(m.id);
        deduped.push(m);
      }
    }

    // Step 3: Apply search filter
    if (!searchQuery.trim()) return deduped.slice(0, 80);
    const q = searchQuery.toLowerCase();
    return deduped
      .filter(m => m.id.toLowerCase().includes(q) || m.provider.toLowerCase().includes(q))
      .slice(0, 80);
  }, [allModels, searchQuery, activeSource]);

  // Fetch model for active preset + prompt for this role
  useEffect(() => {
    setLoading(true);
    setSaveMsg('');
    setEditingPrompt(false);
    setDropdownOpen(false);

    Promise.all([
      fetch(`${PIPELINE_API}/presets/${activePreset}`).then(r => r.json()).catch(() => ({ success: false })),
      fetch(`${PIPELINE_API}/prompts/${role}`).then(r => r.json()).catch(() => ({ success: false })),
    ]).then(([presetData, promptData]) => {
      if (presetData.success && presetData.preset) {
        const roles = presetData.preset.roles || {};
        const m = roles[role] || '';
        setModel(m);
        setSearchQuery(m);
      }
      if (promptData.success && promptData.prompt) {
        setPrompt(promptData.prompt.system || '');
        setTemperature(promptData.prompt.temperature ?? 0.3);
        setEditedPrompt(promptData.prompt.system || '');
      }
      setLoading(false);
    });
  }, [role, activePreset]);

  // Save model change
  const saveModel = useCallback(async (newModel: string) => {
    if (newModel === model) return;
    setSaving(true);
    setSaveMsg('');
    try {
      const res = await fetch(`${PIPELINE_API}/presets/update-role`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preset_name: activePreset, role, model: newModel }),
      });
      const data = await res.json();
      if (data.success) {
        setModel(newModel);
        setSaveMsg('model saved ✓');
      } else {
        setSaveMsg(`error: ${data.detail || 'unknown'}`);
      }
    } catch (e) {
      setSaveMsg('network error');
    }
    setSaving(false);
    setTimeout(() => setSaveMsg(''), 2500);
  }, [model, activePreset, role]);

  // Select a model from dropdown
  const selectModel = useCallback((modelId: string) => {
    setSearchQuery(modelId);
    setDropdownOpen(false);
    saveModel(modelId);
  }, [saveModel]);

  // Close dropdown on click outside
  useEffect(() => {
    if (!dropdownOpen) return;
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node) &&
          inputRef.current && !inputRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
        // Restore current model if user didn't select
        setSearchQuery(model);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [dropdownOpen, model]);

  // Save prompt change
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
    setTimeout(() => setSaveMsg(''), 2500);
  }, [role, editedPrompt, temperature]);

  if (loading) {
    return (
      <div style={{ color: NOLAN_PALETTE.textDim, fontSize: 10, padding: 4, marginTop: 8 }}>
        loading config...
      </div>
    );
  }

  return (
    <div style={{ marginTop: 12 }}>
      {/* Section header */}
      <SectionHeader label="role config" />

      {/* MARKER_137.6D: Model — searchable combobox */}
      <div style={{ marginBottom: 8, position: 'relative' }}>
        <div style={{ fontSize: 8, color: NOLAN_PALETTE.textDim, textTransform: 'uppercase', marginBottom: 3 }}>
          model ({activePreset})
        </div>
        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          <input
            ref={inputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setDropdownOpen(true);
              setHighlightIdx(0);
            }}
            onFocus={() => {
              setDropdownOpen(true);
              setHighlightIdx(0);
            }}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') {
                e.preventDefault();
                setHighlightIdx(i => Math.min(i + 1, filteredModels.length - 1));
              } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setHighlightIdx(i => Math.max(i - 1, 0));
              } else if (e.key === 'Enter') {
                e.preventDefault();
                if (dropdownOpen && filteredModels[highlightIdx]) {
                  selectModel(filteredModels[highlightIdx].id);
                } else if (searchQuery.trim()) {
                  // Allow custom model ID entry
                  selectModel(searchQuery.trim());
                }
              } else if (e.key === 'Escape') {
                setDropdownOpen(false);
                setSearchQuery(model);
                inputRef.current?.blur();
              }
            }}
            disabled={saving}
            placeholder="search models..."
            style={{
              flex: 1,
              background: 'rgba(0,0,0,0.3)',
              border: `1px solid ${dropdownOpen ? NOLAN_PALETTE.borderLight : NOLAN_PALETTE.borderDim}`,
              borderRadius: 2,
              padding: '4px 6px',
              color: '#fff',
              fontSize: 10,
              fontFamily: 'monospace',
              outline: 'none',
            }}
          />
          {/* MARKER_137.7E: Show source filter badge */}
          <span style={{ fontSize: 8, color: activeSource ? '#6a8a6a' : NOLAN_PALETTE.textDim }}>
            {activeSource ? activeSource[0] : (allModels.length > 0 ? 'all' : '...')}
          </span>
        </div>

        {/* MARKER_137.6E: Dropdown list */}
        {dropdownOpen && filteredModels.length > 0 && (
          <div
            ref={dropdownRef}
            style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              right: 0,
              maxHeight: 200,
              overflowY: 'auto',
              background: '#111',
              border: `1px solid ${NOLAN_PALETTE.borderLight}`,
              borderRadius: '0 0 3px 3px',
              zIndex: 100,
              boxShadow: '0 4px 12px rgba(0,0,0,0.6)',
            }}
          >
            {filteredModels.map((m, idx) => {
              const isCurrent = m.id === model;
              const isHighlighted = idx === highlightIdx;
              return (
                <div
                  key={`${m.id}-${m.source}`}
                  onClick={() => selectModel(m.id)}
                  onMouseEnter={() => setHighlightIdx(idx)}
                  style={{
                    padding: '4px 8px',
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: isHighlighted
                      ? 'rgba(255,255,255,0.08)'
                      : isCurrent
                        ? 'rgba(255,255,255,0.04)'
                        : 'transparent',
                    borderLeft: isCurrent ? '2px solid #fff' : '2px solid transparent',
                  }}
                >
                  <span style={{
                    fontSize: 9,
                    fontFamily: 'monospace',
                    color: isCurrent ? '#fff' : NOLAN_PALETTE.text,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    flex: 1,
                  }}>
                    {m.id}
                  </span>
                  <span style={{
                    fontSize: 7,
                    color: NOLAN_PALETTE.textDim,
                    marginLeft: 6,
                    flexShrink: 0,
                    textTransform: 'uppercase',
                  }}>
                    {m.source}
                  </span>
                </div>
              );
            })}
            {filteredModels.length >= 80 && (
              <div style={{
                padding: '3px 8px',
                fontSize: 8,
                color: NOLAN_PALETTE.textDim,
                textAlign: 'center',
                borderTop: `1px solid ${NOLAN_PALETTE.borderDim}`,
              }}>
                type to filter • {activeSource ? `${activeSource[0]} models` : `${allModels.length} all models`}
              </div>
            )}
            {!activeSource && filteredModels.length > 0 && filteredModels.length < 80 && (
              <div style={{
                padding: '3px 8px',
                fontSize: 8,
                color: '#8a8a6a',
                textAlign: 'center',
                borderTop: `1px solid ${NOLAN_PALETTE.borderDim}`,
              }}>
                select a key in Balance tab to filter by provider
              </div>
            )}
          </div>
        )}
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
        marginTop: 8,
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
              minHeight: 100,
              maxHeight: 200,
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
        <div>
          <pre
            style={{
              background: '#181818',
              color: '#b0b0b0',
              padding: '6px 8px',
              borderRadius: 3,
              fontSize: 9,
              fontFamily: 'monospace',
              overflow: 'auto',
              maxHeight: 80,
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
            {prompt.slice(0, 300)}
            {prompt.length > 300 && '\n... (click to edit)'}
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
        </div>
      )}
    </div>
  );
}


// MARKER_137.3C: Main DetailPanel
export function DetailPanel({ node, stats, onAction, activePreset, selectedEdge }: DetailPanelProps) {
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
      {/* MARKER_137.3D: Edge info (when edge is selected) */}
      {selectedEdge && (
        <div style={{ marginBottom: 12 }}>
          <SectionHeader label="connection" />
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 8,
          }}>
            <MetaItem label="From" value={selectedEdge.source.split('_').slice(-1)[0]} />
            <MetaItem label="To" value={selectedEdge.target.split('_').slice(-1)[0]} />
            <MetaItem label="Type" value={selectedEdge.type} />
            <MetaItem label="ID" value={selectedEdge.id} />
          </div>
        </div>
      )}

      {/* Selected Node Info */}
      {node ? (
        <div style={{ marginBottom: 16 }}>
          <SectionHeader label="selected" />

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
            {node.durationS != null && <MetaItem label="Duration" value={`${node.durationS}s`} />}
            {node.tokens != null && <MetaItem label="Tokens" value={node.tokens} />}
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

          {/* MARKER_137.3E: Role editor for agent nodes — active preset only */}
          {node.type === 'agent' && node.role && (
            <RoleEditor role={node.role} activePreset={activePreset} />
          )}
        </div>
      ) : !selectedEdge ? (
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
      ) : null}

      {/* Stats Summary */}
      {stats && (
        <div style={{ marginTop: 'auto', paddingTop: 12, borderTop: `1px solid ${NOLAN_PALETTE.borderDim}` }}>
          <SectionHeader label="overview" />

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


// ── Shared sub-components ──

function SectionHeader({ label }: { label: string }) {
  return (
    <div
      style={{
        fontSize: 9,
        color: NOLAN_PALETTE.textDim,
        textTransform: 'uppercase',
        letterSpacing: 1,
        marginBottom: 8,
      }}
    >
      {label}
    </div>
  );
}

function MetaItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div style={{ fontSize: 8, color: NOLAN_PALETTE.textDim, textTransform: 'uppercase' }}>
        {label}
      </div>
      <div style={{ fontSize: 11, color: NOLAN_PALETTE.text, wordBreak: 'break-all' }}>
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
