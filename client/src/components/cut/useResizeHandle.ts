/**
 * MARKER_170.11.RESIZE_HANDLE
 * Hook for panel resize interactions (horizontal and vertical).
 * Returns onMouseDown handler and current size.
 */
import { useState, useCallback, useRef } from 'react';

type Direction = 'horizontal' | 'vertical';

export function useResizeHandle(
  direction: Direction,
  initialSize: number,
  minSize: number,
  maxSize: number,
  /** For horizontal: true = dragging right edge (size grows with positive delta).
   *  false = dragging left edge (size shrinks with positive delta). */
  invert = false,
) {
  const [size, setSize] = useState(initialSize);
  const dragging = useRef(false);
  const startPos = useRef(0);
  const startSize = useRef(initialSize);

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragging.current = true;
      startPos.current = direction === 'horizontal' ? e.clientX : e.clientY;
      startSize.current = size;

      const onMouseMove = (ev: MouseEvent) => {
        if (!dragging.current) return;
        const delta = direction === 'horizontal'
          ? ev.clientX - startPos.current
          : ev.clientY - startPos.current;
        const newSize = invert
          ? startSize.current - delta
          : startSize.current + delta;
        setSize(Math.max(minSize, Math.min(maxSize, newSize)));
      };

      const onMouseUp = () => {
        dragging.current = false;
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      };

      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
      document.body.style.cursor = direction === 'horizontal' ? 'col-resize' : 'row-resize';
      document.body.style.userSelect = 'none';
    },
    [direction, size, minSize, maxSize, invert],
  );

  return { size, onMouseDown } as const;
}
