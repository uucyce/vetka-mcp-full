/**
 * MARKER_144.11: NodeStreamView — agent output + artifact links for selected DAG node.
 *
 * When a node is clicked in DAG:
 * - Shows live stream events filtered by node's agent/taskId
 * - Shows historical pipeline output if node is complete
 * - Lists artifacts produced by this node with click-to-view
 *
 * Nolan palette, monospace, compact. ADDITIVE — does not modify existing panels.
 *
 * @phase 144
 * @status active
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useMCCStore } from '../../store/useMCCStore';
import type { StreamEvent } from '../../store/useMCCStore';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import type { DAGNode } from '../../types/dag';
import { ReflexInsight } from '../chat/ReflexInsight';
import type { ChatMessage } from '../../types/chat';
// MARKER_176.15: Centralized MCC API config import.
import { API_BASE } from '../../config/api.config';


interface NodeArtifact {
  id: string;
  name: string;
  status: string;
  artifact_type: string;
  language: string;
  file_path: string;
  size_bytes: number;
}

interface NodeStreamViewProps {
  node: DAGNode;
  onViewArtifact?: (artifact: NodeArtifact) => void;
}

// Tab type for the stream view
type StreamTab = 'stream' | 'output' | 'artifacts';

export function NodeStreamView({ node, onViewArtifact }: NodeStreamViewProps) {
  const [activeTab, setActiveTab] = useState<StreamTab>('stream');
  const [artifacts, setArtifacts] = useState<NodeArtifact[]>([]);
  const [nodeOutput, setNodeOutput] = useState<string>('');
  const [loadingOutput, setLoadingOutput] = useState(false);
  const [loadingArtifacts, setLoadingArtifacts] = useState(false);

  const streamEvents = useMCCStore(s => s.streamEvents);

  // Filter stream events for this specific node
  const nodeEvents = useMemo(() => {
    return streamEvents.filter(e => {
      // Match by taskId
      if (node.taskId && e.taskId === node.taskId) return true;
      // Match by role (agent nodes show their role's events)
      if (node.role && e.role === node.role) return true;
      // Match by node label in message
      if (e.message.includes(node.id) || e.message.includes(node.label)) return true;
      return false;
    }).slice(0, 20);
  }, [streamEvents, node]);

  // Fetch node output from pipeline history
  useEffect(() => {
    if (!node.taskId || node.taskId === 'draft') return;

    setLoadingOutput(true);
    fetch(`${API_BASE}/dag/node/${encodeURIComponent(node.id)}`)
      .then(r => r.json())
      .then(data => {
        if (data.success && data.node) {
          const output = data.node.output || data.node.result || data.node.description || '';
          setNodeOutput(typeof output === 'string' ? output : JSON.stringify(output, null, 2));
        }
      })
      .catch(() => setNodeOutput(''))
      .finally(() => setLoadingOutput(false));
  }, [node.id, node.taskId]);

  // Fetch artifacts related to this node
  useEffect(() => {
    setLoadingArtifacts(true);
    fetch(`${API_BASE}/artifacts`)
      .then(r => r.json())
      .then(data => {
        const allArtifacts: NodeArtifact[] = data.artifacts || [];
        // Filter artifacts by node's taskId or by filename matching node label
        const related = allArtifacts.filter(a => {
          if (node.taskId && a.file_path?.includes(node.taskId)) return true;
          if (a.name?.toLowerCase().includes(node.label.toLowerCase())) return true;
          return false;
        });
        setArtifacts(related);
      })
      .catch(() => setArtifacts([]))
      .finally(() => setLoadingArtifacts(false));
  }, [node.id, node.taskId, node.label]);

  const handleArtifactClick = useCallback((artifact: NodeArtifact) => {
    onViewArtifact?.(artifact);
  }, [onViewArtifact]);

  const tabStyle = (tab: StreamTab): React.CSSProperties => ({
    background: activeTab === tab ? 'rgba(255,255,255,0.06)' : 'transparent',
    border: `1px solid ${activeTab === tab ? NOLAN_PALETTE.border : NOLAN_PALETTE.borderDim}`,
    borderBottom: activeTab === tab ? 'none' : `1px solid ${NOLAN_PALETTE.borderDim}`,
    borderRadius: '2px 2px 0 0',
    padding: '3px 8px',
    color: activeTab === tab ? NOLAN_PALETTE.text : NOLAN_PALETTE.textDim,
    fontSize: 8,
    cursor: 'pointer',
    fontFamily: 'monospace',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Node header */}
      <div style={{
        padding: '6px 10px',
        borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{
            fontSize: 8, color: NOLAN_PALETTE.textDim,
            textTransform: 'uppercase', letterSpacing: 1,
          }}>
            {node.type}
          </span>
          <span style={{
            fontSize: 10, color: NOLAN_PALETTE.text, fontWeight: 600,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {node.label}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 6, marginTop: 3, fontSize: 8 }}>
          <StatusBadge status={node.status} />
          {node.role && <span style={{ color: '#666' }}>role: {node.role}</span>}
          {node.model && <span style={{ color: '#555' }}>model: {node.model}</span>}
          {node.durationS != null && (
            <span style={{ color: '#555' }}>{node.durationS.toFixed(1)}s</span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{
        display: 'flex', gap: 0, padding: '4px 10px 0',
        borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
        flexShrink: 0,
      }}>
        <button style={tabStyle('stream')} onClick={() => setActiveTab('stream')}>
          stream ({nodeEvents.length})
        </button>
        <button style={tabStyle('output')} onClick={() => setActiveTab('output')}>
          output
        </button>
        <button style={tabStyle('artifacts')} onClick={() => setActiveTab('artifacts')}>
          artifacts ({artifacts.length})
        </button>
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
        {activeTab === 'stream' && (
          <StreamTabContent events={nodeEvents} />
        )}
        {activeTab === 'output' && (
          <OutputTabContent output={nodeOutput} loading={loadingOutput} node={node} />
        )}
        {activeTab === 'artifacts' && (
          <ArtifactsTabContent
            artifacts={artifacts}
            loading={loadingArtifacts}
            onViewArtifact={handleArtifactClick}
          />
        )}
      </div>
    </div>
  );
}

