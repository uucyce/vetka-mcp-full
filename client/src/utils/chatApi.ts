/**
 * Chat API utilities for sending messages and fetching conversation history.
 *
 * @status active
 * @phase 96
 * @depends ../config/api.config
 * @used_by ./components/chat/ChatPanel, ./components/chat/MessageInput
 */
import { API_BASE } from '../config/api.config';

export interface ChatApiResponse {
  workflow_id?: string;
  conversation_id?: string;
  message?: string;
  error?: string;
}

export async function sendChatMessage(
  message: string,
  nodeId?: string,
  nodePath?: string,  // Phase 27.10: Add node_path for agent context
  conversationId?: string
): Promise<ChatApiResponse> {
  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        node_id: nodeId,
        node_path: nodePath,  // Phase 27.10: Backend needs path for file context
        conversation_id: conversationId,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return response.json();
  } catch (error) {
    console.error('[ChatAPI] Error:', error);
    return {
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

export async function getConversationHistory(conversationId: string): Promise<any[]> {
  try {
    const response = await fetch(`${API_BASE}/chat/history/${conversationId}`);
    if (!response.ok) return [];
    const data = await response.json();
    return data.messages || [];
  } catch {
    return [];
  }
}

// ============================================================
// Phase 100.2: Pinned Files Persistence API
// ============================================================

/**
 * Save pinned file IDs to backend for persistence across reload.
 */
export async function savePinnedFiles(chatId: string, pinnedFileIds: string[]): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/chats/${chatId}/pinned`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pinned_file_ids: pinnedFileIds }),
    });

    if (!response.ok) {
      console.warn('[ChatAPI] Failed to save pinned files:', response.status);
      return false;
    }

    return true;
  } catch (error) {
    console.error('[ChatAPI] Error saving pinned files:', error);
    return false;
  }
}

/**
 * Load pinned file IDs from backend on chat load.
 */
export async function loadPinnedFiles(chatId: string): Promise<string[]> {
  try {
    const response = await fetch(`${API_BASE}/chats/${chatId}/pinned`);
    if (!response.ok) return [];
    const data = await response.json();
    return data.pinned_file_ids || [];
  } catch {
    return [];
  }
}

// ============================================================
// MARKER_136.W3B: Chat-File Links API (Phase 136 Wave 3)
// ============================================================

/**
 * Get all chats that are linked to a specific file path.
 * Returns chats where the file is pinned or mentioned.
 */
export interface LinkedChat {
  id: string;
  display_name: string;
  context_type: string;
  message_count: number;
  last_activity?: string;
}

export async function getChatsForFile(filePath: string): Promise<LinkedChat[]> {
  try {
    const response = await fetch(`${API_BASE}/files/linked-chats?path=${encodeURIComponent(filePath)}`);
    if (!response.ok) return [];
    const data = await response.json();
    return data.chats || [];
  } catch {
    return [];
  }
}

/**
 * Link a file to a chat (save as pinned file in chat).
 */
export async function linkFileToChat(chatId: string, filePath: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/chats/${chatId}/link-file`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: filePath }),
    });
    return response.ok;
  } catch {
    return false;
  }
}
