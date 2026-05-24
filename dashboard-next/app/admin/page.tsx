import Link from 'next/link'
import {
  Users, MessageSquare, TrendingUp, Plus,
  DollarSign, TrendingDown, UserCheck, BarChart3,
  ArrowUpRight, ArrowDownRight, Minus,
} from 'lucide-react'
import { getMetrics, getClientesRecientes } from '@/lib/data/metrics'
import { Button } from '@/components/ui/button'

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  iconBg,
  iconColor,
  badge,
  badgePositive,
}: {
  label: string
  value: string | number
  sub: string
  icon: React.ElementType
  iconBg: string
  iconColor: string
  badge?: string
  badgePositive?: boolean
}) {
  return (
    <div className="rounded-xl border border-border bg-card-bg p-5 transition-all duration-200 hover:border-border-light hover:shadow-[0_0_0_1px_rgba(56,189,248,0.06),0_8px_32px_rgba(0,0,0,0.4)]">
      <div className="flex items-start justify-between mb-4">
        <p className="text-xs font-medium text-text-secondary uppercase tracking-wider">{label}</p>
        <span className={['flex h-8 w-8 items-center justify-center rounded-lg', iconBg].join(' ')}>
          <Icon className={['h-4 w-4', iconColor].join(' ')} />
        </span>
      </div>
      <p className="text-3xl font-bold text-text-primary leading-none">{value}</p>
      <div className="flex items-center gap-2 mt-2">
        <p className="text-xs text-text-muted">{sub}</p>
        {badge !== undefined && (
          <span className={[
            'flex items-center gap-0.5 text-xs font-medium px-1.5 py-0.5 rounded',
            badgePositive
              ? 'text-success bg-success/10'
              : badgePositive === false
                ? 'text-error bg-error/10'
                : 'text-text-muted bg-surface',
          ].join(' ')}>
            {badgePositive === true && <ArrowUpRight className="h-3 w-3" />}
            {badgePositive === false && <ArrowDownRight className="h-3 w-3" />}
            {badgePositive === undefined && <Minus className="h-3 w-3" />}
            {badge}
          </span>
        )}
      </div>
    </div>
  )
}

function PlanBar({ label, count, mrr, porcentaje, color }: {
  label: string
  count: number
  mrr: number
  porcentaje: number
  color: string
}) {
  const formatUSD = (v: number) =>
    new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(v)

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-text-secondary font-medium">{label}</span>
        <span className="text-text-muted">{count} cliente{count !== 1 ? 's' : ''} · {formatUSD(mrr)}/mes</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-surface overflow-hidden">
        <div
          className={['h-full rounded-full transition-all duration-700', color].join(' ')}
          style={{ width: `${porcentaje}%` }}
        />
      </div>
      <p className="text-xs text-text-muted text-right">{porcentaje}%</p>
    </div>
  )
}

