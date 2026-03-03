/**
 * MARKER_154.12A: MiniChat — compact chat overlay in DAG canvas.
 *
 * Compact: single input line + last response.
 * Expanded: full ArchitectChat with history.
 * Position: top-left.
 *
 * @phase 154
 * @wave 4
 * @status active
 */

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { MiniWindow } from './MiniWindow';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import type { MiniContextPayload } from './MiniContext';
import { useMCCStore } from '../../store/useMCCStore';

const API_BASE = 'http://localhost:5001/api';

interface MiniChatProps {
  context?: MiniContextPayload;
}

function useChatModelLabel(context?: MiniContextPayload): string {
  const activePreset = useMCCStore((s) => s.activePreset || 'dragon_silver');
  const presets = useMCCStore((s) => s.presets);
  const fetchPresets = useMCCStore((s) => s.fetchPresets);

  useEffect(() => {
    fetchPresets();
  }, [fetchPresets]);

  const presetRoles = ((presets?.[activePreset] as any)?.roles || {}) as Record<string, string>;
  const architectPresetModel = String(presetRoles?.architect || '');
  const roleKey = context?.role ? String(context.role).toLowerCase() : '';
  const effectiveRoleKey = roleKey === 'eval' ? 'verifier' : roleKey;
  const rolePresetModel = effectiveRoleKey ? String(presetRoles?.[effectiveRoleKey] || '') : '';

  if (!context || context.scope === 'project') {
    return architectPresetModel || 'from preset';
  }
  if (context.model) return context.model;
  if (context.nodeKind === 'agent' && rolePresetModel) return rolePresetModel;
  return 'from preset';
}

function openContextModelChooser() {
  window.dispatchEvent(new CustomEvent('mcc-miniwindow-open', {
    detail: { windowId: 'context', expanded: true },
  }));
}

function resolveChatScope(context?: MiniContextPayload): { scope: 'project' | 'task' | 'agent' | 'node'; label: string } {
  if (!context || context.scope === 'project') {
    return { scope: 'project', label: 'Project architect' };
  }
  if (context.nodeKind === 'task') {
    return { scope: 'task', label: `Task architect: ${context.label}` };
  }
  if (context.nodeKind === 'agent') {
    return { scope: 'agent', label: `Agent context: ${context.role || context.label}` };
  }
  return { scope: 'node', label: `Node context: ${context.label}` };
}

