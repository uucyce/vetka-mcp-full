/**
 * MYCELIUM standalone entry point.
 * MARKER_175.1: Dedicated React root for MCC — bypasses App.tsx entirely.
 * No static Tauri imports, no Three.js, no 3D tree.
 *
 * @status active
 * @phase 175
 * @depends react, react-dom, ./MyceliumStandalone, ./styles
 * @used_by mycelium.html
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import MyceliumStandalone from './MyceliumStandalone';
import './styles/voice.css';
import './styles/tokens.css';
import { initBrowserAgentBridge } from './utils/browserAgentBridge';

// MARKER_175.1: Browser agent bridge for Claude in Chrome etc.
initBrowserAgentBridge();

/**
 * MARKER_175.1: Error boundary for standalone MCC.
 * Same pattern as main.tsx but with MCC-specific messaging.
 */
type ErrorBoundaryState = {
  hasError: boolean;
  message: string;
  stack?: string;
};

class MCCErrorBoundary extends React.Component<React.PropsWithChildren, ErrorBoundaryState> {
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
    console.error('[MYCELIUM_RUNTIME_ERROR]', error, info);
    try {
      localStorage.setItem('mycelium_last_runtime_error', stack || error?.message || 'unknown');
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
        <h2 style={{ margin: '0 0 8px 0', fontSize: 18 }}>MYCELIUM Runtime Error</h2>
        <div style={{ marginBottom: 8, color: '#ff9b9b' }}>{this.state.message}</div>
        <div style={{ marginBottom: 10, color: '#999', fontSize: 12 }}>
          Error saved in localStorage key:
          <code style={{ marginLeft: 6, color: '#ccc' }}>mycelium_last_runtime_error</code>
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
    <MCCErrorBoundary>
      <MyceliumStandalone />
    </MCCErrorBoundary>
  </React.StrictMode>
);
