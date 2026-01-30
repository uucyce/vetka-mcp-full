import { useEffect, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';
import { Play, Pause, SkipBack, SkipForward } from 'lucide-react';
import { AlertCircle } from 'lucide-react';

interface Props {
  url: string;
  filename: string;
}

export function AudioWaveform({ url, filename }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState('0:00');
  const [duration, setDuration] = useState('0:00');
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const formatTime = (seconds: number) => {
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `${min}:${sec.toString().padStart(2, '0')}`;
  };

  useEffect(() => {
    if (!containerRef.current) return;

    // ✅ Destroy previous instance if exists (prevent memory leaks)
    if (wavesurferRef.current) {
      wavesurferRef.current.destroy();
      wavesurferRef.current = null;
    }

    setIsReady(false);
    setError(null);

    try {
      const ws = WaveSurfer.create({
        container: containerRef.current,
        waveColor: '#666666',
        progressColor: '#3b82f6',
        cursorColor: '#ffffff',
        barWidth: 2,
        barGap: 1,
        barRadius: 2,
        height: 80,
        normalize: true,
      });

      wavesurferRef.current = ws;

      ws.on('ready', () => {
        setDuration(formatTime(ws.getDuration()));
        setIsReady(true);
      });

      ws.on('audioprocess', () => {
        setCurrentTime(formatTime(ws.getCurrentTime()));
      });

      ws.on('play', () => setIsPlaying(true));
      ws.on('pause', () => setIsPlaying(false));
      ws.on('error', (err) => {
        console.error('[AudioWaveform] Error:', err);
        setError('Failed to load audio file');
      });

      ws.load(url);
    } catch (err) {
      console.error('[AudioWaveform] Init error:', err);
      setError('Failed to initialize audio player');
    }

    // ✅ CLEANUP - destroy on unmount or URL change (prevent memory leaks)
    return () => {
      if (wavesurferRef.current) {
        wavesurferRef.current.destroy();
        wavesurferRef.current = null;
      }
    };
  }, [url]);

  if (error) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-vetka-bg p-4">
        <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
        <p className="text-vetka-text mb-2">Failed to load audio</p>
        <p className="text-vetka-muted text-sm">{error}</p>
      </div>
    );
  }

  const togglePlay = () => wavesurferRef.current?.playPause();
  const skipBack = () => wavesurferRef.current?.skip(-10);
  const skipForward = () => wavesurferRef.current?.skip(10);

  return (
    <div className="h-full flex flex-col items-center justify-center bg-vetka-bg p-6">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-4">
          <span className="text-vetka-muted text-sm">{filename}</span>
        </div>

        <div ref={containerRef} className="w-full mb-4 cursor-pointer" />

        <div className="flex justify-between text-xs text-vetka-muted mb-4">
          <span>{currentTime}</span>
          <span>{duration}</span>
        </div>

        <div className="flex items-center justify-center gap-4">
          <button onClick={skipBack} className="p-3 hover:bg-vetka-border rounded-full text-vetka-muted hover:text-white transition-colors">
            <SkipBack size={24} />
          </button>
          <button onClick={togglePlay} className="p-4 bg-vetka-accent hover:bg-blue-600 rounded-full text-white transition-colors">
            {isPlaying ? <Pause size={28} /> : <Play size={28} className="ml-1" />}
          </button>
          <button onClick={skipForward} className="p-3 hover:bg-vetka-border rounded-full text-vetka-muted hover:text-white transition-colors">
            <SkipForward size={24} />
          </button>
        </div>
      </div>
    </div>
  );
}
