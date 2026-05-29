'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import { ExternalLink, CheckCircle, AlertCircle, Loader2, ArrowLeft, Calendar, Eye, EyeOff } from 'lucide-react'
import Link from 'next/link'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? ''

function buildSteps(serviceAccountEmail: string) {
  return [
    {
      number: 1,
      title: 'Crea un Service Account en Google Cloud',
      items: [
        'Ve a Google Cloud Console → IAM & Admin → Service Accounts',
        'Crea un Service Account nuevo',
        'En "Keys" → "Add Key" → "Create new key" → JSON',
        'Descarga el archivo JSON generado',
      ],
      link: { label: 'Abrir Google Cloud Console', url: 'https://console.cloud.google.com/iam-admin/serviceaccounts' },
    },
    {
      number: 2,
      title: 'Comparte el calendario con el agente',
      items: [
        'Ve a Google Calendar → Configuración del calendario',
        'En "Compartir con personas específicas" → "+ Agregar personas"',
        `Ingresa el email del Service Account: ${serviceAccountEmail || '(pega primero las credenciales)'}`,
        'Permiso: "Realizar cambios en eventos" → Guardar',
      ],
      warning: serviceAccountEmail
        ? `Comparte el calendario con: ${serviceAccountEmail}`
        : undefined,
    },
    {
      number: 3,
      title: 'Copia el ID del calendario',
      items: [
        'En la configuración del calendario, baja hasta "Integrar el calendario"',
        'Copia el "ID de calendario" (termina en @group.calendar.google.com o es un email)',
        'Pégalo en el campo Calendar ID de abajo',
      ],
    },
  ]
}

