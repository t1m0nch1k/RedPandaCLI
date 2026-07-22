import { useState, useEffect } from "react";

interface CalendarEvent {
  id: number;
  title: string;
  description: string;
  start_time: string;
  end_time: string;
  category: string;
}

interface Props {
  sendRequest: (method: string, params?: Record<string, unknown>) => Promise<any>;
}

export default function CalendarPanel({ sendRequest }: Props) {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [startTime, setStartTime] = useState("");

  const loadEvents = async () => {
    setLoading(true);
    try {
      // Load upcoming 7 days
      const now = new Date();
      const end = new Date();
      end.setDate(now.getDate() + 7);
      
      const res = await sendRequest("calendar.get", { 
        date_from: now.toISOString(), 
        date_to: end.toISOString() 
      });
      if (res && res.results) {
        setEvents(res.results);
      }
    } catch (err) {
      console.error("Failed to load events", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !startTime) return;
    
    try {
      const d = new Date(startTime);
      await sendRequest("calendar.add", { 
        title, 
        description,
        start_time: d.toISOString()
      });
      setTitle("");
      setDescription("");
      setStartTime("");
      loadEvents();
    } catch (err) {
      console.error("Failed to add event", err);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await sendRequest("calendar.delete", { id });
      loadEvents();
    } catch (err) {
      console.error("Failed to delete event", err);
    }
  };

  return (
    <div style={{ padding: 20, color: "#e0e0e0", height: "100%", display: "flex", flexDirection: "column", boxSizing: "border-box" }}>
      <h2 style={{ margin: "0 0 20px 0", fontSize: 18, fontWeight: 500 }}>Calendar & Events</h2>

      <form onSubmit={handleAdd} style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20, background: "rgba(255,255,255,0.03)", padding: 15, borderRadius: 8 }}>
        <input
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="Event Title..."
          style={{ padding: "8px 12px", borderRadius: 6, border: "1px solid #333", background: "#1a1a2e", color: "#fff", outline: "none" }}
          required
        />
        <input
          type="datetime-local"
          value={startTime}
          onChange={e => setStartTime(e.target.value)}
          style={{ padding: "8px 12px", borderRadius: 6, border: "1px solid #333", background: "#1a1a2e", color: "#fff", outline: "none" }}
          required
        />
        <input
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="Description (optional)..."
          style={{ padding: "8px 12px", borderRadius: 6, border: "1px solid #333", background: "#1a1a2e", color: "#fff", outline: "none" }}
        />
        <button type="submit" style={{ padding: "8px 16px", borderRadius: 6, background: "#8b5cf6", color: "#fff", border: "none", cursor: "pointer", alignSelf: "flex-start" }}>
          Schedule Event
        </button>
      </form>

      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 10, paddingRight: 10 }}>
        <h3 style={{ margin: "0 0 10px 0", fontSize: 14, color: "#aaa" }}>Upcoming Events (7 days)</h3>
        {loading ? (
          <div style={{ color: "#888", textAlign: "center", marginTop: 20 }}>Loading...</div>
        ) : events.length === 0 ? (
          <div style={{ color: "#888", textAlign: "center", marginTop: 20 }}>No upcoming events.</div>
        ) : (
          events.map(ev => (
            <div key={ev.id} style={{ background: "rgba(255,255,255,0.03)", padding: 12, borderRadius: 8, border: "1px solid rgba(255,255,255,0.05)", display: "flex", gap: 10 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, fontWeight: 500, color: "#fff" }}>{ev.title}</div>
                <div style={{ fontSize: 13, color: "#aaa", marginTop: 4 }}>{new Date(ev.start_time).toLocaleString()}</div>
                {ev.description && <div style={{ fontSize: 13, marginTop: 8, color: "#ccc" }}>{ev.description}</div>}
              </div>
              <button 
                onClick={() => handleDelete(ev.id)}
                style={{ background: "transparent", border: "none", color: "#ef4444", cursor: "pointer", padding: "4px 8px", borderRadius: 4, alignSelf: "flex-start" }}
                onMouseEnter={e => (e.currentTarget.style.background = "rgba(239, 68, 68, 0.1)")}
                onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
              >
                Cancel
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
