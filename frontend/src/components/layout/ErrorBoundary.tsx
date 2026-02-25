import { Component, type ReactNode, type ErrorInfo } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * ErrorBoundary — catches unhandled render errors in the subtree.
 *
 * Wraps individual screens in AppShell so an error in one screen does not
 * crash the entire application.  Shows "Something went wrong" with a Reload
 * button that calls `window.location.reload()`.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // In production, forward to an error reporting service here.
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  private handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          data-testid="error-boundary-fallback"
          className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center"
        >
          <p className="text-base font-medium text-red-600">
            Something went wrong
          </p>
          {this.state.error && (
            <p className="text-sm text-gray-500">{this.state.error.message}</p>
          )}
          <button
            type="button"
            onClick={this.handleReload}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white
                       hover:bg-blue-700"
          >
            Reload
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
