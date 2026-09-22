import { Component, type ReactNode } from "react";

/** Rendering failures in optional news content must not unmount trading providers. */
export class NewsErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className="px-6 py-16 text-center" role="alert">
        <h1 className="text-lg text-white/80">News could not be displayed</h1>
        <p className="mt-2 text-sm text-white/50">Please try again shortly.</p>
        <button type="button" onClick={() => this.setState({ failed: false })}
          className="mt-4 rounded-md border border-white/15 px-3 py-2 text-sm text-white/70 hover:bg-white/5 cursor-pointer">
          Try again
        </button>
      </main>
    );
  }
}
