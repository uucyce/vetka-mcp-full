/**
 * File preview component displaying selected file content with code viewer.
 * Supports multiple file types with demo fallback content.
 *
 * @status active
 * @phase 96
 * @depends react, ./Panel, ./viewers/CodeViewer, ../../store/useStore
 * @used_by ./App (currently unused - artifact panel preferred)
 */
// Phase 27.14: Renamed from ChatPanel to FilePreview (file preview component)
import { useState, useEffect, useCallback } from 'react';
import { Panel } from './Panel';
import { CodeViewer } from './viewers/CodeViewer';
import { useStore } from '../../store/useStore';

export function FilePreview() {
  const selectedId = useStore((state) => state.selectedId);
  const nodes = useStore((state) => state.nodes);
  const [content, setContent] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedNode = selectedId ? nodes[selectedId] : null;

  // Fetch file content when selection changes
  useEffect(() => {
    if (!selectedNode || selectedNode.type === 'folder') {
      setContent(null);
      return;
    }

    const fetchContent = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `/api/files/read?path=${encodeURIComponent(selectedNode.path)}`
        );
        if (!response.ok) throw new Error('Failed to load file');
        const data = await response.json();
        setContent(data.content);
      } catch {
        // Demo mode fallback
        setContent(getDemoContent(selectedNode.name, selectedNode.path));
        setError(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchContent();
  }, [selectedNode]);

  const handleCopyPath = useCallback(() => {
    if (selectedNode) {
      navigator.clipboard.writeText(selectedNode.path);
    }
  }, [selectedNode]);

  return (
    <Panel title="File Preview" position="left" defaultWidth={400} defaultCollapsed={true}>
      {selectedNode ? (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          {/* File header */}
          <div style={{ marginBottom: 16 }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                marginBottom: 8,
              }}
            >
              <span style={{ fontSize: 24 }}>
                {selectedNode.type === 'folder' ? '\uD83D\uDCC1' : '\uD83D\uDCC4'}
              </span>
              <div>
                <div
                  style={{
                    color: '#e0e0e0',
                    fontSize: 14,
                    fontWeight: 600,
                    wordBreak: 'break-word',
                  }}
                >
                  {selectedNode.name}
                </div>
                <div style={{ color: '#666', fontSize: 11 }}>{selectedNode.path}</div>
              </div>
            </div>

            {/* Metadata badges - monochrome */}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <span
                style={{
                  padding: '2px 8px',
                  borderRadius: 4,
                  background: '#333',
                  color: '#999',
                  fontSize: 11,
                }}
              >
                {selectedNode.backendType}
              </span>
              <span
                style={{
                  padding: '2px 8px',
                  borderRadius: 4,
                  background: '#444',
                  color: '#ccc',
                  fontSize: 11,
                }}
              >
                depth {selectedNode.depth}
              </span>
              {selectedNode.extension && (
                <span
                  style={{
                    padding: '2px 8px',
                    borderRadius: 4,
                    background: '#555',
                    color: '#ddd',
                    fontSize: 11,
                  }}
                >
                  .{selectedNode.extension}
                </span>
              )}
            </div>
          </div>

          {/* Content viewer */}
          <div style={{ flex: 1, minHeight: 0 }}>
            {isLoading ? (
              <div style={{ color: '#888', textAlign: 'center', padding: 40 }}>
                Loading...
              </div>
            ) : selectedNode.type === 'folder' ? (
              <div
                style={{
                  color: '#666',
                  textAlign: 'center',
                  padding: 40,
                  background: '#1a1a1a',
                  borderRadius: 8,
                }}
              >
                <div style={{ fontSize: 48, marginBottom: 16 }}>{'\uD83D\uDCC1'}</div>
                <div>Folder selected</div>
                <div style={{ fontSize: 12, marginTop: 8 }}>
                  Select a file to preview content
                </div>
              </div>
            ) : content ? (
              <CodeViewer content={content} fileName={selectedNode.name} />
            ) : (
              <div style={{ color: '#888', textAlign: 'center', padding: 40 }}>
                {error || 'No content available'}
              </div>
            )}
          </div>

          {/* Actions */}
          <div
            style={{
              marginTop: 16,
              display: 'flex',
              gap: 8,
              borderTop: '1px solid #333',
              paddingTop: 16,
            }}
          >
            <button
              onClick={handleCopyPath}
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: 6,
                border: '1px solid #444',
                background: 'transparent',
                color: '#888',
                cursor: 'pointer',
                fontSize: 12,
              }}
            >
              Copy Path
            </button>
            <button
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: 6,
                border: '1px solid #444',
                background: 'transparent',
                color: '#888',
                cursor: 'pointer',
                fontSize: 12,
              }}
            >
              Ask Agent
            </button>
          </div>
        </div>
      ) : (
        <div
          style={{
            textAlign: 'center',
            color: '#666',
            padding: 40,
          }}
        >
          <div style={{ fontSize: 48, marginBottom: 16 }}>{'\uD83D\uDC46'}</div>
          <div>Select a file or folder</div>
          <div style={{ fontSize: 12, marginTop: 8 }}>Click on any card in the 3D view</div>
        </div>
      )}
    </Panel>
  );
}

function getDemoContent(name: string, path: string): string {
  const ext = name.split('.').pop()?.toLowerCase();

  if (ext === 'py') {
    return `# ${name}
# Path: ${path}

def main():
    """Main entry point"""
    print("Hello from ${name}")

if __name__ == "__main__":
    main()
`;
  }

  if (ext === 'tsx' || ext === 'jsx') {
    return `// ${name}
// Path: ${path}

import React from 'react';

export function Component() {
  return (
    <div>
      <h1>Hello from ${name}</h1>
    </div>
  );
}
`;
  }

  if (ext === 'ts' || ext === 'js') {
    return `// ${name}
// Path: ${path}

export function main() {
  // console.log('Hello from ${name}');
}

main();
`;
  }

  if (ext === 'json') {
    return `{
  "name": "${name}",
  "path": "${path}",
  "demo": true
}`;
  }

  if (ext === 'md') {
    return `# ${name}

> Path: ${path}

This is demo content for the markdown file.

## Features

- Feature 1
- Feature 2
- Feature 3
`;
  }

  return `// Demo content for ${name}
// File: ${path}

// This is placeholder content shown in demo mode
// Connect to Flask backend to see actual file content
`;
}
