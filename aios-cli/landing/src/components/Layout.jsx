import { Link, Outlet, useLocation } from 'react-router-dom'
import WorldClock from './WorldClock'
import ElasticThread from './ElasticThread'

export default function Layout() {
  const location = useLocation()
  const isCli = location.pathname === '/cli'
  const accentColor = isCli ? '#cef563' : '#422EFF'

  return (
    <div style={{ '--accent-color': accentColor, minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Elastic Canvas Thread follower across landing */}
      <ElasticThread color={accentColor} />

      {/* Global Header */}
      <header
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          padding: '1.2rem 2rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          zIndex: 100,
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          backgroundColor: 'rgba(11, 13, 19, 0.75)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span
              style={{
                display: 'inline-block',
                width: 10,
                height: 10,
                backgroundColor: accentColor,
                borderRadius: isCli ? 0 : '50%',
                boxShadow: `0 0 12px ${accentColor}`,
              }}
            />
            <span style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', letterSpacing: '-0.02em', color: '#fff' }}>
              AIOS
            </span>
            <span style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.15em', color: 'var(--text-muted)', border: '1px solid var(--border-color)', padding: '1px 6px', borderRadius: 3 }}>
              {isCli ? 'CLI // v0.1.0' : 'DESKTOP TAURI'}
            </span>
          </Link>

          {/* World Clock Component (dw.studio design reference) */}
          <div className="desktop-only" style={{ display: 'flex' }}>
            <WorldClock />
          </div>
        </div>

        <nav style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '12px', fontWeight: 700, letterSpacing: '0.08em' }}>
          <Link
            to="/"
            style={{
              padding: '0.4rem 1rem',
              borderRadius: 'var(--radius-sm)',
              border: !isCli ? '1px solid var(--accent-color)' : '1px solid transparent',
              color: !isCli ? '#fff' : 'var(--text-muted)',
              backgroundColor: !isCli ? 'rgba(66, 46, 255, 0.15)' : 'transparent',
              transition: 'all 0.2s',
            }}
          >
            [ TAURI DESKTOP ]
          </Link>
          <Link
            to="/cli"
            style={{
              padding: '0.4rem 1rem',
              borderRadius: 'var(--radius-sm)',
              border: isCli ? '1px solid var(--accent-color)' : '1px solid transparent',
              color: isCli ? '#fff' : 'var(--text-muted)',
              backgroundColor: isCli ? 'rgba(206, 245, 99, 0.15)' : 'transparent',
              transition: 'all 0.2s',
            }}
          >
            [ CYBER CLI ]
          </Link>
        </nav>
      </header>

      {/* Main Page View */}
      <main style={{ flex: 1 }}>
        <Outlet />
      </main>

      {/* Global Footer (2026 Editorial Layout) */}
      <footer
        style={{
          paddingBlock: 'var(--sp)',
          borderTop: '1px solid var(--border-color)',
          backgroundColor: 'rgba(0,0,0,0.4)',
        }}
      >
        <div className="container" style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: '2rem' }}>
          <div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '2.5rem', marginBottom: '0.5rem' }}>
              AIOS OS
            </div>
            <p style={{ maxWidth: '400px', fontSize: '0.85rem' }}>
              Next-generation autonomous AI system. Built in Python & Rust with native local tools, FTS5 long-term memory, and Tauri GUI.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '3rem', fontSize: '0.85rem' }}>
            <div>
              <div style={{ color: 'var(--text-color)', fontWeight: 700, marginBottom: '0.8rem', textTransform: 'uppercase' }}>
                ARCHITECTURE
              </div>
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.4rem', color: 'var(--text-muted)' }}>
                <li>• Intent Classifier</li>
                <li>• Tool Registry & MCP</li>
                <li>• SQLite FTS5 Memory</li>
                <li>• Tauri 2.0 / Rust IPC</li>
              </ul>
            </div>

            <div>
              <div style={{ color: 'var(--text-color)', fontWeight: 700, marginBottom: '0.8rem', textTransform: 'uppercase' }}>
                RESOURCES
              </div>
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                <li>
                  <a href="https://github.com/t1m0nch1k/RedPandaCLI" target="_blank" rel="noreferrer" style={{ color: 'var(--accent-color)' }}>
                    GITHUB REPOSITORY ↗
                  </a>
                </li>
                <li>
                  <Link to="/cli" style={{ color: 'var(--text-muted)' }}>
                    CLI COMMANDS
                  </Link>
                </li>
                <li>
                  <Link to="/" style={{ color: 'var(--text-muted)' }}>
                    DESKTOP BUILD
                  </Link>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div className="container" style={{ marginTop: '3rem', paddingTop: '1.5rem', borderTop: '1px solid rgba(255,255,255,0.04)', display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)' }}>
          <span>© 2026 AIOS OS. ALL RIGHTS RESERVED. NO AI-BLANDNESS.</span>
          <span>CRAFTED WITH TAURI, RUST & PYTHON</span>
        </div>
      </footer>
    </div>
  )
}
