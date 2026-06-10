'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { useState, useEffect } from 'react'
import { formatFechaCompleta } from '@/lib/date-format'
import Link from 'next/link'
import { MessageCircle, ChevronRight, Camera, Share2, Calendar } from 'lucide-react'
import { PromptGenerator } from '@/components/prompt-generator'

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
  { id: 'links_pago', nombre: 'Links de Pago', descripcion: 'Payphone, MercadoPago, PayPal' },
  { id: 'calificacion', nombre: 'Calificación', descripcion: 'Scoring automático de leads' },
  { id: 'campanas', nombre: 'Campañas', descripcion: 'Mensajería masiva' },
  { id: 'analytics', nombre: 'Analytics', descripcion: 'Reportes y métricas' },
  { id: 'alertas', nombre: 'Alertas', descripcion: 'Notificaciones del sistema' }
]

export default function ConfiguracionPage() {
  const [agente, setAgente] = useState<Agente | null>(null)
  const [agenteDraft, setAgenteDraft] = useState<Agente | null>(null)
  const [editingAgente, setEditingAgente] = useState(false)
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
        setAgenteDraft(agenteData.data)
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
    if (!agenteDraft) return

    setSaving(true)
    try {
      const response = await fetch('/api/cliente/agente', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agenteDraft)
      })

      if (response.ok) {
        setAgente(agenteDraft)
        setEditingAgente(false)
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

  function handleCancelAgente() {
    setAgenteDraft(agente)
    setEditingAgente(false)
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
    <div className="space-y-4 md:space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold text-text-primary">Configuración</h1>
        <p className="text-text-secondary mt-1 text-sm md:text-base">Personaliza tu agente IA y los módulos activos</p>
      </div>

      {/* Channel cards */}
      <div className="space-y-2">
        <p className="text-xs font-semibold text-text-muted uppercase tracking-widest">Canales</p>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <Link href="/cliente/configuracion/whatsapp">
            <Card className="cursor-pointer hover:border-accent/50 transition-colors h-full">
              <CardContent className="pt-4 pb-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#25D366]/10">
                    <MessageCircle className="h-5 w-5 text-[#25D366]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-text-primary text-sm">WhatsApp Business</p>
                    <p className="text-xs text-text-secondary">Conecta tu número</p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-text-muted shrink-0" />
                </div>
              </CardContent>
            </Card>
          </Link>

          <Link href="/cliente/configuracion/instagram">
            <Card className="cursor-pointer hover:border-accent/50 transition-colors h-full">
              <CardContent className="pt-4 pb-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#E1306C]/10">
                    <Camera className="h-5 w-5 text-[#E1306C]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-text-primary text-sm">Instagram Business</p>
                    <p className="text-xs text-text-secondary">Conecta tu cuenta</p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-text-muted shrink-0" />
                </div>
              </CardContent>
            </Card>
          </Link>

          <Link href="/cliente/configuracion/facebook">
            <Card className="cursor-pointer hover:border-accent/50 transition-colors h-full">
              <CardContent className="pt-4 pb-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#1877F2]/10">
                    <Share2 className="h-5 w-5 text-[#1877F2]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-text-primary text-sm">Facebook Messenger</p>
                    <p className="text-xs text-text-secondary">Conecta tu página</p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-text-muted shrink-0" />
                </div>
              </CardContent>
            </Card>
          </Link>

          <Link href="/cliente/configuracion/calendar">
            <Card className="cursor-pointer hover:border-accent/50 transition-colors h-full">
              <CardContent className="pt-4 pb-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#4285F4]/10">
                    <Calendar className="h-5 w-5 text-[#4285F4]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-text-primary text-sm">Google Calendar</p>
                    <p className="text-xs text-text-secondary">Gestión de citas</p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-text-muted shrink-0" />
                </div>
              </CardContent>
            </Card>
          </Link>
        </div>
      </div>

      {agente && (
        <Card>
          <CardHeader className="flex flex-row items-start justify-between">
            <div>
              <CardTitle>Configuración del Agente</CardTitle>
              <CardDescription>Personaliza el comportamiento de tu agente IA</CardDescription>
            </div>
            {!editingAgente && (
              <Button variant="outline" size="sm" onClick={() => setEditingAgente(true)}>
                Editar
              </Button>
            )}
          </CardHeader>
          <CardContent className="space-y-4 md:space-y-6">
            {editingAgente && agenteDraft ? (
              <>
                <div className="space-y-2">
                  <Label>Nombre del Agente</Label>
                  <Input
                    value={agenteDraft.nombre}
                    onChange={(e) => setAgenteDraft({ ...agenteDraft, nombre: e.target.value })}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>Tono</Label>
                    <select
                      value={agenteDraft.tono}
                      onChange={(e) => setAgenteDraft({ ...agenteDraft, tono: e.target.value as Agente['tono'] })}
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
                      value={agenteDraft.idioma}
                      onChange={(e) => setAgenteDraft({ ...agenteDraft, idioma: e.target.value as Agente['idioma'] })}
                      className="w-full px-3 py-2 border rounded-lg bg-background text-text-primary"
                    >
                      <option>Español</option>
                      <option>Inglés</option>
                      <option>Portugués</option>
                    </select>
                  </div>

                  <div className="space-y-2">
                    <Label>Modelo</Label>
                    <select
                      value={agenteDraft.modelo}
                      onChange={(e) => setAgenteDraft({ ...agenteDraft, modelo: e.target.value as Agente['modelo'] })}
                      className="w-full px-3 py-2 border rounded-lg bg-background text-text-primary"
                    >
                      <option>GPT-4o</option>
                      <option>GPT-4 Turbo</option>
                      <option>GPT-3.5 Turbo</option>
                    </select>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>System Prompt</Label>
                    <PromptGenerator
                      agenteName={agenteDraft.nombre}
                      tono={agenteDraft.tono}
                      idioma={agenteDraft.idioma}
                      modulosActivos={modulos.filter((m) => m.activo).map((m) => m.id)}
                      onApply={(prompt) => setAgenteDraft({ ...agenteDraft, system_prompt: prompt })}
                    />
                  </div>
                  <Textarea
                    value={agenteDraft.system_prompt}
                    onChange={(e) => setAgenteDraft({ ...agenteDraft, system_prompt: e.target.value })}
                    className="min-h-40"
                  />
                </div>

                <div className="flex gap-2">
                  <Button onClick={handleSaveAgente} disabled={saving}>
                    {saving ? 'Guardando...' : 'Guardar'}
                  </Button>
                  <Button variant="outline" onClick={handleCancelAgente} disabled={saving}>
                    Cancelar
                  </Button>
                </div>
              </>
            ) : (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-4 gap-x-8">
                  <div>
                    <p className="text-xs text-text-secondary uppercase tracking-wide mb-1">Nombre del Agente</p>
                    <p className="text-text-primary font-medium">{agente.nombre}</p>
                  </div>
                  <div>
                    <p className="text-xs text-text-secondary uppercase tracking-wide mb-1">Modelo</p>
                    <p className="text-text-primary font-medium">{agente.modelo}</p>
                  </div>
                  <div>
                    <p className="text-xs text-text-secondary uppercase tracking-wide mb-1">Tono</p>
                    <p className="text-text-primary font-medium">{agente.tono}</p>
                  </div>
                  <div>
                    <p className="text-xs text-text-secondary uppercase tracking-wide mb-1">Idioma</p>
                    <p className="text-text-primary font-medium">{agente.idioma}</p>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-text-secondary uppercase tracking-wide mb-2">System Prompt</p>
                  <p className="text-text-primary text-sm whitespace-pre-wrap bg-surface rounded-lg p-3 max-h-40 overflow-y-auto">
                    {agente.system_prompt || '—'}
                  </p>
                </div>
              </>
            )}
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
              <div key={pago.id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 border rounded-lg">
                <div className="flex-1 min-w-0">
                  <p className="font-medium">${pago.monto.toFixed(2)} {pago.moneda}</p>
                  <p className="text-sm text-text-secondary">
                    {pago.banco_origen ? `De: ${pago.banco_origen}` : 'Transferencia bancaria'}
                  </p>
                  <p className="text-sm text-text-secondary">
                    {formatFechaCompleta(pago.created_at.split('T')[0])}
                  </p>
                  {pago.numero_transaccion && (
                    <p className="text-xs text-text-secondary">Ref: {pago.numero_transaccion}</p>
                  )}
                </div>
                <div className="flex gap-2 shrink-0">
                  <Button
                    size="sm"
                    onClick={() => handlePagoAction(pago.id, 'aprobar')}
                    className="flex-1 sm:flex-none"
                  >
                    Aprobar
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handlePagoAction(pago.id, 'rechazar')}
                    className="flex-1 sm:flex-none"
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
