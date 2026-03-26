/**
 * MARKER_GAMMA-P2: Live encode + upload progress rows.
 * Monochrome progress bars — no color.
 */
import type { CSSProperties } from 'react';
import type { PublishJob } from './types';
import { PLATFORM_LABELS } from './types';

const ROW: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  padding: '6px 0',
  borderBottom: '1px solid #1a1a1a',
  fontSize: 11,
};

const BAR_BG: CSSProperties = {
  flex: 1,
  height: 4,
  background: '#222',
  borderRadius: 2,
  overflow: 'hidden',
};

const STATUS_COLORS: Record<string, string> = {
  pending: '#555',
  encoding: '#999',
  uploading: '#aaa',
  scheduled: '#888',
  done: '#ccc',
  error: '#666',
};

interface Props {
  jobs: PublishJob[];
}

export function PublishQueue({ jobs }: Props) {
  if (jobs.length === 0) return null;

  return (
    <div data-testid="publish-queue" style={{ marginTop: 12 }}>
      <div style={{ color: '#888', fontSize: 10, textTransform: 'uppercase', marginBottom: 6, letterSpacing: '0.5px' }}>
        Queue
      </div>
      {jobs.map((job) => {
        const progress = job.status === 'encoding'
          ? job.encodeProgress
          : job.status === 'uploading'
            ? job.uploadProgress
            : job.status === 'done' ? 1 : 0;

        return (
          <div key={job.id} style={ROW}>
            <span style={{ color: '#999', width: 70, flexShrink: 0 }}>
              {PLATFORM_LABELS[job.platform]}
            </span>
            <div style={BAR_BG}>
              <div style={{
                width: `${progress * 100}%`,
                height: '100%',
                background: STATUS_COLORS[job.status] ?? '#555',
                borderRadius: 2,
                transition: 'width 0.3s',
              }} />
            </div>
            <span style={{ color: '#666', width: 70, textAlign: 'right', flexShrink: 0 }}>
              {job.status === 'error' ? 'Error' :
               job.status === 'done' ? 'Done' :
               `${Math.round(progress * 100)}%`}
            </span>
          </div>
        );
      })}
    </div>
  );
}
