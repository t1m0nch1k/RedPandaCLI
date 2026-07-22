import { useState, useEffect, useCallback } from "react";
import type { ToolMetadata, ProviderConfig, McpServer } from "../types";

interface SettingsData {
  [key: string]: unknown;
}

interface Props {
  settings: SettingsData;
  onSave: (section: string, values: Record<string, unknown>) => void;
  getSystemStatus: () => void;
  systemStatus: Record<string, unknown> | null;
  tools?: ToolMetadata[];
  ollamaModels?: string[];
  refreshOllamaModels?: () => void;
  ollamaModelsError?: string;
  themeId?: string;
  onThemeChange?: (themeId: string) => void;
}

type SettingsTab = "general" | "llm" | "voice" | "vision" | "security" | "tools" | "providers" | "mcp" | "sites" | "about";

const TABS: { key: SettingsTab; label: string }[] = [
  { key: "general", label: "General" },
  { key: "llm", label: "LLM" },
  { key: "providers", label: "Providers" },
  { key: "mcp", label: "MCP Servers" },
  { key: "voice", label: "Voice" },
  { key: "vision", label: "Vision" },
  { key: "security", label: "Security" },
  { key: "tools", label: "Tools" },
  { key: "sites", label: "Sites" },
  { key: "about", label: "About" },
];

function inputStyle(wide = false): Record<string, string | number> {
  return {
    width: wide ? "100%" : 280,
    padding: "6px 10px",
    borderRadius: 6,
    border: "1px solid #333",
    background: "#1a1a2e",
    color: "#e0e0e0",
    fontSize: 13,
    outline: "none",
    boxSizing: "border-box" as const,
  };
}

function labelStyle(): Record<string, string | number> {
  return {
    fontSize: 12,
    color: "#888",
    marginBottom: 4,
    display: "block",
  };
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: "#ccc", marginBottom: 10 }}>{title}</div>
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <label style={labelStyle()}>{label}</label>
      {children}
    </div>
  );
}