// Compact content: one-line input + last answer
function ChatCompact({ context }: MiniChatProps) {
  const [input, setInput] = useState('');
  const [lastAnswer, setLastAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const scope = useMemo(() => resolveChatScope(context), [context]);
  const modelLabel = useChatModelLabel(context);

  useEffect(() => {
    const handlePrefill = (event: Event) => {
      const detail = (event as CustomEvent).detail || {};
      const message = String(detail.message || '').trim();
      if (!message) return;
      setInput(message);
      requestAnimationFrame(() => inputRef.current?.focus());
    };
    window.addEventListener('mcc-chat-prefill', handlePrefill as EventListener);
    return () => window.removeEventListener('mcc-chat-prefill', handlePrefill as EventListener);
  }, []);

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;
    const message = input.trim();
    setInput('');
    setLoading(true);
    setLastAnswer(null);

    try {
      const res = await fetch(`${API_BASE}/chat/quick`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          role: 'architect',
          context: {
            chat_scope: scope.scope,
            nav_level: context?.navLevel,
            focus_scope_key: context?.focusScopeKey,
            node_id: context?.nodeId,
            node_kind: context?.nodeKind,
            task_id: context?.taskId,
            role: context?.role,
            selected_node_ids: context?.selectedNodeIds || [],
          },
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setLastAnswer(data.response || data.message || '(no response)');
    } catch (err) {
      setLastAnswer('⚠ Failed to get response');
    } finally {
      setLoading(false);
    }
  }, [input, loading]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      e.stopPropagation();
      handleSend();
    }
  }, [handleSend]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 4 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6 }}>
        <div
          style={{
            color: '#7f8893',
            fontSize: 8,
            textTransform: 'uppercase',
            letterSpacing: 0.35,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
          title={scope.label}
        >
          {scope.label}
        </div>
        <button
          type="button"
          onClick={openContextModelChooser}
          style={{
            border: `1px solid ${NOLAN_PALETTE.borderDim}`,
            background: 'transparent',
            color: '#9aa4af',
            borderRadius: 4,
            fontSize: 8,
            padding: '1px 5px',
            cursor: 'pointer',
            fontFamily: 'monospace',
            maxWidth: 110,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
          title={`Model: ${modelLabel}. Click to open Context model chooser.`}
        >
          {modelLabel}
        </button>
      </div>
      {/* Last answer */}
      <div
        style={{
          flex: 1,
          overflow: 'hidden',
          color: lastAnswer ? NOLAN_PALETTE.textMuted : '#333',
          fontSize: 9,
          lineHeight: 1.4,
        }}
      >
        {loading ? (
          <span style={{ color: '#555' }}>thinking...</span>
        ) : lastAnswer ? (
          lastAnswer.slice(0, 200)
        ) : (
          'Ask the architect anything...'
        )}
      </div>

      {/* Input */}
      <div style={{ display: 'flex', gap: 4 }}>
        <input
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask..."
          style={{
            flex: 1,
            background: NOLAN_PALETTE.bg,
            border: `1px solid ${NOLAN_PALETTE.border}`,
            borderRadius: 3,
            color: NOLAN_PALETTE.text,
            fontFamily: 'monospace',
            fontSize: 9,
            padding: '3px 6px',
            outline: 'none',
          }}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || loading}
          style={{
            background: NOLAN_PALETTE.bg,
            border: `1px solid ${NOLAN_PALETTE.border}`,
            borderRadius: 3,
            color: input.trim() ? NOLAN_PALETTE.text : '#444',
            fontSize: 9,
            cursor: input.trim() ? 'pointer' : 'default',
            padding: '2px 6px',
            fontFamily: 'monospace',
          }}
        >
          →
        </button>
      </div>
    </div>
  );
}

// Expanded content: placeholder for full ArchitectChat
// In future, this imports and wraps ArchitectChat component with mode='expanded'
function ChatExpanded({ context }: MiniChatProps) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const scope = useMemo(() => resolveChatScope(context), [context]);
  const modelLabel = useChatModelLabel(context);

  useEffect(() => {
    const handlePrefill = (event: Event) => {
      const detail = (event as CustomEvent).detail || {};
      const message = String(detail.message || '').trim();
      if (!message) return;
      setInput(message);
      requestAnimationFrame(() => inputRef.current?.focus());
    };
    window.addEventListener('mcc-chat-prefill', handlePrefill as EventListener);
    return () => window.removeEventListener('mcc-chat-prefill', handlePrefill as EventListener);
  }, []);

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;
    const message = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: message }]);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat/quick`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          role: 'architect',
          context: {
            chat_scope: scope.scope,
            nav_level: context?.navLevel,
            focus_scope_key: context?.focusScopeKey,
            node_id: context?.nodeId,
            node_kind: context?.nodeKind,
            task_id: context?.taskId,
            role: context?.role,
            selected_node_ids: context?.selectedNodeIds || [],
          },
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.response || data.message || '' }]);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: '⚠ Error getting response' }]);
    } finally {
      setLoading(false);
    }
  }, [input, loading]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Messages */}
      <div style={{ flex: 1, overflow: 'auto', padding: '8px 12px' }}>
        <div
          style={{
            color: '#7f8893',
            fontSize: 8,
            textTransform: 'uppercase',
            letterSpacing: 0.35,
            marginBottom: 8,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 8,
          }}
        >
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{scope.label}</span>
          <button
            type="button"
            onClick={openContextModelChooser}
            style={{
              border: `1px solid ${NOLAN_PALETTE.borderDim}`,
              background: 'transparent',
              color: '#9aa4af',
              borderRadius: 4,
              fontSize: 8,
              padding: '1px 6px',
              cursor: 'pointer',
              fontFamily: 'monospace',
              maxWidth: 180,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
            title={`Model: ${modelLabel}. Click to open Context model chooser.`}
          >
            model: {modelLabel}
          </button>
        </div>
        {messages.length === 0 && (
          <div style={{ color: '#444', fontSize: 10, textAlign: 'center', marginTop: 40 }}>
            Ask the architect about your project...
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} style={{ marginBottom: 8 }}>
            <div style={{
              color: msg.role === 'user' ? NOLAN_PALETTE.textAccent : NOLAN_PALETTE.textMuted,
              fontSize: 8,
              textTransform: 'uppercase',
              marginBottom: 2,
            }}>
              {msg.role === 'user' ? 'YOU' : 'ARCHITECT'}
            </div>
            <div style={{
              color: NOLAN_PALETTE.text,
              fontSize: 11,
              lineHeight: 1.5,
              whiteSpace: 'pre-wrap',
            }}>
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ color: '#555', fontSize: 10 }}>thinking...</div>
        )}
      </div>

      {/* Input bar */}
      <div style={{
        display: 'flex',
        gap: 6,
        padding: '8px 12px',
        borderTop: `1px solid ${NOLAN_PALETTE.border}`,
      }}>
        <input
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              e.stopPropagation();
              handleSend();
            }
          }}
          placeholder="Type a message..."
          style={{
            flex: 1,
            background: NOLAN_PALETTE.bg,
            border: `1px solid ${NOLAN_PALETTE.border}`,
            borderRadius: 4,
            color: NOLAN_PALETTE.text,
            fontFamily: 'monospace',
            fontSize: 11,
            padding: '6px 10px',
            outline: 'none',
          }}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || loading}
          style={{
            padding: '4px 12px',
            background: input.trim() ? '#1a1a1a' : NOLAN_PALETTE.bg,
            border: `1px solid ${input.trim() ? NOLAN_PALETTE.text : NOLAN_PALETTE.border}`,
            borderRadius: 4,
            color: input.trim() ? NOLAN_PALETTE.text : '#555',
            fontSize: 11,
            cursor: input.trim() ? 'pointer' : 'default',
            fontFamily: 'monospace',
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}

export function MiniChat({ context }: MiniChatProps) {
  return (
    <MiniWindow
      windowId="chat" // MARKER_155.DRAGGABLE.011: Unique ID for position persistence
      title="Chat"
      icon="💬"
      position="bottom-left"
      compactWidth={210}
      compactHeight={130}
      compactContent={<ChatCompact context={context} />}
      expandedContent={<ChatExpanded context={context} />}
    />
  );
}
