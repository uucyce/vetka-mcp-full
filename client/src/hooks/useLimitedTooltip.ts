import { useMemo } from 'react';

const STORAGE_KEY = 'vetka_tooltip_seen';

type TooltipMap = Record<string, number>;

function loadMap(): TooltipMap {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function saveMap(map: TooltipMap) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
}

export function useLimitedTooltip(id: string, text: string, maxViews = 3) {
  const map = useMemo(() => loadMap(), []);
  const seen = map[id] || 0;

  const onMouseEnter = () => {
    const current = loadMap();
    const count = current[id] || 0;
    if (count >= maxViews) return;
    current[id] = count + 1;
    saveMap(current);
  };

  return {
    title: seen >= maxViews ? undefined : text,
    onMouseEnter,
  };
}
