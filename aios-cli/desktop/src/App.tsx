import { useState, useCallback, useRef, useEffect } from "react";
import { listen } from "@tauri-apps/api/event";
import type { ToolMetadata, TimelineEntry, ChatMessage, ConfirmRequest, Toast as ToastType, FsListResult, FsReadResult, Attachment, ConversationInfo } from "./types";
import { useWebSocket } from "./components/useWebSocket";
import ChatPanel from "./components/ChatPanel";
import TimelinePanel from "./components/TimelinePanel";
import ToolListPanel from "./components/ToolListPanel";
import SettingsPanel from "./components/SettingsPanel";
import MemoryPanel from "./components/MemoryPanel";
import CalendarPanel from "./components/CalendarPanel";
import TimerPanel from "./components/TimerPanel";
import ConfirmModal from "./components/ConfirmModal";
import ExitModal from "./components/ExitModal";
import Toast from "./components/Toast";
import VoiceButton from "./components/VoiceButton";
import CoderPanel from "./components/CoderPanel";
import TitleBar from "./components/TitleBar";
import ErrorBoundary from "./components/ErrorBoundary";
import LogPanel from "./components/LogPanel";
import { pushLog } from "./lib/logStore";
import { getThemeDef } from "./theme/themes";

const EVENT_TO_TIMELINE: Record<string, string> = {
  "executor.step.started": "step.started",
  "executor.step.finished": "step.completed",
  "executor.completed": "executor.completed",
  "executor.aborted": "executor.aborted",
  "intent.classified": "intent.classified",
  "planner.plan_created": "plan.created",
  "plan.confirmed": "plan.confirmed",
  "plan.rejected": "plan.rejected",
};

let msgCounter = 0;
let toastCounter = 0;

