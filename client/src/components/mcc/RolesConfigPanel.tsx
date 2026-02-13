/**
 * MARKER_143.P6: RolesConfigPanel — dynamic role-to-model overview + editor.
 * Reads roles DYNAMICALLY from active preset API (not hardcoded).
 * Click a role → expands the original RoleEditor from DetailPanel.
 * Only one role expanded at a time.
 * Supports adding custom roles.
 *
 * @phase 143
 * @status active
 */
import { useState, useEffect, useCallback } from 'react';
import { useMCCStore } from '../../store/useMCCStore';
import { RoleEditor } from './DetailPanel';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

const PIPELINE_API = 'http://localhost:5001/api/pipeline';

// MARKER_143.P6D: Role display shortcodes — known roles get abbreviations
const ROLE_SHORT: Record<string, string> = {
  architect: 'ARC',
  researcher: 'RES',
  coder: 'COD',
  verifier: 'VER',
  scout: 'SCT',
  doctor: 'DOC',
};

function getRoleShort(role: string): string {
  return ROLE_SHORT[role] || role.slice(0, 3).toUpperCase();
}

export function RolesConfigPanel() {
  const activePreset = useMCCStore(s => s.activePreset);
  const [roleModels, setRoleModels] = useState<Record<string, string>>({});
  const [expandedRole, setExpandedRole] = useState<string | null>(null);
  const [addingRole, setAddingRole] = useState(false);
  const [newRoleName, setNewRoleName] = useState('');
  const [newRoleModel, setNewRoleModel] = useState('');
  const [addMsg, setAddMsg] = useState('');

  // MARKER_143.P6E: Fetch roles dynamically from active preset
  useEffect(() => {
    fetch(`${PIPELINE_API}/presets/${activePreset}`)
      .then(r => r.json())
      .then(data => {
        if (data.success && data.preset?.roles) {
          setRoleModels(data.preset.roles);
        }
      })
      .catch(() => {});
    // Reset UI on preset change
    setExpandedRole(null);
    setAddingRole(false);
    setAddMsg('');
  }, [activePreset]);

  // MARKER_143.P6F: Add custom role to preset
  const handleAddRole = useCallback(async () => {
    const roleName = newRoleName.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_');
    if (!roleName) { setAddMsg('enter role name'); return; }
    if (roleModels[roleName]) { setAddMsg('role exists'); return; }
    if (!newRoleModel.trim()) { setAddMsg('enter model'); return; }

    try {
      const res = await fetch(`${PIPELINE_API}/presets/update-role`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preset_name: activePreset,
          role: roleName,
          model: newRoleModel.trim(),
        }),
      });
      const data = await res.json();
      if (data.success) {
        setRoleModels(prev => ({ ...prev, [roleName]: newRoleModel.trim() }));
        setNewRoleName('');
        setNewRoleModel('');
        setAddingRole(false);
        setAddMsg('');
      } else {
        setAddMsg(`error: ${data.detail || 'failed'}`);
      }
    } catch {
      setAddMsg('network error');
    }
  }, [activePreset, newRoleName, newRoleModel, roleModels]);

  const roles = Object.entries(roleModels);

  return (
    <div style={{ marginTop: 10 }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 6,
      }}>
        <span style={{
          fontSize: 9, color: '#555', textTransform: 'uppercase', letterSpacing: 1,
        }}>
          team roles ({roles.length})
        </span>
        <span style={{
          fontSize: 8, color: '#444',
          background: 'rgba(255,255,255,0.03)',
          padding: '1px 5px', borderRadius: 2,
        }}>
          {activePreset}
        </span>
      </div>

      {/* MARKER_143.P6G: Dynamic role list — click to expand RoleEditor */}
      {roles.map(([role, model]) => {
        const isExpanded = expandedRole === role;
        const modelShort = model ? (model.split('/').pop()?.split(':')[0] || model) : '—';

        return (
          <div key={role}>
            {/* Compact role row */}
            <div
              onClick={() => setExpandedRole(isExpanded ? null : role)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 6px',
                cursor: 'pointer',
                borderRadius: 2,
                transition: 'background 0.1s',
                background: isExpanded ? 'rgba(255,255,255,0.06)' : 'transparent',
                borderLeft: isExpanded ? '2px solid #888' : '2px solid transparent',
              }}
              onMouseEnter={e => {
                if (!isExpanded) e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
              }}
              onMouseLeave={e => {
                if (!isExpanded) e.currentTarget.style.background = 'transparent';
              }}
            >
              <span style={{
                fontSize: 8, fontWeight: 700, color: isExpanded ? '#fff' : '#888',
                letterSpacing: 0.5, textTransform: 'uppercase',
                minWidth: 28,
              }}>{getRoleShort(role)}</span>
              <span style={{
                flex: 1, fontSize: 9, color: isExpanded ? '#fff' : '#ccc',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }} title={model}>
                {modelShort}
              </span>
              <span style={{ fontSize: 8, color: '#444' }}>{isExpanded ? '▾' : '▸'}</span>
            </div>

            {/* Expanded: full RoleEditor from DetailPanel */}
            {isExpanded && (
              <div style={{
                padding: '0 4px 8px 4px',
                borderLeft: '2px solid #333',
                marginLeft: 2,
              }}>
                <RoleEditor role={role} activePreset={activePreset} />
              </div>
            )}
          </div>
        );
      })}

      {/* MARKER_143.P6H: Add custom role */}
      {!addingRole ? (
        <div
          onClick={() => setAddingRole(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '4px 6px', cursor: 'pointer',
            color: '#555', fontSize: 9,
            marginTop: 4,
            borderRadius: 2,
          }}
          onMouseEnter={e => e.currentTarget.style.color = '#888'}
          onMouseLeave={e => e.currentTarget.style.color = '#555'}
        >
          <span style={{ fontSize: 10 }}>+</span>
          <span>add role</span>
        </div>
      ) : (
        <div style={{ marginTop: 6, padding: '6px', background: 'rgba(255,255,255,0.02)', borderRadius: 3 }}>
          <div style={{ fontSize: 8, color: '#555', textTransform: 'uppercase', marginBottom: 4, letterSpacing: 1 }}>
            new role
          </div>
          <div style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
            <input
              type="text"
              value={newRoleName}
              onChange={e => setNewRoleName(e.target.value)}
              placeholder="role name"
              style={{
                flex: 1,
                background: 'rgba(0,0,0,0.4)',
                border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                borderRadius: 2,
                padding: '3px 6px',
                color: '#fff', fontSize: 9, fontFamily: 'monospace',
                outline: 'none',
              }}
              onKeyDown={e => {
                if (e.key === 'Escape') { setAddingRole(false); setAddMsg(''); }
              }}
              autoFocus
            />
          </div>
          <div style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
            <input
              type="text"
              value={newRoleModel}
              onChange={e => setNewRoleModel(e.target.value)}
              placeholder="model id (e.g. qwen3-coder)"
              style={{
                flex: 1,
                background: 'rgba(0,0,0,0.4)',
                border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                borderRadius: 2,
                padding: '3px 6px',
                color: '#fff', fontSize: 9, fontFamily: 'monospace',
                outline: 'none',
              }}
              onKeyDown={e => {
                if (e.key === 'Enter') handleAddRole();
                if (e.key === 'Escape') { setAddingRole(false); setAddMsg(''); }
              }}
            />
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            <button
              onClick={handleAddRole}
              style={{
                flex: 1, padding: '3px 6px',
                background: 'rgba(255,255,255,0.05)',
                border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                borderRadius: 2,
                color: '#ccc', fontSize: 9, cursor: 'pointer',
                fontFamily: 'monospace',
              }}
            >
              add
            </button>
            <button
              onClick={() => { setAddingRole(false); setAddMsg(''); }}
              style={{
                padding: '3px 6px',
                background: 'transparent',
                border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                borderRadius: 2,
                color: '#666', fontSize: 9, cursor: 'pointer',
                fontFamily: 'monospace',
              }}
            >
              ✕
            </button>
          </div>
          {addMsg && (
            <div style={{
              fontSize: 8, marginTop: 3,
              color: addMsg.startsWith('error') ? '#a66' : '#a88',
            }}>
              {addMsg}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
