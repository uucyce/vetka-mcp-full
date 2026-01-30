/**
 * SmartVoiceInput - Smart voice/text input with auto-mode switching.
 * Shows mic when empty, send when text present, wave when listening.
 *
 * @status active
 * @phase 96
 * @depends react, lucide-react, Web Speech API
 * @used_by MessageInput (optional integration)
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { Mic, Send, Square, Loader2 } from 'lucide-react';

interface SmartVoiceInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  isLoading: boolean;
  disabled?: boolean;
  placeholder?: string;
}

// Wave drawing for listening mode
function drawWave(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  phase: number,
  intensity: number,
  color: string
) {
  const centerY = height / 2;
  const amplitude = 8 * Math.max(0.4, intensity);
  const frequency = 0.03;

  ctx.clearRect(0, 0, width, height);
  ctx.beginPath();

  for (let x = 0; x < width; x++) {
    const y =
      centerY +
      Math.sin(x * frequency + phase) * amplitude +
      Math.sin(x * frequency * 2.3 + phase * 1.4) * (amplitude * 0.5) +
      Math.sin(x * frequency * 0.7 + phase * 0.8) * (amplitude * 0.3);

    if (x === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }

  // Gradient stroke
  const gradient = ctx.createLinearGradient(0, 0, width, 0);
  gradient.addColorStop(0, 'transparent');
  gradient.addColorStop(0.2, color + '60');
  gradient.addColorStop(0.5, color);
  gradient.addColorStop(0.8, color + '60');
  gradient.addColorStop(1, 'transparent');

  ctx.strokeStyle = gradient;
  ctx.lineWidth = 2.5;
  ctx.lineCap = 'round';
  ctx.stroke();

  // Glow
  ctx.shadowColor = color;
  ctx.shadowBlur = 10 * intensity;
  ctx.stroke();
}

export function SmartVoiceInput({
  value,
  onChange,
  onSend,
  isLoading,
  disabled = false,
  placeholder = 'Type or speak...',
}: SmartVoiceInputProps) {
  const [isListening, setIsListening] = useState(false);
  const [intensity, setIntensity] = useState(0.5);
  const [statusText, setStatusText] = useState<string | null>(null);

  const inputRef = useRef<HTMLTextAreaElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const recognitionRef = useRef<any>(null);
  const animationRef = useRef<number | undefined>(undefined);
  const phaseRef = useRef<number>(0);

  // Determine button mode: voice (mic/wave) or send
  const hasText = value.trim().length > 0;
  const showSendMode = hasText && !isListening;

  // Wave animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !isListening) {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = undefined;
      }
      return;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const animate = () => {
      drawWave(ctx, canvas.width, canvas.height, phaseRef.current, intensity, '#4a9eff');
      phaseRef.current += 0.08;
      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isListening, intensity]);

  // Web Speech API STT
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
    recognition.lang = 'ru-RU'; // Russian primary, will auto-detect

    let finalTranscript = '';

    recognition.onstart = () => {
      setIsListening(true);
      setStatusText('Listening...');
      // Simulate audio intensity variation
      const intensityInterval = setInterval(() => {
        if (isListening) {
          setIntensity(0.3 + Math.random() * 0.7);
        }
      }, 100);
      (recognition as any)._intensityInterval = intensityInterval;
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

      // Update input with current transcription
      const currentText = value.trim();
      const newText = currentText
        ? currentText + ' ' + (finalTranscript + interimTranscript).trim()
        : (finalTranscript + interimTranscript).trim();

      onChange(newText);
    };

    recognition.onerror = (event: any) => {
      console.error('[Voice] Recognition error:', event.error);
      if (event.error !== 'aborted') {
        setStatusText(`Error: ${event.error}`);
        setTimeout(() => setStatusText(null), 2000);
      }
      setIsListening(false);
      clearInterval((recognition as any)._intensityInterval);
    };

    recognition.onend = () => {
      setIsListening(false);
      setStatusText(null);
      setIntensity(0.5);
      clearInterval((recognition as any)._intensityInterval);
      inputRef.current?.focus();
    };

    try {
      recognition.start();
    } catch (e) {
      console.error('[Voice] Failed to start recognition:', e);
      setStatusText('Mic access denied');
      setTimeout(() => setStatusText(null), 2000);
    }
  }, [disabled, isLoading, isListening, value, onChange]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setIsListening(false);
    setStatusText(null);
  }, []);

  // Handle smart button click
  const handleButtonClick = useCallback(() => {
    if (isLoading) return;

    if (isListening) {
      // Stop listening
      stopListening();
    } else if (showSendMode) {
      // Send message
      onSend();
    } else {
      // Start listening
      startListening();
    }
  }, [isLoading, isListening, showSendMode, stopListening, startListening, onSend]);

  // Handle textarea keyboard
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!isLoading && value.trim()) {
          onSend();
        }
      }
    },
    [isLoading, value, onSend]
  );

  // Auto-resize textarea
  useEffect(() => {
    const textarea = inputRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
  }, [value]);

  // Button icon and color based on state
  const getButtonStyle = () => {
    if (isLoading) {
      return { bg: '#2a2a2a', color: '#666', shadow: 'none' };
    }
    if (isListening) {
      return { bg: '#1a2a3a', color: '#4a9eff', shadow: '0 0 16px rgba(74, 158, 255, 0.5)' };
    }
    if (showSendMode) {
      return { bg: '#1a3a2a', color: '#4aff9e', shadow: '0 0 12px rgba(74, 255, 158, 0.3)' };
    }
    return { bg: '#2a2a2a', color: '#888', shadow: 'none' };
  };

  const buttonStyle = getButtonStyle();

  return (
    <div style={{ padding: 12, borderTop: '1px solid #222', position: 'relative' }}>
      {/* Status text */}
      {statusText && (
        <div
          style={{
            position: 'absolute',
            top: -28,
            left: '50%',
            transform: 'translateX(-50%)',
            background: '#1a1a1a',
            color: '#4a9eff',
            padding: '4px 12px',
            borderRadius: 12,
            fontSize: 12,
            border: '1px solid #333',
          }}
        >
          {statusText}
        </div>
      )}

      <div
        style={{
          display: 'flex',
          gap: 8,
          alignItems: 'flex-end',
          background: '#1a1a1a',
          borderRadius: 12,
          padding: '10px 12px',
          border: isListening ? '1px solid #4a9eff40' : '1px solid #333',
          transition: 'border-color 0.3s ease',
        }}
      >
        {/* Wave canvas (shown when listening) */}
        {isListening && (
          <canvas
            ref={canvasRef}
            width={80}
            height={32}
            style={{
              display: 'block',
              opacity: 0.9,
            }}
          />
        )}

        {/* Text input */}
        <textarea
          ref={inputRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isListening ? 'Listening...' : placeholder}
          disabled={disabled || isLoading}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            color: '#fff',
            resize: 'none',
            outline: 'none',
            fontSize: 14,
            lineHeight: 1.4,
            minHeight: 20,
            maxHeight: 120,
            fontFamily: 'inherit',
            opacity: isListening ? 0.7 : 1,
          }}
          rows={1}
        />

        {/* Smart button: Mic → Send → Stop */}
        <button
          onClick={handleButtonClick}
          disabled={disabled || (showSendMode && !value.trim())}
          style={{
            width: 40,
            height: 40,
            borderRadius: '50%',
            border: 'none',
            background: buttonStyle.bg,
            color: buttonStyle.color,
            cursor: disabled ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.25s ease',
            boxShadow: buttonStyle.shadow,
            opacity: disabled ? 0.5 : 1,
            flexShrink: 0,
          }}
          title={
            isListening
              ? 'Stop listening'
              : showSendMode
              ? 'Send message'
              : 'Voice input'
          }
        >
          {isLoading ? (
            <Loader2 size={20} className="spin-animation" />
          ) : isListening ? (
            <Square size={16} fill="currentColor" />
          ) : showSendMode ? (
            <Send size={18} />
          ) : (
            <Mic size={20} />
          )}
        </button>
      </div>

      <div
        style={{
          marginTop: 6,
          fontSize: 10,
          color: '#444',
          textAlign: 'center',
        }}
      >
        {isListening
          ? 'Tap square to stop • говорите...'
          : 'Tap mic to speak • Enter to send'}
      </div>

      <style>{`
        .spin-animation { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

export default SmartVoiceInput;
