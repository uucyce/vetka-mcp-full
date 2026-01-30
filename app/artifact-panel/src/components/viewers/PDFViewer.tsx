import { useState } from 'react';
import { Viewer, Worker } from '@react-pdf-viewer/core';
import { defaultLayoutPlugin } from '@react-pdf-viewer/default-layout';
import { AlertCircle } from 'lucide-react';
import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/default-layout/lib/styles/index.css';

interface Props {
  url: string;
}

export function PDFViewer({ url }: Props) {
  const [error, setError] = useState<string | null>(null);
  const defaultLayoutPluginInstance = defaultLayoutPlugin({
    sidebarTabs: (defaultTabs) => [defaultTabs[0]],
  });

  if (error) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-vetka-bg p-4">
        <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
        <p className="text-vetka-text mb-2">Failed to load PDF</p>
        <p className="text-vetka-muted text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="h-full [&_.rpv-core__viewer]:bg-vetka-bg [&_.rpv-default-layout__toolbar]:bg-vetka-surface [&_.rpv-default-layout__sidebar]:bg-vetka-surface">
      <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
        <Viewer
          fileUrl={url}
          plugins={[defaultLayoutPluginInstance]}
          theme="dark"
          onDocumentLoad={() => setError(null)}
        />
      </Worker>
    </div>
  );
}