const PLAN_COLORS: Record<string, string> = {
  basico: 'bg-accent-indigo',
  profesional: 'bg-accent',
  empresarial: 'bg-success',
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

  const growthBadge = metrics.crecimientoClientes === 0
    ? { text: 'Sin cambio', positive: undefined }
    : metrics.crecimientoClientes > 0
      ? { text: `+${metrics.crecimientoClientes}% vs mes anterior`, positive: true }
      : { text: `${metrics.crecimientoClientes}% vs mes anterior`, positive: false }

  const churnPositive = metrics.churnRate === 0 ? undefined : false

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl md:text-4xl font-bold text-text-primary tracking-tight">Dashboard</h1>
        <p className="text-text-secondary mt-1.5 text-sm">Panel de administración global</p>
      </div>

      {/* Fila 1: Revenue */}
      <section className="space-y-3">
        <h2 className="text-xs font-semibold text-text-muted uppercase tracking-widest">Revenue</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard
            label="MRR"
            value={formatCurrency(metrics.mrr)}
            sub="Ingresos mensuales recurrentes"
            icon={TrendingUp}
            iconBg="bg-success/10"
            iconColor="text-success"
          />
          <StatCard
            label="ARR"
            value={formatCurrency(metrics.arr)}
            sub="Ingresos anuales proyectados"
            icon={DollarSign}
            iconBg="bg-success/10"
            iconColor="text-success"
          />
          <StatCard
            label="MRR Nuevo"
            value={formatCurrency(metrics.mrrNuevoEsteMes)}
            sub="De nuevos clientes este mes"
            icon={ArrowUpRight}
            iconBg="bg-accent/10"
            iconColor="text-accent"
            badge={metrics.mrrNuevoEsteMes > 0 ? 'Este mes' : undefined}
            badgePositive={metrics.mrrNuevoEsteMes > 0 ? true : undefined}
          />
          <StatCard
            label="ARPU"
            value={formatCurrency(metrics.arpu)}
            sub="Ingreso promedio por cliente"
            icon={BarChart3}
            iconBg="bg-accent-indigo/10"
            iconColor="text-accent-indigo"
          />
        </div>
      </section>

      {/* Fila 2: Clientes */}
      <section className="space-y-3">
        <h2 className="text-xs font-semibold text-text-muted uppercase tracking-widest">Clientes</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard
            label="Total Clientes"
            value={metrics.totalClientes}
            sub="Todos los clientes"
            icon={Users}
            iconBg="bg-accent/10"
            iconColor="text-accent"
          />
          <StatCard
            label="Activos"
            value={metrics.clientesActivos}
            sub="Con suscripción activa"
            icon={UserCheck}
            iconBg="bg-success/10"
            iconColor="text-success"
          />
          <StatCard
            label="Nuevos este mes"
            value={metrics.clientesNuevosEsteMes}
            sub="Clientes registrados"
            icon={TrendingUp}
            iconBg="bg-accent/10"
            iconColor="text-accent"
            badge={growthBadge.text}
            badgePositive={growthBadge.positive}
          />
          <StatCard
            label="Churn Rate"
            value={`${metrics.churnRate}%`}
            sub={`${metrics.clientesPausados} cliente${metrics.clientesPausados !== 1 ? 's' : ''} pausado${metrics.clientesPausados !== 1 ? 's' : ''}`}
            icon={TrendingDown}
            iconBg={metrics.churnRate > 10 ? 'bg-error/10' : 'bg-warning/10'}
            iconColor={metrics.churnRate > 10 ? 'text-error' : 'text-warning'}
            badge={metrics.churnRate === 0 ? 'Sin churn' : undefined}
            badgePositive={churnPositive}
          />
        </div>
      </section>

      {/* Fila 3: Operaciones + Distribución */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Mensajes hoy */}
        <div className="rounded-xl border border-border bg-card-bg p-5">
          <div className="flex items-start justify-between mb-4">
            <p className="text-xs font-medium text-text-secondary uppercase tracking-wider">Mensajes hoy</p>
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-indigo/10">
              <MessageSquare className="h-4 w-4 text-accent-indigo" />
            </span>
          </div>
          <p className="text-3xl font-bold text-text-primary leading-none">{metrics.mensajesHoy}</p>
          <p className="text-xs text-text-muted mt-2">En todos los clientes</p>
        </div>

        {/* Distribución por plan */}
        <div className="lg:col-span-2 rounded-xl border border-border bg-card-bg p-5">
          <p className="text-xs font-medium text-text-secondary uppercase tracking-wider mb-5">
            Distribución por plan
          </p>
          {metrics.distribucionPlanes.length === 0 || metrics.clientesActivos === 0 ? (
            <p className="text-sm text-text-muted">Sin datos</p>
          ) : (
            <div className="space-y-4">
              {metrics.distribucionPlanes.map((p) => (
                <PlanBar
                  key={p.plan}
                  label={p.label}
                  count={p.count}
                  mrr={p.mrr}
                  porcentaje={p.porcentaje}
                  color={PLAN_COLORS[p.plan] || 'bg-accent'}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Tabla clientes recientes */}
      <div>
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
                        <Link href={`/admin/clientes/${cliente.id}`}>
                          {cliente.nombre}
                        </Link>
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
