/**
 * MessageBubble - Individual chat message with reactions and TTS.
 * Renders user, assistant, system, and compound messages.
 *
 * @status active
 * @phase 98
 * @depends react, lucide-react, ChatMessage type, CompoundMessage, useTTS
 * @used_by MessageList
 */

import { useState } from 'react';
import { User, Bot, ClipboardList, Code, TestTube, Building, Sparkles, Reply, FileText, SmilePlus, Volume2, VolumeX } from 'lucide-react';
import type { ChatMessage } from '../../types/chat';
import { CompoundMessage } from './CompoundMessage';
import { useTTS } from '../voice/useTTS';

// Phase 48.3: Max chars before showing "read more"
const MAX_PREVIEW_LENGTH = 500;

// Phase 48.4: Quick reactions
const QUICK_REACTIONS = ['👍', '👎', '❤️', '🔥', '💡', '🤔'];

// Phase 98: Emoji to reaction name mapping for CAM API
const EMOJI_TO_REACTION: Record<string, string> = {
  '👍': 'thumbs_up',
  '👎': 'thumbs_down',
  '❤️': 'heart',
  '🔥': 'fire',
  '💡': 'lightbulb',
  '🤔': 'thinking',
};

interface Props {
  message: ChatMessage;
  onReply?: (msg: { id: string; model: string; text: string }) => void;
  onOpenArtifact?: (id: string, content: string, agent?: string) => void;  // Phase 48.5.1: Added agent
  onReaction?: (messageId: string, reaction: string) => void;
}

const AGENT_ICONS: Record<string, React.ReactNode> = {
  PM: <ClipboardList size={14} />,
  Dev: <Code size={14} />,
  QA: <TestTube size={14} />,
  Architect: <Building size={14} />,
  Hostess: <Sparkles size={14} />,
};

