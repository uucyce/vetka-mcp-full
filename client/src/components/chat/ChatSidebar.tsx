/**
 * Chat Sidebar Component - Phase 50 + 129.2
 * Displays chat history and allows switching between conversations.
 *
 * @file ChatSidebar.tsx
 * @status ACTIVE
 * @phase Phase 50 - Chat History + Sidebar UI
 * @lastUpdate 2026-02-10
 *
 * Features:
 * - Load and display all chats with pagination
 * - Search/filter chats by file name
 * - Select chat to load message history
 * - Show message count and last updated timestamp
 * - Delete chat (optional)
 *
 * MARKER_129.2A: Pagination with offset/limit (already implemented)
 * MARKER_129.2B: Loading skeleton animation
 * MARKER_129.2C: Scroll-to-load-more with IntersectionObserver
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import './ChatSidebar.css';

interface Chat {
  id: string;
  file_name: string;
  file_path: string;
  display_name?: string;  // Phase 74: Custom chat name
  context_type?: string;  // Phase 74: "file" | "folder" | "group" | "topic"
  items?: string[];       // Phase 74: File paths for groups
  topic?: string;         // Phase 74: Topic for file-less chats
  created_at: string;
  updated_at: string;
  message_count?: number;
  // TODO_CAM_INDICATOR: Add CAM activation field here (hot/warm/cold status from /api/cam/activation?chat_id=...)
  cam_activation?: 'hot' | 'warm' | 'cold';  // Show memory priority in sidebar
}

interface ChatSidebarProps {
  isOpen: boolean;
  onSelectChat: (chatId: string, filePath: string, fileName: string) => void;
  currentChatId?: string;
  onClose?: () => void;
}

/**
 * MARKER_129.2B: Loading skeleton for chat items
 */
