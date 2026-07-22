import { useMemo } from "react";
import type { ToolMetadata } from "../types";

interface Props {
  tools: ToolMetadata[];
}

const CATEGORY_LABELS: Record<string, string> = {
  system: "System",
  desktop: "Desktop",
  browser: "Browser",
  terminal: "Terminal",
  file: "File",
  clipboard: "Clipboard",
  screen: "Screen",
  window: "Window",
  misc: "Other",
};

const CATEGORY_COLORS: Record<string, string> = {
  system: "#a78bfa",
  desktop: "#60a5fa",
  browser: "#34d399",
  terminal: "#f472b6",
  file: "#fbbf24",
  clipboard: "#fb923c",
  screen: "#22d3ee",
  window: "#818cf8",
  misc: "#9ca3af",
};

export default function ToolListPanel({ tools }: Props) {
  const grouped = useMemo(() => {
    const map = new Map<string, ToolMetadata[]>();
    for (const t of tools) {
      const cat = t.category || "misc";
      if (!map.has(cat)) map.set(cat, []);
      map.get(cat)!.push(t);
    }
    return Array.from(map.entries()).sort();
  }, [tools]);

  return (
    <div style={{ padding: "8px 0" }}>
      {grouped.map(([category, items]) => (
        <div key={category} style={{ marginBottom: 12 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "4px 12px",
              fontSize: 11,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.5px",
              color: CATEGORY_COLORS[category] || "#999",
            }}
          >
            <span style={{ fontSize: 8 }}>●</span>
            {CATEGORY_LABELS[category] || category}
            <span style={{ color: "#555", marginLeft: 4 }}>{items.length}</span>
          </div>
          {items.map((tool) => (
            <div
              key={tool.name}
              style={{
                padding: "6px 12px 6px 24px",
                fontSize: 13,
                cursor: "default",
                borderRadius: 4,
                margin: "1px 4px",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.background = "#2a2a3e";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.background = "transparent";
              }}
              title={tool.description}
            >
              <div style={{ color: "#e0e0e0", display: "flex", alignItems: "center", gap: 6 }}>
                {tool.name}
                {tool.risky && (
                  <span
                    style={{
                      fontSize: 9,
                      color: "#f87171",
                      border: "1px solid #f87171",
                      borderRadius: 3,
                      padding: "0 4px",
                      lineHeight: "16px",
                    }}
                  >
                    risky
                  </span>
                )}
              </div>
              <div style={{ color: "#666", fontSize: 11, marginTop: 1 }}>
                {tool.description}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
