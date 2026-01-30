import { useState } from 'react';
import { AlertCircle } from 'lucide-react';

interface Props {
  url: string;
}

export function MediaViewer({ url }: Props) {
  const [error, setError] = useState<string | null>(null);

  if (error) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-vetka-bg p-4">
        <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
        <p className="text-vetka-text mb-2">Failed to load video</p>
        <p className="text-vetka-muted text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="h-full flex items-center justify-center bg-vetka-bg p-4">
      <video
        src={url}
        controls
        className="max-w-full max-h-full"
        style={{ backgroundColor: '#0a0a0a' }}
        onError={() => setError('Unable to play this video format')}
      />
    </div>
  );
}
