/**
 * MARKER_GAMMA-14 + GAMMA-R4.1 + R4.2: Custom drag preview — thumbnail + filename + duration + multi-count.
 * Extracted from ProjectPanel.tsx into shared util (Gamma-8 refactor).
 */

export function setDragPreview(
  e: React.DragEvent,
  name: string,
  modality: string | undefined,
  posterUrl: string | undefined,
  durationSec?: number | null,
  multiCount?: number,
) {
  const el = document.createElement('div');
  el.style.cssText = 'position:fixed;top:-200px;left:-200px;width:96px;padding:4px;background:#1a1a1a;border:1px solid #555;border-radius:4px;font-size:8px;font-family:system-ui,sans-serif;color:#ccc;text-align:center;pointer-events:none;z-index:99999';
  if (posterUrl) {
    const img = document.createElement('img');
    img.src = posterUrl;
    img.style.cssText = 'width:88px;height:56px;object-fit:cover;border-radius:2px;display:block;margin:0 auto 3px';
    el.appendChild(img);
  } else {
    const icon = document.createElement('div');
    icon.style.cssText = 'width:88px;height:56px;display:flex;align-items:center;justify-content:center;font-size:20px;color:#444;margin:0 auto 3px;background:#111;border-radius:2px';
    icon.textContent = modality === 'audio' ? '\u266A' : modality === 'image' ? '\u25FB' : '\u25B6';
    el.appendChild(icon);
  }
  const label = document.createElement('div');
  label.style.cssText = 'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:88px;margin:0 auto';
  label.textContent = name;
  el.appendChild(label);
  // Duration + modality badge row
  if (durationSec || modality) {
    const meta = document.createElement('div');
    meta.style.cssText = 'display:flex;justify-content:space-between;margin-top:2px;color:#666;font-size:7px';
    if (modality) {
      const mod = document.createElement('span');
      mod.textContent = modality.toUpperCase();
      meta.appendChild(mod);
    }
    if (durationSec) {
      const dur = document.createElement('span');
      dur.style.cssText = 'font-variant-numeric:tabular-nums';
      dur.textContent = `${Number(durationSec).toFixed(1)}s`;
      meta.appendChild(dur);
    }
    el.appendChild(meta);
  }
  // MARKER_GAMMA-R4.2: Multi-clip badge
  if (multiCount && multiCount > 1) {
    const badge = document.createElement('div');
    badge.style.cssText = 'margin-top:3px;padding:1px 6px;background:#333;border-radius:2px;color:#ccc;font-size:8px;text-align:center';
    badge.textContent = `${multiCount} clips`;
    el.appendChild(badge);
  }
  document.body.appendChild(el);
  e.dataTransfer.setDragImage(el, 48, 35);
  requestAnimationFrame(() => document.body.removeChild(el));
}
