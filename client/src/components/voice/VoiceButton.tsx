/**
 * VoiceButton - Microphone button with wave animation and STT.
 * Supports compact mode for inline use and full mode with wave display.
 *
 * @status active
 * @phase 96
 * @depends react, lucide-react, VoiceWave, api.config, Socket.IO
 * @used_by MessageInput
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { Mic, MicOff, Volume2, Loader2 } from 'lucide-react';
import { VoiceWave } from './VoiceWave';
import { getSocketUrl } from '../../config/api.config';

interface VoiceButtonProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
  compact?: boolean; // For MessageInput integration
}

// Socket.IO types
interface VoiceSocket {
  emit: (event: string, data?: any) => void;
  on: (event: string, callback: (data: any) => void) => void;
  off: (event: string, callback?: (data: any) => void) => void;
  connected: boolean;
}

export function VoiceButton({
  onTranscript,
  disabled = false,
  compact = false,
}: VoiceButtonProps) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [intensity, setIntensity] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const socketRef = useRef<VoiceSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Get socket from global or create connection
  useEffect(() => {
    // Access socket.io client from window (set by useSocket hook)
    const getSocket = () => {
      if (typeof window !== 'undefined' && (window as any).io) {
        const io = (window as any).io;
        // Connect to same server as main socket
        const socketUrl = getSocketUrl();
        socketRef.current = io(socketUrl, {
          transports: ['websocket', 'polling'],
          reconnection: true,
        });
      }
    };

    getSocket();

    return () => {
      if (socketRef.current) {
        socketRef.current.off('voice_transcribed');
        socketRef.current.off('voice_status');
        socketRef.current.off('voice_error');
      }
    };
  }, []);

  // Socket event listeners
  useEffect(() => {
    const socket = socketRef.current;
    if (!socket) return;

    const handleTranscribed = (data: { text: string; final: boolean }) => {
      if (data.text) {
        onTranscript(data.text);
      }
      setIsProcessing(false);
    };

    const handleStatus = (data: { status: string }) => {
      if (data.status === 'speaking') {
        setIsSpeaking(true);
      } else if (data.status === 'idle') {
        setIsSpeaking(false);
        setIsListening(false);
      } else if (data.status === 'listening') {
        setIsListening(true);
      }
    };

    const handleError = (data: { error: string }) => {
      setError(data.error);
      setIsProcessing(false);
      setIsListening(false);
      setTimeout(() => setError(null), 3000);
    };

    socket.on('voice_transcribed', handleTranscribed);
    socket.on('voice_status', handleStatus);
    socket.on('voice_error', handleError);

    return () => {
      socket.off('voice_transcribed', handleTranscribed);
      socket.off('voice_status', handleStatus);
      socket.off('voice_error', handleError);
    };
  }, [onTranscript]);

  // Audio level analysis for wave intensity
  const analyzeAudio = useCallback((stream: MediaStream) => {
    try {
      audioContextRef.current = new AudioContext();
      analyserRef.current = audioContextRef.current.createAnalyser();
      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);

      analyserRef.current.fftSize = 256;
      const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);

      const updateIntensity = () => {
        if (!analyserRef.current || !isListening) {
          setIntensity(0);
          return;
        }

        analyserRef.current.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
        setIntensity(Math.min(1, average / 128));

        animationFrameRef.current = requestAnimationFrame(updateIntensity);
      };

      updateIntensity();
    } catch (e) {
      console.error('[Voice] Audio analysis error:', e);
    }
  }, [isListening]);

  const startListening = useCallback(async () => {
    if (disabled || isListening || isProcessing) return;

    setError(null);

    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      streamRef.current = stream;

      // Start audio analysis for wave animation
      analyzeAudio(stream);

      // Create MediaRecorder
      const mimeType = MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : 'audio/mp4';

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      const chunks: Blob[] = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        setIsProcessing(true);

        // Create blob from chunks
        const blob = new Blob(chunks, { type: mimeType });

        // Convert to base64
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64 = (reader.result as string).split(',')[1];

          // Send to backend for STT
          if (socketRef.current?.connected) {
            socketRef.current.emit('voice_audio', {
              audio: base64,
              final: true,
            });
          } else {
            // Fallback: use Web Speech API if available
            fallbackWebSpeechSTT();
          }
        };
        reader.readAsDataURL(blob);

        // Cleanup stream
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      };

      // Start recording
      mediaRecorder.start();
      setIsListening(true);

      // Notify backend
      socketRef.current?.emit('voice_start');

    } catch (err) {
      console.error('[Voice] Mic access denied:', err);
      setError('Microphone access denied');
    }
  }, [disabled, isListening, isProcessing, analyzeAudio]);

  const stopListening = useCallback(() => {
    if (!isListening || !mediaRecorderRef.current) return;

    // Stop recording
    mediaRecorderRef.current.stop();
    setIsListening(false);
    setIntensity(0);

    // Cancel animation frame
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // Notify backend
    socketRef.current?.emit('voice_stop');
  }, [isListening]);

  // Fallback: Web Speech API for browsers that support it
  const fallbackWebSpeechSTT = useCallback(() => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      setError('Speech recognition not supported');
      setIsProcessing(false);
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      onTranscript(transcript);
      setIsProcessing(false);
    };

    recognition.onerror = (event: any) => {
      console.error('[Voice] Web Speech error:', event.error);
      setError('Speech recognition failed');
      setIsProcessing(false);
    };

    recognition.onend = () => {
      setIsProcessing(false);
    };

    recognition.start();
  }, [onTranscript]);

  const mode = isListening ? 'listening' : isSpeaking ? 'speaking' : 'idle';
  const isActive = isListening || isSpeaking;

  // Compact mode for inline use
  if (compact) {
    return (
      <button
        onClick={isListening ? stopListening : startListening}
        disabled={disabled || isSpeaking || isProcessing}
        style={{
          width: 36,
          height: 36,
          borderRadius: '50%',
          border: 'none',
          background: isListening ? '#1a3a5c' : '#2a2a2a',
          color: isListening ? '#4a9eff' : '#666',
          cursor: disabled ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.2s ease',
          boxShadow: isListening ? '0 0 12px rgba(74, 158, 255, 0.4)' : 'none',
          opacity: disabled ? 0.5 : 1,
        }}
        title={isListening ? 'Stop recording' : 'Voice input'}
      >
        {isProcessing ? (
          <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />
        ) : isListening ? (
          <MicOff size={18} />
        ) : (
          <Mic size={18} />
        )}
      </button>
    );
  }

  // Full mode with wave animation
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '8px 12px',
        background: isActive ? '#0f0f0f' : 'transparent',
        borderRadius: 8,
        transition: 'background 0.3s ease',
      }}
    >
      {/* Wave Animation */}
      <VoiceWave
        isActive={isActive}
        mode={mode}
        intensity={intensity}
        width={compact ? 80 : 120}
        height={compact ? 30 : 40}
      />

      {/* Mic Button */}
      <button
        onClick={isListening ? stopListening : startListening}
        disabled={disabled || isSpeaking || isProcessing}
        style={{
          width: 48,
          height: 48,
          borderRadius: '50%',
          border: 'none',
          background: isListening ? '#1a3a5c' : '#1a1a1a',
          color: isListening ? '#4a9eff' : '#888',
          cursor: disabled ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.2s ease',
          boxShadow: isListening ? '0 0 20px rgba(74, 158, 255, 0.5)' : 'none',
          opacity: disabled ? 0.5 : 1,
        }}
        title={isListening ? 'Stop recording' : 'Start voice input'}
      >
        {isProcessing ? (
          <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
        ) : isListening ? (
          <MicOff size={24} />
        ) : (
          <Mic size={24} />
        )}
      </button>

      {/* Speaking indicator */}
      {isSpeaking && (
        <Volume2
          size={20}
          style={{
            color: '#4aff9e',
            animation: 'pulse 1s infinite',
          }}
        />
      )}

      {/* Error message */}
      {error && (
        <span
          style={{
            fontSize: 11,
            color: '#f44',
            background: '#2a1a1a',
            padding: '4px 8px',
            borderRadius: 4,
          }}
        >
          {error}
        </span>
      )}

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100% {opacity:1} 50% {opacity:0.5} }
      `}</style>
    </div>
  );
}

export default VoiceButton;
