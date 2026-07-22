import { useState, useEffect, useCallback } from "react";

declare global {
  interface Window {
    __TAURI_INTERNALS__?: Record<string, unknown>;
    __TAURI__?: Record<string, unknown>;
  }
}

async function getWindow() {
  if (typeof window === "undefined") return null;
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    return getCurrentWindow();
  } catch {
    return null;
  }
}

interface Props {
  onShowLogs?: () => void;
}

export default function TitleBar({ onShowLogs }: Props) {
  const [maximized, setMaximized] = useState(false);

  useEffect(() => {
    getWindow().then(async (w) => {
      if (!w) return;
      setMaximized(await w.isMaximized());
      const unlisten = await w.onResized(() => {
        w.isMaximized().then(setMaximized);
      });
      return () => { unlisten(); };
    });
  }, []);

  const handleMinimize = useCallback(async () => {
    const w = await getWindow();
    w?.minimize();
  }, []);

  const handleMaximize = useCallback(async () => {
    const w = await getWindow();
    if (!w) return;
    await w.toggleMaximize();
    setMaximized(await w.isMaximized());
  }, []);

  const handleClose = useCallback(async () => {
    const w = await getWindow();
    w?.close();
  }, []);

  return (
    <div className="titlebar" data-tauri-drag-region>
      <div className="titlebar-left" data-tauri-drag-region>
        <svg className="titlebar-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" data-tauri-drag-region>
          <polyline points="16 18 22 12 16 6" />
          <polyline points="8 6 2 12 8 18" />
        </svg>
        <span className="titlebar-label" data-tauri-drag-region>AIOS</span>
      </div>
      <div className="titlebar-center" data-tauri-drag-region />
      <div style={{ display: "flex", alignItems: "center", gap: 2, paddingRight: 4 }}>
        <button
          onClick={onShowLogs}
          title="Open Logs (Ctrl+Shift+L)"
          style={{
            background: "none", border: "none", color: "#66666e", cursor: "pointer",
            display: "flex", padding: "4px 6px", borderRadius: 4, fontSize: 11,
            fontFamily: "inherit",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "#ccc")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "#66666e")}
        >
          Logs
        </button>
      </div>
      <div className="titlebar-actions">
        <button className="titlebar-btn" onClick={handleMinimize} title="Minimize">
          <svg width="12" height="12" viewBox="0 0 12 12"><rect y="5" width="12" height="1.5" fill="currentColor" /></svg>
        </button>
        <button className="titlebar-btn" onClick={handleMaximize} title={maximized ? "Restore" : "Maximize"}>
          {maximized ? (
            <svg width="12" height="12" viewBox="0 0 12 12">
              <rect x="2.5" y="0.5" width="9" height="9" rx="1" fill="none" stroke="currentColor" strokeWidth="1" />
              <rect x="0.5" y="2.5" width="9" height="9" rx="1" fill="#121214" stroke="currentColor" strokeWidth="1" />
            </svg>
          ) : (
            <svg width="12" height="12" viewBox="0 0 12 12">
              <rect x="0.5" y="0.5" width="11" height="11" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1" />
            </svg>
          )}
        </button>
        <button className="titlebar-btn titlebar-btn-close" onClick={handleClose} title="Close">
          <svg width="12" height="12" viewBox="0 0 12 12">
            <line x1="1" y1="1" x2="11" y2="11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="11" y1="1" x2="1" y2="11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>
      </div>
    </div>
  );
}
