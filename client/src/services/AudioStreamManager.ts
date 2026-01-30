/**
 * AudioStreamManager - PCM audio streaming with VAD for low-latency voice.
 * Streams 16kHz mono PCM frames with built-in Voice Activity Detection.
 *
 * @status active
 * @phase 96
 * @depends Web Audio API (AudioContext, MediaStream)
 * @used_by VoiceButton (optional real-time mode)
 */

export interface AudioStreamConfig {
  sampleRate: number;        // 16000 Hz for STT
  frameSize: number;         // 512-4096 samples (32-256ms)
  channels: number;          // 1 (mono)
  onAudioFrame: (pcm: Float32Array, rms: number) => void;
  onVADChange?: (isSpeaking: boolean) => void;
  onError?: (error: Error) => void;
}

export interface AudioStreamManagerState {
  isStreaming: boolean;
  isSpeaking: boolean;
  currentRMS: number;
}

export class AudioStreamManager {
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private processorNode: ScriptProcessorNode | null = null;
  private isStreaming = false;

  // VAD state
  private vadThreshold = 0.015;    // RMS threshold for speech detection
  private vadSilenceMs = 400;      // Silence duration to detect end of speech
  private lastSpeechTime = 0;
  private isSpeaking = false;
  private currentRMS = 0;

  // Callbacks
  private config: AudioStreamConfig;

  constructor(config: AudioStreamConfig) {
    this.config = config;
  }

  /**
   * Start audio streaming from microphone
   */
  async start(): Promise<void> {
    if (this.isStreaming) {
      // console.warn('[AudioStream] Already streaming');
      return;
    }

    try {
      // Request microphone access
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: this.config.sampleRate,
          channelCount: this.config.channels,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });

      // Create audio context with target sample rate
      this.audioContext = new AudioContext({
        sampleRate: this.config.sampleRate
      });

      // Create source from microphone stream
      this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);

      // Create processor for PCM frames
      // Note: ScriptProcessorNode is deprecated but works everywhere
      // AudioWorklet requires more complex setup with separate file
      this.processorNode = this.audioContext.createScriptProcessor(
        this.config.frameSize,
        this.config.channels,
        this.config.channels
      );

      // Frame counter for periodic logging
      let frameCount = 0;

      this.processorNode.onaudioprocess = (event) => {
        if (!this.isStreaming) return;

        const pcm = event.inputBuffer.getChannelData(0);
        frameCount++;

        // Calculate RMS for VAD
        this.currentRMS = this.calculateRMS(pcm);
        const nowSpeaking = this.currentRMS > this.vadThreshold;

        // Log RMS periodically (every 50 frames ~ 1.5s at 2048 buffer)
        if (frameCount % 50 === 0) {
          // console.log(`[AudioStream] RMS: ${this.currentRMS.toFixed(4)}, threshold: ${this.vadThreshold}, speaking: ${this.isSpeaking}`);
        }

        if (nowSpeaking) {
          this.lastSpeechTime = Date.now();

          if (!this.isSpeaking) {
            this.isSpeaking = true;
            // console.log('[AudioStream] 🎤 Speech STARTED, RMS:', this.currentRMS.toFixed(4));
            this.config.onVADChange?.(true);
          }
        } else if (this.isSpeaking) {
          // Check silence duration
          const silenceTime = Date.now() - this.lastSpeechTime;
          if (silenceTime > this.vadSilenceMs) {
            this.isSpeaking = false;
            // console.log('[AudioStream] 🔇 Speech ENDED after', silenceTime, 'ms silence');
            this.config.onVADChange?.(false);
          }
        }

        // Send PCM frame (copy to avoid buffer reuse issues)
        this.config.onAudioFrame(new Float32Array(pcm), this.currentRMS);
      };

      // Connect: mic → processor → destination (destination required for processing)
      this.sourceNode.connect(this.processorNode);
      // Connect to destination with zero gain (required for onaudioprocess to fire)
      const gainNode = this.audioContext.createGain();
      gainNode.gain.value = 0; // Mute output to avoid feedback
      this.processorNode.connect(gainNode);
      gainNode.connect(this.audioContext.destination);

      this.isStreaming = true;
      // console.log('[AudioStream] Started streaming at', this.config.sampleRate, 'Hz');

    } catch (error) {
      console.error('[AudioStream] Failed to start:', error);
      this.config.onError?.(error as Error);
      throw error;
    }
  }

  /**
   * Stop audio streaming and cleanup
   */
  stop(): void {
    // console.log('[AudioStream] Stopping...');
    this.isStreaming = false;

    if (this.processorNode) {
      this.processorNode.disconnect();
      this.processorNode = null;
    }

    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }

    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }

    this.isSpeaking = false;
    this.currentRMS = 0;

    // console.log('[AudioStream] Stopped');
  }

  /**
   * Calculate RMS (Root Mean Square) for audio level
   */
  private calculateRMS(pcm: Float32Array): number {
    let sum = 0;
    for (let i = 0; i < pcm.length; i++) {
      sum += pcm[i] * pcm[i];
    }
    return Math.sqrt(sum / pcm.length);
  }

  /**
   * Set VAD threshold (0.0 - 1.0)
   */
  setVADThreshold(threshold: number): void {
    this.vadThreshold = Math.max(0.001, Math.min(0.5, threshold));
    // console.log('[AudioStream] VAD threshold set to', this.vadThreshold);
  }

  /**
   * Set silence detection duration (ms)
   */
  setSilenceDuration(ms: number): void {
    this.vadSilenceMs = Math.max(100, Math.min(2000, ms));
    // console.log('[AudioStream] Silence duration set to', this.vadSilenceMs, 'ms');
  }

  /**
   * Get current state
   */
  getState(): AudioStreamManagerState {
    return {
      isStreaming: this.isStreaming,
      isSpeaking: this.isSpeaking,
      currentRMS: this.currentRMS,
    };
  }

  // Getters
  get streaming(): boolean { return this.isStreaming; }
  get speaking(): boolean { return this.isSpeaking; }
  get rms(): number { return this.currentRMS; }
}

/**
 * Convert Float32 PCM to Int16 for transmission
 */
export function float32ToInt16(float32: Float32Array): Int16Array {
  const int16 = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    // Clamp to [-1, 1] and scale to Int16 range
    const sample = Math.max(-1, Math.min(1, float32[i]));
    int16[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
  }
  return int16;
}

/**
 * Convert Int16 array to base64 for Socket.IO transmission
 */
export function int16ToBase64(int16: Int16Array): string {
  const bytes = new Uint8Array(int16.buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

export default AudioStreamManager;