// --- Sub-components ---

function StatusBadge({ status }: { status: string }) {
  const color = {
    pending: '#666',
    running: NOLAN_PALETTE.statusRunning || '#e0e0e0',
    done: NOLAN_PALETTE.statusDone || '#8a8',
    failed: NOLAN_PALETTE.statusFailed || '#a66',
  }[status] || '#555';

  return (
    <span style={{
      color,
      fontSize: 8,
      textTransform: 'uppercase',
    }}>
      {status === 'running' ? '● ' : ''}{status}
    </span>
  );
}

/** MARKER_174.B: Role → avatar emoji for chat bubbles */
const ROLE_AVATAR: Record<string, string> = {
  architect: '🏗️',
  coder: '⚡',
  researcher: '🔍',
  scout: '🐝',
  verifier: '✅',
  pipeline: '⚙️',
  board: '📋',
  stats: '📊',
  '@reflex': '🎯',
};

/** MARKER_174.B: Role → accent color for chat bubbles */
const ROLE_COLOR: Record<string, string> = {
  architect: 'rgba(234, 179, 8, 0.15)',     // gold
  coder: 'rgba(59, 130, 246, 0.15)',        // blue
  researcher: 'rgba(16, 185, 129, 0.15)',   // green
  scout: 'rgba(249, 115, 22, 0.15)',        // orange
  verifier: 'rgba(139, 92, 246, 0.15)',     // purple
  pipeline: 'rgba(255, 255, 255, 0.04)',
  '@reflex': 'rgba(139, 92, 246, 0.10)',
};

/**
 * MARKER_174.B: Chat-style stream tab — agent messages as bubbles with ReflexInsight pills.
 * Replaces plain-text log with conversational UX.
 */
