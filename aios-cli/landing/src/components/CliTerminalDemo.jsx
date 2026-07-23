import { useState } from 'react'

const DEMO_COMMANDS = [
  {
    cmd: 'aios intent "git commit -m fix login error"',
    output: [
      '⚡ [INTENT_ENGINE] Intent classified in 0.004s',
      '↳ Type: NATIVE_COMMAND',
      '↳ Action: git_commit',
      '↳ Risk Level: LOW',
      '✔ Executed directly without LLM API call (Saved 1,200 tokens)',
    ],
  },
  {
    cmd: 'aios chat "Refactor server.py using async pattern"',
    output: [
      '🧠 [AIOS_CORE] Reading src/aios/desktop/server.py...',
      '↳ Analysis: 465 lines loaded into context window',
      '↳ Executing code patch via multi_replace_file_content...',
      '✔ Changes applied & validated with pytest (12/12 passed)',
    ],
  },
  {
    cmd: 'aios mcp list',
    output: [
      '🔌 [MCP_REGISTRY] Connected servers (2):',
      '  • talk-to-figma (14 tools) [CONNECTED via stdio]',
      '  • github-mcp (8 tools) [CONNECTED via stdio]',
      '↳ Total active tools: 38 registered',
    ],
  },
  {
    cmd: 'aios memory search "database schema"',
    output: [
      '💾 [LONG_TERM_MEMORY] FTS5 SQLite query: "database schema"',
      '↳ Match #1: "User table uses bcrypt for password hashing" (score: 0.94)',
      '↳ Match #2: "FTS5 virtual table activated in memory.py" (score: 0.88)',
    ],
  },
]

export default function CliTerminalDemo() {
  const [activeTab, setActiveTab] = useState(0)

  return (
    <div
      style={{
        backgroundColor: '#050608',
        border: '1px solid var(--accent-color)',
        boxShadow: '8px 8px 0px rgba(206, 245, 99, 0.2)',
        borderRadius: '4px',
        overflow: 'hidden',
        fontFamily: 'var(--font-mono)',
      }}
    >
      {/* Terminal Titlebar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '0.6rem 1rem',
          backgroundColor: '#0e1117',
          borderBottom: '1px solid rgba(206, 245, 99, 0.3)',
          fontSize: '11px',
        }}
      >
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#ff5f56' }} />
          <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#ffbd2e' }} />
          <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#27c93f' }} />
          <span style={{ marginLeft: '0.5rem', color: 'var(--text-muted)' }}>bash - aios-cli tty1</span>
        </div>
        <span style={{ color: 'var(--accent-color)', fontWeight: 700 }}>[ CYBER_TTY ]</span>
      </div>

      {/* Demo Tab Selector */}
      <div
        style={{
          display: 'flex',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          backgroundColor: '#090b0f',
          overflowX: 'auto',
        }}
      >
        {DEMO_COMMANDS.map((demo, idx) => (
          <button
            key={idx}
            onClick={() => setActiveTab(idx)}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: activeTab === idx ? 'rgba(206, 245, 99, 0.15)' : 'transparent',
              color: activeTab === idx ? 'var(--accent-color)' : 'var(--text-muted)',
              border: 'none',
              borderBottom: activeTab === idx ? '2px solid var(--accent-color)' : '2px solid transparent',
              fontSize: '12px',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              fontFamily: 'inherit',
            }}
          >
            Tab {idx + 1}: {demo.cmd.split(' ')[1]}
          </button>
        ))}
      </div>

      {/* Terminal Content Body */}
      <div style={{ padding: '1.5rem', minHeight: '220px', fontSize: '13px', lineHeight: 1.7, color: '#e0e0e0' }}>
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', color: 'var(--accent-color)' }}>
          <span style={{ fontWeight: 700 }}>user@antigravity:~$</span>
          <span style={{ color: '#fff' }}>{DEMO_COMMANDS[activeTab].cmd}</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          {DEMO_COMMANDS[activeTab].output.map((line, lIdx) => (
            <div
              key={lIdx}
              style={{
                color: line.startsWith('✔')
                  ? 'var(--accent-color)'
                  : line.startsWith('⚡') || line.startsWith('🔌') || line.startsWith('🧠') || line.startsWith('💾')
                  ? '#fff'
                  : 'var(--text-muted)',
              }}
            >
              {line}
            </div>
          ))}
        </div>

        <div style={{ marginTop: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--accent-color)' }}>
          <span>user@antigravity:~$</span>
          <span style={{ width: 8, height: 16, backgroundColor: 'var(--accent-color)', display: 'inline-block', animation: 'blink 1s infinite' }} />
        </div>
      </div>
    </div>
  )
}
