import { useState, useEffect, useRef, useCallback } from "react";
import { getLogs, subscribe, clearLogs, getAllText, type LogEntry } from "../lib/logStore";

const LEVEL_COLORS: Record<string, string> = {
  error: "#f44",
  warn: "#fb0",
  info: "#48f",
  debug: "#888",
  log: "#aaa",
};

const LEVEL_BG: Record<string, string> = {
  error: "rgba(255,68,68,0.08)",
  warn: "rgba(255,187,0,0.08)",
};

export default function LogPanel({ onClose }: { onClose: () => void }) {
  const [logs, setLogs] = useState<LogEntry[]>(getLogs);
  const [filter, setFilter] = useState<"all" | "frontend" | "backend">("all");
  const [levelFilter, setLevelFilter] = useState<string>("all");
  const [autoScroll, setAutoScroll] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevLenRef = useRef(logs.length);

  useEffect(() => subscribe(() => setLogs(getLogs())), []);

  useEffect(() => {
    if (autoScroll && logs.length > prevLenRef.current) {
      scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
    }
    prevLenRef.current = logs.length;
  }, [logs, autoScroll]);

  const filtered = logs.filter((e) => {
    if (filter !== "all" && e.source !== filter) return false;
    if (levelFilter !== "all" && e.level !== levelFilter) return false;
    return true;
  });

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(getAllText()).catch(() => {});
  }, []);

  const handleDownload = useCallback(() => {
    const blob = new Blob([getAllText()], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `aios-logs-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 9999,
      background: "#0b0b0e", color: "#e3e3e6",
      display: "flex", flexDirection: "column",
      fontFamily: "'Cascadia Code', 'Fira Code', 'Consolas', monospace",
      fontSize: 12,
    }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "8px 12px", borderBottom: "1px solid #2a2a2e",
        flexShrink: 0,
      }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#888" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
        <span style={{ fontWeight: 600, fontSize: 13 }}>Logs</span>
        <span style={{ color: "#666", fontSize: 11 }}>({logs.length} entries)</span>
        <div style={{ flex: 1 }} />
        <select value={filter} onChange={(e) => setFilter(e.target.value as typeof filter)} style={selectStyle()}>
          <option value="all">All sources</option>
          <option value="frontend">Frontend</option>
          <option value="backend">Backend</option>
        </select>
        <select value={levelFilter} onChange={(e) => setLevelFilter(e.target.value)} style={selectStyle()}>
          <option value="all">All levels</option>
          <option value="error">Errors</option>
          <option value="warn">Warnings</option>
          <option value="info">Info</option>
          <option value="log">Log</option>
          <option value="debug">Debug</option>
        </select>
        <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: "#888", cursor: "pointer" }}>
          <input type="checkbox" checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} />
          Auto-scroll
        </label>
        <button onClick={clearLogs} style={btnStyle()} title="Clear">Clear</button>
        <button onClick={handleCopy} style={btnStyle()} title="Copy all">Copy</button>
        <button onClick={handleDownload} style={btnStyle()} title="Download as .txt">Save</button>
        <button onClick={onClose} style={{ ...btnStyle(), color: "#f88" }} title="Close (Esc)">✕</button>
      </div>

      {/* Log entries */}
      <div ref={scrollRef} style={{
        flex: 1, overflow: "auto", padding: 0,
      }}>
        {filtered.length === 0 ? (
          <div style={{ padding: 32, textAlign: "center", color: "#555", fontSize: 13 }}>
            No log entries match the current filters.
          </div>
        ) : (
          filtered.map((e) => (
            <div key={e.id} style={{
              padding: "2px 12px", lineHeight: 1.5,
              borderBottom: "1px solid rgba(255,255,255,0.02)",
              color: e.source === "backend" ? "#8cf" : "#ccc",
              background: LEVEL_BG[e.level] || "transparent",
              whiteSpace: "pre-wrap", wordBreak: "break-all",
            }}>
              <span style={{ color: "#555", marginRight: 8 }}>
                {e.timestamp.slice(11, 23)}
              </span>
              <span style={{
                display: "inline-block", width: 48,
                color: LEVEL_COLORS[e.level] || "#aaa",
                fontWeight: e.level === "error" ? 700 : 400,
              }}>
                {e.level.toUpperCase()}
              </span>
              <span style={{
                display: "inline-block", width: 60,
                color: e.source === "backend" ? "#48f" : "#888",
                fontSize: 10,
              }}>
                [{e.source}]
              </span>
              <span>{e.message}</span>
            </div>
          ))
        )}
      </div>

      {/* Footer hint */}
      <div style={{
        padding: "4px 12px", borderTop: "1px solid #2a2a2e",
        fontSize: 10, color: "#555", flexShrink: 0,
        display: "flex", justifyContent: "space-between",
      }}>
        <span>Press Esc to close</span>
        <span>{filtered.length} shown / {logs.length} total</span>
      </div>
    </div>
  );
}

function selectStyle(): React.CSSProperties {
  return {
    background: "#1e1e22", color: "#ccc", border: "1px solid #333",
    borderRadius: 4, padding: "4px 6px", fontSize: 11, outline: "none",
    cursor: "pointer",
  };
}

function btnStyle(): React.CSSProperties {
  return {
    background: "#2a2a2e", color: "#ccc", border: "1px solid #333",
    borderRadius: 4, padding: "4px 10px", fontSize: 11, cursor: "pointer",
    fontFamily: "inherit",
  };
}
