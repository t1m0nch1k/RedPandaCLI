import { useState, useEffect } from "react";

interface Timer {
  id: string;
  label: string;
  type: "timer" | "stopwatch" | "alarm";
  state: "idle" | "running" | "paused" | "finished";
  remaining_sec: number;
  elapsed_sec: number;
}

interface Props {
  sendRequest: (method: string, params?: Record<string, unknown>) => Promise<any>;
}

export default function TimerPanel({ sendRequest }: Props) {
  const [timers, setTimers] = useState<Timer[]>([]);
  const [label, setLabel] = useState("");
  const [duration, setDuration] = useState("60");

  const loadTimers = async () => {
    try {
      const res = await sendRequest("timer.list");
      if (res && res.results) {
        setTimers(res.results);
      }
    } catch (err) {
      console.error("Failed to load timers", err);
    }
  };

  useEffect(() => {
    loadTimers();
    const interval = setInterval(loadTimers, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleAddTimer = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await sendRequest("timer.create", { label: label || "Timer", duration_sec: parseInt(duration) || 60 });
      setLabel("");
      setDuration("60");
      loadTimers();
    } catch (err) {
      console.error("Failed to add timer", err);
    }
  };

  const handleAddStopwatch = async () => {
    try {
      await sendRequest("timer.stopwatch", { label: label || "Stopwatch" });
      setLabel("");
      loadTimers();
    } catch (err) {
      console.error("Failed to add stopwatch", err);
    }
  };

  const handleAction = async (id: string, action: string) => {
    try {
      await sendRequest("timer.action", { id, action });
      loadTimers();
    } catch (err) {
      console.error(`Failed to ${action} timer`, err);
    }
  };

  const formatTime = (sec: number) => {
    const s = Math.floor(sec);
    const m = Math.floor(s / 60);
    const h = Math.floor(m / 60);
    const mStr = (m % 60).toString().padStart(2, "0");
    const sStr = (s % 60).toString().padStart(2, "0");
    if (h > 0) return `${h}:${mStr}:${sStr}`;
    return `${mStr}:${sStr}`;
  };

  return (
    <div style={{ padding: 20, color: "#e0e0e0", height: "100%", display: "flex", flexDirection: "column", boxSizing: "border-box" }}>
      <h2 style={{ margin: "0 0 20px 0", fontSize: 18, fontWeight: 500 }}>Clocks & Timers</h2>

      <div style={{ display: "flex", gap: 10, marginBottom: 20, background: "rgba(255,255,255,0.03)", padding: 15, borderRadius: 8 }}>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10 }}>
          <input
            value={label}
            onChange={e => setLabel(e.target.value)}
            placeholder="Label (e.g. Boil Eggs)"
            style={{ padding: "8px 12px", borderRadius: 6, border: "1px solid #333", background: "#1a1a2e", color: "#fff", outline: "none" }}
          />
          <div style={{ display: "flex", gap: 10 }}>
            <input
              type="number"
              value={duration}
              onChange={e => setDuration(e.target.value)}
              placeholder="Seconds"
              style={{ flex: 1, padding: "8px 12px", borderRadius: 6, border: "1px solid #333", background: "#1a1a2e", color: "#fff", outline: "none" }}
            />
            <button onClick={handleAddTimer} style={{ padding: "8px 16px", borderRadius: 6, background: "#8b5cf6", color: "#fff", border: "none", cursor: "pointer" }}>
              + Timer
            </button>
            <button onClick={handleAddStopwatch} style={{ padding: "8px 16px", borderRadius: 6, background: "#3b82f6", color: "#fff", border: "none", cursor: "pointer" }}>
              + Stopwatch
            </button>
          </div>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexWrap: "wrap", gap: 15, alignContent: "flex-start" }}>
        {timers.length === 0 ? (
          <div style={{ color: "#888", width: "100%", textAlign: "center", marginTop: 20 }}>No active timers.</div>
        ) : (
          timers.map(t => (
            <div key={t.id} style={{ 
              background: t.state === "finished" ? "rgba(239, 68, 68, 0.1)" : "rgba(255,255,255,0.03)", 
              padding: 15, 
              borderRadius: 8, 
              border: `1px solid ${t.state === "finished" ? "rgba(239, 68, 68, 0.3)" : "rgba(255,255,255,0.05)"}`, 
              width: "200px",
              display: "flex", flexDirection: "column", gap: 10
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 13, color: "#aaa", textTransform: "uppercase" }}>{t.type}</span>
                <span style={{ fontSize: 11, padding: "2px 6px", borderRadius: 4, background: "rgba(255,255,255,0.1)" }}>{t.state}</span>
              </div>
              <div style={{ fontSize: 16, fontWeight: 500 }}>{t.label}</div>
              
              <div style={{ fontSize: 32, fontWeight: 300, textAlign: "center", margin: "10px 0", fontFamily: "monospace" }}>
                {t.type === "stopwatch" ? formatTime(t.elapsed_sec) : formatTime(t.remaining_sec)}
              </div>

              <div style={{ display: "flex", gap: 5, justifyContent: "center" }}>
                {t.state === "running" && (
                  <button onClick={() => handleAction(t.id, "pause")} style={{ padding: "4px 8px", borderRadius: 4, background: "#fbbf24", color: "#000", border: "none", cursor: "pointer", fontSize: 12 }}>Pause</button>
                )}
                {t.state === "paused" && (
                  <button onClick={() => handleAction(t.id, "resume")} style={{ padding: "4px 8px", borderRadius: 4, background: "#10b981", color: "#fff", border: "none", cursor: "pointer", fontSize: 12 }}>Resume</button>
                )}
                {t.state !== "finished" && (
                  <button onClick={() => handleAction(t.id, "stop")} style={{ padding: "4px 8px", borderRadius: 4, background: "#6b7280", color: "#fff", border: "none", cursor: "pointer", fontSize: 12 }}>Stop</button>
                )}
                <button onClick={() => handleAction(t.id, "delete")} style={{ padding: "4px 8px", borderRadius: 4, background: "#ef4444", color: "#fff", border: "none", cursor: "pointer", fontSize: 12 }}>Delete</button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
