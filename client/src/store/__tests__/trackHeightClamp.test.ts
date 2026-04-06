/**
 * MARKER_A3.5 — Track height min/max constraint tests.
 *
 * Tests:
 * 1. setTrackHeight clamps at minimum (20px)
 * 2. setTrackHeight clamps at maximum (200px)
 * 3. setTrackHeight accepts value within bounds
 * 4. setTrackHeightForLane clamps at minimum (20px)
 * 5. setTrackHeightForLane clamps at maximum (200px)
 * 6. setTrackHeightForLane accepts value within bounds
 * 7. cycleTrackHeights presets all within 20-200 range
 * 8. setTrackHeight at exact boundary: 20 accepted
 * 9. setTrackHeight at exact boundary: 200 accepted
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useCutEditorStore } from '../useCutEditorStore';

const TRACK_HEIGHT_MIN = 20;
const TRACK_HEIGHT_MAX = 200;

function resetStore() {
  useCutEditorStore.setState({ trackHeight: 56, trackHeights: {} });
}

describe('MARKER_A3.5: Track height min/max constraints', () => {
  beforeEach(resetStore);

  it('1. setTrackHeight clamps below minimum', () => {
    useCutEditorStore.getState().setTrackHeight(5);
    expect(useCutEditorStore.getState().trackHeight).toBe(TRACK_HEIGHT_MIN);
  });

  it('2. setTrackHeight clamps above maximum', () => {
    useCutEditorStore.getState().setTrackHeight(999);
    expect(useCutEditorStore.getState().trackHeight).toBe(TRACK_HEIGHT_MAX);
  });

  it('3. setTrackHeight accepts value within bounds', () => {
    useCutEditorStore.getState().setTrackHeight(80);
    expect(useCutEditorStore.getState().trackHeight).toBe(80);
  });

  it('4. setTrackHeightForLane clamps below minimum', () => {
    useCutEditorStore.getState().setTrackHeightForLane('A1', 0);
    expect(useCutEditorStore.getState().trackHeights['A1']).toBe(TRACK_HEIGHT_MIN);
  });

  it('5. setTrackHeightForLane clamps above maximum', () => {
    useCutEditorStore.getState().setTrackHeightForLane('V1', 500);
    expect(useCutEditorStore.getState().trackHeights['V1']).toBe(TRACK_HEIGHT_MAX);
  });

  it('6. setTrackHeightForLane accepts value within bounds', () => {
    useCutEditorStore.getState().setTrackHeightForLane('A2', 112);
    expect(useCutEditorStore.getState().trackHeights['A2']).toBe(112);
  });

  it('7. cycleTrackHeights presets all within 20-200 range', () => {
    // Cycle 3 times to hit all presets
    for (let i = 0; i < 3; i++) {
      useCutEditorStore.getState().cycleTrackHeights();
      const h = useCutEditorStore.getState().trackHeight;
      expect(h).toBeGreaterThanOrEqual(TRACK_HEIGHT_MIN);
      expect(h).toBeLessThanOrEqual(TRACK_HEIGHT_MAX);
    }
  });

  it('8. setTrackHeight at exact minimum boundary', () => {
    useCutEditorStore.getState().setTrackHeight(TRACK_HEIGHT_MIN);
    expect(useCutEditorStore.getState().trackHeight).toBe(TRACK_HEIGHT_MIN);
  });

  it('9. setTrackHeight at exact maximum boundary', () => {
    useCutEditorStore.getState().setTrackHeight(TRACK_HEIGHT_MAX);
    expect(useCutEditorStore.getState().trackHeight).toBe(TRACK_HEIGHT_MAX);
  });
});