export function MessageBubble({ message, onReply, onOpenArtifact, onReaction }: Props) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const isCompound = message.type === 'compound';

  // Phase 48.4: Emoji reactions state
  const [showReactions, setShowReactions] = useState(false);
  const [reactions, setReactions] = useState<string[]>([]);

  // Phase 60.5: TTS hook for speaking messages
  const { speak, stop, isSpeaking } = useTTS();

  // Phase 98: Handle reaction with CAM API integration
  const handleReaction = async (emoji: string) => {
    const isRemoving = reactions.includes(emoji);

    setReactions(prev => {
      // Toggle reaction
      if (prev.includes(emoji)) {
        return prev.filter(r => r !== emoji);
      }
      return [...prev, emoji];
    });
    setShowReactions(false);
    onReaction?.(message.id, emoji);

    // Phase 98: POST to CAM API for weight boost (only when adding, not removing)
    if (!isRemoving) {
      const reactionName = EMOJI_TO_REACTION[emoji] || 'thinking';
      const modelId = message.metadata?.model || message.agent || 'unknown';

      try {
        const response = await fetch('/api/cam/reaction', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message_id: message.id,
            reaction: reactionName,
            model_id: modelId,
            context: {
              topic: message.content?.slice(0, 100),  // First 100 chars as topic hint
            }
          })
        });

        if (response.ok) {
          const data = await response.json();
          console.log(`[CAM] Reaction recorded: ${reactionName} for ${modelId}, weight delta: ${data.weight_delta}`);
        }
      } catch (error) {
        console.warn('[CAM] Failed to record reaction:', error);
        // Silent fail - don't disrupt UX for analytics
      }
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  // System message - Phase 57: Grayscale style
  if (isSystem) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '8px 12px',
        background: '#1a1a1a',
        border: '1px solid #333',
        borderRadius: 6,
        marginBottom: 12,
      }}>
        <span style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: '#555',
          flexShrink: 0
        }} />
        <span style={{ color: '#888', fontSize: 12 }}>{message.content}</span>
      </div>
    );
  }

  // User message
  if (isUser) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-end',
        marginBottom: 12,
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          marginBottom: 4,
        }}>
          <span style={{ fontSize: 10, color: '#666' }}>{formatTime(message.timestamp)}</span>
          <User size={14} color="#4a9eff" />
        </div>
        <div style={{
          maxWidth: '85%',
          padding: '10px 14px',
          background: '#1a3a5c',
          borderRadius: '16px 16px 4px 16px',
          color: '#e0e0e0',
          fontSize: 14,
          lineHeight: 1.5,
        }}>
          {message.content}
        </div>
      </div>
    );
  }

  // Compound message (workflow result)
  if (isCompound && message.sections) {
    return (
      <div style={{ marginBottom: 12 }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          marginBottom: 8,
          flexWrap: 'wrap',
        }}>
          <Bot size={14} color="#4aff9e" />
          <span style={{ fontSize: 12, color: '#4aff9e', fontWeight: 500 }}>
            Workflow Complete
          </span>

          {/* Duration */}
          {message.metadata?.duration && (
            <span style={{ fontSize: 10, color: '#666' }}>
              ({(message.metadata.duration / 1000).toFixed(1)}s)
            </span>
          )}

          {/* Score */}
          {message.metadata?.score != null && (
            <span style={{
              fontSize: 10,
              color: '#f0c040',
              padding: '2px 6px',
              background: 'rgba(240, 192, 64, 0.1)',
              borderRadius: 4
            }}>
              ⭐ {message.metadata.score}
            </span>
          )}

          {/* Model */}
          {message.metadata?.model && (
            <span style={{ fontSize: 10, color: '#666' }}>
              · {message.metadata.model}
            </span>
          )}
        </div>
        <CompoundMessage sections={message.sections} />
      </div>
    );
  }

  // Assistant message
  const isStreaming = message.metadata?.isStreaming;
  // Phase 48.3: Long message handling
  // Phase 74 fix: Guard against null/undefined content
  const isLong = (message.content?.length || 0) > MAX_PREVIEW_LENGTH;
  const modelName = message.metadata?.model || message.agent || 'assistant';

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'flex-start',
      marginBottom: 12,
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        marginBottom: 4,
      }}>
        {message.agent && AGENT_ICONS[message.agent] ? (
          <span style={{ color: '#4aff9e' }}>{AGENT_ICONS[message.agent]}</span>
        ) : (
          <Bot size={14} color="#4aff9e" />
        )}
        {/* Phase 49: Agent/model name - larger and bolder */}
        <span style={{ fontSize: 13, fontWeight: 600, color: '#ccc' }}>
          {message.agent || message.metadata?.model || 'assistant'}
        </span>
        <span style={{ fontSize: 10, color: '#555' }}>{formatTime(message.timestamp)}</span>

        {/* Phase 46: Streaming indicator */}
        {isStreaming && (
          <span style={{
            fontSize: 10,
            color: '#4aff9e',
            animation: 'pulse 1s infinite',
          }}>
            streaming...
          </span>
        )}
      </div>
      <div style={{
        maxWidth: '85%',
        padding: '10px 14px',
        background: '#1a1a1a',
        borderRadius: '4px 16px 16px 16px',
        color: '#e0e0e0',
        fontSize: 14,
        lineHeight: 1.5,
        border: '1px solid #222',
      }}>
        {/* Phase 48.3: Show preview for long messages */}
        {/* Phase 74 fix: Guard against null/undefined content */}
        {isLong && !isStreaming ? (
          <>
            <div style={{ whiteSpace: 'pre-wrap' }}>
              {(message.content || '').slice(0, MAX_PREVIEW_LENGTH)}...
            </div>
            <button
              onClick={() => onOpenArtifact?.(message.id, message.content || '', modelName)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                marginTop: 10,
                padding: '6px 10px',
                background: '#222',
                border: '1px solid #333',
                borderRadius: 6,
                color: '#888',
                fontSize: 12,
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = '#2a2a2a';
                e.currentTarget.style.color = '#aaa';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = '#222';
                e.currentTarget.style.color = '#888';
              }}
            >
              <FileText size={14} />
              Read full response ({(message.content || '').length} chars)
            </button>
          </>
        ) : (
          <>
            <div style={{ whiteSpace: 'pre-wrap' }}>{message.content || ''}</div>
            {/* Phase 46: Streaming cursor */}
            {isStreaming && <span style={{ opacity: 0.7, animation: 'blink 0.5s infinite' }}>▊</span>}
          </>
        )}
      </div>

      {/* Phase 46: Token metadata display */}
      {message.metadata?.tokens_output && !isStreaming && (
        <div style={{
          display: 'flex',
          gap: 8,
          marginTop: 4,
          fontSize: 10,
          color: '#666',
        }}>
          <span>🧠 {message.metadata.tokens_output} tokens</span>
          {message.metadata.tokens_input && (
            <span>📥 {message.metadata.tokens_input} input</span>
          )}
        </div>
      )}

      {/* Phase 48.5: Emoji reactions + Reply button in same row */}
      {/* Phase 98: TODO_CAM_EMOJI IMPLEMENTED - reactions now POST to /api/cam/reaction
          Weight mapping: 👍=+0.1, 👎=-0.1, ❤️=+0.15, 🔥=+0.2, 💡=+0.1, 🤔=0 (tracked) */}
      {!isStreaming && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          marginTop: 6,
          position: 'relative'
        }}>
          {/* Show selected reactions */}
          {reactions.length > 0 && (
            <div style={{
              display: 'flex',
              gap: 2,
              padding: '2px 6px',
              background: '#1a1a1a',
              borderRadius: 12,
              border: '1px solid #333'
            }}>
              {reactions.map((r, i) => (
                <span
                  key={i}
                  style={{ fontSize: 14, cursor: 'pointer' }}
                  onClick={() => handleReaction(r)}
                  title="Click to remove"
                >
                  {r}
                </span>
              ))}
            </div>
          )}

          {/* Action buttons: TTS + emoji + reply */}
          <div style={{ display: 'flex', gap: 4, marginLeft: reactions.length > 0 ? 0 : 0 }}>
            {/* Phase 60.5: TTS button */}
            <button
              onClick={() => isSpeaking ? stop() : speak(message.content)}
              style={{
                background: isSpeaking ? '#1a2a3a' : 'transparent',
                border: 'none',
                cursor: 'pointer',
                padding: 2,
                borderRadius: 4,
                opacity: isSpeaking ? 1 : 0.4,
                transition: 'all 0.2s'
              }}
              onMouseEnter={e => (e.currentTarget.style.opacity = '0.8')}
              onMouseLeave={e => (e.currentTarget.style.opacity = isSpeaking ? '1' : '0.4')}
              title={isSpeaking ? 'Stop speaking' : 'Read aloud'}
            >
              {isSpeaking ? (
                <VolumeX size={14} color="#4a9eff" />
              ) : (
                <Volume2 size={14} color="#666" />
              )}
            </button>

            {/* Add reaction button */}
            <button
              onClick={() => setShowReactions(!showReactions)}
              style={{
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                padding: 2,
                opacity: 0.4,
                transition: 'opacity 0.2s'
              }}
              onMouseEnter={e => (e.currentTarget.style.opacity = '0.8')}
              onMouseLeave={e => (e.currentTarget.style.opacity = '0.4')}
              title="Add reaction"
            >
              <SmilePlus size={14} color="#666" />
            </button>

            {/* Reply button - Phase 48.5: moved here */}
            {onReply && (
              <button
                onClick={() => onReply({
                  id: message.id,
                  model: modelName,
                  text: message.content
                })}
                style={{
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  padding: 2,
                  opacity: 0.4,
                  transition: 'opacity 0.2s'
                }}
                onMouseEnter={e => (e.currentTarget.style.opacity = '0.8')}
                onMouseLeave={e => (e.currentTarget.style.opacity = '0.4')}
                title="Reply to this message"
              >
                <Reply size={14} color="#666" />
              </button>
            )}
          </div>

          {/* Reaction picker */}
          {showReactions && (
            <div style={{
              position: 'absolute',
              bottom: '100%',
              left: 0,
              display: 'flex',
              gap: 4,
              padding: '6px 8px',
              background: '#1a1a1a',
              border: '1px solid #333',
              borderRadius: 8,
              marginBottom: 4,
              boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
            }}>
              {QUICK_REACTIONS.map(emoji => (
                <button
                  key={emoji}
                  onClick={() => handleReaction(emoji)}
                  style={{
                    background: reactions.includes(emoji) ? '#333' : 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '4px 6px',
                    borderRadius: 4,
                    fontSize: 16,
                    transition: 'background 0.2s'
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = '#333')}
                  onMouseLeave={e => (e.currentTarget.style.background = reactions.includes(emoji) ? '#333' : 'transparent')}
                >
                  {emoji}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Phase 49: Keyframes for streaming cursor */}
      <style>{`
        @keyframes blink { 0%,50% {opacity:1} 51%,100% {opacity:0} }
        @keyframes pulse { 0%,100% {opacity:1} 50% {opacity:0.5} }
      `}</style>
    </div>
  );
}
