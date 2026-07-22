import type { ConfirmRequest } from "../types";

const OVERLAY: Record<string, string | number> = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.6)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
};

const MODAL: Record<string, string | number> = {
  background: "#1a1a2e",
  border: "1px solid #333",
  borderRadius: 12,
  width: 520,
  maxWidth: "90vw",
  maxHeight: "80vh",
  display: "flex",
  flexDirection: "column",
  boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
};

const HEADER: Record<string, string | number> = {
  padding: "16px 20px",
  borderBottom: "1px solid #2a2a3e",
  fontSize: 16,
  fontWeight: 700,
  color: "#fff",
};

const BODY: Record<string, string | number> = {
  flex: 1,
  overflow: "auto",
  padding: "12px 20px",
};

const STEP_CARD: Record<string, string | number> = {
  padding: "10px 14px",
  background: "#14142a",
  borderRadius: 8,
  marginBottom: 8,
  border: "1px solid #2a2a3e",
};

const RISKY_BADGE: Record<string, string | number> = {
  display: "inline-block",
  fontSize: 10,
  fontWeight: 700,
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  color: "#f87171",
  border: "1px solid #f87171",
  borderRadius: 4,
  padding: "0 6px",
  lineHeight: "18px",
  marginLeft: 8,
};

const FOOTER: Record<string, string | number> = {
  display: "flex",
  justifyContent: "flex-end",
  gap: 10,
  padding: "12px 20px",
  borderTop: "1px solid #2a2a3e",
};

const BTN_BASE: Record<string, string | number> = {
  padding: "8px 24px",
  borderRadius: 8,
  border: "none",
  fontSize: 14,
  fontWeight: 600,
  cursor: "pointer",
};

interface Props {
  confirm: ConfirmRequest;
  onApprove: (confirmId: string) => void;
  onReject: (confirmId: string) => void;
}

export default function ConfirmModal({ confirm, onApprove, onReject }: Props) {
  const steps = confirm.plan.steps;

  return (
    <div style={OVERLAY}>
      <div style={MODAL}>
        <div style={HEADER}>Confirm Action</div>

        <div style={BODY}>
          <div
            style={{ fontSize: 12, color: "#888", marginBottom: 8 }}
          >
            "{confirm.user_input}"
          </div>

          {steps.length === 0 && (
            <div style={{ color: "#555", fontSize: 13 }}>No steps in this plan.</div>
          )}

          {steps.map((step, i) => (
            <div key={i} style={STEP_CARD}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  marginBottom: 4,
                }}
              >
                <span
                  style={{
                    width: 20,
                    height: 20,
                    borderRadius: "50%",
                    background: "#4361ee",
                    color: "#fff",
                    fontSize: 11,
                    fontWeight: 700,
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginRight: 8,
                    flexShrink: 0,
                  }}
                >
                  {i + 1}
                </span>
                <span style={{ fontSize: 14, fontWeight: 600, color: "#e0e0e0" }}>
                  {step.action}
                </span>
                {step.risky && <span style={RISKY_BADGE}>risky</span>}
              </div>

              {step.description && (
                <div style={{ fontSize: 13, color: "#999", marginLeft: 28 }}>
                  {step.description}
                </div>
              )}

              {step.reasoning && (
                <div
                  style={{
                    fontSize: 12,
                    color: "#666",
                    fontStyle: "italic",
                    marginLeft: 28,
                    marginTop: 4,
                  }}
                >
                  {step.reasoning}
                </div>
              )}

              {step.params && Object.keys(step.params).length > 0 && (
                <div style={{ marginLeft: 28, marginTop: 6 }}>
                  <pre
                    style={{
                      fontSize: 11,
                      color: "#888",
                      background: "#0f0f1a",
                      padding: "4px 8px",
                      borderRadius: 4,
                      margin: 0,
                      overflow: "auto",
                    }}
                  >
                    {JSON.stringify(step.params, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>

        <div style={FOOTER}>
          <button
            onClick={() => onReject(confirm.confirm_id)}
            style={{
              ...BTN_BASE,
              background: "transparent",
              border: "1px solid #555",
              color: "#ccc",
            }}
          >
            Reject
          </button>
          <button
            onClick={() => onApprove(confirm.confirm_id)}
            style={{
              ...BTN_BASE,
              background: "#4361ee",
              color: "#fff",
            }}
          >
            Approve
          </button>
        </div>
      </div>
    </div>
  );
}
