'use client'

import { useUser } from '@clerk/nextjs'
import { useRouter } from 'next/navigation'
import { useState } from 'react'

function CambiarContrasenaForm() {
  const router = useRouter()
  const { user, isLoaded } = useUser()

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showCurrent, setShowCurrent] = useState(false)
  const [showNew, setShowNew] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (newPassword !== confirmPassword) {
      setError('Las contraseñas nuevas no coinciden')
      return
    }

    if (newPassword.length < 8) {
      setError('La nueva contraseña debe tener al menos 8 caracteres')
      return
    }

    if (currentPassword === newPassword) {
      setError('La nueva contraseña debe ser diferente a la actual')
      return
    }

    if (!user) return
    setLoading(true)

    try {
      // Clerk verifies current password and updates to new one atomically
      await user.updatePassword({ currentPassword, newPassword })
    } catch (err: unknown) {
      const clerkError = err as { errors?: Array<{ longMessage?: string; message: string }> }
      setError(
        clerkError?.errors?.[0]?.longMessage ??
        clerkError?.errors?.[0]?.message ??
        'Error al cambiar la contraseña'
      )
      setLoading(false)
      return
    }

    try {
      // Clear must_change_password flag and receive custom JWT
      const res = await fetch('/api/auth/cambiar-contrasena', { method: 'POST' })
      const data = await res.json()

      if (!data.success) {
        setError(data.error ?? 'Error al actualizar el estado del usuario')
        return
      }

      setSuccess(true)
      const role = data.user?.role
      setTimeout(() => router.push(role === 'super_admin' ? '/admin' : '/cliente'), 1500)
    } catch {
      setError('Error de conexión. Intenta de nuevo.')
    } finally {
      setLoading(false)
    }
  }

  if (!isLoaded) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center bg-background">
        <svg className="w-6 h-6 animate-spin" viewBox="0 0 24 24" fill="none" style={{ color: 'var(--accent)' }}>
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    )
  }

  if (!user) {
    router.replace('/sign-in')
    return null
  }

  const email = user.emailAddresses[0]?.emailAddress ?? ''
  const canSubmit = !loading && currentPassword && newPassword && confirmPassword

  return (
    <div className="relative flex min-h-[100dvh] items-center justify-center overflow-hidden bg-background px-4 py-8">
      {/* Top ambient glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse 60% 50% at 50% -10%, rgba(56,189,248,0.12) 0%, transparent 70%)',
        }}
      />
      {/* Bottom indigo glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute bottom-0 left-1/2 -translate-x-1/2 w-150 h-75"
        style={{
          background:
            'radial-gradient(ellipse 80% 60% at 50% 100%, rgba(129,140,248,0.07) 0%, transparent 70%)',
        }}
      />
      {/* Subtle grid */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            'linear-gradient(var(--border-light) 1px, transparent 1px), linear-gradient(90deg, var(--border-light) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />

      <div className="relative w-full max-w-sm">
        {/* Brand */}
        <div className="text-center mb-8">
          <div
            className="inline-flex items-center justify-center w-12 h-12 rounded-2xl mb-4"
            style={{
              background: 'rgba(56,189,248,0.1)',
              border: '1px solid rgba(56,189,248,0.22)',
            }}
          >
            <svg
              className="w-6 h-6"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ color: 'var(--accent)' }}
            >
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          </div>
          <h1 className="text-xl font-semibold text-text-primary tracking-tight">
            Configura tu contraseña
          </h1>
          <p className="mt-1 text-sm text-text-secondary">
            Por seguridad, debes crear una contraseña personal antes de continuar.
          </p>
        </div>

        {/* Form card */}
        <div
          className="glass rounded-2xl p-7"
          style={{
            boxShadow: '0 0 0 1px rgba(56,189,248,0.07), 0 24px 48px rgba(0,0,0,0.4)',
          }}
        >
          {success ? (
            <div className="flex flex-col items-center gap-3 py-4">
              <div
                className="flex items-center justify-center w-10 h-10 rounded-full"
                style={{ background: 'rgba(34,211,160,0.12)', border: '1px solid rgba(34,211,160,0.3)' }}
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--success)' }}>
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <p className="text-sm font-medium" style={{ color: 'var(--success)' }}>
                ¡Contraseña actualizada!
              </p>
              <p className="text-xs text-center" style={{ color: 'var(--text-secondary)' }}>
                Redirigiendo al panel...
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate className="space-y-5">
              {/* Email (read-only) */}
              {email && (
                <div className="space-y-2">
                  <label
                    className="block text-xs font-medium tracking-widest uppercase"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Correo electrónico
                  </label>
                  <div
                    className="w-full rounded-xl px-4 py-3 text-sm"
                    style={{
                      background: 'rgba(255,255,255,0.02)',
                      border: '1px solid var(--border-light)',
                      color: 'var(--text-secondary)',
                    }}
                  >
                    {email}
                  </div>
                </div>
              )}

              {/* Current (temp) password */}
              <PasswordField
                id="currentPassword"
                label="Contraseña temporal"
                value={currentPassword}
                onChange={setCurrentPassword}
                show={showCurrent}
                onToggle={() => setShowCurrent((v) => !v)}
                placeholder="Contraseña recibida por email"
                autoComplete="current-password"
              />

              {/* New password */}
              <PasswordField
                id="newPassword"
                label="Nueva contraseña"
                value={newPassword}
                onChange={setNewPassword}
                show={showNew}
                onToggle={() => setShowNew((v) => !v)}
                placeholder="Mínimo 8 caracteres"
                autoComplete="new-password"
              />

              {/* Confirm new password */}
              <PasswordField
                id="confirmPassword"
                label="Confirmar nueva contraseña"
                value={confirmPassword}
                onChange={setConfirmPassword}
                show={showNew}
                onToggle={() => setShowNew((v) => !v)}
                placeholder="Repite la nueva contraseña"
                autoComplete="new-password"
              />

              {/* Error */}
              {error && (
                <div
                  className="flex items-start gap-2.5 rounded-xl px-4 py-3 text-sm"
                  style={{
                    background: 'rgba(248,113,113,0.08)',
                    border: '1px solid rgba(248,113,113,0.2)',
                    color: 'var(--error)',
                  }}
                >
                  <svg className="w-4 h-4 mt-0.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  <span>{error}</span>
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={!canSubmit}
                className="w-full rounded-xl py-3 text-sm font-semibold transition-all duration-150 disabled:cursor-not-allowed"
                style={{
                  background: !canSubmit ? 'rgba(56,189,248,0.25)' : 'var(--accent)',
                  color: !canSubmit ? 'rgba(56,189,248,0.5)' : '#060D13',
                  boxShadow: !canSubmit ? 'none' : '0 0 20px rgba(56,189,248,0.28)',
                }}
                onMouseEnter={(e) => {
                  if (canSubmit) {
                    e.currentTarget.style.background = 'var(--accent-hover)'
                    e.currentTarget.style.boxShadow = '0 0 28px rgba(56,189,248,0.4)'
                  }
                }}
                onMouseLeave={(e) => {
                  if (canSubmit) {
                    e.currentTarget.style.background = 'var(--accent)'
                    e.currentTarget.style.boxShadow = '0 0 20px rgba(56,189,248,0.28)'
                  }
                }}
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Guardando...
                  </span>
                ) : (
                  'Guardar contraseña'
                )}
              </button>
            </form>
          )}
        </div>

        <p
          className="text-center text-xs mt-6"
          style={{ color: 'var(--text-muted)' }}
        >
          ¿Necesitas ayuda?{' '}
          <span style={{ color: 'var(--text-secondary)' }}>
            Contacta al administrador
          </span>
        </p>
      </div>
    </div>
  )
}

