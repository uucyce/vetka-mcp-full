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
import type { MycoHelperMode } from '../../store/useMCCStore';
import mycoIdleQuestion from '../../assets/myco/myco_idle_question.png';
import mycoReadySmile from '../../assets/myco/myco_ready_smile.png';
import mycoSpeakingLoop from '../../assets/myco/myco_speaking_loop.apng';

const API_BASE = 'http://localhost:5001/api';

interface MiniChatProps {
  context?: MiniContextPayload;
}

const MYCO_MODE_ORDER: MycoHelperMode[] = ['off', 'passive'];

function nextMycoMode(mode: MycoHelperMode): MycoHelperMode {
  const idx = MYCO_MODE_ORDER.indexOf(mode);
  if (idx < 0) return 'off';
  return MYCO_MODE_ORDER[(idx + 1) % MYCO_MODE_ORDER.length];
}

type MycoAvatarVisualState = 'idle' | 'speaking' | 'ready';

function isMycoTrigger(message: string): boolean {
  const m = String(message || '').trim().toLowerCase();
  return m.startsWith('/myco') || m.startsWith('/help myco') || m === '?';
}

function emitMycoReplyEvent() {
  window.dispatchEvent(new CustomEvent('mcc-myco-reply', {
    detail: { ts: Date.now() },
  }));
}

