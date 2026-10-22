import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
  onError?: (error: Error, info: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    this.props.onError?.(error, info);
    console.error('[ErrorBoundary]', error, info);
  }

  reset = () => this.setState({ hasError: false, error: null });

  render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.reset);
      }
      return (
        <div className="flex flex-col items-center justify-center min-h-[300px] gap-4 p-8">
          <div className="text-4xl">⚠️</div>
          <p className="text-[var(--color-accent-rose)] font-mono text-sm">
            {this.state.error.message}
          </p>
          <button
            onClick={this.reset}
            className="px-4 py-2 rounded-lg border border-[var(--color-border-strong)]
                       text-sm text-[var(--color-accent-cyan)] hover:bg-[var(--color-surface-2)]
                       transition-colors duration-[var(--transition-fast)]"
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
