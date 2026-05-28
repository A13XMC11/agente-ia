'use client'

import { useEffect } from 'react'

export function SessionRefresher() {
  useEffect(() => {
    const refresh = () => fetch('/api/auth/refresh', { method: 'POST' })

    // Check on load and every 30 minutes
    refresh()
    const interval = setInterval(refresh, 30 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  return null
}
