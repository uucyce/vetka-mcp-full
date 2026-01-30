# H4 Report: Native Dialog API Analysis

## MARKER_H4_PLUGIN_STATUS

**Status:** INSTALLED AND READY ✅

- **Plugin:** `tauri-plugin-dialog`
- **Version:** 2.x (from Cargo.toml line 15)
- **Installed in:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src-tauri/Cargo.toml`
- **Initialization:** Already added to tauri build via `tauri_plugin_dialog::init()` in main.rs

### Cargo.toml Entry
```toml
tauri-plugin-dialog = "2"
```

**No additional installation needed** — the plugin is already available in the project.

---

## MARKER_H4_CAPABILITIES

**Current Status:** PERMISSIONS ALREADY CONFIGURED ✅

The capabilities in `capabilities/default.json` (line 9) already include:
```json
"dialog:default"
```

This is the **minimal permission** needed for file/folder dialogs.

### If You Need Advanced Permissions

For additional dialog features, you may extend permissions to include:
```json
{
  "identifier": "dialog:allow-open",
  "allow": ["*"]
}
```

However, `dialog:default` is sufficient for:
- Opening single files
- Opening multiple files
- Opening single folders
- Opening multiple folders
- File filters (extensions)

**Action Required:** None — existing `"dialog:default"` is sufficient for ScanPanel use case.

---

## MARKER_H4_API_USAGE

### Import Statement (TypeScript)

```typescript
import { open } from '@tauri-apps/plugin-dialog';
```

### Function Signature

```typescript
async function open(options: OpenDialogOptions): Promise<string | string[] | null>
```

### Return Values

The return type depends on your options:
- **Single file:** `string | null`
- **Multiple files:** `string[] | null`
- **Single folder:** `string | null`
- **Multiple folders:** `string[] | null`
- **User cancels:** `null`

### Key Parameters

| Parameter | Type | Purpose |
|-----------|------|---------|
| `directory` | `boolean` | `true` = select folders, `false` = select files |
| `multiple` | `boolean` | `true` = allow multi-select, `false` = single selection |
| `filters` | `DialogFilter[]` | File type filters (e.g., `.ts`, `.js`) |
| `defaultPath` | `string` | Initial directory when dialog opens |
| `title` | `string` | Dialog window title (desktop only) |
| `canCreateDirectories` | `boolean` | Allow folder creation (macOS only) |
| `recursive` | `boolean` | Subdirectory access in directory mode |

---

## MARKER_H4_FILE_VS_FOLDER

### Opening File Picker Dialog

```typescript
// Single file
const file = await open({
  directory: false,
  multiple: false,
  title: "Choose a file"
});
// Returns: "/path/to/file.txt" or null

// Multiple files
const files = await open({
  directory: false,
  multiple: true,
  title: "Choose files"
});
// Returns: ["/path/to/file1.txt", "/path/to/file2.js"] or null

// With file type filters
const file = await open({
  directory: false,
  multiple: false,
  filters: [
    {
      name: 'Text Files',
      extensions: ['txt', 'md']
    },
    {
      name: 'Code Files',
      extensions: ['ts', 'js', 'py']
    }
  ]
});
```

### Opening Folder Picker Dialog

```typescript
// Single folder
const folder = await open({
  directory: true,
  multiple: false,
  title: "Choose a folder"
});
// Returns: "/path/to/folder" or null

// Multiple folders
const folders = await open({
  directory: true,
  multiple: true,
  title: "Choose folders"
});
// Returns: ["/path/to/folder1", "/path/to/folder2"] or null

// With directory creation allowed (macOS)
const folder = await open({
  directory: true,
  multiple: false,
  canCreateDirectories: true,
  title: "Select or create a folder"
});
```

---

## MARKER_H4_CODE_EXAMPLE

### Step 1: Add to tauri.ts Bridge

Add these functions to `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/config/tauri.ts`:

```typescript
// ============================================
// Native Dialog - File/Folder Picker (Phase H4)
// ============================================

import { open as openDialog } from '@tauri-apps/plugin-dialog';

export interface DialogOptions {
  directory?: boolean;
  multiple?: boolean;
  defaultPath?: string;
  title?: string;
  filters?: Array<{ name: string; extensions: string[] }>;
}

/**
 * Open native file picker dialog (Tauri only)
 * Returns single file path or null if cancelled
 *
 * @param options Dialog options
 * @returns File path or null
 *
 * @example
 * const file = await pickFile({ title: "Choose a file" });
 * if (file) console.log("Selected:", file);
 */
export async function pickFile(options?: DialogOptions): Promise<string | null> {
  if (!isTauri()) return null;

  try {
    return await openDialog({
      directory: false,
      multiple: false,
      ...options
    }) as string | null;
  } catch (e) {
    console.warn('File picker failed:', e);
    return null;
  }
}

