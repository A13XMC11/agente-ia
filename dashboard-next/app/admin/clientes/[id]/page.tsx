'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'

interface Cliente {
  id: string
  nombre: string
  email: string
  telefono: string
  plan: string
  estado: 'activo' | 'pausado' | 'cancelado'
  precio_mensual: number
  created_at: string
}

interface Agente {
  id: string
  nombre: string
  tono: string
  idioma: string
  modelo: string
  system_prompt: string
}

interface Modulo {
  id: string
  nombre: string
  descripcion: string
  activo: boolean
}

const MODULOS_DISPONIBLES = [
  { id: 'ventas', nombre: 'Ventas', descripcion: 'Catálogo, cotizaciones, objecciones' },
  { id: 'agendamiento', nombre: 'Agendamiento', descripcion: 'Integración Google Calendar' },
  { id: 'cobros', nombre: 'Cobros', descripcion: 'Verificación de pagos' },
  { id: 'links_pago', nombre: 'Links de Pago', descripcion: 'Stripe, MercadoPago, PayPal' },
  { id: 'calificacion', nombre: 'Calificación', descripcion: 'Scoring de leads' },
  { id: 'campanas', nombre: 'Campañas', descripcion: 'Mensajería masiva' },
  { id: 'analytics', nombre: 'Analytics', descripcion: 'Reportes y métricas' },
  { id: 'alertas', nombre: 'Alertas', descripcion: 'Notificaciones' }
]

