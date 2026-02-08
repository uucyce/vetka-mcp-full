/**
 * Glow Texture Generator for VETKA 3D
 * Phase 123.8: Radial gradient sprite for file activity glow
 *
 * Creates a soft radial gradient texture for use with Sprite + AdditiveBlending.
 * This creates a true "glow" effect without heavy post-processing.
 *
 * @phase 123.8
 */

import * as THREE from 'three';

// Singleton cache for glow textures (one per intensity level)
const textureCache = new Map<string, THREE.CanvasTexture>();

/**
 * Create a radial gradient glow texture.
 * Center is bright, edges fade to transparent.
 *
 * @param color - Glow color (default: white)
 * @param size - Canvas size (default: 128 for good quality)
 * @returns THREE.CanvasTexture with radial gradient
 */
export function createGlowTexture(
  color: string = '#ffffff',
  size: number = 128
): THREE.CanvasTexture {
  const cacheKey = `${color}:${size}`;

  // Return cached texture if exists
  const cached = textureCache.get(cacheKey);
  if (cached) return cached;

  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;

  const center = size / 2;
  const radius = size / 2;

  // Create radial gradient: bright center → transparent edges
  const gradient = ctx.createRadialGradient(center, center, 0, center, center, radius);

  // Parse color to RGB for gradient stops
  const tempDiv = document.createElement('div');
  tempDiv.style.color = color;
  document.body.appendChild(tempDiv);
  const computedColor = getComputedStyle(tempDiv).color;
  document.body.removeChild(tempDiv);

  // Extract RGB values
  const rgbMatch = computedColor.match(/\d+/g);
  const r = rgbMatch ? parseInt(rgbMatch[0]) : 255;
  const g = rgbMatch ? parseInt(rgbMatch[1]) : 255;
  const b = rgbMatch ? parseInt(rgbMatch[2]) : 255;

  // Gradient stops: bright center → soft falloff → transparent
  gradient.addColorStop(0, `rgba(${r},${g},${b},0.8)`);     // Bright center
  gradient.addColorStop(0.2, `rgba(${r},${g},${b},0.5)`);   // Still visible
  gradient.addColorStop(0.5, `rgba(${r},${g},${b},0.2)`);   // Fading
  gradient.addColorStop(0.8, `rgba(${r},${g},${b},0.05)`);  // Almost gone
  gradient.addColorStop(1, `rgba(${r},${g},${b},0)`);       // Fully transparent

  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);

  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;

  // Cache the texture
  textureCache.set(cacheKey, texture);

  return texture;
}

/**
 * Pre-generated white glow texture (most common use case)
 * Lazy-loaded on first access
 */
let _whiteGlowTexture: THREE.CanvasTexture | null = null;

export function getWhiteGlowTexture(): THREE.CanvasTexture {
  if (!_whiteGlowTexture) {
    _whiteGlowTexture = createGlowTexture('#ffffff', 128);
  }
  return _whiteGlowTexture;
}
