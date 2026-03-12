/**
 * MARKER_153.2C: SandboxDropdown — single sandbox per project.
 *
 * Phase 146 had a multi-playground dropdown listing up to 5 worktrees.
 * Phase 153 simplifies: one sandbox per project, quota display, recreate/delete.
 *
 * States:
 * - No project: hidden (nothing to show)
 * - Project but no sandbox: [Create Sandbox] button
 * - Sandbox exists: [Sandbox ✓ 2.1/10GB] chip → popup with delete/recreate
 *
 * @phase 153
 * @wave 2
 */

import { useCallback, useEffect, useRef, useState } from 'react';
// MARKER_176.15: Centralized MCC API config import.
import { MCC_API } from '../../config/api.config';


interface SandboxStatus {
  exists: boolean;
  sandbox_path: string;
  file_count: number;
  used_gb: number;
  quota_gb: number;
  percent: number;
  warning: boolean;
  exceeded: boolean;
}

export function SandboxDropdown() {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<SandboxStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${MCC_API}/sandbox/status`);
      if (!res.ok) return;
      setStatus(await res.json());
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const onVisibility = () => {
      if (!document.hidden) fetchStatus();
    };
    window.addEventListener('task-board-updated', fetchStatus as EventListener);
    window.addEventListener('pipeline-stats', fetchStatus as EventListener);
    window.addEventListener('focus', fetchStatus);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.removeEventListener('task-board-updated', fetchStatus as EventListener);
      window.removeEventListener('pipeline-stats', fetchStatus as EventListener);
      window.removeEventListener('focus', fetchStatus);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [fetchStatus]);

  useEffect(() => {
    if (open) fetchStatus();
  }, [open, fetchStatus]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const handleCreate = useCallback(async () => {
    setLoading(true);
    try {
      // Recreate uses the project config source → sandbox
      await fetch(`${MCC_API}/sandbox/recreate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force: false }),
      });
      await fetchStatus();
    } finally {
      setLoading(false);
      setOpen(false);
    }
  }, [fetchStatus]);

  const handleRecreate = useCallback(async () => {
    setLoading(true);
    try {
      await fetch(`${MCC_API}/sandbox/recreate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force: true }),
      });
      await fetchStatus();
    } finally {
      setLoading(false);
      setOpen(false);
    }
  }, [fetchStatus]);

  const handleDelete = useCallback(async () => {
    setLoading(true);
    try {
      await fetch(`${MCC_API}/sandbox`, { method: 'DELETE' });
      await fetchStatus();
    } finally {
      setLoading(false);
      setOpen(false);
    }
  }, [fetchStatus]);

  // Don't render if no status yet (loading) or no project configured
  if (!status) return null;

  const exists = status.exists;
  const usedLabel = `${status.used_gb}/${status.quota_gb}GB`;
  const percentColor = status.exceeded ? '#e74c3c' : status.warning ? '#f39c12' : '#4ecdc4';

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => (exists ? setOpen(v => !v) : handleCreate())}
        disabled={loading}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 10px',
          background: open ? 'rgba(255,255,255,0.06)' : 'transparent',
          border: '1px solid #333',
          borderRadius: 3,
          color: '#ddd',
          fontSize: 10,
          fontFamily: 'monospace',
          cursor: loading ? 'wait' : 'pointer',
          minWidth: 120,
        }}
      >
        {exists ? (
          <>
            <span style={{ color: percentColor }}>{'●'}</span>
            <span>Sandbox</span>
            <span style={{ color: '#777' }}>{usedLabel}</span>
            <span style={{ marginLeft: 'auto', color: '#666' }}>{'▾'}</span>
          </>
        ) : (
          <>
            <span>{'+'}</span>
            <span>{loading ? 'Creating...' : 'Create Sandbox'}</span>
          </>
        )}
      </button>

      {open && exists && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            marginTop: 2,
            width: 260,
            background: '#111',
            border: '1px solid #333',
            borderRadius: 4,
            zIndex: 1000,
            boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
            fontFamily: 'monospace',
          }}
        >
          {/* Status header */}
          <div style={{ padding: '10px 12px', borderBottom: '1px solid #222' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#aaa' }}>
              <span>{status.file_count.toLocaleString()} files</span>
              <span style={{ color: percentColor }}>{status.percent}%</span>
            </div>
            {/* Usage bar */}
            <div style={{
              marginTop: 6,
              height: 3,
              background: '#222',
              borderRadius: 2,
              overflow: 'hidden',
            }}>
              <div style={{
                width: `${Math.min(status.percent, 100)}%`,
                height: '100%',
                background: percentColor,
                borderRadius: 2,
                transition: 'width 0.3s',
              }} />
            </div>
            <div style={{ marginTop: 4, fontSize: 9, color: '#666' }}>
              {usedLabel}
            </div>
          </div>

          {/* Actions */}
          <div style={{ padding: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
            <button
              onClick={handleRecreate}
              disabled={loading}
              style={{
                width: '100%',
                background: '#1a1a1a',
                border: '1px solid #333',
                borderRadius: 3,
                color: '#ddd',
                padding: '5px 8px',
                fontSize: 10,
                fontFamily: 'monospace',
                cursor: loading ? 'wait' : 'pointer',
                textAlign: 'left',
              }}
            >
              {'↻'} Recreate from source
            </button>
            <button
              onClick={handleDelete}
              disabled={loading}
              style={{
                width: '100%',
                background: '#1a1a1a',
                border: '1px solid #422',
                borderRadius: 3,
                color: '#a77',
                padding: '5px 8px',
                fontSize: 10,
                fontFamily: 'monospace',
                cursor: loading ? 'wait' : 'pointer',
                textAlign: 'left',
              }}
            >
              {'✕'} Delete sandbox
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
