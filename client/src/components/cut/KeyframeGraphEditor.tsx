/**
 * MARKER_KF58: FCP7 Ch.58-59 — Keyframe Graph Editor
 *
 * Canvas panel that shows keyframe curves for a selected clip + property.
 * Features:
 *   - Diamond markers at keyframe positions (draggable)
 *   - Bezier tangent handles (cp_in / cp_out)
 *   - Curve drawn via cubic bezier / easing segments
 *   - Property selector (opacity, volume, brightness, contrast, …)
 *   - Add / remove keyframe buttons
 *   - Reads/writes via useCutEditorStore (addKeyframe / removeKeyframe / updateKeyframeBezier)
 */
import { useRef, useEffect, useCallback, useState } from 'react';
import { useCutEditorStore, interpolateKeyframes, type Keyframe } from '../../store/useCutEditorStore';
import { useSelectionStore } from '../../store/useSelectionStore';

// ─── Constants ────────────────────────────────────────────────────────────────
const PADDING = { top: 16, bottom: 16, left: 40, right: 12 };
const DIAMOND_R = 5;   // half-size of diamond shape (px)
const HANDLE_R  = 3;   // radius of bezier handle dot (px)
// HANDLE_ARM: default arm length in px when auto-creating bezier handles (future)
// const HANDLE_ARM = 32;

const PROPERTIES = [
  'opacity', 'volume', 'brightness', 'contrast', 'saturation',
  'blur', 'gamma', 'speed',
];

// ─── Types ────────────────────────────────────────────────────────────────────
type DragTarget =
  | { kind: 'diamond'; idx: number }
  | { kind: 'cp_out'; idx: number }
  | { kind: 'cp_in';  idx: number }
  | null;

// ─── Helpers ─────────────────────────────────────────────────────────────────
function clamp(v: number, lo: number, hi: number) { return v < lo ? lo : v > hi ? hi : v; }

