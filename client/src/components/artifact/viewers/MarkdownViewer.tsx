/**
 * MarkdownViewer - Renders markdown content with GFM support.
 * Uses react-markdown with remark-gfm for GitHub-flavored markdown.
 *
 * @status active
 * @phase 96
 * @depends react-markdown, remark-gfm
 * @used_by ArtifactPanel
 */

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  content: string;
}

export function MarkdownViewer({ content }: Props) {
  return (
    <div style={{
      height: '100%',
      overflow: 'auto',
      background: '#0a0a0a',
      padding: 24,
      color: '#e0e0e0',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      lineHeight: 1.6
    }}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ ...props }) => (
            <h1 style={{ fontSize: 28, fontWeight: 'bold', color: '#fff', marginBottom: 16 }} {...props} />
          ),
          h2: ({ ...props }) => (
            <h2 style={{ fontSize: 22, fontWeight: 'bold', color: '#fff', marginBottom: 12 }} {...props} />
          ),
          h3: ({ ...props }) => (
            <h3 style={{ fontSize: 18, fontWeight: 'bold', color: '#fff', marginBottom: 8 }} {...props} />
          ),
          p: ({ ...props }) => (
            <p style={{ marginBottom: 12 }} {...props} />
          ),
          code: ({ inline, ...props }: any) => inline
            ? <code style={{ background: '#1a1a1a', padding: '2px 6px', borderRadius: 4, fontSize: 13 }} {...props} />
            : <code style={{ display: 'block', background: '#1a1a1a', padding: 12, borderRadius: 8, overflow: 'auto', fontSize: 13, margin: '8px 0' }} {...props} />,
          blockquote: ({ ...props }) => (
            <blockquote style={{ borderLeft: '4px solid #333', paddingLeft: 16, fontStyle: 'italic', color: '#888', margin: '16px 0' }} {...props} />
          ),
          a: ({ ...props }) => (
            <a style={{ color: '#60a5fa', textDecoration: 'none' }} {...props} />
          ),
          ul: ({ ...props }) => (
            <ul style={{ paddingLeft: 24, marginBottom: 12 }} {...props} />
          ),
          ol: ({ ...props }) => (
            <ol style={{ paddingLeft: 24, marginBottom: 12 }} {...props} />
          ),
          li: ({ ...props }) => (
            <li style={{ marginBottom: 4 }} {...props} />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