const ChatSkeleton = () => (
  <div className="chat-sidebar-skeleton">
    {[1, 2, 3, 4, 5].map((i) => (
      <div key={i} className="chat-skeleton-item">
        <div className="chat-skeleton-icon" />
        <div className="chat-skeleton-content">
          <div className="chat-skeleton-title" />
          <div className="chat-skeleton-meta" />
        </div>
      </div>
    ))}
  </div>
);

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  isOpen,
  onSelectChat,
  currentChatId,
  onClose
}) => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const LIMIT = 50;

  // MARKER_129.2C: IntersectionObserver for infinite scroll
  const loadMoreRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Load chats on component mount (auto-load on app startup)
  useEffect(() => {
    loadChats(true);
  }, []);

  // Reload chats when sidebar opens (refresh on visibility)
  useEffect(() => {
    if (isOpen) {
      loadChats(true);
    }
  }, [isOpen]);

  // MARKER_RENAME_FIX: Listen for external rename events
  // MARKER_RENAME_DEBUG_FIX: Added debugging for sidebar event listener
  useEffect(() => {
    const handleChatRenamed = (e: Event) => {
      const { chatId, newName } = (e as CustomEvent).detail;
      console.log('[SIDEBAR DEBUG 1] Received chat-renamed event:', { chatId, newName });
      console.log('[SIDEBAR DEBUG 2] Current chats before update:', chats.map(c => ({ id: c.id, name: c.display_name })));

      setChats(prevChats => {
        const updated = prevChats.map(c =>
          c.id === chatId ? { ...c, display_name: newName } : c
        );
        console.log('[SIDEBAR DEBUG 3] Updated chats:', updated.map(c => ({ id: c.id, name: c.display_name })));
        return updated;
      });
    };

    console.log('[SIDEBAR DEBUG 0] Setting up chat-renamed event listener');
    window.addEventListener('chat-renamed', handleChatRenamed);
    return () => {
      console.log('[SIDEBAR DEBUG 0] Cleaning up chat-renamed event listener');
      window.removeEventListener('chat-renamed', handleChatRenamed);
    };
  }, [chats]);

  const loadChats = async (reset: boolean = false) => {
    if (reset) {
      setLoading(true);
      setOffset(0);
    } else {
      setLoadingMore(true);
    }

    try {
      const currentOffset = reset ? 0 : offset;
      const response = await fetch(`/api/chats?limit=${LIMIT}&offset=${currentOffset}`);
      if (response.ok) {
        const data = await response.json();

        if (reset) {
          setChats(data.chats || []);
        } else {
          setChats(prev => [...prev, ...(data.chats || [])]);
        }

        setTotal(data.total || 0);
        setHasMore(data.has_more || false);
        setOffset(currentOffset + (data.chats?.length || 0));

        // console.log(`[ChatSidebar] Loaded ${data.chats?.length || 0} chats (total: ${data.total})`);
      } else {
        console.error(`[ChatSidebar] Error loading chats: ${response.status}`);
      }
    } catch (error) {
      console.error('[ChatSidebar] Error fetching chats:', error);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  // MARKER_129.2C: Wrapped in useCallback for IntersectionObserver
  const loadMoreChats = useCallback(() => {
    if (!loadingMore && hasMore) {
      loadChats(false);
    }
  }, [loadingMore, hasMore]);

  // MARKER_129.2C: IntersectionObserver for scroll-to-load-more
  useEffect(() => {
    if (!loadMoreRef.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting && hasMore && !loadingMore && !loading) {
          loadMoreChats();
        }
      },
      { threshold: 0.1 }
    );

    observer.observe(loadMoreRef.current);
    return () => observer.disconnect();
  }, [hasMore, loadingMore, loading, loadMoreChats]);

  const filteredChats = chats.filter(chat =>
    chat.file_name.toLowerCase().includes(search.toLowerCase())
  );

  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMins < 1) return 'just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays < 7) return `${diffDays}d ago`;
      return date.toLocaleDateString();
    } catch {
      return dateString.split('T')[0];
    }
  };

  const handleDeleteChat = async (e: React.MouseEvent, chatId: string) => {
    e.stopPropagation();

    if (!confirm('Delete this chat? This cannot be undone.')) {
      return;
    }

    try {
      const response = await fetch(`/api/chats/${chatId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        setChats(chats.filter(c => c.id !== chatId));
        // console.log(`[ChatSidebar] Deleted chat ${chatId}`);
      } else {
        console.error(`[ChatSidebar] Error deleting chat: ${response.status}`);
      }
    } catch (error) {
      console.error('[ChatSidebar] Error deleting chat:', error);
    }
  };

  // Phase 74: Rename chat functionality
  const handleRenameChat = async (e: React.MouseEvent, chat: Chat) => {
    e.stopPropagation();

    const currentName = chat.display_name || chat.file_name;
    const newName = prompt('Enter new name for this chat:', currentName);

    if (!newName || newName.trim() === '' || newName.trim() === currentName) {
      return;
    }

    try {
      const response = await fetch(`/api/chats/${chat.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ display_name: newName.trim() })
      });

      if (response.ok) {
        // Update local state
        setChats(chats.map(c =>
          c.id === chat.id ? { ...c, display_name: newName.trim() } : c
        ));
      } else {
        console.error(`[ChatSidebar] Error renaming chat: ${response.status}`);
      }
    } catch (error) {
      console.error('[ChatSidebar] Error renaming chat:', error);
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="chat-sidebar">
      {/* Header */}
      <div className="chat-sidebar-header">
        <h3 className="chat-sidebar-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          Chat History
        </h3>
        {onClose && (
          <button className="chat-sidebar-close" onClick={onClose}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        )}
      </div>

      {/* Search */}
      <div className="chat-sidebar-search">
        <input
          type="text"
          placeholder="Search chats..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="chat-sidebar-search-input"
        />
      </div>

      {/* Chats List */}
      <div className="chat-sidebar-list" ref={listRef}>
        {/* MARKER_129.2B: Skeleton loading */}
        {loading && <ChatSkeleton />}

        {!loading && filteredChats.length === 0 && (
          <div className="chat-sidebar-empty">
            {chats.length === 0 ? 'No chats yet' : 'No matches found'}
          </div>
        )}

        {!loading && filteredChats.map((chat) => (
          <div
            key={chat.id}
            className={`chat-sidebar-item ${
              currentChatId === chat.id ? 'active' : ''
            }`}
            onClick={() =>
              onSelectChat(chat.id, chat.file_path, chat.file_name)
            }
          >
            <div className="chat-sidebar-item-content">
              <div className="chat-sidebar-item-name">
                {/* Phase 74.3: Context-aware SVG icons */}
                {chat.context_type === 'folder' ? (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                  </svg>
                ) : chat.context_type === 'group' ? (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                  </svg>
                ) : chat.context_type === 'topic' ? (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    <circle cx="12" cy="10" r="1" fill="currentColor"/><circle cx="8" cy="10" r="1" fill="currentColor"/><circle cx="16" cy="10" r="1" fill="currentColor"/>
                  </svg>
                ) : (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                  </svg>
                )}
                <span style={{ marginLeft: 6 }}>{chat.display_name || chat.file_name}</span>
              </div>
              <div className="chat-sidebar-item-meta">
                <span className="chat-sidebar-item-time">
                  {formatDate(chat.updated_at)}
                </span>
                {chat.message_count !== undefined && (
                  <span className="chat-sidebar-item-count">
                    {chat.message_count} msg
                  </span>
                )}
              </div>
            </div>

            {/* Phase 74.3: Actions with SVG icons */}
            {/* MARKER_EDIT_NAME_SIDEBAR: Edit Name button in sidebar history */}
            {/* Status: WORKING - handleRenameChat() -> PATCH /api/chats/{id} */}
            {/* Issue: NONE - This button is fully functional */}
            <div className="chat-sidebar-item-actions">
              <button
                className="chat-sidebar-item-edit"
                onClick={(e) => handleRenameChat(e, chat)}
                title="Rename chat"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
              <button
                className="chat-sidebar-item-delete"
                onClick={(e) => handleDeleteChat(e, chat.id)}
                title="Delete chat"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="3 6 5 6 21 6"/>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
              </button>
            </div>
          </div>
        ))}

        {/* MARKER_129.2C: Scroll trigger for infinite load */}
        {hasMore && !loading && (
          <div ref={loadMoreRef} className="chat-sidebar-load-trigger">
            {loadingMore && (
              <div className="chat-sidebar-loading-more">
                <span className="chat-loading-spinner" />
                Loading more...
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer with Refresh and Load More */}
      <div className="chat-sidebar-footer">
        <button
          className="chat-sidebar-refresh"
          onClick={() => loadChats(true)}
          disabled={loading}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: 6 }}>
            <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
          {loading ? 'Loading...' : 'Refresh'}
        </button>

        {hasMore && !loading && (
          <button
            className="chat-sidebar-load-more"
            onClick={loadMoreChats}
            disabled={loadingMore}
          >
            {loadingMore ? 'Loading...' : `Load More (${chats.length}/${total})`}
          </button>
        )}

        {!hasMore && chats.length > 0 && (
          <div className="chat-sidebar-footer-info">
            All {total} chats loaded
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatSidebar;