/**
 * Open native file picker dialog with multiple selection
 * Returns array of file paths or null if cancelled
 *
 * @param options Dialog options
 * @returns File paths array or null
 */
export async function pickFiles(options?: DialogOptions): Promise<string[] | null> {
  if (!isTauri()) return null;

  try {
    return await openDialog({
      directory: false,
      multiple: true,
      ...options
    }) as string[] | null;
  } catch (e) {
    console.warn('Files picker failed:', e);
    return null;
  }
}

/**
 * Open native folder picker dialog (Tauri only)
 * Returns single folder path or null if cancelled
 *
 * @param options Dialog options
 * @returns Folder path or null
 *
 * @example
 * const folder = await pickFolder({ title: "Choose a folder" });
 * if (folder) console.log("Selected folder:", folder);
 */
export async function pickFolder(options?: DialogOptions): Promise<string | null> {
  if (!isTauri()) return null;

  try {
    return await openDialog({
      directory: true,
      multiple: false,
      ...options
    }) as string | null;
  } catch (e) {
    console.warn('Folder picker failed:', e);
    return null;
  }
}

/**
 * Open native folder picker dialog with multiple selection
 * Returns array of folder paths or null if cancelled
 *
 * @param options Dialog options
 * @returns Folder paths array or null
 */
export async function pickFolders(options?: DialogOptions): Promise<string[] | null> {
  if (!isTauri()) return null;

  try {
    return await openDialog({
      directory: true,
      multiple: true,
      ...options
    }) as string[] | null;
  } catch (e) {
    console.warn('Folders picker failed:', e);
    return null;
  }
}
```

### Step 2: Use in Components

```typescript
import { pickFolder, pickFile } from '../../config/tauri';

// In ScanPanel component:
const handleBrowseFolder = async () => {
  const folder = await pickFolder({
    title: "Select a folder to scan"
  });

  if (folder) {
    setPathInput(folder);  // Auto-fill path input
    // Optionally auto-submit:
    // await handleAddFolder();
  }
};

