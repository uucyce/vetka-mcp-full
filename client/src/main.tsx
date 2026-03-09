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
import ArtifactMediaStandalone from './ArtifactMediaStandalone';
import ArtifactStandalone from './ArtifactStandalone';
import CutStandalone from './CutStandalone';
import WebShellStandalone from './WebShellStandalone';
import './styles/voice.css'; // Phase 60.5: Voice animations
import './styles/tokens.css'; // Phase 151.17: Nolan design tokens
import { initBrowserAgentBridge } from './utils/browserAgentBridge'; // Phase 80: Browser Agent API

// Phase 80: Initialize browser agent bridge for Claude in Chrome etc.
initBrowserAgentBridge();

// MARKER_134.FIX_ROUTER: Pathname-based routing (no react-router needed)
const pathname = window.location.pathname;

function Root() {
  if (pathname === '/mycelium') {
    return <MyceliumStandalone />;
  }
  if (pathname === '/web-shell') {
    return <WebShellStandalone />;
  }
  if (pathname === '/artifact-media') {
    return <ArtifactMediaStandalone />;
  }
  if (pathname === '/artifact-window') {
    return <ArtifactStandalone />;
  }
  if (pathname === '/cut') {
    return <CutStandalone />;
  }
  return <App />;
}

type ErrorBoundaryState = {
  hasError: boolean;
  message: string;
  stack?: string;
};

class AppErrorBoundary extends React.Component<React.PropsWithChildren, ErrorBoundaryState> {
  constructor(props: React.PropsWithChildren) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      message: error?.message || 'Unknown runtime error',
      stack: error?.stack,
    };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    const stack = [error?.stack, info?.componentStack].filter(Boolean).join('\n\n');
    // Keep logs for terminal/dev runs and persist for Tauri sessions without DevTools.
    console.error('[MCC_RUNTIME_ERROR]', error, info);
    try {
      localStorage.setItem('vetka_last_runtime_error', stack || error?.message || 'unknown');
    } catch {
      // ignore storage failures
    }
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div
        style={{
          height: '100vh',
          width: '100vw',
          background: '#0b0b0b',
          color: '#e6e6e6',
          fontFamily: 'monospace',
          padding: 16,
          boxSizing: 'border-box',
          overflow: 'auto',
        }}
      >
        <h2 style={{ margin: '0 0 8px 0', fontSize: 18 }}>MCC Runtime Error</h2>
        <div style={{ marginBottom: 8, color: '#ff9b9b' }}>{this.state.message}</div>
        <div style={{ marginBottom: 10, color: '#999', fontSize: 12 }}>
          Send this screen to Codex. Error is also saved in localStorage key:
          <code style={{ marginLeft: 6, color: '#ccc' }}>vetka_last_runtime_error</code>
        </div>
        <pre
          style={{
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            fontSize: 12,
            lineHeight: 1.45,
            margin: 0,
          }}
        >
          {this.state.stack || 'No stack available'}
        </pre>
      </div>
    );
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <Root />
    </AppErrorBoundary>
  </React.StrictMode>
);
