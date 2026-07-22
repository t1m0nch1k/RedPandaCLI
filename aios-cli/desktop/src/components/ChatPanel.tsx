import { useRef, useEffect, useMemo } from "react";
import type { ChatMessage } from "../types";

function formatTime(ts: Date): string {
  const d = ts instanceof Date ? ts : new Date(ts);
  const now = new Date();
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
  if (sameDay) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleDateString([], { day: "numeric", month: "short" }) +
    " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function renderMarkdown(text: string): string {
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, _lang, code) =>
    `<pre><code>${code.trim()}</code></pre>`
  );

  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

  html = html.replace(/\n/g, "<br>");

  return html;
}

interface Props {
  messages: ChatMessage[];
  connected: boolean;
}

export default function ChatPanel({ messages, connected }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const grouped = useMemo(() => {
    const groups: { msgs: ChatMessage[]; sender: string }[] = [];
    for (const m of messages) {
      const last = groups[groups.length - 1];
      if (last && last.sender === m.sender) {
        last.msgs.push(m);
      } else {
        groups.push({ msgs: [m], sender: m.sender });
      }
    }
    return groups;
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="chat-messages-area">
        <div className="empty-chat">
          {connected ? "Send a command to get started." : "Connecting to AIOS core..."}
        </div>
      </div>
    );
  }

  return (
    <div className="chat-messages-area">
      {grouped.map((group) => (
        <div key={group.msgs[0].id} className={`message-group ${group.sender}`}>
          {group.sender !== "user" && (
            <div className="message-sender-label">AIOS</div>
          )}
          {group.msgs.map((msg, mi) => (
            <div
              key={msg.id}
              className={`message-bubble ${group.sender}${mi === 0 ? " first-in-group" : " mid-in-group"}`}
            >
              <span
                dangerouslySetInnerHTML={{
                  __html: renderMarkdown(msg.text) + (msg.streaming
                    ? '<span class="streaming-cursor"></span>'
                    : ""),
                }}
              />
              <div className="message-timestamp">
                {formatTime(msg.timestamp)}
              </div>
            </div>
          ))}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
