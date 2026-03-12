/**
 * MARKER_137.1A: League Selector — horizontal preset tabs.
 * Replaces FilterBar. Shows all presets as clickable chips.
 * Active preset highlighted. "+ New" for creating custom presets.
 *
 * @phase 137
 * @status active
 */

import { useState, useEffect, useCallback } from 'react';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
// MARKER_176.15: Centralized MCC API config import.
import { API_BASE } from '../../config/api.config';

const PIPELINE_API = `${API_BASE}/pipeline`;

export interface PresetInfo {
  name: string;
  description: string;
  provider: string;
  roles: Record<string, string>;
}

interface LeagueSelectorProps {
  activePreset: string;
  onPresetChange: (name: string) => void;
  compact?: boolean;
}

export function LeagueSelector({
  activePreset,
  onPresetChange,
  compact = false,
}: LeagueSelectorProps) {
  const [presets, setPresets] = useState<Record<string, PresetInfo>>({});
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');

  // Fetch presets on mount
  useEffect(() => {
    fetch(`${PIPELINE_API}/presets`)
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          setPresets(data.presets || {});
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  // MARKER_137.1B: Create new preset by cloning active
  const handleCreate = useCallback(async () => {
    if (!newName.trim()) return;
    const cloneName = newName.trim().toLowerCase().replace(/\s+/g, '_');

    try {
      const res = await fetch(`${PIPELINE_API}/presets/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: cloneName,
          clone_from: activePreset,
        }),
      });
      const data = await res.json();
      if (data.success) {
        // Refresh presets
        const fresh = await fetch(`${PIPELINE_API}/presets`).then(r => r.json());
        if (fresh.success) {
          setPresets(fresh.presets || {});
          onPresetChange(cloneName);
        }
      }
    } catch (e) {
      console.warn('[LeagueSelector] Create failed:', e);
    }

    setCreating(false);
    setNewName('');
  }, [newName, activePreset, onPresetChange]);

  // MARKER_137.1C: Get tier icon for preset
  const getPresetIcon = (name: string): string => {
    if (name.includes('gold')) return '◆';
    if (name.includes('silver')) return '◇';
    if (name.includes('bronze')) return '○';
    if (name.includes('titan')) return '■';
    return '●';
  };

  // MARKER_137.1D: Get short display name
  const getDisplayName = (name: string): string => {
    return name
      .replace('dragon_', '')
      .replace('titans_', 't:')
      .replace(/_/g, ' ');
  };

  if (loading) {
    return (
      <div style={{
        padding: compact ? '4px 8px' : '6px 12px',
        borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
        background: NOLAN_PALETTE.bgDim,
        fontSize: 10,
        color: NOLAN_PALETTE.textDim,
      }}>
        loading presets...
      </div>
    );
  }

  const presetNames = Object.keys(presets);

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        padding: compact ? '4px 8px' : '6px 12px',
        borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
        background: NOLAN_PALETTE.bgDim,
        overflowX: 'auto',
        flexShrink: 0,
      }}
    >
      {/* MARKER_137.1E: Preset chips */}
      {presetNames.map((name) => {
        const isActive = name === activePreset;
        const preset = presets[name];
        const roleCount = preset?.roles ? Object.keys(preset.roles).length : 0;

        return (
          <button
            key={name}
            onClick={() => onPresetChange(name)}
            title={`${name}\n${preset?.description || ''}\n${roleCount} roles • ${preset?.provider || 'unknown'}`}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              padding: compact ? '3px 8px' : '4px 10px',
              background: isActive ? 'rgba(255,255,255,0.08)' : 'transparent',
              border: `1px solid ${isActive ? '#fff' : NOLAN_PALETTE.borderDim}`,
              borderRadius: 3,
              color: isActive ? '#fff' : NOLAN_PALETTE.textMuted,
              fontSize: 10,
              fontFamily: 'monospace',
              cursor: 'pointer',
              transition: 'all 0.15s',
              whiteSpace: 'nowrap',
              flexShrink: 0,
            }}
          >
            <span style={{ fontSize: 8 }}>{getPresetIcon(name)}</span>
            <span>{getDisplayName(name)}</span>
          </button>
        );
      })}

      {/* MARKER_137.1F: New preset button / inline input */}
      {creating ? (
        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          <input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreate();
              if (e.key === 'Escape') { setCreating(false); setNewName(''); }
            }}
            placeholder="preset name"
            style={{
              background: 'rgba(0,0,0,0.4)',
              border: `1px solid ${NOLAN_PALETTE.borderLight}`,
              borderRadius: 2,
              padding: '3px 6px',
              color: '#fff',
              fontSize: 10,
              fontFamily: 'monospace',
              width: 100,
              outline: 'none',
            }}
          />
          <button
            onClick={handleCreate}
            style={{
              background: 'rgba(255,255,255,0.08)',
              border: `1px solid ${NOLAN_PALETTE.borderDim}`,
              borderRadius: 2,
              padding: '3px 6px',
              color: NOLAN_PALETTE.text,
              fontSize: 10,
              cursor: 'pointer',
            }}
          >
            +
          </button>
          <button
            onClick={() => { setCreating(false); setNewName(''); }}
            style={{
              background: 'transparent',
              border: 'none',
              color: NOLAN_PALETTE.textDim,
              fontSize: 10,
              cursor: 'pointer',
            }}
          >
            ×
          </button>
        </div>
      ) : (
        <button
          onClick={() => setCreating(true)}
          title="Clone current preset as new"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 3,
            padding: compact ? '3px 6px' : '4px 8px',
            background: 'transparent',
            border: `1px dashed ${NOLAN_PALETTE.borderDim}`,
            borderRadius: 3,
            color: NOLAN_PALETTE.textDim,
            fontSize: 10,
            fontFamily: 'monospace',
            cursor: 'pointer',
            transition: 'all 0.15s',
            whiteSpace: 'nowrap',
            flexShrink: 0,
          }}
        >
          + new
        </button>
      )}
    </div>
  );
}
