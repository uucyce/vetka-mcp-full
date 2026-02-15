/**
 * MARKER_151.8: ArchitectChat panel with compact/expanded zoom modes.
 * State for messages + model is shared through Zustand store.
 */

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { useDevPanelStore } from '../../store/useDevPanelStore';
import { useArchitectStore, type ArchitectMessage } from '../../store/useArchitectStore';

const API_BASE = 'http://localhost:5001/api/debug';

const COLORS = {
  bgLight: '#1a1a1a',
  border: '#222',
  borderLight: '#333',
  text: '#e0e0e0',
  textMuted: '#888',
  textDim: '#666',
  accent: '#555',
};

interface ModelOption {
  id: string;
  name: string;
  provider?: string;
  source?: string;
  source_display?: string;
  type?: string;
}

interface ArchitectChatProps {
  mode?: 'compact' | 'expanded';
  onPlanCreated?: (plan: string) => void;
}

export function ArchitectChat({ mode = 'expanded', onPlanCreated }: ArchitectChatProps) {
  const setActiveTab = useDevPanelStore(s => s.setActiveTab);

  const messages = useArchitectStore(s => s.messages);
  const model = useArchitectStore(s => s.selectedModel);
  const loading = useArchitectStore(s => s.isGenerating);
  const addMessage = useArchitectStore(s => s.addMessage);
  const setModel = useArchitectStore(s => s.setSelectedModel);
  const setLoading = useArchitectStore(s => s.setIsGenerating);

  const [input, setInput] = useState('');
  const [modelOptions, setModelOptions] = useState<ModelOption[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const visibleMessages = useMemo(
    () => (mode === 'compact' ? messages.slice(-5) : messages),
    [messages, mode]
  );

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [visibleMessages]);

  useEffect(() => {
    if (mode === 'compact') return;
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
        setModelOptions([]);
      } finally {
        if (mounted) setModelsLoading(false);
      }
    };
    loadModels();
    return () => {
      mounted = false;
    };
  }, [mode, model, setModel]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;

    const userMessage: ArchitectMessage = {
      id: `arch_${Date.now()}_user`,
      role: 'user',
      content: input.trim(),
      timestamp: Date.now(),
    };
    addMessage(userMessage);
    setInput('');
    setLoading(true);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);

    try {
      const selectedModel = modelOptions.find((m) => m.id === model);
      const modelSource = selectedModel?.source || selectedModel?.provider || selectedModel?.source_display || '';

      const res = await fetch(`${API_BASE}/llm-call`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model,
          model_source: modelSource,
          messages: [
            {
              role: 'system',
              content: `You are the Architect agent in the VETKA pipeline.\nBreak tasks into actionable subtasks.\nOutput concise numbered subtasks and key notes.`,
            },
            { role: 'user', content: userMessage.content },
          ],
          max_tokens: 2000,
          temperature: 0.3,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      const data = await res.json();

      if (data.success && data.response) {
        const subtasks: string[] = [];
        for (const line of String(data.response).split('\n')) {
          const match = line.match(/^\d+\.\s+(.+)/);
          if (match) subtasks.push(match[1].replace(/\{needs_research.*\}/, '').trim());
        }

        addMessage({
          id: `arch_${Date.now()}_assistant`,
          role: 'architect',
          content: data.response,
          timestamp: Date.now(),
          subtasks: subtasks.length > 0 ? subtasks : undefined,
        });
        onPlanCreated?.(data.response);
      } else {
        addMessage({
          id: `arch_${Date.now()}_err`,
          role: 'architect',
          content: `Error: ${data.error || 'Unknown error from LLM'}`,
          timestamp: Date.now(),
        });
      }
    } catch (err) {
      clearTimeout(timeoutId);
      const errorMsg = err instanceof Error
        ? (err.name === 'AbortError' ? 'Request timeout (60s)' : err.message)
        : 'Failed to connect';
      addMessage({
        id: `arch_${Date.now()}_err`,
        role: 'architect',
        content: `Error: ${errorMsg}`,
        timestamp: Date.now(),
      });
    } finally {
      setLoading(false);
    }
  }, [input, loading, addMessage, setLoading, model, modelOptions, onPlanCreated]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', fontFamily: 'monospace', color: COLORS.text }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: mode === 'compact' ? '4px 0' : '8px 0', borderBottom: `1px solid ${COLORS.border}`, marginBottom: 8 }}>
        <div style={{ fontSize: mode === 'compact' ? 8 : 10, fontWeight: 600, letterSpacing: 1.2, textTransform: 'uppercase', color: COLORS.text }}>
          architect
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {loading && <span style={{ fontSize: 9, color: COLORS.textMuted }}>thinking...</span>}
          {mode === 'expanded' && (
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              style={{ background: COLORS.bgLight, border: `1px solid ${COLORS.border}`, borderRadius: 2, color: COLORS.textMuted, fontSize: 9, padding: '2px 6px', fontFamily: 'monospace', maxWidth: 180 }}
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
                </>
              )}
            </select>
          )}

          <button
            onClick={() => setActiveTab(mode === 'compact' ? 'architect' : 'mcc')}
            style={{ border: '1px solid #333', borderRadius: 2, background: 'transparent', color: '#999', fontFamily: 'monospace', fontSize: 9, padding: '1px 6px', cursor: 'pointer' }}
            title={mode === 'compact' ? 'Expand to Architect tab' : 'Collapse back to MCC'}
          >
            {mode === 'compact' ? '↗' : '↙'}
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', minHeight: mode === 'compact' ? 90 : 0, maxHeight: mode === 'compact' ? 190 : 'none', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {visibleMessages.length === 0 && (
          <div style={{ textAlign: 'center', color: COLORS.textDim, padding: mode === 'compact' ? 8 : 24, fontSize: mode === 'compact' ? 9 : 10 }}>
            describe a task for architect
          </div>
        )}

        {visibleMessages.map((msg) => (
          <div key={msg.id} style={{ padding: mode === 'compact' ? '5px 7px' : '8px 10px', background: msg.role === 'user' ? 'transparent' : 'rgba(255,255,255,0.02)', borderRadius: 4, border: `1px solid ${msg.role === 'user' ? COLORS.border : COLORS.borderLight}` }}>
            <div style={{ fontSize: 8, color: msg.role === 'user' ? COLORS.textMuted : COLORS.accent, marginBottom: 4, textTransform: 'uppercase', letterSpacing: 1 }}>
              {msg.role === 'user' ? 'you' : 'architect'}
            </div>
            <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: 1.45, color: msg.role === 'user' ? COLORS.textMuted : COLORS.text, fontSize: mode === 'compact' ? 9 : 10 }}>
              {msg.content}
            </div>
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      <div style={{ display: 'flex', gap: 6, paddingTop: 8, borderTop: `1px solid ${COLORS.border}` }}>
        {mode === 'compact' ? (
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="message architect..."
            disabled={loading}
            style={{ flex: 1, background: COLORS.bgLight, border: `1px solid ${COLORS.border}`, borderRadius: 3, color: COLORS.text, padding: '6px 8px', fontSize: 10, fontFamily: 'monospace', outline: 'none', minWidth: 0 }}
          />
        ) : (
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="describe task to plan..."
            disabled={loading}
            style={{ flex: 1, background: COLORS.bgLight, border: `1px solid ${COLORS.border}`, borderRadius: 3, color: COLORS.text, padding: '8px 10px', fontSize: 11, fontFamily: 'monospace', resize: 'none', minHeight: 40, maxHeight: 80, outline: 'none' }}
          />
        )}

        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          style={{ padding: mode === 'compact' ? '6px 10px' : '8px 16px', background: loading || !input.trim() ? 'transparent' : 'rgba(255,255,255,0.05)', border: `1px solid ${loading || !input.trim() ? COLORS.border : COLORS.borderLight}`, borderRadius: 3, color: loading || !input.trim() ? COLORS.textDim : COLORS.text, fontSize: mode === 'compact' ? 9 : 10, fontFamily: 'monospace', cursor: loading || !input.trim() ? 'not-allowed' : 'pointer', fontWeight: 500 }}
        >
          {loading ? '...' : (mode === 'compact' ? 'send' : 'plan')}
        </button>
      </div>
    </div>
  );
}
