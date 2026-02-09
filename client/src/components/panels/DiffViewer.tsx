/**
 * MARKER_128.4A: DiffViewer — Unified diff display component
 * Parses unified diff format, shows green additions / red removals.
 * No external dependencies — pure string parsing.
 *
 * @status active
 * @phase 128.4
 * @style Nolan dark (#1a3a1a green, #3a1a1a red, #181818 context)
 */

import { useMemo } from 'react';

interface DiffViewerProps {
  diff: string;
  maxHeight?: number;
}

interface DiffLine {
  type: 'add' | 'remove' | 'context' | 'header' | 'hunk';
  content: string;
  lineNum?: number;
}

// MARKER_128.4A: Parse unified diff into structured lines
function parseDiff(diff: string): DiffLine[] {
  if (!diff) return [];

  const lines = diff.split('\n');
  const result: DiffLine[] = [];
  let lineNum = 0;

  for (const line of lines) {
    if (line.startsWith('---') || line.startsWith('+++')) {
      // File headers
      result.push({ type: 'header', content: line });
    } else if (line.startsWith('@@')) {
      // Hunk header (e.g., @@ -42,6 +42,12 @@)
      result.push({ type: 'hunk', content: line });
      // Extract starting line number from hunk
      const match = line.match(/@@ -\d+(?:,\d+)? \+(\d+)/);
      if (match) {
        lineNum = parseInt(match[1], 10) - 1;
      }
    } else if (line.startsWith('+')) {
      // Added line
      lineNum++;
      result.push({ type: 'add', content: line.slice(1), lineNum });
    } else if (line.startsWith('-')) {
      // Removed line (no line number — it's from old file)
      result.push({ type: 'remove', content: line.slice(1) });
    } else if (line.startsWith(' ') || line === '') {
      // Context line
      lineNum++;
      result.push({ type: 'context', content: line.slice(1) || '', lineNum });
    }
  }

  return result;
}

// Line type styles — Nolan muted colors
const LINE_STYLES: Record<DiffLine['type'], { bg: string; color: string; prefix?: string }> = {
  add: { bg: '#1a3a1a', color: '#8a8', prefix: '+' },
  remove: { bg: '#3a1a1a', color: '#a88', prefix: '-' },
  context: { bg: '#181818', color: '#888', prefix: ' ' },
  header: { bg: '#252525', color: '#666', prefix: '' },
  hunk: { bg: '#1a1a2a', color: '#668', prefix: '' },
};

export function DiffViewer({ diff, maxHeight = 300 }: DiffViewerProps) {
  const lines = useMemo(() => parseDiff(diff), [diff]);

  if (!diff || lines.length === 0) {
    return (
      <div style={{
        background: '#181818',
        color: '#555',
        padding: '12px',
        borderRadius: 3,
        fontSize: 10,
        fontFamily: 'monospace',
        fontStyle: 'italic',
        border: '1px solid #222',
      }}>
        No diff available
      </div>
    );
  }

  return (
    <div style={{
      background: '#181818',
      borderRadius: 3,
      overflow: 'auto',
      maxHeight,
      fontSize: 10,
      fontFamily: 'monospace',
      border: '1px solid #222',
    }}>
      {lines.map((line, idx) => {
        const style = LINE_STYLES[line.type];
        const isCodeLine = line.type === 'add' || line.type === 'remove' || line.type === 'context';

        return (
          <div
            key={idx}
            style={{
              display: 'flex',
              background: style.bg,
              borderLeft: line.type === 'add'
                ? '2px solid #4a8a4a'
                : line.type === 'remove'
                  ? '2px solid #8a4a4a'
                  : '2px solid transparent',
            }}
          >
            {/* Line number gutter */}
            {isCodeLine && (
              <span style={{
                width: 36,
                padding: '1px 6px',
                textAlign: 'right',
                color: '#444',
                background: 'rgba(0,0,0,0.2)',
                userSelect: 'none',
                flexShrink: 0,
              }}>
                {line.lineNum || ''}
              </span>
            )}
            {/* Prefix (+/-/space) */}
            {isCodeLine && (
              <span style={{
                width: 14,
                padding: '1px 2px',
                textAlign: 'center',
                color: style.color,
                userSelect: 'none',
                flexShrink: 0,
                fontWeight: line.type !== 'context' ? 700 : 400,
              }}>
                {style.prefix}
              </span>
            )}
            {/* Content */}
            <span style={{
              flex: 1,
              padding: isCodeLine ? '1px 6px' : '2px 8px',
              color: style.color,
              whiteSpace: 'pre',
              overflow: 'hidden',
            }}>
              {line.content}
            </span>
          </div>
        );
      })}
    </div>
  );
}
