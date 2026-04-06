/**
 * MARKER_IMPORT-DIALOG-FIX: Verify Import Media dialog configuration.
 *
 * Bug: openFileDialog was missing from tauri.ts — only openFolderDialog existed.
 * The hidden <input> in ProjectPanel had webkitdirectory, greying out video files.
 *
 * These tests verify:
 * 1. openFileDialog() exists in tauri.ts with directory=false
 * 2. openFolderDialog() still exists for folder import
 * 3. MEDIA_FILE_EXTENSIONS constant includes all required formats
 * 4. ProjectPanel file input does NOT have webkitdirectory
 * 5. ProjectPanel folder input DOES have webkitdirectory
 * 6. ProjectPanel imports openFileDialog and openFolderDialog from tauri
 * 7. MenuBar has both "Import Media..." and "Import Folder..." entries
 * 8. Tauri openFileDialog uses correct filter groups
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const TAURI_TS_PATH = resolve(__dirname, '../../../config/tauri.ts');
const PROJECT_PANEL_PATH = resolve(__dirname, '../ProjectPanel.tsx');
const MENU_BAR_PATH = resolve(__dirname, '../MenuBar.tsx');

const tauriSrc = readFileSync(TAURI_TS_PATH, 'utf-8');
const projectPanelSrc = readFileSync(PROJECT_PANEL_PATH, 'utf-8');
const menuBarSrc = readFileSync(MENU_BAR_PATH, 'utf-8');

describe('MARKER_IMPORT-DIALOG-FIX: tauri.ts openFileDialog', () => {
  it('exports openFileDialog function', () => {
    expect(tauriSrc).toMatch(/export\s+async\s+function\s+openFileDialog/);
  });

  it('openFileDialog uses directory: false', () => {
    // Extract from openFileDialog to the next export (greedy enough to capture full body)
    const fnMatch = tauriSrc.match(/export\s+async\s+function\s+openFileDialog[\s\S]*?(?=\nexport\s)/);
    expect(fnMatch).not.toBeNull();
    const fnBody = fnMatch![0];
    expect(fnBody).toContain('directory: false');
    expect(fnBody).not.toMatch(/directory:\s*true/);
  });

  it('openFolderDialog still exists and uses directory: true', () => {
    expect(tauriSrc).toMatch(/export\s+async\s+function\s+openFolderDialog/);
    const fnMatch = tauriSrc.match(/export\s+async\s+function\s+openFolderDialog[\s\S]*?^}/m);
    expect(fnMatch).not.toBeNull();
    expect(fnMatch![0]).toContain('directory: true');
  });

  it('exports MEDIA_FILE_EXTENSIONS with required formats', () => {
    expect(tauriSrc).toMatch(/export\s+const\s+MEDIA_FILE_EXTENSIONS/);
    const required = ['mp4', 'mov', 'avi', 'mkv', 'mts', 'wav', 'mp3', 'aif'];
    for (const ext of required) {
      expect(tauriSrc).toContain(`'${ext}'`);
    }
  });

  it('openFileDialog has Video, Audio, Image, All Media filter groups', () => {
    const fnMatch = tauriSrc.match(/export\s+async\s+function\s+openFileDialog[\s\S]*?(?=\nexport\s)/);
    expect(fnMatch).not.toBeNull();
    const fnBody = fnMatch![0];
    expect(fnBody).toContain("name: 'Video'");
    expect(fnBody).toContain("name: 'Audio'");
    expect(fnBody).toContain("name: 'Image'");
    expect(fnBody).toContain("name: 'All Media'");
  });
});

describe('MARKER_IMPORT-DIALOG-FIX: ProjectPanel inputs', () => {
  it('file input does NOT have webkitdirectory', () => {
    // Find the file input (ref={fileInputRef})
    const fileInputMatch = projectPanelSrc.match(
      /ref=\{fileInputRef\}[\s\S]*?\/>/
    );
    expect(fileInputMatch).not.toBeNull();
    const fileInput = fileInputMatch![0];
    expect(fileInput).not.toContain('webkitdirectory');
    expect(fileInput).not.toContain('directory=""');
  });

  it('folder input DOES have webkitdirectory', () => {
    const folderInputMatch = projectPanelSrc.match(
      /ref=\{folderInputRef\}[\s\S]*?\/>/
    );
    expect(folderInputMatch).not.toBeNull();
    const folderInput = folderInputMatch![0];
    expect(folderInput).toContain('webkitdirectory');
  });

  it('imports openFileDialog and openFolderDialog from tauri', () => {
    expect(projectPanelSrc).toMatch(/import\s*\{[^}]*openFileDialog[^}]*\}\s*from\s*['"].*tauri['"]/);
    expect(projectPanelSrc).toMatch(/import\s*\{[^}]*openFolderDialog[^}]*\}\s*from\s*['"].*tauri['"]/);
  });

  it('file input has accept attribute with media types', () => {
    const fileInputMatch = projectPanelSrc.match(
      /ref=\{fileInputRef\}[\s\S]*?\/>/
    );
    expect(fileInputMatch).not.toBeNull();
    expect(fileInputMatch![0]).toContain('accept={MEDIA_ACCEPT}');
  });

  it('has both openFilePicker and openFolderPicker callbacks', () => {
    expect(projectPanelSrc).toMatch(/const\s+openFilePicker\s*=/);
    expect(projectPanelSrc).toMatch(/const\s+openFolderPicker\s*=/);
  });

  it('listens for cut:import-folder event', () => {
    expect(projectPanelSrc).toContain("'cut:import-folder'");
  });
});

describe('MARKER_IMPORT-DIALOG-FIX: MenuBar entries', () => {
  it('has Import Media... menu item', () => {
    expect(menuBarSrc).toContain("'Import Media...'");
  });

  it('has Import Folder... menu item', () => {
    expect(menuBarSrc).toContain("'Import Folder...'");
  });

  it('Import Media dispatches cut:import-media event', () => {
    // Find the Import Media line and check it dispatches the right event
    const importLine = menuBarSrc.match(/Import Media\.\.\.[\s\S]*?cut:import-media/);
    expect(importLine).not.toBeNull();
  });

  it('Import Folder dispatches cut:import-folder event', () => {
    const importLine = menuBarSrc.match(/Import Folder\.\.\.[\s\S]*?cut:import-folder/);
    expect(importLine).not.toBeNull();
  });
});
