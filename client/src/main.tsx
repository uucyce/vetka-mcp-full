/**
 * Application entry point. Initializes React and browser agent bridge.
 * MARKER_134.FIX_ROUTER: Uses pathname check instead of react-router
 *
 * @status active
 * @phase 134
 * @depends react, react-dom, ./App, ./MyceliumStandalone, ./styles/voice.css, ./utils/browserAgentBridge
 * @used_by index.html
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import MyceliumStandalone from './MyceliumStandalone';
import './styles/voice.css'; // Phase 60.5: Voice animations
import { initBrowserAgentBridge } from './utils/browserAgentBridge'; // Phase 80: Browser Agent API

// Phase 80: Initialize browser agent bridge for Claude in Chrome etc.
initBrowserAgentBridge();

// MARKER_134.FIX_ROUTER: Pathname-based routing (no react-router needed)
const pathname = window.location.pathname;

function Root() {
  if (pathname === '/mycelium') {
    return <MyceliumStandalone />;
  }
  return <App />;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);
