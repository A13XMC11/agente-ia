'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      console.log('[LOGIN PAGE] Submitting login for:', email)

      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
        }),
      })

      console.log('[LOGIN PAGE] Response status:', response.status)
      const data = await response.json()
      console.log('[LOGIN PAGE] Response data:', {
        success: data.success,
        hasUser: !!data.user,
        userRole: data.user?.role,
        error: data.error,
      })

      if (!data.success) {
        console.error('[LOGIN PAGE] Login failed:', data.error)
        setError(data.error || 'Login failed')
        return
      }

      console.log('[LOGIN PAGE] Login successful, user role:', data.user?.role)
      console.log('[LOGIN PAGE] Redirecting...')

      // Redirect based on user role
      let redirectPath = '/admin'
      if (data.user?.role === 'super_admin') {
        redirectPath = '/admin'
      } else if (data.user?.role === 'admin') {
        redirectPath = '/cliente'
      } else if (data.user?.role === 'operador') {
        redirectPath = '/cliente'
      } else {
        // Default to /admin if role is undefined or unknown
        redirectPath = '/admin'
      }

      console.log('[LOGIN PAGE] Redirecting to:', redirectPath)
      router.push(redirectPath)
      router.refresh()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred'
      console.error('[LOGIN PAGE] Unexpected error:', errorMessage)
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-2 text-center">
          <CardTitle className="text-3xl">Agente IA</CardTitle>
          <CardDescription>Ingresa con tu cuenta para continuar</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="rounded-lg bg-red-900/20 border border-red-900/50 p-3 text-sm text-red-300">
                {error}
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="tu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Contraseña</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={isLoading}
            >
              {isLoading ? 'Ingresando...' : 'Ingresar'}
            </Button>

            <p className="text-center text-sm text-text-secondary">
              Para una demostración, usa:
              <br />
              Email: demo@example.com
              <br />
              Contraseña: password123
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
