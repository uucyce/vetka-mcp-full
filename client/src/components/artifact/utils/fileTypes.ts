/**
 * File type utilities for determining viewer type and language.
 * Maps file extensions to viewer types and syntax highlighting languages.
 *
 * @status active
 * @phase 96
 * @depends none
 * @used_by ArtifactPanel, CodeViewer
 */

export type ViewerType = 'code' | 'markdown' | 'image' | 'unknown';

const FILE_TYPES: Record<ViewerType, string[]> = {
  code: [
    '.js', '.jsx', '.ts', '.tsx', '.py', '.java', '.cpp', '.c', '.h', '.hpp',
    '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.sh', '.bash', '.zsh',
    '.sql', '.r', '.m', '.lua', '.perl', '.pl',
    '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.env', '.cfg',
    '.css', '.scss', '.less', '.html', '.vue', '.svelte',
    '.dockerfile', '.makefile', '.cmake', '.txt'
  ],
  markdown: ['.md', '.mdx', '.markdown'],
  image: ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico', '.avif', '.tiff'],
  unknown: []
};

export function getViewerType(filename: string): ViewerType {
  if (!filename) return 'unknown';
  const ext = '.' + filename.split('.').pop()?.toLowerCase();

  for (const [type, extensions] of Object.entries(FILE_TYPES)) {
    if (extensions.includes(ext)) {
      return type as ViewerType;
    }
  }

  return 'code'; // Default to code viewer
}

export function getLanguage(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() || '';

  const langMap: Record<string, string> = {
    'js': 'javascript', 'jsx': 'javascript',
    'ts': 'typescript', 'tsx': 'typescript',
    'py': 'python',
    'json': 'json',
    'html': 'html',
    'css': 'css',
    'md': 'markdown',
    'yaml': 'yaml', 'yml': 'yaml',
    'sh': 'shell', 'bash': 'shell',
    'sql': 'sql',
    'go': 'go',
    'rs': 'rust',
    'cpp': 'cpp', 'c': 'cpp',
    'java': 'java',
    'rb': 'ruby',
    'php': 'php',
  };

  return langMap[ext] || ext;
}
