import type { MycoModeAHint } from '../myco/mycoModeATypes';

export type SearchLaneMode =
  | 'input'
  | 'myco_guidance'
  | 'voice_listening'
  | 'voice_thinking'
  | 'voice_speaking';

export interface SearchLanePayload {
  title: string;
  body: string;
  previewBody: string;
  stateKey: string;
  editable: boolean;
  interactive: boolean;
  source: 'input' | 'myco' | 'voice';
}

export interface SearchLaneResolverInput {
  laneSurface: 'main' | 'chat';
  query: string;
  activeIsSearching: boolean;
  showContextMenu: boolean;
  isFocused: boolean;
  voiceState: 'idle' | 'listening' | 'thinking' | 'speaking';
  onVoiceTrigger?: (() => void) | undefined;
  searchContext: 'vetka' | 'web' | 'file' | 'cloud' | 'social';
  mycoHint?: MycoModeAHint | null;
  mycoStateKey?: string;
  explicitAgentMode?: 'myco' | 'jarvis_vetka';
}

export interface SearchLaneResolvedState {
  surface: 'main' | 'chat';
  mode: SearchLaneMode;
  payload: SearchLanePayload;
  showVoiceTrigger: boolean;
  showVoiceActivity: boolean;
  showThinkingIndicator: boolean;
  showMycoTicker: boolean;
}

export function getLaneIdlePlaceholderText(explicitAgentMode?: 'myco' | 'jarvis_vetka'): string {
  return explicitAgentMode === 'jarvis_vetka'
    ? 'tap vetka to talk or tap text to search'
    : 'tap myco to talk or tap text to search';
}

function buildMycoTickerText(hint: MycoModeAHint | null | undefined): string {
  if (!hint) return '';
  // Keep raw titles for preview/model context, but avoid duplicating the obvious on-screen file/name in the lane text.
  return [hint.body, ...hint.nextActions.slice(0, 2)].filter(Boolean).join('  •  ').trim();
}

function buildMycoPreviewBody(hint: MycoModeAHint | null | undefined): string {
  if (!hint) return '';
  return [hint.body, ...hint.nextActions, hint.shortcuts.join('  | ')].filter(Boolean).join('\n\n');
}

export function resolveSearchLaneState(input: SearchLaneResolverInput): SearchLaneResolvedState {
  const showVoiceTrigger = Boolean(input.onVoiceTrigger && !input.query && !input.activeIsSearching);
  const showVoiceActivity = input.voiceState === 'listening' || input.voiceState === 'speaking';
  const showThinkingIndicator = input.voiceState === 'thinking';
  const showMycoTicker = Boolean(
    input.mycoHint
      && !input.isFocused
      && input.explicitAgentMode === 'myco'
      && !input.query.trim()
      && !input.activeIsSearching
      && !input.showContextMenu
      && !showThinkingIndicator
      && input.voiceState === 'idle',
  );

  if (input.voiceState === 'listening') {
    return {
      surface: input.laneSurface,
      mode: 'voice_listening',
      payload: {
        title: 'VETKA listening',
        body: '',
        previewBody: '',
        stateKey: 'voice_listening',
        editable: false,
        interactive: false,
        source: 'voice',
      },
      showVoiceTrigger,
      showVoiceActivity,
      showThinkingIndicator,
      showMycoTicker,
    };
  }

  if (input.voiceState === 'speaking') {
    return {
      surface: input.laneSurface,
      mode: 'voice_speaking',
      payload: {
        title: 'VETKA speaking',
        body: '',
        previewBody: '',
        stateKey: 'voice_speaking',
        editable: false,
        interactive: false,
        source: 'voice',
      },
      showVoiceTrigger,
      showVoiceActivity,
      showThinkingIndicator,
      showMycoTicker,
    };
  }

  if (input.voiceState === 'thinking') {
    return {
      surface: input.laneSurface,
      mode: 'voice_thinking',
      payload: {
        title: 'VETKA thinking',
        body: '',
        previewBody: '',
        stateKey: 'voice_thinking',
        editable: false,
        interactive: false,
        source: 'voice',
      },
      showVoiceTrigger,
      showVoiceActivity,
      showThinkingIndicator,
      showMycoTicker,
    };
  }

  if (showMycoTicker) {
    return {
      surface: input.laneSurface,
      mode: 'myco_guidance',
      payload: {
        title: input.mycoHint?.title || '',
        body: buildMycoTickerText(input.mycoHint),
        previewBody: buildMycoPreviewBody(input.mycoHint),
        stateKey: input.mycoStateKey || '',
        editable: false,
        interactive: true,
        source: 'myco',
      },
      showVoiceTrigger,
      showVoiceActivity,
      showThinkingIndicator,
      showMycoTicker,
    };
  }

  return {
    surface: input.laneSurface,
    mode: 'input',
      payload: {
        title: '',
        body: '',
        previewBody: getLaneIdlePlaceholderText(input.explicitAgentMode),
        stateKey: input.mycoStateKey || '',
        editable: true,
        interactive: false,
      source: 'input',
    },
    showVoiceTrigger,
    showVoiceActivity,
    showThinkingIndicator,
    showMycoTicker,
  };
}
