/**
 * useTTS - Text-to-Speech hook using browser speechSynthesis API.
 * Auto-detects language and selects appropriate voice.
 *
 * @status active
 * @phase 96
 * @depends react, Web Speech API (speechSynthesis)
 * @used_by MessageBubble
 */

import { useCallback, useState, useRef, useEffect } from 'react';

interface TTSOptions {
  lang?: string;
  rate?: number;
  pitch?: number;
  voice?: string;
}

interface TTSState {
  isSpeaking: boolean;
  isPaused: boolean;
  error: string | null;
}

export function useTTS() {
  const [state, setState] = useState<TTSState>({
    isSpeaking: false,
    isPaused: false,
    error: null,
  });

  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const voicesRef = useRef<SpeechSynthesisVoice[]>([]);

  // Load available voices
  useEffect(() => {
    const loadVoices = () => {
      voicesRef.current = speechSynthesis.getVoices();
    };

    // Voices may load asynchronously
    loadVoices();
    speechSynthesis.onvoiceschanged = loadVoices;

    return () => {
      speechSynthesis.onvoiceschanged = null;
    };
  }, []);

  // Auto-detect language from text
  const detectLanguage = useCallback((text: string): string => {
    // Simple heuristic: check for Cyrillic characters
    const hasCyrillic = /[\u0400-\u04FF]/.test(text);
    if (hasCyrillic) return 'ru-RU';

    // Check for Chinese
    const hasChinese = /[\u4E00-\u9FFF]/.test(text);
    if (hasChinese) return 'zh-CN';

    // Check for Japanese
    const hasJapanese = /[\u3040-\u309F\u30A0-\u30FF]/.test(text);
    if (hasJapanese) return 'ja-JP';

    // Check for German umlauts
    const hasGerman = /[äöüßÄÖÜ]/.test(text);
    if (hasGerman) return 'de-DE';

    // Check for French accents
    const hasFrench = /[àâçéèêëîïôûùüÿœæ]/i.test(text);
    if (hasFrench) return 'fr-FR';

    // Default to English
    return 'en-US';
  }, []);

  // Find best voice for language
  const findVoice = useCallback((lang: string): SpeechSynthesisVoice | null => {
    const voices = voicesRef.current;
    if (voices.length === 0) return null;

    // Prefer local voices over remote
    const localVoice = voices.find(
      (v) => v.lang.startsWith(lang.split('-')[0]) && v.localService
    );
    if (localVoice) return localVoice;

    // Fallback to any matching voice
    const anyVoice = voices.find((v) => v.lang.startsWith(lang.split('-')[0]));
    return anyVoice || null;
  }, []);

  // Speak text
  const speak = useCallback(
    (text: string, options: TTSOptions = {}) => {
      if (!('speechSynthesis' in window)) {
        setState((s) => ({ ...s, error: 'Speech synthesis not supported' }));
        return;
      }

      // Cancel any existing speech
      speechSynthesis.cancel();

      const lang = options.lang || detectLanguage(text);
      const utterance = new SpeechSynthesisUtterance(text);

      utterance.lang = lang;
      utterance.rate = options.rate ?? 0.95;
      utterance.pitch = options.pitch ?? 1.0;

      // Set voice
      const voice = findVoice(lang);
      if (voice) {
        utterance.voice = voice;
      }

      utterance.onstart = () => {
        setState({ isSpeaking: true, isPaused: false, error: null });
      };

      utterance.onend = () => {
        setState({ isSpeaking: false, isPaused: false, error: null });
      };

      utterance.onerror = (event) => {
        console.error('[TTS] Error:', event.error);
        setState({ isSpeaking: false, isPaused: false, error: event.error });
      };

      utterance.onpause = () => {
        setState((s) => ({ ...s, isPaused: true }));
      };

      utterance.onresume = () => {
        setState((s) => ({ ...s, isPaused: false }));
      };

      utteranceRef.current = utterance;
      speechSynthesis.speak(utterance);
    },
    [detectLanguage, findVoice]
  );

  // Stop speaking
  const stop = useCallback(() => {
    speechSynthesis.cancel();
    setState({ isSpeaking: false, isPaused: false, error: null });
  }, []);

  // Pause speaking
  const pause = useCallback(() => {
    if (speechSynthesis.speaking && !speechSynthesis.paused) {
      speechSynthesis.pause();
    }
  }, []);

  // Resume speaking
  const resume = useCallback(() => {
    if (speechSynthesis.paused) {
      speechSynthesis.resume();
    }
  }, []);

  // Get available voices
  const getVoices = useCallback(() => {
    return voicesRef.current;
  }, []);

  return {
    speak,
    stop,
    pause,
    resume,
    getVoices,
    isSpeaking: state.isSpeaking,
    isPaused: state.isPaused,
    error: state.error,
  };
}

export default useTTS;
