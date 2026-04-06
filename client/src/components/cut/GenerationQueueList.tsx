/**
 * MARKER_GEN-QUEUE: Generation Queue List — job rows with status, progress, context menu.
 *
 * Features:
 *   - Job rows: provider monogram, prompt excerpt, status, progress bar, cost, ETA
 *   - Drag to reorder queued jobs
 *   - Right-click context menu: Preview, Accept, Cancel, Retry, Duplicate, Copy Prompt
 *   - Completed jobs separated by horizontal rule
 *
 * Monochrome — ZERO color. Status via brightness + shape.
 *
 * @phase GENERATION_CONTROL
 * @task tb_1774432042_1
 */
import { useState, useCallback, useRef, useEffect, type CSSProperties, type MouseEvent } from 'react';
import { useGenerationControlStore, type JobRecord, type JobRecordStatus } from '../../store/useGenerationControlStore';
import { PROVIDER_MAP } from '../../config/generation.config';

// ─── Types (local view model — maps from JobRecord) ───

type JobStatus = JobRecordStatus;

interface GenerationJob {
  id: string;
  providerId: string;
  providerMonogram: string;
  prompt: string;
  status: JobStatus;
  progress: number; // 0-1
  cost: number | null;
  eta: string | null;
  createdAt: number;
  completedAt: number | null;
  previewUrl: string | null;
}

interface ContextMenuState {
  visible: boolean;
  x: number;
  y: number;
  jobId: string | null;
}

// ─── Map store JobRecord → local view model ───

function toViewModel(r: JobRecord): GenerationJob {
  const provider = PROVIDER_MAP.get(r.providerId);
  return {
    id: r.id,
    providerId: r.providerId,
    providerMonogram: provider?.monogram ?? r.providerId.slice(0, 1).toUpperCase(),
    prompt: r.prompt,
    status: r.status,
    progress: r.progress,
    cost: r.cost,
    eta: r.eta,
    createdAt: r.createdAt,
    completedAt: r.completedAt,
    previewUrl: r.previewUrl,
  };
}

// ─── Styles ───

const PANEL: CSSProperties = {
  display: 'flex', flexDirection: 'column', height: '100%',
  background: '#0d0d0d', fontFamily: 'system-ui', fontSize: 11, color: '#ccc',
  overflow: 'auto',
};

const HEADER: CSSProperties = {
  padding: '8px 10px', borderBottom: '1px solid #1a1a1a',
  fontWeight: 600, fontSize: 12, flexShrink: 0,
};

const JOB_ROW: CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 8,
  padding: '6px 10px', borderBottom: '1px solid #111',
  cursor: 'default',
};

const MONOGRAM: CSSProperties = {
  width: 18, height: 18, borderRadius: 3,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  background: '#1a1a1a', color: '#888', fontSize: 9, fontWeight: 700,
  flexShrink: 0,
};

const PROMPT_TEXT: CSSProperties = {
  flex: 1, overflow: 'hidden', textOverflow: 'ellipsis',
  whiteSpace: 'nowrap', fontSize: 10, color: '#aaa',
};

const STATUS_BADGE: CSSProperties = {
  fontSize: 8, padding: '1px 5px', borderRadius: 2,
  textTransform: 'uppercase', fontWeight: 600,
  flexShrink: 0,
};

const PROGRESS_BAR_BG: CSSProperties = {
  width: 50, height: 4, background: '#1a1a1a', borderRadius: 2,
  overflow: 'hidden', flexShrink: 0,
};

const COST_TEXT: CSSProperties = {
  fontSize: 9, color: '#666', fontFamily: 'monospace',
  width: 40, textAlign: 'right', flexShrink: 0,
};

const ETA_TEXT: CSSProperties = {
  fontSize: 9, color: '#444', width: 36, textAlign: 'right', flexShrink: 0,
};

const SEPARATOR: CSSProperties = {
  borderTop: '1px solid #222', margin: '4px 10px',
};

const CONTEXT_MENU: CSSProperties = {
  position: 'fixed', zIndex: 99999,
  background: '#1a1a1a', border: '1px solid #333', borderRadius: 4,
  boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
  minWidth: 140, padding: '4px 0',
};