export default function CalendarConfigPage() {
  const [currentCalendarId, setCurrentCalendarId] = useState<string | null>(null)
  const [hasCredentials, setHasCredentials] = useState(false)
  const [credentialsEmail, setCredentialsEmail] = useState<string | null>(null)
  const [globalServiceEmail, setGlobalServiceEmail] = useState('')
  const [loadingConfig, setLoadingConfig] = useState(true)

  const [calendarId, setCalendarId] = useState('')
  const [credentialsJson, setCredentialsJson] = useState('')
  const [showJson, setShowJson] = useState(false)
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null)

  // Validate credentials JSON in real time
  const jsonValidation = (() => {
    if (!credentialsJson.trim()) return null
    try {
      const p = JSON.parse(credentialsJson)
      if (p.type !== 'service_account') return { ok: false, message: 'Debe ser tipo "service_account"' }
      if (!p.client_email || !p.private_key) return { ok: false, message: 'Faltan campos: client_email o private_key' }
      return { ok: true, message: p.client_email as string }
    } catch {
      return { ok: false, message: 'JSON inválido' }
    }
  })()

  const displayedEmail = credentialsEmail ?? globalServiceEmail

  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
    const headers: Record<string, string> = {}
    if (token) headers['Authorization'] = `Bearer ${token}`

    Promise.all([
      fetch('/api/cliente/calendar').then((r) => r.json()),
      fetch(`${API_URL}/api/calendar/service-account-email`, { headers })
        .then((r) => r.json())
        .catch(() => ({ success: false })),
    ])
      .then(([calRes, saRes]) => {
        if (calRes.success && calRes.data) {
          setCurrentCalendarId(calRes.data.google_calendar_id ?? null)
          setHasCredentials(calRes.data.has_credentials ?? false)
          setCredentialsEmail(calRes.data.credentials_email ?? null)
        }
        if (saRes.success && saRes.email) {
          setGlobalServiceEmail(saRes.email)
        }
      })
      .catch(console.error)
      .finally(() => setLoadingConfig(false))
  }, [])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!calendarId.trim()) return
    if (credentialsJson && jsonValidation && !jsonValidation.ok) return

    setSaving(true)
    setResult(null)

    try {
      const body: Record<string, string> = { google_calendar_id: calendarId.trim() }
      if (credentialsJson.trim()) body.google_calendar_credentials_json = credentialsJson.trim()

      const res = await fetch('/api/cliente/calendar', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()

      if (res.ok && data.success) {
        setResult({ ok: true, message: 'Configuración guardada exitosamente' })
        setCurrentCalendarId(calendarId.trim())
        if (credentialsJson.trim() && jsonValidation?.ok) {
          setHasCredentials(true)
          setCredentialsEmail(jsonValidation.message)
        }
        setCalendarId('')
        setCredentialsJson('')
      } else {
        setResult({ ok: false, message: data.error ?? 'Error al guardar la configuración' })
      }
    } catch {
      setResult({ ok: false, message: 'Error de conexión. Inténtalo de nuevo.' })
    } finally {
      setSaving(false)
    }
  }

  const steps = buildSteps(jsonValidation?.ok ? jsonValidation.message : displayedEmail)

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <Link href="/cliente/configuracion" className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary mb-3">
          <ArrowLeft className="h-4 w-4" />
          Volver a Configuración
        </Link>
        <h1 className="text-2xl md:text-3xl font-bold text-text-primary">Conectar Google Calendar</h1>
        <p className="text-text-secondary mt-1 text-sm">
          Conecta un calendario de Google para que el agente gestione citas automáticamente
        </p>
      </div>

      {/* Current status */}
      {!loadingConfig && currentCalendarId && (
        <Card className="border-success/30 bg-success/5">
          <CardContent className="pt-4 pb-4">
            <div className="flex items-start gap-3">
              <CheckCircle className="h-5 w-5 text-success shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-medium text-success">Calendar conectado</p>
                <p className="text-sm text-text-secondary font-mono break-all">{currentCalendarId}</p>
                {hasCredentials && credentialsEmail && (
                  <p className="text-xs text-text-secondary">
                    Cuenta de servicio: <span className="font-mono text-accent">{credentialsEmail}</span>
                  </p>
                )}
                {!hasCredentials && (
                  <p className="text-xs text-warning flex items-center gap-1">
                    <AlertCircle className="h-3 w-3 shrink-0" />
                    Sin credenciales propias — usando cuenta global del sistema
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Guide */}
      <Card>
        <CardHeader>
          <CardTitle>Cómo conectar tu Google Calendar</CardTitle>
          <CardDescription>Sigue esta guía antes de ingresar tu Calendar ID</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {steps.map((step, idx) => (
            <div key={step.number}>
              {idx > 0 && <Separator className="mb-6" />}
              <div className="flex gap-4">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent text-white text-sm font-bold">
                  {step.number}
                </div>
                <div className="space-y-2 flex-1">
                  <p className="font-semibold text-text-primary">{step.title}</p>
                  <ul className="space-y-1">
                    {step.items.map((item) => (
                      <li key={item} className="flex items-start gap-2 text-sm text-text-secondary">
                        <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-text-muted shrink-0" />
                        {item}
                      </li>
                    ))}
                  </ul>
                  {step.warning && (
                    <div className="flex items-start gap-2 rounded-md bg-warning/10 px-3 py-2">
                      <AlertCircle className="h-4 w-4 text-warning shrink-0 mt-0.5" />
                      <p className="text-sm text-warning font-medium">{step.warning}</p>
                    </div>
                  )}
                  {'link' in step && step.link && (
                    <a href={step.link.url} target="_blank" rel="noopener noreferrer">
                      <Button variant="outline" size="sm" className="gap-2 mt-1">
                        {step.link.label}
                        <ExternalLink className="h-3.5 w-3.5" />
                      </Button>
                    </a>
                  )}
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Form */}
      <Card>
        <CardHeader>
          <CardTitle>Credenciales y Calendar ID</CardTitle>
          <CardDescription>
            Ingresa las credenciales del Service Account y el ID de tu calendario
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSave} className="space-y-5">

            {/* Credentials JSON */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="credentials_json">
                  {hasCredentials ? 'Actualizar credenciales (Service Account JSON)' : 'Credenciales Service Account (JSON)'}
                </Label>
                <button
                  type="button"
                  onClick={() => setShowJson(!showJson)}
                  className="flex items-center gap-1 text-xs text-text-secondary hover:text-text-primary transition-colors"
                >
                  {showJson ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                  {showJson ? 'Ocultar' : 'Mostrar'}
                </button>
              </div>
              <Textarea
                id="credentials_json"
                rows={showJson ? 10 : 4}
                placeholder={
                  hasCredentials
                    ? 'Pega el nuevo JSON para actualizar las credenciales...'
                    : '{"type": "service_account", "project_id": "...", "client_email": "...", "private_key": "..."}'
                }
                className="font-mono text-xs resize-none"
                value={credentialsJson}
                onChange={(e) => {
                  setCredentialsJson(e.target.value)
                  setResult(null)
                }}
              />
              {credentialsJson && jsonValidation && (
                <div className={`flex items-center gap-1.5 text-xs ${jsonValidation.ok ? 'text-success' : 'text-error'}`}>
                  {jsonValidation.ok
                    ? <><CheckCircle className="h-3.5 w-3.5 shrink-0" /> JSON válido — cuenta: <span className="font-mono">{jsonValidation.message}</span></>
                    : <><AlertCircle className="h-3.5 w-3.5 shrink-0" /> {jsonValidation.message}</>
                  }
                </div>
              )}
              {hasCredentials && !credentialsJson && (
                <p className="text-xs text-text-muted">
                  Deja vacío para mantener las credenciales actuales
                  {credentialsEmail && <> (<span className="font-mono">{credentialsEmail}</span>)</>}.
                </p>
              )}
            </div>

            <Separator />

            {/* Calendar ID */}
            <div className="space-y-2">
              <Label htmlFor="calendar_id">Calendar ID *</Label>
              <Input
                id="calendar_id"
                placeholder="ej: abc123xyz@group.calendar.google.com"
                value={calendarId}
                onChange={(e) => {
                  setCalendarId(e.target.value)
                  setResult(null)
                }}
                required
              />
              <p className="text-xs text-text-muted">
                Lo encuentras en Google Calendar → Configuración del calendario → Integrar el calendario
              </p>
            </div>

            {result && (
              <div
                className={`flex items-start gap-2 rounded-md px-3 py-3 text-sm ${
                  result.ok ? 'bg-success/10 text-success' : 'bg-error/10 text-error'
                }`}
              >
                {result.ok
                  ? <CheckCircle className="h-4 w-4 shrink-0 mt-0.5" />
                  : <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                }
                <span>{result.message}</span>
              </div>
            )}

            <Button
              type="submit"
              disabled={saving || (!!credentialsJson && !!jsonValidation && !jsonValidation.ok)}
              className="w-full sm:w-auto"
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Guardando...
                </>
              ) : (
                <>
                  <Calendar className="h-4 w-4 mr-2" />
                  Guardar configuración
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
