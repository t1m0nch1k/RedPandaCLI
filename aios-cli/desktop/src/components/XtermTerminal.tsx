import { useEffect, useRef, forwardRef, useImperativeHandle } from 'react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import { xtermThemeFor } from '../theme/themes'

export interface XtermHandle {
  write: (data: string) => void
}

interface Props {
  onCommand?: (command: string) => void
}

const XtermTerminal = forwardRef<XtermHandle, Props>(({ onCommand }, ref) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const termRef = useRef<Terminal | null>(null)
  const fitRef = useRef<FitAddon | null>(null)
  const commandBufferRef = useRef('')

  useEffect(() => {
    const host = containerRef.current
    if (!host) return

    const themeId = document.documentElement.getAttribute('data-theme') || 'aios-dark'
    const term = new Terminal({
      cursorBlink: true,
      cursorStyle: 'bar',
      fontFamily: "'JetBrains Mono', 'SF Mono', 'Cascadia Code', Consolas, 'Courier New', monospace",
      fontSize: 13,
      lineHeight: 1.3,
      scrollback: 5000,
      allowProposedApi: true,
      theme: xtermThemeFor(themeId),
      convertEol: true,
    })
    const fit = new FitAddon()
    term.loadAddon(fit)
    term.open(host)
    termRef.current = term
    fitRef.current = fit

    term.onData((data) => {
      const code = data.charCodeAt(0)
      if (code === 13) {
        const cmd = commandBufferRef.current.trim()
        term.write('\r\n')
        commandBufferRef.current = ''
        if (cmd) onCommand?.(cmd)
      } else if (code === 127) {
        if (commandBufferRef.current.length > 0) {
          commandBufferRef.current = commandBufferRef.current.slice(0, -1)
          term.write('\b \b')
        }
      } else if (data >= ' ' || code === 9) {
        commandBufferRef.current += data
        term.write(data)
      }
    })

    term.attachCustomKeyEventHandler((e) => {
      const mod = e.ctrlKey || e.metaKey
      if (!mod || e.type !== 'keydown') return true
      const key = e.key.toLowerCase()
      if (key === 'c' && term.hasSelection()) {
        navigator.clipboard.writeText(term.getSelection()).catch(() => {})
        return false
      }
      if (key === 'v') {
        navigator.clipboard.readText().then((text) => {
          commandBufferRef.current += text
          term.write(text.replace(/\n/g, '\r\n'))
        }).catch(() => {})
        return false
      }
      if (key === 'l') {
        term.clear()
        return false
      }
      return true
    })

    let disposed = false

    function safeFit(): void {
      try { fit.fit() } catch { }
    }

    const ro = new ResizeObserver(() => {
      if (disposed) return
      requestAnimationFrame(safeFit)
    })
    ro.observe(host)
    window.addEventListener('resize', safeFit)

    const themeObs = new MutationObserver(() => {
      const attrs = document.documentElement.getAttribute('data-theme')
      term.options.theme = xtermThemeFor(attrs || 'aios-dark')
    })
    themeObs.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme', 'style']
    })

    setTimeout(safeFit, 100)

    term.write('\x1b[33mAIOS Terminal\x1b[0m — type a command\r\n')

    return () => {
      disposed = true
      ro.disconnect()
      themeObs.disconnect()
      window.removeEventListener('resize', safeFit)
      term.dispose()
      termRef.current = null
      fitRef.current = null
    }
  }, [onCommand])

  useImperativeHandle(ref, () => ({
    write: (data: string) => termRef.current?.write(data),
  }), [])

  return (
    <div
      ref={containerRef}
      style={{ width: '100%', height: '100%', overflow: 'hidden' }}
    />
  )
})

export default XtermTerminal
