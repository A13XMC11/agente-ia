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

interface FormData {
  // Client
  nombre: string
  email: string
  telefono: string
  plan: string
  precio_mensual: string

  // Agent
  nombreAgente: string
  tono: string
  idioma: string
  modelo: string
  systemPrompt: string

  // Modules
  modulos: Record<string, boolean>

  // WhatsApp
  whatsappEnabled: boolean
  whatsappPhone: string
  whatsappToken: string
}

export default function NuevoClientePage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [formData, setFormData] = useState<FormData>({
    nombre: '',
    email: '',
    telefono: '',
    plan: 'Starter - $99/mes',
    precio_mensual: '99',

    nombreAgente: '',
    tono: 'Amigable',
    idioma: 'Español',
    modelo: 'GPT-4o',
    systemPrompt: '',

    modulos: {
      Ventas: false,
      Agendamiento: false,
      Cobros: false,
      'Links de Pago': false,
      Calificación: false,
      Campañas: false,
      Analytics: false,
      Alertas: false,
    },

    whatsappEnabled: true,
    whatsappPhone: '',
    whatsappToken: '',
  })

  const handleInputChange = (field: keyof FormData, value: any) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  const handleModuloChange = (moduleName: string, checked: boolean) => {
    setFormData((prev) => ({
      ...prev,
      modulos: {
        ...prev.modulos,
        [moduleName]: checked,
      },
    }))
  }

  const validateForm = (): string | null => {
    if (!formData.nombre.trim()) return 'Nombre del negocio es requerido'
    if (!formData.email.trim()) return 'Email es requerido'
    if (!formData.email.includes('@')) return 'Email inválido'
    if (!formData.telefono.trim()) return 'Teléfono es requerido'
    if (!formData.nombreAgente.trim()) return 'Nombre del agente es requerido'
    if (!formData.systemPrompt.trim()) return 'System prompt es requerido'
    if (formData.whatsappEnabled && !formData.whatsappPhone.trim()) return 'Phone Number ID de WhatsApp es requerido'
    if (formData.whatsappEnabled && !formData.whatsappToken.trim()) return 'Token de WhatsApp es requerido'

    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess(false)

    const validationError = validateForm()
    if (validationError) {
      setError(validationError)
      return
    }

    setLoading(true)

    try {
      const response = await fetch('/api/clientes/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          nombre: formData.nombre,
          email: formData.email,
          telefono: formData.telefono,
          plan: formData.plan,
          precio_mensual: parseInt(formData.precio_mensual) || 0,
          nombreAgente: formData.nombreAgente,
          tono: formData.tono,
          idioma: formData.idioma,
          modelo: formData.modelo,
          systemPrompt: formData.systemPrompt,
          modulos: formData.modulos,
          whatsappEnabled: formData.whatsappEnabled,
          whatsappPhone: formData.whatsappPhone,
          whatsappToken: formData.whatsappToken,
        }),
      })

      const data = await response.json()

      if (!data.success) {
        throw new Error(data.error || 'Error creating client')
      }

      setSuccess(true)
      setTimeout(() => {
        router.push('/admin/clientes')
      }, 2000)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error creating client'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <Link href="/admin/clientes" className="text-accent hover:text-accent-hover mb-2 inline-block">
          ← Volver
        </Link>
        <h1 className="text-3xl font-bold text-text-primary">Nuevo Cliente</h1>
        <p className="text-text-secondary mt-2">Crea un nuevo cliente y configura su agente IA</p>
      </div>

      {error && (
        <div className="bg-error/10 border border-error text-error px-4 py-3 rounded">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-success/10 border border-success text-success px-4 py-3 rounded">
          Cliente creado exitosamente. Redirigiendo...
        </div>
      )}

      {/* Client Data */}
      <Card>
        <CardHeader>
          <CardTitle>Información del Cliente</CardTitle>
          <CardDescription>Datos básicos del cliente</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="client-name">Nombre del Negocio *</Label>
              <Input
                id="client-name"
                placeholder="Ej: Mi Tienda Online"
                value={formData.nombre}
                onChange={(e) => handleInputChange('nombre', e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="client-email">Email *</Label>
              <Input
                id="client-email"
                type="email"
                placeholder="admin@minegogio.com"
                value={formData.email}
                onChange={(e) => handleInputChange('email', e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="client-phone">Teléfono *</Label>
              <Input
                id="client-phone"
                placeholder="+57 300 1234567"
                value={formData.telefono}
                onChange={(e) => handleInputChange('telefono', e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="client-plan">Plan *</Label>
              <Select
                id="client-plan"
                value={formData.plan}
                onChange={(e) => {
                  const plan = e.target.value
                  handleInputChange('plan', plan)
                  const precio = plan.includes('99') ? '99' : plan.includes('299') ? '299' : '0'
                  handleInputChange('precio_mensual', precio)
                }}
              >
                <option>Starter - $99/mes</option>
                <option>Professional - $299/mes</option>
                <option>Enterprise - Consultar</option>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Separator />

      {/* Agent Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Configuración del Agente</CardTitle>
          <CardDescription>Personaliza el comportamiento inicial del agente</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="agent-name">Nombre del Agente *</Label>
              <Input
                id="agent-name"
                placeholder="Asistente Virtual"
                value={formData.nombreAgente}
                onChange={(e) => handleInputChange('nombreAgente', e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="tone">Tono *</Label>
              <Select
                id="tone"
                value={formData.tono}
                onChange={(e) => handleInputChange('tono', e.target.value)}
              >
                <option>Amigable</option>
                <option>Formal</option>
                <option>Profesional</option>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="language">Idioma *</Label>
              <Select
                id="language"
                value={formData.idioma}
                onChange={(e) => handleInputChange('idioma', e.target.value)}
              >
                <option>Español</option>
                <option>Inglés</option>
                <option>Portugués</option>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="model">Modelo IA *</Label>
              <Select
                id="model"
                value={formData.modelo}
                onChange={(e) => handleInputChange('modelo', e.target.value)}
              >
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
              placeholder="Eres un asistente amable que ayuda a los clientes con sus preguntas..."
              className="min-h-32"
              value={formData.systemPrompt}
              onChange={(e) => handleInputChange('systemPrompt', e.target.value)}
              required
            />
          </div>
        </CardContent>
      </Card>

      <Separator />

      {/* Modules */}
      <Card>
        <CardHeader>
          <CardTitle>Módulos a Activar</CardTitle>
          <CardDescription>Selecciona qué funcionalidades estará disponible para este cliente</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[
              { name: 'Ventas', desc: 'Catálogo, cotizaciones, objecciones' },
              { name: 'Agendamiento', desc: 'Integración Google Calendar' },
              { name: 'Cobros', desc: 'Verificación de pagos con IA Vision' },
              { name: 'Links de Pago', desc: 'Stripe, MercadoPago, PayPal' },
              { name: 'Calificación', desc: 'Scoring automático de leads' },
              { name: 'Campañas', desc: 'Mensajería masiva' },
              { name: 'Analytics', desc: 'Reportes y métricas' },
              { name: 'Alertas', desc: 'Notificaciones del sistema' },
            ].map((module) => (
              <div key={module.name} className="flex items-center justify-between">
                <div>
                  <Label className="text-base font-medium">{module.name}</Label>
                  <p className="text-sm text-text-secondary">{module.desc}</p>
                </div>
                <Switch
                  checked={formData.modulos[module.name]}
                  onChange={(checked) => handleModuloChange(module.name, checked)}
                />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Separator />

      {/* Channels */}
      <Card>
        <CardHeader>
          <CardTitle>Canales</CardTitle>
          <CardDescription>Configura los canales de comunicación</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label className="text-base font-medium">WhatsApp *</Label>
              <Switch
                checked={formData.whatsappEnabled}
                onChange={(checked) => handleInputChange('whatsappEnabled', checked)}
              />
            </div>

            {formData.whatsappEnabled && (
              <div className="space-y-2 pl-4">
                <div className="space-y-2">
                  <Label htmlFor="whatsapp-phone">Phone Number ID *</Label>
                  <Input
                    id="whatsapp-phone"
                    placeholder="123456789012345"
                    value={formData.whatsappPhone}
                    onChange={(e) => handleInputChange('whatsappPhone', e.target.value)}
                    required={formData.whatsappEnabled}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="whatsapp-token">Token *</Label>
                  <Input
                    id="whatsapp-token"
                    placeholder="EABC..."
                    value={formData.whatsappToken}
                    onChange={(e) => handleInputChange('whatsappToken', e.target.value)}
                    required={formData.whatsappEnabled}
                  />
                </div>
              </div>
            )}
          </div>

          <Separator />

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label className="text-base font-medium">Instagram</Label>
              <Switch disabled />
            </div>

            <div className="flex items-center justify-between">
              <Label className="text-base font-medium">Facebook</Label>
              <Switch disabled />
            </div>

            <div className="flex items-center justify-between">
              <Label className="text-base font-medium">Email</Label>
              <Switch disabled />
            </div>
          </div>

          <p className="text-xs text-text-muted">Los otros canales se habilitarán en futuras versiones</p>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex gap-4">
        <Button type="submit" disabled={loading}>
          {loading ? 'Creando cliente...' : 'Crear Cliente'}
        </Button>
        <Link href="/admin/clientes">
          <Button type="button" variant="outline" disabled={loading}>
            Cancelar
          </Button>
        </Link>
      </div>
    </form>
  )
}
