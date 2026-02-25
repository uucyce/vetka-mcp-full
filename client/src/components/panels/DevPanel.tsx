/**
 * MARKER_143.P5: DevPanel — simplified 4-tab container.
 * Board + DAG + Watcher + Artifacts merged into MCC tab.
 * Remaining tabs: MCC, Stats, Architect, Balance.
 *
 * Previously: 7 tabs, ~1045 lines, Board state duplicated here.
 * Now: 4 tabs, ~200 lines, all task state lives in useMCCStore.
 *
 * @phase 143
 * @status active
 * @depends FloatingWindow, MyceliumCommandCenter, PipelineStats, ArchitectChat, BalancesPanel
 */

import { useState, useEffect, useCallback } from 'react';
import { FloatingWindow } from '../artifact/FloatingWindow';
import { StatsWorkspace } from './StatsWorkspace';
import { ArchitectChat } from './ArchitectChat';
import { BalancesPanel } from './BalancesPanel';
import { AgentStatusBar } from './AgentStatusBar';
import { useMyceliumSocket } from '../../hooks/useMyceliumSocket';
import { MyceliumCommandCenter } from '../mcc/MyceliumCommandCenter';
import { useMCCStore } from '../../store/useMCCStore';
import { useDevPanelStore, type DevPanelTab } from '../../store/useDevPanelStore';

interface DevPanelProps {
  isOpen?: boolean;
  onClose?: () => void;
  standalone?: boolean;
}

const TABS: { id: DevPanelTab; label: string }[] = [
  { id: 'mcc', label: 'MCC' },
  { id: 'stats', label: 'Stats' },
  { id: 'architect', label: 'Architect' },
  { id: 'balance', label: 'Balance' },
];

// MARKER_128.7A: Toast notification
interface ToastData {
  id: string;
  message: string;
  type: 'success' | 'error';
  taskId?: string;
}

export function DevPanel({ isOpen = true, onClose, standalone = false }: DevPanelProps) {
  const activeTab = useDevPanelStore(s => s.activeTab);
  const setActiveTab = useDevPanelStore(s => s.setActiveTab);
  const [toasts, setToasts] = useState<ToastData[]>([]);

  // MARKER_129.C14B: MYCELIUM WebSocket connection
  const { connected: myceliumConnected } = useMyceliumSocket();

  // MARKER_128.7B: Show toast for completed task
  const showToast = useCallback((message: string, type: 'success' | 'error', taskId?: string) => {
    const id = `toast_${Date.now()}`;
    setToasts(prev => [...prev, { id, message, type, taskId }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  }, []);

  // Listen for pipeline completion toasts
  useEffect(() => {
    if (!isOpen) return;

    const handleBoardUpdate = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.task_id && (detail?.status === 'done' || detail?.status === 'failed')) {
        const taskTitle = detail.title || detail.task_id.slice(0, 15);
        const confidence = detail.stats?.verifier_avg_confidence;
        const message = detail.status === 'done'
          ? `Pipeline done: ${taskTitle}${confidence ? ` — ${Math.round(confidence * 100)}%` : ''}`
          : `Pipeline failed: ${taskTitle}`;
        showToast(message, detail.status === 'done' ? 'success' : 'error', detail.task_id);
      }
    };

    window.addEventListener('task-board-updated', handleBoardUpdate);
    return () => window.removeEventListener('task-board-updated', handleBoardUpdate);
  }, [isOpen, showToast]);

  if (!isOpen) return null;

  const content = (
    <>
      {/* Tab bar */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        padding: '0 12px',
        background: 'rgba(0,0,0,0.2)',
      }}>
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              flex: 1,
              padding: '10px 0',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === tab.id ? '1px solid #e0e0e0' : '1px solid transparent',
              color: activeTab === tab.id ? '#e0e0e0' : '#444',
              fontSize: 10,
              fontFamily: 'monospace',
              fontWeight: activeTab === tab.id ? 600 : 400,
              letterSpacing: 1.5,
              textTransform: 'uppercase',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            {tab.label}
          </button>
        ))}

        {/* MYCELIUM connection indicator */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            padding: '0 8px',
            fontSize: 9,
            color: myceliumConnected ? '#4a4' : '#444',
            fontFamily: 'monospace',
            letterSpacing: 0.5,
          }}
          title={myceliumConnected ? 'MYCELIUM connected' : 'MYCELIUM disconnected'}
        >
          <span style={{
            width: 5, height: 5, borderRadius: '50%',
            background: myceliumConnected ? '#4a4' : '#333',
          }} />
          MYC
        </div>
      </div>

      {/* Tab content */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100% - 36px)',
        color: '#e0e0e0',
        fontSize: 13,
      }}>
        {/* ═══ MCC TAB ═══ (unified workspace: tasks + DAG + detail + stream) */}
        {activeTab === 'mcc' && (
          <div style={{ flex: 1, minHeight: 0 }}>
            <MyceliumCommandCenter />
          </div>
        )}

        {/* ═══ STATS TAB ═══ */}
        {activeTab === 'stats' && (
          <div style={{ padding: 12, flex: 1, overflowY: 'auto' }}>
            <StatsWorkspace />
          </div>
        )}

        {/* ═══ ARCHITECT TAB ═══ */}
        {activeTab === 'architect' && (
          <div style={{ padding: 12, flex: 1, overflowY: 'auto' }}>
            <ArchitectChat mode="expanded" />
          </div>
        )}

        {/* ═══ BALANCE TAB ═══ */}
        {activeTab === 'balance' && (
          <div style={{ padding: 12, flex: 1, overflowY: 'auto' }}>
            <BalancesPanel />
          </div>
        )}
      </div>

      {/* Multi-Agent Status Bar */}
      <AgentStatusBar />

      {/* Toast notifications */}
      {toasts.length > 0 && (
        <div style={{
          position: 'fixed',
          bottom: 20, right: 20,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
          zIndex: 10000,
        }}>
          {toasts.map(toast => (
            <div
              key={toast.id}
              onClick={() => {
                if (toast.taskId) {
                  setActiveTab('mcc');
                  // Select the task in MCC store so it focuses in the left panel
                  useMCCStore.getState().selectTask(toast.taskId);
                }
                setToasts(prev => prev.filter(t => t.id !== toast.id));
              }}
              style={{
                background: '#1a1a1a',
                borderLeft: `3px solid ${toast.type === 'success' ? '#2d5a3d' : '#5a2d2d'}`,
                padding: '10px 14px',
                borderRadius: 3,
                color: '#ccc',
                fontSize: 11,
                fontFamily: 'monospace',
                cursor: 'pointer',
                boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
                animation: 'slideUp 0.2s ease-out',
                maxWidth: 300,
              }}
            >
              {toast.message}
            </div>
          ))}
        </div>
      )}

      <style>{`
        @keyframes slideUp {
          from { transform: translateY(20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
      `}</style>
    </>
  );

  // Standalone mode
  if (standalone) {
    return (
      <div style={{
        width: '100%', height: '100%',
        background: '#0d0d0d',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {content}
      </div>
    );
  }

  // Normal floating window mode
  return (
    <FloatingWindow
      title="Dev Panel"
      isOpen={isOpen}
      onClose={onClose || (() => {})}
      defaultWidth={420}
      defaultHeight={600}
    >
      {content}
    </FloatingWindow>
  );
}
