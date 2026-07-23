import { useEffect, useRef } from 'react'

export default function ElasticThread({ color = '#cef563' }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    // Disable on touch / reduced motion / narrow screens
    if (window.innerWidth < 1024 || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return
    }

    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    let animationFrameId
    let width = (canvas.width = window.innerWidth)
    let height = (canvas.height = window.innerHeight)

    const pointsCount = 35
    const spring = 0.35
    const friction = 0.5
    
    let mouse = { x: width / 2, y: height / 2 }
    let points = Array.from({ length: pointsCount }, () => ({
      x: width / 2,
      y: height / 2,
      vx: 0,
      vy: 0,
    }))

    const handleMouseMove = (e) => {
      mouse.x = e.clientX
      mouse.y = e.clientY
    }

    const handleResize = () => {
      width = canvas.width = window.innerWidth
      height = canvas.height = window.innerHeight
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('resize', handleResize)

    const render = () => {
      ctx.clearRect(0, 0, width, height)

      // Leader follows cursor
      points[0].x = mouse.x
      points[0].y = mouse.y

      // Followers physics
      for (let i = 1; i < pointsCount; i++) {
        const prev = points[i - 1]
        const pt = points[i]

        pt.vx += (prev.x - pt.x) * spring
        pt.vy += (prev.y - pt.y) * spring
        pt.vx *= friction
        pt.vy *= friction

        pt.x += pt.vx
        pt.y += pt.vy
      }

      // Draw smooth quadratic curve through points
      ctx.beginPath()
      ctx.moveTo(points[0].x, points[0].y)

      for (let i = 1; i < pointsCount - 1; i++) {
        const xc = (points[i].x + points[i + 1].x) / 2
        const yc = (points[i].y + points[i + 1].y) / 2
        ctx.quadraticCurveTo(points[i].x, points[i].y, xc, yc)
      }

      ctx.strokeStyle = color
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'

      // Tapering line width
      for (let i = 0; i < pointsCount - 1; i++) {
        const pt = points[i]
        const nextPt = points[i + 1]
        const progress = 1 - i / pointsCount
        const lineWidth = Math.max(0.5, progress * 4.5)

        ctx.beginPath()
        ctx.moveTo(pt.x, pt.y)
        ctx.lineTo(nextPt.x, nextPt.y)
        ctx.lineWidth = lineWidth
        ctx.stroke()
      }

      animationFrameId = requestAnimationFrame(render)
    }

    render()

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(animationFrameId)
    }
  }, [color])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none',
        zIndex: 9999,
        opacity: 0.85,
      }}
    />
  )
}
