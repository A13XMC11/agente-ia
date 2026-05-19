import Link from 'next/link'
import { Users, MessageSquare, TrendingUp, Plus } from 'lucide-react'
import { getMetrics, getClientesRecientes } from '@/lib/data/metrics'
import { Button } from '@/components/ui/button'

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  iconBg,
  iconColor,
  className,
}: {
  label: string
  value: string | number
  sub: string
  icon: React.ElementType
  iconBg: string
  iconColor: string
  className?: string
}) {
  return (
    <div
      className={[
        'rounded-xl border border-border bg-card-bg p-5',
        'transition-all duration-200 hover:border-border-light',
        'hover:shadow-[0_0_0_1px_rgba(56,189,248,0.06),0_8px_32px_rgba(0,0,0,0.4)]',
        className ?? '',
      ].join(' ')}
    >
      <div className="flex items-start justify-between mb-4">
        <p className="text-xs font-medium text-text-secondary uppercase tracking-wider">{label}</p>
        <span className={['flex h-8 w-8 items-center justify-center rounded-lg', iconBg].join(' ')}>
          <Icon className={['h-4 w-4', iconColor].join(' ')} />
        </span>
      </div>
      <p className="text-3xl font-bold text-text-primary leading-none">{value}</p>
      <p className="text-xs text-text-muted mt-2">{sub}</p>
    </div>
  )
}

export default async function AdminDashboard() {
  const [metrics, clientesRecientes] = await Promise.all([
    getMetrics(),
    getClientesRecientes(),
  ])

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(value)

  const formatDate = (dateString: string) =>
    new Date(dateString).toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' })

  const metricCards = [
    { label: 'Total Clientes', value: metrics.totalClientes, sub: 'Clientes activos',          icon: Users,        iconBg: 'bg-accent/10',        iconColor: 'text-accent',        className: 'stagger-1' },
    { label: 'MRR',            value: formatCurrency(metrics.mrr), sub: 'Ingresos mensuales',  icon: TrendingUp,   iconBg: 'bg-success/10',       iconColor: 'text-success',       className: 'stagger-2' },
    { label: 'Mensajes Hoy',   value: metrics.mensajesHoy, sub: 'En todos los clientes',       icon: MessageSquare,iconBg: 'bg-accent-indigo/10', iconColor: 'text-accent-indigo', className: 'stagger-3' },
  ]

  return (
    <div className="space-y-8">
      <div className="stagger-1">
        <h1 className="text-3xl md:text-4xl font-bold text-text-primary tracking-tight">Dashboard</h1>
        <p className="text-text-secondary mt-1.5 text-sm">Panel de administración global</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 md:gap-4">
        {metricCards.map((c) => <StatCard key={c.label} {...c} />)}
      </div>

      <div className="stagger-3">
        <div className="flex items-center justify-between mb-3 gap-3">
          <h2 className="text-lg font-semibold text-text-primary">Clientes recientes</h2>
          <Link href="/admin/clientes/nuevo">
            <Button size="sm" className="text-xs gap-1.5">
              <Plus className="h-3.5 w-3.5" />
              Nuevo cliente
            </Button>
          </Link>
        </div>

        <div className="rounded-xl border border-border bg-card-bg overflow-hidden">
          {clientesRecientes.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-14 text-center">
              <Users className="h-10 w-10 text-text-muted mb-3" />
              <p className="text-text-secondary text-sm font-medium">No hay clientes aún</p>
              <p className="text-text-muted text-xs mt-1">Crea tu primer cliente para empezar</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    {['Nombre', 'Email', 'Plan', 'Estado', 'Fecha'].map((h) => (
                      <th key={h} className="text-left py-3 px-5 text-xs font-semibold text-text-muted uppercase tracking-wider">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {clientesRecientes.map((cliente) => (
                    <tr key={cliente.id} className="hover:bg-surface/40 transition-colors duration-150 group">
                      <td className="py-3.5 px-5 font-medium text-text-primary group-hover:text-accent transition-colors duration-150">
                        {cliente.nombre}
                      </td>
                      <td className="py-3.5 px-5 text-text-secondary">{cliente.email}</td>
                      <td className="py-3.5 px-5 text-text-secondary capitalize">{cliente.plan}</td>
                      <td className="py-3.5 px-5">
                        <span className={[
                          'px-2 py-0.5 rounded-md text-xs font-medium border',
                          cliente.estado === 'activo'
                            ? 'bg-success/10 text-success border-success/15'
                            : 'bg-warning/10 text-warning border-warning/15',
                        ].join(' ')}>
                          {cliente.estado}
                        </span>
                      </td>
                      <td className="py-3.5 px-5 text-text-muted text-xs">{formatDate(cliente.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
