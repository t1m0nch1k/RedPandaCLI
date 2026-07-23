import { useState, useEffect } from 'react'

const CITIES = [
  { name: 'TOKYO', timeZone: 'Asia/Tokyo' },
  { name: 'LONDON', timeZone: 'Europe/London' },
  { name: 'NEW YORK', timeZone: 'America/New_York' },
]

export default function WorldClock() {
  const [times, setTimes] = useState({})

  useEffect(() => {
    const updateTimes = () => {
      const newTimes = {}
      CITIES.forEach((city) => {
        newTimes[city.name] = new Intl.DateTimeFormat('en-GB', {
          timeZone: city.timeZone,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false,
        }).format(new Date())
      })
      setTimes(newTimes)
    }

    updateTimes()
    const timer = setInterval(updateTimes, 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', fontSize: '11px', letterSpacing: '0.08em', color: 'rgba(255,255,255,0.5)', fontFamily: 'var(--font-mono)' }}>
      {CITIES.map((c) => (
        <div key={c.name} style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
          <span style={{ color: 'var(--text-muted)' }}>{c.name}</span>
          <span style={{ color: 'var(--text-color)', fontWeight: 700 }}>{times[c.name] || '--:--:--'}</span>
        </div>
      ))}
    </div>
  )
}