function valueRange(kfs: Keyframe[]): [number, number] {
  if (kfs.length === 0) return [0, 1];
  let lo = kfs[0].value, hi = kfs[0].value;
  for (const k of kfs) {
    if (k.value < lo) lo = k.value;
    if (k.value > hi) hi = k.value;
    if (k.cp_out) { const v = k.value + k.cp_out[1]; if (v < lo) lo = v; if (v > hi) hi = v; }
    if (k.cp_in)  { const v = k.value - k.cp_in[1];  if (v < lo) lo = v; if (v > hi) hi = v; }
  }
  const span = hi - lo;
  const pad = span < 0.01 ? 0.5 : span * 0.15;
  return [lo - pad, hi + pad];
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function KeyframeGraphEditor() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [property, setProperty] = useState('opacity');
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const dragRef = useRef<DragTarget>(null);
  const dragStartRef = useRef<{ mx: number; my: number; kfs: Keyframe[] } | null>(null);

  const addKeyframe        = useCutEditorStore((s) => s.addKeyframe);
  const removeKeyframe     = useCutEditorStore((s) => s.removeKeyframe);
  const updateKeyframeBezier = useCutEditorStore((s) => s.updateKeyframeBezier);
  const lanes              = useCutEditorStore((s) => s.lanes);
  const currentTime        = useCutEditorStore((s) => s.currentTime);
  const selectedClipId     = useSelectionStore((s) => s.selectedClipId);

  // Resolve keyframes for selected clip + property
  const keyframes: Keyframe[] = (() => {
    if (!selectedClipId) return [];
    for (const lane of lanes) {
      const clip = lane.clips.find((c) => c.clip_id === selectedClipId);
      if (clip?.keyframes?.[property]) return clip.keyframes[property];
    }
    return [];
  })();

  // Clip duration
  const clipDuration: number = (() => {
    if (!selectedClipId) return 10;
    for (const lane of lanes) {
      const clip = lane.clips.find((c) => c.clip_id === selectedClipId);
      if (clip) return clip.duration_sec;
    }
    return 10;
  })();

  // Clip start (for playhead display)
  const clipStart: number = (() => {
    if (!selectedClipId) return 0;
    for (const lane of lanes) {
      const clip = lane.clips.find((c) => c.clip_id === selectedClipId);
      if (clip) return clip.start_sec;
    }
    return 0;
  })();

  // ── Coordinate helpers ────────────────────────────────────────────────────
  function getInner(canvas: HTMLCanvasElement) {
    return {
      w: canvas.width  - PADDING.left - PADDING.right,
      h: canvas.height - PADDING.top  - PADDING.bottom,
    };
  }

  function toCanvas(timeSec: number, value: number, canvas: HTMLCanvasElement, vLo: number, vHi: number) {
    const { w, h } = getInner(canvas);
    const x = PADDING.left + (timeSec / Math.max(clipDuration, 0.001)) * w;
    const y = PADDING.top  + (1 - (value - vLo) / Math.max(vHi - vLo, 0.001)) * h;
    return { x, y };
  }

  function fromCanvas(cx: number, cy: number, canvas: HTMLCanvasElement, vLo: number, vHi: number) {
    const { w, h } = getInner(canvas);
    const timeSec = clamp((cx - PADDING.left) / w, 0, 1) * clipDuration;
    const value   = vLo + (1 - clamp((cy - PADDING.top) / h, 0, 1)) * (vHi - vLo);
    return { timeSec, value };
  }

  // ── Draw ──────────────────────────────────────────────────────────────────
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { w, h } = getInner(canvas);
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Background
    ctx.fillStyle = '#0a0a0a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const [vLo, vHi] = valueRange(keyframes);

    // Grid lines
    ctx.strokeStyle = '#1a1a1a';
    ctx.lineWidth = 1;
    for (let gi = 0; gi <= 4; gi++) {
      const gy = PADDING.top + (gi / 4) * h;
      ctx.beginPath(); ctx.moveTo(PADDING.left, gy); ctx.lineTo(PADDING.left + w, gy); ctx.stroke();
    }

    // Y-axis labels
    ctx.fillStyle = '#555';
    ctx.font = '9px system-ui, sans-serif';
    ctx.textAlign = 'right';
    for (let gi = 0; gi <= 4; gi++) {
      const v = vHi - (gi / 4) * (vHi - vLo);
      const gy = PADDING.top + (gi / 4) * h;
      ctx.fillText(v.toFixed(2), PADDING.left - 4, gy + 3);
    }

    // Playhead
    const relTime = currentTime - clipStart;
    if (relTime >= 0 && relTime <= clipDuration) {
      const px = PADDING.left + (relTime / clipDuration) * w;
      ctx.strokeStyle = '#e0c040';
      ctx.lineWidth = 1;
      ctx.setLineDash([2, 3]);
      ctx.beginPath(); ctx.moveTo(px, PADDING.top); ctx.lineTo(px, PADDING.top + h); ctx.stroke();
      ctx.setLineDash([]);
    }

    if (keyframes.length === 0) {
      ctx.fillStyle = '#333';
      ctx.font = '11px system-ui, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('No keyframes — Add with Ctrl+K or the button below', canvas.width / 2, canvas.height / 2);
      return;
    }

    // ── Draw curve ──────────────────────────────────────────────────────────
    ctx.strokeStyle = '#5588cc';
    ctx.lineWidth = 1.5;
    ctx.beginPath();

    for (let i = 0; i < keyframes.length - 1; i++) {
      const kfA = keyframes[i];
      const kfB = keyframes[i + 1];
      const pA = toCanvas(kfA.time_sec, kfA.value, canvas, vLo, vHi);
      const pB = toCanvas(kfB.time_sec, kfB.value, canvas, vLo, vHi);

      if (i === 0) ctx.moveTo(pA.x, pA.y);

      if (kfA.easing === 'bezier' && (kfA.cp_out || kfB.cp_in)) {
        const dt = kfB.time_sec - kfA.time_sec;
        const cp1t = kfA.cp_out ? kfA.time_sec + kfA.cp_out[0] : kfA.time_sec + dt / 3;
        const cp1v = kfA.cp_out ? kfA.value   + kfA.cp_out[1] : kfA.value   + (kfB.value - kfA.value) / 3;
        const cp2t = kfB.cp_in  ? kfB.time_sec - kfB.cp_in[0] : kfB.time_sec - dt / 3;
        const cp2v = kfB.cp_in  ? kfB.value   - kfB.cp_in[1] : kfB.value   - (kfB.value - kfA.value) / 3;
        const c1 = toCanvas(cp1t, cp1v, canvas, vLo, vHi);
        const c2 = toCanvas(cp2t, cp2v, canvas, vLo, vHi);
        ctx.bezierCurveTo(c1.x, c1.y, c2.x, c2.y, pB.x, pB.y);
      } else if (kfA.easing === 'ease_in') {
        ctx.bezierCurveTo(pA.x + (pB.x - pA.x) * 0.5, pA.y, pB.x, pB.y, pB.x, pB.y);
      } else if (kfA.easing === 'ease_out') {
        ctx.bezierCurveTo(pA.x, pA.y, pA.x + (pB.x - pA.x) * 0.5, pB.y, pB.x, pB.y);
      } else if (kfA.easing === 'bezier') {
        // bezier without cp data → smooth step approximation via symmetric handles
        const mx = (pA.x + pB.x) / 2;
        ctx.bezierCurveTo(mx, pA.y, mx, pB.y, pB.x, pB.y);
      } else {
        ctx.lineTo(pB.x, pB.y);
      }
    }
    // Extend hold from last keyframe
    if (keyframes.length > 0) {
      const last = keyframes[keyframes.length - 1];
      if (last.time_sec < clipDuration) {
        const pL = toCanvas(last.time_sec, last.value, canvas, vLo, vHi);
        const pEnd = toCanvas(clipDuration, last.value, canvas, vLo, vHi);
        if (keyframes.length === 1) ctx.moveTo(pL.x, pL.y);
        ctx.lineTo(pEnd.x, pEnd.y);
      }
    }
    ctx.stroke();

    // ── Bezier handles ──────────────────────────────────────────────────────
    keyframes.forEach((kf, i) => {
      const p = toCanvas(kf.time_sec, kf.value, canvas, vLo, vHi);
      if (kf.easing === 'bezier') {
        ctx.strokeStyle = '#446688';
        ctx.lineWidth = 1;
        if (kf.cp_out) {
          const hp = toCanvas(kf.time_sec + kf.cp_out[0], kf.value + kf.cp_out[1], canvas, vLo, vHi);
          ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(hp.x, hp.y); ctx.stroke();
          ctx.fillStyle = '#88aacc';
          ctx.beginPath(); ctx.arc(hp.x, hp.y, HANDLE_R, 0, Math.PI * 2); ctx.fill();
        }
        if (kf.cp_in) {
          const hp = toCanvas(kf.time_sec - kf.cp_in[0], kf.value - kf.cp_in[1], canvas, vLo, vHi);
          ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(hp.x, hp.y); ctx.stroke();
          ctx.fillStyle = '#88aacc';
          ctx.beginPath(); ctx.arc(hp.x, hp.y, HANDLE_R, 0, Math.PI * 2); ctx.fill();
        }
      }

      // ── Diamond ──────────────────────────────────────────────────────────
      const isHovered = hoveredIdx === i;
      ctx.fillStyle   = isHovered ? '#ffffff' : '#aaccee';
      ctx.strokeStyle = '#223344';
      ctx.lineWidth   = 1;
      ctx.beginPath();
      ctx.moveTo(p.x,            p.y - DIAMOND_R);
      ctx.lineTo(p.x + DIAMOND_R, p.y);
      ctx.lineTo(p.x,            p.y + DIAMOND_R);
      ctx.lineTo(p.x - DIAMOND_R, p.y);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
    });

  }, [keyframes, clipDuration, clipStart, currentTime, hoveredIdx]);

  useEffect(() => { draw(); }, [draw]);

  // Resize observer
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ro = new ResizeObserver(() => {
      const parent = canvas.parentElement;
      if (parent) {
        canvas.width  = parent.clientWidth;
        canvas.height = parent.clientHeight;
        draw();
      }
    });
    ro.observe(canvas.parentElement!);
    return () => ro.disconnect();
  }, [draw]);

  // ── Hit test ──────────────────────────────────────────────────────────────
  function hitTest(mx: number, my: number): DragTarget {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const [vLo, vHi] = valueRange(keyframes);
    for (let i = 0; i < keyframes.length; i++) {
      const kf = keyframes[i];
      const p = toCanvas(kf.time_sec, kf.value, canvas, vLo, vHi);
      if (Math.abs(mx - p.x) + Math.abs(my - p.y) <= DIAMOND_R + 2) return { kind: 'diamond', idx: i };
      if (kf.easing === 'bezier') {
        if (kf.cp_out) {
          const hp = toCanvas(kf.time_sec + kf.cp_out[0], kf.value + kf.cp_out[1], canvas, vLo, vHi);
          if (Math.hypot(mx - hp.x, my - hp.y) <= HANDLE_R + 3) return { kind: 'cp_out', idx: i };
        }
        if (kf.cp_in) {
          const hp = toCanvas(kf.time_sec - kf.cp_in[0], kf.value - kf.cp_in[1], canvas, vLo, vHi);
          if (Math.hypot(mx - hp.x, my - hp.y) <= HANDLE_R + 3) return { kind: 'cp_in',  idx: i };
        }
      }
    }
    return null;
  }

  // ── Mouse handlers ────────────────────────────────────────────────────────
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    if (dragRef.current && dragStartRef.current) {
      const canvas2 = canvasRef.current!;
      const [vLo, vHi] = valueRange(dragStartRef.current.kfs);
      const { timeSec: newTime, value: newValue } = fromCanvas(mx, my, canvas2, vLo, vHi);
      const kf = dragStartRef.current.kfs[dragRef.current.idx];
      if (!kf) return;

      if (dragRef.current.kind === 'diamond') {
        // Move diamond: remove old, add new
        removeKeyframe(selectedClipId!, property, kf.time_sec);
        addKeyframe(selectedClipId!, property, clamp(newTime, 0, clipDuration), newValue);
      } else if (dragRef.current.kind === 'cp_out') {
        const dt = Math.max(0, newTime - kf.time_sec);
        const dv = newValue - kf.value;
        updateKeyframeBezier(selectedClipId!, property, kf.time_sec, [dt, dv], kf.cp_in);
      } else if (dragRef.current.kind === 'cp_in') {
        const dt = Math.max(0, kf.time_sec - newTime);
        const dv = kf.value - newValue;
        updateKeyframeBezier(selectedClipId!, property, kf.time_sec, kf.cp_out, [dt, dv]);
      }
      return;
    }

    // Hover
    const hit = hitTest(mx, my);
    setHoveredIdx(hit?.kind === 'diamond' ? hit.idx : null);
    canvas.style.cursor = hit ? 'grab' : 'crosshair';
  }, [keyframes, clipDuration, selectedClipId, property, addKeyframe, removeKeyframe, updateKeyframeBezier]);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const hit = hitTest(mx, my);
    if (hit) {
      dragRef.current = hit;
      dragStartRef.current = { mx, my, kfs: [...keyframes] };
      canvas.style.cursor = 'grabbing';
    }
  }, [keyframes]);

  const handleMouseUp = useCallback(() => {
    dragRef.current = null;
    dragStartRef.current = null;
    if (canvasRef.current) canvasRef.current.style.cursor = 'crosshair';
  }, []);

  const handleDoubleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!selectedClipId) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    // Double-click on diamond → remove
    const hit = hitTest(mx, my);
    if (hit?.kind === 'diamond') {
      removeKeyframe(selectedClipId, property, keyframes[hit.idx].time_sec);
      return;
    }

    // Double-click on empty → add keyframe
    const [vLo, vHi] = valueRange(keyframes.length > 0 ? keyframes : [{ time_sec: 0, value: 0, easing: 'linear' }, { time_sec: clipDuration, value: 1, easing: 'linear' }]);
    const { timeSec, value } = fromCanvas(mx, my, canvas, vLo, vHi);
    addKeyframe(selectedClipId, property, clamp(timeSec, 0, clipDuration), value);
  }, [selectedClipId, property, keyframes, clipDuration, addKeyframe, removeKeyframe]);

  // ── Add at playhead ───────────────────────────────────────────────────────
  const handleAddAtPlayhead = useCallback(() => {
    if (!selectedClipId) return;
    const relTime = currentTime - clipStart;
    if (relTime < 0 || relTime > clipDuration) return;
    // Interpolate current value from existing keyframes (or default 1)
    let value = 1;
    if (keyframes.length > 0) {
      value = interpolateKeyframes(keyframes, relTime);
    }
    addKeyframe(selectedClipId, property, relTime, value);
  }, [selectedClipId, property, currentTime, clipStart, clipDuration, keyframes, addKeyframe]);

  // ─── UI ───────────────────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#0a0a0a', userSelect: 'none' }}>
      {/* Toolbar */}
      <div style={{ display: 'flex', gap: 4, padding: '3px 6px', borderBottom: '1px solid #1a1a1a', flexShrink: 0, alignItems: 'center' }}>
        <span style={{ color: '#555', fontSize: 10, marginRight: 4 }}>PARAM</span>
        <select
          value={property}
          onChange={(e) => setProperty(e.target.value)}
          style={{ background: '#1a1a1a', color: '#aaa', border: '1px solid #333', borderRadius: 2, fontSize: 10, padding: '1px 4px', cursor: 'pointer' }}
        >
          {PROPERTIES.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <span style={{ flex: 1 }} />
        <button
          onClick={handleAddAtPlayhead}
          disabled={!selectedClipId}
          title="Add keyframe at playhead (Ctrl+K)"
          style={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 2, color: selectedClipId ? '#aaa' : '#444', fontSize: 10, padding: '2px 8px', cursor: selectedClipId ? 'pointer' : 'default' }}
        >
          + KF
        </button>
        {!selectedClipId && (
          <span style={{ color: '#444', fontSize: 10, marginLeft: 6 }}>No clip selected</span>
        )}
      </div>

      {/* Canvas */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <canvas
          ref={canvasRef}
          style={{ display: 'block', width: '100%', height: '100%', cursor: 'crosshair' }}
          onMouseMove={handleMouseMove}
          onMouseDown={handleMouseDown}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onDoubleClick={handleDoubleClick}
        />
      </div>

      {/* Keyframe list (bottom strip) */}
      {keyframes.length > 0 && (
        <div style={{ display: 'flex', gap: 2, padding: '2px 6px', borderTop: '1px solid #1a1a1a', flexShrink: 0, overflowX: 'auto' }}>
          {keyframes.map((kf, i) => (
            <button
              key={i}
              title={`t=${kf.time_sec.toFixed(3)}s  v=${kf.value.toFixed(3)}  [${kf.easing}]`}
              onMouseEnter={() => setHoveredIdx(i)}
              onMouseLeave={() => setHoveredIdx(null)}
              onClick={() => selectedClipId && removeKeyframe(selectedClipId, property, kf.time_sec)}
              style={{
                background: hoveredIdx === i ? '#2a2a2a' : '#151515',
                border: '1px solid #2a2a2a',
                borderRadius: 2,
                color: '#666',
                fontSize: 9,
                padding: '1px 4px',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              ◆ {kf.time_sec.toFixed(2)}s
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
