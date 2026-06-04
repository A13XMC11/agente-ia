'use client'

import { Button } from '@/components/ui/button'
import { CreditCard, CheckCircle, XCircle, Clock } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { formatTimestamp } from '@/lib/date-format'

interface Pago {
  id: string
  monto: number
  moneda: string
  metodo_pago: string
  estado: string
  banco_origen: string | null
  banco_destino: string | null
  numero_transaccion: string | null
  created_at: string
}

interface Toast {
  message: string
  type: 'success' | 'error'
}

function EstadoBadge({ estado }: { estado: string }) {
  if (estado === 'verificado') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-success/10 text-success border border-success/15">
        <CheckCircle className="h-3 w-3" />
        Aprobado
      </span>
    )
  }
  if (estado === 'rechazado') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-error/10 text-error border border-error/15">
        <XCircle className="h-3 w-3" />
        Rechazado
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-warning/10 text-warning border border-warning/15">
      <Clock className="h-3 w-3" />
      Pendiente
    </span>
  )
}

const formatMonto = (monto: number, moneda: string) =>
  new Intl.NumberFormat('es-MX', { style: 'currency', currency: moneda || 'MXN' }).format(monto)

export default function PagosPage() {
  const [pagos, setPagos] = useState<Pago[]>([])
  const [loading, setLoading] = useState(true)
  const [procesando, setProcesando] = useState<string | null>(null)
  const [toast, setToast] = useState<Toast | null>(null)

  function showToast(message: string, type: Toast['type']) {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3500)
  }

  const loadPagos = useCallback(async () => {
    try {
      const res = await fetch('/api/cliente/pagos')
      if (!res.ok) throw new Error('Failed')
      const data = await res.json()
      setPagos(data.data || [])
    } catch {
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadPagos()
  }, [loadPagos])

  async function handleAccion(id: string, accion: 'aprobar' | 'rechazar') {
    setProcesando(id)
    try {
      const res = await fetch('/api/cliente/pagos', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, accion }),
      })
      if (!res.ok) throw new Error('Failed')
      const nuevoEstado = accion === 'aprobar' ? 'verificado' : 'rechazado'
      setPagos((prev) => prev.map((p) => (p.id === id ? { ...p, estado: nuevoEstado } : p)))
      showToast(
        accion === 'aprobar' ? 'Pago aprobado exitosamente' : 'Pago rechazado',
        accion === 'aprobar' ? 'success' : 'error',
      )
    } catch {
      showToast('Error al procesar el pago. Intenta de nuevo.', 'error')
    } finally {
      setProcesando(null)
    }
  }

  const pendientes = pagos.filter((p) => p.estado === 'pendiente').length

  return (
    <div className="space-y-5">
      {/* Toast */}
      {toast && (
        <div
          className={[
            'fixed top-4 right-4 z-50 flex items-center gap-2.5 rounded-xl px-4 py-3 text-sm font-medium shadow-2xl border',
            'animate-[fadeInUp_200ms_ease-out_both]',
            toast.type === 'success'
              ? 'bg-success/15 text-success border-success/25'
              : 'bg-error/15 text-error border-error/25',
          ].join(' ')}
        >
          {toast.type === 'success'
            ? <CheckCircle className="h-4 w-4 shrink-0" />
            : <XCircle className="h-4 w-4 shrink-0" />
          }
          {toast.message}
        </div>
      )}

      <div className="stagger-1">
        <h1 className="text-3xl font-bold text-text-primary tracking-tight">Pagos</h1>
        <p className="text-text-secondary mt-1.5 text-sm">
          Verifica y aprueba comprobantes de pago de tus clientes
        </p>
      </div>

      {/* Summary badge */}
      {pendientes > 0 && (
        <div className="stagger-2 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-warning/10 border border-warning/20 text-warning text-sm font-medium">
          <Clock className="h-4 w-4" />
          {pendientes} pago{pendientes !== 1 ? 's' : ''} pendiente{pendientes !== 1 ? 's' : ''} de revisión
        </div>
      )}

      <div className="stagger-3 rounded-xl border border-border bg-card-bg overflow-hidden">
        <div className="px-5 py-3.5 border-b border-border flex items-center justify-between">
          <p className="text-sm font-medium text-text-primary">Comprobantes</p>
          <p className="text-xs text-text-muted">{pagos.length} total</p>
        </div>

        {loading ? (
          <div className="divide-y divide-border">
            {[1, 2, 3].map((i) => (
              <div key={i} className="px-5 py-4 flex gap-4 animate-pulse">
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-24 rounded bg-surface" />
                  <div className="h-3 w-40 rounded bg-surface" />
                </div>
                <div className="h-8 w-32 rounded bg-surface" />
              </div>
            ))}
          </div>
        ) : pagos.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-14 text-center">
            <CreditCard className="h-10 w-10 text-text-muted mb-3" />
            <p className="text-text-secondary text-sm font-medium">Sin pagos pendientes</p>
            <p className="text-text-muted text-xs mt-1 max-w-xs">
              Los comprobantes aparecerán aquí cuando tus clientes los envíen
            </p>
          </div>
        ) : (
          <>
            {/* Mobile */}
            <ul className="md:hidden divide-y divide-border">
              {pagos.map((pago) => (
                <li key={pago.id} className="p-4 space-y-3">
                  <div className="flex justify-between items-start gap-3">
                    <div className="min-w-0">
                      <p className="font-bold text-text-primary text-lg tabular-nums">
                        {formatMonto(pago.monto, pago.moneda)}
                      </p>
                      <p className="text-xs text-text-secondary capitalize">{pago.metodo_pago}</p>
                      {pago.numero_transaccion && (
                        <p className="text-xs text-text-muted truncate">#{pago.numero_transaccion}</p>
                      )}
                      <p className="text-xs text-text-muted">{formatTimestamp(pago.created_at)}</p>
                    </div>
                    <EstadoBadge estado={pago.estado} />
                  </div>
                  {(pago.banco_origen || pago.banco_destino) && (
                    <p className="text-xs text-text-secondary">
                      {pago.banco_origen} → {pago.banco_destino}
                    </p>
                  )}
                  {pago.estado === 'pendiente' && (
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        className="flex-1 text-xs bg-success hover:bg-success/90 text-white shadow-none"
                        onClick={() => handleAccion(pago.id, 'aprobar')}
                        disabled={procesando === pago.id}
                      >
                        <CheckCircle className="h-3 w-3" />
                        Aprobar
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="flex-1 text-xs border-error/40 text-error hover:bg-error/8"
                        onClick={() => handleAccion(pago.id, 'rechazar')}
                        disabled={procesando === pago.id}
                      >
                        <XCircle className="h-3 w-3" />
                        Rechazar
                      </Button>
                    </div>
                  )}
                </li>
              ))}
            </ul>

            {/* Desktop */}
            <div className="hidden overflow-x-auto overscroll-x-contain md:block">
              <table className="min-w-[900px] w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    {['Monto', 'Método', 'Bancos', 'Transacción', 'Fecha', 'Estado', ''].map((h) => (
                      <th key={h} className="text-left py-3 px-5 text-xs font-semibold text-text-muted uppercase tracking-wider">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {pagos.map((pago) => (
                    <tr key={pago.id} className="hover:bg-surface/40 transition-colors duration-150">
                      <td className="py-3.5 px-5 font-bold text-text-primary tabular-nums">
                        {formatMonto(pago.monto, pago.moneda)}
                      </td>
                      <td className="py-3.5 px-5 text-text-secondary capitalize">{pago.metodo_pago}</td>
                      <td className="py-3.5 px-5 text-text-secondary text-xs">
                        {pago.banco_origen && pago.banco_destino
                          ? `${pago.banco_origen} → ${pago.banco_destino}`
                          : pago.banco_origen || pago.banco_destino || '—'}
                      </td>
                      <td className="py-3.5 px-5 text-text-muted text-xs font-mono">
                        {pago.numero_transaccion ? `#${pago.numero_transaccion}` : '—'}
                      </td>
                      <td className="py-3.5 px-5 text-text-muted text-xs">
                        {formatTimestamp(pago.created_at)}
                      </td>
                      <td className="py-3.5 px-5">
                        <EstadoBadge estado={pago.estado} />
                      </td>
                      <td className="py-3.5 px-5">
                        {pago.estado === 'pendiente' && (
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              className="text-xs bg-success hover:bg-success/90 text-white shadow-none"
                              onClick={() => handleAccion(pago.id, 'aprobar')}
                              disabled={procesando === pago.id}
                            >
                              <CheckCircle className="h-3 w-3" />
                              Aprobar
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-xs border-error/40 text-error hover:bg-error/8"
                              onClick={() => handleAccion(pago.id, 'rechazar')}
                              disabled={procesando === pago.id}
                            >
                              <XCircle className="h-3 w-3" />
                              Rechazar
                            </Button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