export default function ClienteDetalle() {
  const params = useParams()
  const clienteId = params.id as string

  const [cliente, setCliente] = useState<Cliente | null>(null)
  const [agente, setAgente] = useState<Agente | null>(null)
  const [modulos, setModulos] = useState<Modulo[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadData()
  }, [clienteId])

  async function loadData() {
    try {
      const [clienteRes, agenteRes, modulosRes] = await Promise.all([
        fetch(`/api/clientes/${clienteId}`),
        fetch(`/api/clientes/${clienteId}/agente`),
        fetch(`/api/clientes/${clienteId}/modulos`)
      ])

      if (clienteRes.ok) {
        const clienteData = await clienteRes.json()
        setCliente(clienteData.data)
      }

      if (agenteRes.ok) {
        const agenteData = await agenteRes.json()
        setAgente(agenteData.data)
      }

      if (modulosRes.ok) {
        const modulosData = await modulosRes.json()
        setModulos(modulosData.data || [])
      }
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleSaveCliente() {
    if (!cliente) return
    setSaving(true)

    try {
      const response = await fetch(`/api/clientes/${clienteId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cliente)
      })

      if (response.ok) {
        alert('Cliente actualizado exitosamente')
      } else {
        alert('Error al actualizar el cliente')
      }
    } catch (error) {
      console.error('Error saving cliente:', error)
      alert('Error al actualizar')
    } finally {
      setSaving(false)
    }
  }

  async function handleSaveAgente() {
    if (!agente) return
    setSaving(true)

    try {
      const response = await fetch(`/api/clientes/${clienteId}/agente`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agente)
      })

      if (response.ok) {
        alert('Agente actualizado exitosamente')
      } else {
        alert('Error al actualizar el agente')
      }
    } catch (error) {
      console.error('Error saving agente:', error)
      alert('Error al actualizar')
    } finally {
      setSaving(false)
    }
  }

  async function handleToggleModulo(moduloId: string, activo: boolean) {
    try {
      const response = await fetch(`/api/clientes/${clienteId}/modulos`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ modulo_id: moduloId, activo })
      })

      if (response.ok) {
        setModulos(modulos.map(m =>
          m.id === moduloId ? { ...m, activo } : m
        ))
      }
    } catch (error) {
      console.error('Error toggling modulo:', error)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-text-primary">Detalle del Cliente</h1>
        <Card>
          <CardContent className="pt-6">
            <p className="text-text-secondary">Cargando...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!cliente) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-text-primary">Cliente no encontrado</h1>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">{cliente.nombre}</h1>
          <p className="text-text-secondary mt-2">{cliente.email}</p>
        </div>
        <span className={`px-3 py-1 rounded-lg text-sm font-medium ${
          cliente.estado === 'activo'
            ? 'bg-success/10 text-success'
            : cliente.estado === 'pausado'
            ? 'bg-warning/10 text-warning'
            : 'bg-error/10 text-error'
        }`}>
          {cliente.estado}
        </span>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Información General</CardTitle>
          <CardDescription>Datos del cliente</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Nombre</Label>
              <Input
                value={cliente.nombre}
                onChange={(e) => setCliente({ ...cliente, nombre: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label>Email</Label>
              <Input
                type="email"
                value={cliente.email}
                onChange={(e) => setCliente({ ...cliente, email: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label>Teléfono</Label>
              <Input
                value={cliente.telefono}
                onChange={(e) => setCliente({ ...cliente, telefono: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label>Plan</Label>
              <Input
                value={cliente.plan}
                onChange={(e) => setCliente({ ...cliente, plan: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label>Precio Mensual</Label>
              <Input
                type="number"
                value={cliente.precio_mensual}
                onChange={(e) => setCliente({ ...cliente, precio_mensual: parseFloat(e.target.value) })}
              />
            </div>

            <div className="space-y-2">
              <Label>Estado</Label>
              <select
                value={cliente.estado}
                onChange={(e) => setCliente({ ...cliente, estado: e.target.value as any })}
                className="w-full px-3 py-2 border rounded-lg bg-background text-text-primary"
              >
                <option>activo</option>
                <option>pausado</option>
                <option>cancelado</option>
              </select>
            </div>
          </div>

          <Button onClick={handleSaveCliente} disabled={saving}>
            {saving ? 'Guardando...' : 'Guardar Cliente'}
          </Button>
        </CardContent>
      </Card>

      <Separator />

      {agente && (
        <Card>
          <CardHeader>
            <CardTitle>Configuración del Agente</CardTitle>
            <CardDescription>Personalización de IA para este cliente</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Nombre del Agente</Label>
                <Input
                  value={agente.nombre}
                  onChange={(e) => setAgente({ ...agente, nombre: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label>Modelo</Label>
                <select
                  value={agente.modelo}
                  onChange={(e) => setAgente({ ...agente, modelo: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg bg-background text-text-primary"
                >
                  <option>GPT-4o</option>
                  <option>GPT-4 Turbo</option>
                  <option>GPT-3.5 Turbo</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label>Tono</Label>
                <select
                  value={agente.tono}
                  onChange={(e) => setAgente({ ...agente, tono: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg bg-background text-text-primary"
                >
                  <option>Amigable</option>
                  <option>Formal</option>
                  <option>Profesional</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label>Idioma</Label>
                <select
                  value={agente.idioma}
                  onChange={(e) => setAgente({ ...agente, idioma: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg bg-background text-text-primary"
                >
                  <option>Español</option>
                  <option>Inglés</option>
                  <option>Portugués</option>
                </select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>System Prompt</Label>
              <Textarea
                value={agente.system_prompt}
                onChange={(e) => setAgente({ ...agente, system_prompt: e.target.value })}
                className="min-h-40"
              />
            </div>

            <Button onClick={handleSaveAgente} disabled={saving}>
              {saving ? 'Guardando...' : 'Guardar Agente'}
            </Button>
          </CardContent>
        </Card>
      )}

      <Separator />

      <Card>
        <CardHeader>
          <CardTitle>Módulos Activos</CardTitle>
          <CardDescription>Funcionalidades habilitadas para este cliente</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {MODULOS_DISPONIBLES.map((modDef) => {
              const modActive = modulos.find(m => m.id === modDef.id)
              const activo = modActive?.activo || false

              return (
                <div key={modDef.id} className="flex items-center justify-between">
                  <div>
                    <Label className="text-base font-medium">{modDef.nombre}</Label>
                    <p className="text-sm text-text-secondary">{modDef.descripcion}</p>
                  </div>
                  <Switch
                    checked={activo}
                    onCheckedChange={(checked) => handleToggleModulo(modDef.id, checked)}
                  />
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
