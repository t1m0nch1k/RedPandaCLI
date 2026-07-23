import { useState } from 'react'

export default function DesktopAppMockup() {
  const [activeTab, setActiveTab] = useState('chat')
  const [coderFile, setCoderFile] = useState('App.tsx')

  return (
    <div
      style={{
        width: '100%',
        maxWidth: '1000px',
        marginInline: 'auto',
        borderRadius: 'var(--radius-lg)',
        background: 'rgba(15, 18, 28, 0.75)',
        backdropFilter: 'blur(30px) saturate(150%)',
        WebkitBackdropFilter: 'blur(30px) saturate(150%)',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        boxShadow: '0 30px 80px rgba(0, 0, 0, 0.6), inset 0 1px 0px rgba(255, 255, 255, 0.15)',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        height: '540px',
      }}
    >
      {/* Titlebar mockup */}
      <div
        style={{
          height: '38px',
          backgroundColor: 'rgba(10, 12, 18, 0.9)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingInline: '1rem',
          fontSize: '12px',
          userSelect: 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div style={{ display: 'flex', gap: '0.4rem' }}>
            <span style={{ width: 11, height: 11, borderRadius: '50%', backgroundColor: '#ff5f56' }} />
            <span style={{ width: 11, height: 11, borderRadius: '50%', backgroundColor: '#ffbd2e' }} />
            <span style={{ width: 11, height: 11, borderRadius: '50%', backgroundColor: '#27c93f' }} />
          </div>
          <span style={{ color: 'var(--text-muted)', marginLeft: '0.5rem', fontWeight: 500 }}>AIOS Desktop — Personal Agentic Shell</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '11px', color: '#27c93f' }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: '#27c93f', display: 'inline-block' }} />
          <span>Core Connected (ws://127.0.0.1:8765)</span>
        </div>
      </div>

      {/* Main App Layout Grid */}
      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        {/* Sidebar */}
        <div
          style={{
            width: '180px',
            backgroundColor: 'rgba(8, 10, 15, 0.6)',
            borderRight: '1px solid rgba(255, 255, 255, 0.06)',
            padding: '0.75rem 0.5rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.3rem',
          }}
        >
          <button
            style={{
              padding: '0.6rem',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--accent-color)',
              backgroundColor: 'rgba(66, 46, 255, 0.2)',
              color: '#fff',
              fontSize: '12px',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.4rem',
              marginBottom: '0.5rem',
            }}
          >
            <span>+ New Chat</span>
          </button>

          {[
            { id: 'chat', label: 'Chat Engine', icon: '💬' },
            { id: 'coder', label: 'Coder & IDE', icon: '💻' },
            { id: 'tools', label: 'Registered Tools', icon: '⚡' },
            { id: 'timeline', label: 'Automations', icon: '📊' },
            { id: 'memory', label: 'FTS5 Memory', icon: '🧠' },
            { id: 'calendar', label: 'Calendar', icon: '📅' },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              style={{
                padding: '0.55rem 0.75rem',
                borderRadius: '6px',
                border: 'none',
                backgroundColor: activeTab === item.id ? 'rgba(255, 255, 255, 0.08)' : 'transparent',
                color: activeTab === item.id ? '#fff' : 'var(--text-muted)',
                fontSize: '12px',
                textAlign: 'left',
                display: 'flex',
                alignItems: 'center',
                gap: '0.6rem',
                cursor: 'pointer',
                fontFamily: 'inherit',
              }}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </div>

        {/* View Content Area */}
        <div style={{ flex: 1, backgroundColor: 'rgba(12, 14, 22, 0.4)', padding: '1.2rem', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          {activeTab === 'chat' && (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ alignSelf: 'flex-start', backgroundColor: 'rgba(255, 255, 255, 0.05)', padding: '0.75rem 1rem', borderRadius: '12px', maxWidth: '80%', fontSize: '13px' }}>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '0.3rem' }}>USER</div>
                  Analyze the codebase and prepare a desktop Tauri release build.
                </div>

                <div style={{ alignSelf: 'flex-end', backgroundColor: 'rgba(66, 46, 255, 0.25)', border: '1px solid rgba(66, 46, 255, 0.4)', padding: '0.75rem 1rem', borderRadius: '12px', maxWidth: '80%', fontSize: '13px' }}>
                  <div style={{ fontSize: '10px', color: 'rgba(255, 255, 255, 0.7)', marginBottom: '0.3rem' }}>AIOS ASSISTANT</div>
                  I found 17 modules in `aios-cli/desktop`. Compiling Rust backend via Cargo and building Vite bundle...
                </div>
              </div>

              {/* Chat Input Bar Mockup */}
              <div style={{ marginTop: 'auto', display: 'flex', gap: '0.5rem', backgroundColor: 'rgba(0,0,0,0.3)', padding: '0.6rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)' }}>
                <input
                  readOnly
                  value="Start a new task or query long-term memory..."
                  style={{ flex: 1, background: 'transparent', border: 'none', color: '#fff', fontSize: '13px', outline: 'none' }}
                />
                <button style={{ backgroundColor: 'var(--accent-color)', border: 'none', color: '#fff', padding: '0.4rem 0.8rem', borderRadius: '6px', fontSize: '11px', fontWeight: 700 }}>
                  SEND ➔
                </button>
              </div>
            </div>
          )}

          {activeTab === 'coder' && (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '0.8rem' }}>
              <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '0.4rem', fontSize: '12px' }}>
                {['App.tsx', 'server.py', 'lib.rs'].map((f) => (
                  <button
                    key={f}
                    onClick={() => setCoderFile(f)}
                    style={{
                      padding: '0.3rem 0.7rem',
                      borderRadius: '4px',
                      border: 'none',
                      backgroundColor: coderFile === f ? 'rgba(255,255,255,0.1)' : 'transparent',
                      color: coderFile === f ? '#fff' : 'var(--text-muted)',
                      fontSize: '11px',
                    }}
                  >
                    {f}
                  </button>
                ))}
              </div>

              <div style={{ flex: 1, backgroundColor: '#050609', padding: '1rem', borderRadius: '6px', fontFamily: 'var(--font-mono)', fontSize: '12px', color: '#34d399', overflow: 'hidden' }}>
                {coderFile === 'App.tsx' && (
                  <pre>{`export default function App() {\n  const [tools, setTools] = useState<ToolMetadata[]>([]);\n  const ws = useWebSocket(handleEvent, handleResponse);\n  return <TauriShell activeView="coder" />;\n}`}</pre>
                )}
                {coderFile === 'server.py' && (
                  <pre>{`class DesktopIPCServer:\n    async def _handle_jsonrpc(self, ws, raw):\n        result = await self._dispatch(ws, method, params)\n        await ws.send(json.dumps(result))`}</pre>
                )}
                {coderFile === 'lib.rs' && (
                  <pre>{`pub fn run() {\n    tauri::Builder::default()\n        .plugin(tauri_plugin_dialog::init())\n        .run(tauri::generate_context!())\n}`}</pre>
                )}
              </div>
            </div>
          )}

          {activeTab === 'tools' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-color)' }}>REGISTERED SYSTEM & MCP TOOLS (38)</div>
              {[
                { name: 'fs.read', cat: 'FILE SYSTEM', desc: 'Reads contents of local files securely.' },
                { name: 'mcp.figma.get_document', cat: 'MCP / FIGMA', desc: 'Extracts vector layer definitions from Figma REST API.' },
                { name: 'term.exec', cat: 'TERMINAL', desc: 'Executes non-blocking background commands with output streaming.' },
              ].map((t) => (
                <div key={t.name} style={{ backgroundColor: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', padding: '0.75rem 1rem', borderRadius: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 700, color: 'var(--accent-color)', fontSize: '13px' }}>{t.name}</span>
                    <span style={{ fontSize: '9px', border: '1px solid rgba(255,255,255,0.2)', padding: '1px 6px', borderRadius: '3px' }}>{t.cat}</span>
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '0.3rem' }}>{t.desc}</div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'timeline' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
              <div style={{ fontSize: '12px', fontWeight: 700 }}>AUTOMATION TIMELINE & AUDIT LOG</div>
              {[
                { time: '18:59:41', event: 'executor.step.started', status: 'SUCCESS', desc: 'Launched background process task-25 (npm run tauri dev)' },
                { time: '19:00:25', event: 'overlay.daemon.ready', status: 'INFO', desc: 'Global hotkey overlay daemon listening' },
              ].map((log, i) => (
                <div key={i} style={{ display: 'flex', gap: '1rem', fontSize: '11px', padding: '0.5rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>{log.time}</span>
                  <span style={{ color: 'var(--accent-color)', fontWeight: 700 }}>{log.event}</span>
                  <span style={{ flex: 1, color: 'var(--text-color)' }}>{log.desc}</span>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'memory' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
              <div style={{ fontSize: '12px', fontWeight: 700 }}>FTS5 LONG-TERM KNOWLEDGE BASE</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Indexed project facts and persistent user preferences:</div>
              <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.08)', fontSize: '12px' }}>
                <div>• User prefers 2026 Expressive Minimalism for Web UI</div>
                <div>• Port 8765 used for Tauri Python IPC socket</div>
                <div>• Virtual environment at .venv/Scripts/python.exe</div>
              </div>
            </div>
          )}

          {activeTab === 'calendar' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
              <div style={{ fontSize: '12px', fontWeight: 700 }}>UPCOMING SCHEDULE & AGENTIC ALARMS</div>
              <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, backgroundColor: 'rgba(66, 46, 255, 0.15)', border: '1px solid var(--accent-color)', padding: '1rem', borderRadius: '8px' }}>
                  <div style={{ fontSize: '10px', color: 'var(--accent-color)' }}>TODAY 20:00</div>
                  <div style={{ fontWeight: 700, fontSize: '13px', marginTop: '0.2rem' }}>Release AIOS Desktop 0.1.0</div>
                </div>
                <div style={{ flex: 1, backgroundColor: 'rgba(255, 255, 255, 0.03)', border: '1px solid rgba(255, 255, 255, 0.08)', padding: '1rem', borderRadius: '8px' }}>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>TOMORROW 10:00</div>
                  <div style={{ fontWeight: 700, fontSize: '13px', marginTop: '0.2rem' }}>Automated System Diagnostics</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
