/**
 * MARKER_152.7: Inline TaskEditor for MCC list.
 */
import { useMemo, useState } from 'react';

interface EditableTask {
  id: string;
  title: string;
  description?: string;
  priority: number;
  tags?: string[];
  source?: string;
  source_chat_id?: string;
  source_group_id?: string;
}

interface TaskEditorProps {
  task: EditableTask;
  onSaved?: () => void;
  onCancel?: () => void;
}

const API_BASE = 'http://localhost:5001/api/debug';

function sourceBadge(source?: string): { icon: string; label: string } {
  const s = String(source || '').toLowerCase();
  if (s.includes('dragon')) return { icon: '🐉', label: 'Dragon' };
  if (s.includes('opus')) return { icon: '🤖', label: 'Opus' };
  if (s.includes('codex')) return { icon: '📝', label: 'Codex' };
  if (s.includes('heartbeat')) return { icon: '⏱', label: 'Heartbeat' };
  if (s.includes('manual') || s === 'api') return { icon: '👤', label: 'Manual' };
  if (s) return { icon: '•', label: s };
  return { icon: '👤', label: 'Manual' };
}

export function TaskEditor({ task, onSaved, onCancel }: TaskEditorProps) {
  const [title, setTitle] = useState(task.title || '');
  const [description, setDescription] = useState(task.description || '');
  const [priority, setPriority] = useState(task.priority || 3);
  const [tagsRaw, setTagsRaw] = useState((task.tags || []).join(', '));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const source = useMemo(() => sourceBadge(task.source), [task.source]);

  const handleSave = async () => {
    if (!title.trim()) {
      setMessage('title required');
      return;
    }

    const tags = tagsRaw
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    setSaving(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_BASE}/task-board/${encodeURIComponent(task.id)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
          priority,
          tags,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data?.success) {
        setMessage('saved');
        onSaved?.();
      } else {
        setMessage(data?.error || 'save failed');
      }
    } catch {
      setMessage('save error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      style={{
        borderTop: '1px solid #1a1a1a',
        borderBottom: '1px solid #222',
        padding: '7px 8px',
        background: '#0d0d0d',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ fontSize: 10 }}>{source.icon}</span>
        <span style={{ color: '#888', fontSize: 9 }}>{source.label}</span>
        {task.source_chat_id && (
          <span style={{ color: '#666', fontSize: 9 }} title="Source chat ID">
            From: Chat #{String(task.source_chat_id).slice(0, 8)}
          </span>
        )}
        {task.source_group_id && (
          <span style={{ color: '#555', fontSize: 8 }} title="Source group ID">
            group:{String(task.source_group_id).slice(0, 8)}
          </span>
        )}
      </div>

      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="task title"
        style={{
          background: '#111',
          border: '1px solid #333',
          borderRadius: 2,
          color: '#ddd',
          fontSize: 10,
          fontFamily: 'monospace',
          padding: '4px 6px',
          outline: 'none',
        }}
      />

      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="description"
        rows={3}
        style={{
          background: '#111',
          border: '1px solid #333',
          borderRadius: 2,
          color: '#bbb',
          fontSize: 9,
          fontFamily: 'monospace',
          padding: '5px 6px',
          outline: 'none',
          resize: 'vertical',
        }}
      />

      <div style={{ display: 'flex', gap: 6 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#888', fontSize: 9 }}>
          priority
          <input
            type="number"
            min={1}
            max={5}
            value={priority}
            onChange={(e) => setPriority(Math.max(1, Math.min(5, Number(e.target.value || 3))))}
            style={{
              width: 44,
              background: '#111',
              border: '1px solid #333',
              borderRadius: 2,
              color: '#ddd',
              fontSize: 9,
              fontFamily: 'monospace',
              padding: '3px 4px',
            }}
          />
        </label>

        <input
          value={tagsRaw}
          onChange={(e) => setTagsRaw(e.target.value)}
          placeholder="tags: ui, bug, mcc"
          style={{
            flex: 1,
            minWidth: 0,
            background: '#111',
            border: '1px solid #333',
            borderRadius: 2,
            color: '#aaa',
            fontSize: 9,
            fontFamily: 'monospace',
            padding: '3px 6px',
            outline: 'none',
          }}
        />
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            background: saving ? 'transparent' : 'rgba(78,205,196,0.14)',
            border: '1px solid #4ecdc4',
            borderRadius: 2,
            color: saving ? '#666' : '#bffff9',
            fontSize: 9,
            fontFamily: 'monospace',
            padding: '3px 8px',
            cursor: saving ? 'wait' : 'pointer',
          }}
        >
          {saving ? '...' : 'save'}
        </button>
        <button
          onClick={onCancel}
          style={{
            background: 'transparent',
            border: '1px solid #333',
            borderRadius: 2,
            color: '#888',
            fontSize: 9,
            fontFamily: 'monospace',
            padding: '3px 8px',
            cursor: 'pointer',
          }}
        >
          cancel
        </button>
        {message && <span style={{ color: message === 'saved' ? '#7ab07a' : '#aa7777', fontSize: 9 }}>{message}</span>}
      </div>
    </div>
  );
}
