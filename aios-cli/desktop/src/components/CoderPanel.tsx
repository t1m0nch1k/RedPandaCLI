import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import { ChevronRight, File, Folder, FolderOpen, Search, Terminal as TerminalIcon, X, Plus, GitBranch } from 'lucide-react';
import type { ChatMessage, FsListResult, FsReadResult, FileEntry } from "../types";
import MonacoEditor from "./MonacoEditor";
import XtermTerminal, { type XtermHandle } from "./XtermTerminal";
import { fileIcon, folderIcon } from "./iconMap";

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

function renderCoderMarkdown(text: string): string {
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

interface Kr {
  doc_id: string; text: string; score: number; metadata: Record<string, unknown>;
}

interface Props {
  messages: ChatMessage[];
  onSend: (text: string) => void;
  connected: boolean;
  onBack: () => void;
  sendBinary: (data: ArrayBufferLike) => void;
  sendJson: (method: string, params?: Record<string, unknown>) => number | undefined;
  fileTree: FsListResult | null;
  fileContent: FsReadResult | null;
  onSave: (path: string, content: string) => number | undefined;
  termResult: { stdout: string; stderr: string; returncode: number } | null;
  knowledgeResults: Kr[];
  knowledgeStatus: { status: string; document_count?: number } | null;
  desktopPath: string | null;
}

export default function CoderPanel({ messages, onSend, connected, onBack, sendBinary, sendJson, fileTree, fileContent, onSave, termResult, knowledgeResults, knowledgeStatus, desktopPath }: Props) {
  const [chatInput, setChatInput] = useState("");
  const [recording, setRecording] = useState(false);
  const [currentFilePath, setCurrentFilePath] = useState("");
  const [editorContent, setEditorContent] = useState("");
  const [isDirty, setIsDirty] = useState(false);
  const [dirCache, setDirCache] = useState<Record<string, FileEntry[]>>({});
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set());
  const loadingDirs = useRef<Set<string>>(new Set());
  const [showTerminal, setShowTerminal] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Kr[]>([]);
  const [searching, setSearching] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [kbStatus, setKbStatus] = useState<string>("");
  const [rootDir, setRootDir] = useState<string | null>(null);
  const [showNewFile, setShowNewFile] = useState(false);
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [newItemName, setNewItemName] = useState("");
  const xtermRef = useRef<XtermHandle>(null);

  const navigateToDir = useCallback((dir: string) => {
    setRootDir(dir);
    setExpandedDirs(new Set());
    setDirCache({});
  }, []);

  const refreshDir = useCallback((path: string) => {
    setDirCache(prev => {
      const next = { ...prev };
      delete next[path];
      return next;
    });
    loadingDirs.current.add(path);
    sendJson("fs.list", { path });
  }, [sendJson]);

  useEffect(() => {
    if (fileContent) {
      setEditorContent(fileContent.content);
      setIsDirty(false);
    }
  }, [fileContent]);

  useEffect(() => {
    if (fileTree && fileTree.entries) {
      setDirCache(prev => ({ ...prev, [fileTree.path]: fileTree.entries }));
      loadingDirs.current.delete(fileTree.path);
    }
  }, [fileTree]);

  useEffect(() => {
    if (desktopPath && !rootDir) {
      navigateToDir(desktopPath);
    }
  }, [desktopPath, rootDir, navigateToDir]);

  useEffect(() => {
    if (connected && rootDir) {
      sendJson("fs.list", { path: rootDir });
      sendJson("knowledge.status");
    }
  }, [connected, sendJson, rootDir]);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const handleEditorChange = useCallback((value: string) => {
    setEditorContent(value);
    setIsDirty(value !== (fileContent?.content ?? ""));
  }, [fileContent]);

  const handleSave = useCallback(() => {
    if (!currentFilePath || !isDirty) return;
    onSave(currentFilePath, editorContent);
    setIsDirty(false);
  }, [currentFilePath, isDirty, editorContent, onSave]);

  const handleChatSend = useCallback(() => {
    const text = chatInput.trim();
    if (!text || !connected) return;
    if (fileContent && currentFilePath) {
      sendJson("chat.send", { text, stream: true, context: { file: { path: currentFilePath, content: fileContent.content } } });
    } else {
      onSend(text);
    }
    setChatInput("");
  }, [chatInput, connected, onSend, sendJson, fileContent, currentFilePath]);

  const handleChatKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        handleChatSend();
      }
    },
    [handleChatSend]
  );

  const groupedMessages = useMemo(() => {
    const groups: { msgs: ChatMessage[]; sender: string }[] = [];
    for (const m of messages) {
      const last = groups[groups.length - 1];
      if (last && last.sender === m.sender) {
        last.msgs.push(m);
      } else {
        groups.push({ msgs: [m], sender: m.sender });
      }
    }
    return groups.slice(-20);
  }, [messages]);

  const handleVoiceStart = useCallback(async () => {
    if (!connected) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "audio/webm",
      });
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        chunksRef.current = [];
        try {
          const arrayBuffer = await blob.arrayBuffer();
          const audioCtx = new AudioContext({ sampleRate: 16000 });
          const audioBuf = await audioCtx.decodeAudioData(arrayBuffer);
          const channel = audioBuf.getChannelData(0);
          const pcm16 = new Int16Array(channel.length);
          for (let i = 0; i < channel.length; i++) {
            const s = Math.round(channel[i] * 32768);
            pcm16[i] = Math.max(-32768, Math.min(32767, s));
          }
          audioCtx.close();
          if (pcm16.length > 0) sendBinary(pcm16.buffer);
        } catch { }
        setRecording(false);
        sendJson("voice.ptt_stop");
      };
      recorder.start(100);
      setRecording(true);
      sendJson("voice.ptt_start");
    } catch { }
  }, [connected, sendBinary, sendJson]);

  const handleVoiceStop = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const openFile = useCallback((path: string) => {
    setCurrentFilePath(path);
    sendJson("fs.read", { path });
  }, [sendJson]);

  const toggleFolder = useCallback((path: string) => {
    setExpandedDirs(prev => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
        if (!dirCache[path] && !loadingDirs.current.has(path)) {
          loadingDirs.current.add(path);
          sendJson("fs.list", { path });
        }
      }
      return next;
    });
  }, [dirCache, sendJson]);

  const sortEntries = useCallback((entries: FileEntry[] | undefined): FileEntry[] => {
    if (!entries) return [];
    return [...entries].sort((a, b) => {
      if (a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1;
      return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
    });
  }, []);

  const renderTreeNode = useCallback((entry: FileEntry, parentPath: string, depth: number): React.ReactNode => {
    const fullPath = parentPath ? parentPath + "/" + entry.name : entry.name;
    const isExpanded = expandedDirs.has(fullPath);
    const children = entry.is_dir ? dirCache[fullPath] : undefined;
    const icon = entry.is_dir
      ? folderIcon(entry.name, isExpanded)
      : (fullPath === currentFilePath ? fileIcon(entry.name) : fileIcon(entry.name));

    return (
      <div key={fullPath}>
        <div
          className="coder-file-item"
          style={{
            cursor: "pointer", padding: "2px 8px 2px " + (12 + depth * 16) + "px",
            display: "flex", alignItems: "center", gap: 4, fontSize: 13,
            color: fullPath === currentFilePath ? 'var(--color-accent)' : 'var(--color-text)',
            userSelect: "none", whiteSpace: "nowrap",
            background: fullPath === currentFilePath ? 'var(--color-accent-soft)' : 'transparent',
            borderRadius: 4, margin: '0 4px',
          }}
          onClick={() => entry.is_dir ? toggleFolder(fullPath) : openFile(fullPath)}
          onMouseEnter={(e) => { if (fullPath !== currentFilePath) e.currentTarget.style.background = 'var(--color-surface-raised)' }}
          onMouseLeave={(e) => { if (fullPath !== currentFilePath) e.currentTarget.style.background = 'transparent' }}
        >
          {entry.is_dir ? (
            <ChevronRight
              size={10}
              style={{
                flexShrink: 0,
                transform: isExpanded ? "rotate(90deg)" : "none",
                transition: "transform 0.1s",
                color: 'var(--color-text-muted)'
              }}
            />
          ) : (
            <span style={{ width: 10, flexShrink: 0 }} />
          )}
          {entry.is_dir ? (
            isExpanded
              ? <FolderOpen size={14} style={{ flexShrink: 0, color: '#dcb67a' }} />
              : <Folder size={14} style={{ flexShrink: 0, color: '#b8944f' }} />
          ) : (
            <File size={14} style={{ flexShrink: 0, color: icon.color }} />
          )}
          <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis" }}>
            {entry.name}
          </span>
          {!entry.is_dir && (
            <span style={{ color: 'var(--color-text-muted)', fontSize: 11, flexShrink: 0 }}>
              {entry.size > 1024 ? `${(entry.size / 1024).toFixed(1)} KB` : `${entry.size} B`}
            </span>
          )}
        </div>
        {entry.is_dir && isExpanded && (
          children ? (
            sortEntries(children).map(child => renderTreeNode(child, fullPath, depth + 1))
          ) : (
            <div style={{ paddingLeft: 28 + (depth + 1) * 16, color: 'var(--color-text-muted)', fontSize: 11 }}>
              Loading...
            </div>
          )
        )}
      </div>
    );
  }, [expandedDirs, dirCache, currentFilePath, sortEntries, toggleFolder, openFile]);

  const goUpDir = useCallback(() => {
    if (!rootDir) return;
    const parent = rootDir.replace(/\\/g, "/").replace(/\/?[^/\\]+$/, "");
    if (parent && parent !== rootDir) navigateToDir(parent);
  }, [rootDir, navigateToDir]);

  const handleCreateFile = useCallback(() => {
    const name = newItemName.trim();
    if (!name || !rootDir) return;
    const fullPath = rootDir + "/" + name;
    sendJson("fs.create_file", { path: fullPath });
    setNewItemName("");
    setShowNewFile(false);
    setTimeout(() => refreshDir(rootDir), 300);
  }, [newItemName, rootDir, sendJson, refreshDir]);

  const handleCreateFolder = useCallback(() => {
    const name = newItemName.trim();
    if (!name || !rootDir) return;
    const fullPath = rootDir + "/" + name;
    sendJson("fs.mkdir", { path: fullPath, parents: true, exist_ok: false });
    setNewItemName("");
    setShowNewFolder(false);
    setTimeout(() => refreshDir(rootDir), 300);
  }, [newItemName, rootDir, sendJson, refreshDir]);

  const handlePickFolder = useCallback(async () => {
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selected = await open({ directory: true, multiple: false, title: "Open Folder" });
      if (selected) {
        navigateToDir(selected as string);
      }
    } catch {
      const dir = prompt("Enter directory path:");
      if (dir && dir.trim()) navigateToDir(dir.trim());
    }
  }, [navigateToDir]);

  const handleCreateKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>, action: () => void) => {
    if (e.key === "Enter") action();
    if (e.key === "Escape") { setShowNewFile(false); setShowNewFolder(false); setNewItemName(""); }
  }, []);

  const handleTermCommand = useCallback((command: string) => {
    if (!connected) return;
    xtermRef.current?.write(`\r\n$ ${command}\r\n`);
    sendJson("term.exec", { command, timeout: 30 });
  }, [connected, sendJson]);

  useEffect(() => {
    if (termResult) {
      let output = '';
      if (termResult.stdout) output += termResult.stdout;
      if (termResult.stderr) output += `\r\n\x1b[31m${termResult.stderr}\x1b[0m`;
      output += `\r\n\x1b[90mExit code: ${termResult.returncode}\x1b[0m\r\n`;
      xtermRef.current?.write(output);
    }
  }, [termResult]);

  const doCodeSearch = useCallback(() => {
    const q = searchQuery.trim();
    if (!q || !connected) return;
    setSearching(true);
    setSearchResults([]);
    sendJson("knowledge.code_search", { query: q, top_k: 10 });
  }, [searchQuery, connected, sendJson]);

  const handleSearchKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") doCodeSearch();
  }, [doCodeSearch]);

  const doIndexDir = useCallback(() => {
    if (!connected) return;
    setIndexing(true);
    sendJson("knowledge.index_directory", { path: ".", repo_root: "." });
  }, [connected, sendJson]);

  useEffect(() => {
    if (knowledgeResults.length > 0 || searching) {
      setSearching(false);
      setSearchResults(knowledgeResults);
    }
  }, [knowledgeResults, searching]);

  useEffect(() => {
    if (knowledgeStatus) {
      setKbStatus(knowledgeStatus.document_count !== undefined
        ? `${knowledgeStatus.document_count} docs indexed`
        : knowledgeStatus.status);
    }
  }, [knowledgeStatus]);

  const updateActivity = useCallback((view: "explorer" | "search") => {
    setShowSearch(view === "search");
  }, []);

  return (
    <div className="coder-container">
      <div className="coder-titlebar">
        <div style={{ display: "flex", alignItems: "center", gap: 8, width: 80 }}>
          <button onClick={onBack} title="Back to main" style={{ background: "none", border: "none", color: 'var(--color-text-muted)', cursor: "pointer", display: "flex", padding: 4 }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          </button>
        </div>
        <div className="coder-project-title">
          <GitBranch size={12} />
          <span>AIOS — Coder</span>
        </div>
        <div className="coder-top-actions">
          <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
            {connected ? '● Connected' : '○ Disconnected'}
          </span>
        </div>
      </div>

      <div className="coder-workspace">
        <div className="coder-workspace-main">
          {/* Activity Bar */}
          <div className="coder-activity-bar">
            <button className={`coder-activity-btn${!showSearch ? " active" : ""}`} title="Explorer" onClick={() => updateActivity("explorer")}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 9h18M3 15h18M3 3h18M3 21h18"/></svg>
            </button>
            <button className={`coder-activity-btn${showSearch ? " active" : ""}`} title="Search" onClick={() => updateActivity("search")}>
              <Search size={18} />
            </button>
            <button className="coder-activity-btn" title="Source Control">
              <GitBranch size={18} />
            </button>
            <div style={{ flex: 1 }} />
            <button
              className={`coder-activity-btn${showTerminal ? " active" : ""}`}
              onClick={() => setShowTerminal(v => !v)}
              title="Terminal"
            >
              <TerminalIcon size={18} />
            </button>
          </div>

          {/* File Explorer / Search */}
          <div className="coder-explorer">
            {!showSearch ? (
              <>
                <div className="coder-explorer-heading">
                  <span>{!rootDir ? "Explorer" : rootDir.split(/[/\\]/).pop()}</span>
                  {rootDir && <div style={{ display: "flex", gap: 2 }}>
                    <button className="coder-activity-btn" title="New File" onClick={() => { setShowNewFolder(false); setShowNewFile(v => !v); setNewItemName(""); }}>
                      <Plus size={12} />
                    </button>
                    <button className="coder-activity-btn" title="New Folder" onClick={() => { setShowNewFile(false); setShowNewFolder(v => !v); setNewItemName(""); }}>
                      <FolderPlus size={12} />
                    </button>
                    <button className="coder-activity-btn" title="Open Folder" onClick={handlePickFolder}>
                      <FolderOpen size={12} />
                    </button>
                  </div>}
                </div>
                {rootDir && (
                  <div style={{ display: "flex", alignItems: "center", gap: 2, padding: "2px 8px", borderBottom: "1px solid var(--color-border)", fontSize: 11, color: 'var(--color-text-muted)' }}>
                    <span style={{ cursor: "pointer", padding: "2px 4px", borderRadius: 3 }} onClick={() => navigateToDir(rootDir.replace(/[/\\][^/\\]+$/, "") || rootDir)}>
                      {rootDir.split(/[/\\]/).pop()}
                    </span>
                    <span style={{ flex: 1 }} />
                    <span style={{ cursor: "pointer", padding: "0 4px" }} onClick={goUpDir} title="Go up">↑</span>
                  </div>
                )}
                {(showNewFile || showNewFolder) && (
                  <div style={{ padding: "4px 8px", display: "flex", gap: 4, borderBottom: "1px solid var(--color-border)", alignItems: "center" }}>
                    {showNewFolder
                      ? <Folder size={14} style={{ flexShrink: 0, color: '#b8944f' }} />
                      : <File size={14} style={{ flexShrink: 0, color: '#608b4e' }} />
                    }
                    <input
                      value={newItemName}
                      onChange={e => setNewItemName(e.target.value)}
                      onKeyDown={e => handleCreateKeyDown(e, showNewFile ? handleCreateFile : handleCreateFolder)}
                      placeholder={showNewFile ? "filename.ext" : "folder-name"}
                      style={{
                        flex: 1, padding: "4px 6px", background: 'var(--color-surface-raised)',
                        border: "1px solid var(--color-border)", borderRadius: 4,
                        color: 'var(--color-text)', fontSize: 12, outline: "none",
                      }}
                      autoFocus
                    />
                  </div>
                )}
                <div className="coder-file-list" style={{ overflow: 'auto', flex: 1 }}>
                  {!rootDir ? (
                    <div style={{ padding: "32px 16px", textAlign: "center" }}>
                      <FolderOpen size={48} style={{ color: 'var(--color-border-strong)', marginBottom: 12 }} />
                      <div style={{ fontSize: 13, color: 'var(--color-text-muted)', marginBottom: 12 }}>No folder opened</div>
                      <div
                        onClick={handlePickFolder}
                        style={{
                          display: "inline-flex", alignItems: "center", gap: 6,
                          padding: "6px 14px", borderRadius: 4,
                          color: 'var(--color-text)', fontSize: 12, cursor: "pointer",
                          background: 'var(--color-surface-raised)', border: "1px solid var(--color-border)",
                        }}
                      >
                        <FolderOpen size={14} />
                        Open Folder
                      </div>
                    </div>
                  ) : dirCache[rootDir] ? (
                    sortEntries(dirCache[rootDir]).map(entry => renderTreeNode(entry, rootDir === "." ? "" : rootDir, 0))
                  ) : (
                    <div style={{ color: 'var(--color-text-muted)', fontSize: 12, padding: "20px 16px", textAlign: "center" }}>
                      Loading...
                    </div>
                  )}
                </div>
              </>
            ) : (
              <>
                <div className="coder-explorer-heading" style={{ justifyContent: "space-between" }}>
                  <span>SEARCH</span>
                  <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>{kbStatus}</span>
                </div>
                <div style={{ padding: "8px 12px", display: "flex", flexDirection: "column", gap: 8 }}>
                  <input
                    className="coder-search-input"
                    placeholder="Search code..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={handleSearchKeyDown}
                    disabled={!connected}
                    style={{
                      width: "100%", padding: "6px 8px", background: 'var(--color-surface-raised)',
                      border: "1px solid var(--color-border)", borderRadius: 4,
                      color: 'var(--color-text)', fontSize: 13, outline: "none",
                    }}
                  />
                  <div style={{ display: "flex", gap: 6 }}>
                    <button
                      onClick={doCodeSearch}
                      disabled={!connected || searching}
                      style={{
                        flex: 1, padding: "4px 8px", background: 'var(--color-surface-raised)',
                        border: "1px solid var(--color-border)", borderRadius: 4,
                        color: 'var(--color-text)', cursor: "pointer", fontSize: 12,
                      }}
                    >
                      {searching ? "Searching..." : "Search"}
                    </button>
                    <button
                      onClick={doIndexDir}
                      disabled={!connected || indexing}
                      title="Index project files"
                      style={{
                        padding: "4px 8px", background: 'var(--color-surface-raised)',
                        border: "1px solid var(--color-border)", borderRadius: 4,
                        color: 'var(--color-text)', cursor: "pointer", fontSize: 12,
                      }}
                    >
                      {indexing ? "..." : "Index"}
                    </button>
                  </div>
                  <div className="search-results" style={{ maxHeight: 300, overflowY: "auto", display: "flex", flexDirection: "column", gap: 4 }}>
                    {searchResults.length === 0 && !searching && (
                      <div style={{ color: 'var(--color-text-muted)', fontSize: 12, textAlign: "center", padding: 12 }}>
                        {kbStatus ? "Search your codebase" : "Index project files first"}
                      </div>
                    )}
                    {searchResults.map((r, i) => (
                      <div
                        key={i}
                        style={{
                          padding: "6px 8px", background: 'var(--color-surface)',
                          borderRadius: 4, cursor: "pointer",
                          border: "1px solid var(--color-border)",
                        }}
                        onClick={() => {
                          const path = r.metadata?.path as string;
                          if (path) openFile(path);
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--color-border-strong)')}
                        onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--color-border)')}
                      >
                        <div style={{ fontSize: 12, color: '#608b4e', overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {r.metadata?.path as string || r.doc_id}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--color-text-secondary)', marginTop: 2, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                          {r.text.slice(0, 200)}
                        </div>
                        <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginTop: 2 }}>
                          Score: {(1 - r.score).toFixed(3)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Editor + Terminal column */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
            {/* Monaco Editor */}
            <div className="coder-editor" style={{ flex: showTerminal ? "1 1 50%" : "1 1 100%", display: 'flex', flexDirection: 'column' }}>
              {currentFilePath && (
                <div className="coder-editor-header">
                  <span className="coder-editor-filename" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    {fileIcon(currentFilePath.split('/').pop() || currentFilePath).type && (
                      <File size={12} style={{ color: fileIcon(currentFilePath.split('/').pop() || currentFilePath).color }} />
                    )}
                    {currentFilePath.split("/").pop() || currentFilePath}
                    {isDirty && <span style={{ color: 'var(--color-warning)' }}> ●</span>}
                  </span>
                  <button className="coder-editor-save-btn" onClick={handleSave} disabled={!isDirty}
                    style={{
                      padding: '2px 10px', fontSize: 12, borderRadius: 4,
                      background: isDirty ? 'var(--color-accent-soft)' : 'transparent',
                      border: '1px solid var(--color-border)', color: 'var(--color-text)',
                      cursor: isDirty ? 'pointer' : 'default', opacity: isDirty ? 1 : 0.5,
                    }}>
                    Save
                  </button>
                </div>
              )}
              <div className="coder-code-view" style={{ flex: 1, overflow: 'hidden' }}>
                {fileContent ? (
                  <MonacoEditor
                    path={currentFilePath}
                    value={editorContent}
                    onChange={handleEditorChange}
                  />
                ) : (
                  <div style={{ color: 'var(--color-text-muted)', fontSize: 13, padding: 20, textAlign: 'center' }}>
                    {currentFilePath ? "Loading..." : "Select a file to view"}
                  </div>
                )}
              </div>
            </div>

            {/* Xterm Terminal */}
            {showTerminal && (
              <div className="coder-terminal-panel" style={{
                flex: '0 0 auto', height: 200, display: 'flex', flexDirection: 'column',
                borderTop: '1px solid var(--color-border)'
              }}>
                <div className="coder-terminal-header" style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '4px 12px', fontSize: 11, color: 'var(--color-text-secondary)',
                  background: 'var(--color-surface)', borderBottom: '1px solid var(--color-border)',
                  flexShrink: 0,
                }}>
                  <span>TERMINAL</span>
                  <button onClick={() => setShowTerminal(false)} title="Close terminal"
                    style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer' }}>
                    <X size={12} />
                  </button>
                </div>
                <div style={{ flex: 1, padding: 4, background: 'var(--color-bg)' }}>
                  <XtermTerminal ref={xtermRef} onCommand={handleTermCommand} />
                </div>
              </div>
            )}
          </div>

          {/* AI Chat Pane */}
          <div className="coder-chat-pane" style={{
            width: 300, borderLeft: '1px solid var(--color-border)',
            display: 'flex', flexDirection: 'column', flexShrink: 0,
            background: 'var(--color-surface)',
          }}>
            <div className="coder-pane-header" style={{
              padding: '8px 12px', fontSize: 11, color: 'var(--color-text-secondary)',
              borderBottom: '1px solid var(--color-border)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <span>AI CHAT</span>
            </div>

            <div className="coder-chat-history" style={{ flex: 1, overflow: 'auto', padding: 8 }}>
              {messages.length === 0 && (
                <div style={{ color: 'var(--color-text-muted)', fontSize: 12, textAlign: 'center', padding: 20 }}>
                  {connected ? "Ask AI about your code..." : "Connecting..."}
                </div>
              )}
              {groupedMessages.map((group) => (
                <div key={group.msgs[0].id}>
                  {group.msgs.map((msg) => (
                    <div key={msg.id} className={`coder-chat-bubble ${msg.sender === "user" ? "user" : ""}`}
                      style={{
                        padding: '8px 10px', marginBottom: group.msgs.length > 1 ? 2 : 6,
                        borderRadius: 8, fontSize: 13, lineHeight: 1.5,
                        background: msg.sender === "user" ? 'var(--color-accent-soft)' : 'var(--color-surface-raised)',
                        color: 'var(--color-text)',
                      }}>
                      <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginBottom: 4 }}>
                        {msg.sender === "user" ? "You" : "AI"}
                      </div>
                      <span dangerouslySetInnerHTML={{ __html: renderCoderMarkdown(msg.text) }} />
                      <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginTop: 4, textAlign: "right" }}>
                        {formatTime(msg.timestamp)}
                      </div>
                    </div>
                  ))}
                </div>
              ))}
              <div ref={chatBottomRef} />
            </div>

            <div className="coder-input-container" style={{
              borderTop: '1px solid var(--color-border)', padding: 8, flexShrink: 0,
            }}>
              <div className="coder-perplexity-box" style={{
                display: 'flex', flexDirection: 'column', gap: 6,
              }}>
                <textarea
                  className="coder-ai-input"
                  placeholder="Ask AI or dictate code..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={handleChatKeyDown}
                  disabled={!connected}
                  style={{
                    width: '100%', padding: '8px 10px', background: 'var(--color-surface-raised)',
                    border: '1px solid var(--color-border)', borderRadius: 8,
                    color: 'var(--color-text)', fontSize: 13, outline: 'none', resize: 'none',
                    fontFamily: 'inherit', minHeight: 60,
                  }}
                />
                {fileContent && currentFilePath && (
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 4, padding: '4px 8px',
                    background: 'var(--color-surface-raised)', borderRadius: 4, fontSize: 11,
                    color: '#608b4e',
                  }}>
                    <File size={12} />
                    <span>{currentFilePath.split("/").pop()}</span>
                  </div>
                )}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button
                      className={`coder-ai-tool-btn${recording ? " active-voice" : ""}`}
                      title="Voice input"
                      onMouseDown={handleVoiceStart}
                      onMouseUp={handleVoiceStop}
                      onMouseLeave={recording ? handleVoiceStop : undefined}
                      style={{
                        padding: 4, background: 'none', border: 'none', color: recording ? 'var(--color-danger)' : 'var(--color-text-muted)',
                        cursor: 'pointer', borderRadius: 4,
                      }}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="12" y1="1" x2="12" y2="23"/><line x1="17" y1="5" x2="17" y2="19"/><line x1="7" y1="5" x2="7" y2="19"/>
                      </svg>
                    </button>
                  </div>
                  <button className="coder-send-btn" onClick={handleChatSend}
                    style={{
                      padding: '4px 12px', borderRadius: 4, fontSize: 11,
                      background: 'var(--color-accent-soft)', border: '1px solid var(--color-border)',
                      color: 'var(--color-text)', cursor: 'pointer',
                    }}>
                    Ctrl+Enter
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Statusbar */}
      <div className="coder-statusbar" style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 12px', height: 24, fontSize: 11,
        background: 'var(--color-chrome)', color: 'var(--color-text-secondary)',
        borderTop: '1px solid var(--color-border)', flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ color: connected ? 'var(--color-success)' : 'var(--color-danger)' }}>
            ● {connected ? "Connected" : "Disconnected"}
          </span>
          {isDirty && <span style={{ color: 'var(--color-warning)' }}>unsaved</span>}
        </div>
        <div>
          {currentFilePath && <span>{currentFilePath.split("/").pop()}</span>}
        </div>
      </div>
    </div>
  );
}

function FolderPlus(props: { size?: number }) {
  return (
    <svg width={props.size || 12} height={props.size || 12} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-6l-2-2H5a2 2 0 0 0-2 2Z"/>
      <line x1="12" y1="12" x2="12" y2="18"/><line x1="9" y1="15" x2="15" y2="15"/>
    </svg>
  );
}
