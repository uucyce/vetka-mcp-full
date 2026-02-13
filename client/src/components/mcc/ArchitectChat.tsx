/**
 * MARKER_144.12: ArchitectChat — conversational interface with the Architect agent.
 *
 * Embedded at the bottom of the MCC left column (below task list).
 * User sends messages → Architect responds with reasoning + optional DAG mutations.
 * Two modes:
 * 1. Autonomous: user creates task at top, Architect decomposes + executes
 * 2. Collaborative: user chats here, iterates on plan, Architect proposes changes
 *
 * The Architect sees current DAG state + chat history as context.
 * When Architect proposes DAG changes, they appear as pending suggestions
 * that user can accept/reject before applying.
 *
 * @phase 144
 * @status active
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { useMCCStore } from '../../store/useMCCStore';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

const API_BASE = 'http://localhost:5001';

interface ChatMessage {
  id: string;
  role: 'user' | 'architect';
  content: string;
  timestamp: number;
  // Optional DAG mutations proposed by architect
  dagChanges?: {
    addNodes?: Array<{ type: string; label: string }>;
    removeNodes?: string[];
    addEdges?: Array<{ source: string; target: string; type: string }>;
  };
  accepted?: boolean; // Whether proposed changes were accepted
}

interface ArchitectChatProps {
  /** Currently selected node ID in DAG — provides context for Architect */
  selectedNodeId?: string | null;
  /** Current workflow nodes for context */
  workflowContext?: { nodeCount: number; edgeCount: number };
  /** Callback when Architect proposes DAG changes user accepts */
  onAcceptChanges?: (changes: ChatMessage['dagChanges']) => void;
}

