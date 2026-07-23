import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import DesktopLanding from './pages/DesktopLanding'
import CliLanding from './pages/CliLanding'
import { useEffect } from 'react'
import Lenis from 'lenis'

function App() {
  // Initialize Lenis for smooth scrolling globally
  useEffect(() => {
    const lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      direction: 'vertical',
      gestureDirection: 'vertical',
      smooth: true,
      mouseMultiplier: 1,
      smoothTouch: false,
      touchMultiplier: 2,
      infinite: false,
    })

    function raf(time) {
      lenis.raf(time)
      requestAnimationFrame(raf)
    }

    requestAnimationFrame(raf)

    return () => {
      lenis.destroy()
    }
  }, [])

  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<DesktopLanding />} />
        <Route path="cli" element={<CliLanding />} />
      </Route>
    </Routes>
  )
}

export default App
