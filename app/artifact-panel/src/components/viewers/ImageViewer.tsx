import { useState } from 'react';
import { TransformWrapper, TransformComponent, useControls } from 'react-zoom-pan-pinch';
import { ZoomIn, ZoomOut, RotateCcw, AlertCircle } from 'lucide-react';

interface Props {
  url: string;
  filename: string;
}

function Controls() {
  const { zoomIn, zoomOut, resetTransform } = useControls();
  
  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2 p-2 
                    bg-vetka-surface/90 border border-vetka-border rounded-lg
                    opacity-0 group-hover:opacity-100 transition-opacity">
      <button onClick={() => zoomIn()} className="p-2 hover:bg-vetka-border rounded text-vetka-muted hover:text-white" title="Zoom In">
        <ZoomIn size={18} />
      </button>
      <button onClick={() => zoomOut()} className="p-2 hover:bg-vetka-border rounded text-vetka-muted hover:text-white" title="Zoom Out">
        <ZoomOut size={18} />
      </button>
      <button onClick={() => resetTransform()} className="p-2 hover:bg-vetka-border rounded text-vetka-muted hover:text-white" title="Reset">
        <RotateCcw size={18} />
      </button>
    </div>
  );
}

export function ImageViewer({ url, filename }: Props) {
  const [error, setError] = useState(false);

  if (error) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-vetka-bg p-4">
        <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
        <p className="text-vetka-text mb-2">Failed to load image</p>
        <p className="text-vetka-muted text-sm">{filename}</p>
      </div>
    );
  }

  return (
    <div className="relative h-full group bg-vetka-bg">
      <TransformWrapper initialScale={1} minScale={0.1} maxScale={10} wheel={{ step: 0.1 }} doubleClick={{ mode: 'reset' }}>
        <TransformComponent wrapperClass="!w-full !h-full" contentClass="!w-full !h-full flex items-center justify-center">
          <img 
            src={url} 
            alt={filename}
            onError={() => {
              console.error('[ImageViewer] Failed to load:', url);
              setError(true);
            }}
            className="max-w-full max-h-full object-contain" 
            draggable={false} 
          />
        </TransformComponent>
        <Controls />
      </TransformWrapper>
    </div>
  );
}
