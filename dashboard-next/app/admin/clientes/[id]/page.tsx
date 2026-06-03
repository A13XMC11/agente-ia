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
import { CheckCircle, AlertTriangle, XCircle, Clock } from 'lucide-react'

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

interface Subscription {
  status: 'active' | 'past_due' | 'cancelled' | 'trialing' | 'pending_payment'
  monthly_amount: number
  next_billing_date: string | null
  current_period_end: string | null
  payment_failed_count: number
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

const PLANES = [
  { id: 'basico', nombre: 'Básico', precio: 149 },
  { id: 'profesional', nombre: 'Profesional', precio: 249 },
  { id: 'empresarial', nombre: 'Empresarial', precio: 399 },
]

const MODULOS_DISPONIBLES = [
  { id: 'ventas', nombre: 'Ventas', descripcion: 'Catálogo, cotizaciones, objecciones' },
  { id: 'agendamiento', nombre: 'Agendamiento', descripcion: 'Integración Google Calendar' },
  { id: 'cobros', nombre: 'Cobros', descripcion: 'Verificación de pagos' },
  { id: 'links_pago', nombre: 'Links de Pago', descripcion: 'Payphone, MercadoPago, PayPal' },
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
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editingCliente, setEditingCliente] = useState(false)
  const [editingAgente, setEditingAgente] = useState(false)
  const [clienteDraft, setClienteDraft] = useState<Cliente | null>(null)
  const [agenteDraft, setAgenteDraft] = useState<Agente | null>(null)
  const [billingAmount, setBillingAmount] = useState('')
  const [billingPhone, setBillingPhone] = useState('')
  const [billingLoading, setBillingLoading] = useState(false)
  const [isPollingBilling, setIsPollingBilling] = useState(false)

  useEffect(() => {
    loadData()
  }, [clienteId])