const MENU_ITEM: CSSProperties = {
  padding: '5px 12px', fontSize: 10, color: '#aaa',
  cursor: 'pointer', userSelect: 'none',
};

const MENU_ITEM_HOVER: CSSProperties = {
  ...MENU_ITEM, background: '#222', color: '#ccc',
};

const EMPTY: CSSProperties = {
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  flex: 1, color: '#444', fontSize: 10,
};

// ─── Status helpers ───

function statusStyle(status: JobStatus): CSSProperties {
  switch (status) {
    case 'generating': return { ...STATUS_BADGE, background: '#222', color: '#ccc' };
    case 'queued':     return { ...STATUS_BADGE, background: '#151515', color: '#666' };
    case 'previewing': return { ...STATUS_BADGE, background: '#222', color: '#aaa' };
    case 'completed':  return { ...STATUS_BADGE, background: '#1a1a1a', color: '#888' };
    case 'cancelled':  return { ...STATUS_BADGE, background: '#111', color: '#444' };
    case 'failed':     return { ...STATUS_BADGE, background: '#1a1a1a', color: '#666' };
  }
}

function statusLabel(status: JobStatus): string {
  switch (status) {
    case 'generating': return 'GEN';
    case 'queued':     return 'QUE';
    case 'previewing': return 'PRV';
    case 'completed':  return 'DONE';
    case 'cancelled':  return 'CXL';
    case 'failed':     return 'FAIL';
  }
}

// ─── Component ───

