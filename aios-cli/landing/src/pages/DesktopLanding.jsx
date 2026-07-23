import { useEffect, useRef } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Environment } from '@react-three/drei'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import SplitType from 'split-type'
import PandaModel from '../components/PandaModel'
import DesktopAppMockup from '../components/DesktopAppMockup'

gsap.registerPlugin(ScrollTrigger)

export default function DesktopLanding() {
  const manifestRef = useRef(null)

  useEffect(() => {
    // Hero Text Reveal
    const heroText = new SplitType('.desktop-hero-title', { types: 'lines, chars' })
    gsap.fromTo(
      heroText.chars,
      { y: 80, opacity: 0 },
      { y: 0, opacity: 1, stagger: 0.02, duration: 1, ease: 'power4.out', delay: 0.2 }
    )

    // Manifest Line Mask Reveal (mel-creative.ru design reference)
    const manifestLines = new SplitType('.desktop-manifest-text', { types: 'lines' })

    manifestLines.lines.forEach((line) => {
      const wrapper = document.createElement('div')
      wrapper.style.position = 'relative'
      wrapper.style.display = 'inline-block'
      wrapper.style.width = '100%'

      const mask = document.createElement('div')
      mask.style.position = 'absolute'
      mask.style.top = '0'
      mask.style.left = '0'
      mask.style.width = '100%'
      mask.style.height = '100%'
      mask.style.backgroundColor = 'var(--accent-color)'
      mask.style.opacity = '0.85'
      mask.style.transformOrigin = 'right'

      line.parentNode.insertBefore(wrapper, line)
      wrapper.appendChild(line)
      wrapper.appendChild(mask)

      gsap.to(mask, {
        scaleX: 0,
        ease: 'none',
        scrollTrigger: {
          trigger: wrapper,
          start: 'top 75%',
          end: 'bottom 45%',
          scrub: 1,
        },
      })
    })

    return () => {
      heroText.revert()
      manifestLines.revert()
    }
  }, [])

  return (
    <div style={{ backgroundColor: '#0b0d13', color: '#f4f5f8', minHeight: '100vh', position: 'relative' }}>
      {/* Background Radial Glow */}
      <div
        style={{
          position: 'absolute',
          top: '-150px',
          left: '50%',
          transform: 'translateX(-50%)',
          width: '800px',
          height: '600px',
          background: 'radial-gradient(circle, rgba(66, 46, 255, 0.18) 0%, rgba(11, 13, 19, 0) 70%)',
          pointerEvents: 'none',
          zIndex: 0,
        }}
      />

      {/* Hero Section */}
      <section className="section container" style={{ paddingTop: '140px', position: 'relative', zIndex: 1 }}>
        <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'center', marginBottom: '1.5rem' }}>
          <span className="tag-badge" style={{ borderColor: 'var(--accent-color)' }}>
            <span className="dot" /> TAURI 2.0 + RUST CORE
          </span>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>[+] NATIVE DESKTOP GUI</span>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '3rem', alignItems: 'center' }}>
          <div style={{ flex: '1 1 500px' }}>
            <h1 className="desktop-hero-title" style={{ marginBottom: '1.5rem' }}>
              AGENTIC<br />
              <span style={{ color: 'var(--accent-color)' }}>DESKTOP</span>
            </h1>

            <p style={{ fontSize: 'clamp(1.1rem, 1.6vw, 1.35rem)', color: 'var(--text-muted)', maxWidth: '520px', lineHeight: 1.5, marginBottom: '2.5rem' }}>
              Your proactive local AI companion. Equipped with FTS5 long-term memory, native calendar integration, Monaco Coder IDE, and system-wide hotkeys.
            </p>

            <div style={{ display: 'flex', gap: '1.2rem', flexWrap: 'wrap' }}>
              <a href="#download" className="btn-primary" style={{ backgroundColor: 'var(--accent-color)', color: '#fff' }}>
                DOWNLOAD APP (.EXE)
              </a>
              <a href="#demo" className="btn-secondary">
                EXPLORE GUI DEMO
              </a>
            </div>
          </div>

          {/* 3D Panda Mascot Center */}
          <div style={{ flex: '1 1 380px', height: '420px', position: 'relative' }}>
            <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
              <ambientLight intensity={0.7} />
              <spotLight position={[10, 10, 10]} angle={0.2} penumbra={1} intensity={1.2} />
              <PandaModel scale={1.6} position={[0, -0.9, 0]} />
              <Environment preset="city" />
              <OrbitControls enableZoom={false} enablePan={false} autoRotate autoRotateSpeed={1.5} />
            </Canvas>
          </div>
        </div>
      </section>

      {/* Interactive App GUI Mockup Section */}
      <section id="demo" className="section container" style={{ position: 'relative', zIndex: 1, paddingBlock: '4rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
          <span style={{ fontSize: '11px', color: 'var(--accent-color)', letterSpacing: '0.15em', textTransform: 'uppercase' }}>
            [ LIVE INTERACTIVE PREVIEW ]
          </span>
          <h2 style={{ fontSize: 'clamp(2rem, 4.5vw, 4.5rem)', marginTop: '0.4rem' }}>EXPERIENCE THE INTERFACE</h2>
        </div>

        <DesktopAppMockup />
      </section>

      {/* Manifest Section (mel-creative.ru Line Mask Reveal) */}
      <section className="section container" style={{ paddingBlock: 'clamp(5rem, 12vw, 12rem)', position: 'relative', zIndex: 1 }}>
        <div style={{ fontSize: '11px', color: 'var(--accent-color)', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: '1.5rem' }}>
          {'{ THE DESKTOP MANIFESTO }'}
        </div>
        <h2
          className="desktop-manifest-text"
          ref={manifestRef}
          style={{
            fontSize: 'clamp(2.2rem, 5.5vw, 5.5rem)',
            lineHeight: 0.95,
            letterSpacing: '-0.03em',
            maxWidth: '1150px',
            color: 'var(--text-color)',
          }}
        >
          AIOS Desktop runs locally on your machine. It active-listens for timers, reminds you of upcoming meetings, manages codebase refactoring with Monaco, and keeps all sensitive context strictly on your hardware.
        </h2>
      </section>

      {/* Liquid Glass Feature Cards */}
      <section className="section container" style={{ position: 'relative', zIndex: 1 }}>
        <div style={{ marginBottom: '3rem' }}>
          <span style={{ fontSize: '11px', color: 'var(--accent-color)', letterSpacing: '0.15em', textTransform: 'uppercase' }}>
            [ CAPABILITIES ]
          </span>
          <h2 style={{ fontSize: 'clamp(2rem, 4vw, 4rem)', marginTop: '0.4rem' }}>ENGINEERED FOR FLOW</h2>
        </div>

        <div className="grid-auto">
          <div className="glass-panel" style={{ padding: '2.5rem' }}>
            <div style={{ fontSize: '11px', color: 'var(--accent-color)', fontWeight: 700, marginBottom: '1rem', letterSpacing: '0.1em' }}>
              01 // PROACTIVE ENGINE
            </div>
            <h3 style={{ fontSize: '1.8rem', marginBottom: '1rem' }}>SYSTEM-WIDE EVENTS</h3>
            <p style={{ fontSize: '0.92rem', lineHeight: 1.6 }}>
              Initiates proactive notifications when background timers trigger or calendar events are imminent over high-speed WebSocket IPC.
            </p>
          </div>

          <div className="glass-panel" style={{ padding: '2.5rem' }}>
            <div style={{ fontSize: '11px', color: 'var(--accent-color)', fontWeight: 700, marginBottom: '1rem', letterSpacing: '0.1em' }}>
              02 // MONACO CODER
            </div>
            <h3 style={{ fontSize: '1.8rem', marginBottom: '1rem' }}>FULL CODEBASE EDITOR</h3>
            <p style={{ fontSize: '0.92rem', lineHeight: 1.6 }}>
              Integrated Monaco editor with terminal outputs and automatic multi-file patch diffs for rapid pair-programming.
            </p>
          </div>

          <div className="glass-panel" style={{ padding: '2.5rem' }}>
            <div style={{ fontSize: '11px', color: 'var(--accent-color)', fontWeight: 700, marginBottom: '1rem', letterSpacing: '0.1em' }}>
              03 // FTS5 LONG-TERM MEMORY
            </div>
            <h3 style={{ fontSize: '1.8rem', marginBottom: '1rem' }}>PERSISTENT KNOWLEDGE</h3>
            <p style={{ fontSize: '0.92rem', lineHeight: 1.6 }}>
              Stores project facts, user preferences, and code patterns locally in SQLite FTS5 for instant sub-millisecond retrieval.
            </p>
          </div>

          <div className="glass-panel" style={{ padding: '2.5rem' }}>
            <div style={{ fontSize: '11px', color: 'var(--accent-color)', fontWeight: 700, marginBottom: '1rem', letterSpacing: '0.1em' }}>
              04 // TAURI 2.0 ARCHITECTURE
            </div>
            <h3 style={{ fontSize: '1.8rem', marginBottom: '1rem' }}>LIGHTWEIGHT RUST CORE</h3>
            <p style={{ fontSize: '0.92rem', lineHeight: 1.6 }}>
              Consumes less than 15MB RAM idle versus 500MB+ in bloated Electron apps. Instant launch time with native tray minimize.
            </p>
          </div>
        </div>
      </section>

      {/* Tauri vs Electron Comparison Section */}
      <section className="section container" style={{ position: 'relative', zIndex: 1 }}>
        <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
          <span style={{ fontSize: '11px', color: 'var(--accent-color)', letterSpacing: '0.15em', textTransform: 'uppercase' }}>
            [ BENCHMARKS ]
          </span>
          <h2 style={{ fontSize: 'clamp(2rem, 4.5vw, 4.5rem)', marginTop: '0.4rem' }}>TAURI VS ELECTRON</h2>
        </div>

        <div
          className="glass-panel"
          style={{
            padding: '2.5rem',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(280px, 100%), 1fr))',
            gap: '2rem',
          }}
        >
          <div>
            <div style={{ fontSize: '12px', color: 'var(--accent-color)', fontWeight: 700, marginBottom: '0.5rem' }}>
              MEMORY FOOTPRINT (IDLE)
            </div>
            <div style={{ fontSize: 'clamp(2.5rem, 4vw, 4rem)', fontFamily: 'var(--font-display)', color: '#fff' }}>
              15 MB <span style={{ fontSize: '1rem', color: 'var(--accent-color)' }}>VS 480 MB</span>
            </div>
            <p style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>32x lighter memory utilization thanks to native OS webview.</p>
          </div>

          <div>
            <div style={{ fontSize: '12px', color: 'var(--accent-color)', fontWeight: 700, marginBottom: '0.5rem' }}>
              STARTUP TIME
            </div>
            <div style={{ fontSize: 'clamp(2.5rem, 4vw, 4rem)', fontFamily: 'var(--font-display)', color: '#fff' }}>
              0.2s <span style={{ fontSize: '1rem', color: 'var(--accent-color)' }}>VS 4.5s</span>
            </div>
            <p style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>Instant window creation with compiled Rust IPC hooks.</p>
          </div>

          <div>
            <div style={{ fontSize: '12px', color: 'var(--accent-color)', fontWeight: 700, marginBottom: '0.5rem' }}>
              INSTALLER SIZE
            </div>
            <div style={{ fontSize: 'clamp(2.5rem, 4vw, 4rem)', fontFamily: 'var(--font-display)', color: '#fff' }}>
              12 MB <span style={{ fontSize: '1rem', color: 'var(--accent-color)' }}>VS 120 MB</span>
            </div>
            <p style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>Minimal distribution footprint without Chromium bundle bloat.</p>
          </div>
        </div>
      </section>

      {/* CTA Download Section */}
      <section id="download" className="section container" style={{ textAlign: 'center', paddingBlock: 'clamp(5rem, 12vw, 12rem)', position: 'relative', zIndex: 1 }}>
        <h2 style={{ fontSize: 'clamp(3rem, 7.5vw, 8.5rem)', color: 'var(--text-color)', marginBottom: '1.5rem' }}>
          DOWNLOAD <span style={{ color: 'var(--accent-color)' }}>AIOS DESKTOP</span>
        </h2>
        <p style={{ maxWidth: '550px', marginInline: 'auto', marginBottom: '3rem', fontSize: '1.1rem' }}>
          Available for Windows x64 (.msi / .exe), macOS (Apple Silicon / Intel), and Linux (.AppImage).
        </p>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '1.5rem', flexWrap: 'wrap' }}>
          <a href="https://github.com/t1m0nch1k/RedPandaCLI/releases" target="_blank" rel="noreferrer" className="btn-primary" style={{ backgroundColor: 'var(--accent-color)', color: '#fff' }}>
            DOWNLOAD FOR WINDOWS (.EXE)
          </a>
          <a href="https://github.com/t1m0nch1k/RedPandaCLI" target="_blank" rel="noreferrer" className="btn-secondary">
            OTHER PLATFORMS ↗
          </a>
        </div>
      </section>
    </div>
  )
}