  useEffect(() => {
    if (subscription?.status !== 'pending_payment') return

    setIsPollingBilling(true)
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/admin/clientes/${clienteId}/billing`)
        if (!res.ok) return
        const data = await res.json()
        const updated: Subscription | null = data.data ?? null
        setSubscription(updated)
        if (updated?.status !== 'pending_payment') {
          setIsPollingBilling(false)
        }
      } catch {
        // keep polling on network error
      }
    }, 5000)

    return () => {
      clearInterval(interval)
      setIsPollingBilling(false)
    }
  }, [subscription?.status, clienteId])

  async function loadData() {
    try {
      const [clienteRes, agenteRes, modulosRes, billingRes] = await Promise.all([
        fetch(`/api/clientes/${clienteId}`),
        fetch(`/api/clientes/${clienteId}/agente`),
        fetch(`/api/clientes/${clienteId}/modulos`),
        fetch(`/api/admin/clientes/${clienteId}/billing`),
      ])

      if (clienteRes.ok) {
        const clienteData = await clienteRes.json()
        setCliente(clienteData.data)
        setClienteDraft(clienteData.data)
      }

      if (agenteRes.ok) {
        const agenteData = await agenteRes.json()
        setAgente(agenteData.data)
        setAgenteDraft(agenteData.data)
      }

      if (modulosRes.ok) {
        const modulosData = await modulosRes.json()
        setModulos(modulosData.data || [])
      }

      if (billingRes.ok) {
        const billingData = await billingRes.json()
        setSubscription(billingData.data ?? null)
      }
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleSaveCliente() {
    if (!clienteDraft) return
    setSaving(true)

    try {
      const response = await fetch(`/api/clientes/${clienteId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(clienteDraft)
      })

      if (response.ok) {
        setCliente(clienteDraft)
        setEditingCliente(false)
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

  function handleCancelCliente() {
    setClienteDraft(cliente)
    setEditingCliente(false)
  }

  async function handleSaveAgente() {
    if (!agenteDraft) return
    setSaving(true)

    try {
      const response = await fetch(`/api/clientes/${clienteId}/agente`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agenteDraft)
      })

      if (response.ok) {
        setAgente(agenteDraft)
        setEditingAgente(false)
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

  function handleCancelAgente() {
    setAgenteDraft(agente)
    setEditingAgente(false)
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

  async function handleCreateSubscription() {
    const amount = parseFloat(billingAmount)
    if (!amount || amount <= 0) return alert('Ingresa un monto válido')
    if (!billingPhone.trim()) return alert('Ingresa el número de teléfono Payphone del cliente')
    setBillingLoading(true)
    try {
      const res = await fetch(`/api/admin/clientes/${clienteId}/billing`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ monthly_amount: amount, phone_number: billingPhone.trim(), country_code: '593' }),
      })
      const data = await res.json()
      if (res.ok && data.success) {
        alert('Suscripción creada. El cliente recibirá una notificación en su app Payphone para aprobar el pago.')
        const refreshed = await fetch(`/api/admin/clientes/${clienteId}/billing`)
        if (refreshed.ok) setSubscription((await refreshed.json()).data)
        setBillingAmount('')
        setBillingPhone('')
      } else {
        alert(data.error || 'Error al crear suscripción')
      }
    } catch {
      alert('Error de red')
    } finally {
      setBillingLoading(false)
    }
  }

  async function handleManualActivate() {
    if (!confirm('¿Confirmas que verificaste el pago en el dashboard de Payphone y quieres activar la suscripción?')) return
    setBillingLoading(true)
    try {
      const res = await fetch(`/api/admin/clientes/${clienteId}/billing`, { method: 'PATCH' })
      const data = await res.json()
      if (res.ok && data.success) {
        alert('Suscripción activada correctamente')
        const refreshed = await fetch(`/api/admin/clientes/${clienteId}/billing`)
        const refreshedData = await refreshed.json()
        setSubscription(refreshedData.data ?? null)
      } else {
        alert(data.error || 'Error al activar suscripción')
      }
    } catch {
      alert('Error de red')
    } finally {
      setBillingLoading(false)
    }
  }

  async function handleCancelSubscription() {
    if (!confirm('¿Cancelar suscripción? El cliente quedará pausado.')) return
    setBillingLoading(true)
    try {
      const res = await fetch(`/api/admin/clientes/${clienteId}/billing`, { method: 'DELETE' })
      const data = await res.json()
      if (res.ok && data.success) {
        alert('Suscripción cancelada')
        setSubscription(null)
      } else {
        alert(data.error || 'Error al cancelar')
      }
    } catch {
      alert('Error de red')
    } finally {
      setBillingLoading(false)
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
        <div className="flex items-center gap-3">
          <span className={`px-3 py-1 rounded-lg text-sm font-medium ${
            cliente.estado === 'activo'
              ? 'bg-success/10 text-success'
              : cliente.estado === 'pausado'
              ? 'bg-warning/10 text-warning'
              : 'bg-error/10 text-error'
          }`}>
            {cliente.estado}
          </span>
          <a href={`/admin/clientes/${clienteId}/panel`}>
            <Button>Ver Panel del Cliente</Button>
          </a>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-start justify-between">
          <div>
            <CardTitle>Información General</CardTitle>
            <CardDescription>Datos del cliente</CardDescription>
          </div>
          {!editingCliente && (
            <Button variant="outline" size="sm" onClick={() => setEditingCliente(true)}>
              Editar
            </Button>
          )}
        </CardHeader>
        <CardContent className="space-y-6">
          {editingCliente && clienteDraft ? (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Nombre</Label>
                  <Input
                    value={clienteDraft.nombre}
                    onChange={(e) => setClienteDraft({ ...clienteDraft, nombre: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input
                    type="email"
                    value={clienteDraft.email}
                    onChange={(e) => setClienteDraft({ ...clienteDraft, email: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Teléfono</Label>
                  <Input
                    value={clienteDraft.telefono}
                    onChange={(e) => setClienteDraft({ ...clienteDraft, telefono: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Plan</Label>
                  <select
                    value={clienteDraft.plan}
                    onChange={(e) => {
                      const plan = PLANES.find(p => p.id === e.target.value)
                      setClienteDraft({
                        ...clienteDraft,
                        plan: e.target.value,
                        precio_mensual: plan?.precio ?? clienteDraft.precio_mensual,
                      })
                    }}
                    className="w-full px-3 py-2 border rounded-lg bg-background text-text-primary"
                  >
                    {PLANES.map(p => (
                      <option key={p.id} value={p.id}>{p.nombre}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label>Precio Mensual</Label>
                  <div className="flex items-center h-10 px-3 border rounded-lg bg-surface text-text-primary">
                    ${PLANES.find(p => p.id === clienteDraft.plan)?.precio ?? clienteDraft.precio_mensual}/mes
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Estado</Label>
                  <select
                    value={clienteDraft.estado}
                    onChange={(e) => setClienteDraft({ ...clienteDraft, estado: e.target.value as Cliente['estado'] })}
                    className="w-full px-3 py-2 border rounded-lg bg-background text-text-primary"
                  >
                    <option>activo</option>
                    <option>pausado</option>
                    <option>cancelado</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-2">
                <Button onClick={handleSaveCliente} disabled={saving}>
                  {saving ? 'Guardando...' : 'Guardar'}
                </Button>
                <Button variant="outline" onClick={handleCancelCliente} disabled={saving}>
                  Cancelar
                </Button>
              </div>
            </>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-y-4 gap-x-8">
              <div>
                <p className="text-xs text-text-secondary uppercase tracking-wide mb-1">Nombre</p>
                <p className="text-text-primary font-medium">{cliente.nombre}</p>
              </div>
              <div>
                <p className="text-xs text-text-secondary uppercase tracking-wide mb-1">Email</p>
                <p className="text-text-primary font-medium">{cliente.email}</p>
              </div>
              <div>
                <p className="text-xs text-text-secondary uppercase tracking-wide mb-1">Teléfono</p>
                <p className="text-text-primary font-medium">{cliente.telefono || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-text-secondary uppercase tracking-wide mb-1">Plan</p>
                <p className="text-text-primary font-medium capitalize">{cliente.plan}</p>
              </div>
              <div>
                <p className="text-xs text-text-secondary uppercase tracking-wide mb-1">Precio Mensual</p>
                <p className="text-text-primary font-medium">
                  {cliente.precio_mensual ? `$${cliente.precio_mensual}/mes` : '—'}
                </p>
              </div>
              <div>
                <p className="text-xs text-text-secondary uppercase tracking-wide mb-1">Estado</p>
                <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                  cliente.estado === 'activo' ? 'bg-success/10 text-success' :
                  cliente.estado === 'pausado' ? 'bg-warning/10 text-warning' :
                  'bg-error/10 text-error'
                }`}>
                  {cliente.estado}
                </span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Separator />

      {agente && (
        <Card>
          <CardHeader className="flex flex-row items-start justify-between">
            <div>
              <CardTitle>Configuración del Agente</CardTitle>
              <CardDescription>Personalización de IA para este cliente</CardDescription>
            </div>
            {!editingAgente && (
              <Button variant="outline" size="sm" onClick={() => setEditingAgente(true)}>
                Editar
              </Button>
            )}
          </CardHeader>
          <CardContent className="space-y-6">
            {editingAgente && agenteDraft ? (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Nombre del Agente</Label>
                    <Input
                      value={agenteDraft.nombre}
                      onChange={(e) => setAgenteDraft({ ...agenteDraft, nombre: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Modelo</Label>
                    <select
                      value={agenteDraft.modelo}
                      onChange={(e) => setAgenteDraft({ ...agenteDraft, modelo: e.target.value })}
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
                      value={agenteDraft.tono}
                      onChange={(e) => setAgenteDraft({ ...agenteDraft, tono: e.target.value })}
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
                      onChange={(e) => setAgenteDraft({ ...agenteDraft, idioma: e.target.value })}
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
                <div className="grid grid-cols-1 md:grid-cols-2 gap-y-4 gap-x-8">
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

      {/* ── Billing ─────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Facturación</CardTitle>
          <CardDescription>Suscripción Payphone de este cliente</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {subscription && subscription.status !== 'cancelled' ? (
            <>
              <div className="flex items-center gap-3">
                {subscription.status === 'active' && <CheckCircle className="h-5 w-5 text-success" />}
                {subscription.status === 'past_due' && <AlertTriangle className="h-5 w-5 text-warning" />}
                {subscription.status === 'pending_payment' && <Clock className="h-5 w-5 text-accent" />}
                <div>
                  <p className="font-semibold text-text-primary capitalize">{subscription.status.replace('_', ' ')}</p>
                  <p className="text-sm text-text-secondary">
                    ${subscription.monthly_amount}/mes
                    {subscription.next_billing_date && (
                      <> · Próximo cobro: {new Date(subscription.next_billing_date).toLocaleDateString('es')}</>
                    )}
                    {subscription.payment_failed_count > 0 && (
                      <> · {subscription.payment_failed_count} pago(s) fallido(s)</>
                    )}
                  </p>
                  {subscription.status === 'pending_payment' && (
                    <p className="text-xs text-text-secondary mt-1">
                      {isPollingBilling
                        ? 'Verificando pago automáticamente...'
                        : 'Esperando aprobación del cliente en su app Payphone. Si ya pagó, actívala manualmente.'}
                    </p>
                  )}
                </div>
              </div>
              <div className="flex gap-2 flex-wrap">
                {subscription.status === 'pending_payment' && (
                  <Button
                    onClick={handleManualActivate}
                    disabled={billingLoading}
                    className="w-full sm:w-auto"
                  >
                    {billingLoading ? 'Activando...' : 'Activar manualmente'}
                  </Button>
                )}
                <Button
                  variant="destructive"
                  onClick={handleCancelSubscription}
                  disabled={billingLoading}
                  className="w-full sm:w-auto"
                >
                  {billingLoading ? 'Cancelando...' : 'Cancelar suscripción'}
                </Button>
              </div>
            </>
          ) : (
            <div className="space-y-3">
              {subscription?.status === 'cancelled' && (
                <p className="text-sm text-text-secondary flex items-center gap-2">
                  <XCircle className="h-4 w-4 text-error" />
                  Suscripción cancelada. Puedes crear una nueva.
                </p>
              )}
              {!subscription && (
                <p className="text-sm text-text-secondary">Sin suscripción activa. Crea una para habilitar el cobro mensual.</p>
              )}
              <div className="flex items-end gap-3 flex-wrap">
                <div className="space-y-1">
                  <Label>Monto mensual (USD)</Label>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="149.00"
                    value={billingAmount}
                    onChange={(e) => setBillingAmount(e.target.value)}
                    className="w-36"
                  />
                </div>
                <div className="space-y-1">
                  <Label>Teléfono Payphone del cliente</Label>
                  <Input
                    type="tel"
                    placeholder="0984111222"
                    value={billingPhone}
                    onChange={(e) => setBillingPhone(e.target.value)}
                    className="w-44"
                  />
                </div>
                <Button
                  onClick={handleCreateSubscription}
                  disabled={billingLoading || !billingAmount || !billingPhone}
                  className="self-end"
                >
                  {billingLoading ? 'Creando...' : 'Crear suscripción'}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

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
