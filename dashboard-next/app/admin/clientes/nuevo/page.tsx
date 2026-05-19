'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import Link from 'next/link'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { CheckCircle, Circle, Copy, ExternalLink } from 'lucide-react'

// ─── Constants ────────────────────────────────────────────────────────────────

const PLANES = [
  {
    id: 'basico',
    label: 'Plan Básico',
    precio: 149,
    descripcion: 'Agente WhatsApp + calificación de leads',
    modulos: ['ventas', 'calificacion', 'alertas'],
  },
  {
    id: 'profesional',
    label: 'Plan Profesional',
    precio: 249,
    descripcion: 'Todo lo básico + Instagram + Facebook + Analytics',
    modulos: ['ventas', 'calificacion', 'alertas', 'seguimientos', 'analytics'],
  },
  {
    id: 'empresarial',
    label: 'Plan Empresarial',
    precio: 399,
    descripcion: 'Todo incluido + cobros + llamadas',
    modulos: ['ventas', 'agendamiento', 'cobros', 'links_pago', 'calificacion', 'campanas', 'analytics', 'alertas', 'seguimientos'],
  },
] as const

type PlanId = 'basico' | 'profesional' | 'empresarial'

const TODOS_LOS_MODULOS = [
  { key: 'ventas', label: 'Ventas', desc: 'Catálogo, cotizaciones, objecciones' },
  { key: 'agendamiento', label: 'Agendamiento', desc: 'Integración Google Calendar' },
  { key: 'cobros', label: 'Cobros', desc: 'Verificación de pagos con IA Vision' },
  { key: 'links_pago', label: 'Links de Pago', desc: 'Stripe, MercadoPago, PayPal' },
  { key: 'calificacion', label: 'Calificación', desc: 'Scoring automático de leads' },
  { key: 'campanas', label: 'Campañas', desc: 'Mensajería masiva' },
  { key: 'analytics', label: 'Analytics', desc: 'Reportes y métricas' },
  { key: 'alertas', label: 'Alertas', desc: 'Notificaciones del sistema' },
  { key: 'seguimientos', label: 'Seguimientos', desc: 'Follow-ups automáticos' },
]

const INDUSTRIAS = [
  'restaurante',
  'retail / tienda',
  'servicios profesionales',
  'salud / clínica',
  'educación',
  'inmobiliaria',
  'automotriz',
  'tecnología',
  'construcción',
  'otro',
]

const BANCOS_ECUADOR = [
  'Banco Pichincha',
  'Banco Guayaquil',
  'Banco Pacífico',
  'Produbanco',
  'Banco Internacional',
  'Banco Bolivariano',
  'Cooperativa JEP',
  'Otro',
]

// ─── Types ────────────────────────────────────────────────────────────────────

interface FormData {
  // Paso 1 – Datos del negocio
  nombre: string
  email: string
  telefono: string
  whatsapp_dueño: string
  industria: string
  website: string
  plan: PlanId
  modulos: Record<string, boolean>

  // Agente
  nombreAgente: string
  tono: string
  idioma: string
  modelo: string
  systemPrompt: string

  // Paso 2 – WhatsApp
  whatsappEnabled: boolean
  whatsappPhone: string
  whatsappToken: string
  whatsappWabaId: string

  // Paso 3 – Datos bancarios
  banco: string
  tipo_cuenta: 'corriente' | 'ahorros'
  numero_cuenta: string
  titular: string
  ruc: string
}

function modulosFromPlan(planId: PlanId): Record<string, boolean> {
  const plan = PLANES.find((p) => p.id === planId)
  const activos = new Set<string>(plan?.modulos ?? [])
  return Object.fromEntries(TODOS_LOS_MODULOS.map((m) => [m.key, activos.has(m.key)]))
}

const defaultModulos = modulosFromPlan('basico')

// ─── Component ────────────────────────────────────────────────────────────────