function buildMycoReply(context?: MiniContextPayload): string {
  const level = String(context?.navLevel || 'roadmap');
  const kind = String(context?.nodeKind || 'project');
  const label = String(context?.label || 'project');
  const role = String(context?.role || '');
  const scopeLine = `you are in ${level} view`;
  if (!context || context.scope === 'project') {
    return `🍄\n- ${scopeLine}\n- this is project-level context\n- next: click a node and ask again`;
  }
  if (kind === 'task') {
    return `🍄\n- ${scopeLine}\n- selected task: ${label}\n- next: press Enter to drill into workflow`;
  }
  if (kind === 'agent') {
    return `🍄\n- ${scopeLine}\n- selected agent: ${role || label}\n- next: open Context to review model/prompt`;
  }
  if (kind === 'file' || kind === 'directory') {
    return `🍄\n- ${scopeLine}\n- selected code scope: ${label}\n- next: inspect Context and linked tasks`;
  }
  return `🍄\n- ${scopeLine}\n- selected node: ${label}\n- next: ask architect or open Context`;
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

function buildMycoHeaderHint(context?: MiniContextPayload): string {
  if (!context || context.scope === 'project') return 'project context linked';
  if (context.nodeKind === 'task') return `task ${String(context.taskId || context.label || '')} linked`;
  if (context.nodeKind === 'agent') return `${String(context.role || context.label || 'agent')} context`;
  return String(context.label || context.nodeId || 'node context');
}

// Compact content: one-line input + last answer
function ChatCompact({ context }: MiniChatProps) {
  const [input, setInput] = useState('');
  const [lastAnswer, setLastAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const scope = useMemo(() => resolveChatScope(context), [context]);
  const modelLabel = useChatModelLabel(context);
  const contextName = String(context?.label || context?.taskId || 'project');
  const mycoHeaderHint = useMemo(() => buildMycoHeaderHint(context), [context]);
  const helperMode = useMCCStore((s) => s.helperMode);
  const setHelperMode = useMCCStore((s) => s.setHelperMode);
  const [mycoAvatarState, setMycoAvatarState] = useState<MycoAvatarVisualState>('idle');
  const mycoAvatarTimersRef = useRef<number[]>([]);
  const mycoAvatarSrc = useMemo(() => {
    if (mycoAvatarState === 'speaking') return mycoSpeakingLoop;
    if (mycoAvatarState === 'ready') return mycoReadySmile;
    return mycoIdleQuestion;
  }, [mycoAvatarState]);

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

  useEffect(() => {
    const onActivate = (event: Event) => {
      const detail = (event as CustomEvent).detail || {};
      const force = Boolean(detail.force);
      // MARKER_162.P2.MYCO.TOP_ACTIVATE_RACE_GUARD.V1:
      // `force` allows deterministic first response on top->chat handoff.
      if (helperMode === 'off' && !force) return;
      emitMycoReplyEvent();
      setLastAnswer(buildMycoReply(context));
    };
    window.addEventListener('mcc-myco-activate', onActivate as EventListener);
    return () => window.removeEventListener('mcc-myco-activate', onActivate as EventListener);
  }, [context, helperMode]);

  useEffect(() => {
    const clearTimers = () => {
      mycoAvatarTimersRef.current.forEach((timerId) => window.clearTimeout(timerId));
      mycoAvatarTimersRef.current = [];
    };
    const onMycoReply = () => {
      clearTimers();
      setMycoAvatarState('speaking');
      const readyTimer = window.setTimeout(() => setMycoAvatarState('ready'), 1500);
      const idleTimer = window.setTimeout(() => setMycoAvatarState('idle'), 3900);
      mycoAvatarTimersRef.current = [readyTimer, idleTimer];
    };
    window.addEventListener('mcc-myco-reply', onMycoReply as EventListener);
    return () => {
      window.removeEventListener('mcc-myco-reply', onMycoReply as EventListener);
      clearTimers();
    };
  }, []);

  useEffect(() => {
    const onActivate = (event: Event) => {
      const detail = (event as CustomEvent).detail || {};
      const force = Boolean(detail.force);
      if (helperMode === 'off' && !force) return;
      emitMycoReplyEvent();
      setMessages(prev => [...prev, { role: 'helper_myco', content: buildMycoReply(context) }]);
    };
    window.addEventListener('mcc-myco-activate', onActivate as EventListener);
    return () => window.removeEventListener('mcc-myco-activate', onActivate as EventListener);
  }, [context, helperMode]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;
    const message = input.trim();
    setInput('');
    if (isMycoTrigger(message)) {
      if (helperMode === 'off') {
        setLastAnswer('🍄 helper is off. Toggle helper icon.');
        return;
      }
      emitMycoReplyEvent();
      setLastAnswer(buildMycoReply(context));
      return;
    }
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
  }, [context, helperMode, input, loading]);

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
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
          }}
          title={helperMode !== 'off' ? `MYCO context: ${contextName}` : scope.label}
        >
          {helperMode !== 'off' ? (
            <button
              type="button"
              // MARKER_162.P2.MYCO.CHAT_SINGLE_LEFT_ANCHOR.V1:
              // In chat mode keep one MYCO anchor on the left; remove duplicated right-side icon.
              onClick={() => setHelperMode(nextMycoMode(helperMode))}
              style={{
                border: 'none',
                background: 'transparent',
                padding: 0,
                margin: 0,
                color: '#b8c2cd',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                fontFamily: 'inherit',
                fontSize: 8,
              }}
              title="Disable helper and return MYCO to top bar"
            >
              <img
                src={mycoAvatarSrc}
                alt="Helper avatar"
                style={{ width: 24, height: 34, objectFit: 'contain' }}
              />
              <span style={{ textTransform: 'none', letterSpacing: 0, color: '#b8c2cd' }}>{mycoHeaderHint}</span>
            </button>
          ) : (
            scope.label
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {helperMode === 'off' && (
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
          )}
        </div>
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
          helperMode !== 'off'
            ? `Я MYCO. Помочь с "${contextName}"? Нажми два раза, чтобы раскрыть ноду, или дай задание команде.`
            : 'Ask the architect...'
        )}
      </div>

      {/* Input */}
      <div style={{ display: 'flex', gap: 4 }}>
        <input
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={helperMode !== 'off' ? 'Ask MYCO...' : 'Ask...'}
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
  const helperMode = useMCCStore((s) => s.helperMode);
  const setHelperMode = useMCCStore((s) => s.setHelperMode);
  const mycoHeaderHint = useMemo(() => buildMycoHeaderHint(context), [context]);
  const [mycoAvatarState, setMycoAvatarState] = useState<MycoAvatarVisualState>('idle');
  const mycoAvatarTimersRef = useRef<number[]>([]);
  const mycoAvatarSrc = useMemo(() => {
    if (mycoAvatarState === 'speaking') return mycoSpeakingLoop;
    if (mycoAvatarState === 'ready') return mycoReadySmile;
    return mycoIdleQuestion;
  }, [mycoAvatarState]);

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

  useEffect(() => {
    const clearTimers = () => {
      mycoAvatarTimersRef.current.forEach((timerId) => window.clearTimeout(timerId));
      mycoAvatarTimersRef.current = [];
    };
    const onMycoReply = () => {
      clearTimers();
      setMycoAvatarState('speaking');
      const readyTimer = window.setTimeout(() => setMycoAvatarState('ready'), 1500);
      const idleTimer = window.setTimeout(() => setMycoAvatarState('idle'), 3900);
      mycoAvatarTimersRef.current = [readyTimer, idleTimer];
    };
    window.addEventListener('mcc-myco-reply', onMycoReply as EventListener);
    return () => {
      window.removeEventListener('mcc-myco-reply', onMycoReply as EventListener);
      clearTimers();
    };
  }, []);

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;
    const message = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: message }]);
    if (isMycoTrigger(message)) {
      if (helperMode === 'off') {
        setMessages(prev => [...prev, { role: 'helper_myco', content: 'Helper is off. Toggle helper icon to passive/active.' }]);
        return;
      }
      emitMycoReplyEvent();
      setMessages(prev => [...prev, { role: 'helper_myco', content: buildMycoReply(context) }]);
      return;
    }
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
  }, [context, helperMode, input, loading]);

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
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {helperMode !== 'off' ? (
              <button
                type="button"
                onClick={() => setHelperMode(nextMycoMode(helperMode))}
                style={{
                  border: 'none',
                  background: 'transparent',
                  padding: 0,
                  margin: 0,
                  color: '#b8c2cd',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  fontFamily: 'inherit',
                  fontSize: 8,
                }}
                title="Disable helper and return MYCO to top bar"
              >
                <img
                  src={mycoAvatarSrc}
                  alt="Helper avatar"
                  style={{ width: 24, height: 34, objectFit: 'contain' }}
                />
                <span style={{ textTransform: 'none', letterSpacing: 0, color: '#b8c2cd' }}>{mycoHeaderHint}</span>
              </button>
            ) : scope.label}
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {helperMode === 'off' && (
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
            )}
          </div>
        </div>
        {messages.length === 0 && (
          <div style={{ color: '#444', fontSize: 10, textAlign: 'center', marginTop: 40 }}>
            {helperMode !== 'off'
              ? `Я MYCO. Помочь с "${String(context?.label || context?.taskId || 'project')}"?`
              : 'Ask the architect about your project...'}
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
              {msg.role === 'user' ? 'YOU' : msg.role === 'helper_myco' ? 'HELPER' : 'ARCHITECT'}
            </div>
            {msg.role === 'helper_myco' ? (
              <div
                // MARKER_162.P2.MYCO.CHAT_BUBBLE_TAIL.V1:
                // MYCO messages render as comic bubble with tail to emphasize speaker identity.
                style={{
                  position: 'relative',
                  display: 'inline-block',
                  maxWidth: '95%',
                  color: NOLAN_PALETTE.text,
                  fontSize: 11,
                  lineHeight: 1.5,
                  whiteSpace: 'pre-wrap',
                  background: '#0b0d11',
                  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  borderRadius: 10,
                  padding: '7px 9px',
                }}
              >
                <span
                  style={{
                    position: 'absolute',
                    left: -9,
                    top: 10,
                    width: 0,
                    height: 0,
                    borderTop: '7px solid transparent',
                    borderBottom: '7px solid transparent',
                    borderRight: `9px solid ${NOLAN_PALETTE.borderDim}`,
                  }}
                />
                <span
                  style={{
                    position: 'absolute',
                    left: -7,
                    top: 11,
                    width: 0,
                    height: 0,
                    borderTop: '6px solid transparent',
                    borderBottom: '6px solid transparent',
                    borderRight: '8px solid #0b0d11',
                  }}
                />
                {msg.content}
              </div>
            ) : (
              <div style={{
                color: NOLAN_PALETTE.text,
                fontSize: 11,
                lineHeight: 1.5,
                whiteSpace: 'pre-wrap',
              }}>
                {msg.content}
              </div>
            )}
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
