/**
 * Smart Voice-Aware Message Input with Realtime Pipeline.
 * Supports text input, @mentions, and voice recording with VAD-based turn detection.
 * Auto-detects voice models and switches between Send/Mic modes dynamically.
 *
 * @status active
 * @phase 96
 * @depends react, lucide-react, useRealtimeVoice, MentionPopup
 * @used_by ChatPanel
 */

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { Mic, Send, Square, Loader2, Volume2 } from 'lucide-react';
import { MentionPopup } from './MentionPopup';
import { useRealtimeVoice } from '../../hooks/useRealtimeVoice';

// Phase 57.8.3: Group participant type for filtering mentions
interface GroupParticipant {
  agent_id: string;
  display_name: string;
  role?: string;
}

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  isLoading: boolean;
  disabled?: boolean;
  replyTo?: string;  // Display name for placeholder
  replyToModel?: string;  // Full model ID for voice detection
  isGroupMode?: boolean;
  groupParticipants?: GroupParticipant[];
  // Phase 80.30: Solo chat models for @mention dropdown
  soloModels?: string[];
  // Phase 60.5: Voice models list for smart detection
  voiceModels?: string[];
  // Phase 60.5: Selected model from ModelDirectory
  selectedModel?: string | null;
  // Phase 60.5: Voice-only mode (always show mic)
  voiceOnlyMode?: boolean;
  onVoiceOnlyModeChange?: (value: boolean) => void;
  // Phase 60.5: Auto-continue voice after response
  autoContinueVoice?: boolean;
  onAutoContinueVoiceChange?: (value: boolean) => void;
  // Phase 60.5.1: Realtime voice mode
  realtimeVoiceEnabled?: boolean;
  onRealtimeVoiceChange?: (enabled: boolean) => void;
  // TODO_CAM_UI: Pass CAM context suggestions to enrich input hints
  cam_suggestions?: string[];  // Show hot/warm files in placeholder or autocomplete
}

// Voice mode types for wave animation
type VoiceMode = 'idle' | 'listening' | 'speaking' | 'playing';

// Get wave color based on mode (must be 6-char hex for gradient alpha suffix)
function getWaveColor(mode: VoiceMode): string {
  switch (mode) {
    case 'speaking': return '#4a9eff';   // Blue - user speaking
    case 'playing': return '#4aff9e';    // Green - model speaking
    case 'listening': return '#66aabb';  // Teal - waiting for speech
    default: return '#555555';           // Gray - idle
  }
}

