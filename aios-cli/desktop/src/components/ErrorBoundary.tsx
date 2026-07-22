import { Component, type ReactNode } from "react";
import { pushLog } from "../lib/logStore";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: { componentStack?: string }) {
    pushLog("frontend", "error", `React Error: ${error.message}\n${error.stack || ""}\nComponent Stack: ${info.componentStack || ""}`);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: 32, background: "#0b0b0e", color: "#e3e3e6",
          height: "100dvh", display: "flex", flexDirection: "column",
          fontFamily: "system-ui, sans-serif", justifyContent: "center", alignItems: "center",
        }}>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#f44" strokeWidth="1.5" style={{ marginBottom: 16 }}>
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <h2 style={{ margin: "0 0 8px", fontSize: 18 }}>Crashed</h2>
          <pre style={{ color: "#f88", fontSize: 13, maxWidth: 600, textAlign: "center", marginBottom: 16, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
            {this.state.error?.message}
          </pre>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={this.handleReset} style={{
              padding: "8px 20px", background: "#4361ee", color: "#fff",
              border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13,
            }}>
              Try Again
            </button>
            <button onClick={() => {
              const logs = JSON.stringify({ error: this.state.error?.message, stack: this.state.error?.stack });
              navigator.clipboard.writeText(logs).catch(() => {});
            }} style={{
              padding: "8px 20px", background: "#2a2a2e", color: "#ccc",
              border: "1px solid #333", borderRadius: 6, cursor: "pointer", fontSize: 13,
            }}>
              Copy Error
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
