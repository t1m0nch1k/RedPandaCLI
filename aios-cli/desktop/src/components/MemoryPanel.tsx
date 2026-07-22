import { useState, useEffect } from "react";

interface MemoryItem {
  id: number;
  created_at: string;
  category: string;
  content: string;
  metadata: string;
  importance: number;
}

interface Props {
  sendRequest: (method: string, params?: Record<string, unknown>) => Promise<any>;
}

export default function MemoryPanel({ sendRequest }: Props) {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [newContent, setNewContent] = useState("");

  const loadMemories = async (searchQuery: string = "") => {
    setLoading(true);
    try {
      const method = searchQuery ? "memory.search" : "memory.list";
      const params = searchQuery ? { query: searchQuery } : {};
      const res = await sendRequest(method, params);
      if (res && res.results) {
        setMemories(res.results);
      }
    } catch (err) {
      console.error("Failed to load memories", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMemories();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadMemories(query);
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;
    try {
      await sendRequest("memory.store", { content: newContent });
      setNewContent("");
      loadMemories(query);
    } catch (err) {
      console.error("Failed to add memory", err);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await sendRequest("memory.delete", { id });
      loadMemories(query);
    } catch (err) {
      console.error("Failed to delete memory", err);
    }
  };

  return (
    <div style={{ padding: 20, color: "#e0e0e0", height: "100%", display: "flex", flexDirection: "column", boxSizing: "border-box" }}>
      <h2 style={{ margin: "0 0 20px 0", fontSize: 18, fontWeight: 500 }}>Long-Term Memory</h2>
      
      <div style={{ display: "flex", gap: 10, marginBottom: 20 }}>
        <form onSubmit={handleSearch} style={{ flex: 1, display: "flex", gap: 10 }}>
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search memories..."
            style={{
              flex: 1, padding: "8px 12px", borderRadius: 6, border: "1px solid #333",
              background: "#1a1a2e", color: "#fff", outline: "none"
            }}
          />
          <button type="submit" style={{ padding: "8px 16px", borderRadius: 6, background: "#3b82f6", color: "#fff", border: "none", cursor: "pointer" }}>
            Search
          </button>
        </form>
      </div>

      <form onSubmit={handleAdd} style={{ display: "flex", gap: 10, marginBottom: 20 }}>
        <input
          value={newContent}
          onChange={e => setNewContent(e.target.value)}
          placeholder="Remember that..."
          style={{
            flex: 1, padding: "8px 12px", borderRadius: 6, border: "1px solid #333",
            background: "#1a1a2e", color: "#fff", outline: "none"
          }}
        />
        <button type="submit" style={{ padding: "8px 16px", borderRadius: 6, background: "#10b981", color: "#fff", border: "none", cursor: "pointer" }}>
          Add Fact
        </button>
      </form>

      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 10, paddingRight: 10 }}>
        {loading ? (
          <div style={{ color: "#888", textAlign: "center", marginTop: 20 }}>Loading...</div>
        ) : memories.length === 0 ? (
          <div style={{ color: "#888", textAlign: "center", marginTop: 20 }}>No memories found.</div>
        ) : (
          memories.map(m => (
            <div key={m.id} style={{ background: "rgba(255,255,255,0.03)", padding: 12, borderRadius: 8, border: "1px solid rgba(255,255,255,0.05)", display: "flex", gap: 10 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, lineHeight: 1.5 }}>{m.content}</div>
                <div style={{ display: "flex", gap: 10, marginTop: 8, fontSize: 11, color: "#888" }}>
                  <span>{new Date(m.created_at).toLocaleString()}</span>
                  <span>Cat: {m.category}</span>
                  <span>Imp: {m.importance}</span>
                </div>
              </div>
              <button 
                onClick={() => handleDelete(m.id)}
                style={{ background: "transparent", border: "none", color: "#ef4444", cursor: "pointer", padding: "4px 8px", borderRadius: 4, alignSelf: "flex-start" }}
                onMouseEnter={e => (e.currentTarget.style.background = "rgba(239, 68, 68, 0.1)")}
                onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
              >
                Delete
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
