/**
 * MentionPopup - Dropdown for @mention autocomplete in chat input.
 * Shows group participants in group mode, tracked models in solo mode.
 * Dynamically filters based on user input.
 *
 * @status active
 * @phase 96
 * @depends react, lucide-react, MENTION_ALIASES
 * @used_by MessageInput
 */

import {
  ClipboardList,
  Code,
  TestTube,
  Building,
  Brain,
  Terminal,
  Cpu,
  Sparkles,
  Star,
  Search,
  Users,
  Bot,
} from 'lucide-react';
import { MENTION_ALIASES } from '../../types/chat';

const ICONS: Record<string, React.ReactNode> = {
  ClipboardList: <ClipboardList size={14} />,
  Code: <Code size={14} />,
  TestTube: <TestTube size={14} />,
  Building: <Building size={14} />,
  Brain: <Brain size={14} />,
  Terminal: <Terminal size={14} />,
  Cpu: <Cpu size={14} />,
  Sparkles: <Sparkles size={14} />,
  Star: <Star size={14} />,
  Search: <Search size={14} />,
  Users: <Users size={14} />,
  Bot: <Bot size={14} />,
};

// Phase 80.22: Group participant type with model info
interface GroupParticipant {
  agent_id: string;
  display_name: string;  // Contains "Role (Model)" format from backend
  role?: string;
  model_id?: string;
}

interface Props {
  filter: string;
  onSelect: (alias: string) => void;
  // Phase 80.22: When in group mode, show dynamic participants from group
  groupParticipants?: GroupParticipant[];
  isGroupMode?: boolean;
  // Phase 80.30: For solo chat - show only models that were used in this chat
  soloModels?: string[];  // Array of model IDs used in current solo chat
  // TODO_CAM_UI: Add CAM-ranked model suggestions in mention popup
  cam_ranked_models?: Array<{ id: string; name: string; cam_score: number }>;  // From GET /api/cam/suggestions
}

export function MentionPopup({ filter, onSelect, groupParticipants, isGroupMode, soloModels }: Props) {
  // MARKER_94.7_MENTION_POPUP: @ mention popup component
  // Phase 80.22: Dynamic mention dropdown based on group mode

  // Phase 80.30: Solo chat mode with tracked models
  if (!isGroupMode && soloModels && soloModels.length > 0) {
    const filteredModels = soloModels.filter(model =>
      model.toLowerCase().includes(filter.toLowerCase())
    );

    if (filteredModels.length === 0) {
      return null;
    }

    return (
      <div style={{
        position: 'absolute',
        bottom: '100%',
        left: 12,
        right: 12,
        marginBottom: 8,
        background: '#1a1a1a',
        border: '1px solid #333',
        borderRadius: 8,
        overflow: 'hidden',
        boxShadow: '0 -4px 20px rgba(0,0,0,0.5)',
        maxHeight: 300,
        overflowY: 'auto',
      }}>
        <div style={{
          padding: '6px 12px',
          fontSize: 10,
          color: '#666',
          background: '#111',
          textTransform: 'uppercase',
          letterSpacing: 1,
        }}>
          Models in this chat
        </div>
        {filteredModels.map((model) => (
          <button
            key={model}
            onClick={() => onSelect(`@${model}`)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '10px 12px',
              background: 'transparent',
              border: 'none',
              borderBottom: '1px solid #222',
              cursor: 'pointer',
              textAlign: 'left',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#222')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          >
            <span style={{ color: '#8a8a8a' }}>{ICONS.Bot}</span>
            <div>
              <div style={{ color: '#e0e0e0', fontSize: 13 }}>@{model.split('/').pop()}</div>
              <div style={{ color: '#666', fontSize: 11 }}>{model}</div>
            </div>
          </button>
        ))}
      </div>
    );
  }

  // In group mode with participants - show ONLY dynamic participants
  if (isGroupMode && groupParticipants && groupParticipants.length > 0) {
    // Build dynamic entries from group participants
    const dynamicParticipants = groupParticipants
      .filter(p => {
        // Filter by search text
        const alias = p.agent_id.replace('@', '').toLowerCase();
        const displayName = p.display_name?.toLowerCase() || '';
        return alias.includes(filter.toLowerCase()) || displayName.includes(filter.toLowerCase());
      })
      .map(p => ({
        alias: p.agent_id, // e.g., "@PM"
        label: p.display_name || p.agent_id, // e.g., "PM (GPT-4o)"
        role: p.role,
      }));

    // Always include Hostess in group mode (if matches filter)
    const showHostess = 'hostess'.includes(filter.toLowerCase());

    if (dynamicParticipants.length === 0 && !showHostess) {
      return null;
    }

    return (
      <div style={{
        position: 'absolute',
        bottom: '100%',
        left: 12,
        right: 12,
        marginBottom: 8,
        background: '#1a1a1a',
        border: '1px solid #333',
        borderRadius: 8,
        overflow: 'hidden',
        boxShadow: '0 -4px 20px rgba(0,0,0,0.5)',
        maxHeight: 300,
        overflowY: 'auto',
      }}>
        <div style={{
          padding: '6px 12px',
          fontSize: 10,
          color: '#666',
          background: '#111',
          textTransform: 'uppercase',
          letterSpacing: 1,
        }}>
          Group Members
        </div>
        {/* Phase 80.22: Dynamic participants from group */}
        {dynamicParticipants.map(({ alias, label }) => (
          <button
            key={alias}
            onClick={() => onSelect(alias)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '10px 12px',
              background: 'transparent',
              border: 'none',
              borderBottom: '1px solid #222',
              cursor: 'pointer',
              textAlign: 'left',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#222')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          >
            <span style={{ color: '#8a8a8a' }}>{ICONS.Bot}</span>
            <div>
              <div style={{ color: '#e0e0e0', fontSize: 13 }}>{alias}</div>
              <div style={{ color: '#666', fontSize: 11 }}>{label}</div>
            </div>
          </button>
        ))}
        {/* Hostess - always available in group mode */}
        {showHostess && (
          <button
            key="@hostess"
            onClick={() => onSelect('@hostess')}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '10px 12px',
              background: 'transparent',
              border: 'none',
              borderBottom: '1px solid #222',
              cursor: 'pointer',
              textAlign: 'left',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#222')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          >
            <span style={{ color: '#8a8a8a' }}>{ICONS.Users}</span>
            <div>
              <div style={{ color: '#e0e0e0', fontSize: 13 }}>@hostess</div>
              <div style={{ color: '#666', fontSize: 11 }}>Hostess (Orchestrator)</div>
            </div>
          </button>
        )}
      </div>
    );
  }

  // Phase 80.33: Empty solo chat - show invitation to add model
  // No hardcoded fallback - only show models that are actually in the chat
  return (
    <div style={{
      position: 'absolute',
      bottom: '100%',
      left: 12,
      right: 12,
      marginBottom: 8,
      background: '#1a1a1a',
      border: '1px solid #333',
      borderRadius: 8,
      overflow: 'hidden',
      boxShadow: '0 -4px 20px rgba(0,0,0,0.5)',
      padding: '16px 12px',
      textAlign: 'center',
    }}>
      <div style={{ color: '#666', fontSize: 12, marginBottom: 8 }}>
        {ICONS.Bot}
      </div>
      <div style={{ color: '#888', fontSize: 13, marginBottom: 4 }}>
        No models in this chat yet
      </div>
      <div style={{ color: '#555', fontSize: 11 }}>
        Select a model from the sidebar to start chatting
      </div>
    </div>
  );
}
