'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { ExternalLink, CheckCircle, AlertCircle, Loader2, ArrowLeft } from 'lucide-react'
import Link from 'next/link'

interface InstagramConfig {
  phone_number_id: string
  waba_id: string
  activo: boolean
}

interface Step {
  number: number
  title: string
  items: string[]
  link?: { label: string; url: string }
  warning?: string
}

const STEPS: Step[] = [
  {
    number: 1,
    title: 'Ve a Meta for Developers',
    items: [
      'Abre developers.facebook.com en tu navegador',
      'Inicia sesión con tu cuenta de Facebook Business',
    ],
    link: { label: 'Abrir Meta Developers', url: 'https://developers.facebook.com' },
  },
  {
    number: 2,
    title: 'Crea o selecciona tu app',
    items: [
      'Haz click en "Mis Apps" → "Crear app"',
      'Tipo de app: selecciona "Business"',
      'Nombre: usa el nombre de tu negocio',
    ],
  },
  {
    number: 3,
    title: 'Agrega Messenger a tu app y vincula tu Página',
    items: [
      'En el panel de tu app, haz click en "Agregar producto"',
      'Busca "Messenger" y selecciónalo',
      'En Configuración de Messenger → vincula tu Página de Facebook',
      'Copia el Page ID que aparece en la sección "Páginas de Facebook"',
    ],
    warning: 'Tu Página de Facebook debe estar conectada a una cuenta de Instagram Business/Creator',
  },
  {
    number: 4,
    title: 'Vincula tu cuenta de Instagram Business',
    items: [
      'Ve a tu Página de Facebook → Configuración → Instagram',
      'Haz click en "Conectar cuenta" y sigue los pasos',
      'Asegúrate de que tu cuenta de Instagram esté en modo Business o Creator',
    ],
    link: { label: 'Ir a Meta Business Suite', url: 'https://business.facebook.com' },
  },
  {
    number: 5,
    title: 'Genera tu token de página permanente',
    items: [
      'Ve a Meta Business Suite → Configuración del negocio',
      'Usuarios del sistema → Crea un "Usuario del sistema administrador"',
      'Asígnale tu app con permisos: instagram_basic, instagram_manage_messages, pages_messaging',
      'Haz click en "Generar token" → selecciona tu Página → Guárdalo',
    ],
    link: { label: 'Abrir Configuración del Negocio', url: 'https://business.facebook.com/settings' },
  },
]

export default function InstagramConfigPage() {
  const [currentConfig, setCurrentConfig] = useState<InstagramConfig | null>(null)
  const [loadingConfig, setLoadingConfig] = useState(true)
  const [form, setForm] = useState({ page_id: '', access_token: '' })
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null)

  useEffect(() => {
    fetch('/api/cliente/instagram')
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data) setCurrentConfig(res.data)
      })
      .catch(console.error)
      .finally(() => setLoadingConfig(false))
  }, [])

  async function handleConnect(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setResult(null)

    try {
      const res = await fetch('/api/cliente/instagram', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await res.json()

      if (res.ok && data.success) {
        setResult({ ok: true, message: '✅ Instagram conectado exitosamente' })
        setCurrentConfig({ phone_number_id: form.page_id, waba_id: data.instagram_account_id, activo: true })
        setForm({ page_id: '', access_token: '' })
      } else {
        setResult({ ok: false, message: data.error ?? '❌ Error al verificar las credenciales' })
      }
    } catch {
      setResult({ ok: false, message: '❌ Error de conexión. Inténtalo de nuevo.' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <Link href="/cliente/configuracion" className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary mb-3">
          <ArrowLeft className="h-4 w-4" />
          Volver a Configuración
        </Link>
        <h1 className="text-2xl md:text-3xl font-bold text-text-primary">Conectar Instagram Business</h1>
        <p className="text-text-secondary mt-1 text-sm">
          Conecta tu cuenta de Instagram Business para activar el agente IA en tus DMs
        </p>
      </div>

      {!loadingConfig && currentConfig?.activo && (
        <Card className="border-success/30 bg-success/5">
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-3">
              <CheckCircle className="h-5 w-5 text-success shrink-0" />
              <div>
                <p className="font-medium text-success">Instagram conectado</p>
                <p className="text-sm text-text-secondary">
                  Page ID: <span className="font-mono">{currentConfig.phone_number_id}</span>
                  {currentConfig.waba_id && (
                    <> · Instagram Account ID: <span className="font-mono">{currentConfig.waba_id}</span></>
                  )}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Cómo conectar tu Instagram Business en 5 pasos</CardTitle>
          <CardDescription>Sigue esta guía antes de ingresar tus credenciales</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {STEPS.map((step, idx) => (
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
                  {step.link && (
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
          <CardTitle>Ingresa tus credenciales</CardTitle>
          <CardDescription>
            El sistema verificará automáticamente que la página tenga Instagram Business vinculado.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleConnect} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="page_id">Page ID de Facebook</Label>
              <Input
                id="page_id"
                placeholder="Ej: 123456789012345"
                value={form.page_id}
                onChange={(e) => setForm({ ...form, page_id: e.target.value })}
                required
              />
              <p className="text-xs text-text-muted">
                Lo encuentras en: Configuración de Messenger → Páginas de Facebook vinculadas
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="access_token">Token de acceso de página</Label>
              <Input
                id="access_token"
                type="password"
                placeholder="EAAxxxxxxxxxxxxxxxx..."
                value={form.access_token}
                onChange={(e) => setForm({ ...form, access_token: e.target.value })}
                required
              />
              <p className="text-xs text-text-muted">
                Generado en Meta Business Suite → Usuarios del sistema → Generar token
              </p>
            </div>

            {result && (
              <div className={[
                'flex items-start gap-2 rounded-md px-3 py-3 text-sm',
                result.ok ? 'bg-success/10 text-success' : 'bg-error/10 text-error',
              ].join(' ')}>
                {result.ok
                  ? <CheckCircle className="h-4 w-4 shrink-0 mt-0.5" />
                  : <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />}
                <span>{result.message}</span>
              </div>
            )}

            <Button type="submit" disabled={saving} className="w-full sm:w-auto">
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Verificando...
                </>
              ) : (
                'Verificar y conectar'
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
