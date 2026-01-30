/**
 * Code viewer component with syntax language detection and monospace display.
 *
 * @status active
 * @phase 96
 * @depends none
 * @used_by ../FilePreview, ../../artifact/ArtifactWindow
 */
interface CodeViewerProps {
  content: string;
  language?: string;
  fileName?: string;
}

export function CodeViewer({ content, language, fileName }: CodeViewerProps) {
  const lang = language || getLanguageFromFileName(fileName);

  return (
    <div
      style={{
        background: '#1e1e1e',
        borderRadius: 8,
        overflow: 'auto',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div
        style={{
          padding: '8px 12px',
          borderBottom: '1px solid #333',
          fontSize: 12,
          color: '#888',
          flexShrink: 0,
        }}
      >
        {fileName || 'code'} &bull; {lang}
      </div>
      <pre
        style={{
          margin: 0,
          padding: 16,
          fontSize: 13,
          fontFamily: 'Monaco, Consolas, monospace',
          color: '#d4d4d4',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          overflow: 'auto',
          flex: 1,
        }}
      >
        <code>{content}</code>
      </pre>
    </div>
  );
}

function getLanguageFromFileName(fileName?: string): string {
  if (!fileName) return 'text';
  const ext = fileName.split('.').pop()?.toLowerCase();
  const langMap: Record<string, string> = {
    py: 'python',
    js: 'javascript',
    ts: 'typescript',
    tsx: 'typescript',
    jsx: 'javascript',
    md: 'markdown',
    json: 'json',
    html: 'html',
    css: 'css',
    yaml: 'yaml',
    yml: 'yaml',
    toml: 'toml',
    sh: 'shell',
    bash: 'shell',
    sql: 'sql',
    rs: 'rust',
    go: 'go',
    rb: 'ruby',
    php: 'php',
    java: 'java',
    kt: 'kotlin',
    swift: 'swift',
    c: 'c',
    cpp: 'cpp',
    h: 'c',
    hpp: 'cpp',
  };
  return langMap[ext || ''] || 'text';
}
