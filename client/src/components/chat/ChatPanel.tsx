/**
 * ChatPanel - Main chat interface with messages, input, and sidebars.
 * Supports solo and group chat modes with real-time Socket.IO messaging.
 *
 * @status active
 * @phase 96
 * @depends react, lucide-react, useStore, useSocket, MessageList, MessageInput, GroupCreatorPanel, ChatSidebar, ScanPanel, UnifiedSearchBar, ArtifactPanel, FloatingWindow, ModelDirectory
 * @used_by App
 */

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { X, Reply } from 'lucide-react';
import { useStore } from '../../store/useStore';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { WorkflowProgress } from './WorkflowProgress';
import { ModelDirectory } from '../ModelDirectory';
import { GroupCreatorPanel } from './GroupCreatorPanel';
import { useSocket } from '../../hooks/useSocket';
import { FloatingWindow } from '../artifact/FloatingWindow';
import { ArtifactPanel } from '../artifact/ArtifactPanel';
import { ChatSidebar } from './ChatSidebar';
import { ScanPanel, type ScannerEvent } from '../scanner/ScanPanel';
import { UnifiedSearchBar } from '../search/UnifiedSearchBar';
import type { ChatMessage, SearchResult } from '../../types/chat';
import { savePinnedFiles } from '../../utils/chatApi';
import { API_BASE } from '../../config/api.config';

// Phase 48.3: Reply target type
interface ReplyTarget {
  id: string;
  model: string;
  text: string;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  leftPanel: 'none' | 'history' | 'models';
  setLeftPanel: (value: 'none' | 'history' | 'models') => void;
}

