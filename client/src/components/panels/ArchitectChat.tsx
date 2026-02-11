/**
 * MARKER_136.W2B: ArchitectChat — Direct Architect agent interaction.
 * Replaces LeagueTester (TEST tab) with a chat interface for planning.
 * Users can ask Architect to plan tasks and see decomposition.
 * Style: Nolan monochrome.
 *
 * @status active
 * @phase 136
 * @depends react
 * @used_by DevPanel
 */

import { useState, useCallback, useRef, useEffect } from 'react';

const API_BASE = 'http://localhost:5001/api/debug';

// Nolan palette
const COLORS = {
  bg: '#111',
  bgLight: '#1a1a1a',
  border: '#222',
  borderLight: '#333',
  text: '#e0e0e0',
  textMuted: '#888',
  textDim: '#666',
  accent: '#555',
};

interface ArchitectMessage {
  role: 'user' | 'architect';
  content: string;
  timestamp: number;
  subtasks?: string[];
}

interface ModelOption {
  id: string;
  name: string;
  provider?: string;
  source?: string;
  source_display?: string;
  type?: string;
}

interface ArchitectChatProps {
  onPlanCreated?: (plan: string) => void;
}

export function ArchitectChat({ onPlanCreated }: ArchitectChatProps) {
  const [messages, setMessages] = useState<ArchitectMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [model, setModel] = useState('kimi-k2.5');  // Default architect model
  // MARKER_139.MCC_ARCHITECT_MODELS: Dynamic model inventory for Architect chat
  const [modelOptions, setModelOptions] = useState<ModelOption[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // MARKER_139.MCC_ARCHITECT_MODELS: Load actual models and prioritize Polza
  useEffect(() => {
    let mounted = true;
    const loadModels = async () => {
      setModelsLoading(true);
      try {
        const res = await fetch('/api/models/autodetect');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const all = (data.models || []) as ModelOption[];

        const textModels = all.filter((m) => {
          const type = (m.type || '').toLowerCase();
          return type !== 'voice' && type !== 'stt' && type !== 'tts';
        });

        const polza = textModels.filter((m) =>
          String(m.source || '').toLowerCase() === 'polza' ||
          String(m.provider || '').toLowerCase() === 'polza' ||
          String(m.source_display || '').toLowerCase() === 'polza'
        );

        const selected = polza.length > 0 ? polza : textModels;
        const unique = selected.filter((m, i, arr) =>
          !!m.id && arr.findIndex((x) => x.id === m.id) === i
        );

        if (!mounted) return;
        setModelOptions(unique);

        if (unique.length > 0 && !unique.some((m) => m.id === model)) {
          setModel(unique[0].id);
        }
      } catch {
        if (!mounted) return;
        // keep fallback static model list below
        setModelOptions([]);
      } finally {
        if (mounted) setModelsLoading(false);
      }
    };

    loadModels();
    return () => { mounted = false; };
  }, []);

  // MARKER_137.ARCHITECT_FIX: Improved error handling + timeout
  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;

    const userMessage: ArchitectMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    // AbortController for 60s timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);

    try {
      // Call Architect via LLM endpoint
      const res = await fetch(`${API_BASE}/llm-call`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model,
          messages: [
            {
              role: 'system',
              content: `You are the Architect agent in the VETKA pipeline.
Your job is to break down tasks into clear, actionable subtasks.

When given a task:
1. Analyze what needs to be done
2. Break it into 3-7 subtasks
3. For each subtask, indicate if it needs_research (unclear parts)
4. Be specific and actionable

Output format:
## Plan: [task summary]

### Subtasks:
1. [subtask description] ${'{'}needs_research: true/false{'}'}
2. ...

### Notes:
- Any architectural decisions or considerations`
            },
            {
              role: 'user',
              content: input.trim(),
            },
          ],
          max_tokens: 2000,
          temperature: 0.3,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();

      if (data.success && data.response) {
        // Parse subtasks from response
        const subtasks: string[] = [];
        const lines = data.response.split('\n');
        for (const line of lines) {
          const match = line.match(/^\d+\.\s+(.+)/);
          if (match) {
            subtasks.push(match[1].replace(/\{needs_research.*\}/, '').trim());
          }
        }

        const architectMessage: ArchitectMessage = {
          role: 'architect',
          content: data.response,
          timestamp: Date.now(),
          subtasks: subtasks.length > 0 ? subtasks : undefined,
        };

        setMessages(prev => [...prev, architectMessage]);
        onPlanCreated?.(data.response);
      } else {
        // Show detailed error from backend
        const errorMsg = data.error || 'Unknown error from LLM';
        setMessages(prev => [...prev, {
          role: 'architect',
          content: `Error: ${errorMsg}\n\nModel: ${model}\nTip: Check if model is available via Polza/provider.`,
          timestamp: Date.now(),
        }]);
      }
    } catch (err) {
      clearTimeout(timeoutId);
      // Detailed error messages
      let errorMsg = 'Failed to connect';
      if (err instanceof Error) {
        if (err.name === 'AbortError') {
          errorMsg = 'Request timeout (60s) — LLM may be unavailable';
        } else {
          errorMsg = err.message;
        }
      }
      setMessages(prev => [...prev, {
        role: 'architect',
        content: `Error: ${errorMsg}\n\nModel: ${model}`,
        timestamp: Date.now(),
      }]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, model, onPlanCreated]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      fontFamily: 'monospace',
      fontSize: 11,
      color: COLORS.text,
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 0',
        borderBottom: `1px solid ${COLORS.border}`,
        marginBottom: 8,
      }}>
        <div style={{
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: 1.5,
          textTransform: 'uppercase',
          color: COLORS.text,
        }}>
          architect planning
        </div>
        {loading && (
          <span style={{ fontSize: 9, color: COLORS.textMuted, marginRight: 6 }}>
            thinking...
          </span>
        )}
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          style={{
            background: COLORS.bgLight,
            border: `1px solid ${COLORS.border}`,
            borderRadius: 2,
            color: COLORS.textMuted,
            fontSize: 9,
            padding: '2px 6px',
            fontFamily: 'monospace',
          }}
        >
          {modelsLoading && <option value={model}>loading models...</option>}
          {!modelsLoading && modelOptions.length > 0 && modelOptions.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name || m.id} {(m.source_display || m.provider) ? `(${m.source_display || m.provider})` : ''}
            </option>
          ))}
          {!modelsLoading && modelOptions.length === 0 && (
            <>
              <option value="kimi-k2.5">Kimi K2.5</option>
              <option value="gpt-4o">GPT-4o</option>
              <option value="claude-3-5-sonnet-20241022">Sonnet</option>
              <option value="qwen3-235b">Qwen 235B</option>
            </>
          )}
        </select>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        overflowX: 'hidden',
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}>
        {messages.length === 0 && (
          <div style={{
            textAlign: 'center',
            color: COLORS.textDim,
            padding: 32,
            fontSize: 10,
          }}>
            describe a task for the architect to plan
          </div>
        )}

        {loading && (
          <div style={{
            color: COLORS.textMuted,
            fontSize: 10,
            padding: '4px 8px',
            border: `1px solid ${COLORS.border}`,
            borderRadius: 3,
            background: 'rgba(255,255,255,0.02)',
          }}>
            model {model} is generating plan...
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} style={{
            padding: '8px 10px',
            background: msg.role === 'user' ? 'transparent' : 'rgba(255,255,255,0.02)',
            borderRadius: 4,
            border: `1px solid ${msg.role === 'user' ? COLORS.border : COLORS.borderLight}`,
          }}>
            {/* Role badge */}
            <div style={{
              fontSize: 8,
              color: msg.role === 'user' ? COLORS.textMuted : COLORS.accent,
              marginBottom: 4,
              textTransform: 'uppercase',
              letterSpacing: 1,
            }}>
              {msg.role === 'user' ? 'you' : 'architect'}
            </div>

            {/* Content */}
            <div style={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              lineHeight: 1.5,
              color: msg.role === 'user' ? COLORS.textMuted : COLORS.text,
              fontSize: 10,
            }}>
              {msg.content}
            </div>

            {/* Subtasks quick view */}
            {msg.subtasks && msg.subtasks.length > 0 && (
              <div style={{
                marginTop: 8,
                paddingTop: 8,
                borderTop: `1px solid ${COLORS.border}`,
              }}>
                <div style={{ fontSize: 8, color: COLORS.textDim, marginBottom: 4 }}>
                  SUBTASKS ({msg.subtasks.length})
                </div>
                {msg.subtasks.map((sub, i) => (
                  <div key={i} style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 6,
                    padding: '2px 0',
                    fontSize: 9,
                    color: COLORS.textMuted,
                  }}>
                    <span style={{ color: COLORS.textDim }}>{i + 1}.</span>
                    <span>{sub}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{
        display: 'flex',
        gap: 6,
        paddingTop: 10,
        borderTop: `1px solid ${COLORS.border}`,
      }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="describe task to plan..."
          disabled={loading}
          style={{
            flex: 1,
            background: COLORS.bgLight,
            border: `1px solid ${COLORS.border}`,
            borderRadius: 3,
            color: COLORS.text,
            padding: '8px 10px',
            fontSize: 11,
            fontFamily: 'monospace',
            resize: 'none',
            minHeight: 40,
            maxHeight: 80,
            outline: 'none',
          }}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          style={{
            padding: '8px 16px',
            background: loading || !input.trim() ? 'transparent' : 'rgba(255,255,255,0.05)',
            border: `1px solid ${loading || !input.trim() ? COLORS.border : COLORS.borderLight}`,
            borderRadius: 3,
            color: loading || !input.trim() ? COLORS.textDim : COLORS.text,
            fontSize: 10,
            fontFamily: 'monospace',
            cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
            fontWeight: 500,
          }}
        >
          {loading ? '...' : 'plan'}
        </button>
      </div>
    </div>
  );
}
