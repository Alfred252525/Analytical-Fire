'use client'

import { useState, useEffect } from 'react'
import Dashboard from '@/components/Dashboard'
import Login from '@/components/Login'
import { getAuthToken, setAuthToken } from '@/lib/auth'

export default function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = getAuthToken()
    setIsAuthenticated(!!token)
    setLoading(false)
  }, [])

  const handleLogin = (token: string) => {
    setAuthToken(token)
    setIsAuthenticated(true)
  }

  const handleLogout = () => {
    setAuthToken('')
    setIsAuthenticated(false)
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    )
  }

  return (
    <main className="min-h-screen">
      {isAuthenticated ? (
        <Dashboard onLogout={handleLogout} />
      ) : (
        <Login onLogin={handleLogin} />
      )}
    </main>
  )
}