export default function SettingsPanel({
  settings,
  onSave,
  getSystemStatus,
  systemStatus,
  tools,
  ollamaModels = [],
  refreshOllamaModels,
  ollamaModelsError,
  themeId,
  onThemeChange,
}: Props) {
  const [activeTab, setActiveTab] = useState<SettingsTab>("general");
  const [dirty, setDirty] = useState(false);

  // General form
  const ipcSection = (settings["ipc"] as Record<string, unknown>) || {};
  const [ipcHost, setIpcHost] = useState(String(ipcSection["host"] || ""));
  const [ipcPort, setIpcPort] = useState(String(ipcSection["port"] || ""));
  const toolsSection = (settings["tools"] as Record<string, unknown>) || {};
  const [workingDir, setWorkingDir] = useState(String(toolsSection["working_dir"] || ""));
  const hotkeysSection = (settings["hotkeys"] as Record<string, unknown>) || {};
  const [hkMainWindow, setHkMainWindow] = useState(String(hotkeysSection["main_window"] || "ctrl+alt+space"));
  const [hkOverlay, setHkOverlay] = useState(String(hotkeysSection["overlay"] || "alt+space"));
  const knowledgeSection = (settings["knowledge"] as Record<string, unknown>) || {};
  const [kbDbPath, setKbDbPath] = useState(String(knowledgeSection["db_path"] || ""));
  const memorySection = (settings["memory"] as Record<string, unknown>) || {};
  const [memDbPath, setMemDbPath] = useState(String(memorySection["db_path"] || ""));

  // LLM form
  const llmSection = (settings["llm"] as Record<string, unknown>) || {};
  const [llmProvider, setLlmProvider] = useState(String(llmSection["provider"] || ""));
  const [llmBaseUrl, setLlmBaseUrl] = useState(String(llmSection["base_url"] || ""));
  const [llmModel, setLlmModel] = useState(String(llmSection["model"] || ""));

  // Voice form
  const voiceSection = (settings["voice"] as Record<string, unknown>) || {};
  const sttSection = (voiceSection["stt"] as Record<string, unknown>) || {};
  const [sttModel, setSttModel] = useState(String(sttSection["model_size"] || ""));
  const [sttLang, setSttLang] = useState(String(sttSection["language"] || ""));
  const [sttDevice, setSttDevice] = useState(String(sttSection["device"] || ""));

  // Vision form
  const visionSection = (settings["vision"] as Record<string, unknown>) || {};
  const [visionOcr, setVisionOcr] = useState(Boolean(visionSection["enable_ocr"]));

  // Sites form
  const siteSearchSection = (settings["site_search"] as Record<string, unknown>) || {};
  const [defaultEngine, setDefaultEngine] = useState(String(siteSearchSection["default_engine"] || "google"));

  // Security form
  const securitySection = (settings["security"] as Record<string, unknown>) || {};
  const [confirmActions, setConfirmActions] = useState(
    ((securitySection["confirm_actions"] as string[]) || []).join(", ")
  );

  // Tools permissions
  const confirmActionSet = new Set(
    ((securitySection["confirm_actions"] as string[]) || []).map((s: string) => s.toLowerCase())
  );
  const [toolPermissions, setToolPermissions] = useState<Record<string, boolean>>(
    Object.fromEntries(
      (tools || []).map((t) => [t.name, confirmActionSet.has(t.name.toLowerCase())])
    )
  );

  // Providers
  const providersSection = (settings["providers"] as ProviderConfig[]) || [];
  const [providers, setProviders] = useState<ProviderConfig[]>(providersSection.length > 0
    ? providersSection
    : [
        { id: "default-ollama", name: "Ollama", api: "openai", baseUrl: "http://127.0.0.1:11434", models: [] },
        { id: "default-openai", name: "OpenAI", api: "openai", baseUrl: "https://api.openai.com/v1", models: [] },
        { id: "default-anthropic", name: "Anthropic", api: "anthropic", baseUrl: "https://api.anthropic.com", models: [] },
      ]
  );
  const [editingProvider, setEditingProvider] = useState<ProviderConfig | null>(null);
  const [showProviderForm, setShowProviderForm] = useState(false);

  // MCP Servers
  const mcpSection = (settings["mcp_servers"] as McpServer[]) || [];
  const [mcpServers, setMcpServers] = useState<McpServer[]>(mcpSection);
  const [editingMcp, setEditingMcp] = useState<McpServer | null>(null);
  const [showMcpForm, setShowMcpForm] = useState(false);

  useEffect(() => {
    if (activeTab === "about") {
      getSystemStatus();
    }
  }, [activeTab, getSystemStatus]);

  const resetFromSettings = useCallback(() => {
    const ipc = (settings["ipc"] as Record<string, unknown>) || {};
    setIpcHost(String(ipc["host"] || ""));
    setIpcPort(String(ipc["port"] || ""));

    const tc = (settings["tools"] as Record<string, unknown>) || {};
    setWorkingDir(String(tc["working_dir"] || ""));

    const llm = (settings["llm"] as Record<string, unknown>) || {};
    setLlmProvider(String(llm["provider"] || ""));
    setLlmBaseUrl(String(llm["base_url"] || ""));
    setLlmModel(String(llm["model"] || ""));

    const voice = (settings["voice"] as Record<string, unknown>) || {};
    const stt = (voice["stt"] as Record<string, unknown>) || {};
    setSttModel(String(stt["model_size"] || ""));
    setSttLang(String(stt["language"] || ""));
    setSttDevice(String(stt["device"] || ""));

    const vision = (settings["vision"] as Record<string, unknown>) || {};
    setVisionOcr(Boolean(vision["enable_ocr"]));

    const sec = (settings["security"] as Record<string, unknown>) || {};
    setConfirmActions(((sec["confirm_actions"] as string[]) || []).join(", "));

    const hk = (settings["hotkeys"] as Record<string, unknown>) || {};
    setHkMainWindow(String(hk["main_window"] || "ctrl+alt+space"));
    setHkOverlay(String(hk["overlay"] || "alt+space"));

    const kb = (settings["knowledge"] as Record<string, unknown>) || {};
    setKbDbPath(String(kb["db_path"] || ""));

    const mem = (settings["memory"] as Record<string, unknown>) || {};
    setMemDbPath(String(mem["db_path"] || ""));

    const ss = (settings["site_search"] as Record<string, unknown>) || {};
    setDefaultEngine(String(ss["default_engine"] || "google"));

    const prov = (settings["providers"] as ProviderConfig[]) || [];
    setProviders(prov.length > 0 ? prov : [
      { id: "default-ollama", name: "Ollama", api: "openai", baseUrl: "http://127.0.0.1:11434", models: [] },
      { id: "default-openai", name: "OpenAI", api: "openai", baseUrl: "https://api.openai.com/v1", models: [] },
      { id: "default-anthropic", name: "Anthropic", api: "anthropic", baseUrl: "https://api.anthropic.com", models: [] },
    ]);

    const mcp = (settings["mcp_servers"] as McpServer[]) || [];
    setMcpServers(mcp);
  }, [settings]);

  useEffect(() => {
    resetFromSettings();
  }, [settings, resetFromSettings]);

  const handleSave = (section: string, values: Record<string, unknown>) => {
    onSave(section, values);
    setDirty(false);
  };

  const renderGeneralTab = () => (
    <div>
      <Section title="IPC Server">
        <Field label="Host">
          <input
            value={ipcHost}
            onChange={(e) => { setIpcHost(e.target.value); setDirty(true); }}
            placeholder="127.0.0.1"
            style={inputStyle()}
          />
        </Field>
        <Field label="Port">
          <input
            value={ipcPort}
            onChange={(e) => { setIpcPort(e.target.value); setDirty(true); }}
            placeholder="8765"
            style={inputStyle()}
          />
        </Field>
      </Section>
      <Section title="File Tools">
        <Field label="Working Directory">
          <input
            value={workingDir}
            onChange={(e) => { setWorkingDir(e.target.value); setDirty(true); }}
            placeholder="(no restriction)"
            style={inputStyle(true)}
          />
          <div style={{ fontSize: 11, color: "#666", marginTop: 4 }}>
            Restrict file read/write/list to this directory. Leave empty for no restriction.
          </div>
        </Field>
      </Section>
      <Section title="Global Hotkeys">
        <Field label="Focus Window">
          <input
            value={hkMainWindow}
            onChange={(e) => { setHkMainWindow(e.target.value); setDirty(true); }}
            placeholder="ctrl+alt+space"
            style={inputStyle()}
          />
          <div style={{ fontSize: 11, color: "#666", marginTop: 4 }}>
            Hotkey to focus/show the main AIOS window.
          </div>
        </Field>
        <Field label="Overlay (Screenshot)">
          <input
            value={hkOverlay}
            onChange={(e) => { setHkOverlay(e.target.value); setDirty(true); }}
            placeholder="alt+space"
            style={inputStyle()}
          />
          <div style={{ fontSize: 11, color: "#666", marginTop: 4 }}>
            Hotkey to capture screen and show overlay.
          </div>
        </Field>
      </Section>
      <Section title="Knowledge Base">
        <Field label="Database Path">
          <input
            value={kbDbPath}
            onChange={(e) => { setKbDbPath(e.target.value); setDirty(true); }}
            placeholder="(default: data/aios_knowledge.db)"
            style={inputStyle(true)}
          />
        </Field>
      </Section>
      <Section title="Memory">
        <Field label="Database Path">
          <input
            value={memDbPath}
            onChange={(e) => { setMemDbPath(e.target.value); setDirty(true); }}
            placeholder="(default: data/aios_memory.db)"
            style={inputStyle(true)}
          />
        </Field>
      </Section>
      {onThemeChange && (
        <Section title="Appearance">
          <Field label="Theme">
            <select
              value={themeId || "aios-dark"}
              onChange={(e) => { onThemeChange(e.target.value); setDirty(true); }}
              style={inputStyle()}
            >
              <option value="aios-dark">AIOS Dark</option>
              <option value="aios-light">AIOS Light</option>
              <option value="cyberpunk">Cyberpunk</option>
              <option value="minimal">Minimal</option>
              <option value="fox">Fox</option>
              <option value="github-dark">GitHub Dark</option>
              <option value="monokai-pro">Monokai Pro</option>
              <option value="tokyo-night">Tokyo Night</option>
              <option value="catppuccin">Catppuccin Mocha</option>
              <option value="nord">Nord</option>
              <option value="dracula">Dracula</option>
              <option value="solarized-dark">Solarized Dark</option>
            </select>
          </Field>
        </Section>
      )}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button
          onClick={() => handleSave("ipc", { host: ipcHost, port: parseInt(ipcPort, 10) || 8765 })}
          style={saveBtnStyle()}
        >
          Save IPC
        </button>
        <button
          onClick={() => handleSave("hotkeys", { main_window: hkMainWindow, overlay: hkOverlay })}
          style={saveBtnStyle()}
        >
          Save Hotkeys
        </button>
        <button
          onClick={() => handleSave("knowledge", { db_path: kbDbPath })}
          style={saveBtnStyle()}
        >
          Save Knowledge
        </button>
        <button
          onClick={() => handleSave("memory", { db_path: memDbPath })}
          style={saveBtnStyle()}
        >
          Save Memory
        </button>
      </div>
    </div>
  );

  const renderLlmTab = () => (
    <div>
      <Section title="Model Provider">
        <Field label="Provider">
          <select
            value={llmProvider}
            onChange={(e) => { setLlmProvider(e.target.value); setDirty(true); }}
            style={inputStyle()}
          >
            <option value="ollama">Ollama</option>
            <option value="openai">OpenAI</option>
          </select>
        </Field>
        <Field label="Base URL">
          <input
            value={llmBaseUrl}
            onChange={(e) => { setLlmBaseUrl(e.target.value); setDirty(true); }}
            placeholder="http://127.0.0.1:11434"
            style={inputStyle()}
          />
        </Field>
        <Field label="Model">
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <select
              value={llmModel}
              onChange={(e) => { setLlmModel(e.target.value); setDirty(true); }}
              style={inputStyle()}
            >
              {llmModel && !ollamaModels.includes(llmModel) && (
                <option value={llmModel}>{llmModel}</option>
              )}
              {ollamaModels.length === 0 && <option value={llmModel}>{llmModel || "No models found"}</option>}
              {ollamaModels.map((model) => (
                <option key={model} value={model}>{model}</option>
              ))}
            </select>
            <button
              type="button"
              onClick={refreshOllamaModels}
              style={{ ...saveBtnStyle(), padding: "6px 12px", background: "#2a2a3e" }}
            >
              Refresh
            </button>
          </div>
          {ollamaModelsError && (
            <div style={{ fontSize: 11, color: "#f87171", marginTop: 4 }}>{ollamaModelsError}</div>
          )}
          {!ollamaModelsError && ollamaModels.length > 0 && (
            <div style={{ fontSize: 11, color: "#666", marginTop: 4 }}>
              Detected {ollamaModels.length} local Ollama model(s).
            </div>
          )}
        </Field>
      </Section>
      <button onClick={() => handleSave("llm", { provider: llmProvider, base_url: llmBaseUrl, model: llmModel })} style={saveBtnStyle()}>
        Save LLM Settings
      </button>
    </div>
  );

  const renderVoiceTab = () => (
    <div>
      <Section title="Speech-to-Text (Whisper)">
        <Field label="Model Size">
          <select
            value={sttModel}
            onChange={(e) => { setSttModel(e.target.value); setDirty(true); }}
            style={inputStyle()}
          >
            <option value="tiny">tiny</option>
            <option value="base">base</option>
            <option value="small">small</option>
            <option value="medium">medium</option>
            <option value="large">large</option>
          </select>
        </Field>
        <Field label="Language">
          <input
            value={sttLang}
            onChange={(e) => { setSttLang(e.target.value); setDirty(true); }}
            placeholder="ru"
            style={inputStyle()}
          />
        </Field>
        <Field label="Device">
          <select
            value={sttDevice}
            onChange={(e) => { setSttDevice(e.target.value); setDirty(true); }}
            style={inputStyle()}
          >
            <option value="auto">auto</option>
            <option value="cpu">cpu</option>
            <option value="cuda">cuda</option>
          </select>
        </Field>
      </Section>
      <button onClick={() => handleSave("voice", { stt: { model_size: sttModel, language: sttLang, device: sttDevice } })} style={saveBtnStyle()}>
        Save Voice Settings
      </button>
    </div>
  );

  const renderVisionTab = () => (
    <div>
      <Section title="Screen Analysis">
        <Field label="Enable OCR">
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", color: "#ccc", fontSize: 13 }}>
            <input
              type="checkbox"
              checked={visionOcr}
              onChange={(e) => { setVisionOcr(e.target.checked); setDirty(true); }}
              style={{ accentColor: "#4361ee" }}
            />
            Enable text recognition in screen captures
          </label>
        </Field>
      </Section>
      <button onClick={() => handleSave("vision", { enable_ocr: visionOcr })} style={saveBtnStyle()}>
        Save Vision Settings
      </button>
    </div>
  );

  const renderSecurityTab = () => (
    <div>
      <Section title="Action Confirmation">
        <Field label="Confirm Actions">
          <input
            value={confirmActions}
            onChange={(e) => { setConfirmActions(e.target.value); setDirty(true); }}
            placeholder="terminal_exec, close_app"
            style={inputStyle(true)}
          />
          <div style={{ fontSize: 11, color: "#666", marginTop: 4 }}>
            Comma-separated list of action names that require confirmation before execution.
          </div>
        </Field>
      </Section>
      <button onClick={() => handleSave("security", { confirm_actions: confirmActions.split(",").map((s) => s.trim()).filter(Boolean) })} style={saveBtnStyle()}>
        Save Security Settings
      </button>
    </div>
  );

  const renderToolsTab = () => {
    const riskyTools = (tools || []).filter((t) => t.risky);
    const safeTools = (tools || []).filter((t) => !t.risky);

    const toggleTool = (name: string) => {
      setToolPermissions((prev) => ({ ...prev, [name]: !prev[name] }));
      setDirty(true);
    };

    const savePermissions = () => {
      const confirmList = Object.entries(toolPermissions)
        .filter(([, needsConfirm]) => needsConfirm)
        .map(([name]) => name);
      handleSave("security", { confirm_actions: confirmList });
    };

    return (
      <div>
        <Section title="Tool Permissions">
          <div style={{ fontSize: 12, color: "#888", marginBottom: 10 }}>
            Toggle confirmation requirement for each tool. Risky tools require confirmation by default.
          </div>
          {riskyTools.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "#f87171", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.3px" }}>
                Risky Tools
              </div>
              {riskyTools.map((t) => (
                <label
                  key={t.name}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "4px 0",
                    cursor: "pointer",
                    fontSize: 13,
                    color: "#ccc",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={toolPermissions[t.name] ?? true}
                    onChange={() => toggleTool(t.name)}
                    style={{ accentColor: "#4361ee" }}
                  />
                  <span style={{ flex: 1 }}>{t.name}</span>
                  <span style={{ fontSize: 11, color: "#666" }}>{t.description}</span>
                </label>
              ))}
            </div>
          )}
          {safeTools.length > 0 && (
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: "#34d399", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.3px" }}>
                Safe Tools
              </div>
              {safeTools.map((t) => (
                <label
                  key={t.name}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "4px 0",
                    cursor: "pointer",
                    fontSize: 13,
                    color: "#ccc",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={toolPermissions[t.name] ?? false}
                    onChange={() => toggleTool(t.name)}
                    style={{ accentColor: "#4361ee" }}
                  />
                  <span style={{ flex: 1 }}>{t.name}</span>
                  <span style={{ fontSize: 11, color: "#666" }}>{t.description}</span>
                </label>
              ))}
            </div>
          )}
        </Section>
        <button onClick={savePermissions} style={saveBtnStyle()}>
          Save Tool Permissions
        </button>
      </div>
    );
  };

  const renderSitesTab = () => (
    <div>
      <Section title="Search Engine">
        <Field label="Default engine">
          <select
            value={defaultEngine}
            onChange={(e) => { setDefaultEngine(e.target.value); setDirty(true); }}
            style={inputStyle()}
          >
            {["google", "duckduckgo", "yandex", "bing"].map((e) => (
              <option key={e} value={e}>{e}</option>
            ))}
          </select>
        </Field>
        <button onClick={() => handleSave("site_search", {
          default_engine: defaultEngine,
          engines: (siteSearchSection["engines"] as Record<string, string>) || {},
        })} style={saveBtnStyle()}>
          Save Site Settings
        </button>
      </Section>
    </div>
  );

  const renderProvidersTab = () => {
    const addOrEditProvider = () => {
      if (!editingProvider) return;
      const exists = providers.find((p) => p.id === editingProvider.id);
      if (exists) {
        setProviders((prev) => prev.map((p) => p.id === editingProvider.id ? editingProvider : p));
      } else {
        setProviders((prev) => [...prev, editingProvider]);
      }
      setShowProviderForm(false);
      setEditingProvider(null);
      setDirty(true);
    };

    const removeProvider = (id: string) => {
      setProviders((prev) => prev.filter((p) => p.id !== id));
      setDirty(true);
    };

    const openNewProvider = () => {
      setEditingProvider({ id: `prov-${Date.now()}`, name: "", api: "openai", baseUrl: "", models: [] });
      setShowProviderForm(true);
    };

    const openEditProvider = (p: ProviderConfig) => {
      setEditingProvider({ ...p });
      setShowProviderForm(true);
    };

    return (
      <div>
        <Section title="LLM Providers">
          <div style={{ fontSize: 12, color: "#888", marginBottom: 10 }}>
            Manage API providers for LLM access. You can add OpenAI-compatible, Anthropic, or custom endpoints.
          </div>
          {providers.map((p) => (
            <div key={p.id} style={{
              display: "flex", alignItems: "center", gap: 8,
              padding: "8px 10px", marginBottom: 6,
              borderRadius: 6, background: "#1a1a2e", border: "1px solid #2a2a3e"
            }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, color: "#e0e0e0", fontWeight: 600 }}>{p.name}</div>
                <div style={{ fontSize: 11, color: "#888", marginTop: 2 }}>
                  {p.api} &middot; {p.baseUrl} &middot; {p.models.length} model(s)
                </div>
              </div>
              <button onClick={() => openEditProvider(p)} style={iconBtnStyle()} title="Edit">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </button>
              <button onClick={() => removeProvider(p.id)} style={{ ...iconBtnStyle(), color: "#f87171" }} title="Remove">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              </button>
            </div>
          ))}
          <button onClick={openNewProvider} style={{ ...saveBtnStyle(), background: "#2a2a3e", marginTop: 4 }}>
            + Add Provider
          </button>
        </Section>

        {showProviderForm && editingProvider && (
          <Section title={providers.find((p) => p.id === editingProvider.id) ? "Edit Provider" : "New Provider"}>
            <Field label="Name">
              <input value={editingProvider.name} onChange={(e) => setEditingProvider({ ...editingProvider, name: e.target.value })} placeholder="My Provider" style={inputStyle()} />
            </Field>
            <Field label="API Type">
              <select value={editingProvider.api} onChange={(e) => setEditingProvider({ ...editingProvider, api: e.target.value as ProviderConfig["api"] })} style={inputStyle()}>
                <option value="openai">OpenAI-compatible</option>
                <option value="anthropic">Anthropic</option>
                <option value="gemini">Google Gemini</option>
                <option value="custom">Custom</option>
              </select>
            </Field>
            <Field label="Base URL">
              <input value={editingProvider.baseUrl} onChange={(e) => setEditingProvider({ ...editingProvider, baseUrl: e.target.value })} placeholder="https://api.openai.com/v1" style={inputStyle(true)} />
            </Field>
            <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
              <button onClick={addOrEditProvider} style={saveBtnStyle()}>
                {providers.find((p) => p.id === editingProvider.id) ? "Update" : "Add"}
              </button>
              <button onClick={() => { setShowProviderForm(false); setEditingProvider(null); }} style={{ ...saveBtnStyle(), background: "#333" }}>
                Cancel
              </button>
            </div>
          </Section>
        )}

        {providers.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <button onClick={() => onSave("providers", { providers: providers as unknown as Record<string, unknown>[] })} style={saveBtnStyle()}>
              Save All Providers
            </button>
          </div>
        )}
      </div>
    );
  };

  const renderMcpTab = () => {
    const addOrEditMcp = () => {
      if (!editingMcp) return;
      const exists = mcpServers.find((s) => s.id === editingMcp.id);
      if (exists) {
        setMcpServers((prev) => prev.map((s) => s.id === editingMcp.id ? editingMcp : s));
      } else {
        setMcpServers((prev) => [...prev, editingMcp]);
      }
      setShowMcpForm(false);
      setEditingMcp(null);
      setDirty(true);
    };

    const removeMcp = (id: string) => {
      setMcpServers((prev) => prev.filter((s) => s.id !== id));
      setDirty(true);
    };

    const toggleMcp = (id: string) => {
      setMcpServers((prev) => prev.map((s) => s.id === id ? { ...s, enabled: !s.enabled } : s));
      setDirty(true);
    };

    const openNewMcp = () => {
      setEditingMcp({ id: `mcp-${Date.now()}`, name: "", transport: "stdio", enabled: true, command: "", args: [] });
      setShowMcpForm(true);
    };

    const openEditMcp = (s: McpServer) => {
      setEditingMcp({ ...s });
      setShowMcpForm(true);
    };

    return (
      <div>
        <Section title="MCP Servers">
          <div style={{ fontSize: 12, color: "#888", marginBottom: 10 }}>
            Model Context Protocol servers provide extra tools and capabilities to the AI.
          </div>
          {mcpServers.length === 0 && (
            <div style={{ fontSize: 13, color: "#666", padding: "12px 0" }}>
              No MCP servers configured. Add one to extend AI capabilities.
            </div>
          )}
          {mcpServers.map((s) => (
            <div key={s.id} style={{
              display: "flex", alignItems: "center", gap: 8,
              padding: "8px 10px", marginBottom: 6,
              borderRadius: 6, background: "#1a1a2e", border: "1px solid #2a2a3e"
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, flex: 1, minWidth: 0 }}>
                <input
                  type="checkbox"
                  checked={s.enabled}
                  onChange={() => toggleMcp(s.id)}
                  style={{ accentColor: "#4361ee", flexShrink: 0 }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, color: "#e0e0e0", fontWeight: 600 }}>{s.name}</div>
                  <div style={{ fontSize: 11, color: "#888", marginTop: 2 }}>
                    {s.transport}
                    {s.transport === "stdio" && s.command ? ` \u00b7 ${s.command}` : ""}
                    {s.url ? ` \u00b7 ${s.url}` : ""}
                  </div>
                </div>
              </div>
              <button onClick={() => openEditMcp(s)} style={iconBtnStyle()} title="Edit">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </button>
              <button onClick={() => removeMcp(s.id)} style={{ ...iconBtnStyle(), color: "#f87171" }} title="Remove">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              </button>
            </div>
          ))}
          <button onClick={openNewMcp} style={{ ...saveBtnStyle(), background: "#2a2a3e", marginTop: 4 }}>
            + Add MCP Server
          </button>
        </Section>

        {showMcpForm && editingMcp && (
          <Section title={mcpServers.find((s) => s.id === editingMcp.id) ? "Edit MCP Server" : "New MCP Server"}>
            <Field label="Name">
              <input value={editingMcp.name} onChange={(e) => setEditingMcp({ ...editingMcp, name: e.target.value })} placeholder="My MCP Server" style={inputStyle()} />
            </Field>
            <Field label="Transport">
              <select value={editingMcp.transport} onChange={(e) => setEditingMcp({ ...editingMcp, transport: e.target.value as McpServer["transport"] })} style={inputStyle()}>
                <option value="stdio">STDIO</option>
                <option value="http">HTTP</option>
                <option value="sse">SSE</option>
              </select>
            </Field>
            {editingMcp.transport === "stdio" && (
              <>
                <Field label="Command">
                  <input value={editingMcp.command || ""} onChange={(e) => setEditingMcp({ ...editingMcp, command: e.target.value })} placeholder="npx" style={inputStyle(true)} />
                </Field>
                <Field label="Arguments">
                  <input
                    value={(editingMcp.args || []).join(" ")}
                    onChange={(e) => setEditingMcp({ ...editingMcp, args: e.target.value.split(" ").filter(Boolean) })}
                    placeholder="-m my_mcp_server --port 3000"
                    style={inputStyle(true)}
                  />
                </Field>
              </>
            )}
            {editingMcp.transport !== "stdio" && (
              <Field label="URL">
                <input value={editingMcp.url || ""} onChange={(e) => setEditingMcp({ ...editingMcp, url: e.target.value })} placeholder="http://localhost:3000" style={inputStyle(true)} />
              </Field>
            )}
            <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
              <button onClick={addOrEditMcp} style={saveBtnStyle()}>
                {mcpServers.find((s) => s.id === editingMcp.id) ? "Update" : "Add"}
              </button>
              <button onClick={() => { setShowMcpForm(false); setEditingMcp(null); }} style={{ ...saveBtnStyle(), background: "#333" }}>
                Cancel
              </button>
            </div>
          </Section>
        )}

        {mcpServers.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <button onClick={() => onSave("mcp_servers", { mcp_servers: mcpServers as unknown as Record<string, unknown>[] })} style={saveBtnStyle()}>
              Save All MCP Servers
            </button>
          </div>
        )}
      </div>
    );
  };

  const renderAboutTab = () => (
    <div>
      <Section title="System Status">
        {systemStatus ? (
          <div style={{ fontSize: 13, lineHeight: 1.6 }}>
            {Object.entries(systemStatus).map(([key, val]) => (
              <div key={key} style={{ display: "flex", gap: 8, padding: "2px 0" }}>
                <span style={{ color: "#888", minWidth: 100 }}>{key}</span>
                <span style={{ color: "#ccc" }}>
                  {typeof val === "object" && val !== null
                    ? JSON.stringify(val, null, 1)
                    : String(val)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: "#666", fontSize: 13 }}>Loading system status...</div>
        )}
      </Section>
      <Section title="Storage">
        <div style={{ fontSize: 13, color: "#888" }}>
          <div>Settings file: settings/default.json + local.override.json</div>
          <div style={{ marginTop: 4 }}>
            Changes are persisted to <code style={{ color: "#a78bfa" }}>settings/local.override.json</code>
          </div>
        </div>
      </Section>
    </div>
  );

  const TAB_RENDERERS: Record<SettingsTab, () => React.ReactNode> = {
    general: renderGeneralTab,
    llm: renderLlmTab,
    providers: renderProvidersTab,
    mcp: renderMcpTab,
    voice: renderVoiceTab,
    vision: renderVisionTab,
    security: renderSecurityTab,
    tools: renderToolsTab,
    sites: renderSitesTab,
    about: renderAboutTab,
  };

  return (
    <div style={{ padding: "8px 16px", height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Sub-tabs */}
      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid #2a2a3e", marginBottom: 16 }}>
        {TABS.map((tab) => (
          <div
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: "8px 14px",
              fontSize: 12,
              cursor: "pointer",
              color: activeTab === tab.key ? "#fff" : "#666",
              borderBottom: activeTab === tab.key ? "2px solid #4361ee" : "2px solid transparent",
              transition: "all 0.15s",
              textTransform: "uppercase",
              letterSpacing: "0.3px",
            }}
          >
            {tab.label}
          </div>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: "auto", paddingBottom: 16 }}>
        {TAB_RENDERERS[activeTab]()}
      </div>

      {dirty && (
        <div style={{ fontSize: 11, color: "#fbbf24", padding: "4px 0", borderTop: "1px solid #2a2a3e", marginTop: 8 }}>
          Unsaved changes
        </div>
      )}
    </div>
  );
}

function saveBtnStyle(): Record<string, string | number> {
  return {
    padding: "8px 18px",
    borderRadius: 6,
    border: "none",
    background: "#4361ee",
    color: "#fff",
    fontSize: 13,
    cursor: "pointer",
  };
}

function iconBtnStyle(): Record<string, string | number> {
  return {
    background: "none",
    border: "none",
    cursor: "pointer",
    color: "#888",
    padding: 4,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 4,
  };
}
