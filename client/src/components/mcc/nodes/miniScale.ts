export function resolveMiniScale(mini?: boolean, miniScale?: number): number {
  if (!mini) return 1;
  const parsed = Number(miniScale);
  if (!Number.isFinite(parsed)) return 0.22;
  return Math.max(0.1, Math.min(1, parsed));
}

export function scalePx(base: number, scale: number, min = 1): number {
  return Math.max(min, Math.round(base * scale));
}
