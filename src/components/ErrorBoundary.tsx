import { Component, ErrorInfo, ReactNode } from "react";

/** A render error shows what happened instead of an empty screen. */
export default class ErrorBoundary extends Component<{ children: ReactNode; label?: string }, { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // eslint-disable-next-line no-console
    console.error(`Emu Hub${this.props.label ? ` (${this.props.label})` : ""} crashed:`, error, info.componentStack);
  }

  render(): ReactNode {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <div className="ed-error-screen">
        <h2>Emu Hub hit an error</h2>
        <pre>{String(error?.message || error)}</pre>
      </div>
    );
  }
}
