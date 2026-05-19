'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { CreditCard, CheckCircle, XCircle } from 'lucide-react'
import { useState, useEffect } from 'react'
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

export default function PagosPage() {
  const [pagos, setPagos] = useState<Pago[]>([])
  const [loading, setLoading] = useState(true)
  const [procesando, setProcesando] = useState<string | null>(null)

  useEffect(() => {
    loadPagos()
  }, [])

  async function loadPagos() {
    try {
      const response = await fetch('/api/cliente/pagos')
      if (!response.ok) throw new Error('Failed to load')
      const data = await response.json()
      setPagos(data.data || [])
    } catch (error) {
      console.error('Error loading pagos:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleAccion(id: string, accion: 'aprobar' | 'rechazar') {
    setProcesando(id)
    try {
      const response = await fetch('/api/cliente/pagos', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, accion }),
      })
      if (!response.ok) throw new Error('Failed to update')
      setPagos((prev) => prev.filter((p) => p.id !== id))
    } catch (error) {
      console.error('Error updating pago:', error)
    } finally {
      setProcesando(null)
    }
  }

  const formatMonto = (monto: number, moneda: string) =>
    new Intl.NumberFormat('es-MX', { style: 'currency', currency: moneda || 'MXN' }).format(monto)

  return (
    <div className="space-y-4 md:space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold text-text-primary">Pagos Pendientes</h1>
        <p className="text-text-secondary mt-1 text-sm md:text-base">
          Verifica y aprueba comprobantes de pago enviados por tus clientes
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Comprobantes por Revisar</CardTitle>
          <CardDescription>{pagos.length} pago{pagos.length !== 1 ? 's' : ''} pendiente{pagos.length !== 1 ? 's' : ''}</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-12">
              <p className="text-text-secondary">Cargando pagos...</p>
            </div>
          ) : pagos.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <CreditCard className="h-12 w-12 text-text-muted mb-4" />
              <p className="text-text-secondary">Sin pagos pendientes</p>
              <p className="text-sm text-text-muted mt-2">
                Los comprobantes de pago aparecerán aquí cuando tus clientes los envíen
              </p>
            </div>
          ) : (
            <>
              {/* Mobile: card list */}
              <div className="md:hidden space-y-3">
                {pagos.map((pago) => (
                  <div key={pago.id} className="p-4 border rounded-lg space-y-3">
                    <div className="flex justify-between items-start gap-2">
                      <div className="min-w-0">
                        <p className="font-semibold text-text-primary">
                          {formatMonto(pago.monto, pago.moneda)}
                        </p>
                        <p className="text-xs text-text-secondary">{pago.metodo_pago}</p>
                        {pago.numero_transaccion && (
                          <p className="text-xs text-text-muted truncate">#{pago.numero_transaccion}</p>
                        )}
                      </div>
                      <p className="text-xs text-text-muted shrink-0">{formatTimestamp(pago.created_at)}</p>
                    </div>
                    {(pago.banco_origen || pago.banco_destino) && (
                      <p className="text-xs text-text-secondary">
                        {pago.banco_origen} → {pago.banco_destino}
                      </p>
                    )}
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        className="flex-1 bg-success hover:bg-success/90 text-white text-xs"
                        onClick={() => handleAccion(pago.id, 'aprobar')}
                        disabled={procesando === pago.id}
                      >
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Aprobar
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="flex-1 border-error text-error hover:bg-error/10 text-xs"
                        onClick={() => handleAccion(pago.id, 'rechazar')}
                        disabled={procesando === pago.id}
                      >
                        <XCircle className="h-3 w-3 mr-1" />
                        Rechazar
                      </Button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Desktop: table */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="border-b">
                    <tr>
                      <th className="text-left py-3 px-4 font-semibold text-text-primary">Monto</th>
                      <th className="text-left py-3 px-4 font-semibold text-text-primary">Método</th>
                      <th className="text-left py-3 px-4 font-semibold text-text-primary">Bancos</th>
                      <th className="text-left py-3 px-4 font-semibold text-text-primary">Transacción</th>
                      <th className="text-left py-3 px-4 font-semibold text-text-primary">Fecha</th>
                      <th className="text-left py-3 px-4 font-semibold text-text-primary">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pagos.map((pago) => (
                      <tr key={pago.id} className="border-b hover:bg-surface">
                        <td className="py-3 px-4 font-semibold text-text-primary">
                          {formatMonto(pago.monto, pago.moneda)}
                        </td>
                        <td className="py-3 px-4 text-text-secondary">{pago.metodo_pago}</td>
                        <td className="py-3 px-4 text-text-secondary text-xs">
                          {pago.banco_origen && pago.banco_destino
                            ? `${pago.banco_origen} → ${pago.banco_destino}`
                            : pago.banco_origen || pago.banco_destino || '-'}
                        </td>
                        <td className="py-3 px-4 text-text-muted text-xs">
                          {pago.numero_transaccion ? `#${pago.numero_transaccion}` : '-'}
                        </td>
                        <td className="py-3 px-4 text-text-secondary text-xs">
                          {formatTimestamp(pago.created_at)}
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              className="bg-success hover:bg-success/90 text-white text-xs"
                              onClick={() => handleAccion(pago.id, 'aprobar')}
                              disabled={procesando === pago.id}
                            >
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Aprobar
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="border-error text-error hover:bg-error/10 text-xs"
                              onClick={() => handleAccion(pago.id, 'rechazar')}
                              disabled={procesando === pago.id}
                            >
                              <XCircle className="h-3 w-3 mr-1" />
                              Rechazar
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
