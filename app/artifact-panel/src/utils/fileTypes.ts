export type ViewerType = 'code' | 'richtext' | 'markdown' | 'media' | 'audio' | 'image' | 'pdf' | '3d' | 'unknown';

const FILE_TYPES: Record<ViewerType, string[]> = {
  code: [
    '.js', '.jsx', '.ts', '.tsx', '.py', '.java', '.cpp', '.c', '.h', '.hpp',
    '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.sh', '.bash', '.zsh',
    '.sql', '.r', '.m', '.lua', '.perl', '.pl',
    '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.env', '.cfg',
    '.css', '.scss', '.less', '.html', '.vue', '.svelte',
    '.dockerfile', '.makefile', '.cmake'
  ],
  richtext: ['.txt'],
  markdown: ['.md', '.mdx', '.markdown'],
  media: ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.m4v', '.ogv', '.3gp'],
  audio: ['.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac', '.opus', '.wma'],
  image: ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico', '.avif', '.tiff'],
  pdf: ['.pdf'],
  '3d': ['.gltf', '.glb', '.obj', '.fbx', '.stl', '.3ds', '.dae'],
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
  
  return 'code';
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
