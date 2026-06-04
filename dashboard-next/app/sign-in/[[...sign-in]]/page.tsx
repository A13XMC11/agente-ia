'use client'

import { useSignIn } from '@clerk/nextjs'
import { AlertCircle, ArrowRight, Eye, EyeOff, Lock, Mail, Shield } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useState } from 'react'

export default function SignInPage() {
  const router = useRouter()
  const { signIn } = useSignIn()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [needsMFA, setNeedsMFA] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!signIn) return

    setErrorMsg('')
    setLoading(true)

    try {
      if (needsMFA) {
        const { error } = await signIn.mfa.verifyTOTP({ code: totpCode })
        if (error) {
          setErrorMsg(error.longMessage ?? error.message ?? 'Código incorrecto, intenta de nuevo.')
          return
        }
        if (signIn.status === 'complete') {
          const { error: finalizeError } = await signIn.finalize()
          if (finalizeError) {
            setErrorMsg(finalizeError.longMessage ?? finalizeError.message ?? 'Error al finalizar sesión')
            return
          }
          router.push('/api/auth/sync')
        }
        return
      }

      const { error: createError } = await signIn.create({ identifier: email })
      if (createError) {
        setErrorMsg(createError.longMessage ?? createError.message ?? 'Credenciales incorrectas')
        return
      }

      const { error: passwordError } = await signIn.password({ password })
      if (passwordError) {
        setErrorMsg(passwordError.longMessage ?? passwordError.message ?? 'Credenciales incorrectas')
        return
      }

      if (signIn.status === 'complete') {
        const { error: finalizeError } = await signIn.finalize()
        if (finalizeError) {
          setErrorMsg(finalizeError.longMessage ?? finalizeError.message ?? 'Error al finalizar sesión')
          return
        }
        router.push('/api/auth/sync')
      } else if (signIn.status === 'needs_second_factor') {
        setNeedsMFA(true)
      } else {
        setErrorMsg(`Estado inesperado: ${signIn.status}`)
      }
    } catch (err: unknown) {
      const clerkError = err as { errors?: Array<{ longMessage?: string; message: string }> }
      const msg =
        clerkError?.errors?.[0]?.longMessage ??
        clerkError?.errors?.[0]?.message ??
        'Credenciales incorrectas'
      setErrorMsg(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-[100dvh] overflow-hidden bg-background">

      {/* ── Left panel: illustration ── */}
      <div
        className="relative hidden min-h-[100dvh] overflow-hidden lg:flex lg:w-1/2 xl:w-3/5"
        style={{
          background: 'linear-gradient(135deg, #060D13 0%, #0F1E2D 60%, #0a1929 100%)',
        }}
      >
        <img
          src="/lanlabs_home.png"
          alt="Agente IA — canales de comunicación"
          className="absolute inset-0 h-full w-full select-none object-cover"
          draggable={false}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              'linear-gradient(180deg, rgba(6,13,19,0.05) 0%, rgba(6,13,19,0.18) 52%, rgba(6,13,19,0.78) 100%), radial-gradient(ellipse 70% 60% at 50% 50%, rgba(56,189,248,0.08) 0%, transparent 70%)',
          }}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.025]"
          style={{
            backgroundImage:
              'linear-gradient(rgba(56,189,248,0.8) 1px, transparent 1px), linear-gradient(90deg, rgba(56,189,248,0.8) 1px, transparent 1px)',
            backgroundSize: '48px 48px',
          }}
        />

        <div className="relative z-10 mt-auto flex w-full flex-col items-center px-8 pb-8 text-center xl:pb-10">
          <div className="space-y-2">
            <h2 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
              Tu agente IA, siempre activo
            </h2>
            <p className="text-sm max-w-xs mx-auto leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
              WhatsApp, Instagram, Facebook y más — todo desde un solo panel.
            </p>
          </div>
          <div className="flex gap-2 mt-5">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="rounded-full"
                style={{
                  width: i === 1 ? 20 : 6,
                  height: 6,
                  background: i === 1 ? 'var(--accent)' : 'rgba(56,189,248,0.25)',
                }}
              />
            ))}
          </div>
        </div>
      </div>

      {/* ── Right panel: form ── */}
      <div className="flex flex-1 items-center justify-center relative overflow-hidden px-6">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              'radial-gradient(ellipse 60% 50% at 50% -10%, rgba(56,189,248,0.10) 0%, transparent 70%)',
          }}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute bottom-0 left-1/2 -translate-x-1/2 w-96 h-64"
          style={{
            background:
              'radial-gradient(ellipse 80% 60% at 50% 100%, rgba(129,140,248,0.06) 0%, transparent 70%)',
          }}
        />

        <div className="relative w-full max-w-[420px]">
          <div
            aria-hidden
            className="absolute -inset-x-6 -inset-y-8 rounded-[2rem] opacity-80 blur-3xl"
            style={{
              background:
                'radial-gradient(ellipse 65% 45% at 50% 0%, rgba(56,189,248,0.14), transparent 70%)',
            }}
          />

          <div
            className="glass relative overflow-hidden rounded-2xl p-8 stagger-2"
            style={{
              background:
                'linear-gradient(180deg, rgba(15,30,45,0.86) 0%, rgba(9,21,33,0.72) 100%)',
              boxShadow:
                '0 0 0 1px rgba(255,255,255,0.08), 0 28px 70px rgba(0,0,0,0.48), inset 0 1px 0 rgba(255,255,255,0.06)',
            }}
          >
            <div
              aria-hidden
              className="absolute inset-x-0 top-0 h-px"
              style={{
                background:
                  'linear-gradient(90deg, transparent, rgba(56,189,248,0.62), transparent)',
              }}
            />

            <div className="mb-8 stagger-1">
              <div
                className="mb-5 inline-flex h-11 w-11 items-center justify-center rounded-xl"
                style={{
                  background: 'rgba(56,189,248,0.10)',
                  border: '1px solid rgba(56,189,248,0.22)',
                  color: 'var(--accent)',
                }}
              >
                <Shield className="h-5 w-5" strokeWidth={1.9} />
              </div>

              <div className="space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-accent">
                  Acceso seguro
                </p>
                <h1 className="text-2xl font-semibold tracking-tight text-text-primary">
                  Entra a Agente IA
                </h1>
                <p className="max-w-[20rem] text-sm leading-6 text-text-secondary">
                  Gestiona conversaciones, clientes y canales desde tu panel.
                </p>
              </div>
            </div>

            <form onSubmit={handleSubmit} noValidate className="space-y-5">
              {needsMFA ? (
                <div className="space-y-2">
                  <label
                    htmlFor="totp"
                    className="block text-xs font-semibold uppercase tracking-[0.18em] text-text-secondary"
                  >
                    Código de autenticación
                  </label>
                  <p className="text-xs text-text-muted">Ingresa el código de 6 dígitos de tu app de autenticación.</p>
                  <div
                    className="group flex items-center gap-3 rounded-xl px-3.5 transition-all duration-200 focus-within:ring-3 focus-within:ring-accent-glow"
                    style={{
                      border: '1px solid var(--border-light)',
                      background: 'rgba(2,6,23,0.28)',
                    }}
                  >
                    <Shield className="h-4 w-4 shrink-0 text-text-muted transition-colors duration-200 group-focus-within:text-accent" strokeWidth={1.8} />
                    <input
                      id="totp"
                      type="text"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      required
                      autoFocus
                      value={totpCode}
                      onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      placeholder="000000"
                      className="h-12 min-w-0 flex-1 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-muted tracking-widest"
                    />
                  </div>
                </div>
              ) : (
                <>
                  <div className="space-y-2">
                    <label
                      htmlFor="email"
                      className="block text-xs font-semibold uppercase tracking-[0.18em] text-text-secondary"
                    >
                      Correo electrónico
                    </label>
                    <div
                      className="group flex items-center gap-3 rounded-xl px-3.5 transition-all duration-200 focus-within:ring-3 focus-within:ring-accent-glow"
                      style={{
                        border: '1px solid var(--border-light)',
                        background: 'rgba(2,6,23,0.28)',
                      }}
                    >
                      <Mail className="h-4 w-4 shrink-0 text-text-muted transition-colors duration-200 group-focus-within:text-accent" strokeWidth={1.8} />
                      <input
                        id="email"
                        type="email"
                        autoComplete="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="tu@empresa.com"
                        className="h-12 min-w-0 flex-1 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-muted"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label
                      htmlFor="password"
                      className="block text-xs font-semibold uppercase tracking-[0.18em] text-text-secondary"
                    >
                      Contraseña
                    </label>
                    <div
                      className="group flex items-center gap-3 rounded-xl px-3.5 transition-all duration-200 focus-within:ring-3 focus-within:ring-accent-glow"
                      style={{
                        border: '1px solid var(--border-light)',
                        background: 'rgba(2,6,23,0.28)',
                      }}
                    >
                      <Lock className="h-4 w-4 shrink-0 text-text-muted transition-colors duration-200 group-focus-within:text-accent" strokeWidth={1.8} />
                      <input
                        id="password"
                        type={showPassword ? 'text' : 'password'}
                        autoComplete="current-password"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        className="h-12 min-w-0 flex-1 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-muted"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword((v) => !v)}
                        className="flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-lg text-text-muted transition-colors duration-200 hover:bg-white/5 hover:text-text-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                        aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                      >
                        {showPassword ? (
                          <EyeOff className="h-4 w-4" strokeWidth={1.8} />
                        ) : (
                          <Eye className="h-4 w-4" strokeWidth={1.8} />
                        )}
                      </button>
                    </div>
                  </div>
                </>
              )}

              {errorMsg && (
                <div
                  className="flex items-start gap-2.5 rounded-xl px-4 py-3 text-sm"
                  style={{
                    background: 'rgba(248,113,113,0.08)',
                    border: '1px solid rgba(248,113,113,0.2)',
                    color: 'var(--error)',
                  }}
                >
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" strokeWidth={1.9} />
                  <span>{errorMsg}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={loading || (needsMFA ? totpCode.length !== 6 : (!email || !password))}
                className="group flex h-12 w-full cursor-pointer items-center justify-center gap-2 rounded-xl text-sm font-semibold transition-all duration-200 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                style={{
                  background: loading || (needsMFA ? totpCode.length !== 6 : (!email || !password)) ? 'rgba(56,189,248,0.25)' : 'var(--accent)',
                  color: loading || (needsMFA ? totpCode.length !== 6 : (!email || !password)) ? 'rgba(56,189,248,0.5)' : '#060D13',
                  boxShadow: loading || (needsMFA ? totpCode.length !== 6 : (!email || !password)) ? 'none' : '0 0 20px rgba(56,189,248,0.28)',
                }}
                onMouseEnter={(e) => {
                  if (!loading && (needsMFA ? totpCode.length === 6 : (email && password))) {
                    e.currentTarget.style.background = 'var(--accent-hover)'
                    e.currentTarget.style.boxShadow = '0 0 28px rgba(56,189,248,0.4)'
                  }
                }}
                onMouseLeave={(e) => {
                  if (!loading && (needsMFA ? totpCode.length === 6 : (email && password))) {
                    e.currentTarget.style.background = 'var(--accent)'
                    e.currentTarget.style.boxShadow = '0 0 20px rgba(56,189,248,0.28)'
                  }
                }}
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden>
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Ingresando...
                  </span>
                ) : (
                  <>
                    {needsMFA ? 'Verificar código' : 'Ingresar'}
                    <ArrowRight className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-0.5" strokeWidth={2} />
                  </>
                )}
              </button>
            </form>

            <div className="mt-6 flex items-center gap-3 rounded-xl px-4 py-3 text-xs text-text-secondary" style={{ background: 'rgba(255,255,255,0.035)' }}>
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-success" />
              Sesión protegida por Clerk y acceso por rol.
            </div>
          </div>

          <p
            className="mt-6 text-center text-xs stagger-3"
            style={{ color: 'var(--text-muted)' }}
          >
            ¿Problemas para ingresar?{' '}
            <span style={{ color: 'var(--text-secondary)' }}>
              Contacta al administrador
            </span>
          </p>
        </div>
      </div>
    </div>
  )
}
