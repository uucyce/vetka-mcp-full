import { useEffect, useRef } from 'react';

export interface IframeMessage {
  type: 'OPEN_FILE' | 'SET_THEME' | 'SET_READONLY' | 'CLOSE_FILE';
  path?: string;
  theme?: 'dark' | 'light';
  readonly?: boolean;
}

export type PanelEventType =
  | 'FILE_OPENED'
  | 'FILE_CLOSED'
  | 'FILE_SAVED'
  | 'FILE_DIRTY'
  | 'ERROR'
  | 'READY';

export interface PanelEventData {
  path?: string;
  isDirty?: boolean;
  message?: string;
}

interface IframeApiHandlers {
  onOpenFile?: (path: string) => void;
  onCloseFile?: (path: string) => void;
  onSetTheme?: (theme: string) => void;
  onSetReadonly?: (readonly: boolean) => void;
}

/**
 * Hook для получения сообщений от родительского фрейма
 * Используется когда ArtifactPanel встроен в VETKA через iframe
 *
 * IMPORTANT: Uses ref to avoid listener recreation on handler changes
 */
export function useIframeApi(handlers: IframeApiHandlers) {
  // Store handlers in ref to avoid effect re-running on every render
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    console.log('[IframeAPI] 🟢 Listener ATTACHED, my origin:', window.location.origin);

    const messageHandler = (event: MessageEvent<IframeMessage>) => {
      // 🔍 DEBUG: Log ALL incoming messages
      console.log('[IframeAPI] 📨 Message received:', {
        data: event.data,
        origin: event.origin,
        myOrigin: window.location.origin,
        source: event.source === window.parent ? 'parent' : 'other'
      });

      // ✅ Security: Ignore messages from unknown origins
      if (event.origin !== window.location.origin) {
        console.warn('[IframeAPI] ❌ Blocked message from:', event.origin, '(expected:', window.location.origin + ')');
        return;
      }

      if (!event.data || typeof event.data !== 'object') {
        console.log('[IframeAPI] ⚠️ Invalid data format');
        return;
      }
      if (!event.data.type) {
        console.log('[IframeAPI] ⚠️ No type in message');
        return;
      }

      console.log('[IframeAPI] ✅ Processing:', event.data);

      // Access current handlers from ref (always up-to-date)
      const currentHandlers = handlersRef.current;
      console.log('[IframeAPI] 🔧 Handlers available:', {
        onOpenFile: !!currentHandlers.onOpenFile,
        onCloseFile: !!currentHandlers.onCloseFile,
        onSetTheme: !!currentHandlers.onSetTheme,
        onSetReadonly: !!currentHandlers.onSetReadonly
      });

      switch (event.data.type) {
        case 'OPEN_FILE':
          if (event.data.path) {
            console.log('[IframeAPI] 📂 Calling onOpenFile with:', event.data.path);
            currentHandlers.onOpenFile?.(event.data.path);
          }
          break;

        case 'CLOSE_FILE':
          if (event.data.path) {
            currentHandlers.onCloseFile?.(event.data.path);
          }
          break;

        case 'SET_THEME':
          if (event.data.theme) {
            currentHandlers.onSetTheme?.(event.data.theme);
          }
          break;

        case 'SET_READONLY':
          if (event.data.readonly !== undefined) {
            currentHandlers.onSetReadonly?.(event.data.readonly);
          }
          break;

        default:
          console.warn('[IframeAPI] Unknown message type:', (event.data as any).type);
      }
    };

    window.addEventListener('message', messageHandler);
    console.log('[IframeAPI] 🎯 Ready to receive PostMessages');

    return () => {
      window.removeEventListener('message', messageHandler);
      console.log('[IframeAPI] 🔴 Listener REMOVED');
    };
  }, []); // Empty deps - listener is set up once on mount
}

/**
 * Отправить событие родительскому фрейму
 * Используется для оповещения VETKA о действиях пользователя
 */
export function postToParent(type: PanelEventType, data: PanelEventData = {}) {
  if (window.parent && window.parent !== window) {
    // ✅ Security: Use current origin instead of '*'
    const targetOrigin = window.location.origin || '*';
    window.parent.postMessage({ type, ...data }, targetOrigin);
    console.log('[IframeAPI] Sent:', type, data);
  }
}

/**
 * Доступные события для отправки:
 *
 * postToParent('FILE_OPENED', { path })
 * postToParent('FILE_CLOSED', { path })
 * postToParent('FILE_SAVED', { path })
 * postToParent('FILE_DIRTY', { path, isDirty: true })
 * postToParent('ERROR', { message: 'Something failed' })
 * postToParent('READY')
 */
