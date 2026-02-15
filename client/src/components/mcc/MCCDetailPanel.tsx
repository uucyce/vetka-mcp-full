/**
 * MARKER_143.P4: MCCDetailPanel — context-sensitive right panel.
 * Mode A: DAG node selected → node info + role editor
 * Mode B: Task selected (done/failed) → PipelineResultsViewer
 * Mode C: Task selected (running) → live progress
 * Mode D: Nothing selected → stats overview
 *
 * @phase 143
 * @status active
 */
import { useMemo, useState, useEffect } from 'react';
import { useMCCStore } from '../../store/useMCCStore';
import { DetailPanel } from './DetailPanel';
import { PipelineResultsViewer } from './PipelineResultsViewer';
import { NodeStreamView } from './NodeStreamView';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import { PipelineStats } from '../panels/PipelineStats';
import { ArchitectChat } from '../panels/ArchitectChat';
import type { DAGNode, DAGStats } from '../../types/dag';

const PIPELINE_API = 'http://localhost:5001/api/pipeline';

interface MCCDetailPanelProps {
  // DAG context
  selectedDagNode: DAGNode | null;
  selectedEdge: { id: string; source: string; target: string; type: string } | null;
  stats: DAGStats | null;
  onNodeAction: (action: string) => void;
  // MARKER_144.5: Edit mode node property editor
  editMode?: boolean;
  onUpdateNodeData?: (nodeId: string, data: Partial<DAGNode>) => void;
  // MARKER_144.11: Artifact viewer callback
  onViewArtifact?: (artifact: { id: string; name: string; file_path: string; language: string }) => void;
}