export function ChatPanel({ isOpen, onClose, leftPanel, setLeftPanel }: Props) {
  const chatMessages = useStore((s) => s.chatMessages);
  const currentWorkflow = useStore((s) => s.currentWorkflow);
  const isTyping = useStore((s) => s.isTyping);
  // Phase 27.10: Get selected node to pass path to backend for agent context
  const selectedNode = useStore((s) => s.selectedId ? s.nodes[s.selectedId] : null);
  const addChatMessage = useStore((s) => s.addChatMessage);
  const clearChat = useStore((s) => s.clearChat);
  const setIsTyping = useStore((s) => s.setIsTyping);
  const setCameraCommand = useStore((s) => s.setCameraCommand);

  // Phase 61: Pinned files for multi-context
  const pinnedFileIds = useStore((s) => s.pinnedFileIds);
  const nodes = useStore((s) => s.nodes);
  const selectNode = useStore((s) => s.selectNode);
  const togglePinFile = useStore((s) => s.togglePinFile);
  const clearPinnedFiles = useStore((s) => s.clearPinnedFiles);
  // Phase 100.2: Set pinned files from backend persistence
  const setPinnedFiles = useStore((s) => s.setPinnedFiles);

  // Phase 45: Use Socket.IO instead of HTTP
  // Phase 57.3: Added joinGroup, leaveGroup for group creation
  const { sendMessage, isConnected, joinGroup, leaveGroup, sendGroupMessage } = useSocket();

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // MARKER_SCROLL_STATE: State tracking if user is at bottom of chat
  // Phase 107.3: Scroll-to-bottom button state
  // true = at bottom (hide button), false = scrolled up (show down arrow button)
  const [isAtBottom, setIsAtBottom] = useState(true);

  // Phase 81: Resizable chat width (min 380 to fit search bar)
  const [chatWidth, setChatWidth] = useState(() => {
    const saved = localStorage.getItem('vetka_chat_width');
    return saved ? Math.max(380, Number(saved)) : 420;
  });
  const [isResizing, setIsResizing] = useState(false);

  // Phase 81.1: Chat position (left or right side)
  const [chatPosition, setChatPosition] = useState<'left' | 'right'>(() => {
    const saved = localStorage.getItem('vetka_chat_position');
    return (saved === 'right') ? 'right' : 'left';
  });

  // Phase 50.3: Left panel state now comes from App.tsx as props
  const [selectedModel, setSelectedModel] = useState<string | null>(null);

  const [currentChatId, setCurrentChatId] = useState<string | null>(null);

  // Phase 74.3: Current chat info for header display
  const [currentChatInfo, setCurrentChatInfo] = useState<{
    id: string;
    displayName: string | null;
    fileName: string;
    contextType: string;
  } | null>(null);

  // Phase 54.3: Scanner/Chat tab state
  // Phase 56.6: Added 'group' tab
  // Phase 80.12: Removed 'group-settings' - using GroupCreatorPanel edit mode instead
  const [activeTab, setActiveTab] = useState<'chat' | 'scanner' | 'group'>('chat');

  // Phase 56.6: Model selection for group creation
  const [modelForGroup, setModelForGroup] = useState<string | null>(null);

  // Phase 57.3: Active group ID for group chat mode
  const [activeGroupId, setActiveGroupId] = useState<string | null>(null);

  // Phase 80.30: Extract unique models from solo chat messages for @mention
  // MARKER_94.7_SOLO_MODELS: Extract models from chat history for mention popup
  const soloModels = useMemo(() => {
    if (activeGroupId) return []; // Not in solo mode
    const models = new Set<string>();
    chatMessages.forEach(msg => {
      // Extract model from message metadata or model field
      const model = (msg as any).model || (msg as any).metadata?.model;
      if (model && typeof model === 'string') {
        models.add(model);
      }
    });
    // Also add currently selected model if any
    if (selectedModel) {
      models.add(selectedModel);
    }
    return Array.from(models);
  }, [chatMessages, selectedModel, activeGroupId]);

  // Phase 80.22: Current group participants for dynamic @mention dropdown
  const [currentGroupParticipants, setCurrentGroupParticipants] = useState<Array<{
    agent_id: string;
    display_name: string;
    role?: string;
    model_id?: string;
  }>>([]);

  // Phase 80.12: Edit mode state for GroupCreatorPanel
  const [groupEditMode, setGroupEditMode] = useState(false);

  // Phase 54.3 Fix: Track last scanned folder for Hostess context
  const [lastScannedFolder, setLastScannedFolder] = useState<string | null>(null);

  // Phase 60.5: Voice models for smart input detection
  const [voiceModels, setVoiceModels] = useState<string[]>([]);

  // Phase 60.5: Voice-only mode toggle (Trigger 2)
  const [voiceOnlyMode, setVoiceOnlyMode] = useState(false);

  // Phase 60.5: Auto-continue voice after response (Trigger 3)
  const [autoContinueVoice, setAutoContinueVoice] = useState(false);

  // Phase 60.5.1: Realtime voice mode (PCM streaming + VAD)
  const [realtimeVoiceEnabled, setRealtimeVoiceEnabled] = useState(false);

  // Phase I5: Chat drop zone state for file pinning
  const [isDragOver, setIsDragOver] = useState(false);
  const [isScanning, setIsScanning] = useState(false);

  // MARKER_CHAT_AUTOLOAD: Chat doesn't load on app startup
  // Current: ChatSidebar loads chats, but main chat panel starts empty - no useEffect to load last active chat
  // Expected: On mount, restore last active chat or show welcome screen with most recent chat pre-selected
  // Fix: Add useEffect to load from sessionStorage or /api/chats/last-active, then auto-select on mount

  // Phase 60.5: Fetch voice models for smart input detection
  useEffect(() => {
    fetch('/api/models')
      .then(r => r.json())
      .then(data => {
        const models = data.models || [];
        // Filter models with type='voice' and extract IDs
        const voiceIds = models
          .filter((m: any) => m.type === 'voice')
          .map((m: any) => m.id);
        setVoiceModels(voiceIds);
        // console.log('[ChatPanel] Loaded voice models:', voiceIds.length);
      })
      .catch(e => console.warn('[ChatPanel] Failed to load voice models:', e));
  }, []);

  // Phase 54.4: Listen for external event to switch to scanner tab
  useEffect(() => {
    const handleSwitchToScanner = () => {
      // console.log('[ChatPanel] External event: switching to scanner tab');
      setActiveTab('scanner');
    };

    window.addEventListener('vetka-switch-to-scanner', handleSwitchToScanner);
    return () => {
      window.removeEventListener('vetka-switch-to-scanner', handleSwitchToScanner);
    };
  }, []);

  // Phase 57.9: Listen for "Ask Hostess about key" event from ModelDirectory
  useEffect(() => {
    const handleAskHostess = (e: CustomEvent) => {
      const key = e.detail?.key;
      if (!key) return;

      // console.log('[ChatPanel] Ask Hostess about unknown key');

      // Switch to chat tab if not already there
      setActiveTab('chat');

      // Exit any group mode
      setActiveGroupId(null);

      // Set input with @hostess and the key (full key for backend to process)
      setInput(`@hostess please add this API key: ${key}`);

      // Auto-send after a brief delay for user to see
      setTimeout(() => {
        // Trigger send via custom event (avoiding direct call to preserve refs)
        const sendEvent = new CustomEvent('vetka-auto-send-message');
        window.dispatchEvent(sendEvent);
      }, 100);
    };

    window.addEventListener('askHostessAboutKey', handleAskHostess as EventListener);
    return () => {
      window.removeEventListener('askHostessAboutKey', handleAskHostess as EventListener);
    };
  }, []);

  // Phase 57.3: Listen for group chat events
  useEffect(() => {
    // Only listen when we have an active group
    if (!activeGroupId) return;

    const handleGroupMessage = (e: CustomEvent) => {
      const data = e.detail;
      // Only process messages for our active group
      if (data.group_id !== activeGroupId) return;

      // Phase 57.7: Skip agent messages here - they come via group_stream_end
      // This prevents duplicate messages
      if (data.sender_id !== 'user') {
        // console.log('[ChatPanel] Skipping agent echo via group_message:', data.sender_id);
        return;
      }

      // Check for duplicate by ID
      const exists = chatMessages.some(msg => msg.id === data.id);
      if (exists) {
        // console.log('[ChatPanel] Skipping duplicate message:', data.id);
        return;
      }

      // console.log('[ChatPanel] Group message received:', data.sender_id);
      addChatMessage({
        id: data.id || crypto.randomUUID(),
        role: 'user',
        content: data.content,
        type: 'text',
        timestamp: data.created_at || new Date().toISOString(),
      });
    };

    const handleGroupStreamStart = (e: CustomEvent) => {
      const data = e.detail;
      if (data.group_id !== activeGroupId) return;

      // console.log('[ChatPanel] Group stream start:', data.agent_id);
      setIsTyping(true);

      // Create placeholder message for streaming
      addChatMessage({
        id: data.id,
        role: 'assistant',
        agent: data.agent_id.replace('@', ''),
        content: '',
        type: 'text',
        timestamp: new Date().toISOString(),
        metadata: { model: data.model, isStreaming: true },
      });
    };

    const handleGroupStreamToken = (e: CustomEvent) => {
      const data = e.detail;
      if (data.group_id !== activeGroupId) return;

      // Append token to streaming message
      useStore.setState((state) => ({
        chatMessages: state.chatMessages.map((msg) =>
          msg.id === data.id
            ? { ...msg, content: msg.content + data.token }
            : msg
        ),
      }));
    };

    const handleGroupStreamEnd = (e: CustomEvent) => {
      const data = e.detail;
      if (data.group_id !== activeGroupId) return;

      // console.log('[ChatPanel] Group stream end:', data.agent_id);
      setIsTyping(false);

      // Finalize streaming message
      useStore.setState((state) => ({
        chatMessages: state.chatMessages.map((msg) =>
          msg.id === data.id
            ? {
                ...msg,
                content: data.full_message,
                metadata: { ...msg.metadata, isStreaming: false },
              }
            : msg
        ),
      }));
    };

    const handleGroupError = (e: CustomEvent) => {
      const data = e.detail;
      console.error('[ChatPanel] Group error:', data.error);
      addChatMessage({
        id: crypto.randomUUID(),
        role: 'system',
        content: `Group error: ${data.error}`,
        type: 'text',
        timestamp: new Date().toISOString(),
      });
    };

    window.addEventListener('group-message', handleGroupMessage as EventListener);
    window.addEventListener('group-stream-start', handleGroupStreamStart as EventListener);
    window.addEventListener('group-stream-token', handleGroupStreamToken as EventListener);
    window.addEventListener('group-stream-end', handleGroupStreamEnd as EventListener);
    window.addEventListener('group-error', handleGroupError as EventListener);

    return () => {
      window.removeEventListener('group-message', handleGroupMessage as EventListener);
      window.removeEventListener('group-stream-start', handleGroupStreamStart as EventListener);
      window.removeEventListener('group-stream-token', handleGroupStreamToken as EventListener);
      window.removeEventListener('group-stream-end', handleGroupStreamEnd as EventListener);
      window.removeEventListener('group-error', handleGroupError as EventListener);
    };
  }, [activeGroupId, addChatMessage, setIsTyping, chatMessages]);

  // Phase 80.14: HTTP Polling fallback for MCP messages
  // This catches messages that may not arrive via SocketIO
  useEffect(() => {
    if (!activeGroupId) return;

    let lastPollTime = Date.now() / 1000;
    let pollCount = 0;

    const pollMessages = async () => {
      try {
        const response = await fetch(
          `/api/debug/mcp/groups/${activeGroupId}/messages?limit=10`
        );
        if (response.ok) {
          const data = await response.json();
          const messages = data.messages || [];

          // Check for new messages since last poll
          let newMessagesCount = 0;
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          messages.forEach((msg: any) => {
            const msgTime = msg.created_at ? new Date(msg.created_at).getTime() / 1000 : 0;

            // Only process messages newer than last poll and not duplicates
            if (msgTime > lastPollTime) {
              // Check if message already exists by ID
              const exists = chatMessages.some(existing => existing.id === msg.id);
              if (!exists && msg.sender_id && msg.content) {
                // console.log('[Poll] Phase 80.14: New message from polling:', msg.sender_id);
                addChatMessage({
                  id: msg.id || crypto.randomUUID(),
                  role: msg.sender_id === 'user' ? 'user' : 'assistant',
                  content: msg.content,
                  agent: msg.sender_id?.replace('@', ''),
                  type: 'text',
                  timestamp: msg.created_at || new Date().toISOString(),
                });
                newMessagesCount++;
              }
            }
          });

          if (newMessagesCount > 0) {
            console.log(`[Poll] Phase 80.14: Added ${newMessagesCount} new messages via polling`);
          }

          // Update last poll time
          lastPollTime = Date.now() / 1000;
        }
      } catch (e) {
        // Silent fail - polling is a fallback mechanism
        if (pollCount % 10 === 0) {
          console.warn('[Poll] Phase 80.14: Polling error:', e);
        }
      }
      pollCount++;
    };

    // Poll every 3 seconds as fallback
    const interval = setInterval(pollMessages, 3000);

    // Also poll once immediately
    pollMessages();

    return () => clearInterval(interval);
  }, [activeGroupId, chatMessages, addChatMessage]);

  // Phase 80.22: Fetch group participants when activeGroupId changes
  // MARKER_94.7_PARTICIPANT_FETCH: Fetch group participants for mention popup
  useEffect(() => {
    if (!activeGroupId) {
      setCurrentGroupParticipants([]);
      return;
    }

    const fetchParticipants = async () => {
      try {
        const response = await fetch(`/api/groups/${activeGroupId}`);
        if (response.ok) {
          const data = await response.json();
          const participants = data.group?.participants;
          if (participants) {
            // Convert object to array
            const participantsArray = Object.values(participants).map((p: any) => ({
              agent_id: p.agent_id,
              display_name: p.display_name,
              role: p.role,
              model_id: p.model_id
            }));
            setCurrentGroupParticipants(participantsArray);
            console.log('[ChatPanel] Phase 80.22: Loaded', participantsArray.length, 'group participants for @mention');
          }
        }
      } catch (error) {
        console.error('[ChatPanel] Phase 80.22: Error fetching group participants:', error);
      }
    };

    fetchParticipants();
  }, [activeGroupId]);

  // Phase 80.26: Refetch participants when new member added to group
  // Phase 80.29: Also refetch on any system message or "Added" pattern
  useEffect(() => {
    if (!activeGroupId) return;

    const refetchParticipants = () => {
      fetch(`/api/groups/${activeGroupId}`)
        .then(res => res.json())
        .then(data => {
          const participants = data.group?.participants;
          if (participants) {
            const participantsArray = Object.values(participants).map((p: any) => ({
              agent_id: p.agent_id,
              display_name: p.display_name,
              role: p.role,
              model_id: p.model_id
            }));
            // Only update if count changed (avoid unnecessary rerenders)
            if (participantsArray.length !== currentGroupParticipants.length) {
              setCurrentGroupParticipants(participantsArray);
              console.log('[ChatPanel] Phase 80.29: Updated @mention to', participantsArray.length, 'participants');
            }
          }
        })
        .catch(err => console.error('[ChatPanel] Phase 80.29: Error refetching:', err));
    };

    const handleGroupMessage = (event: CustomEvent) => {
      const { content, sender_id } = event.detail || {};
      // Refetch on: system messages, "Added" messages, or any message with model ID pattern
      const shouldRefetch =
        sender_id === 'system' ||
        content?.includes('Added') ||
        content?.includes('to group') ||
        content?.includes('Use @');  // "Use @model-name to mention"

      if (shouldRefetch) {
        console.log('[ChatPanel] Phase 80.29: Detected participant change, refetching');
        refetchParticipants();
      }
    };

    window.addEventListener('group-message', handleGroupMessage as EventListener);
    return () => window.removeEventListener('group-message', handleGroupMessage as EventListener);
  }, [activeGroupId, currentGroupParticipants.length]);

  // Phase 48.3: Reply-to state
  const [replyTo, setReplyTo] = useState<ReplyTarget | null>(null);

  // Phase 80.9: Group ID copy state
  const [groupIdCopied, setGroupIdCopied] = useState(false);

  // Phase 48.5.1 + 68.2: Artifact panel with raw content or file support
  const [artifactData, setArtifactData] = useState<{
    content?: string;
    title: string;
    type?: 'text' | 'markdown' | 'code';
    // Phase 68.2: Support for file loading
    file?: { path: string; name: string; extension?: string };
  } | null>(null);

  // Handle model selection from directory (solo chat mode)
  // Phase 60.4: This is only called when NOT in group mode
  const handleModelSelect = useCallback((modelId: string, _modelName: string) => {
    setSelectedModel(modelId);
    // Phase 57.2: Insert full model ID as @mention (not shortName)
    // This ensures backend can identify the model even if selectedModel is cleared
    setInput(prev => `@${modelId} ${prev}`);
    // Phase 60.4: No need to switch activeTab - this callback is only used in solo chat mode
  }, []);

  // Phase 56.6: Handle model selection for group creation
  // Phase 60.4: Fixed - don't modify input, only set model for group slot
  // Phase 80.12: Simplified - model selection now handled within GroupCreatorPanel
  const handleModelSelectForGroup = useCallback((modelId: string, _modelName: string) => {
    // console.log('[ChatPanel] Model selected for group:', modelId);
    setModelForGroup(modelId);
    // Note: Don't modify input here - only set model for group creation
    // Input modification is handled separately for regular chat mode
  }, []);

  // Phase 57.3: Handle group creation via REST API
  const handleCreateGroup = useCallback(async (name: string, agents: Array<{role: string, model: string | null}>) => {
    // console.log('[ChatPanel] Creating group:', { name, agents });

    // Filter out agents without models
    const validAgents = agents.filter(a => a.model !== null);
    if (validAgents.length === 0) {
      addChatMessage({
        id: crypto.randomUUID(),
        role: 'system',
        content: 'Error: At least one agent must have a model assigned',
        type: 'text',
        timestamp: new Date().toISOString(),
      });
      return;
    }

    try {
      // Step 1: Create group with first agent as admin
      const firstAgent = validAgents[0];
      // Phase 80.8: Include model name in display_name for clarity
      const getDisplayName = (role: string, model: string) => {
        // Extract short model name: 'openai/gpt-4o' -> 'GPT-4o', 'ollama/qwen2:7b' -> 'Qwen2'
        const modelPart = model.split('/').pop() || model;
        const shortName = modelPart.split(':')[0].replace(/-/g, ' ');
        // Capitalize first letter of each word
        const prettyModel = shortName.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
        return `${role} (${prettyModel})`;
      };
      const createResponse = await fetch('/api/groups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          description: `Group chat with ${validAgents.length} agents`,
          admin_agent_id: `@${firstAgent.role}`,
          admin_model_id: firstAgent.model,
          admin_display_name: getDisplayName(firstAgent.role, firstAgent.model!)
        })
      });

      if (!createResponse.ok) {
        const errorData = await createResponse.json();
        throw new Error(errorData.detail || 'Failed to create group');
      }

      const { group } = await createResponse.json();
      const groupId = group.id;
      // console.log('[ChatPanel] Group created:', groupId);

      // Step 2: Add remaining agents as participants
      for (let i = 1; i < validAgents.length; i++) {
        const agent = validAgents[i];
        const addResponse = await fetch(`/api/groups/${groupId}/participants`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            agent_id: `@${agent.role}`,
            model_id: agent.model,
            display_name: getDisplayName(agent.role, agent.model!),  // Phase 80.8: Include model name
            role: 'worker'
          })
        });

        if (!addResponse.ok) {
          // console.warn(`[ChatPanel] Failed to add participant ${agent.role}:`, await addResponse.text());
        }
      }

      // Step 3: Join socket room for real-time messages
      // Phase 80.18: Wait for room join acknowledgment before setting active
      const waitForJoin = new Promise<void>((resolve) => {
        const handler = (e: CustomEvent) => {
          if (e.detail.group_id === groupId) {
            window.removeEventListener('group_joined_ack', handler as EventListener);
            console.log('[ChatPanel] Phase 80.18: Room join confirmed for', groupId);
            resolve();
          }
        };
        window.addEventListener('group_joined_ack', handler as EventListener);
        // Timeout fallback after 2 seconds
        setTimeout(() => {
          window.removeEventListener('group_joined_ack', handler as EventListener);
          console.log('[ChatPanel] Phase 80.18: Join ack timeout, proceeding anyway');
          resolve();
        }, 2000);
      });

      joinGroup(groupId);
      await waitForJoin;

      // Step 4: Store active group ID (now safe - room is joined)
      // console.log('[ChatPanel] Setting activeGroupId to:', groupId);
      setActiveGroupId(groupId);

      // Phase 74.8: Save group chat to history with name
      // Phase 80.5: Include group_id for linking to GroupChatManager
      try {
        const chatResponse = await fetch('/api/chats', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            display_name: name,
            context_type: 'group',
            items: validAgents.map(a => `@${a.role}`),
            group_id: groupId  // Phase 80.5: Link to GroupChatManager
          })
        });

        if (chatResponse.ok) {
          const chatData = await chatResponse.json();
          setCurrentChatId(chatData.chat_id);
          setCurrentChatInfo({
            id: chatData.chat_id,
            displayName: name,
            fileName: 'unknown',
            contextType: 'group'
          });
          // console.log('[ChatPanel] Group chat saved to history:', chatData.chat_id);
        }
      } catch (chatError) {
        console.error('[ChatPanel] Failed to save group chat to history:', chatError);
      }

      // Show success message in chat
      addChatMessage({
        id: crypto.randomUUID(),
        role: 'system',
        content: `Group "${name}" created with ${validAgents.length} agents: ${validAgents.map(a => a.role).join(', ')}\n\nUse @role to mention specific agents (e.g., @PM, @Dev)`,
        type: 'text',
        timestamp: new Date().toISOString(),
      });

      // Phase 57.3: Switch to chat tab AND close left panel
      setActiveTab('chat');
      setLeftPanel('none');

    } catch (error) {
      console.error('[ChatPanel] Group creation error:', error);
      addChatMessage({
        id: crypto.randomUUID(),
        role: 'system',
        content: `Error creating group: ${error instanceof Error ? error.message : 'Unknown error'}`,
        type: 'text',
        timestamp: new Date().toISOString(),
      });
    }
  }, [addChatMessage, joinGroup]);

  const handleSend = useCallback(() => {
    if (!input.trim()) return;

    // Phase 45: Check socket connection
    if (!isConnected) {
      // console.warn('[Chat] Socket not connected');
      addChatMessage({
        id: crypto.randomUUID(),
        role: 'system',
        content: 'Error: Not connected to server',
        type: 'text',
        timestamp: new Date().toISOString(),
      });
      return;
    }

    // Phase 57.3: Debug - log activeGroupId state
    // console.log('[Chat] handleSend - activeGroupId:', activeGroupId);

    // Phase 57.3: If in group mode, send via group_message handler
    // Phase 80.35: Pass replyTo.id for reply routing
    if (activeGroupId) {
      // console.log('[Chat] Sending GROUP message to:', activeGroupId);
      sendGroupMessage(activeGroupId, 'user', input.trim(), replyTo?.id);
      // Don't add user message locally - backend will broadcast it back
      setInput('');
      setReplyTo(null);  // Phase 80.35: Clear reply after sending
      setIsTyping(true);
      return;
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input,
      type: 'text',
      timestamp: new Date().toISOString(),
    };

    addChatMessage(userMessage);

    // console.log('[Chat] Sending message via Socket.IO');

    // Phase 48.3: Use replyTo model if replying, otherwise selectedModel
    // Phase 57.2: Also try to extract model from @mention in input
    let modelToUse = replyTo?.model || selectedModel || undefined;

    // Phase 57.2: If no model selected, try to extract from @mention in input
    // This handles cases like "@nvidia/nemotron-3-nano-30b-a3b:free" typed/pasted directly
    if (!modelToUse) {
      // Match full model IDs including / for provider prefix
      const mentionMatch = input.match(/@([\w\-.:\/]+)/);
      if (mentionMatch) {
        const mentionedModel = mentionMatch[1];
        // Check if it looks like a model ID (contains / or :)
        if (mentionedModel.includes('/') || mentionedModel.includes(':')) {
          modelToUse = mentionedModel;
          // console.log('[Chat] Extracted model from @mention:', modelToUse);
        }
      }
    }

    // Phase 54.3 Fix: Use lastScannedFolder as context when in scanner tab
    const contextPath = selectedNode?.path || (activeTab === 'scanner' && lastScannedFolder ? lastScannedFolder : undefined);
    sendMessage(input.trim(), contextPath, modelToUse);

    // Phase 100.6: Initialize chat header for new solo chat
    // This ensures the header appears immediately when user sends first message
    // Phase 100.6.1: Auto-naming from pinned file, selected node, or message keywords
    if (!currentChatInfo && !activeGroupId) {
      const firstPinnedNode = pinnedFileIds.length > 0 ? nodes[pinnedFileIds[0]] : null;
      const contextType = selectedNode?.type === 'folder' ? 'folder' : 'file';

      // Priority: 1) First pinned file name, 2) Selected node name, 3) Message keywords
      let fileName = firstPinnedNode?.name || selectedNode?.name;

      if (!fileName) {
        // Extract first 4 meaningful words from message (skip common words)
        const skipWords = new Set(['the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'not', 'only', 'same', 'so', 'than', 'too', 'very', 'just', 'and', 'but', 'or', 'nor', 'yet', 'both', 'either', 'neither', 'i', 'me', 'my', 'you', 'your', 'he', 'she', 'it', 'we', 'they', 'this', 'that', 'what', 'which', 'who', 'whom']);
        const words = input.trim()
          .replace(/@[\w\-.:\/]+/g, '')  // Remove @mentions
          .split(/\s+/)
          .filter(w => w.length > 2 && !skipWords.has(w.toLowerCase()))
          .slice(0, 4);
        fileName = words.length > 0 ? words.join(' ') : 'New Chat';
      }

      setCurrentChatInfo({
        id: crypto.randomUUID(),
        displayName: null,
        fileName,
        contextType,
      });
    }

    setInput('');
    setSelectedModel(null);
    setReplyTo(null);  // Clear reply after sending
    setIsTyping(true);
  }, [input, isConnected, selectedNode, selectedModel, replyTo, addChatMessage, sendMessage, setIsTyping, activeTab, lastScannedFolder, activeGroupId, sendGroupMessage, currentChatInfo, pinnedFileIds, nodes]);

  // Phase 57.9: Listen for auto-send event (triggered by Ask Hostess button)
  useEffect(() => {
    const handleAutoSend = () => {
      if (input.trim()) {
        // console.log('[ChatPanel] Auto-sending message:', input.slice(0, 50) + '...');
        handleSend();
      }
    };

    window.addEventListener('vetka-auto-send-message', handleAutoSend);
    return () => {
      window.removeEventListener('vetka-auto-send-message', handleAutoSend);
    };
  }, [input, handleSend]);

  // Phase 48.3: Handle reply callback
  const handleReply = useCallback((msg: ReplyTarget) => {
    setReplyTo(msg);
    setSelectedModel(null);  // Clear model selection when replying
  }, []);

  // Phase 48.5.1: Handle open artifact callback - use ArtifactPanel
  const handleOpenArtifact = useCallback((_id: string, content: string, agent?: string) => {
    setArtifactData({
      content,
      title: agent ? `Response from ${agent}` : 'Full Response',
      type: 'text'
    });
  }, []);

  // Phase 68: Search handlers
  const handleSearchSelect = useCallback((result: SearchResult) => {
    // Select node in 3D tree
    if (result.path) {
      selectNode(result.path);
      // Focus camera on selected file
      setCameraCommand({
        target: result.path,
        zoom: 'close',
        highlight: true
      });
    }
  }, [selectNode, setCameraCommand]);

  const handleSearchPin = useCallback((result: SearchResult) => {
    // Pin file to context using the path as ID
    if (result.path) {
      // Find node by path and toggle pin
      const nodeId = Object.keys(nodes).find(id => nodes[id]?.path === result.path);
      if (nodeId) {
        togglePinFile(nodeId);
      }
    }
  }, [nodes, togglePinFile]);

  // Phase 74.3: Rename chat from header
  // MARKER_GROUP_RENAME_UI: Phase 108.5 - Support group chat renaming
  const handleRenameChatFromHeader = useCallback(async () => {
    // Phase 108.5: Handle both regular chats and group chats
    if (activeGroupId) {
      // Group chat mode - rename via /api/groups/{id}
      const currentName = currentChatInfo?.displayName || currentChatInfo?.fileName || 'Group Chat';
      const newName = prompt('Enter new name for this group:', currentName);

      if (!newName || newName.trim() === '' || newName.trim() === currentName) {
        return;
      }

      try {
        // MARKER_GROUP_RENAME_BUG: Only updates /api/groups, not /api/chats
        // Group name is stored in TWO places:
        // 1. /api/groups/{id} (GroupChatManager - source of truth)
        // 2. /api/chats/{currentChatId} with context_type='group' (chat history)
        // PROBLEM: This code only updates #1, leaving chat history out of sync
        // RESULT: Sidebar shows old name until page reload (loads from chat history)
        // FIX_NEEDED: After renaming group, also update chat history entry via PATCH /api/chats/{currentChatId}
        const response = await fetch(`/api/groups/${activeGroupId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: newName.trim() })
        });

        if (response.ok) {
          setCurrentChatInfo(prev => prev ? { ...prev, displayName: newName.trim() } : null);
          console.log(`[ChatPanel] Phase 108.5: Renamed group to "${newName.trim()}"`);

          // MARKER_GROUP_RENAME_SYNC: Sync with chat history for sidebar
          // This ensures sidebar shows updated name immediately without page reload
          if (currentChatId) {
            try {
              await fetch(`/api/chats/${currentChatId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ display_name: newName.trim() })
              });
              console.log('[ChatPanel] Synced group rename to chat history');
            } catch (e) {
              console.warn('[ChatPanel] Failed to sync chat history:', e);
            }
          }
        } else {
          console.error(`[ChatPanel] Error renaming group: ${response.status}`);
        }
      } catch (error) {
        console.error('[ChatPanel] Error renaming group:', error);
      }
    } else {
      // Regular chat mode - rename via /api/chats/{id}
      if (!currentChatInfo) return;

      const currentName = currentChatInfo.displayName || currentChatInfo.fileName;
      const newName = prompt('Enter new name for this chat:', currentName);

      if (!newName || newName.trim() === '' || newName.trim() === currentName) {
        return;
      }

      try {
        const response = await fetch(`/api/chats/${currentChatInfo.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ display_name: newName.trim() })
        });

        if (response.ok) {
          setCurrentChatInfo(prev => prev ? { ...prev, displayName: newName.trim() } : null);
        } else {
          console.error(`[ChatPanel] Error renaming chat: ${response.status}`);
        }
      } catch (error) {
        console.error('[ChatPanel] Error renaming chat:', error);
      }
    }
  }, [currentChatInfo, activeGroupId]);

  // Phase 107.2: New Chat button handler
  const handleNewChat = useCallback(() => {
    // 1. Clear current chat state
    clearChat();

    // 2. Reset chat info
    setCurrentChatInfo(null);
    setCurrentChatId(null);

    // 3. Leave group if in group chat
    if (activeGroupId) {
      leaveGroup(activeGroupId);
      setActiveGroupId(null);
    }

    console.log('[ChatPanel] Started new chat');
  }, [clearChat, activeGroupId, leaveGroup]);

  // Phase 50.1: Handle selecting a chat from history
  // Phase 52.2: Added camera focus on chat selection
  // Phase 74.3: Store chat info for header display
  // Phase 100.2: Load pinned files from backend instead of clearing
  const handleSelectChat = useCallback(async (chatId: string, filePath: string, fileName: string) => {
    setCurrentChatId(chatId);
    setLeftPanel('none');

    try {
      const response = await fetch(`/api/chats/${chatId}`);
      if (response.ok) {
        const data = await response.json();
        // console.log(`[ChatPanel] Loaded chat ${fileName} with ${data.messages?.length || 0} messages`);

        // Phase 100.2: Load pinned files from backend (replaces clearPinnedFiles)
        const savedPins = data.pinned_file_ids || [];
        setPinnedFiles(savedPins);
        // console.log(`[ChatPanel] Loaded ${savedPins.length} pinned files for chat ${chatId}`);

        // Phase 74.3: Store chat info for header
        setCurrentChatInfo({
          id: chatId,
          displayName: data.display_name || null,
          fileName: data.file_name || fileName,
          contextType: data.context_type || 'file'
        });

        // Clear current chat and load history messages
        clearChat();

        // Phase 80.5: If group chat, load from GroupChatManager and join room
        if (data.context_type === 'group' && data.group_id) {
          const groupId = data.group_id;

          // Phase 80.18: Wait for room join acknowledgment before setting active
          const waitForJoin = new Promise<void>((resolve) => {
            const handler = (e: CustomEvent) => {
              if (e.detail.group_id === groupId) {
                window.removeEventListener('group_joined_ack', handler as EventListener);
                console.log('[ChatPanel] Phase 80.18: Room join confirmed for', groupId);
                resolve();
              }
            };
            window.addEventListener('group_joined_ack', handler as EventListener);
            // Timeout fallback after 2 seconds
            setTimeout(() => {
              window.removeEventListener('group_joined_ack', handler as EventListener);
              console.log('[ChatPanel] Phase 80.18: Join ack timeout, proceeding anyway');
              resolve();
            }, 2000);
          });

          // Join socket room for real-time messages
          joinGroup(groupId);
          await waitForJoin;
          setActiveGroupId(groupId);

          // Phase 108.5: Fetch group details to get current name
          try {
            const groupDetailsResponse = await fetch(`/api/groups/${groupId}`);
            if (groupDetailsResponse.ok) {
              const groupDetailsData = await groupDetailsResponse.json();
              const groupName = groupDetailsData.group?.name || data.display_name || 'Group Chat';
              // Update currentChatInfo with actual group name
              setCurrentChatInfo(prev => prev ? { ...prev, displayName: groupName } : prev);
              console.log(`[ChatPanel] Phase 108.5: Loaded group name: "${groupName}"`);
            }
          } catch (groupDetailsError) {
            console.error('[ChatPanel] Phase 108.5: Error loading group details:', groupDetailsError);
          }

          // Load group messages from API
          try {
            const groupResponse = await fetch(`/api/groups/${groupId}/messages?limit=50`);
            if (groupResponse.ok) {
              const groupData = await groupResponse.json();
              // console.log(`[ChatPanel] Loaded ${groupData.messages?.length || 0} group messages`);

              for (const msg of groupData.messages || []) {
                addChatMessage({
                  id: msg.id || crypto.randomUUID(),
                  role: msg.sender_id === 'user' ? 'user' : 'assistant',
                  content: msg.content,
                  agent: msg.sender_id?.replace('@', ''),
                  type: 'text',
                  timestamp: msg.created_at || new Date().toISOString(),
                });
              }
            }
          } catch (groupError) {
            console.error('[ChatPanel] Error loading group messages:', groupError);
          }
        } else {
          // Regular chat - load from chat history
          for (const msg of data.messages || []) {
            addChatMessage({
              id: msg.id || crypto.randomUUID(),
              role: msg.role,
              content: msg.content,
              agent: msg.agent,
              type: msg.role === 'user' ? 'text' : 'text',
              timestamp: msg.timestamp || new Date().toISOString(),
            });
          }
        }

        // Phase 52.2: Focus camera on the file
        if (filePath && data.context_type !== 'group') {
          // console.log(`[ChatPanel] Requesting camera focus on: ${filePath}`);

          // Trigger camera animation via store
          setCameraCommand({
            target: filePath,
            zoom: 'close',
            highlight: true
          });
        }
      } else {
        console.error(`[ChatPanel] Error loading chat: ${response.status}`);
      }
    } catch (error) {
      console.error('[ChatPanel] Error loading chat history:', error);
    }
  }, [addChatMessage, clearChat, setPinnedFiles, setCameraCommand, joinGroup, setActiveGroupId]);

  // Phase 100.2: Auto-save pinned files when they change
  // Uses debounce to avoid excessive API calls
  useEffect(() => {
    if (!currentChatId) return;

    // Debounce save by 500ms
    const timeoutId = setTimeout(() => {
      savePinnedFiles(currentChatId, pinnedFileIds);
      // console.log(`[ChatPanel] Auto-saved ${pinnedFileIds.length} pinned files for chat ${currentChatId}`);
    }, 500);

    return () => clearTimeout(timeoutId);
  }, [currentChatId, pinnedFileIds]);

  // Phase I2: REMOVED auto-switch chat on selectedNode change
  // Previously (Phase 52.1-74.2): This useEffect cleared chat and loaded history
  // when selectedNode.path changed. This caused chat to reset when files were
  // added via drag-and-drop, because selectedNode could change.
  //
  // New behavior: Chat persists until user explicitly switches via:
  // 1. Sidebar (handleSelectChat) - loads chat history
  // 2. "New Chat" button - clears chat
  //
  // The selectedNode is still used for context when sending messages,
  // but it no longer triggers chat switching.

  // Phase 50.4: Smart auto-scroll - only if already at bottom
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;

    // Check if user is already at bottom (within 100px tolerance)
    const atBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;

    // Only auto-scroll if already at bottom (don't interrupt user scrolling)
    if (atBottom) {
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 0);
    }
  }, [chatMessages.length]); // Only on new messages, not on content changes (streaming)

  // Phase 107.3: Track scroll position for scroll-to-bottom button
  // MARKER_SCROLL_STATE: Track if user is at bottom of message list
  // Formula: scrollHeight - scrollTop - clientHeight < 50px threshold
  const handleScroll = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    // When near bottom (within 50px), isAtBottom = true, hide scroll button
    // When scrolled up, isAtBottom = false, show scroll button with down arrow
    const atBottom = scrollHeight - scrollTop - clientHeight < 50;
    // DEBUG: Log scroll state changes
    if (atBottom !== isAtBottom) {
      console.log('[ChatPanel] Scroll state changed:', { atBottom, scrollTop, scrollHeight, clientHeight, diff: scrollHeight - scrollTop - clientHeight });
    }
    setIsAtBottom(atBottom);
  }, [isAtBottom]);

  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      // MARKER_SCROLL_BTN_TOGGLE_FIX: Initialize scroll state on mount
      handleScroll(); // Detect initial scroll position
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, [handleScroll]);

  // DEBUG: Log button visibility state
  useEffect(() => {
    console.log('[ChatPanel] Scroll button visibility:', !isAtBottom ? 'VISIBLE' : 'HIDDEN', { isAtBottom });
  }, [isAtBottom]);

  // Phase 54.3 Fix: Auto-hide sidebars when SWITCHING to scanner (not continuously)
  // Phase 92.9 Fix: Removed leftPanel from deps - was causing panels to close immediately
  useEffect(() => {
    if (activeTab === 'scanner') {
      setLeftPanel('none');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]); // Only trigger on tab change, not on leftPanel change!

  // Phase 54.3 Fix: Hostess greeting when scanner tab opens
  useEffect(() => {
    if (activeTab === 'scanner') {
      // Add Hostess greeting message
      const greetings = [
        'Hi! Select a folder to scan. I will add all files to your Vetka!',
        'Welcome to Scanner! Start with your project root - I will find everything recursively',
        'Ready to scan? Add a folder and watch your Vetka grow!',
      ];
      const greeting = greetings[Math.floor(Math.random() * greetings.length)];

      // Add as Hostess message
      addChatMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        agent: 'Hostess',
        content: greeting,
        type: 'text',
        timestamp: new Date().toISOString(),
      });
    }
  }, [activeTab]); // Only trigger on tab change

  // Phase 81: Handle resize mouse events
  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      let newWidth: number;

      if (chatPosition === 'left') {
        // Chat on LEFT: handle on RIGHT edge, drag RIGHT = increase width
        const leftOffset = leftPanel !== 'none' ? 380 : 0;
        newWidth = e.clientX - leftOffset;
      } else {
        // Chat on RIGHT: handle on LEFT edge, drag LEFT = increase width
        newWidth = window.innerWidth - e.clientX;
      }

      // Clamp between 380px (fit search bar) and 700px
      const clampedWidth = Math.max(380, Math.min(700, newWidth));
      setChatWidth(clampedWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      // Save to localStorage on resize end
      localStorage.setItem('vetka_chat_width', String(chatWidth));
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, leftPanel, chatWidth, chatPosition]);

  // Phase 81.1: Toggle chat position
  const toggleChatPosition = () => {
    const newPosition = chatPosition === 'left' ? 'right' : 'left';
    setChatPosition(newPosition);
    localStorage.setItem('vetka_chat_position', newPosition);
  };

  // Phase 80.9: Copy group ID to clipboard
  const copyGroupId = useCallback(() => {
    if (!activeGroupId) return;
    navigator.clipboard.writeText(activeGroupId);
    setGroupIdCopied(true);
    setTimeout(() => setGroupIdCopied(false), 2000);
  }, [activeGroupId]);

  // Phase 54.4: Handle scanner events for Hostess with file type summary
  const handleScannerEvent = useCallback((event: ScannerEvent) => {
    let hostessMessage = '';

    switch (event.type) {
      case 'directory_added':
        // Save last scanned folder for context
        if (event.path) {
          setLastScannedFolder(event.path);
        }

        // Build file type summary if available
        let typeSummary = '';
        if (event.fileTypes) {
          const topTypes = Object.entries(event.fileTypes)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 3)
            .map(([ext, count]) => `${count} .${ext}`)
            .join(', ');
          typeSummary = topTypes ? ` (${topTypes})` : '';
        }

        if (event.filesCount && event.filesCount > 1000) {
          hostessMessage = `Wow! ${event.filesCount} files from "${event.path}"${typeSummary}! This is a serious project!`;
        } else if (event.filesCount && event.filesCount > 100) {
          hostessMessage = `Great! ${event.filesCount} files from "${event.path}"${typeSummary} added to your Vetka`;
        } else if (event.filesCount && event.filesCount > 0) {
          hostessMessage = `${event.filesCount} files from "${event.path}"${typeSummary}. Drop more folders to grow your tree!`;
        } else {
          hostessMessage = `"${event.path}" added! Files will be indexed.`;
        }
        break;

      case 'directory_removed':
        hostessMessage = 'Directory removed.';
        break;

      case 'scan_complete':
        hostessMessage = 'Scan complete! Your tree is ready.';
        break;

      case 'scan_error':
        hostessMessage = `${event.error || 'Something went wrong'}. Try dropping again?`;
        break;

      case 'files_dropped':
        // Phase 54.4: Global drop event
        if (event.filesCount && event.path) {
          hostessMessage = `Dropped ${event.filesCount} files from "${event.path}"`;
        }
        break;
    }

    if (hostessMessage) {
      addChatMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        agent: 'Hostess',
        content: hostessMessage,
        type: 'text',
        timestamp: new Date().toISOString(),
      });
    }
  }, [addChatMessage]);

  // Phase I5: Handle file drop on chat panel - scan and pin file
  const handleFileDrop = useCallback(async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    // Get file path from dataTransfer
    // For Tauri/native drops, the path comes from files[0].path
    // For HTML5 drops, we may get file:// URLs or paths in text/plain
    const files = e.dataTransfer.files;
    const textData = e.dataTransfer.getData('text/plain');

    let filePath: string | null = null;

    if (files.length > 0) {
      // Native file drop - get path
      const file = files[0];
      // @ts-ignore - path is available in Tauri/Electron context
      filePath = file.path || null;

      // Fallback: try to extract from webkitRelativePath or name
      if (!filePath && file.webkitRelativePath) {
        filePath = file.webkitRelativePath;
      }
    }

    // Fallback: try text data (might be file path or file:// URL)
    if (!filePath && textData) {
      if (textData.startsWith('file://')) {
        // Remove file:// prefix and decode
        filePath = decodeURIComponent(textData.replace('file://', ''));
      } else if (textData.startsWith('/')) {
        // Already an absolute path
        filePath = textData;
      }
    }

    if (!filePath) {
      console.warn('[ChatPanel] I5: No file path found in drop event');
      addChatMessage({
        id: crypto.randomUUID(),
        role: 'system',
        content: 'Could not get file path from drop. Try dragging from Finder.',
        type: 'text',
        timestamp: new Date().toISOString(),
      });
      return;
    }

    console.log('[ChatPanel] I5: Dropped file path:', filePath);
    setIsScanning(true);

    try {
      // Step 1: Scan file via API
      const response = await fetch(`${API_BASE}/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: filePath })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `Scan failed: ${response.status}`);
      }

      const scanResult = await response.json();
      console.log('[ChatPanel] I5: Scan result:', scanResult);

      // Step 2: Find node by path and pin it
      // Wait a bit for store to update with new nodes from scan
      setTimeout(() => {
        const currentNodes = useStore.getState().nodes;
        const nodeEntry = Object.entries(currentNodes).find(([_, node]) => node.path === filePath);

        if (nodeEntry) {
          const [nodeId, node] = nodeEntry;
          togglePinFile(nodeId);

          addChatMessage({
            id: crypto.randomUUID(),
            role: 'assistant',
            agent: 'Hostess',
            content: `Pinned "${node.name}" to context. It will be included in your next message.`,
            type: 'text',
            timestamp: new Date().toISOString(),
          });
        } else {
          // File might be new - show success anyway
          addChatMessage({
            id: crypto.randomUUID(),
            role: 'assistant',
            agent: 'Hostess',
            content: `Scanned "${filePath!.split('/').pop()}". Refresh tree to see it.`,
            type: 'text',
            timestamp: new Date().toISOString(),
          });
        }

        setIsScanning(false);
      }, 500);

    } catch (error) {
      console.error('[ChatPanel] I5: Scan error:', error);
      setIsScanning(false);

      addChatMessage({
        id: crypto.randomUUID(),
        role: 'system',
        content: `Error scanning file: ${error instanceof Error ? error.message : 'Unknown error'}`,
        type: 'text',
        timestamp: new Date().toISOString(),
      });
    }
  }, [addChatMessage, togglePinFile]);

  // Phase I5: Drag event handlers
  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    // Only set false if leaving the drop zone entirely (not entering a child)
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsDragOver(false);
    }
  }, []);

  if (!isOpen) return null;

  // Phase 50.1: SVG History Icon
  const HistoryIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );

  // Phase 54.3: SVG Scanner/Folder Icon
  const ScannerIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
    </svg>
  );

  // Phase 56.7: AI-Human chat icon (robot + human silhouette)
  const AIHumanIcon = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      {/* Robot head */}
      <rect x="3" y="6" width="10" height="8" rx="1.5" />
      <circle cx="6" cy="10" r="1" fill="currentColor" />
      <circle cx="10" cy="10" r="1" fill="currentColor" />
      <line x1="6" y1="12.5" x2="10" y2="12.5" />
      <line x1="8" y1="6" x2="8" y2="4" />
      <circle cx="8" cy="3.5" r="0.5" fill="currentColor" />
      {/* Human silhouette (smaller, right side) */}
      <circle cx="18" cy="7" r="2.5" />
      <path d="M14 20v-3a4 4 0 0 1 4-4h0a4 4 0 0 1 4 4v3" />
    </svg>
  );

  return (
    <>
      {/* Phase 50.1: Left sidebar (mutually exclusive) */}
      {leftPanel === 'history' && (
        <ChatSidebar
          isOpen={true}
          onSelectChat={handleSelectChat}
          currentChatId={currentChatId || undefined}
          onClose={() => setLeftPanel('none')}
        />
      )}

      {leftPanel === 'models' && (
        <ModelDirectory
          isOpen={true}
          onClose={() => {
            setLeftPanel('none');
          }}
          onSelect={handleModelSelect}
          // Phase 57.10: isGroupMode only when creating a group (not when in active group chat)
          // Phase 80.12: Also enable in edit mode (activeGroupId + group tab)
          // Phase 80.19: Also enable when we have activeGroupId for direct model addition
          isGroupMode={(activeTab === 'group' && !activeGroupId) || (activeTab === 'group' && groupEditMode) || !!activeGroupId}
          onSelectForGroup={handleModelSelectForGroup}
          // Phase 80.19: Direct model addition to existing group
          activeGroupId={activeGroupId}
          hasActiveSlot={activeTab === 'group' && (groupEditMode || !activeGroupId)}
          onModelAddedDirect={(participant) => {
            // console.log('[ChatPanel] Model added directly to group:', participant);
            // Notify user
            addChatMessage({
              id: crypto.randomUUID(),
              role: 'system',
              content: `Added ${participant.display_name} (${participant.agent_id}) to group. Use ${participant.agent_id} to mention.`,
              type: 'text',
              timestamp: new Date().toISOString(),
            });
            // Phase 80.32: Force refetch participants for @mention dropdown
            if (activeGroupId) {
              fetch(`/api/groups/${activeGroupId}`)
                .then(res => res.json())
                .then(data => {
                  const participants = data.group?.participants;
                  if (participants) {
                    const participantsArray = Object.values(participants).map((p: any) => ({
                      agent_id: p.agent_id,
                      display_name: p.display_name,
                      role: p.role,
                      model_id: p.model_id
                    }));
                    setCurrentGroupParticipants(participantsArray);
                    console.log('[ChatPanel] Phase 80.32: Refreshed @mention to', participantsArray.length, 'participants after model add');
                  }
                })
                .catch(err => console.error('[ChatPanel] Phase 80.32: Refetch error:', err));
            }
          }}
        />
      )}

      {/* Phase 50.2: Chat panel - fixed width, doesn't shift */}
      {/* Phase 62.1: Semi-transparent with blur - 3D canvas visible through */}
      {/* Phase 69.4: Increased width to match search panel (380px) */}
      {/* Phase 81: Resizable width with handle */}
      {/* Phase 81.1: Position can be left or right */}
      {/* Phase I5: Drop zone for file pinning */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleFileDrop}
        style={{
        position: 'fixed',
        ...(chatPosition === 'left'
          ? { left: leftPanel !== 'none' ? 380 : 0, borderRight: '1px solid rgba(34, 34, 34, 0.8)' }
          : { right: 0, borderLeft: '1px solid rgba(34, 34, 34, 0.8)' }
        ),
        top: 0,
        bottom: 0,
        width: chatWidth,
        background: 'rgba(10, 10, 10, 0.88)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 100,
        transition: 'left 0.3s ease, right 0.3s ease'
      }}>
        {/* Phase 81: Resize handle - position depends on chat side */}
        <div
          onMouseDown={() => setIsResizing(true)}
          style={{
            position: 'absolute',
            ...(chatPosition === 'left' ? { right: -6 } : { left: -6 }),
            top: 0,
            bottom: 0,
            width: 12,
            cursor: 'col-resize',
            background: 'transparent',
            zIndex: 102
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
          }}
          onMouseLeave={(e) => {
            if (!isResizing) {
              e.currentTarget.style.background = 'transparent';
            }
          }}
        />

        {/* Phase I5: Drop overlay indicator */}
        {isDragOver && (
          <div style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(74, 170, 102, 0.15)',
            border: '2px dashed rgba(74, 170, 102, 0.6)',
            borderRadius: 8,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 200,
            pointerEvents: 'none',
          }}>
            <div style={{
              background: 'rgba(0, 0, 0, 0.8)',
              padding: '16px 24px',
              borderRadius: 8,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 8,
            }}>
              {/* Pin icon */}
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#4aa866" strokeWidth="2">
                <path d="M12 17v5M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z" />
              </svg>
              <span style={{ color: '#4aa866', fontSize: 14, fontWeight: 500 }}>
                Drop to pin file
              </span>
              <span style={{ color: '#888', fontSize: 11 }}>
                File will be added to context
              </span>
            </div>
          </div>
        )}

        {/* Phase I5: Scanning indicator */}
        {isScanning && (
          <div style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 200,
          }}>
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 12,
            }}>
              {/* Spinner */}
              <div style={{
                width: 32,
                height: 32,
                border: '3px solid #333',
                borderTopColor: '#4aa866',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
              }} />
              <span style={{ color: '#aaa', fontSize: 13 }}>Scanning file...</span>
              <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </div>
          </div>
        )}

        {/* Header with selected file info - Phase 27.12 */}
        {/* Phase 62.1: Semi-transparent header */}
        <div style={{
          padding: '8px 16px',
          borderBottom: '1px solid rgba(34, 34, 34, 0.8)',
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
          background: 'rgba(15, 15, 15, 0.7)',
        }}>
          {/* Phase 56.7: Redesigned header - AI-Chat LEFT, Scanner/Close RIGHT */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}>
          {/* LEFT SIDE: AI-Chat toggle (Chat/Group mode) */}
          {/* Phase 57: Same icon for both modes, dim when group panel open */}
          {/* Phase 60.4: Don't auto-open Model Directory when entering group mode */}
          {/* Phase 80.12: Team settings tab - when activeGroupId, show Team button that opens settings */}
          {/* Phase 80.23: Team button opens GroupCreatorPanel in editMode (Group Settings) */}
          <button
            onClick={() => {
              if (activeGroupId) {
                // Phase 80.23: In active group - Team button opens Group Settings (beautiful panel)
                setGroupEditMode(true);
                setActiveTab('group');
                setLeftPanel('models');  // Phase 80.34: Auto-open Model Directory
              } else if (activeTab === 'group') {
                // Exit group creation mode -> back to chat
                setActiveTab('chat');
              } else {
                // Enter group creation mode
                setActiveTab('group');
                setLeftPanel('models');  // Phase 80.34: Auto-open Model Directory (телефонная книга)
              }
            }}
            style={{
              background: '#1a1a1a',
              border: 'none',
              borderRadius: 4,
              padding: '6px 10px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              transition: 'all 0.2s',
              opacity: (activeTab === 'group' && !activeGroupId) ? 0.5 : 1
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = '#222';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = '#1a1a1a';
            }}
            title={activeGroupId ? 'Model Directory' : (activeTab === 'group' ? 'Exit Group Mode' : 'Create Team')}
          >
            <div style={{ color: activeGroupId ? '#6a8' : '#888', transition: 'color 0.2s' }}>
              {/* Phase 80.12: Show users icon when in active group */}
              {activeGroupId ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                  <circle cx="9" cy="7" r="4"/>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                  <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                </svg>
              ) : (
                <AIHumanIcon />
              )}
            </div>
            <span style={{
              color: activeGroupId ? '#6a8' : '#888',
              fontWeight: 500,
              fontSize: 12,
              transition: 'color 0.2s'
            }}>
              {activeGroupId ? 'Team' : (activeTab === 'group' ? 'Team' : 'Chat')}
            </span>
          </button>

          {/* History button (in chat, group, or scanner mode) */}
          {/* Phase 92.8: Also show in scanner mode */}
          {(activeTab === 'chat' || activeTab === 'group' || activeTab === 'scanner') && (
            <button
              onClick={() => setLeftPanel(leftPanel === 'history' ? 'none' : 'history')}
              style={{
                background: leftPanel === 'history' ? '#1a1a1a' : 'transparent',
                border: 'none',
                borderRadius: 4,
                padding: 6,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                if (leftPanel !== 'history') {
                  (e.currentTarget as HTMLButtonElement).style.background = '#1a1a1a';
                }
              }}
              onMouseLeave={(e) => {
                if (leftPanel !== 'history') {
                  (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
                }
              }}
              title="Chat History"
            >
              <div style={{ color: leftPanel === 'history' ? '#fff' : '#555', transition: 'color 0.2s' }}>
                <HistoryIcon />
              </div>
            </button>
          )}

          {/* Phase 57.10: Model Directory button - shows in chat mode, group mode, scanner, or active group */}
          {/* Phase 60.4: Also show in group mode for model selection */}
          {/* Phase 92.8: Also show in scanner mode */}
          {(activeTab === 'chat' || activeTab === 'group' || activeTab === 'scanner' || activeGroupId) && (
            <button
              onClick={() => setLeftPanel(leftPanel === 'models' ? 'none' : 'models')}
              style={{
                background: leftPanel === 'models' ? '#1a1a1a' : 'transparent',
                border: 'none',
                borderRadius: 4,
                padding: 6,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                if (leftPanel !== 'models') {
                  (e.currentTarget as HTMLButtonElement).style.background = '#1a1a1a';
                }
              }}
              onMouseLeave={(e) => {
                if (leftPanel !== 'models') {
                  (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
                }
              }}
              title="Model Directory"
            >
              <div style={{ color: leftPanel === 'models' ? '#fff' : '#555', transition: 'color 0.2s' }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
                </svg>
              </div>
            </button>
          )}

          {/* Spacer */}
          <div style={{ flex: 1 }} />

          {/* RIGHT SIDE: Scanner + Close */}
          <button
            onClick={() => setActiveTab(activeTab === 'scanner' ? 'chat' : 'scanner')}
            style={{
              background: activeTab === 'scanner' ? '#1a1a1a' : 'transparent',
              border: 'none',
              borderRadius: 4,
              padding: 6,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              if (activeTab !== 'scanner') {
                (e.currentTarget as HTMLButtonElement).style.background = '#1a1a1a';
              }
            }}
            onMouseLeave={(e) => {
              if (activeTab !== 'scanner') {
                (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
              }
            }}
            title="Scanner"
          >
            <div style={{ color: activeTab === 'scanner' ? '#fff' : '#666', transition: 'color 0.2s' }}>
              <ScannerIcon />
            </div>
          </button>

          {/* Phase 81.1: Toggle chat position button */}
          <button
            onClick={toggleChatPosition}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#555',
              cursor: 'pointer',
              padding: 4,
              display: 'flex',
              alignItems: 'center',
              transition: 'color 0.2s'
            }}
            onMouseEnter={(e) => { e.currentTarget.style.color = '#888'; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = '#555'; }}
            title={chatPosition === 'left' ? 'Move to right' : 'Move to left'}
          >
            {/* Simple arrow icon pointing to opposite side */}
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              {chatPosition === 'left' ? (
                // Arrow pointing right
                <>
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </>
              ) : (
                // Arrow pointing left
                <>
                  <line x1="19" y1="12" x2="5" y2="12" />
                  <polyline points="12 19 5 12 12 5" />
                </>
              )}
            </svg>
          </button>

          {/* Close button */}
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#555',
              cursor: 'pointer',
              padding: 4,
              display: 'flex',
              alignItems: 'center',
            }}
            title="Close"
          >
            <X size={16} />
          </button>
          </div>

          {/* Phase 68.2: Context indicator moved BELOW search bar */}
          {/* Phase 74.6: REMOVED - selectedNode indicator is redundant with pinned context */}
          {/* If node is selected but not pinned, user should pin it to see context */}
          {/* Keeping commented for reference:
          {selectedNode && (
            <div style={{...}}>
              {selectedNode.name || selectedNode.id}
            </div>
          )}
          */}

          {/* Phase 48: Selected model indicator */}
          {/* Phase 57: Grayscale style, no emoji */}
          {/* Phase 74.6: Removed !selectedNode condition since node indicator is removed */}
          {selectedModel && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 8px',
              background: '#1a1a1a',
              borderRadius: 4,
              fontSize: 11,
              color: '#888',
              marginLeft: 'auto',
            }}>
              <span style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: '#4a6'
              }} />
              <span>{selectedModel.split('/')[1] || selectedModel}</span>
              <button
                onClick={() => setSelectedModel(null)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#555',
                  cursor: 'pointer',
                  padding: 0,
                  marginLeft: 4
                }}
              >
                <X size={12} />
              </button>
            </div>
          )}

          {activeTab === 'chat' && currentWorkflow && <WorkflowProgress workflow={currentWorkflow} />}

          {/* Phase 57.3: Active group indicator */}
          {/* Phase 82: Added Settings button */}
          {/* Phase 80.9: Added Group ID copy badge */}
          {activeGroupId && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 12px',
              fontSize: 12,
              color: '#888',
              background: '#161616',
              borderRadius: 4,
            }}>
              <span style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: '#6a8'
              }} />
              <span style={{ color: '#aaa' }}>Group Active</span>
              <span style={{ color: '#555' }}>|</span>
              <span style={{ color: '#666', fontSize: 10 }}>Use @role to mention</span>
              <span style={{ color: '#555' }}>|</span>
              {/* Phase 80.9: Group ID badge with copy */}
              <button
                onClick={copyGroupId}
                title={groupIdCopied ? 'Copied!' : 'Copy Group ID'}
                style={{
                  background: groupIdCopied ? '#1a3a1a' : '#1a1a1a',
                  border: '1px solid #333',
                  borderRadius: 3,
                  padding: '2px 6px',
                  fontSize: 10,
                  color: groupIdCopied ? '#6a8' : '#666',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  transition: 'all 0.2s',
                  fontFamily: 'monospace'
                }}
                onMouseEnter={(e) => {
                  if (!groupIdCopied) {
                    e.currentTarget.style.borderColor = '#555';
                    e.currentTarget.style.color = '#aaa';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!groupIdCopied) {
                    e.currentTarget.style.borderColor = '#333';
                    e.currentTarget.style.color = '#666';
                  }
                }}
              >
                {/* Phase 80: SVG copy icon */}
                {groupIdCopied ? '✓' : (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                  </svg>
                )} {activeGroupId.slice(0, 8)}...
              </button>
              {/* Phase 80.23: Gear button removed - Team button now opens Group Settings */}
              <button
                onClick={() => {
                  if (activeGroupId) leaveGroup(activeGroupId);
                  setActiveGroupId(null);
                  clearChat();
                }}
                style={{
                  background: 'transparent',
                  border: '1px solid #333',
                  color: '#666',
                  cursor: 'pointer',
                  padding: '2px 8px',
                  borderRadius: 3,
                  fontSize: 10,
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#555';
                  e.currentTarget.style.color = '#aaa';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '#333';
                  e.currentTarget.style.color = '#666';
                }}
              >
                Leave
              </button>
            </div>
          )}
        </div>

        {/* Phase 68.2: UnifiedSearchBar - always visible in chat/group mode */}
        {(activeTab === 'chat' || activeTab === 'group') && (
          <UnifiedSearchBar
            onSelectResult={handleSearchSelect}
            onPinResult={handleSearchPin}
            onOpenArtifact={(result) => {
              // Phase 68.2: Open artifact viewer with file from search
              const ext = result.name.includes('.') ? result.name.split('.').pop() : undefined;
              setArtifactData({
                title: result.name,
                file: {
                  path: result.path,
                  name: result.name,
                  extension: ext
                }
              });
            }}
            placeholder="Search code/docs..."
            contextPrefix="vetka/"
            compact={true}
          />
        )}

        {/* Phase 74.3: Chat name header - like pinned context, editable */}
        {/* Phase 74.5: Don't show if file chat and file is already in pinned context */}
        {/* MARKER_EDIT_NAME_CHAT: Edit Name button in chat panel header */}
        {/* Status: WORKING - handleRenameChatFromHeader() -> PATCH /api/chats/{id} */}
        {/* Issue: NONE - This button is fully functional in both chat and group tabs */}
        {(activeTab === 'chat' || activeTab === 'group') && currentChatInfo &&
         !(currentChatInfo.contextType === 'file' && pinnedFileIds.length > 0) && (
          <div style={{
            padding: '6px 12px',
            background: '#0f0f0f',
            borderBottom: '1px solid #222',
          }}>
            <div
              onClick={handleRenameChatFromHeader}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 10px',
                background: '#1a1a1a',
                border: '1px solid #333',
                borderLeft: '3px solid #4a9eff',  // Phase 100.6.2: Accent to distinguish from pinned files
                borderRadius: 4,
                fontSize: 12,
                color: '#bbb',  // Phase 100.6.2: Slightly brighter than pinned files
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#555';
                e.currentTarget.style.background = '#222';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#333';
                e.currentTarget.style.background = '#1a1a1a';
              }}
              title="Click to rename chat"
            >
              {/* Context-type icon */}
              {currentChatInfo.contextType === 'folder' ? (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                </svg>
              ) : currentChatInfo.contextType === 'group' ? (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                </svg>
              ) : currentChatInfo.contextType === 'topic' ? (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
              ) : (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                </svg>
              )}

              {/* Chat name */}
              <span style={{ fontWeight: 500 }}>
                {currentChatInfo.displayName || currentChatInfo.fileName}
              </span>

              {/* Edit icon */}
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="2" style={{ marginLeft: 'auto', flexShrink: 0 }}>
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
              </svg>

              {/* MARKER_CHAT_NEW_BUTTON: New Chat button with icon */}
              {/* Phase 107.2: Replaced X icon with proper New Chat button */}
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#555"
                strokeWidth="2"
                style={{ flexShrink: 0, cursor: 'pointer' }}
                title="New Chat"
                onClick={(e) => {
                  e.stopPropagation();
                  handleNewChat();
                }}
                onMouseEnter={(e) => (e.currentTarget.style.stroke = '#fff')}
                onMouseLeave={(e) => (e.currentTarget.style.stroke = '#555')}
              >
                {/* Chat bubble */}
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                {/* Plus sign */}
                <line x1="12" y1="8" x2="12" y2="14"/>
                <line x1="9" y1="11" x2="15" y2="11"/>
              </svg>
            </div>
          </div>
        )}

        {/* Phase 68.2: Pinned context - AFTER search bar */}
        {(activeTab === 'chat' || activeTab === 'group') && pinnedFileIds.length > 0 && (
          <div style={{
            padding: '6px 12px',
            background: '#0f0f0f',
            borderBottom: '1px solid #222',
          }}>
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 6,
              alignItems: 'center',
            }}>
              {/* Pin icon */}
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="2" style={{ flexShrink: 0 }}>
                <path d="M12 17v5M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z" />
              </svg>

              {/* Pinned files */}
              {pinnedFileIds.slice(0, 8).map(id => {
                const node = nodes[id];
                if (!node) return null;
                return (
                  <div
                    key={id}
                    onClick={() => selectNode(id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      padding: '2px 8px',
                      background: '#1a1a1a',
                      border: '1px solid #333',
                      borderRadius: 4,
                      fontSize: 11,
                      color: '#888',
                      cursor: 'pointer',
                    }}
                    title={node.path}
                  >
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                    </svg>
                    <span style={{ maxWidth: 80, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {node.name}
                    </span>
                    <svg
                      width="10"
                      height="10"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#555"
                      strokeWidth="2"
                      style={{ cursor: 'pointer', marginLeft: 2 }}
                      onClick={(e) => {
                        e.stopPropagation();
                        togglePinFile(id);
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.stroke = '#fff')}
                      onMouseLeave={(e) => (e.currentTarget.style.stroke = '#555')}
                    >
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </div>
                );
              })}

              {pinnedFileIds.length > 8 && (
                <span style={{ fontSize: 10, color: '#555' }}>+{pinnedFileIds.length - 8}</span>
              )}

              {pinnedFileIds.length > 1 && (
                <span title="Clear all">
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#555"
                    strokeWidth="2"
                    style={{ cursor: 'pointer', marginLeft: 'auto' }}
                    onClick={clearPinnedFiles}
                    onMouseEnter={(e) => (e.currentTarget.style.stroke = '#fff')}
                    onMouseLeave={(e) => (e.currentTarget.style.stroke = '#555')}
                  >
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                </span>
              )}
            </div>
          </div>
        )}

        {/* Phase 92.4: Unified Scan Panel (replaces ScannerPanel + ScanProgressPanel) */}
        {activeTab === 'scanner' && (
          <ScanPanel
            onFileClick={(path) => {
              console.log('[ChatPanel] Phase 92.5: onFileClick triggered, sending camera command to:', path);
              selectNode(path);
              setCameraCommand({ target: path, zoom: 'close', highlight: true });
            }}
            // Phase 92.5: Pin file to chat context (same as search)
            onFilePin={(path) => {
              console.log('[ChatPanel] Phase 92.5: onFilePin triggered for:', path);
              // Find node by path and toggle pin
              const nodeId = Object.keys(nodes).find(id => nodes[id]?.path === path);
              if (nodeId) {
                togglePinFile(nodeId);
              } else {
                console.warn('[ChatPanel] Could not find node for path:', path);
              }
            }}
            pinnedPaths={pinnedFileIds.map(id => nodes[id]?.path).filter(Boolean) as string[]}
            isVisible={true}
            onEvent={handleScannerEvent}
          />
        )}

        {/* Phase 56.6: Group Creator panel when group tab active */}
        {/* Phase 80.12: Added edit mode support */}
        {activeTab === 'group' && (
          <div style={{
            flex: '0 0 auto',
            maxHeight: '50%',
            minHeight: 280,
            overflow: 'hidden',
            borderBottom: '1px solid #222',
          }}>
            <GroupCreatorPanel
              selectedModel={modelForGroup}
              onClearSelectedModel={() => setModelForGroup(null)}
              onCreateGroup={handleCreateGroup}
              onAddCustomRole={() => {
                // console.log('[ChatPanel] Add custom role requested');
              }}
              // Phase 60.4: Pass artifact opener for custom role template
              onOpenArtifact={(data) => setArtifactData(data)}
              // Phase 80.12: Edit mode props
              editMode={groupEditMode}
              groupId={activeGroupId || undefined}
              onGroupUpdated={() => {
                // console.log('[ChatPanel] Group updated');
              }}
              onExitEditMode={() => {
                setGroupEditMode(false);
                setActiveTab('chat');
              }}
              onOpenModelDirectory={() => setLeftPanel('models')}
            />
          </div>
        )}

        {/* Messages - always visible, takes remaining space */}
        <div style={{ flex: 1, position: 'relative', minHeight: 0 }}>
          <div
            ref={messagesContainerRef}
            style={{
              height: '100%',
              overflow: 'auto',
              padding: 16,
            }}
          >
            <MessageList
              messages={chatMessages}
              isTyping={isTyping}
              onReply={handleReply}
              onOpenArtifact={handleOpenArtifact}
            />
            <div ref={messagesEndRef} />
          </div>

          {/* MARKER_SCROLL_BTN_LOCATION: Scroll-to-bottom/top button over message list */}
          {/* Phase 107.3: Scroll-to-bottom button */}
          {/* Shows when: isAtBottom=false (scrolled up) */}
          {/* Icon: down arrow (↓) when not at bottom */}
          {/* TODO: Add up arrow (↑) when at top, toggle functionality */}
          {/* MARKER_SCROLL_BTN_FIXED: Phase 107.3 - Always visible, toggles direction */}
          <button
            onClick={() => {
              // MARKER_SCROLL_FUNCTION: Toggle scroll direction based on position
              if (isAtBottom) {
                // Scroll to top
                messagesContainerRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
              } else {
                // Scroll to bottom
                messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
              }
            }}
            style={{
              position: 'absolute',
              bottom: 20,
              right: 20,
              width: 36,
              height: 36,
              borderRadius: '50%',
              background: '#333',
              border: '1px solid #444',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000,
              transition: 'all 0.2s ease',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#444';
              e.currentTarget.style.transform = 'scale(1.05)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#333';
              e.currentTarget.style.transform = 'scale(1)';
            }}
            title={isAtBottom ? "Scroll to top" : "Scroll to bottom"}
          >
            {/* Arrow toggles: DOWN when not at bottom, UP when at bottom */}
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              {isAtBottom ? (
                <polyline points="18 15 12 9 6 15"/>
              ) : (
                <polyline points="6 9 12 15 18 9"/>
              )}
            </svg>
          </button>
        </div>

        {/* Phase 48.3: Reply indicator */}
        {replyTo && (
          <div style={{
            padding: '8px 16px',
            background: '#1a1a1a',
            borderTop: '1px solid #333',
            borderLeft: '3px solid #4aff9e',
            display: 'flex',
            alignItems: 'center',
            gap: 8
          }}>
            <Reply size={14} color="#4aff9e" />
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <div style={{ fontSize: 11, color: '#4aff9e', marginBottom: 2 }}>
                Replying to {replyTo.model}
              </div>
              <div style={{
                fontSize: 12,
                color: '#888',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {replyTo.text.slice(0, 80)}...
              </div>
            </div>
            <button
              onClick={() => setReplyTo(null)}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#666',
                cursor: 'pointer',
                padding: 4
              }}
            >
              <X size={14} />
            </button>
          </div>
        )}

        {/* Input - always visible */}
        {/* Phase 80.22: Pass group participants for dynamic @mention dropdown */}
        <MessageInput
          value={input}
          onChange={setInput}
          onSend={handleSend}
          isLoading={isTyping}
          replyTo={replyTo?.model}
          replyToModel={replyTo?.model}
          isGroupMode={!!activeGroupId}
          groupParticipants={currentGroupParticipants}
          soloModels={soloModels}  // Phase 80.30: Models used in solo chat
          voiceModels={voiceModels}
          selectedModel={selectedModel}
          voiceOnlyMode={voiceOnlyMode}
          onVoiceOnlyModeChange={setVoiceOnlyMode}
          autoContinueVoice={autoContinueVoice}
          onAutoContinueVoiceChange={setAutoContinueVoice}
          realtimeVoiceEnabled={realtimeVoiceEnabled}
          onRealtimeVoiceChange={setRealtimeVoiceEnabled}
        />
      </div>

      {/* Phase 48.5.1: Artifact Panel via FloatingWindow */}
      <FloatingWindow
        title={artifactData?.title || 'Response'}
        isOpen={!!artifactData}
        onClose={() => setArtifactData(null)}
        defaultWidth={700}
        defaultHeight={500}
      >
        <ArtifactPanel
          file={artifactData?.file}
          rawContent={artifactData?.content ? {
            content: artifactData.content,
            title: artifactData.title,
            type: artifactData.type
          } : null}
          onClose={() => setArtifactData(null)}
        />
      </FloatingWindow>
    </>
  );
}
