import { useEffect, useState } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import SplitType from 'split-type'
import CliTerminalDemo from '../components/CliTerminalDemo'

gsap.registerPlugin(ScrollTrigger)

export default function CliLanding() {
  const [copied, setCopied] = useState(false)
  const installCmd = 'npm install -g aios-cli'

  const handleCopy = () => {
    navigator.clipboard.writeText(installCmd)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  useEffect(() => {
    // Cyberbrutalism Title Glitch / Split Reveal
    const title = new SplitType('.cli-hero-title', { types: 'chars' })
    gsap.fromTo(
      title.chars,
      { opacity: 0, scale: 1.4, filter: 'blur(12px)' },
      { opacity: 1, scale: 1, filter: 'blur(0px)', duration: 0.15, stagger: 0.03, ease: 'steps(6)' }
    )

    // Manifest line reveal via scroll scrub
    const manifest = new SplitType('.cli-manifest-text', { types: 'lines' })
    manifest.lines.forEach((line) => {
      gsap.fromTo(
        line,
        { opacity: 0.1, y: 15 },
        {
          opacity: 1,
          y: 0,
          scrollTrigger: {
            trigger: line,
            start: 'top 80%',
            end: 'bottom 60%',
            scrub: 1,
          },
        }
      )
    })

    return () => {
      title.revert()
      manifest.revert()
    }
  }, [])

  return (
    <div style={{ backgroundColor: '#07080b', color: '#f4f5f8', minHeight: '100vh', position: 'relative' }}>
      {/* Background Cyber Grid */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          backgroundImage:
            'linear-gradient(to right, rgba(206, 245, 99, 0.03) 1px, transparent 1px), linear-gradient(to bottom, rgba(206, 245, 99, 0.03) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
          pointerEvents: 'none',
          zIndex: 0,
        }}
      />

      {/* Hero Section */}
      <section className="section container" style={{ paddingTop: '140px', position: 'relative', zIndex: 1 }}>
        <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'center', marginBottom: '1.5rem' }}>
          <span className="tag-badge" style={{ borderColor: 'var(--accent-color)', color: 'var(--accent-color)' }}>
            <span className="dot" /> CYBERBRUTALISM // CLI ENGINE
          </span>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>[+] PYTHON 3.12 + RUST INTEROP</span>
        </div>

        <h1 className="cli-hero-title" style={{ color: 'var(--text-color)', marginBottom: '1rem' }}>
          AIOS <span style={{ color: 'var(--accent-color)' }}>//</span> CLI
        </h1>

        <p style={{ fontSize: 'clamp(1.1rem, 2vw, 1.6rem)', maxWidth: '680px', color: 'var(--text-color)', lineHeight: 1.4, marginBottom: '2.5rem' }}>
          {'//'} Pure hacker vibe. Zero bloat. High-speed local intent classification engine with autonomous tool orchestration.
        </p>

        {/* Copyable Quick Install Bar */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', alignItems: 'center', marginBottom: '4rem' }}>
          <div className="cyber-panel" style={{ flex: '1 1 340px', cursor: 'pointer' }} onClick={handleCopy}>
            <span style={{ color: 'var(--accent-color)', fontWeight: 700 }}>$</span>
            <span style={{ flex: 1, letterSpacing: '0.05em' }}>{installCmd}</span>
            <span style={{ fontSize: '11px', color: copied ? 'var(--accent-color)' : 'var(--text-muted)', border: '1px solid var(--border-color)', padding: '2px 8px', borderRadius: '3px' }}>
              {copied ? '✔ COPIED' : 'COPY'}
            </span>
          </div>

          <a href="https://github.com/t1m0nch1k/RedPandaCLI" target="_blank" rel="noreferrer" className="btn-secondary" style={{ borderColor: 'var(--accent-color)', color: 'var(--accent-color)' }}>
            [ VIEW ON GITHUB ↗ ]
          </a>
        </div>

        {/* Live Interactive CLI Terminal Demo */}
        <div style={{ marginTop: '2rem' }}>
          <CliTerminalDemo />
        </div>
      </section>

      {/* Manifest Section (Scrub reveal per line) */}
      <section className="section container" style={{ paddingBlock: 'clamp(4rem, 10vw, 10rem)', position: 'relative', zIndex: 1 }}>
        <div style={{ fontSize: '12px', color: 'var(--accent-color)', textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: '1.5rem' }}>
          {'{ MANIFESTO_2026 }'}
        </div>
        <h2
          className="cli-manifest-text"
          style={{
            fontSize: 'clamp(2rem, 5.5vw, 5.5rem)',
            lineHeight: 0.95,
            letterSpacing: '-0.03em',
            maxWidth: '1100px',
            color: 'var(--text-color)',
          }}
        >
          Most AI tools wait for heavy cloud LLM calls. AIOS CLI intercepts local intent in milliseconds, executes native shell & git commands without burning API tokens, and syncs automatically with your workspace context.
        </h2>
      </section>

      {/* Architecture Bento Grid (No Grey Shadows, Acid Accent Borders) */}
      <section className="section container" style={{ position: 'relative', zIndex: 1 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '3rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <span style={{ fontSize: '11px', color: 'var(--accent-color)', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
              [ ARCHITECTURE & SPECS ]
            </span>
            <h2 style={{ fontSize: 'clamp(2rem, 4vw, 4rem)', marginTop: '0.4rem' }}>ENGINE CORE</h2>
          </div>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>↳ BUILT FOR POWER USERS & TERMINAL LOVERS</span>
        </div>

        <div className="grid-auto">
          <div
            style={{
              padding: '2.5rem',
              backgroundColor: '#090a0e',
              border: '1px solid rgba(206, 245, 99, 0.25)',
              borderRadius: '4px',
              position: 'relative',
            }}
          >
            <div style={{ fontSize: '12px', color: 'var(--accent-color)', marginBottom: '1rem', fontWeight: 700 }}>
              01 // INTENT CLASSIFIER
            </div>
            <h3 style={{ fontSize: '1.8rem', marginBottom: '1rem' }}>RULE + HYBRID ROUTING</h3>
            <p style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>
              Intercepts simple git status, shell execution, and file inspection requests in ~0.004s before contacting external AI providers. Save 80% of API token budget.
            </p>
          </div>

          <div
            style={{
              padding: '2.5rem',
              backgroundColor: '#090a0e',
              border: '1px solid rgba(206, 245, 99, 0.25)',
              borderRadius: '4px',
            }}
          >
            <div style={{ fontSize: '12px', color: 'var(--accent-color)', marginBottom: '1rem', fontWeight: 700 }}>
              02 // MCP TOOL HUB
            </div>
            <h3 style={{ fontSize: '1.8rem', marginBottom: '1rem' }}>MODEL CONTEXT PROTOCOL</h3>
            <p style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>
              Connect external tools via standard JSON-RPC 2.0 transport (Figma, GitHub, PostgreSQL). Automatic tool registration and parameter schema validation.
            </p>
          </div>

          <div
            style={{
              padding: '2.5rem',
              backgroundColor: '#090a0e',
              border: '1px solid rgba(206, 245, 99, 0.25)',
              borderRadius: '4px',
            }}
          >
            <div style={{ fontSize: '12px', color: 'var(--accent-color)', marginBottom: '1rem', fontWeight: 700 }}>
              03 // FTS5 LOCAL MEMORY
            </div>
            <h3 style={{ fontSize: '1.8rem', marginBottom: '1rem' }}>SQLITE VECTOR & SEARCH</h3>
            <p style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>
              Full-text search (FTS5) for instant retrieval of user facts, project conventions, and past conversation memory without external cloud DB dependencies.
            </p>
          </div>

          <div
            style={{
              padding: '2.5rem',
              backgroundColor: '#090a0e',
              border: '1px solid rgba(206, 245, 99, 0.25)',
              borderRadius: '4px',
            }}
          >
            <div style={{ fontSize: '12px', color: 'var(--accent-color)', marginBottom: '1rem', fontWeight: 700 }}>
              04 // HARDENED SAFETY
            </div>
            <h3 style={{ fontSize: '1.8rem', marginBottom: '1rem' }}>CONFIRMATION GATE</h3>
            <p style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>
              Risky commands (file deletion, git push to main, system modifications) trigger explicit interactive confirmation before execution.
            </p>
          </div>
        </div>
      </section>

      {/* CLI Performance Metrics */}
      <section className="section container" style={{ position: 'relative', zIndex: 1 }}>
        <div
          style={{
            padding: '3rem',
            backgroundColor: '#040507',
            border: '1px solid var(--accent-color)',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(220px, 100%), 1fr))',
            gap: '2rem',
          }}
        >
          <div>
            <div style={{ fontSize: 'clamp(2.5rem, 5vw, 4.5rem)', fontFamily: 'var(--font-display)', color: 'var(--accent-color)', lineHeight: 1 }}>
              0.004s
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '0.5rem', textTransform: 'uppercase' }}>
              INTENT LATENCY
            </div>
          </div>

          <div>
            <div style={{ fontSize: 'clamp(2.5rem, 5vw, 4.5rem)', fontFamily: 'var(--font-display)', color: 'var(--accent-color)', lineHeight: 1 }}>
              100%
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '0.5rem', textTransform: 'uppercase' }}>
              LOCAL PRIVACY
            </div>
          </div>

          <div>
            <div style={{ fontSize: 'clamp(2.5rem, 5vw, 4.5rem)', fontFamily: 'var(--font-display)', color: 'var(--accent-color)', lineHeight: 1 }}>
              38+
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '0.5rem', textTransform: 'uppercase' }}>
              NATIVE & MCP TOOLS
            </div>
          </div>

          <div>
            <div style={{ fontSize: 'clamp(2.5rem, 5vw, 4.5rem)', fontFamily: 'var(--font-display)', color: 'var(--accent-color)', lineHeight: 1 }}>
              0
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '0.5rem', textTransform: 'uppercase' }}>
              TRACKERS & TELEMETRY
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="section container" style={{ textAlign: 'center', paddingBlock: 'clamp(5rem, 12vw, 12rem)', position: 'relative', zIndex: 1 }}>
        <h2 style={{ fontSize: 'clamp(3rem, 8vw, 9rem)', color: 'var(--text-color)', marginBottom: '1.5rem' }}>
          READY TO <span style={{ color: 'var(--accent-color)' }}>SUPERCHARGE</span> YOUR TERMINAL?
        </h2>
        <p style={{ maxWidth: '550px', marginInline: 'auto', marginBottom: '3rem', fontSize: '1.1rem' }}>
          Install AIOS CLI globally with npm or download pre-compiled standalone binary for Windows, macOS, and Linux.
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '1.5rem', flexWrap: 'wrap' }}>
          <button onClick={handleCopy} className="btn-primary" style={{ backgroundColor: 'var(--accent-color)', color: '#07080b' }}>
            [ {copied ? 'COPIED COMMAND!' : 'COPY INSTALL COMMAND'} ]
          </button>
        </div>
      </section>
    </div>
  )
}
