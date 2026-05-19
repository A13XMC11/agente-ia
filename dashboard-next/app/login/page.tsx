'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Bot, AlertCircle } from 'lucide-react'

interface LoginResponse {
  success: boolean
  user?: {
    id: string
    email: string
    role: string
    cliente_id?: string | null
  }
  error?: string
}

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
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      const data: LoginResponse = await response.json()

      if (!data.success || !data.user) {
        setError(data.error || 'Credenciales incorrectas')
        return
      }

      const role = data.user.role
      const path = role === 'super_admin' ? '/admin' : '/cliente'
      router.push(path)
    } catch {
      setError('Error de conexión. Intenta de nuevo.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background p-4">
      {/* Background ambient blobs */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 overflow-hidden"
      >
        <div className="absolute -top-40 -left-40 h-125 w-125 rounded-full bg-accent/5 blur-[120px]" />
        <div className="absolute -bottom-40 -right-40 h-125 w-125 rounded-full bg-accent-indigo/5 blur-[120px]" />
      </div>

      {/* Card */}
      <div className="stagger-1 relative w-full max-w-md">
        <div className="glass rounded-2xl p-8 shadow-[0_32px_80px_rgba(0,0,0,0.6)]">
          {/* Logo */}
          <div className="mb-8 flex flex-col items-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-accent/10 ring-1 ring-accent/25">
              <Bot className="h-7 w-7 text-accent" />
            </div>
            <div className="text-center">
              <h1 className="text-2xl font-bold text-text-primary">Agente IA</h1>
              <p className="text-sm text-text-secondary mt-1">Ingresa con tu cuenta para continuar</p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="flex items-center gap-2.5 rounded-lg border border-error/25 bg-error/8 px-4 py-3 text-sm text-error">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email" className="text-text-secondary text-xs font-medium uppercase tracking-wider">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="tu@empresa.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
                className="h-11 bg-surface/50 border-border hover:border-border-light focus:border-accent/50 transition-colors duration-150"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-text-secondary text-xs font-medium uppercase tracking-wider">
                Contraseña
              </Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
                className="h-11 bg-surface/50 border-border hover:border-border-light focus:border-accent/50 transition-colors duration-150"
              />
            </div>

            <Button
              type="submit"
              className="w-full h-11 text-sm font-semibold mt-2"
              disabled={isLoading}
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 rounded-full border-2 border-background/30 border-t-background animate-spin" />
                  Ingresando...
                </span>
              ) : (
                'Ingresar'
              )}
            </Button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-text-muted">
          Plataforma de agentes IA conversacionales
        </p>
      </div>
    </div>
  )
}
