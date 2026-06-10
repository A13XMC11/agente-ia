'use client'

import { useState, useEffect } from 'react'
import { AlertTriangle, CheckCircle, Clock, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface DueSubscription {
  id: string
  cliente_id: string
  monthly_amount: number
  payment_method: 'transferencia' | 'efectivo'
  status: string
  next_billing_date: string | null
  clientes?: {
    nombre_empresa: string
    email: string
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es', { year: 'numeric', month: 'short', day: 'numeric' })
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)
}

function getDaysUntil(iso: string | null): number | null {
  if (!iso) return null
  return Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000)
}

const METHOD_LABEL: Record<string, string> = {
  transferencia: 'Transferencia',
  efectivo: 'Efectivo',
}

export default function AdminFacturacion() {
  const [subscriptions, setSubscriptions] = useState<DueSubscription[]>([])
  const [loading, setLoading] = useState(true)
  const [renewingId, setRenewingId] = useState<string | null>(null)

  useEffect(() => {
    loadDue()
  }, [])

  async function loadDue() {
    setLoading(true)
    try {
      const res = await fetch('/api/admin/billing/due')
      if (res.ok) {
        const data = await res.json()
        setSubscriptions(data.data ?? [])
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  async function handleRenew(clienteId: string) {
    if (!confirm('¿Registrar el pago de este mes y renovar la suscripción por 30 días?')) return
    setRenewingId(clienteId)
    try {
      const res = await fetch(`/api/admin/clientes/${clienteId}/billing`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'renew' }),
      })
      const data = await res.json()
      if (res.ok && data.success) {
        await loadDue()
      } else {
        alert(data.error || 'Error al renovar')
      }
    } catch {
      alert('Error de red')
    } finally {
      setRenewingId(null)
    }
  }

  return (
    <div className="space-y-8 max-w-4xl">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-text-primary">Renovaciones pendientes</h1>
            <p className="text-text-secondary mt-1 text-sm">
              Suscripciones manuales que vencen en los próximos 3 días
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={loadDue} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Por vencer</CardTitle>
          <CardDescription>
            Solo se muestran suscripciones de transferencia y efectivo (las de Payphone se renuevan automáticamente).
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-10 text-text-muted">
              <Clock className="h-5 w-5 animate-spin mr-2" />
              Cargando...
            </div>
          ) : subscriptions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <CheckCircle className="h-10 w-10 text-success mb-3" />
              <p className="font-medium text-text-primary">Sin renovaciones pendientes</p>
              <p className="text-sm text-text-muted mt-1">Todos los pagos están al día.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {subscriptions.map((sub) => {
                const days = getDaysUntil(sub.next_billing_date)
                const isOverdue = days !== null && days < 0
                const isRenewing = renewingId === sub.cliente_id

                return (
                  <div
                    key={sub.id}
                    className={`flex items-center justify-between gap-4 rounded-lg border p-4 ${
                      isOverdue ? 'border-error/40 bg-error/5' : 'border-border bg-card-bg'
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      {isOverdue ? (
                        <AlertTriangle className="h-5 w-5 text-error shrink-0" />
                      ) : (
                        <Clock className="h-5 w-5 text-warning shrink-0" />
                      )}
                      <div className="min-w-0">
                        <p className="font-medium text-text-primary truncate">
                          {sub.clientes?.nombre_empresa ?? sub.cliente_id.slice(0, 8)}
                        </p>
                        <p className="text-xs text-text-muted">
                          {sub.clientes?.email} · {METHOD_LABEL[sub.payment_method] ?? sub.payment_method}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 shrink-0">
                      <div className="text-right">
                        <p className="text-sm font-semibold text-text-primary">{formatCurrency(sub.monthly_amount)}</p>
                        <p className={`text-xs ${isOverdue ? 'text-error font-medium' : 'text-text-muted'}`}>
                          {isOverdue
                            ? `Venció hace ${Math.abs(days!)} día${Math.abs(days!) !== 1 ? 's' : ''}`
                            : days === 0
                            ? 'Vence hoy'
                            : `Vence en ${days} día${days !== 1 ? 's' : ''} (${formatDate(sub.next_billing_date)})`}
                        </p>
                      </div>
                      <Button
                        size="sm"
                        onClick={() => handleRenew(sub.cliente_id)}
                        disabled={isRenewing}
                      >
                        {isRenewing ? 'Renovando...' : 'Registrar pago'}
                      </Button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
