/**
 * MARKER_151.13: Pipeline Stats v2.
 * Per-agent cards + weak-link focus. Compact/expanded modes share same data path.
 */

import { useMemo } from 'react';
import { TaskData } from './TaskCard';
import { useDevPanelStore } from '../../store/useDevPanelStore';
import { resolveRolePreviewAsset, type MycoRolePreviewRole } from '../mcc/mycoRolePreview';

interface PipelineStatsProps {
  tasks: TaskData[];
  mode?: 'compact' | 'expanded';
  onRefresh?: () => void;
}

interface AgentStats {
  calls: number;
  tokens_in: number;
  tokens_out: number;
  duration_s: number;
  success_count: number;
  fail_count: number;
  retries?: number;
}

interface AgentAggregate {
  role: string;
  calls: number;
  tokensIn: number;
  tokensOut: number;
  durationS: number;
  successCount: number;
  failCount: number;
}

function normalizeRole(role: string): string {
  return role.toLowerCase().trim();
}

function roleLabel(role: string): string {
  const r = normalizeRole(role);
  if (r === 'architect') return 'ARCHITECT';
  if (r === 'researcher') return 'RESEARCHER';
  if (r === 'verifier') return 'VERIFIER';
  if (r === 'coder') return 'CODER';
  if (r === 'scout') return 'SCOUT';
  return role.toUpperCase();
}

function successColor(rate: number): string {
  if (rate >= 70) return '#4ecdc4';
  if (rate >= 50) return '#f0c040';
  return '#ff6666';
}

