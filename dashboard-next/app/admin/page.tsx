import Link from 'next/link'
import {
  Users, MessageSquare, TrendingUp, Plus,
  DollarSign, TrendingDown, UserCheck, BarChart3,
  ArrowUpRight, ArrowDownRight, Minus,
} from 'lucide-react'
import { getMetrics, getClientesRecientes } from '@/lib/data/metrics'
import { Button } from '@/components/ui/button'

function daysUntil(dateStr: string | null | undefined): number | null {
  if (!dateStr) return null
  return Math.max(0, Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86_400_000))
}

/* ── Stat card ──────────────────────────────────── */
function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  iconColor,
  badge,
  badgePositive,
  accentColor,
  delay = 0,
}: {
  label: string
  value: string | number
  sub: string
  icon: React.ElementType
  iconColor: string
  badge?: string
  badgePositive?: boolean
  accentColor: string
  delay?: number
}) {
  return (
    <div
      className="card-hover card-accent-hover relative min-w-0 overflow-hidden rounded-2xl p-4 sm:p-5 group"
      style={{
        background: 'rgba(9,21,33,0.6)',
        border: '1px solid rgba(255,255,255,0.06)',
        animation: `fadeInUp 340ms cubic-bezier(0.23,1,0.32,1) ${delay}ms both`,
      }}
    >
      <div
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
        style={{ background: `radial-gradient(ellipse 80% 60% at 50% 0%, ${accentColor}, transparent)` }}
      />
      <div className="relative">
        <div className="flex items-start justify-between mb-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] select-none" style={{ color: 'rgba(255,255,255,0.32)' }}>
            {label}
          </p>
          <span
            className="flex h-7 w-7 items-center justify-center rounded-lg shrink-0"
            style={{ background: `${iconColor}18`, border: `1px solid ${iconColor}28` }}
          >
            <Icon className="h-3.5 w-3.5" style={{ color: iconColor }} strokeWidth={2} />
          </span>
        </div>
        <p
          className="text-2xl font-bold leading-none tabular-nums sm:text-3xl"
          style={{ color: 'rgba(255,255,255,0.90)', animation: `count-in 500ms cubic-bezier(0.23,1,0.32,1) ${delay + 80}ms both` }}
        >
          {value}
        </p>
        <div className="flex items-center gap-2 mt-2.5">
          <p className="text-[11px]" style={{ color: 'rgba(255,255,255,0.28)' }}>{sub}</p>
          {badge !== undefined && (
            <span
              className="flex items-center gap-0.5 text-[10px] font-semibold px-1.5 py-0.5 rounded-md"
              style={badgePositive === true ? {
                color: '#22D3A0', background: 'rgba(34,211,160,0.10)',
              } : badgePositive === false ? {
                color: '#F87171', background: 'rgba(248,113,113,0.10)',
              } : {
                color: 'rgba(255,255,255,0.35)', background: 'rgba(255,255,255,0.06)',
              }}
            >
              {badgePositive === true && <ArrowUpRight className="h-2.5 w-2.5" strokeWidth={2.5} />}
              {badgePositive === false && <ArrowDownRight className="h-2.5 w-2.5" strokeWidth={2.5} />}
              {badgePositive === undefined && <Minus className="h-2.5 w-2.5" strokeWidth={2.5} />}
              {badge}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

/* ── Plan bar ───────────────────────────────────── */
function PlanBar({ label, count, mrr, porcentaje, color, barColor, delay = 0 }: {
  label: string
  count: number
  mrr: number
  porcentaje: number
  color: string
  barColor: string
  delay?: number
}) {
  const fmt = (v: number) =>
    new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(v)

  return (
    <div
      className="space-y-1.5"
      style={{ animation: `fadeInUp 300ms cubic-bezier(0.23,1,0.32,1) ${delay}ms both` }}
    >
      <div className="flex items-center justify-between text-xs">
        <span className="font-semibold" style={{ color: 'rgba(255,255,255,0.60)' }}>{label}</span>
        <span style={{ color: 'rgba(255,255,255,0.30)' }}>
          {count} cliente{count !== 1 ? 's' : ''} · {fmt(mrr)}/mes
        </span>
      </div>
      <div
        className="h-1.5 w-full rounded-full overflow-hidden"
        style={{ background: 'rgba(255,255,255,0.06)' }}
      >
        <div
          className="h-full rounded-full score-bar-fill"
          style={{
            width: `${porcentaje}%`,
            background: barColor,
            boxShadow: `0 0 8px ${barColor}60`,
          }}
        />
      </div>
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-semibold" style={{ color }}>
          {porcentaje}%
        </span>
      </div>
    </div>
  )
}

const PLAN_CONFIG: Record<string, { color: string; barColor: string }> = {
  basico:      { color: '#818CF8', barColor: '#818CF8' },
  profesional: { color: '#38BDF8', barColor: '#38BDF8' },
  empresarial: { color: '#22D3A0', barColor: '#22D3A0' },
}

/* ── Section label ──────────────────────────────── */
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h2
      className="text-[10px] font-bold uppercase tracking-[0.16em] mb-3 select-none"
      style={{ color: 'rgba(255,255,255,0.28)' }}
    >
      {children}
    </h2>
  )
}

/* ── Page ───────────────────────────────────────── */
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
      ? { text: `+${metrics.crecimientoClientes}%`, positive: true }
      : { text: `${metrics.crecimientoClientes}%`, positive: false }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="stagger-1">
        <p
          className="text-[10px] font-semibold uppercase tracking-[0.16em] mb-1.5"
          style={{ color: 'rgba(255,255,255,0.28)' }}
        >
          Super Admin
        </p>
        <h1 className="text-2xl font-bold text-white/90 tracking-tight">Panel global</h1>
        <p className="mt-1 text-sm" style={{ color: 'rgba(255,255,255,0.35)' }}>
          Métricas de toda la plataforma
        </p>
      </div>

      {/* Revenue metrics */}
      <section className="stagger-2">
        <SectionLabel>Revenue</SectionLabel>
        <div className="grid grid-cols-1 min-[430px]:grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard
            label="MRR"
            value={formatCurrency(metrics.mrr)}
            sub="Ingresos mensuales"
            icon={TrendingUp}
            iconColor="#22D3A0"
            accentColor="rgba(34,211,160,0.07)"
            delay={60}
          />
          <StatCard
            label="ARR"
            value={formatCurrency(metrics.arr)}
            sub="Ingresos anuales proyectados"
            icon={DollarSign}
            iconColor="#22D3A0"
            accentColor="rgba(34,211,160,0.06)"
            delay={100}
          />
          <StatCard
            label="MRR Nuevo"
            value={formatCurrency(metrics.mrrNuevoEsteMes)}
            sub="Nuevos clientes este mes"
            icon={ArrowUpRight}
            iconColor="#38BDF8"
            accentColor="rgba(56,189,248,0.06)"
            badge={metrics.mrrNuevoEsteMes > 0 ? 'Este mes' : undefined}
            badgePositive={metrics.mrrNuevoEsteMes > 0 ? true : undefined}
            delay={140}
          />
          <StatCard
            label="ARPU"
            value={formatCurrency(metrics.arpu)}
            sub="Ingreso por cliente"
            icon={BarChart3}
            iconColor="#818CF8"
            accentColor="rgba(129,140,248,0.06)"
            delay={180}
          />
        </div>
      </section>

      {/* Client metrics */}
      <section className="stagger-3">
        <SectionLabel>Clientes</SectionLabel>
        <div className="grid grid-cols-1 min-[430px]:grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard
            label="Total"
            value={metrics.totalClientes}
            sub="Todos los clientes"
            icon={Users}
            iconColor="#38BDF8"
            accentColor="rgba(56,189,248,0.06)"
            delay={60}
          />
          <StatCard
            label="Activos"
            value={metrics.clientesActivos}
            sub="Con suscripción activa"
            icon={UserCheck}
            iconColor="#22D3A0"
            accentColor="rgba(34,211,160,0.06)"
            delay={100}
          />
          <StatCard
            label="Nuevos"
            value={metrics.clientesNuevosEsteMes}
            sub="Este mes"
            icon={TrendingUp}
            iconColor="#38BDF8"
            accentColor="rgba(56,189,248,0.06)"
            badge={growthBadge.text}
            badgePositive={growthBadge.positive}
            delay={140}
          />
          <StatCard
            label="Churn"
            value={`${metrics.churnRate}%`}
            sub={`${metrics.clientesPausados} pausado${metrics.clientesPausados !== 1 ? 's' : ''}`}
            icon={TrendingDown}
            iconColor={metrics.churnRate > 10 ? '#F87171' : '#FBBF24'}
            accentColor={metrics.churnRate > 10 ? 'rgba(248,113,113,0.06)' : 'rgba(251,191,36,0.06)'}
            badge={metrics.churnRate === 0 ? 'Sin churn' : undefined}
            delay={180}
          />
        </div>
      </section>

      {/* Operations + Plan distribution */}
      <div className="stagger-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Messages today */}
        <div
          className="card-hover card-accent-hover min-w-0 rounded-2xl p-4 overflow-hidden group sm:p-5"
          style={{ background: 'rgba(9,21,33,0.6)', border: '1px solid rgba(255,255,255,0.06)' }}
        >
          <div
            className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
            style={{ background: 'radial-gradient(ellipse 80% 60% at 50% 0%, rgba(129,140,248,0.07), transparent)' }}
          />
          <div className="relative">
            <div className="flex items-start justify-between mb-4">
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em]" style={{ color: 'rgba(255,255,255,0.32)' }}>
                Mensajes hoy
              </p>
              <span
                className="flex h-7 w-7 items-center justify-center rounded-lg shrink-0"
                style={{ background: 'rgba(129,140,248,0.12)', border: '1px solid rgba(129,140,248,0.22)' }}
              >
                <MessageSquare className="h-3.5 w-3.5" style={{ color: '#818CF8' }} strokeWidth={2} />
              </span>
            </div>
            <p className="text-2xl font-bold tabular-nums leading-none sm:text-3xl" style={{ color: 'rgba(255,255,255,0.90)' }}>
              {metrics.mensajesHoy}
            </p>
            <p className="text-[11px] mt-2.5" style={{ color: 'rgba(255,255,255,0.28)' }}>
              En todos los clientes
            </p>
          </div>
        </div>

        {/* Plan distribution */}
        <div
          className="min-w-0 rounded-2xl p-4 sm:p-5 lg:col-span-2"
          style={{ background: 'rgba(9,21,33,0.6)', border: '1px solid rgba(255,255,255,0.06)' }}
        >
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] mb-5" style={{ color: 'rgba(255,255,255,0.32)' }}>
            Distribución por plan
          </p>
          {metrics.distribucionPlanes.length === 0 || metrics.clientesActivos === 0 ? (
            <p className="text-sm" style={{ color: 'rgba(255,255,255,0.28)' }}>Sin datos de planes</p>
          ) : (
            <div className="space-y-5">
              {metrics.distribucionPlanes.map((p, i) => {
                const cfg = PLAN_CONFIG[p.plan] || { color: '#38BDF8', barColor: '#38BDF8' }
                return (
                  <PlanBar
                    key={p.plan}
                    label={p.label}
                    count={p.count}
                    mrr={p.mrr}
                    porcentaje={p.porcentaje}
                    color={cfg.color}
                    barColor={cfg.barColor}
                    delay={i * 60}
                  />
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Recent clients table */}
      <div className="stagger-5">
        <div className="flex items-center justify-between mb-4 gap-3">
          <h2 className="text-sm font-semibold" style={{ color: 'rgba(255,255,255,0.70)' }}>
            Clientes recientes
          </h2>
          <Link href="/admin/clientes/nuevo" className="shrink-0">
            <Button size="sm" className="text-xs gap-1.5 cursor-pointer">
              <Plus className="h-3.5 w-3.5" strokeWidth={2.5} />
              Nuevo cliente
            </Button>
          </Link>
        </div>

        <div
          className="rounded-2xl overflow-hidden"
          style={{ border: '1px solid rgba(255,255,255,0.06)', background: 'rgba(9,21,33,0.5)' }}
        >
          {clientesRecientes.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
              <div
                className="h-12 w-12 rounded-2xl flex items-center justify-center"
                style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
              >
                <Users className="h-5 w-5 text-white/20" strokeWidth={1.5} />
              </div>
              <div>
                <p className="text-white/45 text-sm font-medium">Sin clientes aún</p>
                <p className="text-white/22 text-xs mt-0.5">Crea tu primer cliente para empezar</p>
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto overscroll-x-contain">
              <table className="min-w-[680px] w-full text-sm">
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    {['Nombre', 'Email', 'Plan', 'Estado', 'Próximo cobro', 'Fecha'].map((h) => (
                      <th
                        key={h}
                        className="text-left py-3 px-5 text-[10px] font-semibold uppercase tracking-[0.12em] whitespace-nowrap select-none"
                        style={{ color: 'rgba(255,255,255,0.28)' }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {clientesRecientes.map((cliente, idx) => (
                    <tr
                      key={cliente.id}
                      className="group transition-colors duration-150 hover:bg-white/[0.02]"
                      style={{ borderTop: idx > 0 ? '1px solid rgba(255,255,255,0.04)' : 'none' }}
                    >
                      <td className="py-3.5 px-5 font-semibold" style={{ color: 'rgba(255,255,255,0.78)' }}>
                        <Link
                          href={`/admin/clientes/${cliente.id}`}
                          className="group-hover:text-accent transition-colors duration-150 cursor-pointer"
                        >
                          {cliente.nombre}
                        </Link>
                      </td>
                      <td className="py-3.5 px-5 text-xs font-mono" style={{ color: 'rgba(255,255,255,0.38)' }}>
                        {cliente.email}
                      </td>
                      <td className="py-3.5 px-5 text-xs capitalize" style={{ color: 'rgba(255,255,255,0.45)' }}>
                        {cliente.plan}
                      </td>
                      <td className="py-3.5 px-5">
                        <span
                          className="px-2 py-0.5 rounded-md text-[10px] font-semibold"
                          style={cliente.estado === 'activo' ? {
                            color: '#22D3A0', background: 'rgba(34,211,160,0.10)', border: '1px solid rgba(34,211,160,0.18)',
                          } : {
                            color: '#FBBF24', background: 'rgba(251,191,36,0.10)', border: '1px solid rgba(251,191,36,0.18)',
                          }}
                        >
                          {cliente.estado}
                        </span>
                      </td>
                      <td className="py-3.5 px-5">
                        {(() => {
                          if (cliente.subscription_status === 'cancelled') {
                            return <span style={{ color: 'rgba(255,255,255,0.20)', fontSize: '11px' }}>—</span>
                          }
                          const days = daysUntil(cliente.next_billing_date)
                          if (days === null) return <span style={{ color: 'rgba(255,255,255,0.20)', fontSize: '11px' }}>—</span>
                          const color = days <= 3 ? '#F87171' : days <= 7 ? '#FBBF24' : 'rgba(255,255,255,0.38)'
                          const bg = days <= 3 ? 'rgba(248,113,113,0.10)' : days <= 7 ? 'rgba(251,191,36,0.10)' : 'rgba(255,255,255,0.06)'
                          return (
                            <span
                              className="px-2 py-0.5 rounded-md text-[10px] font-bold tabular-nums"
                              style={{ color, background: bg }}
                            >
                              {days === 0 ? 'Hoy' : `${days}d`}
                            </span>
                          )
                        })()}
                      </td>
                      <td className="py-3.5 px-5 text-[11px] font-mono" style={{ color: 'rgba(255,255,255,0.25)' }}>
                        {formatDate(cliente.created_at)}
                      </td>
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
