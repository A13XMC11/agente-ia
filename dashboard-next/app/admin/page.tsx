import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { Users, MessageSquare, TrendingUp } from 'lucide-react'
import { getMetrics, getClientesRecientes } from '@/lib/data/metrics'

export default async function AdminDashboard() {
  const [metrics, clientesRecientes] = await Promise.all([
    getMetrics(),
    getClientesRecientes(),
  ])

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(value)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-CO')
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-4xl font-bold text-text-primary">Dashboard</h1>
          <p className="text-text-secondary mt-2">Bienvenido al panel de administración</p>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Clientes</CardTitle>
            <Users className="h-4 w-4 text-accent" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{metrics.totalClientes}</div>
            <p className="text-xs text-text-secondary mt-1">Clientes activos</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">MRR</CardTitle>
            <TrendingUp className="h-4 w-4 text-success" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{formatCurrency(metrics.mrr)}</div>
            <p className="text-xs text-text-secondary mt-1">Ingresos mensuales recurrentes</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Mensajes</CardTitle>
            <MessageSquare className="h-4 w-4 text-info" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{metrics.mensajesHoy}</div>
            <p className="text-xs text-text-secondary mt-1">Hoy</p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Clients */}
      <div>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-text-primary">Clientes Recientes</h2>
          <Link href="/admin/clientes/nuevo">
            <Button>Nuevo Cliente</Button>
          </Link>
        </div>

        <Card>
          <CardContent className="pt-6">
            {clientesRecientes.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-text-secondary">No hay clientes aún</p>
                <p className="text-sm text-text-muted mt-2">Crea tu primer cliente para empezar</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-3 px-4 font-semibold text-text-primary">Nombre</th>
                      <th className="text-left py-3 px-4 font-semibold text-text-primary">Email</th>
                      <th className="text-left py-3 px-4 font-semibold text-text-primary">Plan</th>
                      <th className="text-left py-3 px-4 font-semibold text-text-primary">Estado</th>
                      <th className="text-left py-3 px-4 font-semibold text-text-primary">Fecha</th>
                    </tr>
                  </thead>
                  <tbody>
                    {clientesRecientes.map((cliente) => (
                      <tr key={cliente.id} className="border-b hover:bg-surface">
                        <td className="py-3 px-4 text-text-primary">{cliente.nombre}</td>
                        <td className="py-3 px-4 text-text-secondary">{cliente.email}</td>
                        <td className="py-3 px-4 text-text-secondary">{cliente.plan}</td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-1 rounded text-xs font-medium ${
                              cliente.estado === 'activo'
                                ? 'bg-success/10 text-success'
                                : 'bg-warning/10 text-warning'
                            }`}
                          >
                            {cliente.estado}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-text-secondary text-sm">
                          {formatDate(cliente.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