export function PipelineStats({ tasks, mode = 'expanded' }: PipelineStatsProps) {
  const setActiveTab = useDevPanelStore(s => s.setActiveTab);

  const {
    totalRuns,
    successRate,
    weakRole,
    weakRoleRate,
    avgAdjustedSuccess,
    totalAgentCalls,
    byRole,
    presetSummary,
  } = useMemo(() => {
    const doneTasks = tasks.filter(t => t.status === 'done' || t.status === 'failed');

    const roleMap: Record<string, AgentAggregate> = {};
    const presets: Record<string, { runs: number; successWeighted: number }> = {};

    let adjustedSum = 0;
    let adjustedCount = 0;

    for (const task of doneTasks) {
      const stats: any = task.stats || {};

      if (typeof stats.adjusted_success === 'number') {
        adjustedSum += stats.adjusted_success;
        adjustedCount += 1;
      }

      const preset = String(task.preset || stats.preset || 'unknown');
      if (!presets[preset]) presets[preset] = { runs: 0, successWeighted: 0 };
      presets[preset].runs += 1;
      presets[preset].successWeighted += typeof stats.adjusted_success === 'number'
        ? stats.adjusted_success
        : (task.status === 'done' ? 1 : 0);

      const agentStats = (stats.agent_stats || {}) as Record<string, AgentStats>;
      for (const [roleRaw, value] of Object.entries(agentStats)) {
        const role = normalizeRole(roleRaw);
        if (!roleMap[role]) {
          roleMap[role] = {
            role,
            calls: 0,
            tokensIn: 0,
            tokensOut: 0,
            durationS: 0,
            successCount: 0,
            failCount: 0,
          };
        }
        roleMap[role].calls += value.calls || 0;
        roleMap[role].tokensIn += value.tokens_in || 0;
        roleMap[role].tokensOut += value.tokens_out || 0;
        roleMap[role].durationS += value.duration_s || 0;
        roleMap[role].successCount += value.success_count || 0;
        roleMap[role].failCount += value.fail_count || 0;
      }
    }

    const byRoleList = Object.values(roleMap)
      .map((r) => {
        const totalAttempts = r.successCount + r.failCount;
        const rate = totalAttempts > 0 ? (r.successCount / totalAttempts) * 100 : 0;
        return {
          ...r,
          rate,
          avgDuration: r.calls > 0 ? (r.durationS / r.calls) : 0,
        };
      })
      .sort((a, b) => a.role.localeCompare(b.role));

    const weak = byRoleList.length > 0
      ? [...byRoleList].sort((a, b) => a.rate - b.rate)[0]
      : null;

    const successRuns = doneTasks.filter(t => t.status === 'done').length;
    const successPct = doneTasks.length > 0 ? Math.round((successRuns / doneTasks.length) * 100) : 0;

    const presetSummaryList = Object.entries(presets)
      .map(([preset, data]) => ({
        preset,
        runs: data.runs,
        success: data.runs > 0 ? Math.round((data.successWeighted / data.runs) * 100) : 0,
      }))
      .sort((a, b) => b.runs - a.runs);

    return {
      totalRuns: doneTasks.length,
      successRate: successPct,
      weakRole: weak?.role || '-',
      weakRoleRate: weak ? Math.round(weak.rate) : 0,
      avgAdjustedSuccess: adjustedCount > 0 ? Math.round((adjustedSum / adjustedCount) * 100) : 0,
      totalAgentCalls: byRoleList.reduce((sum, r) => sum + r.calls, 0),
      byRole: byRoleList,
      presetSummary: presetSummaryList,
    };
  }, [tasks]);

  if (mode === 'compact') {
    return (
      <div style={{ border: '1px solid #222', borderRadius: 4, padding: 8, background: 'rgba(255,255,255,0.01)' }} data-onboarding="stats-compact">
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
          <span style={{ fontSize: 8, color: '#666', textTransform: 'uppercase', letterSpacing: 1 }}>stats</span>
          <button
            onClick={() => setActiveTab('stats')}
            style={{ marginLeft: 'auto', border: '1px solid #333', borderRadius: 2, background: 'transparent', color: '#999', fontFamily: 'monospace', fontSize: 9, padding: '1px 6px', cursor: 'pointer' }}
            title="Expand to Stats tab"
          >
            ↗
          </button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 6 }}>
          <StatBox label="Runs" value={String(totalRuns)} />
          <StatBox label="Success" value={`${successRate}%`} />
          <StatBox label="Weak" value={roleLabel(weakRole)} />
          <StatBox label="Adjusted" value={`${avgAdjustedSuccess}%`} />
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontSize: 10, color: '#bbb', textTransform: 'uppercase', letterSpacing: 1 }}>
          Team Stats v2
        </div>
        <button
          onClick={() => setActiveTab('mcc')}
          style={{ border: '1px solid #333', borderRadius: 2, background: 'transparent', color: '#999', fontFamily: 'monospace', fontSize: 9, padding: '1px 6px', cursor: 'pointer' }}
          title="Collapse back to MCC"
        >
          ↙
        </button>
      </div>

      <div style={{ border: '1px solid #222', borderRadius: 4, padding: 8, background: 'rgba(255,255,255,0.01)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, fontSize: 10 }}>
          <span style={{ color: '#aaa' }}>runs: <span style={{ color: '#fff' }}>{totalRuns}</span></span>
          <span style={{ color: '#aaa' }}>success: <span style={{ color: '#fff' }}>{successRate}%</span></span>
          <span style={{ color: '#aaa' }}>adjusted: <span style={{ color: '#fff' }}>{avgAdjustedSuccess}%</span></span>
          <span style={{ color: '#ff8a8a' }}>weak: <span style={{ color: '#fff' }}>{roleLabel(weakRole)} ({weakRoleRate}%)</span></span>
          <span style={{ color: '#aaa' }}>calls: <span style={{ color: '#fff' }}>{totalAgentCalls}</span></span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 8 }}>
        {byRole.length === 0 && (
          <div style={{ color: '#666', fontSize: 11, padding: 12, border: '1px solid #222', borderRadius: 4 }}>
            No agent stats yet. Complete at least one task run.
          </div>
        )}

        {byRole.map((row) => {
          const rateRounded = Math.round(row.rate);
          const barColor = successColor(rateRounded);
          const weakTint = rateRounded < 60 ? 'rgba(255,68,68,0.08)' : 'rgba(255,255,255,0.01)';
          const roleAvatarSrc = resolveRolePreviewAsset(
            normalizeRole(row.role) as MycoRolePreviewRole,
            row.role,
          );
          return (
            <div key={row.role} style={{ border: '1px solid #222', borderRadius: 4, padding: 8, background: weakTint }}>
              {/* MARKER_175.AVATAR: Role avatar + label */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                {roleAvatarSrc && (
                  <img
                    src={roleAvatarSrc}
                    alt={row.role}
                    style={{
                      width: 22,
                      height: 22,
                      borderRadius: 3,
                      objectFit: 'cover',
                      flexShrink: 0,
                      opacity: rateRounded < 60 ? 0.6 : 0.85,
                    }}
                  />
                )}
                <span style={{ fontSize: 9, color: '#ddd', fontWeight: 700 }}>
                  {roleLabel(row.role)}
                </span>
              </div>
              <div style={{ height: 8, background: '#1a1a1a', borderRadius: 999, overflow: 'hidden', marginBottom: 6 }}>
                <div style={{ width: `${Math.max(4, rateRounded)}%`, height: '100%', background: barColor }} />
              </div>
              <div style={{ fontSize: 9, color: '#aaa', marginBottom: 2 }}>success: <span style={{ color: '#fff' }}>{rateRounded}%</span></div>
              <div style={{ fontSize: 9, color: '#aaa', marginBottom: 2 }}>avg: <span style={{ color: '#fff' }}>{row.avgDuration.toFixed(1)}s</span></div>
              <div style={{ fontSize: 9, color: '#aaa', marginBottom: 2 }}>calls: <span style={{ color: '#fff' }}>{row.calls}</span></div>
              <div style={{ fontSize: 9, color: '#777' }}>tok: {row.tokensIn + row.tokensOut}</div>
            </div>
          );
        })}
      </div>

      {presetSummary.length > 0 && (
        <div style={{ border: '1px solid #222', borderRadius: 4, padding: 8 }}>
          <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase', marginBottom: 6 }}>team comparison</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {presetSummary.map((row) => (
              <div key={row.preset} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 10 }}>
                <span style={{ color: '#aaa', minWidth: 110 }}>{row.preset}</span>
                <div style={{ flex: 1, height: 6, background: '#1a1a1a', borderRadius: 999, overflow: 'hidden' }}>
                  <div style={{ width: `${Math.max(4, row.success)}%`, height: '100%', background: successColor(row.success) }} />
                </div>
                <span style={{ color: '#ddd', minWidth: 40, textAlign: 'right' }}>{row.success}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ border: '1px solid #222', borderRadius: 3, padding: '6px 7px', background: '#101010' }}>
      <div style={{ color: '#666', fontSize: 8, textTransform: 'uppercase', letterSpacing: 0.6, marginBottom: 4 }}>{label}</div>
      <div style={{ color: '#e0e0e0', fontSize: 11, fontWeight: 600 }}>{value}</div>
    </div>
  );
}
