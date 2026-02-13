/**
 * MARKER_143.P2: PresetDropdown — team/workflow selector dropdown.
 * Replaces LeagueSelector horizontal tabs + hardcoded <select>.
 * Groups presets by family (Dragon, Titan, Other).
 *
 * @phase 143
 * @status active
 */
import { useState, useRef, useEffect, useMemo } from 'react';
import { useMCCStore } from '../../store/useMCCStore';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

// Icons by preset family
function getPresetIcon(name: string): string {
  if (name.includes('gold')) return '◆';
  if (name.includes('silver')) return '◇';
  if (name.includes('bronze')) return '○';
  if (name.includes('titan')) return '■';
  return '●';
}

// Human-readable display name
function displayName(name: string): string {
  return name
    .replace(/^dragon_/, '')
    .replace(/^titans?_/, 't:')
    .replace(/_/g, ' ');
}

// Group presets by family
function groupPresets(presets: Record<string, any>): { label: string; items: string[] }[] {
  const dragon: string[] = [];
  const titan: string[] = [];
  const other: string[] = [];

  for (const name of Object.keys(presets)) {
    if (name.startsWith('dragon_')) dragon.push(name);
    else if (name.startsWith('titan')) titan.push(name);
    else other.push(name);
  }

  const groups: { label: string; items: string[] }[] = [];
  if (dragon.length) groups.push({ label: 'Dragon', items: dragon });
  if (titan.length) groups.push({ label: 'Titan', items: titan });
  if (other.length) groups.push({ label: 'Other', items: other });
  return groups;
}

export function PresetDropdown() {
  const { activePreset, setActivePreset, presets, fetchPresets } = useMCCStore();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const ref = useRef<HTMLDivElement>(null);

  // Fetch presets on mount
  useEffect(() => {
    if (Object.keys(presets).length === 0) fetchPresets();
  }, [presets, fetchPresets]);

  // Close on click outside
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const groups = useMemo(() => groupPresets(presets), [presets]);

  const filteredGroups = useMemo(() => {
    if (!search.trim()) return groups;
    const q = search.toLowerCase();
    return groups
      .map(g => ({
        ...g,
        items: g.items.filter(name =>
          name.toLowerCase().includes(q) ||
          displayName(name).toLowerCase().includes(q)
        ),
      }))
      .filter(g => g.items.length > 0);
  }, [groups, search]);

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      {/* Trigger button */}
      <button
        onClick={() => setOpen(!open)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 10px',
          background: open ? 'rgba(255,255,255,0.06)' : 'transparent',
          border: `1px solid ${NOLAN_PALETTE.borderDim}`,
          borderRadius: 3,
          color: NOLAN_PALETTE.text,
          fontSize: 10,
          fontFamily: 'monospace',
          cursor: 'pointer',
          minWidth: 120,
        }}
      >
        <span>{getPresetIcon(activePreset)}</span>
        <span style={{ fontWeight: 600 }}>{displayName(activePreset)}</span>
        <span style={{ color: NOLAN_PALETTE.textDim, marginLeft: 'auto' }}>▾</span>
      </button>

      {/* Dropdown */}
      {open && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            marginTop: 2,
            width: 280,
            background: '#111',
            border: `1px solid ${NOLAN_PALETTE.border}`,
            borderRadius: 4,
            zIndex: 1000,
            boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
            maxHeight: 340,
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Search */}
          <div style={{ padding: '6px 8px', borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}` }}>
            <input
              autoFocus
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="search presets..."
              style={{
                width: '100%',
                background: 'rgba(255,255,255,0.03)',
                border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                borderRadius: 2,
                color: NOLAN_PALETTE.text,
                padding: '4px 8px',
                fontSize: 10,
                fontFamily: 'monospace',
                outline: 'none',
              }}
              onKeyDown={e => {
                if (e.key === 'Escape') setOpen(false);
              }}
            />
          </div>

          {/* Grouped list */}
          <div style={{ overflowY: 'auto', flex: 1, padding: 4 }}>
            {filteredGroups.map(group => (
              <div key={group.label}>
                <div style={{
                  fontSize: 8,
                  color: NOLAN_PALETTE.textDim,
                  textTransform: 'uppercase',
                  letterSpacing: 1.5,
                  padding: '6px 8px 2px',
                }}>
                  {group.label}
                </div>
                {group.items.map(name => {
                  const isActive = name === activePreset;
                  const config = presets[name];
                  const desc = config?.description?.replace(/^[^\w]*/, '').slice(0, 50) || '';
                  return (
                    <div
                      key={name}
                      onClick={() => {
                        setActivePreset(name);
                        setOpen(false);
                        setSearch('');
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        padding: '5px 8px',
                        borderRadius: 2,
                        cursor: 'pointer',
                        background: isActive ? 'rgba(255,255,255,0.06)' : 'transparent',
                        borderLeft: isActive ? '2px solid #fff' : '2px solid transparent',
                      }}
                      onMouseEnter={e => {
                        if (!isActive) e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
                      }}
                      onMouseLeave={e => {
                        if (!isActive) e.currentTarget.style.background = 'transparent';
                      }}
                    >
                      <span style={{ fontSize: 11, color: NOLAN_PALETTE.textNormal }}>
                        {getPresetIcon(name)}
                      </span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{
                          fontSize: 10,
                          color: isActive ? '#fff' : NOLAN_PALETTE.text,
                          fontWeight: isActive ? 600 : 400,
                          fontFamily: 'monospace',
                        }}>
                          {displayName(name)}
                        </div>
                        {desc && (
                          <div style={{
                            fontSize: 8,
                            color: NOLAN_PALETTE.textDim,
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}>
                            {desc}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ))}
            {filteredGroups.length === 0 && (
              <div style={{ color: NOLAN_PALETTE.textDim, fontSize: 10, padding: 12, textAlign: 'center' }}>
                No presets found
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
