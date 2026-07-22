import { useMemo } from "react";
import type { TimelineEntry } from "../types";

interface Props {
  entries: TimelineEntry[];
}

const STATUS_ICONS = {
  info: "●",
  success: "✓",
  error: "✗",
  warning: "◉",
} as const;

const STATUS_COLORS = {
  info: "#60a5fa",
  success: "#34d399",
  error: "#f87171",
  warning: "#fbbf24",
} as const;

const EVENT_LABELS: Record<string, string> = {
  "intent.classified": "Parse Intent",
  "plan.created": "Create Plan",
  "plan.confirmed": "Confirm Plan",
  "plan.rejected": "Reject Plan",
  "step.started": "Execute Tool",
  "step.completed": "Tool Result",
  "executor.completed": "Completed",
  "executor.aborted": "Aborted",
};

export default function TimelinePanel({ entries }: Props) {
  const grouped = useMemo(() => {
    // Group by execution sessions (separated by executor.completed)
    const sessions: TimelineEntry[][] = [];
    let current: TimelineEntry[] = [];
    for (const e of entries) {
      current.push(e);
      if (e.event_type === "executor.completed" || e.event_type === "executor.aborted") {
        sessions.push(current);
        current = [];
      }
    }
    if (current.length > 0) sessions.push(current);
    return sessions;
  }, [entries]);

  if (entries.length === 0) {
    return (
      <div style={{ color: "#666", padding: 16, fontSize: 13 }}>
        No commands executed yet.
      </div>
    );
  }

  return (
    <div style={{ padding: "8px 0" }}>
      {grouped.map((session, si) => (
        <div key={si} style={{ marginBottom: 16 }}>
          <div
            style={{
              borderLeft: "2px solid #333",
              marginLeft: 10,
              paddingLeft: 16,
            }}
          >
            {session.map((entry) => {
              const label = EVENT_LABELS[entry.event_type] || entry.event_type;
              const icon = STATUS_ICONS[entry.status] || "●";
              const color = STATUS_COLORS[entry.status] || "#999";
              const duration =
                entry.duration_ms != null ? ` (${entry.duration_ms.toFixed(0)}ms)` : "";

              // Skip step.started if step.completed exists in same session
              if (
                entry.event_type === "step.started" &&
                session.find(
                  (e) =>
                    e.event_type === "step.completed" &&
                    e.detail?.action === entry.detail?.action &&
                    e !== entry
                )
              ) {
                return null;
              }

              return (
                <div
                  key={entry.id}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 10,
                    padding: "4px 0",
                    fontSize: 13,
                    lineHeight: 1.5,
                  }}
                >
                  <span style={{ color, flexShrink: 0, marginTop: 1 }}>
                    {icon}
                  </span>
                  <div style={{ minWidth: 0 }}>
                    <span style={{ color: "#e0e0e0" }}>
                      {label}
                    </span>
                    <span style={{ color: "#888", marginLeft: 6 }}>
                      {entry.description}{duration}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
