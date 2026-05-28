'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { ExternalLink, CheckCircle, AlertCircle, Loader2, ArrowLeft, Calendar } from 'lucide-react'
import Link from 'next/link'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? ''

function buildSteps(serviceAccountEmail: string) {
  return [
    {
      number: 1,
      title: 'Abre Google Calendar',
      items: ['Ve a calendar.google.com', 'Inicia sesión con tu cuenta de Google'],
      link: { label: 'Abrir Google Calendar', url: 'https://calendar.google.com' },
    },
    {
      number: 2,
      title: 'Crea o selecciona un calendario',
      items: [
        'En el panel izquierdo, haz clic en "+" junto a "Otros calendarios"',
        'Selecciona "Crear nuevo calendario"',
        'Dale un nombre (ej: "Citas de clientes") y guarda',
      ],
    },
    {
      number: 3,
      title: 'Comparte el calendario con el agente',
      items: [
        'Haz clic en los tres puntos (...) junto al calendario creado',
        'Selecciona "Configuración y uso compartido"',
        'En "Compartir con personas específicas", haz clic en "+ Agregar personas"',
        `Ingresa este email: ${serviceAccountEmail || '(cargando…)'}`,
        'Permiso: "Realizar cambios en eventos" → Guardar',
      ],
      warning: serviceAccountEmail
        ? `Usa exactamente este email: ${serviceAccountEmail}`
        : undefined,
    },
    {
      number: 4,
      title: 'Copia el ID del calendario',
      items: [
        'En la misma pantalla de configuración, baja hasta "Integrar el calendario"',
        'Copia el "ID de calendario" (termina en @group.calendar.google.com o es un email)',
        'Pégalo en el campo de abajo',
      ],
    },
  ]
}

export default function CalendarConfigPage() {
  const [currentCalendarId, setCurrentCalendarId] = useState<string | null>(null)
  const [serviceAccountEmail, setServiceAccountEmail] = useState('')
  const [loadingConfig, setLoadingConfig] = useState(true)
  const [calendarId, setCalendarId] = useState('')
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null)

  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
    const headers: Record<string, string> = {}
    if (token) headers['Authorization'] = `Bearer ${token}`

    Promise.all([
      fetch('/api/cliente/calendar').then((r) => r.json()),
      fetch(`${API_URL}/api/calendar/service-account-email`, { headers }).then((r) => r.json()).catch(() => ({ success: false })),
    ]).then(([calRes, saRes]) => {
      if (calRes.success && calRes.data?.google_calendar_id) {
        setCurrentCalendarId(calRes.data.google_calendar_id)
      }
      if (saRes.success && saRes.email) {
        setServiceAccountEmail(saRes.email)
      }
    }).catch(console.error).finally(() => setLoadingConfig(false))
  }, [])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!calendarId.trim()) return

    setSaving(true)
    setResult(null)

    try {
      const res = await fetch('/api/cliente/calendar', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ google_calendar_id: calendarId.trim() }),
      })
      const data = await res.json()

      if (res.ok && data.success) {
        setResult({ ok: true, message: '✅ Calendar ID guardado exitosamente' })
        setCurrentCalendarId(calendarId.trim())
        setCalendarId('')
      } else {
        setResult({ ok: false, message: data.error ?? '❌ Error al guardar la configuración' })
      }
    } catch {
      setResult({ ok: false, message: '❌ Error de conexión. Inténtalo de nuevo.' })
    } finally {
      setSaving(false)
    }
  }

  const steps = buildSteps(serviceAccountEmail)

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

      {!loadingConfig && currentCalendarId && (
        <Card className="border-success/30 bg-success/5">
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-3">
              <CheckCircle className="h-5 w-5 text-success shrink-0" />
              <div>
                <p className="font-medium text-success">Calendar conectado</p>
                <p className="text-sm text-text-secondary font-mono break-all">{currentCalendarId}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {serviceAccountEmail && (
        <Card className="border-surface bg-surface/50">
          <CardContent className="pt-4 pb-4">
            <div className="flex items-start gap-3">
              <Calendar className="h-5 w-5 text-accent shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-text-primary">Email de la cuenta de servicio</p>
                <p className="text-xs text-text-secondary mt-1">
                  Comparte tu calendario con este email para que el agente pueda crear y gestionar citas:
                </p>
                <p className="text-xs font-mono text-accent mt-1 break-all select-all">{serviceAccountEmail}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Cómo conectar tu Google Calendar en 4 pasos</CardTitle>
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

      <Card>
        <CardHeader>
          <CardTitle>Ingresa tu Calendar ID</CardTitle>
          <CardDescription>
            Lo encuentras en Google Calendar → Configuración del calendario → Integrar el calendario
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSave} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="calendar_id">Calendar ID</Label>
              <Input
                id="calendar_id"
                placeholder="ej: abc123xyz@group.calendar.google.com"
                value={calendarId}
                onChange={(e) => setCalendarId(e.target.value)}
                required
              />
              <p className="text-xs text-text-muted">
                Puede ser un email de Gmail o terminar en @group.calendar.google.com
              </p>
            </div>

            {result && (
              <div
                className={`flex items-start gap-2 rounded-md px-3 py-3 text-sm ${
                  result.ok ? 'bg-success/10 text-success' : 'bg-error/10 text-error'
                }`}
              >
                {result.ok ? (
                  <CheckCircle className="h-4 w-4 shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                )}
                <span>{result.message}</span>
              </div>
            )}

            <Button type="submit" disabled={saving} className="w-full sm:w-auto">
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Guardando...
                </>
              ) : (
                'Guardar Calendar ID'
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
