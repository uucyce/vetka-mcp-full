/**
 * MARKER_C23D: AgentStatusBar — Multi-agent status display.
 * Shows active agents (Dragon, Cursor, etc.) with their current task.
 * Style: Nolan monochrome, compact horizontal bar.
 *
 * @status active
 * @phase 131
 * @depends react
 * @used_by DevPanel
 */

import { useState, useEffect, useCallback } from 'react';

interface AgentStatus {
  agent_name: string;
  agent_type: string;
  task_id: string;
  task_title: string;
  status: string;
  elapsed_seconds: number;
  phase_type?: string;
  subtasks_completed?: number;
  subtasks_total?: number;
}

const API_BASE = 'http://localhost:5001/api/debug';

// Agent icons (simple text, no emoji as per Nolan style)
const AGENT_ICONS: Record<string, string> = {
  dragon: '◆',
  cursor: '◇',
  titan: '▲',
  claude: '●',
  grok: '★',
  default: '○',
};

// Nolan palette
const COLORS = {
  bg: '#0a0a0a',
  border: '#1a1a1a',
  text: '#888',
  textActive: '#e0e0e0',
  textDim: '#444',
  pulse: '#666',
};

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

export function AgentStatusBar() {
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchAgents = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/task-board/active-agents`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setAgents(data.agents || []);
        }
      }
    } catch {
      // Silent fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
    const interval = setInterval(fetchAgents, 5000);
    return () => clearInterval(interval);
  }, [fetchAgents]);

  if (agents.length === 0 && !loading) {
    return null;  // Hide when no active agents
  }

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 16,
      padding: '6px 10px',
      background: COLORS.bg,
      borderTop: `1px solid ${COLORS.border}`,
      fontSize: 10,
      fontFamily: 'monospace',
      color: COLORS.text,
      overflowX: 'auto',
      whiteSpace: 'nowrap',
    }}>
      {agents.map((agent, idx) => {
        const icon = AGENT_ICONS[agent.agent_type?.toLowerCase()] || AGENT_ICONS.default;
        const isRunning = agent.status === 'running';

        return (
          <div
            key={idx}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            {/* Agent icon with pulse animation if running */}
            <span style={{
              color: isRunning ? COLORS.textActive : COLORS.textDim,
              animation: isRunning ? 'agentPulse 1.5s ease-in-out infinite' : 'none',
            }}>
              {icon}
            </span>

            {/* Agent name */}
            <span style={{
              color: isRunning ? COLORS.textActive : COLORS.text,
              fontWeight: isRunning ? 500 : 400,
            }}>
              {agent.agent_name || agent.agent_type}:
            </span>

            {/* Task info */}
            <span style={{
              color: COLORS.text,
              maxWidth: 150,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              {agent.task_id?.slice(0, 12)}
            </span>

            {/* Phase type */}
            {agent.phase_type && (
              <span style={{
                color: COLORS.textDim,
                padding: '0 4px',
                background: 'rgba(255,255,255,0.03)',
                borderRadius: 2,
              }}>
                {agent.phase_type}
              </span>
            )}

            {/* Subtask progress */}
            {agent.subtasks_total && agent.subtasks_total > 0 && (
              <span style={{ color: COLORS.textDim }}>
                {agent.subtasks_completed || 0}/{agent.subtasks_total}
              </span>
            )}

            {/* Elapsed time */}
            {isRunning && (
              <span style={{ color: COLORS.textDim }}>
                {formatElapsed(agent.elapsed_seconds)}
              </span>
            )}

            {/* Separator between agents */}
            {idx < agents.length - 1 && (
              <span style={{ color: COLORS.textDim, marginLeft: 8 }}>|</span>
            )}
          </div>
        );
      })}

      {/* Keyframe animation */}
      <style>{`
        @keyframes agentPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}