export default function App() {
  const [tools, setTools] = useState<ToolMetadata[]>([]);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeView, setActiveView] = useState<"chat" | "timeline" | "tools" | "settings" | "coder" | "memory" | "calendar" | "timer">("chat");
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const [confirmRequest, setConfirmRequest] = useState<ConfirmRequest | null>(null);
  const [settings, setSettings] = useState<Record<string, unknown>>({});
  const [systemStatus, setSystemStatus] = useState<Record<string, unknown> | null>(null);
  const [toasts, setToasts] = useState<ToastType[]>([]);
  const [showExitModal, setShowExitModal] = useState(false);
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [ollamaModelsError, setOllamaModelsError] = useState("");
  const [fileTree, setFileTree] = useState<FsListResult | null>(null);
  const [fileContent, setFileContent] = useState<FsReadResult | null>(null);
  const [termResult, setTermResult] = useState<{ stdout: string; stderr: string; returncode: number } | null>(null);
  const [knowledgeResults, setKnowledgeResults] = useState<{ doc_id: string; text: string; score: number; metadata: Record<string, unknown> }[]>([]);
  const [knowledgeStatus, setKnowledgeStatus] = useState<{ status: string; document_count?: number } | null>(null);
  const [desktopPath, setDesktopPath] = useState<string | null>(null);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [input, setInput] = useState("");
  const [conversations, setConversations] = useState<ConversationInfo[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [themeId, setThemeId] = useState<string>(() => {
    return localStorage.getItem("aios-theme") || "aios-dark";
  });

  const inputRef = useRef<HTMLInputElement>(null);
  const trackedSendRef = useRef<(method: string, params?: Record<string, unknown>) => number | undefined>(
    () => undefined
  );

  const addToast = useCallback((type: ToastType["type"], message: string) => {
    const id = `toast-${toastCounter++}`;
    const msg = typeof message === "string" ? message : String(message);
    setToasts((prev) => [...prev.slice(-4), { id, type, message: msg }]);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const pendingQueries = useRef<Map<number, string>>(new Map());
  const streamingMsgId = useRef<string | null>(null);
  const prevConnectionRef = useRef<string>(connectionStatus);

  const normalizeTimelineEvent = useCallback(
    (event: string, payload: Record<string, unknown>): TimelineEntry | null => {
      const timelineEvent = EVENT_TO_TIMELINE[event];
      if (!timelineEvent) return null;

      const status = (payload as { status?: TimelineEntry["status"] }).status || "info";
      const description = (payload as { description?: string }).description || "";
      const duration_ms =
        (payload as { duration_ms?: number | null }).duration_ms ?? null;

      let detailPayload = payload;
      if (event === "executor.step.finished" && payload.action) {
        detailPayload = {
          action: payload.action,
          result: payload.result,
        };
      }

      return {
        id: crypto.randomUUID(),
        event_type: timelineEvent,
        description,
        timestamp: new Date().toISOString(),
        status,
        detail: detailPayload,
        duration_ms,
      };
    },
    []
  );

  const handleEvent = useCallback(
    (event: string, payload: Record<string, unknown>) => {
      switch (event) {
        case "agent.proactive": {
          const params = payload.params as { trigger?: string; message?: string } || {};
          const msg = params.message || "Notification";
          addToast("info", `🔔 ${msg}`);
          
          setMessages((prev) => [
            ...prev,
            {
              id: `proactive-${Date.now()}`,
              text: msg,
              sender: "assistant",
              timestamp: new Date(),
            },
          ]);
          
          if (document.hidden) {
            try {
              new Notification("AIOS", { body: msg });
            } catch (e) {}
          }
          break;
        }
        case "connection": {
          const newStatus = payload.status as string;
          const prev = prevConnectionRef.current;
          prevConnectionRef.current = newStatus;
          setConnectionStatus(newStatus);
          if (prev !== newStatus) {
            if (newStatus === "connected") addToast("success", "Connected to AIOS core");
            else if (newStatus === "disconnected") addToast("warning", "Disconnected from AIOS core");
          }
          return;
        }
        case "log": {
          const level = String(payload.level || "info");
          const msg = String(payload.message || "");
          pushLog("backend", level as "log" | "info" | "warn" | "error" | "debug", msg);
          if (level === "error" || level === "critical") {
            addToast("error", msg);
          }
          return;
        }
        case "agent.thinking": {
          const text = payload.text as string;
          const msgId = streamingMsgId.current;
          if (msgId) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === msgId ? { ...m, text } : m
              )
            );
          }
          return;
        }
        case "confirm_required":
          setConfirmRequest(payload as unknown as ConfirmRequest);
          return;
        case "tts.speaking": {
          const ttsText = payload.text as string;
          if ("speechSynthesis" in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(ttsText);
            utterance.lang = "ru-RU";
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            window.speechSynthesis.speak(utterance);
          }
          return;
        }
        default: {
          const tlEntry = normalizeTimelineEvent(event, payload);
          if (tlEntry) {
            setTimeline((prev) => [...prev, tlEntry]);
          }
        }
      }
    },
    [normalizeTimelineEvent, addToast]
  );

  const handleResponse = useCallback(
    (id: number | string | null, result: unknown) => {
      const query = pendingQueries.current.get(id as number);
      if (query === "tools.list") {
        setTools(result as ToolMetadata[]);
        pendingQueries.current.delete(id as number);
      } else if (query === "timeline.history") {
        const entries = result as TimelineEntry[];
        if (entries && entries.length > 0) {
          setTimeline((prev) => {
            const existing = new Set(prev.map((e) => e.id));
            const newEntries = entries.filter((e) => !existing.has(e.id));
            if (newEntries.length === 0) return prev;
            return [...prev, ...newEntries];
          });
        }
        pendingQueries.current.delete(id as number);
      } else if (query === "chat.send") {
        const res = result as { reply?: string; results?: unknown[]; error?: { message?: string }; conversation_id?: string } | null;
        const cid = res?.conversation_id;
        if (cid) {
          setCurrentConversationId(cid);
          setConversations((prev) => {
            const exists = prev.find((c) => c.id === cid);
            if (exists) {
              return prev.map((c) =>
                c.id === cid
                  ? { ...c, message_count: c.message_count + 2, updated_at: Date.now() / 1000, last_preview: res?.reply?.slice(0, 80) || "" }
                  : c
              );
            }
            return [{ id: cid, title: "Новый диалог", created_at: Date.now() / 1000, updated_at: Date.now() / 1000, message_count: 1, last_preview: "" }, ...prev];
          });
        }
        if (res?.error) {
          const errorText = res.error.message || "Chat request failed.";
          addToast("error", errorText);
          const streamId = streamingMsgId.current;
          if (streamId) {
            streamingMsgId.current = null;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === streamId ? { ...m, text: errorText, streaming: false } : m
              )
            );
          } else {
            setMessages((prev) => [
              ...prev,
              {
                id: `err-${msgCounter++}`,
                text: errorText,
                sender: "system" as const,
                timestamp: new Date(),
              },
            ]);
          }
          pendingQueries.current.delete(id as number);
          return;
        }
        const streamId = streamingMsgId.current;
        const reply = res?.reply;
        if (streamId) {
          streamingMsgId.current = null;
          if (reply) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === streamId
                  ? { ...m, text: reply, streaming: false }
                  : m
              )
            );
          }
        } else if (reply) {
          setMessages((prev) => {
            if (prev.length > 0 && prev[prev.length - 1].text === reply) {
              return prev;
            }
            return [...prev, {
              id: `sys-${msgCounter++}`,
              text: reply,
              sender: "system" as const,
              timestamp: new Date(),
            }];
          });
        }
        pendingQueries.current.delete(id as number);
      } else if (query === "action.confirm") {
        const res = result as { reply?: string } | null;
        setMessages((prev) => [
          ...prev,
          {
            id: `sys-${msgCounter++}`,
            text: res?.reply ?? "Action completed.",
            sender: "system" as const,
            timestamp: new Date(),
          },
        ]);
        pendingQueries.current.delete(id as number);
      } else if (query === "settings.get") {
        setSettings(result as Record<string, unknown>);
        pendingQueries.current.delete(id as number);
      } else if (query === "settings.update") {
        const res = result as Record<string, unknown>;
        if (res && !("error" in res)) {
          setSettings((prev) => ({ ...prev, ...res }));
          addToast("success", "Settings saved");
          trackedSend("settings.get");
        } else {
          addToast("error", "Failed to save settings");
        }
        pendingQueries.current.delete(id as number);
      } else if (query === "mcp.list") {
        const servers = result as { mcp_servers: Record<string, unknown>[] };
        if (servers?.mcp_servers) {
          setSettings((prev) => ({ ...prev, mcp_servers: servers.mcp_servers }));
        }
        pendingQueries.current.delete(id as number);
      } else if (query === "providers.list") {
        const provs = result as { providers: Record<string, unknown>[] };
        if (provs?.providers) {
          setSettings((prev) => ({ ...prev, providers: provs.providers }));
        }
        pendingQueries.current.delete(id as number);
      } else if (query === "system.status") {
        setSystemStatus(result as Record<string, unknown>);
        pendingQueries.current.delete(id as number);
      } else if (query === "llm.models") {
        const res = result as { models?: string[]; error?: string };
        setOllamaModels(res.models || []);
        setOllamaModelsError(res.error || "");
        if (res.error) addToast("warning", `Ollama models unavailable: ${res.error}`);
        pendingQueries.current.delete(id as number);
      } else if (query === "voice.ptt_stop") {
        const res = result as { reply?: string } | null;
        setMessages((prev) => [
          ...prev,
          {
            id: `sys-${msgCounter++}`,
            text: res?.reply ?? "Voice sent.",
            sender: "system" as const,
            timestamp: new Date(),
          },
        ]);
        pendingQueries.current.delete(id as number);
      } else if (query === "fs.list") {
        setFileTree(result as FsListResult);
        pendingQueries.current.delete(id as number);
      } else if (query === "fs.read") {
        const fr = result as FsReadResult;
        setFileContent(fr);
        if (fr && "content" in fr && !fr.error) {
          setAttachments((prev) => [...prev, { name: fr.name, content: fr.content, size: fr.size }]);
          addToast("success", `Attached: ${fr.name}`);
        } else if (fr?.error) {
          addToast("error", `File error: ${fr.error}`);
        }
        pendingQueries.current.delete(id as number);
      } else if (query === "fs.write") {
        const wr = result as { success: boolean; path: string; error?: string };
        if (wr.success) addToast("success", `Saved ${wr.path.split("/").pop() || wr.path}`);
        else addToast("error", wr.error || "Failed to save file");
        pendingQueries.current.delete(id as number);
      } else if (query === "term.exec") {
        setTermResult(result as { stdout: string; stderr: string; returncode: number });
        pendingQueries.current.delete(id as number);
      } else if (query === "conversation.list") {
        const list = result as ConversationInfo[];
        setConversations(list);
        if (list.length > 0 && !currentConversationId) {
          const mostRecent = list[0];
          setCurrentConversationId(mostRecent.id);
        }
        pendingQueries.current.delete(id as number);
      } else if (query === "conversation.create") {
        const res = result as { id: string; title: string };
        setCurrentConversationId(res.id);
        setMessages([]);
        setConversations((prev) => [{ id: res.id, title: res.title, created_at: Date.now() / 1000, updated_at: Date.now() / 1000, message_count: 0, last_preview: "" }, ...prev]);
        setTimeout(() => inputRef.current?.focus(), 0);
        pendingQueries.current.delete(id as number);
      } else if (query === "conversation.get") {
        const res = result as { messages: { role: string; content: string }[] };
        setMessages(
          res.messages.map((m, i) => ({
            id: `hist-${i}`,
            text: m.content || "",
            sender: (m.role === "user" ? "user" : "system") as "user" | "system",
            timestamp: new Date(),
          }))
        );
        pendingQueries.current.delete(id as number);
      } else if (query === "conversation.clear") {
        if (currentConversationId) {
          setConversations((prev) => prev.filter((c) => c.id !== currentConversationId));
          setCurrentConversationId(null);
          setMessages([]);
          trackedSendRef.current("conversation.create");
        }
        pendingQueries.current.delete(id as number);
      } else if (query === "conversation.rename") {
        const res = result as { ok: boolean };
        if (res.ok && currentConversationId) {
          // title was set by user action, no extra work needed
        }
        pendingQueries.current.delete(id as number);
      } else if (query === "knowledge.code_search") {
        setKnowledgeResults(result as { doc_id: string; text: string; score: number; metadata: Record<string, unknown> }[]);
        pendingQueries.current.delete(id as number);
      } else if (query === "knowledge.status") {
        setKnowledgeStatus(result as { status: string; document_count?: number });
        pendingQueries.current.delete(id as number);
      } else if (query === "fs.mkdir") {
        const mk = result as { success: boolean; path: string; error?: string };
        if (mk.success) addToast("success", `Created folder ${mk.path.split("/").pop() || mk.path}`);
        else addToast("error", mk.error || "Failed to create folder");
        pendingQueries.current.delete(id as number);
      } else if (query === "fs.create_file") {
        const cf = result as { success: boolean; path: string; error?: string };
        if (cf.success) addToast("success", `Created file ${cf.path.split("/").pop() || cf.path}`);
        else addToast("error", cf.error || "Failed to create file");
        pendingQueries.current.delete(id as number);
      } else if (query === "system.desktop_path") {
        const dp = result as { path?: string };
        if (dp.path) {
          setDesktopPath(dp.path);
        }
        pendingQueries.current.delete(id as number);
      } else if (query === "vision.capture") {
        const vr = result as { summary?: string; error?: string; windows?: unknown[] };
        if (vr.error) {
          addToast("error", `Screen capture: ${vr.error}`);
        } else {
          setMessages((prev) => [...prev, {
            id: `vision-${msgCounter++}`,
            text: `📷 Screen capture:\n${vr.summary || "No visual data detected"}`,
            sender: "system",
            timestamp: new Date(),
          }]);
        }
        pendingQueries.current.delete(id as number);
      } else if (query === "knowledge.index_file" || query === "knowledge.index_directory") {
        const idx = result as { indexed?: number; doc_id?: string; error?: string };
        if (idx.error) addToast("error", `Index error: ${idx.error}`);
        else if (idx.indexed !== undefined) addToast("success", `Indexed ${idx.indexed} files`);
        else if (idx.doc_id) addToast("success", `Indexed ${idx.doc_id}`);
        pendingQueries.current.delete(id as number);
      }
    },
    [addToast, currentConversationId]
  );

  const ws = useWebSocket(handleEvent, handleResponse);
  const wsSend = ws as unknown as {
    send: (m: string, p?: Record<string, unknown>) => number | undefined;
    sendBinary: (d: ArrayBufferLike) => void;
  };

  const trackedSend = useCallback(
    (method: string, params: Record<string, unknown> = {}) => {
      const id = wsSend.send(method, params);
      if (id !== undefined) {
        pendingQueries.current.set(id, method);
      }
      return id;
    },
    [wsSend]
  );
  trackedSendRef.current = trackedSend;

  const handleApprove = useCallback(
    (confirmId: string) => {
      setConfirmRequest(null);
      trackedSend("action.confirm", { confirm_id: confirmId, approved: true });
    },
    [trackedSend]
  );

  const handleReject = useCallback(
    (confirmId: string) => {
      setConfirmRequest(null);
      trackedSend("action.confirm", { confirm_id: confirmId, approved: false });
    },
    [trackedSend]
  );

  const handleSend = useCallback(
    (text: string) => {
      let fullText = text;
      if (attachments.length > 0) {
        const attached = attachments.map((a) =>
          `### File: ${a.name}\`\`\`\n${a.content}\n\`\`\``
        ).join("\n\n");
        fullText = `${text}\n\n${attached}`;
        setAttachments([]);
      }
      const streamId = `stream-${msgCounter}`;
      setMessages((prev) => [
        ...prev,
        {
          id: `user-${msgCounter++}`,
          text: fullText,
          sender: "user",
          timestamp: new Date(),
        },
        {
          id: streamId,
          text: "",
          sender: "system",
          timestamp: new Date(),
          streaming: true,
        },
      ]);
      streamingMsgId.current = streamId;
      trackedSend("chat.send", { text: fullText, stream: true, conversation_id: currentConversationId || undefined });
    },
    [trackedSend, attachments, currentConversationId]
  );

  const handleSaveSettings = useCallback(
    (section: string, values: Record<string, unknown>) => {
      trackedSend("settings.update", { section, values });
    },
    [trackedSend]
  );

  const handleGetSystemStatus = useCallback(() => {
    trackedSend("system.status");
  }, [trackedSend]);

  const handleRefreshOllamaModels = useCallback(() => {
    trackedSend("llm.models");
  }, [trackedSend]);

  const onConnected = useCallback(() => {
    trackedSend("tools.list");
    trackedSend("timeline.history", { limit: 50 });
    trackedSend("settings.get");
    trackedSend("llm.models");
    trackedSend("conversation.list");
  }, [trackedSend]);

  const [showLogs, setShowLogs] = useState(false);

  useEffect(() => {
    const def = getThemeDef(themeId);
    for (const [key, value] of Object.entries(def.vars)) {
      document.documentElement.style.setProperty(key, value);
    }
    document.documentElement.setAttribute("data-theme", def.base);
    localStorage.setItem("aios-theme", themeId);
  }, [themeId]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "L") {
        e.preventDefault();
        setShowLogs((v) => !v);
      }
      if (e.key === "Escape" && showLogs) {
        setShowLogs(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [showLogs]);

  useEffect(() => {
    const unlisten = listen("close-requested", () => {
      setShowExitModal(true);
    });
    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  const prevConnected = useRef(connectionStatus);
  if (prevConnected.current !== connectionStatus) {
    prevConnected.current = connectionStatus;
    if (connectionStatus === "connected") {
      setTimeout(onConnected, 100);
    }
  }

  const handleNewThread = useCallback(() => {
    setMessages([]);
    setActiveView("chat");
    trackedSend("conversation.create");
  }, [trackedSend]);

  const switchConversation = useCallback(
    (cid: string) => {
      if (cid === currentConversationId) return;
      setCurrentConversationId(cid);
      setMessages([]);
      trackedSend("conversation.get", { conversation_id: cid });
      setActiveView("chat");
    },
    [currentConversationId, trackedSend]
  );

  const handleSearchSubmit = useCallback(() => {
    const text = input.trim();
    if (!text || connectionStatus !== "connected") return;

    const lower = text.toLowerCase();
    if (lower === "/coder") {
      setActiveView("coder");
      setInput("");
      return;
    }
    if (lower === "/chat") {
      setActiveView("chat");
      setInput("");
      return;
    }

    handleSend(text);
    setInput("");
  }, [input, connectionStatus, handleSend]);

  const handleSearchKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") handleSearchSubmit();
    },
    [handleSearchSubmit]
  );

  const sidebarItems = [
    { key: "timeline" as const, label: "Automations", icon: "search" },
    { key: "tools" as const, label: "Skills", icon: "star" },
    { key: "coder" as const, label: "Coder", icon: "code" },
    { key: "memory" as const, label: "Memory", icon: "database" },
    { key: "calendar" as const, label: "Calendar", icon: "calendar" },
    { key: "timer" as const, label: "Timers", icon: "clock" },
  ];

  const connected = connectionStatus === "connected";

  const handleApplications = useCallback(() => {
    setActiveView("tools");
  }, []);

  const handleFileManager = useCallback(() => {
    setActiveView("coder");
  }, []);

  const handleCaptureScreen = useCallback(() => {
    if (!connected) return;
    trackedSend("vision.capture");
    addToast("info", "Capturing screen...");
  }, [connected, trackedSend, addToast]);

  const handleClipboard = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (!text) { addToast("warning", "Clipboard is empty"); return; }
      setInput(text);
      addToast("success", "Pasted from clipboard");
    } catch {
      addToast("error", "Cannot read clipboard");
    }
  }, [addToast]);

  const handleAttachFile = useCallback(async () => {
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selected = await open({
        multiple: false,
        title: "Attach File",
        filters: [{ name: "All Files", extensions: ["*"] }],
      });
      if (!selected) return;
      trackedSend("fs.read", { path: selected });
    } catch {
      addToast("error", "Failed to pick file");
    }
  }, [trackedSend, addToast]);

  const detachAttachment = useCallback((name: string) => {
    setAttachments((prev) => prev.filter((a) => a.name !== name));
  }, []);

  return (
    <ErrorBoundary>
    <div className="app-shell">
      <TitleBar onShowLogs={() => setShowLogs(true)} />
      <div className="app-window">
      {activeView === "coder" ? (
        <CoderPanel
          messages={messages}
          onSend={handleSend}
          connected={connected}
          onBack={() => setActiveView("chat")}
          sendBinary={wsSend.sendBinary}
          sendJson={trackedSend}
          fileTree={fileTree}
          fileContent={fileContent}
          onSave={(path, content) => trackedSend("fs.write", { path, content })}
          termResult={termResult}
          knowledgeResults={knowledgeResults}
          knowledgeStatus={knowledgeStatus}
          desktopPath={desktopPath}
        />
      ) : (
        <>
      {/* Sidebar */}
      <aside className="sidebar">
        {/* New chat button */}
        <div className="sidebar-section" style={{ padding: "0 12px 8px 12px" }}>
          <button
            className="new-chat-btn"
            onClick={handleNewThread}
            disabled={!connected}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 5v14M5 12h14"/></svg>
            <span>Новый чат</span>
          </button>
        </div>

        {/* Conversation list */}
        <div className="conversation-list">
          {conversations.map((conv) => (
            <button
              key={conv.id}
              className={`conversation-item${currentConversationId === conv.id ? " active" : ""}`}
              onClick={() => switchConversation(conv.id)}
            >
              <div className="conversation-item-icon">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              </div>
              <div className="conversation-item-content">
                <span className="conversation-item-title">{conv.title}</span>
                <span className="conversation-item-meta">{conv.message_count} сообщ.</span>
              </div>
            </button>
          ))}
        </div>

        <div className="sidebar-section">
          {sidebarItems.map((item) => (
            <button
              key={item.key}
              className={`sidebar-item${activeView === item.key ? " active" : ""}`}
              onClick={() => setActiveView(item.key)}
            >
              <div className="sidebar-item-icon">
                {item.icon === "search" ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="m4.93 4.93 4.24 4.24"/></svg>
                ) : item.icon === "code" ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
                ) : item.icon === "database" ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>
                ) : item.icon === "calendar" ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                ) : item.icon === "clock" ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                ) : (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                )}
              </div>
              <span>{item.label}</span>
            </button>
          ))}
        </div>

        <div className="sidebar-footer">
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div className={`connection-dot ${connected ? "connected" : "disconnected"}`} />
            <span style={{ fontSize: 11, color: "#888" }}>{connected ? "Connected" : "Disconnected"}</span>
          </div>
          <button
            className="sidebar-settings-btn"
            onClick={() => setActiveView("settings")}
            title="Settings"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {activeView === "chat" ? (
          /* Messenger-style chat layout */
          <div className="chat-container">
            <ChatPanel messages={messages} connected={connected} />

            {attachments.length > 0 && (
              <div className="attachment-bar">
                {attachments.map((a) => (
                  <div key={a.name} className="attachment-chip">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
                    <span className="attachment-chip-name">{a.name}</span>
                    <span className="attachment-chip-size">({(a.size / 1024).toFixed(1)} KB)</span>
                    <button
                      className="attachment-chip-remove"
                      onClick={() => detachAttachment(a.name)}
                      title="Remove"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6 6 18M6 6l12 12"/></svg>
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Bottom bar: input + tools */}
            <div className="chat-input-area">
              <div className="search-bar-wrapper">
                <input
                  ref={inputRef}
                  className="search-input"
                  placeholder="Start a task..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleSearchKeyDown}
                  disabled={!connected}
                />
                <button className="action-add-btn" title="Add context">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                </button>
              </div>
              <div className="tools-row">
                <button className="tool-icon-btn" title="Applications" onClick={handleApplications}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>
                </button>
                <button className="tool-icon-btn" title="File Manager" onClick={handleFileManager}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
                </button>
                <button className="tool-icon-btn" title="Capture Screen" onClick={handleCaptureScreen}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                </button>
                <button className="tool-icon-btn" title="Paste from Clipboard" onClick={handleClipboard}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                </button>
                <button className="tool-icon-btn" title="Attach File" onClick={handleAttachFile}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
                </button>

                <div className="tool-divider" />

                <VoiceButton
                  className="tool-icon-btn"
                  connected={connected}
                  sendBinary={wsSend.sendBinary}
                  sendJson={trackedSend}
                />
              </div>
            </div>
          </div>
        ) : (
          /* Perplexity overlay for non-chat views */
          <div className="perplexity-overlay">
            {activeView === "timeline" && (
              <div className="overlay-view">
                <TimelinePanel entries={timeline} />
              </div>
            )}

            {activeView === "tools" && (
              <div className="overlay-view">
                <ToolListPanel tools={tools} />
              </div>
            )}

            {activeView === "settings" && (
              <div className="overlay-view">
                <div className="overlay-header">
                  <button className="overlay-back-btn" onClick={() => setActiveView("chat")} title="Back">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
                  </button>
                  <span className="overlay-title">Settings</span>
                </div>
                <SettingsPanel
                  settings={settings}
                  onSave={handleSaveSettings}
                  getSystemStatus={handleGetSystemStatus}
                  systemStatus={systemStatus}
                  tools={tools}
                  ollamaModels={ollamaModels}
                  refreshOllamaModels={handleRefreshOllamaModels}
                  ollamaModelsError={ollamaModelsError}
                  themeId={themeId}
                  onThemeChange={setThemeId}
                />
              </div>
            )}

            {activeView === "memory" && (
              <div style={{ flex: 1, overflowY: "auto" }}>
                <MemoryPanel sendRequest={trackedSend} />
              </div>
            )}

            {activeView === "calendar" && (
              <div style={{ flex: 1, overflowY: "auto" }}>
                <CalendarPanel sendRequest={trackedSend} />
              </div>
            )}

            {activeView === "timer" && (
              <div style={{ flex: 1, overflowY: "auto" }}>
                <TimerPanel sendRequest={trackedSend} />
              </div>
            )}
          </div>
        )}

        {/* Status footer (always visible) */}
        <div className="status-footer">
          <div className="footer-links">
            <span className="footer-link">Local</span>
            <span className="footer-link">Cloud</span>
          </div>
          <div>{messages.filter((m) => m.sender === "system").length > 0 ? `${messages.filter((m) => m.sender === "system").length} responses` : "—"}</div>
        </div>
      </main>
        </>
      )}
      </div>

      {confirmRequest && (
        <ConfirmModal
          confirm={confirmRequest}
          onApprove={handleApprove}
          onReject={handleReject}
        />
      )}

      {showExitModal && (
        <ExitModal onClose={() => setShowExitModal(false)} />
      )}
      
      <Toast toasts={toasts} onDismiss={dismissToast} />


      {showLogs && <LogPanel onClose={() => setShowLogs(false)} />}
    </div>
    </ErrorBoundary>
  );
}
