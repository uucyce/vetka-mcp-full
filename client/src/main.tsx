/**
 * Application entry point. Initializes React and browser agent bridge.
 *
 * @status active
 * @phase 96
 * @depends react, react-dom, ./App, ./styles/voice.css, ./utils/browserAgentBridge
 * @used_by index.html
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/voice.css'; // Phase 60.5: Voice animations
import { initBrowserAgentBridge } from './utils/browserAgentBridge'; // Phase 80: Browser Agent API

// Phase 80: Initialize browser agent bridge for Claude in Chrome etc.
initBrowserAgentBridge();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
