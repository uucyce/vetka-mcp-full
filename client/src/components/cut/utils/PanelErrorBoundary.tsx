/**
 * MARKER_GAMMA-APP1: Per-panel error boundary.
 * One panel crash doesn't kill the entire UI.
 * Fallback shows error message + reload button.
 */
import { Component, type ReactNode } from 'react';

interface Props {
  panelName?: string;
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class PanelErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: { componentStack?: string | null }) {
    console.error(`[CUT Panel Error] ${this.props.panelName || 'Unknown'}:`, error, info.componentStack);
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          background: '#0a0a0a',
          color: '#555',
          fontFamily: 'system-ui, -apple-system, sans-serif',
          fontSize: 10,
          gap: 8,
          padding: 16,
        }}>
          <span style={{ fontSize: 11, color: '#888' }}>
            Panel error: {this.props.panelName || 'Unknown'}
          </span>
          <span style={{ fontSize: 9, color: '#444', maxWidth: 200, textAlign: 'center', wordBreak: 'break-word' }}>
            {this.state.error?.message || 'Unknown error'}
          </span>
          <button
            onClick={this.handleReload}
            style={{
              background: '#1a1a1a',
              border: '1px solid #333',
              borderRadius: 4,
              color: '#ccc',
              fontSize: 10,
              padding: '4px 12px',
              cursor: 'pointer',
              marginTop: 4,
            }}
          >
            Reload Panel
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
