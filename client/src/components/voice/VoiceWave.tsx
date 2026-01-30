/**
 * VoiceWave - Canvas-based audio wave animation.
 * Displays listening/speaking states with intensity-based amplitude.
 *
 * @status active
 * @phase 96
 * @depends react
 * @used_by VoiceButton
 */

import { useEffect, useRef } from 'react';

interface VoiceWaveProps {
  isActive: boolean;
  mode: 'listening' | 'speaking' | 'idle';
  intensity?: number; // 0-1, audio level
  width?: number;
  height?: number;
}

export function VoiceWave({
  isActive,
  mode,
  intensity = 0.5,
  width = 120,
  height = 40,
}: VoiceWaveProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | undefined>(undefined);
  const phaseRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const centerY = height / 2;

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      if (!isActive) {
        // Idle: single thin line with gradient
        const gradient = ctx.createLinearGradient(0, 0, width, 0);
        gradient.addColorStop(0, 'transparent');
        gradient.addColorStop(0.3, '#333');
        gradient.addColorStop(0.5, '#555');
        gradient.addColorStop(0.7, '#333');
        gradient.addColorStop(1, 'transparent');

        ctx.beginPath();
        ctx.moveTo(0, centerY);
        ctx.lineTo(width, centerY);
        ctx.strokeStyle = gradient;
        ctx.lineWidth = 2;
        ctx.stroke();

        animationRef.current = requestAnimationFrame(draw);
        return;
      }

      // Active: wave animation
      const amplitude = 12 * Math.max(0.3, intensity);
      const frequency = mode === 'listening' ? 0.025 : 0.035;
      const speed = mode === 'listening' ? 0.06 : 0.09;

      // Draw wave
      ctx.beginPath();
      for (let x = 0; x < width; x++) {
        // Multiple sine waves for organic feel
        const y =
          centerY +
          Math.sin(x * frequency + phaseRef.current) * amplitude +
          Math.sin(x * frequency * 2 + phaseRef.current * 1.5) * (amplitude * 0.4) +
          Math.sin(x * frequency * 0.5 + phaseRef.current * 0.7) * (amplitude * 0.3);

        if (x === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }

      // Gradient stroke - blue for listening, green for speaking
      const gradient = ctx.createLinearGradient(0, 0, width, 0);
      if (mode === 'listening') {
        // Blue accent
        gradient.addColorStop(0, 'transparent');
        gradient.addColorStop(0.2, '#1a3a5c');
        gradient.addColorStop(0.5, '#4a9eff');
        gradient.addColorStop(0.8, '#1a3a5c');
        gradient.addColorStop(1, 'transparent');
      } else {
        // Green accent
        gradient.addColorStop(0, 'transparent');
        gradient.addColorStop(0.2, '#1a3a2a');
        gradient.addColorStop(0.5, '#4aff9e');
        gradient.addColorStop(0.8, '#1a3a2a');
        gradient.addColorStop(1, 'transparent');
      }

      ctx.strokeStyle = gradient;
      ctx.lineWidth = 2.5;
      ctx.lineCap = 'round';
      ctx.stroke();

      // Glow effect
      ctx.save();
      ctx.shadowColor = mode === 'listening' ? '#4a9eff' : '#4aff9e';
      ctx.shadowBlur = 8 * intensity;
      ctx.stroke();
      ctx.restore();

      phaseRef.current += speed;
      animationRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isActive, mode, intensity, width, height]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{
        display: 'block',
        background: 'transparent',
        opacity: isActive ? 1 : 0.4,
        transition: 'opacity 0.3s ease',
      }}
    />
  );
}

export default VoiceWave;