function StreamTabContent({ events }: { events: StreamEvent[] }) {
  if (events.length === 0) {
    return (
      <div style={{ padding: 10, color: NOLAN_PALETTE.textDim, fontSize: 9, textAlign: 'center' }}>
        No stream events for this node yet.
        <br />
        <span style={{ fontSize: 8, color: '#444' }}>Events appear during pipeline execution.</span>
      </div>
    );
  }

  return (
    <div style={{ padding: '4px 6px', display: 'flex', flexDirection: 'column', gap: 3 }}>
      {events.map(event => {
        // MARKER_174.B: Rich rendering for REFLEX events
        if (event.metadata?.type === 'reflex') {
          const reflexMsg: ChatMessage = {
            id: event.id,
            role: 'system',
            content: event.message,
            type: 'reflex',
            timestamp: new Date(event.ts).toISOString(),
            metadata: { reflex: event.metadata as any },
          };
          return (
            <div key={event.id} style={{ display: 'flex', gap: 4, alignItems: 'flex-start' }}>
              <span style={{ fontSize: 10, minWidth: 16 }}>
                {ROLE_AVATAR[event.role] || ROLE_AVATAR['@reflex']}
              </span>
              <div style={{ flex: 1 }}>
                <ReflexInsight message={reflexMsg} />
              </div>
            </div>
          );
        }

        // MARKER_174.B: Chat bubble for regular agent messages
        const avatar = ROLE_AVATAR[event.role] || '💬';
        const bgColor = ROLE_COLOR[event.role] || 'rgba(255,255,255,0.04)';
        return (
          <div key={event.id} style={{
            display: 'flex', gap: 5, alignItems: 'flex-start',
          }}>
            <span style={{ fontSize: 10, minWidth: 16, marginTop: 1 }}>{avatar}</span>
            <div style={{
              flex: 1,
              background: bgColor,
              borderRadius: '4px 8px 8px 4px',
              padding: '3px 8px',
              borderLeft: `2px solid ${bgColor.replace(/[\d.]+\)$/, '0.4)')}`,
            }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 6, marginBottom: 1,
              }}>
                <span style={{
                  fontSize: 8, color: 'rgba(255,255,255,0.5)',
                  textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.5px',
                }}>
                  {event.role}
                </span>
                <span style={{ fontSize: 7, color: '#444' }}>
                  {new Date(event.ts).toLocaleTimeString()}
                </span>
              </div>
              <span style={{
                fontSize: 9, color: '#bbb', lineHeight: '14px',
                display: 'block', wordBreak: 'break-word',
              }} title={event.message}>
                {event.message}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function OutputTabContent({ output, loading, node }: { output: string; loading: boolean; node: DAGNode }) {
  if (loading) {
    return (
      <div style={{ padding: 10, color: NOLAN_PALETTE.textDim, fontSize: 9 }}>
        Loading output...
      </div>
    );
  }

  if (!output && node.status === 'pending') {
    return (
      <div style={{ padding: 10, color: NOLAN_PALETTE.textDim, fontSize: 9, textAlign: 'center' }}>
        Waiting for execution...
      </div>
    );
  }

  if (!output && node.status === 'running') {
    return (
      <div style={{ padding: 10, color: '#ccc', fontSize: 9, textAlign: 'center' }}>
        <span style={{
          display: 'inline-block', width: 6, height: 6, borderRadius: '50%',
          background: '#e0e0e0', marginRight: 6,
          animation: 'nodeStreamPulse 1.5s infinite',
        }} />
        Agent is working...
        <style>{`@keyframes nodeStreamPulse { 0%,100%{opacity:1} 50%{opacity:0.3} }`}</style>
      </div>
    );
  }

  if (!output) {
    return (
      <div style={{ padding: 10, color: NOLAN_PALETTE.textDim, fontSize: 9, textAlign: 'center' }}>
        No output recorded.
      </div>
    );
  }

  return (
    <pre style={{
      padding: 8,
      margin: 0,
      fontSize: 9,
      color: '#bbb',
      fontFamily: 'monospace',
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-word',
      lineHeight: 1.5,
    }}>
      {output}
    </pre>
  );
}

function ArtifactsTabContent({
  artifacts,
  loading,
  onViewArtifact,
}: {
  artifacts: NodeArtifact[];
  loading: boolean;
  onViewArtifact: (artifact: NodeArtifact) => void;
}) {
  if (loading) {
    return (
      <div style={{ padding: 10, color: NOLAN_PALETTE.textDim, fontSize: 9 }}>
        Loading artifacts...
      </div>
    );
  }

  if (artifacts.length === 0) {
    return (
      <div style={{ padding: 10, color: NOLAN_PALETTE.textDim, fontSize: 9, textAlign: 'center' }}>
        No artifacts linked to this node.
      </div>
    );
  }

  return (
    <div style={{ padding: 4 }}>
      {artifacts.map(artifact => (
        <div
          key={artifact.id}
          onClick={() => onViewArtifact(artifact)}
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
            padding: '6px 8px',
            cursor: 'pointer',
            borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
            transition: 'background 0.1s',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 10, color: NOLAN_PALETTE.text }}>
              {artifact.name}
            </span>
            <span style={{
              fontSize: 7,
              color: artifact.status === 'approved' ? '#8a8' :
                     artifact.status === 'rejected' ? '#a66' : '#666',
              textTransform: 'uppercase',
            }}>
              {artifact.status}
            </span>
          </div>
          <div style={{ display: 'flex', gap: 8, fontSize: 8, color: '#555' }}>
            <span>{artifact.language}</span>
            <span>{artifact.artifact_type}</span>
            {artifact.size_bytes > 0 && (
              <span>{(artifact.size_bytes / 1024).toFixed(1)}kb</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