export function ArchitectChat({
  selectedNodeId,
  workflowContext,
  onAcceptChanges,
}: ArchitectChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activePreset = useMCCStore(s => s.activePreset);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = useCallback(async () => {
    const text = inputValue.trim();
    if (!text || isThinking) return;

    const userMsg: ChatMessage = {
      id: `msg_${Date.now()}_user`,
      role: 'user',
      content: text,
      timestamp: Date.now(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setIsThinking(true);

    try {
      // Call Architect via mycelium_call_model or direct API
      const resp = await fetch(`${API_BASE}/api/architect/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          context: {
            selectedNodeId,
            workflowContext,
            preset: activePreset,
            chatHistory: messages.slice(-6).map(m => ({
              role: m.role,
              content: m.content,
            })),
          },
        }),
      });

      if (resp.ok) {
        const data = await resp.json();
        const architectMsg: ChatMessage = {
          id: `msg_${Date.now()}_arch`,
          role: 'architect',
          content: data.response || data.message || 'No response from Architect.',
          timestamp: Date.now(),
          dagChanges: data.dag_changes || undefined,
        };
        setMessages(prev => [...prev, architectMsg]);
      } else {
        // Fallback: try pipeline endpoint
        const fallbackResp = await fetch(`${API_BASE}/api/pipeline/quick-ask`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question: text,
            preset: activePreset,
            role: 'architect',
          }),
        });

        if (fallbackResp.ok) {
          const data = await fallbackResp.json();
          const architectMsg: ChatMessage = {
            id: `msg_${Date.now()}_arch`,
            role: 'architect',
            content: data.response || data.answer || 'Architect is thinking...',
            timestamp: Date.now(),
          };
          setMessages(prev => [...prev, architectMsg]);
        } else {
          // Last fallback: show error
          setMessages(prev => [...prev, {
            id: `msg_${Date.now()}_err`,
            role: 'architect',
            content: `[Architect API not available. Create a task above and use @dragon to dispatch.]`,
            timestamp: Date.now(),
          }]);
        }
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        id: `msg_${Date.now()}_err`,
        role: 'architect',
        content: `[Connection error. The Architect endpoint may not be running yet.]`,
        timestamp: Date.now(),
      }]);
    } finally {
      setIsThinking(false);
    }
  }, [inputValue, isThinking, messages, selectedNodeId, workflowContext, activePreset]);

  const handleAcceptChanges = useCallback((msg: ChatMessage) => {
    if (msg.dagChanges && onAcceptChanges) {
      onAcceptChanges(msg.dagChanges);
      setMessages(prev => prev.map(m =>
        m.id === msg.id ? { ...m, accepted: true } : m
      ));
    }
  }, [onAcceptChanges]);

  // Collapsed mode — just shows input
  if (!expanded) {
    return (
      <div style={{
        borderTop: `1px solid ${NOLAN_PALETTE.borderDim}`,
        padding: '4px 8px',
        background: '#0a0a0a',
      }}>
        <div
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            cursor: 'pointer', padding: '3px 0',
          }}
          onClick={() => setExpanded(true)}
        >
          <span style={{ fontSize: 8, color: '#555', textTransform: 'uppercase', letterSpacing: 1 }}>
            architect
          </span>
          <span style={{ flex: 1, fontSize: 8, color: '#444' }}>
            {messages.length > 0 ? `${messages.length} messages` : 'click to chat'}
          </span>
          <span style={{ fontSize: 9, color: '#555' }}>▲</span>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      borderTop: `1px solid ${NOLAN_PALETTE.borderDim}`,
      display: 'flex',
      flexDirection: 'column',
      background: '#0a0a0a',
      maxHeight: 280,
      minHeight: 120,
    }}>
      {/* Header */}
      <div
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '4px 8px',
          borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
          cursor: 'pointer',
        }}
        onClick={() => setExpanded(false)}
      >
        <span style={{ fontSize: 8, color: '#888', textTransform: 'uppercase', letterSpacing: 1 }}>
          architect chat
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {selectedNodeId && (
            <span style={{ fontSize: 7, color: '#555' }}>
              ctx: {selectedNodeId.slice(0, 10)}
            </span>
          )}
          <span style={{ fontSize: 9, color: '#555' }}>▼</span>
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        minHeight: 0,
        padding: '4px 0',
      }}>
        {messages.length === 0 && (
          <div style={{ padding: '12px 8px', color: '#444', fontSize: 8, textAlign: 'center', lineHeight: 1.6 }}>
            Chat with the Architect agent.
            <br />
            Describe your task — Architect will plan subtasks.
            <br />
            <span style={{ color: '#555' }}>Shift+Enter to send</span>
          </div>
        )}

        {messages.map(msg => (
          <div key={msg.id} style={{
            padding: '4px 8px',
            borderBottom: `1px solid rgba(255,255,255,0.02)`,
          }}>
            {/* Role + time */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
              <span style={{
                fontSize: 7,
                color: msg.role === 'user' ? '#888' : '#a9a',
                textTransform: 'uppercase',
                fontWeight: 600,
                letterSpacing: '0.5px',
              }}>
                {msg.role === 'user' ? 'you' : 'architect'}
              </span>
              <span style={{ fontSize: 7, color: '#333' }}>
                {new Date(msg.timestamp).toLocaleTimeString()}
              </span>
            </div>

            {/* Content */}
            <div style={{
              fontSize: 9,
              color: msg.role === 'user' ? '#ccc' : '#aaa',
              lineHeight: 1.5,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}>
              {msg.content}
            </div>

            {/* DAG changes proposal */}
            {msg.dagChanges && (
              <div style={{
                marginTop: 4,
                padding: '4px 6px',
                background: 'rgba(255,255,255,0.02)',
                border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                borderRadius: 2,
              }}>
                <div style={{ fontSize: 7, color: '#888', textTransform: 'uppercase', marginBottom: 3 }}>
                  proposed changes
                </div>
                {msg.dagChanges.addNodes && msg.dagChanges.addNodes.length > 0 && (
                  <div style={{ fontSize: 8, color: '#8a8' }}>
                    + {msg.dagChanges.addNodes.length} node(s): {msg.dagChanges.addNodes.map(n => n.label).join(', ')}
                  </div>
                )}
                {msg.dagChanges.removeNodes && msg.dagChanges.removeNodes.length > 0 && (
                  <div style={{ fontSize: 8, color: '#a66' }}>
                    − {msg.dagChanges.removeNodes.length} node(s)
                  </div>
                )}
                {msg.dagChanges.addEdges && msg.dagChanges.addEdges.length > 0 && (
                  <div style={{ fontSize: 8, color: '#aaa' }}>
                    + {msg.dagChanges.addEdges.length} edge(s)
                  </div>
                )}
                {!msg.accepted ? (
                  <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                    <button
                      onClick={() => handleAcceptChanges(msg)}
                      style={{
                        background: 'rgba(100,160,100,0.1)',
                        border: '1px solid rgba(100,160,100,0.3)',
                        borderRadius: 2,
                        color: '#8a8',
                        fontSize: 8,
                        padding: '2px 8px',
                        cursor: 'pointer',
                        fontFamily: 'monospace',
                      }}
                    >accept</button>
                    <button
                      onClick={() => setMessages(prev => prev.map(m =>
                        m.id === msg.id ? { ...m, accepted: false, dagChanges: undefined } : m
                      ))}
                      style={{
                        background: 'transparent',
                        border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                        borderRadius: 2,
                        color: '#666',
                        fontSize: 8,
                        padding: '2px 8px',
                        cursor: 'pointer',
                        fontFamily: 'monospace',
                      }}
                    >reject</button>
                  </div>
                ) : (
                  <div style={{ fontSize: 8, color: '#8a8', marginTop: 3 }}>✓ applied</div>
                )}
              </div>
            )}
          </div>
        ))}

        {isThinking && (
          <div style={{ padding: '4px 8px', fontSize: 8, color: '#666' }}>
            <span style={{
              display: 'inline-block', width: 4, height: 4,
              borderRadius: '50%', background: '#888', marginRight: 4,
              animation: 'archChatPulse 1.2s infinite',
            }} />
            Architect is thinking...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '4px 8px 6px',
        borderTop: `1px solid ${NOLAN_PALETTE.borderDim}`,
      }}>
        <div style={{ display: 'flex', gap: 3 }}>
          <textarea
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            placeholder="Ask the Architect..."
            rows={2}
            style={{
              flex: 1,
              background: 'rgba(255,255,255,0.03)',
              border: `1px solid ${NOLAN_PALETTE.borderDim}`,
              borderRadius: 2,
              color: '#ccc',
              padding: '4px 6px',
              fontSize: 9,
              fontFamily: 'monospace',
              outline: 'none',
              resize: 'none',
              minWidth: 0,
            }}
          />
          <button
            onClick={sendMessage}
            disabled={!inputValue.trim() || isThinking}
            style={{
              background: inputValue.trim() && !isThinking ? 'rgba(255,255,255,0.06)' : 'transparent',
              color: inputValue.trim() && !isThinking ? '#ccc' : '#333',
              border: `1px solid ${NOLAN_PALETTE.borderDim}`,
              borderRadius: 2,
              padding: '4px 8px',
              fontSize: 9,
              cursor: inputValue.trim() && !isThinking ? 'pointer' : 'not-allowed',
              fontFamily: 'monospace',
              alignSelf: 'flex-end',
            }}
            title="Send (Shift+Enter)"
          >→</button>
        </div>
      </div>

      <style>{`@keyframes archChatPulse { 0%,100%{opacity:1} 50%{opacity:0.3} }`}</style>
    </div>
  );
}
