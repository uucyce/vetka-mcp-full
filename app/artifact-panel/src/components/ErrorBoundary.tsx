import { Component, type ReactNode } from 'react';
import { AlertCircle, RefreshCcw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, info: { componentStack: string }) => void;
  name?: string; // For debugging
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error Boundary для catch runtime errors в компонентах
 * Используется как глобально, так и per-viewer
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: { componentStack: string }) {
    console.error(`[ErrorBoundary${this.props.name ? `: ${this.props.name}` : ''}]`, error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="h-full flex flex-col items-center justify-center bg-vetka-bg p-4">
            <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
            <p className="text-vetka-text mb-2 font-medium">Something went wrong</p>
            <p className="text-vetka-muted text-sm mb-6 max-w-md text-center">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <button
              onClick={this.handleReset}
              className="flex items-center gap-2 px-4 py-2 bg-vetka-accent hover:bg-blue-600 
                         text-white rounded transition-colors"
            >
              <RefreshCcw size={16} />
              Try again
            </button>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
