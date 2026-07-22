import { useEffect } from "react";
import type { Toast as ToastType } from "../types";

const TOAST_COLORS: Record<string, string> = {
  success: "#34d399",
  error: "#f87171",
  info: "#60a5fa",
  warning: "#fbbf24",
};

interface Props {
  toasts: ToastType[];
  onDismiss: (id: string) => void;
}

export default function Toast({ toasts, onDismiss }: Props) {
  return (
    <div
      style={{
        position: "fixed",
        bottom: 20,
        right: 20,
        display: "flex",
        flexDirection: "column",
        gap: 8,
        zIndex: 1000,
      }}
    >
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onDismiss }: { toast: ToastType; onDismiss: (id: string) => void }) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(toast.id), 4000);
    return () => clearTimeout(timer);
  }, [toast.id, onDismiss]);

  return (
    <div
      onClick={() => onDismiss(toast.id)}
      style={{
        padding: "10px 16px",
        borderRadius: 8,
        background: "#1a1a2e",
        border: `1px solid ${TOAST_COLORS[toast.type]}`,
        borderLeft: `3px solid ${TOAST_COLORS[toast.type]}`,
        color: "#e0e0e0",
        fontSize: 13,
        maxWidth: 360,
        cursor: "pointer",
        boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
        animation: "slideIn 0.2s ease-out",
      }}
    >
      {toast.message}
    </div>
  );
}