// MARKER_143.P6I: Compact read-only role summary for overview mode.
// Shows role→model pairs. No editing here — click agent node in DAG to edit.
function RolesSummary({ activePreset }: { activePreset: string }) {
  const [roles, setRoles] = useState<Record<string, string>>({});

  useEffect(() => {
    fetch(`${PIPELINE_API}/presets/${activePreset}`)
      .then(r => r.json())
      .then(data => {
        if (data.success && data.preset?.roles) {
          setRoles(data.preset.roles);
        }
      })
      .catch(() => {});
  }, [activePreset]);

  const entries = Object.entries(roles);
  if (entries.length === 0) return null;

  return (
    <div style={{ marginTop: 10 }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 4,
      }}>
        <span style={{ fontSize: 9, color: '#555', textTransform: 'uppercase', letterSpacing: 1 }}>
          team ({entries.length})
        </span>
        <span style={{ fontSize: 8, color: '#444', background: 'rgba(255,255,255,0.03)', padding: '1px 5px', borderRadius: 2 }}>
          {activePreset}
        </span>
      </div>
      {entries.map(([role, model]) => {
        const modelShort = model ? (model.split('/').pop()?.split(':')[0] || model) : '—';
        return (
          <div key={role} style={{
            display: 'flex', justifyContent: 'space-between',
            padding: '2px 6px', fontSize: 9,
          }}>
            <span style={{ color: '#777', textTransform: 'uppercase', fontSize: 8, minWidth: 28 }}>
              {role.slice(0, 3)}
            </span>
            <span style={{
              color: '#aaa', flex: 1, textAlign: 'right',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }} title={model}>
              {modelShort}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// MARKER_144.11: Tab bar for dag_node mode — switches between Info and Stream views
function DagNodeTabBar({ activeTab, onTabChange }: {
  activeTab: 'info' | 'stream';
  onTabChange: (tab: 'info' | 'stream') => void;
}) {
  const tabBtn = (tab: 'info' | 'stream', label: string): React.CSSProperties => ({
    background: activeTab === tab ? 'rgba(255,255,255,0.06)' : 'transparent',
    border: 'none',
    borderBottom: activeTab === tab ? `1px solid ${NOLAN_PALETTE.text}` : '1px solid transparent',
    padding: '4px 10px',
    color: activeTab === tab ? NOLAN_PALETTE.text : NOLAN_PALETTE.textDim,
    fontSize: 8,
    cursor: 'pointer',
    fontFamily: 'monospace',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  });

  return (
    <div style={{
      display: 'flex',
      borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
      flexShrink: 0,
    }}>
      <button style={tabBtn('info', 'info')} onClick={() => onTabChange('info')}>
        info
      </button>
      <button style={tabBtn('stream', 'stream')} onClick={() => onTabChange('stream')}>
        stream
      </button>
    </div>
  );
}

// MARKER_144.5: Inline node property editor for edit mode
function NodePropertyEditor({
  node,
  onUpdate,
}: {
  node: DAGNode;
  onUpdate: (nodeId: string, data: Partial<DAGNode>) => void;
}) {
  const inputStyle: React.CSSProperties = {
    width: '100%',
    background: 'rgba(255,255,255,0.04)',
    border: `1px solid ${NOLAN_PALETTE.border}`,
    borderRadius: 2,
    padding: '3px 6px',
    color: NOLAN_PALETTE.text,
    fontSize: 10,
    fontFamily: 'monospace',
    outline: 'none',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 8,
    color: NOLAN_PALETTE.textDim,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginBottom: 2,
    marginTop: 8,
  };

  return (
    <div style={{ padding: 10 }}>
      <div style={{ fontSize: 9, color: '#555', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
        edit node
      </div>

      {/* Type (read-only) */}
      <div style={labelStyle}>type</div>
      <div style={{ fontSize: 10, color: NOLAN_PALETTE.textMuted, padding: '3px 0' }}>
        {node.type}
      </div>

      {/* Label */}
      <div style={labelStyle}>label</div>
      <input
        style={inputStyle}
        value={node.label}
        onChange={e => onUpdate(node.id, { label: e.target.value })}
      />

      {/* Description */}
      <div style={labelStyle}>description</div>
      <textarea
        style={{ ...inputStyle, minHeight: 48, resize: 'vertical' }}
        value={node.description || ''}
        onChange={e => onUpdate(node.id, { description: e.target.value })}
        placeholder="Node description..."
      />

      {/* Type-specific fields */}
      {node.type === 'agent' && (
        <>
          <div style={labelStyle}>role</div>
          <select
            style={inputStyle}
            value={node.role || ''}
            onChange={e => onUpdate(node.id, { role: e.target.value as any })}
          >
            <option value="">—</option>
            <option value="scout">scout</option>
            <option value="architect">architect</option>
            <option value="researcher">researcher</option>
            <option value="coder">coder</option>
            <option value="verifier">verifier</option>
          </select>

          <div style={labelStyle}>model</div>
          <input
            style={inputStyle}
            value={node.model || ''}
            onChange={e => onUpdate(node.id, { model: e.target.value })}
            placeholder="e.g. kimi-k2.5"
          />
        </>
      )}

      {/* Status selector for all types */}
      <div style={labelStyle}>status</div>
      <select
        style={inputStyle}
        value={node.status}
        onChange={e => onUpdate(node.id, { status: e.target.value as any })}
      >
        <option value="pending">pending</option>
        <option value="running">running</option>
        <option value="done">done</option>
        <option value="failed">failed</option>
      </select>

      <div style={{ marginTop: 10, fontSize: 8, color: NOLAN_PALETTE.textDimmer, textAlign: 'center' }}>
        ID: {node.id}
      </div>
    </div>
  );
}

export function MCCDetailPanel({
  selectedDagNode,
  selectedEdge,
  stats,
  onNodeAction,
  editMode = false,
  onUpdateNodeData,
  onViewArtifact,
}: MCCDetailPanelProps) {
  const selectedTaskId = useMCCStore(s => s.selectedTaskId);
  const tasks = useMCCStore(s => s.tasks);
  const activePreset = useMCCStore(s => s.activePreset);
  const activeAgents = useMCCStore(s => s.activeAgents);

  // MARKER_144.11: Tab state for dag_node mode (info vs stream)
  const [dagNodeTab, setDagNodeTab] = useState<'info' | 'stream'>('info');

  // Reset tab when node changes
  useEffect(() => {
    setDagNodeTab('info');
  }, [selectedDagNode?.id]);

  const selectedTask = useMemo(() => {
    if (!selectedTaskId) return null;
    return tasks.find(t => t.id === selectedTaskId) || null;
  }, [selectedTaskId, tasks]);

  // Determine mode
  const mode = useMemo(() => {
    if (selectedDagNode) return 'dag_node';
    if (selectedTask && (selectedTask.status === 'done' || selectedTask.status === 'failed')) return 'task_results';
    if (selectedTask && selectedTask.status === 'running') return 'task_running';
    if (selectedTask) return 'task_info';
    return 'overview';
  }, [selectedDagNode, selectedTask]);

  // MARKER_143.P4B: In dag_node mode, DetailPanel renders full-height with its own padding.
  // MARKER_144.5: In edit mode, show NodePropertyEditor instead of read-only DetailPanel.
  // MARKER_144.11: Three sub-views — info (detail), stream (agent output), edit (property editor)
  if (mode === 'dag_node') {
    if (editMode && selectedDagNode && onUpdateNodeData) {
      return (
        <div style={{ height: '100%', fontFamily: 'monospace', color: NOLAN_PALETTE.text, overflowY: 'auto' }}>
          <NodePropertyEditor node={selectedDagNode} onUpdate={onUpdateNodeData} />
        </div>
      );
    }
    return (
      <div style={{ height: '100%', fontFamily: 'monospace', color: NOLAN_PALETTE.text, display: 'flex', flexDirection: 'column' }}>
        {/* MARKER_144.11: Tab bar — info vs stream */}
        <DagNodeTabBar activeTab={dagNodeTab} onTabChange={setDagNodeTab} />

        {dagNodeTab === 'info' && (
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <DetailPanel
              node={selectedDagNode}
              stats={stats}
              onAction={onNodeAction}
              activePreset={activePreset}
              selectedEdge={selectedEdge}
            />
          </div>
        )}

        {dagNodeTab === 'stream' && selectedDagNode && (
          <div style={{ flex: 1, minHeight: 0 }}>
            <NodeStreamView
              node={selectedDagNode}
              onViewArtifact={onViewArtifact}
            />
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflowY: 'auto',
        padding: 10,
        fontFamily: 'monospace',
        color: NOLAN_PALETTE.text,
      }}
    >

      {/* Mode B: Task selected, done/failed — pipeline results */}
      {mode === 'task_results' && selectedTask && (
        <div>
          <div style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 9, color: '#555', textTransform: 'uppercase', letterSpacing: 1 }}>
              results
            </div>
            <div style={{
              fontSize: 11, color: '#fff', fontWeight: 600, marginTop: 2,
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {selectedTask.title}
            </div>
            <div style={{ display: 'flex', gap: 6, marginTop: 4, fontSize: 9 }}>
              {selectedTask.preset && (
                <span style={{ color: '#666', background: 'rgba(255,255,255,0.04)', padding: '1px 4px', borderRadius: 2 }}>
                  {selectedTask.preset}
                </span>
              )}
              <span style={{ color: selectedTask.status === 'done' ? '#8a8' : '#a66' }}>
                {selectedTask.status}
              </span>
              {selectedTask.stats?.duration_s && (
                <span style={{ color: '#555' }}>{selectedTask.stats.duration_s.toFixed(1)}s</span>
              )}
              {selectedTask.stats?.verifier_avg_confidence && (
                <span style={{
                  color: selectedTask.stats.verifier_avg_confidence >= 0.7 ? '#8a8' : '#aa8',
                }}>
                  {(selectedTask.stats.verifier_avg_confidence * 100).toFixed(0)}%
                </span>
              )}
            </div>
          </div>
          <PipelineResultsViewer taskId={selectedTask.id} />
        </div>
      )}

      {/* Mode C: Task running — progress display */}
      {mode === 'task_running' && selectedTask && (
        <div>
          <div style={{ fontSize: 9, color: '#555', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>
            running
          </div>
          <div style={{ fontSize: 11, color: '#fff', fontWeight: 600 }}>{selectedTask.title}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8, fontSize: 10 }}>
            <span style={{
              width: 8, height: 8, borderRadius: '50%', background: '#e0e0e0',
              animation: 'mccDetailPulse 1.5s infinite',
            }} />
            <span style={{ color: '#ccc' }}>Pipeline executing...</span>
          </div>

          {/* Show active agents working on this task */}
          {activeAgents.filter(a => a.task_id === selectedTask.id).map(agent => (
            <div key={agent.agent_name} style={{
              display: 'flex', gap: 6, padding: '4px 0', fontSize: 9, marginTop: 4,
            }}>
              <span style={{ color: '#888' }}>{agent.agent_name}</span>
              <span style={{ color: '#555', flex: 1 }}>{agent.task_title?.slice(0, 30)}</span>
              <span style={{ color: '#444' }}>
                {agent.elapsed_seconds < 60 ? `${agent.elapsed_seconds}s` : `${Math.floor(agent.elapsed_seconds / 60)}m`}
              </span>
            </div>
          ))}

          {selectedTask.preset && (
            <div style={{ marginTop: 8, fontSize: 9, color: '#666' }}>
              team: {selectedTask.preset}
            </div>
          )}

          <style>{`@keyframes mccDetailPulse { 0%,100%{opacity:1} 50%{opacity:0.3} }`}</style>
        </div>
      )}

      {/* Mode: Task selected but not running/done */}
      {mode === 'task_info' && selectedTask && (
        <div>
          <div style={{ fontSize: 9, color: '#555', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>
            task
          </div>
          <div style={{ fontSize: 11, color: '#fff', fontWeight: 600 }}>{selectedTask.title}</div>
          {selectedTask.description && selectedTask.description !== selectedTask.title && (
            <div style={{ fontSize: 9, color: '#888', marginTop: 4, lineHeight: 1.4 }}>
              {selectedTask.description.slice(0, 200)}
            </div>
          )}
          <div style={{ display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
            {selectedTask.tags?.map(tag => (
              <span key={tag} style={{
                fontSize: 8, background: 'rgba(255,255,255,0.04)', color: '#888',
                padding: '1px 5px', borderRadius: 2, fontFamily: 'monospace',
              }}>{tag}</span>
            ))}
          </div>
          <div style={{ fontSize: 9, color: '#555', marginTop: 6 }}>
            status: {selectedTask.status} · P{selectedTask.priority}
            {selectedTask.preset && ` · ${selectedTask.preset}`}
          </div>

        </div>
      )}

      {/* Mode D: Nothing selected — overview + compact role summary */}
      {mode === 'overview' && (
        <div>
          {stats && (
            <div>
              <div style={{ fontSize: 9, color: '#555', textTransform: 'uppercase', marginBottom: 6, letterSpacing: 1 }}>
                overview
              </div>
              {[
                { label: 'Total Tasks', value: stats.totalTasks },
                { label: 'Running', value: stats.runningTasks },
                { label: 'Completed', value: stats.completedTasks },
                { label: 'Failed', value: stats.failedTasks },
                { label: 'Success Rate', value: `${(stats.successRate * 100).toFixed(0)}%` },
              ].map(({ label, value }) => (
                <div key={label} style={{
                  display: 'flex', justifyContent: 'space-between',
                  padding: '3px 0', fontSize: 10,
                }}>
                  <span style={{ color: '#888' }}>{label}</span>
                  <span style={{ color: '#ccc' }}>{value}</span>
                </div>
              ))}
            </div>
          )}

          {/* MARKER_143.P6I: Compact read-only role summary — click agent node in DAG to edit */}
          <RolesSummary activePreset={activePreset} />

          <div style={{ marginTop: 8, fontSize: 8, color: '#444', textAlign: 'center' }}>
            click agent node in DAG to edit role
          </div>
        </div>
      )}

      {/* MARKER_151.9: Compact stats preview (same component as Stats tab) */}
      <div style={{ marginTop: 10, paddingTop: 10, borderTop: `1px solid ${NOLAN_PALETTE.borderDim}` }}>
        <PipelineStats tasks={tasks} mode="compact" />
      </div>

      {/* MARKER_151.8: Compact architect chat (same component as Architect tab) */}
      <div data-onboarding="architect-chat" style={{ marginTop: 10, paddingTop: 10, borderTop: `1px solid ${NOLAN_PALETTE.borderDim}`, minHeight: 230, maxHeight: 320 }}>
        <ArchitectChat mode="compact" />
      </div>
    </div>
  );
}
