# H10 Reconnaissance: ScanPanel Color Audit

**Mission Status:** COMPLETE
**Date:** 2026-01-29
**Objective:** Identify all colored elements in ScanPanel and map to project color palette

---

## EXECUTIVE SUMMARY

ScanPanel currently contains **colored elements that need to be converted to white/gray tones**. The colored elements are primarily:
- **Blue gradients** - Browse button, drag-over indicator, accents
- **Green indicators** - Pin button (active/pinned state)
- **Red indicators** - Delete/remove actions, file remove hovering
- **Yellow indicators** - Scanning status pulse animation

The **progress bar can remain blue** (already approved) as it's a designed accent element.

---

## PROJECT COLOR PALETTE

Based on analysis of voice.css, ChatSidebar.css, and ScanPanel.css:

### Core Palette (Dark Nolan Theme)
- **Background:** #0a0a0a, #0f0f0f, #111, #1a1a1a, #222 (blacks/near-blacks)
- **Text/Neutral:** #555, #666, #888, #aaa, #ccc, #fff (grays)
- **Borders:** #222, #333, #444, #555, #666 (dark grays)

### Accent Colors (Keep Limited)
- **Blue (Primary):** #4a9eff, #4dabf7, #0EA5E9, #7ab3d4 (various blues)
- **Green (Secondary):** #4ade80, #4aff9e (only for positive/pin states)
- **Red (Alert):** #f87171, #ff4a4a (delete/error only)
- **Yellow (Warning):** #facc15 (scanning status)

---

## COLORED ELEMENTS IN SCANPANEL - DETAILED BREAKDOWN

### SECTION 1: Browse Button (Full Width - Tauri Mode)

**File:** `ScanPanel.css`
**CSS Class:** `.browse-folder-btn-full`
**Location:** Lines 299-340

#### Current Colors:
```css
background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);  /* Blue gradient */
color: #4dabf7;  /* Bright blue text */
border-color: #4dabf7;  /* Blue border on hover */
box-shadow: 0 0 12px rgba(77, 171, 247, 0.2);  /* Blue glow */
```

#### Hover State:
```css
background: linear-gradient(135deg, #252548 0%, #1e3a5f 100%);  /* Darker blue */
border-color: #4dabf7;
box-shadow: 0 0 12px rgba(77, 171, 247, 0.2);
```

#### Browse Label:
```css
color: #ccc;  /* Light gray - OK, keep */
```

**ACTION NEEDED:** Convert blue gradient to white/gray gradient and remove colored glow

---

### SECTION 2: Progress Bar

**File:** `ScanPanel.css`
**CSS Class:** `.scan-progress-fill`
**Location:** Lines 173-179

#### Current Colors:
```css
background: linear-gradient(90deg, #5c8aaa 0%, #7ab3d4 100%);  /* Light blue */
box-shadow: 0 0 8px rgba(122, 179, 212, 0.3);  /* Blue glow */
```

**ACTION NEEDED:** KEEP AS-IS (approved - colored accent)

---

### SECTION 3: File Counter Badge

**File:** `ScanPanel.css`
**CSS Class:** `.scan-stats.complete`
**Location:** Lines 105-109

#### Current Colors:
```css
color: #7ab3d4;  /* Light blue text */
background: rgba(122, 179, 212, 0.12);  /* Light blue background */
```

**ACTION NEEDED:** Change to gray tones

---

### SECTION 4: Pin Button

**File:** `ScanPanel.css`
**CSS Class:** `.pin-btn` and `.pin-btn.pinned`
**Location:** Lines 553-585

#### Default State:
```css
color: #555;  /* Dark gray - OK */
background: rgba(255, 255, 255, 0.1);  /* Neutral - OK */
```

#### Pinned State:
```css
color: #4ade80;  /* Bright green */
background: rgba(74, 222, 128, 0.05);  /* Green tint */
opacity: 1;
```

#### Pinned Hover:
```css
color: #f87171;  /* Red on hover */
background: rgba(248, 113, 113, 0.1);  /* Red tint */
```

#### Pinned File Item:
```css
background: rgba(74, 222, 128, 0.05);  /* Green tint */
border-color: rgba(74, 222, 128, 0.2);  /* Green border */
```

**CHECK ICON in pinned:**
```css
color: #4ade80;  /* Green */
```

**ACTION NEEDED:** Remove green/red colors, convert to white/gray

---

### SECTION 5: Drag & Drop Indicator

**File:** `ScanPanel.css`
**CSS Class:** `.scan-panel.drag-over`
**Location:** Lines 764-780

#### Current Colors:
```css
border: 2px dashed #3b82f6;  /* Bright blue */
background: rgba(59, 130, 246, 0.05);  /* Blue tint */
content: "Drop files or folders here";  /* Message */
color: #3b82f6;  /* Blue text */
```

**ACTION NEEDED:** Convert to white/gray borders and text

---

### SECTION 6: Watched Status Indicators (Unused in Phase 92.9+)

