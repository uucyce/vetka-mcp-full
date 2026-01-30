# src/visualizer/tree_renderer.py
"""
VETKA Phase 11.2 Three.js Renderer - Theory Compliant.

Generates interactive HTML visualization from VETKA-JSON v1.3.

Theory compliance (Unified Theory v1.2):
- Trees = Trunk (cylinder) + Branches (curved tubes) + Leaves (rectangular cards)
- NO SPHERES - proper tree geometry only
- Phylotaxis positioning with Golden Angle 137.5 degrees
- LOD with entropy*evalScore importance
- Human is always human (no role selector)

@status: active
@phase: 96
@depends: json, os, pathlib, typing
@used_by: src.visualizer.__init__, src.api.routes.tree_routes
"""

import json
import os
from pathlib import Path
from typing import Optional


class TreeRenderer:
    """Generates Three.js HTML visualization from VETKA-JSON."""

    def __init__(self):
        self.template = self._get_template()

    def render(
        self,
        vetka_json: dict = None,
        output_path: Optional[str] = None,
        use_api: bool = False,
    ) -> str:
        """
        Render VETKA-JSON to interactive HTML.

        Args:
            vetka_json: VETKA-JSON v1.3 format data (optional if use_api=True)
            output_path: Optional path to save HTML file
            use_api: If True, fetch data from /api/tree/data instead of embedding

        Returns:
            HTML string
        """
        html = self.template

        if use_api or vetka_json is None:
            # Use API mode - data loaded dynamically from /api/tree/data
            # No replacement needed, template already has async loader
            pass
        else:
            # Embed data directly for static export
            # Override the loadRealData function to use embedded data
            embedded_script = f"""
        // EMBEDDED DATA MODE (static export)
        VETKA_DATA = {json.dumps(vetka_json, indent=2)};

        // Override loadRealData to use embedded data
        async function loadRealData() {{
            console.log('Using embedded data:', VETKA_DATA.tree?.nodes?.length, 'nodes');
            return VETKA_DATA;
        }}
"""
            html = html.replace("let VETKA_DATA = null;", embedded_script)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)

        return html

    def _get_template(self) -> str:
        """Theory-compliant template: Trunk + Branches + Leaves (NO SPHERES)."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VETKA - Knowledge Tree</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🌳</text></svg>">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Inter, system-ui, -apple-system, sans-serif;
            background: #000000;  /* Pure black per 2015 spec */
            color: #f0f0f0;
            overflow: hidden;
        }
        #canvas-container { width: 100vw; height: 100vh; }

        /* Info Panel */
        #info-panel {
            position: fixed;
            top: 20px;
            left: 20px;
            background: rgba(22, 22, 22, 0.95);
            backdrop-filter: blur(10px);
            padding: 16px 20px;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.1);
            z-index: 100;
            min-width: 240px;
        }
        #info-panel h2 { font-size: 16px; color: #8AA0B0; margin-bottom: 8px; }  /* Itten: muted blue-gray */
        #tree-stats { font-size: 13px; color: #888; margin-bottom: 12px; }

        /* Sorting Controls */
        .sort-controls { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
        .sort-btn {
            background: rgba(40, 40, 40, 0.9);
            border: 1px solid rgba(255,255,255,0.1);
            color: #aaa;
            padding: 6px 10px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 11px;
            transition: all 0.15s;
        }
        .sort-btn:hover { background: rgba(60, 60, 60, 0.9); color: #fff; }
        .sort-btn.active { background: #4A6B8A; color: #fff; border-color: #5A7B9A; }  /* Itten: muted blue */

        /* Search */
        #search-input {
            width: 100%;
            background: rgba(30, 30, 30, 0.9);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 6px;
            padding: 8px 10px;
            color: #fff;
            font-size: 12px;
            margin-top: 8px;
        }
        #search-input:focus { outline: none; border-color: #4A6B8A; }  /* Itten: muted blue */
        #search-input::placeholder { color: #555; }

        /* Search Results */
        #search-results {
            display: none;
            margin-top: 8px;
            padding: 8px;
            background: rgba(30, 30, 30, 0.95);
            border-radius: 6px;
            font-size: 11px;
        }
        #search-results.active { display: block; }
        #search-count { color: #8AA0B0; font-weight: 600; }  /* Itten: muted blue-gray */
        #create-branch-btn {
            margin-top: 8px;
            width: 100%;
            background: linear-gradient(135deg, #4A6B8A, #5A7B9A);  /* Itten: muted blue gradient */
            border: none;
            color: #E0E0E0;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        #create-branch-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(74, 107, 138, 0.3);
        }

        /* Save Button - Itten muted palette */
        .btn-save {
            background: #2A3A4A;
            color: #B8C4D0;
            border: 1px solid #3A4A5A;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 11px;
            font-weight: 600;
            transition: all 0.2s ease;
            width: 100%;
            margin-top: 8px;
        }
        .btn-save:hover {
            background: #3A4A5A;
            border-color: #5A7A8A;
        }
        .btn-save.saving {
            opacity: 0.6;
            cursor: wait;
        }
        .btn-save.saved {
            background: #2A4A3A;
            border-color: #3A5A4A;
            color: #A0D0B0;
        }
        .btn-save.error {
            background: #4A2A2A;
            border-color: #5A3A3A;
            color: #D0A0A0;
        }

        /* Controls */
        #controls {
            position: fixed;
            bottom: 20px;
            left: 20px;
            display: flex;
            gap: 8px;
            z-index: 100;
        }
        #controls button {
            background: rgba(30, 30, 30, 0.95);
            border: 1px solid rgba(255,255,255,0.1);
            color: #fff;
            padding: 10px 18px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.15s ease;
        }
        #controls button:hover { background: rgba(50, 50, 50, 0.95); }
        #controls button.active { background: #8B4513; color: #fff; }

        /* Phase 17.5: Mode Toggle (Directory ↔ Knowledge) */
        #mode-toggle-panel {
            position: fixed;
            left: 20px;
            top: 50%;
            transform: translateY(-50%);
            display: flex;
            flex-direction: column;
            gap: 8px;
            z-index: 150;
            background: rgba(22, 22, 22, 0.95);
            backdrop-filter: blur(10px);
            padding: 12px;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.1);
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }
        #mode-toggle-panel .mode-btn {
            padding: 12px 16px;
            background: rgba(60, 60, 60, 0.9);
            color: #aaa;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s ease;
            text-align: left;
        }
        #mode-toggle-panel .mode-btn:hover {
            background: rgba(80, 80, 80, 0.95);
            color: #fff;
        }
        #mode-toggle-panel .mode-btn.active {
            background: linear-gradient(135deg, #8B4513, #9A4A8B);
            color: #fff;
            border-color: rgba(255,255,255,0.3);
            box-shadow: 0 2px 10px rgba(139, 69, 19, 0.4);
        }

        /* Phase 17.3: Export Panel */
        #export-panel {
            position: fixed;
            bottom: 20px;
            right: 20px;
            display: flex;
            gap: 8px;
            z-index: 100;
        }
        #export-panel button {
            padding: 8px 14px;
            background: rgba(40, 40, 40, 0.9);
            color: #ccc;
            border: 1px solid #555;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
        }
        #export-panel button:hover {
            background: rgba(60, 60, 60, 0.95);
            color: #fff;
            border-color: #888;
        }

        /* Animations */
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-10px); }
            to { opacity: 1; transform: translateX(0); }
        }

        /* ✅ Artifact Panel - Black & White like Chat - Phase 17-M */
        .artifact-panel {
            position: fixed;
            left: 20px;  /* Left side of screen */
            top: 20px;
            width: 500px;
            min-width: 300px;
            min-height: 200px;
            height: calc(100vh - 40px);
            max-height: calc(100vh - 40px);
            background: rgba(26, 26, 26, 0.95);  /* Same as chat with transparency */
            backdrop-filter: blur(10px);
            border: 1px solid rgba(100, 100, 100, 0.3);
            border-radius: 12px;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6);
            z-index: 200;  /* Same level as chat */
            overflow: auto;  /* FIX: Allow scrolling instead of clipping content */
        }

        .artifact-panel.hidden {
            display: none !important;  /* Completely hide when closed */
            pointer-events: none;
        }

        .artifact-panel.fullscreen {
            left: 0 !important;
            top: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            max-width: 100vw;
            max-height: 100vh;
            border-radius: 0;
        }

        .artifact-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 20px;
            border-bottom: 1px solid #333;
            background: #222;  /* Black/white only */
            color: #e0e0e0;
            cursor: move;
        }

        .artifact-header h3 {
            margin: 0;
            color: #e0e0e0;
            font-size: 15px;
            font-weight: 600;
            letter-spacing: 0.3px;
        }

        .artifact-type {
            font-size: 12px;
            color: #888;
            padding: 4px 8px;
            background: #333;
            border-radius: 4px;
        }

        .fullscreen-btn,
        .close-btn {
            background: none;
            border: none;
            color: #888;
            cursor: pointer;
            font-size: 20px;
            padding: 0 4px;
        }

        .fullscreen-btn:hover,
        .close-btn:hover {
            color: #fff;
        }

        .artifact-content {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            color: #e0e0e0;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 13px;
            line-height: 1.5;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .artifact-content code {
            background: #2a2a2a;
            padding: 2px 6px;
            border-radius: 3px;
            color: #e0e0e0;
        }

        .artifact-content pre {
            background: #2a2a2a;
            padding: 12px;
            border-radius: 6px;
            overflow-x: auto;
        }

        .artifact-footer {
            display: flex;
            gap: 12px;
            padding: 16px 20px;
            border-top: 1px solid #333;
            background: #222;
        }

        .btn-primary {
            flex: 1;
            padding: 11px 18px;
            background: #333;  /* Black/white - no orange */
            color: #fff;
            border: 1px solid #555;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 600;
            font-size: 13px;
            transition: all 0.2s ease;
        }

        .btn-primary:hover {
            background: #444;
            border-color: #666;
        }

        .btn-secondary {
            flex: 1;
            padding: 11px 18px;
            background: #2a2a2a;
            color: #e0e0e0;
            border: 1px solid #404040;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s ease;
        }

        .btn-secondary:hover {
            background: #353535;
            border-color: #505050;
        }

        .btn-cancel {
            flex: 0.8;
            padding: 11px 18px;
            background: transparent;
            color: #888;
            border: 1px solid #404040;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s ease;
        }

        .btn-cancel:hover {
            background: #2a2a2a;
            color: #e0e0e0;
        }

        /* ============ Phase 17-M: Artifact Panel Enhancements ============ */

        /* Toolbar buttons layout */
        .artifact-toolbar {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }

        .toolbar-btn {
            background: transparent;
            border: 1px solid #444;
            color: #888;
            padding: 6px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .toolbar-btn:hover {
            background: #333;
            border-color: #555;
            color: #fff;
        }

        .toolbar-btn.active {
            background: #444;
            border-color: #666;
            color: #fff;
        }

        .toolbar-btn.save-btn {
            background: #2a4a2a;
            border-color: #3a6a3a;
            color: #8f8;
        }

        .toolbar-btn.save-btn:hover {
            background: #3a5a3a;
            border-color: #4a7a4a;
        }

        .toolbar-separator {
            width: 1px;
            height: 20px;
            background: #444;
            margin: 0 4px;
        }

        /* Edit mode textarea */
        .artifact-textarea {
            width: 100%;
            height: 100%;
            background: #1a1a1a;
            color: #e0e0e0;
            border: none;
            padding: 20px;
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
            font-size: 13px;
            line-height: 1.5;
            resize: none;
            outline: none;
            box-sizing: border-box;
        }

        .artifact-textarea:focus {
            outline: none;
            box-shadow: inset 0 0 0 2px #444;
        }

        /* Search bar */
        .artifact-search-bar {
            display: none;
            padding: 8px 20px;
            background: #222;
            border-bottom: 1px solid #333;
            gap: 8px;
            align-items: center;
        }

        .artifact-search-bar.visible {
            display: flex;
        }

        .artifact-search-bar input {
            flex: 1;
            background: #1a1a1a;
            border: 1px solid #444;
            color: #e0e0e0;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 13px;
            outline: none;
        }

        .artifact-search-bar input:focus {
            border-color: #666;
        }

        .artifact-search-bar .search-info {
            color: #888;
            font-size: 12px;
            min-width: 60px;
        }

        .artifact-search-bar button {
            background: #333;
            border: 1px solid #444;
            color: #888;
            padding: 4px 8px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }

        .artifact-search-bar button:hover {
            background: #444;
            color: #fff;
        }

        /* Search highlights */
        mark {
            background: #5a5a2a;
            color: #fff;
            padding: 1px 2px;
            border-radius: 2px;
        }

        mark.current {
            background: #8a8a3a;
            box-shadow: 0 0 0 2px #aa0;
        }

        /* Code block styling */
        .code-block {
            background: #1a1a1a;
            border-radius: 6px;
            overflow: hidden;
        }

        .code-block pre {
            margin: 0;
            padding: 16px;
            overflow-x: auto;
        }

        .code-block code {
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
            font-size: 13px;
            line-height: 1.5;
        }

        /* Plain text styling */
        .plain-text {
            white-space: pre-wrap;
            word-break: break-word;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 13px;
            line-height: 1.5;
        }

        /* Markdown body styling */
        .markdown-body {
            color: #e0e0e0;
            line-height: 1.6;
        }

        .markdown-body h1, .markdown-body h2, .markdown-body h3 {
            color: #fff;
            border-bottom: 1px solid #333;
            padding-bottom: 8px;
            margin-top: 24px;
        }

        .markdown-body h1 { font-size: 1.8em; }
        .markdown-body h2 { font-size: 1.5em; }
        .markdown-body h3 { font-size: 1.2em; }

        .markdown-body a {
            color: #6af;
        }

        .markdown-body blockquote {
            border-left: 4px solid #444;
            padding-left: 16px;
            margin-left: 0;
            color: #aaa;
        }

        .markdown-body ul, .markdown-body ol {
            padding-left: 24px;
        }

        .markdown-body li {
            margin: 4px 0;
        }

        .markdown-body table {
            border-collapse: collapse;
            width: 100%;
        }

        .markdown-body th, .markdown-body td {
            border: 1px solid #444;
            padding: 8px 12px;
        }

        .markdown-body th {
            background: #2a2a2a;
        }

        /* Toast notifications */
        .artifact-toast {
            position: fixed;
            bottom: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: #333;
            color: #fff;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            z-index: 10000;
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        }

        .artifact-toast.visible {
            opacity: 1;
        }

        .artifact-toast.success {
            background: #2a4a2a;
            border: 1px solid #3a6a3a;
        }

        .artifact-toast.error {
            background: #4a2a2a;
            border: 1px solid #6a3a3a;
        }

        /* Loading spinner */
        .loading-spinner {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100%;
            color: #888;
        }

        .loading-spinner::after {
            content: '';
            width: 32px;
            height: 32px;
            border: 3px solid #444;
            border-top-color: #888;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Error message */
        .error-message {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 100%;
            color: #f88;
            text-align: center;
            padding: 20px;
        }

        .error-message .error-icon {
            font-size: 48px;
            margin-bottom: 16px;
        }

        /* Line numbers for code */
        .line-numbers {
            counter-reset: line;
        }

        .line-numbers .line {
            display: block;
            padding-left: 60px;
            text-indent: -60px;
            white-space: pre-wrap;
            word-break: break-all;
        }

        .line-numbers .line-num {
            display: inline-block;
            width: 40px;
            padding-right: 12px;
            margin-right: 8px;
            text-align: right;
            color: #555;
            border-right: 1px solid #333;
            user-select: none;
        }

        /* ============ End Phase 17-M Styles ============ */

        /* ============ Phase 17-O: Search Bar ============ */
        .vetka-search-bar {
            position: fixed;
            top: 80px;
            left: 50%;
            transform: translateX(-50%);
            width: 500px;
            max-width: 90vw;
            background: rgba(30, 30, 30, 0.95);
            backdrop-filter: blur(10px);
            border: 1px solid #444;
            border-radius: 12px;
            padding: 12px;
            z-index: 1000;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
            display: none;
        }

        .vetka-search-bar.visible {
            display: block;
        }

        .vetka-search-bar input {
            width: 100%;
            padding: 12px 16px;
            font-size: 16px;
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            color: #fff;
        }

        .vetka-search-bar input:focus {
            outline: none;
            border-color: #007acc;
        }

        .vetka-search-bar input::placeholder {
            color: #666;
        }

        .search-results {
            max-height: 400px;
            overflow-y: auto;
            margin-top: 8px;
        }

        .search-result {
            padding: 12px;
            border-radius: 6px;
            cursor: pointer;
            border-bottom: 1px solid #333;
            transition: background 0.15s ease;
        }

        .search-result:hover {
            background: rgba(0, 122, 204, 0.2);
        }

        .search-result:last-child {
            border-bottom: none;
        }

        .result-name {
            font-weight: 600;
            color: #fff;
            font-size: 14px;
        }

        .result-path {
            font-size: 12px;
            color: #888;
            margin-top: 2px;
        }

        .result-snippet {
            font-size: 13px;
            color: #aaa;
            margin-top: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .result-meta {
            display: flex;
            gap: 8px;
            margin-top: 4px;
            font-size: 11px;
            color: #666;
        }

        .search-loading, .search-empty, .search-error {
            padding: 20px;
            text-align: center;
            color: #888;
        }

        .search-error {
            color: #ff6b6b;
        }

        .search-close {
            position: absolute;
            top: 12px;
            right: 12px;
            background: transparent;
            border: none;
            color: #888;
            font-size: 18px;
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 4px;
        }

        .search-close:hover {
            background: #333;
            color: #fff;
        }

        .search-hint {
            font-size: 11px;
            color: #666;
            margin-top: 8px;
            text-align: center;
        }

        /* ============ Phase 17-Q: Chat Badges ============ */
        .node-badge {
            position: absolute;
            top: -6px;
            right: -6px;
            display: flex;
            align-items: center;
            justify-content: center;
            min-width: 18px;
            height: 18px;
            padding: 0 5px;
            border-radius: 9px;
            font-size: 10px;
            font-weight: 500;
            pointer-events: none;
            backdrop-filter: blur(4px);
        }

        /* Default: subtle gray for total messages */
        .node-badge.total {
            background: rgba(120, 120, 120, 0.5);
            color: rgba(255, 255, 255, 0.8);
            border: 1px solid rgba(150, 150, 150, 0.3);
        }

        /* Unread: subtle green */
        .node-badge.unread {
            background: rgba(76, 175, 80, 0.4);
            color: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(76, 175, 80, 0.3);
        }

        /* Hide badge when count is 0 */
        .node-badge[data-count="0"],
        .node-badge:empty {
            display: none;
        }

        /* ============ Phase 17-P: Branch Context Display ============ */
        .chat-context-display {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 4px 8px;
            background: rgba(40, 40, 40, 0.8);
            border-radius: 4px;
            font-size: 11px;
            color: #aaa;
        }

        .context-icon {
            font-size: 14px;
        }

        .context-path {
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .context-type {
            padding: 2px 6px;
            background: #333;
            border-radius: 3px;
            font-size: 10px;
            color: #888;
        }

        /* ============ End Phase 17-O/P/Q Styles ============ */

        /* Artifact trigger button in chat */
        .artifact-trigger {
            position: absolute;
            bottom: 130px;  /* Raised above input area */
            left: 10px;
            background: #333;
            color: #e0e0e0;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 6px 10px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            z-index: 10;
            transition: all 0.2s ease;
        }

        .artifact-trigger:hover {
            background: #444;
            border-color: #666;
            transform: translateX(-2px);
        }

        /* Chat Panel - Simple Black (NO COLORS) */
        #chat-panel {
            position: fixed;
            top: 20px;
            right: 20px;
            width: 380px;
            /* height: calc(100vh - 40px); -- REMOVED: This blocked JS resize! */
            /* Instead, set initial height via JS or use a default that JS can override */
            height: 600px;  /* Default height - JS resize will override this */
            max-height: calc(100vh - 40px);      /* Prevent going off-screen */
            min-width: 200px;                    /* Matches JS minWidth */
            min-height: 150px;                   /* Matches JS minHeight */
            background: rgba(26, 26, 26, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            border: 1px solid rgba(100, 100, 100, 0.3);
            display: flex;
            flex-direction: column;
            z-index: 200;
            box-shadow: 0 4px 16px rgba(0,0,0,0.6);
            /* resize removed - JS handles resize via .resize-handle elements */
            overflow: hidden;
        }
        #chat-panel.dragging { box-shadow: 0 8px 24px rgba(0,0,0,0.8); }
        #chat-panel.docked-bottom {
            top: auto;
            bottom: 0;
            left: 0;
            right: 0;
            width: 100%;
            height: 250px;
            max-height: 50vh;
            border-radius: 16px 16px 0 0;
            /* resize removed - JS handles this */
        }
        #chat-panel.docked-bottom #chat-messages {
            flex-direction: row;
            flex-wrap: wrap;
        }

        /* Resize handles - 4 углов + 2 края */
        .resize-handle {
            position: absolute;
            width: 16px;
            height: 16px;
            z-index: 10;
        }

        .resize-handle-nw {  /* Верхний левый */
            top: 0;
            left: 0;
            cursor: nwse-resize;
            border-top: 3px solid rgba(255,255,255,0.2);
            border-left: 3px solid rgba(255,255,255,0.2);
            border-radius: 16px 0 0 0;
        }

        .resize-handle-ne {  /* Верхний правый */
            top: 0;
            right: 0;
            cursor: nesw-resize;
            border-top: 3px solid rgba(255,255,255,0.2);
            border-right: 3px solid rgba(255,255,255,0.2);
            border-radius: 0 16px 0 0;
        }

        .resize-handle-sw {  /* Нижний левый */
            bottom: 0;
            left: 0;
            cursor: nesw-resize;
            border-bottom: 3px solid rgba(255,255,255,0.2);
            border-left: 3px solid rgba(255,255,255,0.2);
            border-radius: 0 0 0 16px;
        }

        .resize-handle-se {  /* Нижний правый */
            bottom: 0;
            right: 0;
            cursor: nwse-resize;
            border-bottom: 3px solid rgba(255,255,255,0.2);
            border-right: 3px solid rgba(255,255,255,0.2);
            border-radius: 0 0 16px 0;
        }

        .resize-handle:hover {
            border-color: rgba(100, 149, 237, 0.8);  /* Cornflower blue */
        }

        /* Боковые resize edges - wider and more visible */
        .resize-edge-left {
            position: absolute;
            left: -3px;
            top: 20px;
            bottom: 20px;
            width: 10px;
            cursor: ew-resize;
            background: linear-gradient(to right, rgba(100, 149, 237, 0.15), transparent);
            z-index: 100;
        }

        .resize-edge-left:hover {
            background: linear-gradient(to right, rgba(100, 149, 237, 0.5), transparent);
        }

        .resize-edge-right {
            position: absolute;
            right: -3px;
            top: 20px;
            bottom: 20px;
            width: 10px;
            cursor: ew-resize;
            background: linear-gradient(to left, rgba(100, 149, 237, 0.15), transparent);
            z-index: 100;
        }

        .resize-edge-right:hover {
            background: linear-gradient(to left, rgba(100, 149, 237, 0.5), transparent);
        }

        /* Top edge resize - wider and more visible */
        .resize-edge-top {
            position: absolute;
            top: -3px;
            left: 20px;
            right: 20px;
            height: 10px;
            cursor: ns-resize;
            background: linear-gradient(to bottom, rgba(100, 149, 237, 0.15), transparent);
            z-index: 100;
        }

        .resize-edge-top:hover {
            background: linear-gradient(to bottom, rgba(100, 149, 237, 0.5), transparent);
        }

        /* Bottom edge resize - VERY VISIBLE grab bar */
        .resize-edge-bottom {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 16px;
            cursor: ns-resize;
            background: linear-gradient(to top, rgba(80, 80, 80, 0.9), rgba(50, 50, 50, 0.5));
            border-top: 1px solid rgba(100, 100, 100, 0.4);
            z-index: 100;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 0 0 12px 12px;
        }

        /* Visible grab indicator */
        .resize-edge-bottom::after {
            content: '';
            width: 40px;
            height: 4px;
            background: rgba(150, 150, 150, 0.6);
            border-radius: 2px;
        }

        .resize-edge-bottom:hover {
            background: linear-gradient(to top, rgba(100, 149, 237, 0.6), rgba(70, 100, 180, 0.3));
        }

        .resize-edge-bottom:hover::after {
            background: rgba(100, 149, 237, 0.9);
        }

        /* Dock toggle button - POSITIONED AT BOTTOM */
        .dock-toggle {
            position: absolute;
            bottom: 12px;                          /* ✅ Bottom positioning */
            right: 12px;
            background: rgba(60, 60, 60, 0.85);
            border: none;
            color: #888;
            width: 28px;
            height: 28px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1002;                         /* Above resize handles */
            transition: all 0.2s ease;
        }
        .dock-toggle:hover {
            background: rgba(100, 100, 100, 0.9);
            transform: scale(1.1);
        }
        .dock-toggle svg {
            stroke: #888;
            transition: stroke 0.2s ease;
        }
        .dock-toggle:hover svg {
            stroke: #fff;
        }

        #chat-header {
            padding: 14px 18px;
            background: rgba(35, 35, 35, 0.95);
            border-radius: 12px 12px 0 0;
            cursor: move;
            user-select: none;
            border-bottom: 1px solid rgba(100, 100, 100, 0.2);
        }
        #chat-context { display: flex; align-items: center; gap: 6px; font-size: 12px; flex-wrap: wrap; }
        .selected-node-path { color: #aaa; font-size: 12px; font-weight: 500; }

        #chat-messages { flex: 1; overflow-y: auto; padding: 16px; scroll-behavior: smooth; }
        #chat-messages::-webkit-scrollbar { width: 6px; }
        #chat-messages::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }

        /* Messages - улучшенные стили с цветами агентов */
        .msg {
            padding: 12px 16px;
            margin: 8px 0;
            border-radius: 12px;
            background: rgba(30, 30, 30, 0.95);
            border-left: 4px solid #666;
            animation: msgFadeIn 0.3s ease-out;
        }

        @keyframes msgFadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Цвета по агентам - ЯРКИЕ И ЗАМЕТНЫЕ */
        .msg.PM {
            border-left-color: #FFB347;  /* Оранжевый - PM */
            background: linear-gradient(135deg, rgba(255,179,71,0.15) 0%, rgba(30,30,30,0.95) 100%);
        }

        .msg.Dev {
            border-left-color: #6495ED;  /* Синий - Developer */
            background: linear-gradient(135deg, rgba(100,149,237,0.15) 0%, rgba(30,30,30,0.95) 100%);
        }

        .msg.QA {
            border-left-color: #9370DB;  /* Фиолетовый - QA */
            background: linear-gradient(135deg, rgba(147,112,219,0.15) 0%, rgba(30,30,30,0.95) 100%);
        }

        .msg.Hostess {
            border-left-color: #32CD32;  /* Зелёный - Hostess */
            background: linear-gradient(135deg, rgba(50,205,50,0.15) 0%, rgba(30,30,30,0.95) 100%);
        }

        .msg.Human {
            border-left-color: #32CD32;  /* Зелёный - User */
            background: linear-gradient(135deg, rgba(50,205,50,0.15) 0%, rgba(30,30,30,0.95) 100%);
            margin-left: 20px;  /* Отступ для user сообщений */
        }

        .msg.System {
            border-left-color: #888;
            font-style: italic;
            opacity: 0.7;
        }

        /* PHASE F: Summary Message */
        .msg.Summary {
            border-left-color: #32CD32;
            background: linear-gradient(135deg, rgba(50, 205, 50, 0.15) 0%, rgba(34, 139, 34, 0.1) 100%);
            border: 1px solid rgba(50, 205, 50, 0.3);
        }

        .msg.Summary .msg-avatar {
            background: linear-gradient(135deg, #32CD32 0%, #228B22 100%);
        }

        .msg.Summary .msg-agent {
            color: #32CD32;
            font-weight: 700;
        }

        .msg.Summary .msg-content {
            color: #90EE90;
            font-weight: 500;
        }

        .msg:hover { background: rgba(45, 45, 45, 0.9); }

        .msg-header { display: flex; justify-content: space-between; margin-bottom: 8px; align-items: center; }
        
        .msg-agent { 
            font-weight: 600; 
            font-size: 12px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        
        .msg-agent-icon {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
        }

        .msg.PM .msg-agent { color: #FFB347; }
        .msg.PM .msg-agent-icon { background: rgba(255,179,71,0.3); }
        
        .msg.Dev .msg-agent { color: #6495ED; }
        .msg.Dev .msg-agent-icon { background: rgba(100,149,237,0.3); }
        
        .msg.QA .msg-agent { color: #9370DB; }
        .msg.QA .msg-agent-icon { background: rgba(147,112,219,0.3); }
        
        .msg.Hostess .msg-agent { color: #32CD32; }
        .msg.Hostess .msg-agent-icon { background: rgba(50,205,50,0.3); }
        
        .msg.Human .msg-agent { color: #32CD32; }
        .msg.Human .msg-agent-icon { background: rgba(50,205,50,0.3); }
        
        .msg.System .msg-agent { color: #888; }

        /* Agent Avatar with Gradient Colors */
        .msg-avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: 600;
            color: white;
            margin-right: 8px;
            flex-shrink: 0;
        }

        .msg.PM .msg-avatar { background: linear-gradient(135deg, #FFB347 0%, #FF8C00 100%); }
        .msg.Dev .msg-avatar { background: linear-gradient(135deg, #6495ED 0%, #4169E1 100%); }
        .msg.QA .msg-avatar { background: linear-gradient(135deg, #9370DB 0%, #8A2BE2 100%); }
        .msg.Hostess .msg-avatar { background: linear-gradient(135deg, #32CD32 0%, #228B22 100%); }
        .msg.Human .msg-avatar { background: linear-gradient(135deg, #87CEEB 0%, #4682B4 100%); }
        .msg.System .msg-avatar { background: linear-gradient(135deg, #A9A9A9 0%, #696969 100%); }

        /* Status Emoji Indicator */
        .msg-status-emoji {
            display: inline-block;
            margin-left: 4px;
            font-size: 14px;
            vertical-align: middle;
        }

        .msg-status-emoji.thinking {
            animation: pulse 1.5s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.6; transform: scale(1.1); }
        }

        .msg-time { font-size: 10px; color: #555; }
        .msg-content { font-size: 13px; line-height: 1.5; color: #ddd; }
        .msg-delegation { margin-top: 8px; padding: 5px 8px; background: rgba(60, 60, 60, 0.5); border-radius: 4px; font-size: 11px; color: #999; }
        .msg-artifacts { margin-top: 8px; display: flex; gap: 6px; flex-wrap: wrap; }
        .artifact { background: rgba(60, 60, 60, 0.5); color: #aaa; padding: 4px 8px; border-radius: 4px; font-size: 11px; cursor: pointer; }
        
        /* Artifact Link - Clickable */
        .artifact-link {
            display: inline-block;
            margin-top: 8px;
            padding: 6px 12px;
            background: rgba(96, 165, 250, 0.15);
            color: #60a5fa;
            text-decoration: none;
            border-radius: 4px;
            font-size: 12px;
            cursor: pointer;
            border: 1px solid rgba(96, 165, 250, 0.3);
            transition: all 0.2s ease;
        }
        
        .artifact-link:hover {
            background: rgba(96, 165, 250, 0.25);
            border-color: rgba(96, 165, 250, 0.6);
            text-decoration: none;
        }
        
        .artifact-link:active {
            background: rgba(96, 165, 250, 0.35);
        }
        
        .msg-status { margin-top: 6px; font-size: 10px; color: #888; }

        /* PHASE F: Quick Actions */
        .quick-actions-container {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 12px 16px;
            margin: 12px 0;
            background: rgba(100, 149, 237, 0.08);
            border: 1px solid rgba(100, 149, 237, 0.2);
            border-radius: 8px;
            flex-wrap: wrap;
        }

        .quick-actions-hint {
            color: #888;
            font-size: 12px;
            font-weight: 500;
            white-space: nowrap;
        }

        .quick-actions-buttons {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            flex: 1;
        }

        .quick-action-btn {
            background: rgba(100, 149, 237, 0.2);
            border: 1px solid rgba(100, 149, 237, 0.4);
            color: #6495ED;
            padding: 6px 14px;
            border-radius: 16px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
            font-weight: 500;
            white-space: nowrap;
        }

        .quick-action-btn:hover {
            background: rgba(100, 149, 237, 0.4);
            border-color: rgba(100, 149, 237, 0.6);
            transform: translateY(-1px);
        }

        .quick-action-btn:active {
            transform: translateY(0);
        }

        /* PHASE F: Message Reactions */
        .msg-reactions {
            display: flex;
            gap: 4px;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            opacity: 0;
            transition: opacity 0.2s ease;
        }

        .msg:hover .msg-reactions {
            opacity: 1;
        }

        .reaction-btn {
            background: transparent;
            border: none;
            font-size: 16px;
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 4px;
            transition: all 0.2s ease;
            position: relative;
        }

        .reaction-btn:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: scale(1.2);
        }

        .reaction-btn:active {
            transform: scale(1.1);
        }

        .reaction-btn.active {
            background: rgba(100, 149, 237, 0.3);
            transform: scale(1.15);
        }

        /* Phase G: Saved state for reactions (Task 1) */
        .reaction-btn.saved {
            color: #32CD32; /* Bright Green */
            opacity: 1.0;
        }

        /* Input Area - Simple Black */
        #chat-input-area {
            padding: 14px;
            border-top: 1px solid rgba(100, 100, 100, 0.2);
            background: rgba(30, 30, 30, 0.95);
            border-radius: 0 0 12px 12px;
        }
        #chat-input {
            width: 100%;
            background: rgba(40, 40, 40, 0.8);
            border: 1px solid rgba(100, 100, 100, 0.3);
            border-radius: 8px;
            padding: 10px 12px;
            color: #ccc;
            font-size: 13px;
            resize: vertical;
            min-height: 60px;
            max-height: 180px;
            line-height: 1.4;
        }
        #chat-input:focus { outline: none; border-color: #777; }
        #chat-input::placeholder { color: #666; }
        #chat-send {
            margin-top: 10px;
            width: 100%;
            background: rgba(60, 60, 60, 0.8);
            border: 1px solid rgba(100, 100, 100, 0.3);
            color: #ccc;
            padding: 10px 14px;
            border-radius: 8px;
            font-weight: 500;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        #chat-send:hover {
            background: rgba(80, 80, 80, 0.8);
            border-color: #888;
        }
        #chat-send:active { transform: scale(0.98); }

        /* @Mention Autocomplete Dropdown */
        #mention-dropdown {
            position: absolute;
            bottom: 100%;
            left: 0;
            right: 0;
            background: rgba(35, 35, 35, 0.98);
            border: 1px solid rgba(100, 100, 100, 0.4);
            border-radius: 8px;
            max-height: 200px;
            overflow-y: auto;
            display: none;
            z-index: 1000;
            box-shadow: 0 -4px 12px rgba(0,0,0,0.4);
            margin-bottom: 4px;
        }
        #mention-dropdown.visible { display: block; }
        .mention-item {
            padding: 8px 12px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(80, 80, 80, 0.3);
        }
        .mention-item:last-child { border-bottom: none; }
        .mention-item:hover, .mention-item.selected {
            background: rgba(70, 130, 180, 0.3);
        }
        .mention-alias {
            color: #4FC3F7;
            font-weight: 600;
            font-family: monospace;
        }
        .mention-desc {
            color: #888;
            font-size: 11px;
            margin-left: 10px;
        }
        .mention-type {
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
            margin-left: 8px;
        }
        .mention-type.model { background: rgba(76, 175, 80, 0.3); color: #81C784; }
        .mention-type.agent { background: rgba(255, 152, 0, 0.3); color: #FFB74D; }
        .mention-type.local { background: rgba(156, 39, 176, 0.3); color: #BA68C8; }

        .loading { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 16px; color: #555; }

        /* Controls hint */
        #controls-hint {
            position: fixed;
            bottom: 60px;
            left: 20px;
            font-size: 11px;
            color: #555;
            background: rgba(20, 20, 20, 0.8);
            padding: 6px 12px;
            border-radius: 6px;
            z-index: 99;
        }

        /* VETKA Creation Modal */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(8px);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        .modal-overlay.active { display: flex; }
        .modal-box {
            background: rgba(22, 22, 28, 0.98);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 32px;
            width: 400px;
            max-width: 90vw;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        }
        .modal-title {
            font-size: 18px;
            font-weight: 600;
            color: #fff;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .modal-subtitle {
            font-size: 13px;
            color: #888;
            margin-bottom: 24px;
        }
        .modal-input {
            width: 100%;
            background: rgba(30, 30, 35, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 10px;
            padding: 14px 16px;
            color: #fff;
            font-size: 14px;
            margin-bottom: 24px;
        }
        .modal-input:focus {
            outline: none;
            border-color: #8B4513;
            box-shadow: 0 0 0 3px rgba(139, 69, 19, 0.2);
        }
        .modal-input::placeholder { color: #555; }
        .modal-buttons {
            display: flex;
            gap: 12px;
        }
        .modal-btn {
            flex: 1;
            padding: 12px 20px;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s;
        }
        .modal-btn-cancel {
            background: rgba(60, 60, 65, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #aaa;
        }
        .modal-btn-cancel:hover { background: rgba(80, 80, 85, 0.9); color: #fff; }
        .modal-btn-create {
            background: linear-gradient(135deg, #8B4513, #A0522D);
            border: none;
            color: #fff;
        }
        .modal-btn-create:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 16px rgba(139, 69, 19, 0.4);
        }
        .modal-file-count {
            background: rgba(139, 69, 19, 0.2);
            color: #D2691E;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }

        /* Tree Label (billboard at base) */
        .tree-label {
            position: absolute;
            background: rgba(20, 20, 25, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            color: #fff;
            white-space: nowrap;
            pointer-events: none;
            transform: translate(-50%, -50%);
        }
    </style>
</head>
<body>
    <div class="loading" id="loading">Growing tree...</div>
    <div id="canvas-container"></div>

    <!-- Phase 17-O: Global Search Bar (Cmd+K) -->
    <div id="vetka-search-bar" class="vetka-search-bar">
        <input type="text" id="vetka-search-input" placeholder="Search files... (Cmd+K)" autocomplete="off">
        <div id="vetka-search-results" class="search-results"></div>
        <button class="search-close" onclick="VETKASearch.hide()">&times;</button>
        <div class="search-hint">Press Escape to close</div>
    </div>

    <div id="info-panel">
        <h2>VETKA</h2>
        <div id="tree-stats">Loading...</div>
        <div class="sort-controls">
            <button class="sort-btn active" data-sort="default">VETKA Forest</button>
        </div>
        <input type="text" id="search-input" placeholder="Semantic search: visualization, api, config..." oninput="debounceSemanticSearch(this.value)">
        <div id="search-results">
            <span id="search-count">0</span> files found
            <button id="create-branch-btn" onclick="showCreateVetkaModal()">
                Create VETKA from Selection
            </button>
        </div>

        <!-- Scan Folder Panel (in left panel per spec) -->
        <div id="scan-panel" style="margin-top: 16px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.1);">
            <div style="font-size: 12px; color: #888; margin-bottom: 8px;">Scan Folder</div>
            <input type="text" id="scan-path-input" placeholder="Enter path or choose folder..."
                   style="width: 100%; background: rgba(30,30,30,0.9); border: 1px solid rgba(255,255,255,0.1);
                          border-radius: 6px; padding: 8px 10px; color: #fff; font-size: 11px; margin-bottom: 8px;">
            <div style="display: flex; gap: 6px;">
                <button id="btn-choose-folder" onclick="window.location.href='/onboarding'"
                        style="flex: 1; background: rgba(74,107,138,0.3); border: 1px solid rgba(74,107,138,0.5);
                               color: #aaa; padding: 8px; border-radius: 6px; font-size: 11px; cursor: pointer;">
                    Choose Folder
                </button>
                <button id="btn-start-scan" onclick="startScan()"
                        style="flex: 1; background: linear-gradient(135deg, #4A6B8A, #5C7DA0);
                               border: none; color: #fff; padding: 8px; border-radius: 6px;
                               font-size: 11px; font-weight: 600; cursor: pointer;">
                    Scan
                </button>
            </div>
            <div id="scan-progress" style="display: none; margin-top: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span id="scan-progress-text" style="font-size: 11px; color: #888;">Scanning...</span>
                    <button id="btn-cancel-scan" onclick="cancelScan()"
                            style="background: rgba(90,60,60,0.5); border: 1px solid rgba(140,80,80,0.5);
                                   color: #c88; padding: 4px 10px; border-radius: 4px;
                                   font-size: 10px; cursor: pointer;">
                        Cancel
                    </button>
                </div>
                <div style="background: rgba(30,30,30,0.8); height: 4px; border-radius: 2px; margin-top: 6px; overflow: hidden;">
                    <div id="scan-progress-bar" style="width: 0%; height: 100%; background: #4A6B8A; transition: width 0.3s;"></div>
                </div>
            </div>

            <!-- Save Tree Button -->
            <button id="btn-save-tree" class="btn-save" onclick="saveTreeLayout()" title="Save current tree layout to backend">
                💾 Save Tree
            </button>
        </div>
    </div>

    <!-- VETKA Creation Modal (Phase 17: Simplified - uses search query as semantic tag) -->
    <div class="modal-overlay" id="vetka-modal">
        <div class="modal-box">
            <div class="modal-title">
                Create New VETKA
                <span class="modal-file-count" id="modal-file-count">0 files</span>
            </div>
            <div class="modal-subtitle">
                A new knowledge tree with UMAP positioning and semantic clustering.
            </div>
            <input type="text" class="modal-input" id="vetka-name-input" placeholder="Enter VETKA name..." autofocus>
            <div id="modal-search-tag" style="font-size: 12px; color: #4A6B8A; margin: 8px 0 12px 0;">
                <!-- Search query will be shown here as semantic tag -->
            </div>
            <div class="modal-buttons">
                <button class="modal-btn modal-btn-cancel" onclick="hideCreateVetkaModal()">Cancel</button>
                <button class="modal-btn modal-btn-create" onclick="createVetkaFromSelection()">Create VETKA</button>
            </div>
        </div>
    </div>

    <div id="controls">
        <button id="btn-reset">Reset View</button>
        <button id="btn-focus">Focus</button>
        <button id="btn-lod">LOD: Auto</button>
    </div>
    <div id="controls-hint">
        <span>🖱️ Drag=rotate • Alt+Drag=pan • Scroll=zoom • Click=select • DoubleClick=Finder • Shift+Drag=move node</span>
    </div>

    <!-- Phase 17.5: Mode Toggle (Directory ↔ Knowledge) - Replaces blend slider -->
    <div id="mode-toggle-panel">
        <button id="mode-directory-btn" class="mode-btn active" onclick="switchToDirectoryMode()">
            📁 Directory
        </button>
        <button id="mode-knowledge-btn" class="mode-btn" onclick="switchToKnowledgeMode()">
            🧠 Knowledge
        </button>
    </div>

    <!-- Phase 17.3: Export Panel -->
    <div id="export-panel">
        <button onclick="exportToBlender('json')" title="Export as JSON for Blender">
            Export JSON
        </button>
        <button onclick="exportToBlender('obj')" title="Export as OBJ (3D model)">
            Export OBJ
        </button>
    </div>

    <!-- ✅ TASK 3b: Artifact Panel (LEFT SIDE) - Phase 17-M Enhanced -->
    <div id="artifact-panel" class="artifact-panel hidden">
        <!-- Resize handles - same as chat panel -->
        <div class="resize-handle resize-handle-nw" title="Resize NW"></div>
        <div class="resize-handle resize-handle-ne" title="Resize NE"></div>
        <div class="resize-handle resize-handle-sw" title="Resize SW"></div>
        <div class="resize-handle resize-handle-se" title="Resize SE"></div>
        <div class="resize-edge-left" title="Resize left"></div>
        <div class="resize-edge-right" title="Resize right"></div>
        <div class="resize-edge-top" title="Resize top"></div>
        <div class="resize-edge-bottom" title="Resize bottom"></div>

        <!-- Phase 21-B: Simplified header -->
        <div class="artifact-header drag-handle" style="cursor: move;">
            <span id="artifact-filename" style="font-size: 13px; color: #ccc;">No file selected</span>
            <div style="display: flex; gap: 8px;">
                <button class="fullscreen-btn" onclick="toggleArtifactFullScreen()" title="Toggle full screen" style="background: none; border: none; color: #888; cursor: pointer; font-size: 18px; padding: 0;">⛶</button>
                <button class="close-btn" onclick="closeArtifactPanel()" style="background: none; border: none; color: #888; cursor: pointer; font-size: 20px; padding: 0;">✕</button>
            </div>
        </div>

        <!-- Phase 21-B: React Artifact Panel iframe (same origin!) -->
        <iframe
            id="artifact-panel-iframe"
            src="/artifact-panel/"
            style="flex: 1; width: 100%; border: none; background: #1a1a1a;"
        ></iframe>
    </div>

    <div id="chat-panel">
        <!-- Resize handles - 4 углов + 4 края (все стороны) -->
        <div class="resize-handle resize-handle-nw" title="Resize NW"></div>
        <div class="resize-handle resize-handle-ne" title="Resize NE"></div>
        <div class="resize-handle resize-handle-sw" title="Resize SW"></div>
        <div class="resize-handle resize-handle-se" title="Resize SE"></div>
        <div class="resize-edge-left" title="Resize left"></div>
        <div class="resize-edge-right" title="Resize right"></div>
        <div class="resize-edge-top" title="Resize top"></div>
        <div class="resize-edge-bottom" title="Resize bottom"></div>
        <button class="dock-toggle" onclick="toggleChatDock()" title="Toggle: side ↔ bottom">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>
            </svg>
        </button>
        <div id="chat-header">
            <div id="chat-context">
                <span class="selected-node-path" id="selected-node-path">Click on a node...</span>
                <div class="chat-context-display" id="chat-context-display" style="display: none;">
                    <span class="context-icon"></span>
                    <span class="context-path"></span>
                    <span class="context-type"></span>
                </div>
            </div>
        </div>
        <div id="chat-messages"></div>
        <div id="chat-input-area" style="position: relative;">
            <div id="mention-dropdown"></div>
            <textarea id="chat-input" placeholder="Type @ to mention agents or models..." rows="3"></textarea>
            <button id="chat-send">Send</button>
        </div>
        <button class="artifact-trigger" onclick="toggleArtifactFromChat()" title="Open artifact panel">
            &lt;&lt;
        </button>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.160.0/examples/js/controls/OrbitControls.js"></script>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <!-- Phase 22: GSAP for smooth camera animations -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
    <!-- GoldenLayout для multi-window управления -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/golden-layout@2.6.0/dist/css/goldenlayout-base.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/golden-layout@2.6.0/dist/css/themes/goldenlayout-dark-theme.css">
    <script src="https://cdn.jsdelivr.net/npm/golden-layout@2.6.0/dist/goldenlayout.js"></script>

    <!-- VETKA Modules (Phase 17-R2/R3) - v23.6 cache-bust -->
    <script src="/static/js/config.js?v=23.6"></script>
    <script src="/static/js/layout/sugiyama.js?v=23.6"></script>
    <script src="/static/js/ui/chat_panel.js?v=23.6"></script>
    <script src="/static/js/renderer/lod.js?v=23.6"></script>
    <script src="/static/js/modes/knowledge_mode.js?v=23.6"></script>

    <!-- Phase 23: kg-tree-renderer.js DISABLED - functionality moved to vetka-main.js -->
    <!-- It was creating a second Three.js renderer which caused conflicts -->
    <!-- <script src="/static/js/kg-tree-renderer.js"></script> -->

    <!-- Phase 23 REFACTOR: Main application script (contains all rendering logic) -->
    <!-- Cache-busting: v24.4 - Phase 24: Stems follow drag (production) -->
    <script src="/static/js/vetka-main.js?v=24.4"></script>
</body>
</html>
"""
