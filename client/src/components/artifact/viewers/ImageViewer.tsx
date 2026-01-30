/**
 * ImageViewer - Zoomable image viewer with pan and pinch controls.
 * Uses react-zoom-pan-pinch for transform interactions.
 *
 * @status active
 * @phase 96
 * @depends react, react-zoom-pan-pinch, lucide-react
 * @used_by ArtifactPanel
 */

import { useState } from 'react';
import { TransformWrapper, TransformComponent, useControls } from 'react-zoom-pan-pinch';
import { ZoomIn, ZoomOut, RotateCcw, AlertCircle } from 'lucide-react';

interface Props {
  url: string;
  filename: string;
}

function Controls() {
  const { zoomIn, zoomOut, resetTransform } = useControls();

  const btnStyle = {
    padding: 8,
    background: 'transparent',
    border: 'none',
    borderRadius: 4,
    color: '#888',
    cursor: 'pointer',
  };

  return (
    <div style={{
      position: 'absolute',
      bottom: 16,
      left: '50%',
      transform: 'translateX(-50%)',
      display: 'flex',
      gap: 8,
      padding: 8,
      background: 'rgba(20, 20, 20, 0.9)',
      border: '1px solid #333',
      borderRadius: 8,
    }}>
      <button onClick={() => zoomIn()} style={btnStyle} title="Zoom In">
        <ZoomIn size={18} />
      </button>
      <button onClick={() => zoomOut()} style={btnStyle} title="Zoom Out">
        <ZoomOut size={18} />
      </button>
      <button onClick={() => resetTransform()} style={btnStyle} title="Reset">
        <RotateCcw size={18} />
      </button>
    </div>
  );
}

export function ImageViewer({ url, filename }: Props) {
  const [error, setError] = useState(false);

  if (error) {
    return (
      <div style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#0a0a0a',
        padding: 16
      }}>
        <AlertCircle size={48} color="#ef4444" style={{ marginBottom: 16 }} />
        <p style={{ color: '#e0e0e0', marginBottom: 8 }}>Failed to load image</p>
        <p style={{ color: '#666', fontSize: 12 }}>{filename}</p>
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', height: '100%', background: '#0a0a0a' }}>
      <TransformWrapper
        initialScale={1}
        minScale={0.1}
        maxScale={10}
        wheel={{ step: 0.1 }}
        doubleClick={{ mode: 'reset' }}
      >
        <TransformComponent
          wrapperStyle={{ width: '100%', height: '100%' }}
          contentStyle={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        >
          <img
            src={url}
            alt={filename}
            onError={() => {
              console.error('[ImageViewer] Failed to load:', url);
              setError(true);
            }}
            style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
            draggable={false}
          />
        </TransformComponent>
        <Controls />
      </TransformWrapper>
    </div>
  );
}