// Wave drawing for listening mode
function drawWave(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  phase: number,
  intensity: number,
  mode: VoiceMode = 'listening'
) {
  const centerY = height / 2;
  const amplitude = 10 * Math.max(0.3, intensity);
  const frequency = 0.025;
  const color = getWaveColor(mode);

  ctx.clearRect(0, 0, width, height);
  ctx.beginPath();

  for (let x = 0; x < width; x++) {
    const y =
      centerY +
      Math.sin(x * frequency + phase) * amplitude +
      Math.sin(x * frequency * 2.1 + phase * 1.3) * (amplitude * 0.5) +
      Math.sin(x * frequency * 0.6 + phase * 0.9) * (amplitude * 0.35);

    if (x === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }

  // Gradient for wave with dynamic color
  const gradient = ctx.createLinearGradient(0, 0, width, 0);
  gradient.addColorStop(0, 'transparent');
  gradient.addColorStop(0.15, color + '30');
  gradient.addColorStop(0.5, color);
  gradient.addColorStop(0.85, color + '30');
  gradient.addColorStop(1, 'transparent');

  ctx.strokeStyle = gradient;
  ctx.lineWidth = 2.5;
  ctx.lineCap = 'round';
  ctx.stroke();

  // Glow effect
  ctx.save();
  ctx.shadowColor = color;
  ctx.shadowBlur = 12 * intensity;
  ctx.stroke();
  ctx.restore();
}

export function MessageInput({
  value,
  onChange,
  onSend,
  isLoading,
  disabled,
  replyTo,
  replyToModel,
  isGroupMode,
  groupParticipants,
  soloModels,
  voiceModels = [],
  selectedModel,
  voiceOnlyMode = false,
  onVoiceOnlyModeChange,
  autoContinueVoice = false,
  onAutoContinueVoiceChange,
  realtimeVoiceEnabled = false,
  onRealtimeVoiceChange,
}: Props) {
  const [showMentions, setShowMentions] = useState(false);
  const [mentionFilter, setMentionFilter] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [intensity, setIntensity] = useState(0.5);
  const [statusText, setStatusText] = useState<string | null>(null);

  const inputRef = useRef<HTMLTextAreaElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const recognitionRef = useRef<any>(null);
  const animationRef = useRef<number | undefined>(undefined);
  const phaseRef = useRef<number>(0);
  const intensityIntervalRef = useRef<any>(null);

  // Phase 60.5.1: Realtime voice hook
  // In realtime mode, we DON'T write transcript to input - it's pure audio pipeline
  const realtimeVoice = useRealtimeVoice({
    model: selectedModel || undefined,
    onTranscript: (text, isFinal) => {
      // Just log - don't write to input in realtime mode
      // The pipeline is: Mic → STT → LLM → TTS → Audio
      if (isFinal && text.trim()) {
        // console.log('[Realtime] Transcript:', text);
        setStatusText(`"${text.slice(0, 40)}${text.length > 40 ? '...' : ''}"`);
      }
    },
    onLLMToken: (token) => {
      // Could display streaming response in a separate UI element
      // For now just log - TTS will speak it
    },
    onModelSpeaking: (speaking) => {
      if (speaking) {
        setStatusText('🔊 Отвечаю...');
      } else {
        setStatusText(null);
      }
    },
    onError: (error) => {
      setStatusText(`Ошибка: ${error}`);
      setTimeout(() => setStatusText(null), 3000);
    },
  });

  // Determine voice mode for wave animation
  const voiceMode: VoiceMode = realtimeVoice.isModelSpeaking
    ? 'playing'
    : realtimeVoice.isSpeaking
    ? 'speaking'
    : realtimeVoice.isListening
    ? 'listening'
    : 'idle';

  // Phase 60.5: Check if replying to a voice model
  const isReplyingToVoiceModel = useMemo(() => {
    if (!replyToModel || voiceModels.length === 0) return false;
    return voiceModels.some(vm =>
      vm.toLowerCase() === replyToModel.toLowerCase() ||
      vm.toLowerCase().includes(replyToModel.toLowerCase()) ||
      replyToModel.toLowerCase().includes(vm.toLowerCase())
    );
  }, [replyToModel, voiceModels]);

  // Phase 60.5: Trigger 1 - Check if selected model from ModelDirectory is a voice model
  const isSelectedModelVoice = useMemo(() => {
    if (!selectedModel || voiceModels.length === 0) return false;
    return voiceModels.some(vm =>
      vm.toLowerCase() === selectedModel.toLowerCase() ||
      vm.toLowerCase().includes(selectedModel.toLowerCase()) ||
      selectedModel.toLowerCase().includes(vm.toLowerCase())
    );
  }, [selectedModel, voiceModels]);

  // Phase 60.5: Detect if voice model is mentioned AND no text after it
  const voiceModelDetection = useMemo(() => {
    // Find @model_id pattern in text
    const mentionMatch = value.match(/@([a-zA-Z0-9\-_\/\.]+)/g);
    if (!mentionMatch || mentionMatch.length === 0) {
      return { hasVoiceModel: false, modelId: null, hasTextAfter: false };
    }

    // Get the last mention
    const lastMention = mentionMatch[mentionMatch.length - 1];
    const modelId = lastMention.slice(1); // Remove @

    // Check if it's a voice model
    const isVoiceModel = voiceModels.some(vm =>
      vm.toLowerCase() === modelId.toLowerCase() ||
      vm.toLowerCase().includes(modelId.toLowerCase()) ||
      modelId.toLowerCase().includes(vm.toLowerCase())
    );

    if (!isVoiceModel) {
      return { hasVoiceModel: false, modelId: null, hasTextAfter: false };
    }

    // Check if there's text AFTER the mention
    const lastMentionIndex = value.lastIndexOf(lastMention);
    const textAfterMention = value.slice(lastMentionIndex + lastMention.length).trim();
    const hasTextAfter = textAfterMention.length > 0;

    return { hasVoiceModel: true, modelId, hasTextAfter };
  }, [value, voiceModels]);

  // Determine button mode:
  // - isListening → Stop button
  // - hasVoiceModel && !hasTextAfter → Mic button (voice mode available)
  // - replyTo voice model && empty input → Mic button
  // - hasText → Send button
  // - empty → Send button (disabled)
  const hasText = value.trim().length > 0;

  // Phase 60.5: Voice mode triggers:
  // 1. @mention of voice model (no text after)
  // 2. Reply to voice model message (empty input)
  // 3. Selected model from ModelDirectory is voice model (empty input)
  // 4. Voice-only mode toggle (always show mic unless typing)
  const showVoiceMode = (
    (voiceModelDetection.hasVoiceModel && !voiceModelDetection.hasTextAfter) ||
    (isReplyingToVoiceModel && !hasText) ||
    (isSelectedModelVoice && !hasText) ||
    (voiceOnlyMode && !hasText)
  ) && !isListening;

  // Combined active state (legacy or realtime)
  const isVoiceActive = isListening || realtimeVoice.isListening;
  const effectiveIntensity = realtimeVoice.isListening
    ? Math.min(1, realtimeVoice.audioLevel * 3)  // Scale audio level
    : intensity;

  // Wave animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !isVoiceActive) {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = undefined;
      }
      return;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const animate = () => {
      drawWave(ctx, canvas.width, canvas.height, phaseRef.current, effectiveIntensity, voiceMode);
      phaseRef.current += 0.07;
      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isVoiceActive, effectiveIntensity, voiceMode]);

  // Detect @ typing for mentions
  // MARKER_94.7_AT_DETECTION: @ symbol detection trigger
  useEffect(() => {
    const lastAtIndex = value.lastIndexOf('@');
    if (lastAtIndex !== -1) {
      const textAfterAt = value.slice(lastAtIndex + 1);
      if (!textAfterAt.includes(' ') && textAfterAt.length < 50) {
        setShowMentions(true);
        setMentionFilter(textAfterAt.toLowerCase());
        return;
      }
    }
    setShowMentions(false);
  }, [value]);

  const handleMentionSelect = useCallback(
    (alias: string) => {
      const lastAtIndex = value.lastIndexOf('@');
      const newValue = value.slice(0, lastAtIndex) + alias + ' ';
      onChange(newValue);
      setShowMentions(false);
      inputRef.current?.focus();
    },
    [value, onChange]
  );

  // Start voice recognition
  const startListening = useCallback(() => {
    if (disabled || isLoading || isListening) return;

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setStatusText('Speech not supported');
      setTimeout(() => setStatusText(null), 2000);
      return;
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;

    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = navigator.language || 'ru-RU';

    let finalTranscript = '';
    const baseValue = value;

    recognition.onstart = () => {
      setIsListening(true);
      setStatusText('Слушаю...');
      intensityIntervalRef.current = setInterval(() => {
        setIntensity(0.35 + Math.random() * 0.65);
      }, 80);
    };

    recognition.onresult = (event: any) => {
      let interimTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + ' ';
        } else {
          interimTranscript = transcript;
        }
      }

      const spoken = (finalTranscript + interimTranscript).trim();
      const newText = baseValue.trim()
        ? baseValue.trim() + ' ' + spoken
        : spoken;

      onChange(newText);
    };

    recognition.onerror = (event: any) => {
      console.error('[Voice] Error:', event.error);
      if (event.error !== 'aborted' && event.error !== 'no-speech') {
        setStatusText(`Ошибка: ${event.error}`);
        setTimeout(() => setStatusText(null), 2000);
      }
    };

    recognition.onend = () => {
      setIsListening(false);
      setStatusText(null);
      setIntensity(0.5);
      if (intensityIntervalRef.current) {
        clearInterval(intensityIntervalRef.current);
        intensityIntervalRef.current = null;
      }
      inputRef.current?.focus();
    };

    try {
      recognition.start();
    } catch (e) {
      console.error('[Voice] Start failed:', e);
      setStatusText('Нет доступа к микрофону');
      setTimeout(() => setStatusText(null), 2000);
    }
  }, [disabled, isLoading, isListening, value, onChange]);

  // Stop voice recognition
  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setIsListening(false);
    setStatusText(null);
    if (intensityIntervalRef.current) {
      clearInterval(intensityIntervalRef.current);
      intensityIntervalRef.current = null;
    }
  }, []);

  // Phase 60.5: Trigger 3 - Auto-continue voice after model response
  // When isLoading goes from true to false and autoContinueVoice is on,
  // start listening again (simulates continuous voice dialog)
  const wasLoadingRef = useRef(isLoading);
  useEffect(() => {
    const wasLoading = wasLoadingRef.current;
    wasLoadingRef.current = isLoading;

    // Only trigger when loading just finished
    if (wasLoading && !isLoading && autoContinueVoice) {
      // Check if we should auto-start voice (voice mode conditions met)
      const shouldAutoStart =
        (voiceModelDetection.hasVoiceModel && !voiceModelDetection.hasTextAfter) ||
        isReplyingToVoiceModel ||
        isSelectedModelVoice ||
        voiceOnlyMode;

      if (shouldAutoStart && !isListening && !realtimeVoice.isListening) {
        // Small delay to let the response render and audio finish
        const timer = setTimeout(() => {
          // Use realtime or legacy based on setting
          if (realtimeVoiceEnabled) {
            realtimeVoice.startListening();
          } else {
            startListening();
          }
        }, 600);
        return () => clearTimeout(timer);
      }
    }
  }, [isLoading, autoContinueVoice, voiceModelDetection, isReplyingToVoiceModel, isSelectedModelVoice, voiceOnlyMode, isListening, startListening, realtimeVoiceEnabled, realtimeVoice]);

  // Smart button click handler
  // Phase 60.5.1: Voice models now use realtime pipeline automatically
  // MARKER_90.1_START: Fix voice/text priority
  const handleButtonClick = useCallback(() => {
    // PRIORITY 1: If user typed text, ALWAYS send text (regardless of voice model)
    if (hasText) {
      // Stop any active voice recording first
      if (isListening) stopListening();
      if (realtimeVoice.isListening) realtimeVoice.stopListening();
      onSend();
      return;
    }

    // PRIORITY 2: Voice mode active (empty input + voice model selected/mentioned)
    if (showVoiceMode || voiceOnlyMode || isSelectedModelVoice) {
      if (realtimeVoice.isListening) {
        realtimeVoice.stopListening();
      } else {
        realtimeVoice.startListening();
      }
      return;
    }

    // Legacy voice mode (for non-voice models with voiceOnlyMode)
    if (isListening) {
      stopListening();
    }
  }, [isListening, showVoiceMode, hasText, stopListening, onSend, realtimeVoice, voiceOnlyMode, isSelectedModelVoice]);
  // MARKER_90.1_END

  // Keyboard handling
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (value.trim()) {
          if (isListening) stopListening();
          if (realtimeVoice.isListening) realtimeVoice.stopListening();
          onSend();
        }
      }
      if (e.key === 'Escape') {
        setShowMentions(false);
        if (isListening) stopListening();
        if (realtimeVoice.isListening) realtimeVoice.stopListening();
      }
    },
    [value, onSend, isListening, stopListening, realtimeVoice]
  );

  // Auto-resize textarea
  useEffect(() => {
    const textarea = inputRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
  }, [value]);

  // Button styling - Nolan style (white/gray, subtle)
  const getButtonStyle = () => {
    if (isLoading) {
      return { bg: '#2a2a2a', color: '#555', shadow: 'none' };
    }
    // Phase 60.5.1: Realtime voice states
    if (realtimeVoice.isModelSpeaking) {
      // Model speaking - green glow
      return { bg: '#1a3a2a', color: '#4aff9e', shadow: '0 0 20px rgba(74, 255, 158, 0.5)' };
    }
    if (realtimeVoice.isSpeaking) {
      // User speaking - bright blue
      return { bg: '#1a2a3a', color: '#4a9eff', shadow: '0 0 25px rgba(74, 158, 255, 0.6)' };
    }
    if (realtimeVoice.isListening) {
      // Listening but not speaking - subtle blue
      return { bg: '#1a2a3a', color: '#4a9eff', shadow: '0 0 15px rgba(74, 158, 255, 0.4)' };
    }
    if (isListening) {
      // Legacy listening - blue glow
      return { bg: '#1a2a3a', color: '#4a9eff', shadow: '0 0 20px rgba(74, 158, 255, 0.5)' };
    }
    if (showVoiceMode) {
      // Voice model detected - subtle blue hint
      return { bg: '#1a2a30', color: '#6ab', shadow: '0 0 10px rgba(100, 170, 187, 0.25)' };
    }
    if (hasText) {
      // Ready to send - white (Nolan style, not green)
      return { bg: '#333', color: '#fff', shadow: '0 0 8px rgba(255, 255, 255, 0.15)' };
    }
    // Empty - subtle gray
    return { bg: '#2a2a2a', color: '#555', shadow: 'none' };
  };

  const btnStyle = getButtonStyle();

  // Help text
  const getHelpText = () => {
    // Phase 60.5.1: Realtime voice states
    if (realtimeVoice.isModelSpeaking) {
      return '🔊 модель говорит • нажмите чтобы перебить';
    }
    if (realtimeVoice.isSpeaking) {
      return '🎤 говорите... • пауза = отправка';
    }
    if (realtimeVoice.isListening) {
      return '🎧 слушаю... • ■ остановить';
    }
    if (isListening) {
      return '■ остановить • Esc отмена';
    }
    if (showVoiceMode) {
      return '🎤 голосовой режим • печатайте для текста';
    }
    return 'Enter — отправить • Shift+Enter — строка';
  };

  return (
    <div style={{ padding: 12, borderTop: '1px solid #222', position: 'relative' }}>
      {/* Mention popup */}
      {/* Phase 80.30: Pass soloModels for solo chat @mention dropdown */}
      {showMentions && (
        <MentionPopup
          filter={mentionFilter}
          onSelect={handleMentionSelect}
          isGroupMode={isGroupMode}
          groupParticipants={groupParticipants}
          soloModels={soloModels}
        />
      )}

      {/* Status indicator */}
      {statusText && (
        <div
          style={{
            position: 'absolute',
            top: -26,
            left: '50%',
            transform: 'translateX(-50%)',
            background: '#0f1a2a',
            color: '#4a9eff',
            padding: '4px 14px',
            borderRadius: 12,
            fontSize: 12,
            border: '1px solid #2a3a4a',
            whiteSpace: 'nowrap',
          }}
        >
          {statusText}
        </div>
      )}

      {/* Input container */}
      <div
        style={{
          display: 'flex',
          gap: 10,
          alignItems: 'flex-end',
          background: '#1a1a1a',
          borderRadius: 14,
          padding: '10px 14px',
          border: isVoiceActive
            ? realtimeVoice.isModelSpeaking
              ? '1px solid #4aff9e50'
              : '1px solid #4a9eff50'
            : '1px solid #333',
          transition: 'border-color 0.3s ease, box-shadow 0.3s ease',
          boxShadow: isVoiceActive
            ? realtimeVoice.isModelSpeaking
              ? '0 0 20px rgba(74, 255, 158, 0.15)'
              : '0 0 20px rgba(74, 158, 255, 0.15)'
            : 'none',
        }}
      >
        {/* Wave canvas - shown when listening (legacy or realtime) */}
        {isVoiceActive && (
          <canvas
            ref={canvasRef}
            width={100}
            height={36}
            style={{
              display: 'block',
              flexShrink: 0,
            }}
          />
        )}

        {/* Textarea */}
        <textarea
          ref={inputRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            realtimeVoice.isListening
              ? realtimeVoice.isSpeaking
                ? 'Говорите...'
                : 'Слушаю...'
              : isListening
              ? 'Говорите...'
              : replyTo
              ? `Reply to ${replyTo}...`
              : 'Введите сообщение...'
          }
          disabled={disabled}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            color: '#fff',
            resize: 'none',
            outline: 'none',
            fontSize: 14,
            lineHeight: 1.4,
            minHeight: 22,
            maxHeight: 120,
            fontFamily: 'inherit',
            opacity: isVoiceActive ? 0.8 : 1,
          }}
          rows={1}
        />

        {/* Smart button: Send / Mic / Stop / Speaker */}
        <button
          onClick={handleButtonClick}
          disabled={disabled || (!hasText && !showVoiceMode && !isVoiceActive)}
          style={{
            width: 40,
            height: 40,
            borderRadius: '50%',
            border: 'none',
            background: btnStyle.bg,
            color: btnStyle.color,
            cursor: disabled ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s ease',
            boxShadow: btnStyle.shadow,
            opacity: disabled ? 0.5 : 1,
            flexShrink: 0,
          }}
          title={
            realtimeVoice.isModelSpeaking
              ? 'Перебить модель'
              : realtimeVoice.isListening
              ? 'Остановить'
              : isListening
              ? 'Остановить запись'
              : showVoiceMode
              ? 'Голосовой ввод'
              : 'Отправить (Enter)'
          }
        >
          {isLoading ? (
            <Loader2 size={18} className="vetka-spin" />
          ) : realtimeVoice.isModelSpeaking ? (
            <Volume2 size={18} />
          ) : realtimeVoice.isListening || isListening ? (
            <Square size={14} fill="currentColor" />
          ) : showVoiceMode ? (
            <Mic size={20} />
          ) : (
            <Send size={18} />
          )}
        </button>
      </div>

      {/* Help text - clean, no buttons */}
      <div
        style={{
          marginTop: 6,
          fontSize: 10,
          color: '#444',
          textAlign: 'center',
        }}
      >
        {getHelpText()}
      </div>

      <style>{`
        .vetka-spin { animation: vetka-spin 1s linear infinite; }
        @keyframes vetka-spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