export default function GenerationQueueList() {
  // Initialize from store; sync when store history changes (new jobs arrive)
  const storeHistory = useGenerationControlStore((s) => s.jobHistory);
  const [jobs, setJobs] = useState<GenerationJob[]>(() => storeHistory.map(toViewModel));

  // Sync store → local when new jobs added (avoids overwriting local context-menu mutations)
  const prevLenRef = useRef(storeHistory.length);
  useEffect(() => {
    if (storeHistory.length !== prevLenRef.current) {
      prevLenRef.current = storeHistory.length;
      setJobs(storeHistory.map(toViewModel));
    }
  }, [storeHistory]);

  // Keep active job's status/progress in sync
  useEffect(() => {
    if (storeHistory.length === 0) return;
    const active = storeHistory[0];
    setJobs((prev) => {
      if (prev.length === 0) return prev;
      const head = prev[0];
      if (head.id === active.id && (head.status !== active.status || head.progress !== active.progress)) {
        return [toViewModel(active), ...prev.slice(1)];
      }
      return prev;
    });
  }, [storeHistory]);

  const [contextMenu, setContextMenu] = useState<ContextMenuState>({
    visible: false, x: 0, y: 0, jobId: null,
  });
  const [hoveredMenuItem, setHoveredMenuItem] = useState<string | null>(null);
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close context menu on outside click
  useEffect(() => {
    if (!contextMenu.visible) return;
    const handler = () => setContextMenu((s) => ({ ...s, visible: false }));
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, [contextMenu.visible]);

  const handleContextMenu = useCallback((e: MouseEvent, jobId: string) => {
    e.preventDefault();
    setContextMenu({ visible: true, x: e.clientX, y: e.clientY, jobId });
  }, []);

  const menuAction = useCallback((action: string) => {
    const jobId = contextMenu.jobId;
    if (!jobId) return;
    setContextMenu((s) => ({ ...s, visible: false }));

    switch (action) {
      case 'cancel':
        setJobs((prev) => prev.map((j) => j.id === jobId ? { ...j, status: 'cancelled' as JobStatus, progress: 0 } : j));
        break;
      case 'retry':
        setJobs((prev) => prev.map((j) => j.id === jobId ? { ...j, status: 'queued' as JobStatus, progress: 0 } : j));
        break;
      case 'duplicate':
        setJobs((prev) => {
          const src = prev.find((j) => j.id === jobId);
          if (!src) return prev;
          return [...prev, { ...src, id: `j${Date.now()}`, status: 'queued' as JobStatus, progress: 0, cost: null, eta: null, createdAt: Date.now(), completedAt: null }];
        });
        break;
      case 'copy_prompt': {
        const job = jobs.find((j) => j.id === jobId);
        if (job) navigator.clipboard.writeText(job.prompt).catch(() => {});
        break;
      }
    }
  }, [contextMenu.jobId, jobs]);

  // Drag reorder (queued jobs only)
  const handleDragStart = useCallback((idx: number) => {
    setDragIdx(idx);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, idx: number) => {
    e.preventDefault();
    if (dragIdx === null || dragIdx === idx) return;
    setJobs((prev) => {
      const copy = [...prev];
      const [moved] = copy.splice(dragIdx, 1);
      copy.splice(idx, 0, moved);
      return copy;
    });
    setDragIdx(idx);
  }, [dragIdx]);

  const handleDragEnd = useCallback(() => {
    setDragIdx(null);
  }, []);

  // Split active vs completed
  const activeJobs = jobs.filter((j) => j.status !== 'completed' && j.status !== 'cancelled' && j.status !== 'failed');
  const doneJobs = jobs.filter((j) => j.status === 'completed' || j.status === 'cancelled' || j.status === 'failed');

  const renderJob = (job: GenerationJob, idx: number, draggable: boolean) => (
    <div
      key={job.id}
      style={{
        ...JOB_ROW,
        opacity: dragIdx === idx ? 0.5 : 1,
      }}
      data-testid={`queue-job-${job.id}`}
      onContextMenu={(e) => handleContextMenu(e, job.id)}
      draggable={draggable && job.status === 'queued'}
      onDragStart={() => handleDragStart(idx)}
      onDragOver={(e) => handleDragOver(e, idx)}
      onDragEnd={handleDragEnd}
    >
      <span style={MONOGRAM}>{job.providerMonogram}</span>
      <span style={PROMPT_TEXT} title={job.prompt}>{job.prompt}</span>
      <span style={statusStyle(job.status)}>{statusLabel(job.status)}</span>
      {job.status === 'generating' && (
        <div style={PROGRESS_BAR_BG}>
          <div style={{ height: '100%', width: `${job.progress * 100}%`, background: '#888', borderRadius: 2 }} />
        </div>
      )}
      {job.eta && <span style={ETA_TEXT}>{job.eta}</span>}
      <span style={COST_TEXT}>{job.cost !== null ? `$${job.cost.toFixed(2)}` : '-'}</span>
    </div>
  );

  return (
    <div style={PANEL} data-testid="generation-queue-list">
      <div style={HEADER}>
        Generation Queue
        <span style={{ fontWeight: 400, color: '#555', marginLeft: 6, fontSize: 10 }}>
          ({activeJobs.length} active)
        </span>
      </div>

      {jobs.length === 0 ? (
        <div style={EMPTY}>No jobs in queue</div>
      ) : (
        <>
          {activeJobs.map((job, idx) => renderJob(job, idx, true))}
          {doneJobs.length > 0 && (
            <>
              <div style={SEPARATOR} />
              <div style={{ padding: '2px 10px', fontSize: 9, color: '#444' }}>Completed</div>
              {doneJobs.map((job, idx) => renderJob(job, activeJobs.length + idx, false))}
            </>
          )}
        </>
      )}

      {/* Context menu */}
      {contextMenu.visible && (
        <div
          ref={menuRef}
          style={{ ...CONTEXT_MENU, left: contextMenu.x, top: contextMenu.y }}
          data-testid="queue-context-menu"
        >
          {[
            { id: 'preview', label: 'Preview' },
            { id: 'accept', label: 'Accept' },
            { id: 'cancel', label: 'Cancel' },
            { id: 'retry', label: 'Retry' },
            { id: 'duplicate', label: 'Duplicate' },
            { id: 'copy_prompt', label: 'Copy Prompt' },
          ].map((item) => (
            <div
              key={item.id}
              style={hoveredMenuItem === item.id ? MENU_ITEM_HOVER : MENU_ITEM}
              onMouseEnter={() => setHoveredMenuItem(item.id)}
              onMouseLeave={() => setHoveredMenuItem(null)}
              onClick={() => menuAction(item.id)}
              data-testid={`ctx-${item.id}`}
            >
              {item.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
