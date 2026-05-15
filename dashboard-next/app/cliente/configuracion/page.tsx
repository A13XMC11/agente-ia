'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { useState, useEffect } from 'react'

interface Agente {
  id: string
  nombre: string
  tono: 'Amigable' | 'Formal' | 'Profesional'
  idioma: 'Español' | 'Inglés' | 'Portugués'
  modelo: 'GPT-4o' | 'GPT-4 Turbo' | 'GPT-3.5 Turbo'
  system_prompt: string
}

interface Modulo {
  id: string
  nombre: string
  descripcion: string
  activo: boolean
}

interface DatoBancario {
  id: string
  banco: string
  tipo_cuenta: string
  numero_cuenta: string
  titular: string
  ruc?: string
  activo: boolean
}

interface Pago {
  id: string
  monto: number
  moneda: string
  metodo_pago: string
  estado: string
  banco_origen?: string
  numero_transaccion?: string
  created_at: string
}

const MODULOS_DISPONIBLES = [
  { id: 'ventas', nombre: 'Ventas', descripcion: 'Catálogo, cotizaciones, objecciones' },
  { id: 'agendamiento', nombre: 'Agendamiento', descripcion: 'Integración Google Calendar' },
  { id: 'cobros', nombre: 'Cobros', descripcion: 'Verificación de pagos con IA Vision' },
  { id: 'links_pago', nombre: 'Links de Pago', descripcion: 'Stripe, MercadoPago, PayPal' },
  { id: 'calificacion', nombre: 'Calificación', descripcion: 'Scoring automático de leads' },
  { id: 'campanas', nombre: 'Campañas', descripcion: 'Mensajería masiva' },
  { id: 'analytics', nombre: 'Analytics', descripcion: 'Reportes y métricas' },
  { id: 'alertas', nombre: 'Alertas', descripcion: 'Notificaciones del sistema' }
]

