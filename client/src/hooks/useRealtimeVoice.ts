/**
 * Real-time voice conversation hook with PCM streaming and VAD.
 * Supports voice activity detection, interruption, and TTS playback.
 *
 * @status active
 * @phase 96
 * @depends socket.io-client, AudioStreamManager
 * @used_by VoicePanel, ChatPanel
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { io, Socket } from 'socket.io-client';
import { AudioStreamManager, float32ToInt16 } from '../services/AudioStreamManager';
import { getSocketUrl } from '../config/api.config';

// Socket URL from config
const SOCKET_URL = getSocketUrl();

// Voice socket events
interface VoiceServerToClient {
  voice_status: (data: { status: string; provider?: string }) => void;
  voice_partial: (data: { text: string }) => void;
  voice_final: (data: { text: string; provider?: string }) => void;
  voice_llm_token: (data: { token: string }) => void;
  voice_model_speaking: (data: { speaking: boolean }) => void;
  voice_tts_chunk: (data: { audio: string; format?: string }) => void;
  voice_tts_browser: (data: { text: string }) => void;  // Fallback: use browser TTS
  voice_interrupted: (data: Record<string, never>) => void;
  voice_error: (data: { error: string }) => void;
  voice_providers: (data: { tts: Record<string, boolean>; stt: Record<string, boolean> }) => void;
}

interface VoiceClientToServer {
  voice_stream_start: () => void;
  voice_pcm: (data: { audio: number[]; sampleRate: number }) => void;
  voice_utterance_end: () => void;
  voice_stream_end: () => void;
  voice_interrupt: () => void;
  voice_config: (data: { model?: string; tts_voice?: string; stt_provider?: string; chat_mode?: boolean }) => void;
}

export interface UseRealtimeVoiceOptions {
  onTranscript?: (text: string, isFinal: boolean) => void;
  onLLMToken?: (token: string) => void;
  onModelSpeaking?: (isSpeaking: boolean) => void;
  onError?: (error: string) => void;
  // Voice config
  model?: string;           // LLM model to use
  ttsVoice?: string;        // TTS voice ID
  sttProvider?: string;     // STT provider (whisper/deepgram/openai)
  chatMode?: boolean;       // Chat input mode: STT only, no voice-router LLM/TTS
}

export interface VoiceState {
  isListening: boolean;      // Audio stream active
  isSpeaking: boolean;       // User speaking (VAD)
  isModelSpeaking: boolean;  // Model responding with TTS
  isProcessing: boolean;     // STT/LLM processing
  transcript: string;        // Final transcript
  partialTranscript: string; // Partial (streaming) transcript
  llmResponse: string;       // Accumulated LLM response
  audioLevel: number;        // Current mic level (0-1)
  error: string | null;
}

export function useRealtimeVoice(options: UseRealtimeVoiceOptions = {}) {
  const [state, setState] = useState<VoiceState>({
    isListening: false,
    isSpeaking: false,
    isModelSpeaking: false,
    isProcessing: false,
    transcript: '',
    partialTranscript: '',
    llmResponse: '',
    audioLevel: 0,
    error: null,
  });

  const audioManagerRef = useRef<AudioStreamManager | null>(null);
  const socketRef = useRef<Socket<VoiceServerToClient, VoiceClientToServer> | null>(null);
  const audioQueueRef = useRef<string[]>([]);
  const isPlayingRef = useRef(false);
  // Note: audioContextRef reserved for future AudioWorklet implementation
  // const audioContextRef = useRef<AudioContext | null>(null);

  // Initialize socket connection - ONCE (empty deps)
  useEffect(() => {
    // Prevent double-init in StrictMode
    if (socketRef.current) {
      // console.log('[Voice] Socket already exists, skipping init');
      return;
    }

    // Create dedicated voice socket (same server, different namespace behavior)
    const socket: Socket<VoiceServerToClient, VoiceClientToServer> = io(SOCKET_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      forceNew: false,  // Reuse connection if exists
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      // console.log('[Voice] Socket connected, id:', socket.id);
      // Config will be sent via separate useEffect when options change
    });

    socket.on('disconnect', (reason) => {
      // console.log('[Voice] Socket disconnected, reason:', reason);
    });

    // Voice status updates
    socket.on('voice_status', (data) => {
      // console.log('[Voice] Status:', data.status);
    });

    // Partial transcript (streaming STT)
    socket.on('voice_partial', (data) => {
      setState(s => ({ ...s, partialTranscript: data.text }));
    });

    // Final transcript
    socket.on('voice_final', (data) => {
      // console.log('[Voice] Final transcript:', data.text);
      setState(s => ({
        ...s,
        transcript: data.text,
        partialTranscript: '',
        isProcessing: true,
      }));
      options.onTranscript?.(data.text, true);
    });

    // LLM tokens (streaming)
    socket.on('voice_llm_token', (data) => {
      setState(s => ({ ...s, llmResponse: s.llmResponse + data.token }));
      options.onLLMToken?.(data.token);
    });

    // Model speaking state
    socket.on('voice_model_speaking', (data) => {
      // console.log('[Voice] Model speaking:', data.speaking);
      setState(s => ({
        ...s,
        isModelSpeaking: data.speaking,
        isProcessing: !data.speaking ? false : s.isProcessing,
        llmResponse: data.speaking ? '' : s.llmResponse,
      }));
      options.onModelSpeaking?.(data.speaking);
    });

    // TTS audio chunks
    socket.on('voice_tts_chunk', (data) => {
      audioQueueRef.current.push(data.audio);
      playNextChunk();
    });

    // Browser TTS fallback (when ElevenLabs not available)
    socket.on('voice_tts_browser', (data) => {
      // console.log('[Voice] Browser TTS fallback:', data.text.slice(0, 50));
      speakWithBrowserTTS(data.text);
    });

    // Interrupted
    socket.on('voice_interrupted', () => {
      // console.log('[Voice] Interrupted by user');
      stopTTSPlayback();
      setState(s => ({
        ...s,
        isModelSpeaking: false,
        isProcessing: false,
      }));
    });

    // Errors
    socket.on('voice_error', (data) => {
      console.error('[Voice] Error:', data.error);
      setState(s => ({ ...s, error: data.error, isProcessing: false }));
      options.onError?.(data.error);
    });

    return () => {
      // console.log('[Voice] Cleanup: disconnecting socket');
      socket.disconnect();
      socketRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);  // Empty deps - socket created once per component lifecycle

  // Send config when options change (separate from socket init)
  useEffect(() => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('voice_config', {
        model: options.model,
        tts_voice: options.ttsVoice,
        stt_provider: options.sttProvider,
        chat_mode: options.chatMode,
      });
    }
  }, [options.model, options.ttsVoice, options.sttProvider, options.chatMode]);

  // Play TTS chunks
  const playNextChunk = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;

    isPlayingRef.current = true;
    const base64Audio = audioQueueRef.current.shift()!;

    try {
      await playBase64Audio(base64Audio);
    } catch (e) {
      console.error('[Voice] Playback error:', e);
    }

    isPlayingRef.current = false;

    // Play next if available
    if (audioQueueRef.current.length > 0) {
      playNextChunk();
    }
  }, []);

  // Play base64 audio
  const playBase64Audio = useCallback((base64: string): Promise<void> => {
    return new Promise((resolve) => {
      const audio = new Audio(`data:audio/mp3;base64,${base64}`);
      audio.onended = () => resolve();
      audio.onerror = () => resolve();
      audio.play().catch(() => resolve());
    });
  }, []);

  // Stop TTS playback
  const stopTTSPlayback = useCallback(() => {
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    // Also stop browser TTS
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  }, []);

  // Browser TTS fallback (when no ElevenLabs key)
  const speakWithBrowserTTS = useCallback((text: string) => {
    if (!window.speechSynthesis) {
      // console.warn('[Voice] Browser TTS not available');
      return;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'ru-RU';  // Default to Russian
    utterance.rate = 1.1;
    utterance.pitch = 1.0;

    // Try to find a Russian voice
    const voices = window.speechSynthesis.getVoices();
    const ruVoice = voices.find(v => v.lang.startsWith('ru'));
    if (ruVoice) {
      utterance.voice = ruVoice;
    }

    utterance.onend = () => {
      setState(s => ({ ...s, isModelSpeaking: false }));
    };

    setState(s => ({ ...s, isModelSpeaking: true }));
    window.speechSynthesis.speak(utterance);
  }, []);

  // Start listening
  const startListening = useCallback(async () => {
    if (state.isListening) return;

    try {
      // Create audio manager
      audioManagerRef.current = new AudioStreamManager({
        sampleRate: 16000,
        frameSize: 2048,  // ~128ms at 16kHz
        channels: 1,

        onAudioFrame: (pcm, rms) => {
          // Update audio level for UI
          setState(s => ({ ...s, audioLevel: rms * 10 })); // Scale for visibility

          // Convert Float32 to Int16 array
          const int16 = float32ToInt16(pcm);

          // Send via Socket.IO
          socketRef.current?.emit('voice_pcm', {
            audio: Array.from(int16),
            sampleRate: 16000,
          });
        },

        onVADChange: (isSpeaking) => {
          setState(s => ({ ...s, isSpeaking }));

          if (!isSpeaking) {
            // User stopped speaking - signal end of utterance
            // console.log('[Voice] Utterance end (VAD)');
            socketRef.current?.emit('voice_utterance_end');
          }
        },

        onError: (error) => {
          console.error('[Voice] Audio error:', error);
          setState(s => ({ ...s, error: error.message }));
          options.onError?.(error.message);
        },
      });

      await audioManagerRef.current.start();

      setState(s => ({
        ...s,
        isListening: true,
        error: null,
        transcript: '',
        partialTranscript: '',
        llmResponse: '',
      }));

      socketRef.current?.emit('voice_stream_start');
      // console.log('[Voice] Listening started');

    } catch (error) {
      console.error('[Voice] Failed to start:', error);
      setState(s => ({ ...s, error: (error as Error).message }));
      options.onError?.((error as Error).message);
    }
  }, [state.isListening, options]);

  // Stop listening
  const stopListening = useCallback(() => {
    if (!state.isListening) return;

    audioManagerRef.current?.stop();
    audioManagerRef.current = null;

    setState(s => ({
      ...s,
      isListening: false,
      isSpeaking: false,
      audioLevel: 0,
    }));

    socketRef.current?.emit('voice_stream_end');
    // console.log('[Voice] Listening stopped');
  }, [state.isListening]);

  // Interrupt model (user starts speaking while model talks)
  const interrupt = useCallback(() => {
    // console.log('[Voice] Sending interrupt');
    socketRef.current?.emit('voice_interrupt');
    stopTTSPlayback();
    setState(s => ({
      ...s,
      isModelSpeaking: false,
      isProcessing: false,
    }));
  }, [stopTTSPlayback]);

  // Auto-interrupt when user speaks during model response
  useEffect(() => {
    if (state.isSpeaking && state.isModelSpeaking) {
      // console.log('[Voice] Auto-interrupt: user started speaking');
      interrupt();
    }
  }, [state.isSpeaking, state.isModelSpeaking, interrupt]);

  // Update config
  const setConfig = useCallback((config: {
    model?: string;
    ttsVoice?: string;
    sttProvider?: string;
  }) => {
    socketRef.current?.emit('voice_config', {
      model: config.model,
      tts_voice: config.ttsVoice,
      stt_provider: config.sttProvider,
    });
  }, []);

  // Clear error
  const clearError = useCallback(() => {
    setState(s => ({ ...s, error: null }));
  }, []);

  return {
    ...state,
    startListening,
    stopListening,
    interrupt,
    setConfig,
    clearError,
  };
}

export default useRealtimeVoice;
