import { create } from 'zustand';

const VOICE_ONLY_STORAGE_KEY = 'vetka_solo_voice_only_mode';
const REALTIME_STORAGE_KEY = 'vetka_solo_realtime_voice';

type VoiceEventSource = 'voice_sent' | 'text_typed' | 'manual';

interface VoiceModeStore {
  voiceOnlyMode: boolean;
  realtimeVoiceEnabled: boolean;
  lastVoiceEvent?: VoiceEventSource;
  setVoiceOnlyMode: (value: boolean, source?: VoiceEventSource) => void;
  setRealtimeVoiceEnabled: (value: boolean) => void;
  enableVoiceMode: (source?: VoiceEventSource) => void;
  disableVoiceMode: (source?: VoiceEventSource) => void;
}

const readBoolean = (key: string, fallback: boolean): boolean => {
  if (typeof window === 'undefined') return fallback;
  const current = window.localStorage.getItem(key);
  if (current === 'true') return true;
  if (current === 'false') return false;
  return fallback;
};

const persistBoolean = (key: string, value: boolean) => {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(key, String(value));
};

export const useVoiceModeStore = create<VoiceModeStore>((set) => ({
  voiceOnlyMode: readBoolean(VOICE_ONLY_STORAGE_KEY, true),
  realtimeVoiceEnabled: readBoolean(REALTIME_STORAGE_KEY, true),
  lastVoiceEvent: undefined,
  setVoiceOnlyMode(value, source = 'manual') {
    persistBoolean(VOICE_ONLY_STORAGE_KEY, value);
    set(() => ({ voiceOnlyMode: value, lastVoiceEvent: source }));
  },
  setRealtimeVoiceEnabled(value) {
    persistBoolean(REALTIME_STORAGE_KEY, value);
    set(() => ({ realtimeVoiceEnabled: value }));
  },
  enableVoiceMode(source = 'voice_sent') {
    persistBoolean(VOICE_ONLY_STORAGE_KEY, true);
    set(() => ({ voiceOnlyMode: true, lastVoiceEvent: source }));
  },
  disableVoiceMode(source = 'text_typed') {
    persistBoolean(VOICE_ONLY_STORAGE_KEY, false);
    set(() => ({ voiceOnlyMode: false, lastVoiceEvent: source }));
  },
}));