interface PasswordFieldProps {
  id: string
  label: string
  value: string
  onChange: (v: string) => void
  show: boolean
  onToggle: () => void
  placeholder: string
  autoComplete: string
}

function PasswordField({ id, label, value, onChange, show, onToggle, placeholder, autoComplete }: PasswordFieldProps) {
  return (
    <div className="space-y-2">
      <label
        htmlFor={id}
        className="block text-xs font-medium tracking-widest uppercase"
        style={{ color: 'var(--text-secondary)' }}
      >
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type={show ? 'text' : 'password'}
          autoComplete={autoComplete}
          required
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full rounded-xl px-4 py-3 pr-11 text-sm outline-none transition-all duration-150"
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid var(--border-light)',
            color: 'var(--text-primary)',
          }}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = 'rgba(56,189,248,0.5)'
            e.currentTarget.style.boxShadow = '0 0 0 3px rgba(56,189,248,0.08)'
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = ''
            e.currentTarget.style.boxShadow = ''
          }}
        />
        <button
          type="button"
          onClick={onToggle}
          className="absolute right-3 top-1/2 -translate-y-1/2 transition-colors"
          style={{ color: 'var(--text-muted)' }}
          onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--text-secondary)' }}
          onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-muted)' }}
          aria-label={show ? 'Ocultar contraseña' : 'Mostrar contraseña'}
        >
          {show ? (
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
              <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
              <line x1="1" y1="1" x2="23" y2="23" />
            </svg>
          ) : (
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          )}
        </button>
      </div>
    </div>
  )
}

export default function CambiarContrasenaPage() {
  return <CambiarContrasenaForm />
}
