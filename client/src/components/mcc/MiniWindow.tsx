/**
 * MARKER_154.11A: MiniWindow — compact/expanded floating window framework.
 *
 * Used for MiniChat, MiniTasks, MiniStats in the DAG canvas.
 * Compact: small card in corner (200×150). Expanded: overlay (80% screen).
 * Toggle by clicking header. X or click outside → compact.
 *
 * @phase 154
 * @wave 4
 * @status active
 */

import { useState, useCallback, useRef, useEffect, type ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

type Position = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';

interface MiniWindowProps {
  title: string;
  icon: string;
  position: Position;
  /** Content for compact mode */
  compactContent: ReactNode;
  /** Content for expanded mode */
  expandedContent: ReactNode;
  /** Compact dimensions */
  compactWidth?: number;
  compactHeight?: number;
  /** Whether the window starts expanded */
  defaultExpanded?: boolean;
  /** External control */
  onToggle?: (expanded: boolean) => void;
}

const POSITION_STYLE: Record<Position, React.CSSProperties> = {
  'top-left': { top: 8, left: 8 },
  'top-right': { top: 8, right: 8 },
  'bottom-left': { bottom: 60, left: 8 },  // 60px clearance for FooterActionBar
  'bottom-right': { bottom: 60, right: 8 },
};

export function MiniWindow({
  title,
  icon,
  position,
  compactContent,
  expandedContent,
  compactWidth = 200,
  compactHeight = 140,
  defaultExpanded = false,
  onToggle,
}: MiniWindowProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const overlayRef = useRef<HTMLDivElement>(null);

  const toggle = useCallback(() => {
    const next = !expanded;
    setExpanded(next);
    onToggle?.(next);
  }, [expanded, onToggle]);

  const collapse = useCallback(() => {
    setExpanded(false);
    onToggle?.(false);
  }, [onToggle]);

  // Close on Escape
  useEffect(() => {
    if (!expanded) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') collapse();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [expanded, collapse]);

  // Click outside to close (expanded only)
  const handleOverlayClick = useCallback((e: React.MouseEvent) => {
    if (e.target === overlayRef.current) collapse();
  }, [collapse]);

  return (
    <>
      {/* Compact mode — corner card */}
      <AnimatePresence>
        {!expanded && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.2 }}
            style={{
              position: 'absolute',
              ...POSITION_STYLE[position],
              width: compactWidth,
              height: compactHeight,
              background: 'rgba(15,15,15,0.85)',
              backdropFilter: 'blur(12px)',
              border: `1px solid ${NOLAN_PALETTE.border}`,
              borderRadius: 8,
              overflow: 'hidden',
              zIndex: 50,
              fontFamily: 'monospace',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* Header — click to expand */}
            <div
              onClick={toggle}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                padding: '5px 8px',
                cursor: 'pointer',
                borderBottom: `1px solid ${NOLAN_PALETTE.border}`,
                flexShrink: 0,
              }}
            >
              <span style={{ fontSize: 10 }}>{icon}</span>
              <span style={{ color: NOLAN_PALETTE.textAccent, fontSize: 9, fontWeight: 600, flex: 1 }}>
                {title}
              </span>
              <span style={{ color: '#444', fontSize: 8, cursor: 'pointer' }} title="Expand">
                ↗
              </span>
            </div>

            {/* Compact content */}
            <div style={{ flex: 1, overflow: 'hidden', padding: '4px 8px' }}>
              {compactContent}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Expanded mode — overlay */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            ref={overlayRef}
            onClick={handleOverlayClick}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{
              position: 'absolute',
              inset: 0,
              background: 'rgba(0,0,0,0.5)',
              backdropFilter: 'blur(4px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 80,
            }}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ duration: 0.25 }}
              style={{
                width: '80%',
                maxWidth: 700,
                height: '75%',
                maxHeight: 500,
                background: NOLAN_PALETTE.bgDim,
                border: `1px solid ${NOLAN_PALETTE.border}`,
                borderRadius: 10,
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                fontFamily: 'monospace',
              }}
            >
              {/* Header */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '8px 14px',
                  borderBottom: `1px solid ${NOLAN_PALETTE.border}`,
                  flexShrink: 0,
                }}
              >
                <span style={{ fontSize: 13 }}>{icon}</span>
                <span style={{ color: NOLAN_PALETTE.text, fontSize: 12, fontWeight: 600, flex: 1 }}>
                  {title}
                </span>
                <button
                  onClick={collapse}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: NOLAN_PALETTE.textMuted,
                    cursor: 'pointer',
                    fontSize: 14,
                    padding: '0 4px',
                  }}
                  title="Collapse"
                >
                  ↙
                </button>
                <button
                  onClick={collapse}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: NOLAN_PALETTE.textMuted,
                    cursor: 'pointer',
                    fontSize: 14,
                    padding: '0 4px',
                  }}
                  title="Close"
                >
                  ✕
                </button>
              </div>

              {/* Expanded content */}
              <div style={{ flex: 1, overflow: 'auto' }}>
                {expandedContent}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