export default function ConfiguracionPage() {
  const [agente, setAgente] = useState<Agente | null>(null)
  const [modulos, setModulos] = useState<Modulo[]>([])
  const [datosBancarios, setDatosBancarios] = useState<DatoBancario[]>([])
  const [pagos, setPagos] = useState<Pago[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showAddBanco, setShowAddBanco] = useState(false)
  const [savingBanco, setSavingBanco] = useState(false)
  const [bancoForm, setBancoForm] = useState({
    banco: '',
    tipo_cuenta: 'corriente',
    numero_cuenta: '',
    titular: '',
    ruc: '',
  })

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      const [agenteRes, modulosRes, bancosRes, pagosRes] = await Promise.all([
        fetch('/api/cliente/agente'),
        fetch('/api/cliente/modulos'),
        fetch('/api/cliente/datos-bancarios'),
        fetch('/api/cliente/pagos'),
      ])

      if (agenteRes.ok) {
        const agenteData = await agenteRes.json()
        setAgente(agenteData.data)
      }

      if (modulosRes.ok) {
        const modulosData = await modulosRes.json()
        setModulos(modulosData.data || [])
      }

      if (bancosRes.ok) {
        const bancosData = await bancosRes.json()
        setDatosBancarios(bancosData.data || [])
      }

      if (pagosRes.ok) {
        const pagosData = await pagosRes.json()
        setPagos(pagosData.data || [])
      }
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleSaveAgente() {
    if (!agente) return

    setSaving(true)
    try {
      const response = await fetch('/api/cliente/agente', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agente)
      })

      if (response.ok) {
        alert('Configuración del agente guardada exitosamente')
      } else {
        alert('Error al guardar la configuración')
      }
    } catch (error) {
      console.error('Error saving agente:', error)
      alert('Error al guardar la configuración')
    } finally {
      setSaving(false)
    }
  }

  async function handleToggleModulo(moduloId: string, activo: boolean) {
    try {
      const response = await fetch('/api/cliente/modulos', {
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

  async function handleAddBanco() {
    setSavingBanco(true)
    try {
      const response = await fetch('/api/cliente/datos-bancarios', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bancoForm)
      })

      if (response.ok) {
        const result = await response.json()
        setDatosBancarios([result.data, ...datosBancarios])
        setShowAddBanco(false)
        setBancoForm({
          banco: '',
          tipo_cuenta: 'corriente',
          numero_cuenta: '',
          titular: '',
          ruc: '',
        })
      } else {
        alert('Error al guardar datos bancarios')
      }
    } catch (error) {
      console.error('Error adding banco:', error)
      alert('Error al guardar datos bancarios')
    } finally {
      setSavingBanco(false)
    }
  }

  async function handleDeleteBanco(id: string) {
    if (!confirm('¿Estás seguro de que quieres eliminar esta cuenta?')) return

    try {
      const response = await fetch(`/api/cliente/datos-bancarios?id=${id}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        setDatosBancarios(datosBancarios.filter(b => b.id !== id))
      }
    } catch (error) {
      console.error('Error deleting banco:', error)
    }
  }

  async function handlePagoAction(pagoId: string, accion: 'aprobar' | 'rechazar') {
    try {
      const response = await fetch('/api/cliente/pagos', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: pagoId, accion })
      })

      if (response.ok) {
        setPagos(pagos.map(p =>
          p.id === pagoId ? { ...p, estado: accion === 'aprobar' ? 'verificado' : 'rechazado' } : p
        ))
      }
    } catch (error) {
      console.error('Error processing payment:', error)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-text-primary">Configuración</h1>
        <Card>
          <CardContent className="pt-6">
            <p className="text-text-secondary">Cargando configuración...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Configuración</h1>
        <p className="text-text-secondary mt-2">Personaliza tu agente IA y los módulos activos</p>
      </div>

      {agente && (
        <Card>
          <CardHeader>
            <CardTitle>Configuración del Agente</CardTitle>
            <CardDescription>Personaliza el comportamiento de tu agente IA</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="agent-name">Nombre del Agente</Label>
              <Input
                id="agent-name"
                value={agente.nombre}
                onChange={(e) => setAgente({ ...agente, nombre: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="tone">Tono</Label>
                <select
                  id="tone"
                  value={agente.tono}
                  onChange={(e) => setAgente({ ...agente, tono: e.target.value as any })}
                  className="w-full px-3 py-2 border rounded-lg bg-background text-text-primary"
                >
                  <option>Amigable</option>
                  <option>Formal</option>
                  <option>Profesional</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="language">Idioma</Label>
                <select
                  id="language"
                  value={agente.idioma}
                  onChange={(e) => setAgente({ ...agente, idioma: e.target.value as any })}
                  className="w-full px-3 py-2 border rounded-lg bg-background text-text-primary"
                >
                  <option>Español</option>
                  <option>Inglés</option>
                  <option>Portugués</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="model">Modelo</Label>
                <select
                  id="model"
                  value={agente.modelo}
                  onChange={(e) => setAgente({ ...agente, modelo: e.target.value as any })}
                  className="w-full px-3 py-2 border rounded-lg bg-background text-text-primary"
                >
                  <option>GPT-4o</option>
                  <option>GPT-4 Turbo</option>
                  <option>GPT-3.5 Turbo</option>
                </select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="system-prompt">System Prompt</Label>
              <Textarea
                id="system-prompt"
                value={agente.system_prompt}
                onChange={(e) => setAgente({ ...agente, system_prompt: e.target.value })}
                className="min-h-40"
              />
            </div>

            <Button onClick={handleSaveAgente} disabled={saving}>
              {saving ? 'Guardando...' : 'Guardar Cambios'}
            </Button>
          </CardContent>
        </Card>
      )}

      <Separator />

      <Card>
        <CardHeader>
          <CardTitle>Módulos Activos</CardTitle>
          <CardDescription>Activa o desactiva funcionalidades para tu agente</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
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

      <Separator />

      <Card>
        <CardHeader>
          <CardTitle>Datos Bancarios para Cobros</CardTitle>
          <CardDescription>Configura las cuentas bancarias para recibir transferencias</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {datosBancarios.length > 0 && (
            <div className="space-y-4">
              {datosBancarios.map((banco) => (
                <div key={banco.id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <p className="font-medium">{banco.banco}</p>
                    <p className="text-sm text-text-secondary capitalize">{banco.tipo_cuenta}</p>
                    <p className="text-sm text-text-secondary">Titular: {banco.titular}</p>
                    <p className="text-sm text-text-secondary">Cuenta: {banco.numero_cuenta.slice(-4)}</p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDeleteBanco(banco.id)}
                  >
                    Eliminar
                  </Button>
                </div>
              ))}
            </div>
          )}

          {showAddBanco ? (
            <div className="space-y-4 p-4 border rounded-lg bg-background">
              <div className="space-y-2">
                <Label>Banco</Label>
                <Input
                  value={bancoForm.banco}
                  onChange={(e) => setBancoForm({ ...bancoForm, banco: e.target.value })}
                  placeholder="ej: Banco Pichincha"
                />
              </div>

              <div className="space-y-2">
                <Label>Tipo de Cuenta</Label>
                <select
                  value={bancoForm.tipo_cuenta}
                  onChange={(e) => setBancoForm({ ...bancoForm, tipo_cuenta: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg bg-background text-text-primary"
                >
                  <option>corriente</option>
                  <option>ahorros</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label>Número de Cuenta</Label>
                <Input
                  value={bancoForm.numero_cuenta}
                  onChange={(e) => setBancoForm({ ...bancoForm, numero_cuenta: e.target.value })}
                  placeholder="ej: 1234567890"
                />
              </div>

              <div className="space-y-2">
                <Label>Titular</Label>
                <Input
                  value={bancoForm.titular}
                  onChange={(e) => setBancoForm({ ...bancoForm, titular: e.target.value })}
                  placeholder="ej: Nombre de la Empresa"
                />
              </div>

              <div className="space-y-2">
                <Label>RUC (Opcional)</Label>
                <Input
                  value={bancoForm.ruc}
                  onChange={(e) => setBancoForm({ ...bancoForm, ruc: e.target.value })}
                  placeholder="ej: 1234567890001"
                />
              </div>

              <div className="flex gap-2">
                <Button onClick={handleAddBanco} disabled={savingBanco}>
                  {savingBanco ? 'Guardando...' : 'Guardar'}
                </Button>
                <Button variant="outline" onClick={() => setShowAddBanco(false)}>
                  Cancelar
                </Button>
              </div>
            </div>
          ) : (
            <Button onClick={() => setShowAddBanco(true)}>
              + Agregar Cuenta Bancaria
            </Button>
          )}
        </CardContent>
      </Card>

      {pagos.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Pagos Pendientes de Revisión</CardTitle>
            <CardDescription>Aprueba o rechaza transferencias cuyos montos no coincidan exactamente</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {pagos.map((pago) => (
              <div key={pago.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex-1">
                  <p className="font-medium">${pago.monto.toFixed(2)} {pago.moneda}</p>
                  <p className="text-sm text-text-secondary">
                    {pago.banco_origen ? `De: ${pago.banco_origen}` : 'Transferencia bancaria'}
                  </p>
                  <p className="text-sm text-text-secondary">
                    {new Date(pago.created_at).toLocaleDateString()}
                  </p>
                  {pago.numero_transaccion && (
                    <p className="text-xs text-text-secondary">Ref: {pago.numero_transaccion}</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => handlePagoAction(pago.id, 'aprobar')}
                  >
                    Aprobar
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handlePagoAction(pago.id, 'rechazar')}
                  >
                    Rechazar
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