export default function NuevoClientePage() {
  const router = useRouter()
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [clienteCreado, setClienteCreado] = useState<{ clienteId: string; email: string; password: string } | null>(null)
  const [copied, setCopied] = useState(false)

  const [formData, setFormData] = useState<FormData>({
    nombre: '',
    email: '',
    telefono: '',
    whatsapp_dueño: '',
    industria: '',
    website: '',
    plan: 'basico',
    modulos: defaultModulos,

    nombreAgente: '',
    tono: 'Amigable',
    idioma: 'Español',
    modelo: 'GPT-4o',
    systemPrompt: '',

    whatsappEnabled: true,
    whatsappPhone: '',
    whatsappToken: '',
    whatsappWabaId: '',

    banco: '',
    tipo_cuenta: 'ahorros',
    numero_cuenta: '',
    titular: '',
    ruc: '',
  })

  const set = (field: keyof FormData, value: unknown) =>
    setFormData((prev) => ({ ...prev, [field]: value }))

  const handlePlanChange = (planId: PlanId) => {
    setFormData((prev) => ({
      ...prev,
      plan: planId,
      modulos: modulosFromPlan(planId),
    }))
  }

  const handleModuloChange = (key: string, checked: boolean) =>
    setFormData((prev) => ({
      ...prev,
      modulos: { ...prev.modulos, [key]: checked },
    }))

  // ── Validations per step ──────────────────────────────────────────────────

  const validateStep1 = (): string | null => {
    if (!formData.nombre.trim()) return 'El nombre del negocio es requerido'
    if (!formData.email.trim() || !formData.email.includes('@')) return 'Email inválido'
    if (!formData.telefono.trim()) return 'El teléfono es requerido'
    if (!formData.whatsapp_dueño.trim()) return 'El WhatsApp del dueño es requerido'
    if (!formData.industria) return 'Selecciona la industria'
    if (!formData.nombreAgente.trim()) return 'El nombre del agente es requerido'
    if (!formData.systemPrompt.trim()) return 'El system prompt es requerido'
    return null
  }

  const validateStep2 = (): string | null => {
    if (formData.whatsappEnabled) {
      if (!formData.whatsappPhone.trim()) return 'El Phone Number ID es requerido'
      if (!formData.whatsappToken.trim()) return 'El Token de WhatsApp es requerido'
      if (!formData.whatsappWabaId.trim()) return 'El WABA ID es requerido'
    }
    return null
  }

  const goNext = () => {
    setError('')
    let err: string | null = null
    if (step === 1) err = validateStep1()
    if (step === 2) err = validateStep2()
    if (err) { setError(err); return }
    setStep((s) => s + 1)
  }

  const goBack = () => { setError(''); setStep((s) => s - 1) }

  // ── Submit ────────────────────────────────────────────────────────────────

  const handleSubmit = async () => {
    setError('')
    setLoading(true)

    try {
      const response = await fetch('/api/clientes/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nombre: formData.nombre,
          email: formData.email,
          telefono: formData.telefono,
          whatsapp_dueño: formData.whatsapp_dueño,
          industria: formData.industria,
          website: formData.website,
          plan: formData.plan,
          precio_mensual: PLANES.find((p) => p.id === formData.plan)?.precio ?? 0,
          nombreAgente: formData.nombreAgente,
          tono: formData.tono,
          idioma: formData.idioma,
          modelo: formData.modelo,
          systemPrompt: formData.systemPrompt,
          modulos: formData.modulos,
          whatsappEnabled: formData.whatsappEnabled,
          whatsappPhone: formData.whatsappPhone,
          whatsappToken: formData.whatsappToken,
          whatsappWabaId: formData.whatsappWabaId,
          banco: formData.banco,
          tipo_cuenta: formData.tipo_cuenta,
          numero_cuenta: formData.numero_cuenta,
          titular: formData.titular,
          ruc: formData.ruc,
        }),
      })

      const data = await response.json()
      if (!data.success) throw new Error(data.error || 'Error al crear el cliente')

      setClienteCreado(data.data)
      setSuccess(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear el cliente')
    } finally {
      setLoading(false)
    }
  }

  const copyCredentials = () => {
    if (!clienteCreado) return
    const text = `Email: ${clienteCreado.email}\nContraseña temporal: ${clienteCreado.password}`
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // ── Shared plan info ──────────────────────────────────────────────────────
  const planActual = PLANES.find((p) => p.id === formData.plan)!
  const modulosActivos = TODOS_LOS_MODULOS.filter((m) => formData.modulos[m.key])

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <div>
        <Link href="/admin/clientes" className="text-accent hover:text-accent-hover mb-2 inline-block">
          ← Volver
        </Link>
        <h1 className="text-3xl font-bold text-text-primary">Nuevo Cliente</h1>
        <p className="text-text-secondary mt-2">Configura el agente IA de tu nuevo cliente en 4 pasos</p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2">
        {['Negocio', 'WhatsApp', 'Banco', 'Resumen'].map((label, i) => {
          const n = i + 1
          const done = step > n
          const active = step === n
          return (
            <div key={n} className="flex items-center gap-2">
              <div className={`flex items-center gap-1.5 text-sm font-medium ${active ? 'text-accent' : done ? 'text-success' : 'text-text-muted'}`}>
                {done
                  ? <CheckCircle className="h-5 w-5 text-success" />
                  : <Circle className={`h-5 w-5 ${active ? 'text-accent' : 'text-text-muted'}`} />}
                {label}
              </div>
              {i < 3 && <div className="h-px w-6 bg-border" />}
            </div>
          )
        })}
      </div>

      {error && (
        <div className="bg-error/10 border border-error text-error px-4 py-3 rounded text-sm">
          {error}
        </div>
      )}

      {/* ── PASO 1: Datos del negocio ───────────────────────────────────────── */}
      {step === 1 && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Datos del Negocio</CardTitle>
              <CardDescription>Información principal del cliente</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="nombre">Nombre del Negocio *</Label>
                  <Input
                    id="nombre"
                    placeholder="Ej: Restaurante El Buen Sabor"
                    value={formData.nombre}
                    onChange={(e) => set('nombre', e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Email *</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="admin@negocio.com"
                    value={formData.email}
                    onChange={(e) => set('email', e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="telefono">Teléfono *</Label>
                  <Input
                    id="telefono"
                    placeholder="+593 99 123 4567"
                    value={formData.telefono}
                    onChange={(e) => set('telefono', e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="whatsapp_dueño">WhatsApp del Dueño *</Label>
                  <Input
                    id="whatsapp_dueño"
                    placeholder="+593XXXXXXXXX"
                    value={formData.whatsapp_dueño}
                    onChange={(e) => set('whatsapp_dueño', e.target.value)}
                  />
                  <p className="text-xs text-text-muted">Para recibir alertas importantes del agente</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="industria">Industria *</Label>
                  <Select
                    id="industria"
                    value={formData.industria}
                    onChange={(e) => set('industria', e.target.value)}
                  >
                    <option value="">Seleccionar industria...</option>
                    {INDUSTRIAS.map((ind) => (
                      <option key={ind} value={ind}>{ind.charAt(0).toUpperCase() + ind.slice(1)}</option>
                    ))}
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="website">Sitio Web <span className="text-text-muted">(opcional)</span></Label>
                  <Input
                    id="website"
                    placeholder="https://minegocio.com"
                    value={formData.website}
                    onChange={(e) => set('website', e.target.value)}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Plan</CardTitle>
              <CardDescription>Los módulos se activan automáticamente según el plan</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {PLANES.map((plan) => (
                  <button
                    key={plan.id}
                    type="button"
                    onClick={() => handlePlanChange(plan.id)}
                    className={`text-left p-4 rounded-lg border-2 transition-colors ${
                      formData.plan === plan.id
                        ? 'border-accent bg-accent/5'
                        : 'border-border hover:border-accent/50'
                    }`}
                  >
                    <div className="font-semibold text-text-primary">{plan.label}</div>
                    <div className="text-2xl font-bold text-accent mt-1">${plan.precio}<span className="text-sm font-normal text-text-muted">/mes</span></div>
                    <div className="text-xs text-text-secondary mt-2">{plan.descripcion}</div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {plan.modulos.map((m) => (
                        <span key={m} className="text-xs bg-surface px-1.5 py-0.5 rounded text-text-muted">{m}</span>
                      ))}
                    </div>
                  </button>
                ))}
              </div>

              <Separator />

              <div>
                <p className="text-sm font-medium text-text-primary mb-3">Módulos activos para <span className="text-accent">{planActual.label}</span></p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {TODOS_LOS_MODULOS.map((m) => (
                    <div key={m.key} className="flex items-center justify-between">
                      <div>
                        <span className="text-sm font-medium text-text-primary">{m.label}</span>
                        <p className="text-xs text-text-muted">{m.desc}</p>
                      </div>
                      <Switch
                        checked={formData.modulos[m.key] ?? false}
                        onChange={(checked) => handleModuloChange(m.key, checked)}
                      />
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Configuración del Agente</CardTitle>
              <CardDescription>Personaliza el comportamiento inicial del agente</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="agent-name">Nombre del Agente *</Label>
                  <Input
                    id="agent-name"
                    placeholder="Ej: Sofia"
                    value={formData.nombreAgente}
                    onChange={(e) => set('nombreAgente', e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="tone">Tono</Label>
                  <Select id="tone" value={formData.tono} onChange={(e) => set('tono', e.target.value)}>
                    <option>Amigable</option>
                    <option>Formal</option>
                    <option>Profesional</option>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="language">Idioma</Label>
                  <Select id="language" value={formData.idioma} onChange={(e) => set('idioma', e.target.value)}>
                    <option>Español</option>
                    <option>Inglés</option>
                    <option>Portugués</option>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="model">Modelo IA</Label>
                  <Select id="model" value={formData.modelo} onChange={(e) => set('modelo', e.target.value)}>
                    <option>GPT-4o</option>
                    <option>GPT-4 Turbo</option>
                    <option>GPT-3.5 Turbo</option>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="system-prompt">System Prompt *</Label>
                <Textarea
                  id="system-prompt"
                  placeholder="Eres un asistente amable que ayuda a los clientes de [nombre negocio] con sus preguntas sobre productos y servicios..."
                  className="min-h-32"
                  value={formData.systemPrompt}
                  onChange={(e) => set('systemPrompt', e.target.value)}
                />
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button type="button" onClick={goNext}>Siguiente: WhatsApp →</Button>
          </div>
        </div>
      )}

      {/* ── PASO 2: Configuración WhatsApp ──────────────────────────────────── */}
      {step === 2 && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Configuración WhatsApp</CardTitle>
              <CardDescription>Conecta el número de WhatsApp Business del cliente</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-base font-medium">Activar WhatsApp</Label>
                  <p className="text-sm text-text-muted">El cliente recibirá mensajes a través de WhatsApp</p>
                </div>
                <Switch
                  checked={formData.whatsappEnabled}
                  onChange={(checked) => set('whatsappEnabled', checked)}
                />
              </div>

              {formData.whatsappEnabled && (
                <>
                  <Separator />

                  {/* Instructions */}
                  <div className="bg-surface rounded-lg p-4 space-y-3 text-sm">
                    <p className="font-semibold text-text-primary">Cómo obtener los datos de Meta:</p>
                    <ol className="space-y-2 text-text-secondary list-decimal list-inside">
                      <li>
                        Entra a{' '}
                        <a
                          href="https://developers.facebook.com/apps"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-accent hover:underline inline-flex items-center gap-1"
                        >
                          Meta for Developers <ExternalLink className="h-3 w-3" />
                        </a>{' '}
                        y selecciona tu app.
                      </li>
                      <li>
                        Ve a <strong>WhatsApp → Configuración de API</strong> para encontrar el <strong>Phone Number ID</strong> y el <strong>WABA ID</strong>.
                      </li>
                      <li>
                        El <strong>Token</strong> se genera en{' '}
                        <a
                          href="https://developers.facebook.com/tools/explorer"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-accent hover:underline inline-flex items-center gap-1"
                        >
                          Graph API Explorer <ExternalLink className="h-3 w-3" />
                        </a>{' '}
                        o en <strong>Configuración → Token de acceso permanente</strong>.
                      </li>
                    </ol>
                  </div>

                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="wp-phone">Phone Number ID *</Label>
                      <Input
                        id="wp-phone"
                        placeholder="Ej: 123456789012345"
                        value={formData.whatsappPhone}
                        onChange={(e) => set('whatsappPhone', e.target.value)}
                      />
                      <p className="text-xs text-text-muted">Número de 15 dígitos que identifica tu número de WhatsApp en Meta</p>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="wp-waba">WABA ID *</Label>
                      <Input
                        id="wp-waba"
                        placeholder="Ej: 987654321098765"
                        value={formData.whatsappWabaId}
                        onChange={(e) => set('whatsappWabaId', e.target.value)}
                      />
                      <p className="text-xs text-text-muted">ID de tu cuenta de WhatsApp Business (distinto al Phone Number ID)</p>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="wp-token">Token de Acceso *</Label>
                      <Input
                        id="wp-token"
                        placeholder="EAAB..."
                        value={formData.whatsappToken}
                        onChange={(e) => set('whatsappToken', e.target.value)}
                      />
                      <p className="text-xs text-text-muted">Token permanente de acceso a la API de WhatsApp</p>
                    </div>
                  </div>
                </>
              )}

              {!formData.whatsappEnabled && (
                <div className="text-center py-6 text-text-muted text-sm">
                  WhatsApp desactivado. Podrás configurarlo después desde el perfil del cliente.
                </div>
              )}
            </CardContent>
          </Card>

          <div className="flex justify-between">
            <Button type="button" variant="outline" onClick={goBack}>← Anterior</Button>
            <Button type="button" onClick={goNext}>Siguiente: Datos Bancarios →</Button>
          </div>
        </div>
      )}

      {/* ── PASO 3: Datos bancarios ─────────────────────────────────────────── */}
      {step === 3 && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Datos Bancarios</CardTitle>
              <CardDescription>Cuenta donde el cliente recibirá sus pagos <span className="text-text-muted">(opcional)</span></CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="banco">Banco</Label>
                  <Select id="banco" value={formData.banco} onChange={(e) => set('banco', e.target.value)}>
                    <option value="">Seleccionar banco...</option>
                    {BANCOS_ECUADOR.map((b) => (
                      <option key={b} value={b}>{b}</option>
                    ))}
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="tipo_cuenta">Tipo de Cuenta</Label>
                  <Select
                    id="tipo_cuenta"
                    value={formData.tipo_cuenta}
                    onChange={(e) => set('tipo_cuenta', e.target.value as 'corriente' | 'ahorros')}
                  >
                    <option value="ahorros">Ahorros</option>
                    <option value="corriente">Corriente</option>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="numero_cuenta">Número de Cuenta</Label>
                  <Input
                    id="numero_cuenta"
                    placeholder="Ej: 2200123456"
                    value={formData.numero_cuenta}
                    onChange={(e) => set('numero_cuenta', e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="titular">Titular de la Cuenta</Label>
                  <Input
                    id="titular"
                    placeholder="Nombre completo del titular"
                    value={formData.titular}
                    onChange={(e) => set('titular', e.target.value)}
                  />
                </div>

                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="ruc">RUC <span className="text-text-muted">(opcional)</span></Label>
                  <Input
                    id="ruc"
                    placeholder="Ej: 1712345678001"
                    value={formData.ruc}
                    onChange={(e) => set('ruc', e.target.value)}
                  />
                </div>
              </div>

              <p className="text-xs text-text-muted">
                Estos datos se guardan de forma segura y son usados cuando el agente genera links de pago por transferencia.
              </p>
            </CardContent>
          </Card>

          <div className="flex justify-between">
            <Button type="button" variant="outline" onClick={goBack}>← Anterior</Button>
            <Button type="button" onClick={goNext}>Siguiente: Resumen →</Button>
          </div>
        </div>
      )}

      {/* ── PASO 4: Resumen ─────────────────────────────────────────────────── */}
      {step === 4 && !success && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Resumen del Cliente</CardTitle>
              <CardDescription>Revisa los datos antes de crear al cliente</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Negocio */}
              <div>
                <p className="text-sm font-semibold text-text-primary mb-2">Negocio</p>
                <div className="grid grid-cols-2 gap-y-1 text-sm">
                  <span className="text-text-muted">Nombre:</span><span className="text-text-primary font-medium">{formData.nombre}</span>
                  <span className="text-text-muted">Email:</span><span className="text-text-primary">{formData.email}</span>
                  <span className="text-text-muted">Teléfono:</span><span className="text-text-primary">{formData.telefono}</span>
                  <span className="text-text-muted">WhatsApp dueño:</span><span className="text-text-primary">{formData.whatsapp_dueño}</span>
                  <span className="text-text-muted">Industria:</span><span className="text-text-primary capitalize">{formData.industria || '-'}</span>
                  <span className="text-text-muted">Website:</span><span className="text-text-primary">{formData.website || '-'}</span>
                </div>
              </div>

              <Separator />

              {/* Plan */}
              <div>
                <p className="text-sm font-semibold text-text-primary mb-2">Plan</p>
                <div className="flex items-center gap-3">
                  <span className="text-accent font-bold text-lg">{planActual.label}</span>
                  <span className="text-text-secondary">${planActual.precio}/mes</span>
                </div>
                <p className="text-sm text-text-muted mt-1">{planActual.descripcion}</p>
              </div>

              <Separator />

              {/* Módulos */}
              <div>
                <p className="text-sm font-semibold text-text-primary mb-2">Módulos activos ({modulosActivos.length})</p>
                <div className="flex flex-wrap gap-2">
                  {modulosActivos.map((m) => (
                    <span key={m.key} className="text-xs bg-success/10 text-success px-2 py-1 rounded-full font-medium">
                      ✓ {m.label}
                    </span>
                  ))}
                  {TODOS_LOS_MODULOS.filter((m) => !formData.modulos[m.key]).map((m) => (
                    <span key={m.key} className="text-xs bg-surface text-text-muted px-2 py-1 rounded-full">
                      {m.label}
                    </span>
                  ))}
                </div>
              </div>

              <Separator />

              {/* WhatsApp */}
              <div>
                <p className="text-sm font-semibold text-text-primary mb-2">WhatsApp</p>
                {formData.whatsappEnabled ? (
                  <div className="grid grid-cols-2 gap-y-1 text-sm">
                    <span className="text-text-muted">Estado:</span>
                    <span className="text-success font-medium">✓ Configurado</span>
                    <span className="text-text-muted">Phone Number ID:</span>
                    <span className="text-text-primary font-mono text-xs">{formData.whatsappPhone}</span>
                    <span className="text-text-muted">WABA ID:</span>
                    <span className="text-text-primary font-mono text-xs">{formData.whatsappWabaId}</span>
                  </div>
                ) : (
                  <span className="text-warning text-sm">No configurado</span>
                )}
              </div>

              <Separator />

              {/* Datos bancarios */}
              <div>
                <p className="text-sm font-semibold text-text-primary mb-2">Datos Bancarios</p>
                {formData.banco ? (
                  <div className="grid grid-cols-2 gap-y-1 text-sm">
                    <span className="text-text-muted">Estado:</span>
                    <span className="text-success font-medium">✓ Configurados</span>
                    <span className="text-text-muted">Banco:</span>
                    <span className="text-text-primary">{formData.banco}</span>
                    <span className="text-text-muted">Tipo:</span>
                    <span className="text-text-primary capitalize">{formData.tipo_cuenta}</span>
                    <span className="text-text-muted">Titular:</span>
                    <span className="text-text-primary">{formData.titular}</span>
                  </div>
                ) : (
                  <span className="text-text-muted text-sm">No configurados</span>
                )}
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-between">
            <Button type="button" variant="outline" onClick={goBack}>← Anterior</Button>
            <Button type="button" onClick={handleSubmit} disabled={loading}>
              {loading ? 'Creando cliente...' : 'Crear Cliente'}
            </Button>
          </div>
        </div>
      )}

      {/* ── ÉXITO ───────────────────────────────────────────────────────────── */}
      {success && clienteCreado && (
        <Card>
          <CardHeader>
            <CardTitle className="text-success">¡Cliente creado exitosamente!</CardTitle>
            <CardDescription>El agente está listo. Comparte las credenciales con el cliente.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-surface rounded-lg p-4 font-mono text-sm space-y-1">
              <p><span className="text-text-muted">Email:</span> <span className="text-text-primary">{clienteCreado.email}</span></p>
              <p><span className="text-text-muted">Contraseña temporal:</span> <span className="text-text-primary">{clienteCreado.password}</span></p>
            </div>

            <div className="flex gap-3">
              <Button type="button" variant="outline" onClick={copyCredentials} className="flex items-center gap-2">
                <Copy className="h-4 w-4" />
                {copied ? '¡Copiado!' : 'Copiar credenciales'}
              </Button>
              <Button type="button" onClick={() => router.push('/admin/clientes')}>
                Ver todos los clientes
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