**File:** `ScanPanel.css`
**CSS Class:** `.watched-status.*`
**Location:** Lines 372-383

#### Current Colors:
```css
.watched-status.watching {
  color: #4ade80;  /* Green */
}

.watched-status.scanning {
  color: #facc15;  /* Yellow */
  animation: pulse 1s infinite;
}

.watched-status.error {
  color: #f87171;  /* Red */
}
```

**NOTE:** These are legacy elements (watched directories removed in Phase 92.9) but still in CSS

**ACTION NEEDED:** Can be left as-is (not rendered) or convert for consistency

---

### SECTION 7: Remove Button (Unused)

**File:** `ScanPanel.css`
**CSS Class:** `.remove-btn`
**Location:** Lines 409-424

#### Current Colors:
```css
color: #666;  /* Gray - OK */

.remove-btn:hover {
  color: #f87171;  /* Red on hover */
  background: rgba(248, 113, 113, 0.1);  /* Red tint */
}
```

**NOTE:** Not currently used in rendered component

**ACTION NEEDED:** Leave as-is (unused code)

---

## SUMMARY TABLE: Elements to Change

| Element | Current Color | Type | Location | Replacement |
|---------|---------------|------|----------|------------|
| Browse Button Gradient | #1a1a2e → #16213e (blue) | Background | Line 303 | #1a1a1a → #222 (dark gray) |
| Browse Button Text | #4dabf7 (blue) | Color | Line 306 | #ccc (light gray) |
| Browse Button Border Hover | #4dabf7 (blue) | Border | Line 320 | #555 (dark gray) |
| Browse Button Glow | rgba(77, 171, 247, 0.2) | Box-shadow | Line 321 | Remove or use white/gray |
| File Counter | #7ab3d4 (blue) | Color | Line 107 | #aaa (light gray) |
| File Counter BG | rgba(122, 179, 212, 0.12) | Background | Line 108 | rgba(255, 255, 255, 0.05) |
| Pin Button (pinned) | #4ade80 (green) | Color | Line 578 | #aaa or #999 |
| Pin Button pinned BG | rgba(74, 222, 128, 0.05) | Background | Line 589 | rgba(255, 255, 255, 0.03) |
| Pin Button Border pinned | rgba(74, 222, 128, 0.2) | Border | Line 590 | rgba(255, 255, 255, 0.1) |
| Pin Button Check Icon pinned | #4ade80 (green) | Color | Line 594 | #aaa |
| Pin Button Hover (pinned) | #f87171 (red) | Color | Line 583 | #999 |
| Pin Button Hover BG (pinned) | rgba(248, 113, 113, 0.1) | Background | Line 584 | rgba(255, 255, 255, 0.05) |
| Drag Over Border | #3b82f6 (blue) | Border | Line 765 | #555 or #666 |
| Drag Over BG | rgba(59, 130, 246, 0.05) (blue) | Background | Line 766 | rgba(255, 255, 255, 0.03) |
| Drag Over Text | #3b82f6 (blue) | Color | Line 776 | #aaa |

---

## RECOMMENDED WHITE/GRAY REPLACEMENTS

Based on project palette found in voice.css and ChatSidebar.css:

### Text Colors (Use from Existing Palette)
- **Very Light:** #fff, #ddd, #ccc - Use for primary text
- **Light:** #aaa - Use for secondary/accents
- **Medium:** #888, #666 - Use for tertiary text
- **Dark:** #555 - Use for disabled/muted

### Background Tones
- **Very Dark:** #0a0a0a, #0f0f0f, #111 - Use for main backgrounds (KEEP)
- **Dark:** #1a1a1a, #222 - Use for surface/hover states (KEEP)
- **Medium:** #333, #444 - Use for active/focus states (KEEP)
- **Borders:** #333, #444, #555 - Use for subtle dividers (KEEP)

### Opacity Variants (Already in Palette)
```css
rgba(255, 255, 255, 0.03)  /* Very subtle overlay */
rgba(255, 255, 255, 0.05)  /* Subtle overlay */
rgba(255, 255, 255, 0.08)  /* Light overlay */
rgba(255, 255, 255, 0.1)   /* Moderate overlay */
```

---

## FILES TO MODIFY

1. **Primary:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/scanner/ScanPanel.css`
   - Lines 303-340 (Browse button gradient)
   - Lines 107-108 (File counter color)
   - Lines 578-595 (Pin button states)
   - Lines 765-780 (Drag over indicator)

---

## PHASE REFERENCE

- **Current Phase:** 92.9 (Panel always expanded)
- **Related Phases:**
  - Phase 92.7 - Unified with GroupCreator style
  - Phase 92.8 - Light blue progress bar (KEEP)
  - Phase 100.2 - Native drag & drop
  - Phase I3, I6 - Browse folder button

---

## NEXT STEPS

1. Update ScanPanel.css to replace all colored elements with white/gray equivalents
2. Test hover states and pinned file states
3. Verify consistency with other panels (GroupCreator, ChatSidebar)
4. Keep progress bar blue (already approved accent)
