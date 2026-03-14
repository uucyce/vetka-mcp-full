/**
 * MARKER_154.5A: MatryoshkaTransition — Figma-like drill-down/back animation.
 *
 * Wraps DAGView content. On drill-down: selected node expands to fill canvas.
 * On back: canvas contracts back into parent node position.
 *
 * Uses framer-motion for smooth 300ms cubic-bezier transitions.
 * Direction detected by comparing current vs previous navLevel depth.
 *
 * @phase 154
 * @wave 2
 * @status active
 */

import { useEffect, useRef, useState, type ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { NavLevel } from '../../store/useMCCStore';

// MARKER_154.5A: Level depth for transition direction detection
const LEVEL_DEPTH: Record<NavLevel, number> = {
  first_run: 0,
  roadmap: 1,
  tasks: 2,
  workflow: 3,
  running: 4,
  results: 5,
};

interface MatryoshkaTransitionProps {
  navLevel: NavLevel;
  children: ReactNode;
  // MARKER_155A.G21.DRILL_IN_PLACE: Disable scene-switch animation for single-canvas UX.
  inPlace?: boolean;
}

// Transition variants — expand in (drill-down) or contract out (go back)
const drillDownVariants = {
  initial: { scale: 0.85, opacity: 0, filter: 'blur(4px)' },
  animate: { scale: 1, opacity: 1, filter: 'blur(0px)' },
  exit: { scale: 1.15, opacity: 0, filter: 'blur(4px)' },
};

const goBackVariants = {
  initial: { scale: 1.15, opacity: 0, filter: 'blur(4px)' },
  animate: { scale: 1, opacity: 1, filter: 'blur(0px)' },
  exit: { scale: 0.85, opacity: 0, filter: 'blur(4px)' },
};

const transition = {
  duration: 0.3,
  ease: [0.4, 0, 0.2, 1], // cubic-bezier(0.4, 0, 0.2, 1)
};

export function MatryoshkaTransition({ navLevel, children, inPlace = false }: MatryoshkaTransitionProps) {
  if (inPlace) {
    return (
      <div style={{ width: '100%', height: '100%', position: 'relative' }}>
        {children}
      </div>
    );
  }

  const prevLevelRef = useRef<NavLevel>(navLevel);
  const [direction, setDirection] = useState<'in' | 'out'>('in');

  useEffect(() => {
    const prevDepth = LEVEL_DEPTH[prevLevelRef.current] ?? 0;
    const currDepth = LEVEL_DEPTH[navLevel] ?? 0;

    if (currDepth > prevDepth) {
      setDirection('in');  // Drilling down → zoom in
    } else if (currDepth < prevDepth) {
      setDirection('out'); // Going back → zoom out
    }
    // Same level → no direction change (shouldn't animate)

    prevLevelRef.current = navLevel;
  }, [navLevel]);

  const variants = direction === 'in' ? drillDownVariants : goBackVariants;

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={navLevel}
        variants={variants}
        initial="initial"
        animate="animate"
        exit="exit"
        transition={transition}
        style={{
          width: '100%',
          height: '100%',
          position: 'relative',
        }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
