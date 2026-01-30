/**
 * useJarvis Hook - Jarvis Voice Interface
 * MARKER_104.5
 *
 * React hook for managing Jarvis voice interactions:
 * - Speech recognition via microphone
 * - Real-time audio streaming to backend
 * - State management for listening/thinking/speaking
 * - Audio playback from Jarvis responses
 * - Visual feedback via audio levels
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';

// Jarvis state machine
type JarvisState = 'idle' | 'listening' | 'thinking' | 'speaking';

interface UseJarvisReturn {
  state: JarvisState;
  transcript: string;
  response: string;
  audioLevel: number;
  error: string | null;
  startListening: () => Promise<void>;
  stopListening: () => void;
  toggle: () => Promise<void>;
  isListening: boolean;
}

// Audio processing configuration
const SAMPLE_RATE = 16000; // 16kHz for Whisper
const CHUNK_SIZE = 4096;
const SMOOTHING_FACTOR = 0.3; // For audio level smoothing

export const useJarvis = (): UseJarvisReturn => {
  // State management
  const [state, setState] = useState<JarvisState>('idle');
  const [transcript, setTranscript] = useState<string>('');
  const [response, setResponse] = useState<string>('');
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  // Refs for persistent values
  const socketRef = useRef<Socket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const audioSourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const smoothedLevelRef = useRef<number>(0);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const conversationActiveRef = useRef<boolean>(false);  // Track if in conversation mode

  // Initialize socket connection
  useEffect(() => {
    const socket = io(import.meta.env.VITE_API_URL || 'http://localhost:5001', {
      transports: ['websocket'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5,
    });

    socketRef.current = socket;

    // Socket event listeners
    socket.on('connect', () => {
      console.log('Jarvis socket connected');
      setError(null);
    });

    socket.on('disconnect', () => {
      console.log('Jarvis socket disconnected');
      cleanup();
      setState('idle');
      setAudioLevel(0);
    });

    // Backend sends objects with state/user_id, extract the value
    socket.on('jarvis_state', (data: { state: JarvisState; user_id?: string }) => {
      console.log('Jarvis state:', data);
      setState(data.state);
    });

    socket.on('jarvis_transcript', (data: { text: string; user_id?: string }) => {
      console.log('Jarvis transcript:', data);
      setTranscript(data.text);
    });

    socket.on('jarvis_response', (data: { text: string; user_id?: string }) => {
      console.log('Jarvis response:', data);
      setResponse(data.text);
    });

    socket.on('jarvis_audio', async (data: { audio: string; format: string; user_id?: string }) => {
      console.log('Jarvis audio received:', data.audio?.length, 'chars base64, format:', data.format);
      // Decode base64 to ArrayBuffer
      const binaryString = atob(data.audio);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      await playAudio(bytes.buffer, data.format || 'wav');
    });

    socket.on('jarvis_error', (data: { error: string; event?: string }) => {
      console.error('Jarvis error:', data);
      setError(data.error);
      cleanup();
      setState('idle');
      setAudioLevel(0);
    });

    // VAD auto-stop: Backend detected silence after speech
    socket.on('jarvis_auto_stop', (data: { user_id: string; silence_duration: number }) => {
      console.log('Jarvis auto-stop triggered:', data);
      // Cleanup audio capture (backend already processing)
      cleanup();
      setAudioLevel(0);
      // State will be updated by jarvis_state event from backend
    });

    // Cleanup on unmount
    return () => {
      socket.disconnect();
      cleanup();
    };
  }, []);

  /**
   * Calculate audio level from PCM data
   */
  const calculateAudioLevel = (data: Float32Array): number => {
    let sum = 0;
    for (let i = 0; i < data.length; i++) {
      sum += data[i] * data[i];
    }
    const rms = Math.sqrt(sum / data.length);
    // Apply smoothing
    smoothedLevelRef.current =
      smoothedLevelRef.current * (1 - SMOOTHING_FACTOR) +
      rms * SMOOTHING_FACTOR;
    return Math.min(smoothedLevelRef.current * 10, 1); // Scale and clamp
  };

  /**
   * Convert Float32Array to Int16Array for backend
   */
  const float32ToInt16 = (buffer: Float32Array): Int16Array => {
    const int16 = new Int16Array(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
      const s = Math.max(-1, Math.min(1, buffer[i]));
      int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return int16;
  };

  /**
   * Start listening for user speech
   */
  const startListening = useCallback(async (): Promise<void> => {
    try {
      setError(null);

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: SAMPLE_RATE,
        },
      });

      mediaStreamRef.current = stream;

      // Create audio context
      const audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      audioSourceRef.current = source;

      // Create script processor for audio chunks
      const processor = audioContext.createScriptProcessor(CHUNK_SIZE, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e: AudioProcessingEvent) => {
        const inputData = e.inputBuffer.getChannelData(0);

        // Calculate and update audio level
        const level = calculateAudioLevel(inputData);
        setAudioLevel(level);

        // Convert to Int16 and send to backend
        const int16Data = float32ToInt16(inputData);

        if (socketRef.current?.connected) {
          socketRef.current.emit('jarvis_audio_chunk', {
            audio: int16Data.buffer,
            sample_rate: SAMPLE_RATE,
          });
        }
      };

      // Connect audio nodes
      source.connect(processor);
      processor.connect(audioContext.destination);

      // Emit start event with user_id
      if (socketRef.current?.connected) {
        socketRef.current.emit('jarvis_listen_start', { user_id: 'default_user' });
      }

      // Activate conversation mode
      conversationActiveRef.current = true;
      setState('listening');
      console.log('Jarvis listening started (conversation active)');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to access microphone';
      console.error('Start listening error:', err);
      setError(errorMsg);
      cleanup();
    }
  }, []);

  /**
   * Stop listening
   */
  const stopListening = useCallback((): void => {
    console.log('Jarvis listening stopped');

    // Emit stop event with user_id
    if (socketRef.current?.connected) {
      socketRef.current.emit('jarvis_listen_stop', { user_id: 'default_user' });
    }

    cleanup();
    setState('idle');
    setAudioLevel(0);
    smoothedLevelRef.current = 0;
  }, []);

  /**
   * End conversation completely
   */
  const endConversation = useCallback(() => {
    console.log('Ending Jarvis conversation');
    conversationActiveRef.current = false;
    cleanup();
    setState('idle');
    setAudioLevel(0);
    smoothedLevelRef.current = 0;
  }, []);

  /**
   * Toggle listening state
   * Handles all states: idle, listening, thinking, speaking
   * Click during active conversation = end conversation
   */
  const toggle = useCallback(async (): Promise<void> => {
    if (state === 'speaking') {
      // Stop playback and end conversation
      conversationActiveRef.current = false;
      if (playbackContextRef.current) {
        await playbackContextRef.current.close();
        playbackContextRef.current = null;
      }
      setState('idle');
      return;
    }
    if (state === 'thinking') {
      // End conversation even during thinking
      conversationActiveRef.current = false;
      console.log('Ending conversation during thinking');
      setState('idle');
      return;
    }
    if (state === 'listening') {
      // Click during listening = end conversation
      conversationActiveRef.current = false;
      stopListening();
    } else if (state === 'idle') {
      await startListening();
    }
  }, [state, startListening, stopListening]);

  /**
   * Cleanup audio resources
   */
  const cleanup = (): void => {
    // Stop processor
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current.onaudioprocess = null;
      processorRef.current = null;
    }

    // Stop audio source
    if (audioSourceRef.current) {
      audioSourceRef.current.disconnect();
      audioSourceRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // Stop media stream
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
  };

  /**
   * Play audio response from Jarvis
   * Supports both WAV (Qwen3-TTS) and MP3 (FastTTS) formats
   */
  const playAudio = async (audioData: ArrayBuffer, format: string = 'wav'): Promise<void> => {
    try {
      // Create or reuse playback context
      // Use default sample rate for MP3, fixed for WAV
      if (!playbackContextRef.current) {
        // MP3 uses standard 24kHz, WAV from Qwen3 uses 24kHz
        playbackContextRef.current = new AudioContext({ sampleRate: format === 'mp3' ? 24000 : 24000 });
      }

      const context = playbackContextRef.current;

      console.log(`Playing ${format} audio, ${audioData.byteLength} bytes`);

      // Decode audio data (Web Audio API handles both WAV and MP3)
      const audioBuffer = await context.decodeAudioData(audioData.slice(0));

      // Create buffer source
      const source = context.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(context.destination);

      // Play audio
      source.start(0);

      // Update state when done - auto-resume listening if in conversation
      source.onended = async () => {
        console.log('Jarvis audio playback finished');
        if (conversationActiveRef.current) {
          // Auto-resume listening for continuous conversation
          console.log('Auto-resuming listening...');
          setTimeout(() => {
            // Small delay before resuming to avoid feedback
            if (conversationActiveRef.current) {
              startListening();
            }
          }, 300);
        } else {
          setState('idle');
        }
      };

      setState('speaking');
    } catch (err) {
      console.error('Audio playback error:', err);
      setError('Failed to play audio response');
      setState('idle');
    }
  };

  return {
    state,
    transcript,
    response,
    audioLevel,
    error,
    startListening,
    stopListening,
    toggle,
    isListening: state === 'listening',
  };
};
