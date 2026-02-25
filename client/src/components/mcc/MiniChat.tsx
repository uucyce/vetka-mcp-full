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

import { useState, useCallback, useRef, useEffect } from 'react';
import { MiniWindow } from './MiniWindow';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

const API_BASE = 'http://localhost:5001/api';

// Compact content: one-line input + last answer
function ChatCompact() {
  const [input, setInput] = useState('');
  const [lastAnswer, setLastAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

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
        body: JSON.stringify({ message, role: 'architect' }),
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
function ChatExpanded() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

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
        body: JSON.stringify({ message, role: 'architect' }),
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

export function MiniChat() {
  return (
    <MiniWindow
      windowId="chat" // MARKER_155.DRAGGABLE.011: Unique ID for position persistence
      title="Chat"
      icon="💬"
      position="top-left"
      compactWidth={210}
      compactHeight={130}
      compactContent={<ChatCompact />}
      expandedContent={<ChatExpanded />}
    />
  );
}
