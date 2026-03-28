/**
 * Unit tests for PasteAttributesDialog component.
 *
 * Coverage:
 *   - Renders source/target names in meta block
 *   - Apply button disabled when nothing is checked
 *   - Checking a video attribute enables Apply
 *   - Video section master checkbox toggles all children
 *   - Audio section master checkbox toggles all children
 *   - Escape key calls onClose
 *   - Backdrop click calls onClose
 *   - Apply calls onApply with correct config
 *   - Radio buttons switch keyframe mode
 *   - Multiple target names display as "name (+ N more)"
 */
import { render, screen, fireEvent, cleanup, within } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import PasteAttributesDialog from '../PasteAttributesDialog';

afterEach(cleanup);

// ─── Fixtures ─────────────────────────────────────────────────────────────────

function setup(overrides?: {
  sourceClipName?: string;
  targetClipNames?: string[];
}) {
  const onClose = vi.fn();
  const onApply = vi.fn();
  const props = {
    onClose,
    onApply,
    sourceClipName: overrides?.sourceClipName ?? 'A001_C002.mov',
    targetClipNames: overrides?.targetClipNames ?? ['B001_C001.mov'],
  };
  const result = render(<PasteAttributesDialog {...props} />);
  const dialog = screen.getByTestId('paste-attributes-dialog');
  const within_dialog = within(dialog);
  return { onClose, onApply, dialog, within_dialog, ...result };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('PasteAttributesDialog', () => {
  it('renders source and target clip names', () => {
    const { within_dialog } = setup();
    expect(within_dialog.getByText('A001_C002.mov')).toBeTruthy();
    expect(within_dialog.getByText('B001_C001.mov')).toBeTruthy();
  });

  it('Apply button is disabled when nothing is checked', () => {
    const { within_dialog } = setup();
    const applyBtn = within_dialog.getByRole('button', { name: /apply/i }) as HTMLButtonElement;
    expect(applyBtn.disabled).toBe(true);
  });

  it('checking a video attribute enables Apply', () => {
    const { within_dialog } = setup();
    fireEvent.click(within_dialog.getByRole('checkbox', { name: /effects/i }));
    const applyBtn = within_dialog.getByRole('button', { name: /apply/i }) as HTMLButtonElement;
    expect(applyBtn.disabled).toBe(false);
  });

  it('video master checkbox checks all video children', () => {
    const { within_dialog } = setup();
    const masterCheckbox = within_dialog.getByTitle('Toggle all video attributes');
    fireEvent.click(masterCheckbox);
    const videoLabels = ['Effects', 'Color Correction', 'Motion', 'Speed / Retime', 'Transition'];
    videoLabels.forEach((label) => {
      const checkbox = within_dialog.getByRole('checkbox', { name: new RegExp(label, 'i') }) as HTMLInputElement;
      expect(checkbox.checked).toBe(true);
    });
  });

  it('video master checkbox unchecks all when all are checked', () => {
    const { within_dialog } = setup();
    const masterCheckbox = within_dialog.getByTitle('Toggle all video attributes');
    fireEvent.click(masterCheckbox); // check all
    fireEvent.click(masterCheckbox); // uncheck all
    const videoLabels = ['Effects', 'Color Correction', 'Motion', 'Speed / Retime', 'Transition'];
    videoLabels.forEach((label) => {
      const checkbox = within_dialog.getByRole('checkbox', { name: new RegExp(label, 'i') }) as HTMLInputElement;
      expect(checkbox.checked).toBe(false);
    });
  });

  it('audio master checkbox checks all audio children', () => {
    const { within_dialog } = setup();
    const masterCheckbox = within_dialog.getByTitle('Toggle all audio attributes');
    fireEvent.click(masterCheckbox);
    const volumeCheckbox = within_dialog.getByRole('checkbox', { name: /volume/i }) as HTMLInputElement;
    expect(volumeCheckbox.checked).toBe(true);
  });

  it('Escape key calls onClose', () => {
    const { onClose } = setup();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('backdrop click calls onClose', () => {
    const { onClose, dialog } = setup();
    fireEvent.click(dialog.parentElement!);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('Apply calls onApply with correct config', () => {
    const { onApply, within_dialog } = setup();
    fireEvent.click(within_dialog.getByRole('checkbox', { name: /effects/i }));
    fireEvent.click(within_dialog.getByRole('checkbox', { name: /volume/i }));
    fireEvent.click(within_dialog.getByRole('radio', { name: /stretch to fit/i }));
    fireEvent.click(within_dialog.getByRole('button', { name: /apply/i }));
    expect(onApply).toHaveBeenCalledTimes(1);
    const config = onApply.mock.calls[0][0];
    expect(config.effects).toBe(true);
    expect(config.volume).toBe(true);
    expect(config.colorCorrection).toBe(false);
    expect(config.keyframeMode).toBe('stretch');
  });

  it('Apply does not fire when nothing is checked', () => {
    const { onApply, within_dialog } = setup();
    fireEvent.click(within_dialog.getByRole('button', { name: /apply/i }));
    expect(onApply).not.toHaveBeenCalled();
  });

  it('radio buttons switch keyframe mode', () => {
    const { within_dialog } = setup();
    const maintainRadio = within_dialog.getByRole('radio', { name: /maintain timing/i }) as HTMLInputElement;
    const stretchRadio = within_dialog.getByRole('radio', { name: /stretch to fit/i }) as HTMLInputElement;
    expect(maintainRadio.checked).toBe(true);
    expect(stretchRadio.checked).toBe(false);
    fireEvent.click(stretchRadio);
    expect(stretchRadio.checked).toBe(true);
    expect(maintainRadio.checked).toBe(false);
  });

  it('single target name displayed as-is', () => {
    const { within_dialog } = setup({ targetClipNames: ['B001_C001.mov'] });
    expect(within_dialog.getByText('B001_C001.mov')).toBeTruthy();
  });

  it('multiple target names display as "name (+ N more)"', () => {
    const { within_dialog } = setup({
      targetClipNames: ['B001_C001.mov', 'B001_C002.mov', 'B001_C003.mov'],
    });
    expect(within_dialog.getByText('B001_C001.mov (+ 2 more)')).toBeTruthy();
  });

  it('empty target list displays em-dash', () => {
    const { within_dialog } = setup({ targetClipNames: [] });
    expect(within_dialog.getByText('—')).toBeTruthy();
  });

  it('Cancel button calls onClose', () => {
    const { onClose, within_dialog } = setup();
    fireEvent.click(within_dialog.getByRole('button', { name: /cancel/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