const handleBrowseFile = async () => {
  const file = await pickFile({
    title: "Choose a file",
    filters: [
      { name: 'Text Files', extensions: ['txt', 'md'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  });

  if (file) {
    console.log("Selected file:", file);
  }
};
```

---

## MARKER_H4_INTEGRATION_POINT

### Location: ScanPanel Component

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/scanner/ScanPanel.tsx`

### Integration Strategy

Add a **"Browse Folder" button** next to the path input (around line 749-768):

```typescript
{/* Phase 92.6: Path input + Browse button + RECENTLY SCANNED */}
<div className="path-input-row">
  <input
    ref={pathInputRef}
    type="text"
    className="path-input"
    placeholder="/path/to/folder or click Browse"
    value={pathInput}
    onChange={(e) => setPathInput(e.target.value)}
    onKeyDown={handlePathKeyDown}
    disabled={isAddingPath || isBrowsing}
  />

  {/* NEW: Browse button for native file picker */}
  <button
    className="browse-folder-btn"
    onClick={handleBrowseFolder}
    disabled={isAddingPath || isBrowsing}
    title="Browse for folder (native Finder/Explorer)"
  >
    <FolderIcon />
  </button>

  <button
    className={`add-folder-btn ${isAddingPath ? 'adding' : ''}`}
    onClick={handleAddFolder}
    disabled={isAddingPath || !pathInput.trim() || isBrowsing}
    title="Add folder to scan"
  >
    {isAddingPath ? <LoadingIcon /> : <PlusIcon />}
  </button>
</div>
```

### Handler Implementation

Add to ScanPanel component (after line 503 `handlePathKeyDown`):

```typescript
// Phase H4: Native folder browser button
const [isBrowsing, setIsBrowsing] = useState(false);

const handleBrowseFolder = useCallback(async () => {
  if (!isTauri()) {
    alert('Native folder browser only available in desktop app');
    return;
  }

  setIsBrowsing(true);

  try {
    const folder = await pickFolder({
      title: "Select a folder to scan"
    });

    if (folder) {
      setPathInput(folder);
      // Auto-focus add button for convenience
      setTimeout(() => {
        const addBtn = document.querySelector('.add-folder-btn') as HTMLButtonElement;
        addBtn?.focus();
      }, 0);
    }
  } catch (err) {
    console.error('[ScanPanel] Browse folder error:', err);
    alert('Failed to open folder picker');
  } finally {
    setIsBrowsing(false);
  }
}, []);
```

### CSS Styling

Add to `ScanPanel.css`:

```css
.path-input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.browse-folder-btn {
  padding: 6px 10px;
  background: var(--color-surface-secondary, #2a2a2a);
  border: 1px solid var(--color-border, #444);
  border-radius: 4px;
  color: var(--color-text-secondary, #999);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.browse-folder-btn:hover:not(:disabled) {
  background: var(--color-accent-hover, #1e7a96);
  color: var(--color-accent, #2ba5d7);
  border-color: var(--color-accent, #2ba5d7);
}

.browse-folder-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.browse-folder-btn svg {
  width: 16px;
  height: 16px;
}
```

### Import Requirements

Add these imports to ScanPanel.tsx (after line 25):

```typescript
import { isTauri, pickFolder, type DialogOptions } from '../../config/tauri';
```

---

## MARKER_H4_BROWSER_FALLBACK

For browser mode (non-Tauri), use the File System Access API:

```typescript
// Browser fallback for file selection
async function browserFilePicker(): Promise<FileSystemFileHandle | null> {
  try {
    const [handle] = await (window as any).showOpenFilePicker({
      types: [{
        description: "All files",
        accept: { "*/*": [".*"] }
      }]
    });
    return handle;
  } catch (err) {
    console.log('File picker cancelled or not supported');
    return null;
  }
}

// Browser fallback for folder selection
async function browserFolderPicker(): Promise<FileSystemDirectoryHandle | null> {
  try {
    return await (window as any).showDirectoryPicker();
  } catch (err) {
    console.log('Folder picker cancelled or not supported');
    return null;
  }
}
```

**Note:** Browser File System Access API has limited support. Desktop Tauri app is recommended for reliable native picker support.

---

## MARKER_H4_USAGE_EXAMPLE

### Complete ScanPanel Integration Example

```typescript
// In ScanPanel.tsx component handler
import { pickFolder } from '../../config/tauri';

const handleBrowseFolder = useCallback(async () => {
  if (!isTauri()) {
    alert('Feature available in desktop app only');
    return;
  }

  setIsBrowsing(true);

  try {
    const folder = await pickFolder({
      title: "Select a folder to scan"
      // defaultPath could be last used path
    });

    if (folder) {
      setPathInput(folder);

      // Optional: auto-submit if user wants
      // Commented out for safety - let user review path first
      // await handleAddFolder();
    }
  } catch (err) {
    console.error('Folder picker error:', err);
  } finally {
    setIsBrowsing(false);
  }
}, []);
```

---

## MARKER_H4_TESTING_CHECKLIST

Before integrating, verify:

- [ ] Run Tauri app in development: `npm run tauri dev`
- [ ] Click Browse button → Finder/Explorer dialog opens
- [ ] Select folder → path auto-fills in input
- [ ] Cancel dialog → input remains unchanged
- [ ] Try multiple folders → verify path handling
- [ ] Test in browser mode → shows fallback message

---

## MARKER_H4_LIMITATIONS

### Platform-Specific Notes

| Feature | macOS | Windows | Linux |
|---------|-------|---------|-------|
| File picker | ✅ Native | ✅ Native | ✅ Native |
| Folder picker | ✅ Native | ✅ Native | ✅ Native |
| Multiple select | ✅ Yes | ✅ Yes | ✅ Yes |
| Create folder | ✅ Yes | ❌ No | ❌ No |
| File filters | ✅ Yes | ✅ Yes | ✅ Yes |

### Notes

- Dialog runs in native system (Finder on macOS, Explorer on Windows)
- Selected paths are automatically added to Tauri's filesystem scope
- Returns `null` if user cancels (not an error condition)
- No browser support — desktop app only
- File paths are absolute (e.g., `/Users/danila/Documents/project`)

---

## SUMMARY

**Key Takeaways:**

1. **Plugin Status**: `tauri-plugin-dialog` already installed ✅
2. **Permissions**: `dialog:default` already configured ✅
3. **API**: Simple `open()` function with intuitive options
4. **Integration**: Add browse button next to path input in ScanPanel
5. **Implementation**: 4 helper functions in tauri.ts bridge (`pickFile`, `pickFiles`, `pickFolder`, `pickFolders`)
6. **UX**: Replace typed paths with native picker for better UX
7. **Fallback**: Browser mode shows alert if desktop app not available

**Next Steps:**
1. Add functions to `/client/src/config/tauri.ts`
2. Add browse button handler to ScanPanel component
3. Add CSS styling for new button
4. Test in development build
5. Verify path auto-fills correctly

---

**References:**
- [Tauri Dialog Plugin Documentation](https://v2.tauri.app/reference/javascript/dialog/)
- [Tauri Plugin Dialog - Main Guide](https://v2.tauri.app/plugin/dialog/)
- [GitHub Discussion - File/Directory Selection](https://github.com/tauri-apps/tauri/discussions/11102)
