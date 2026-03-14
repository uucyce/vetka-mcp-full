/**
 * JarvisWave - Simple waveform visualization for Jarvis voice interface
 * Phase 104.5 - Clean version with clickable area
 */
import React, { useEffect, useRef } from 'react';

interface JarvisWaveProps {
  state: 'idle' | 'listening' | 'thinking' | 'speaking';
  audioLevel?: number;
  onClick?: () => void;
  width?: number;
  height?: number;
}

const JarvisWave: React.FC<JarvisWaveProps> = ({
  state,
  audioLevel = 0,
  onClick,
  width = 200,
  height = 40,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number | undefined>(undefined);
  const phaseRef = useRef<number>(0);
  const pulseRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas resolution for sharp rendering
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    // Color mapping
    const colors = {
      idle: '#666666',
      listening: '#3B82F6',
      thinking: '#8B5CF6',
      speaking: '#10B981',
    };

    const animate = () => {
      // Clear canvas
      ctx.clearRect(0, 0, width, height);

      // Keep idle motion minimal; animate stronger only in active states
      const phaseStep = state === 'idle' ? 0.003 : state === 'thinking' ? 0.015 : 0.035;
      phaseRef.current += phaseStep;

      // Update pulse for thinking state
      if (state === 'thinking') {
        pulseRef.current += 0.04;
      }

      // Calculate amplitude based on state and audioLevel
      let baseAmplitude = height * 0.035;

      if (state === 'listening') {
        baseAmplitude = height * 0.16 + audioLevel * height * 0.18;
      } else if (state === 'speaking') {
        baseAmplitude = height * 0.14 + audioLevel * height * 0.16;
      } else if (state === 'thinking') {
        // Pulsing effect
        const pulse = Math.sin(pulseRef.current) * 0.5 + 0.5;
        baseAmplitude = height * 0.08 + pulse * height * 0.08;
      }

      // Draw sine wave
      ctx.beginPath();
      ctx.strokeStyle = colors[state];
      ctx.lineWidth = 2.5;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      const centerY = height / 2;
      const frequency = state === 'idle' ? 0.012 : 0.018;
      const points = width;

      for (let x = 0; x < points; x++) {
        const y = centerY + Math.sin(x * frequency + phaseRef.current) * baseAmplitude;

        if (x === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }

      ctx.stroke();

      // Add glow effect for active states
      if (state !== 'idle') {
        ctx.shadowBlur = state === 'thinking' ? 8 : 6;
        ctx.shadowColor = colors[state];
        ctx.stroke();
        ctx.shadowBlur = 0;
      }

      // Continue animation
      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [state, audioLevel, width, height]);

  // Status text based on state
  const statusText = {
    idle: 'Click to speak',
    listening: 'Listening...',
    thinking: 'Thinking...',
    speaking: 'Speaking...',
  };

  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '8px 16px',
        borderRadius: '12px',
        cursor: onClick ? 'pointer' : 'default',
        background: state !== 'idle' ? 'rgba(255,255,255,0.05)' : 'transparent',
        transition: 'background 0.3s ease',
      }}
    >
      <canvas
        ref={canvasRef}
        style={{
          width: `${width}px`,
          height: `${height}px`,
          display: 'block',
        }}
      />
      <span
        style={{
          fontSize: '10px',
          color: state === 'idle' ? '#666' : '#999',
          marginTop: '4px',
        }}
      >
        {statusText[state]}
      </span>
    </div>
  );
};

export default JarvisWave;
