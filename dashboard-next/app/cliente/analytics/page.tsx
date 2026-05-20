import { BarChart2, MessageSquare, TrendingUp, Calendar, CreditCard } from 'lucide-react'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

/* ── Types ─────────────────────────────────────────── */
interface DayCount { label: string; value: number }
interface CanalStat { label: string; value: number; color: string }
interface EstadoStat { label: string; value: number; color: string }

interface AnalyticsData {
  kpis: {
    mensajesMes: number
    leadsMes: number
    citasMes: number
    pagosVerificados: number
    pagosMontoMes: number
  }
  mensajesPorDia: DayCount[]
  canales: CanalStat[]
  estados: EstadoStat[]
}

/* ── Constants ─────────────────────────────────────── */
const CANAL_COLORS: Record<string, string> = {
  whatsapp: '#22D3A0',
  instagram: '#818CF8',
  facebook: '#60A5FA',
  email: '#FBBF24',
}

const ESTADO_COLORS: Record<string, string> = {
  urgente: '#F87171',
  caliente: '#FB923C',
  interesado: '#FBBF24',
  prospecto: '#60A5FA',
  curioso: '#3D5166',
}

const ESTADO_LABELS: Record<string, string> = {
  urgente: 'Urgente',
  caliente: 'Caliente',
  interesado: 'Interesado',
  prospecto: 'Prospecto',
  curioso: 'Curioso',
}

/* ── Data fetching ─────────────────────────────────── */
async function getAnalyticsData(clienteId: string): Promise<AnalyticsData> {
  const now = new Date()
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1).toISOString()
  const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString()

  const days: DayCount[] = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now.getTime() - i * 24 * 60 * 60 * 1000)
    days.push({ label: d.toLocaleDateString('es', { weekday: 'short' }), value: 0 })
  }

  const [
    { count: mensajesMes },
    { data: mensajesRecientes },
    { count: leadsMes },
    { data: leadsAll },
    { count: citasMes },
    { data: conversacionesAll },
    { data: pagosAll },
  ] = await Promise.all([
    supabase.from('mensajes').select('*', { count: 'exact', head: true }).eq('cliente_id', clienteId).gte('created_at', startOfMonth),
    supabase.from('mensajes').select('created_at').eq('cliente_id', clienteId).gte('created_at', sevenDaysAgo),
    supabase.from('leads').select('*', { count: 'exact', head: true }).eq('cliente_id', clienteId).gte('created_at', startOfMonth),
    supabase.from('leads').select('estado').eq('cliente_id', clienteId),
    supabase.from('citas').select('*', { count: 'exact', head: true }).eq('cliente_id', clienteId).gte('created_at', startOfMonth),
    supabase.from('conversaciones').select('canal').eq('cliente_id', clienteId),
    supabase.from('pagos').select('monto, estado').eq('cliente_id', clienteId).gte('created_at', startOfMonth),
  ])

  // Group messages by day bucket
  for (const msg of mensajesRecientes || []) {
    const daysAgo = Math.floor((now.getTime() - new Date(msg.created_at).getTime()) / 86_400_000)
    const idx = 6 - daysAgo
    if (idx >= 0 && idx < 7) days[idx].value++
  }

  // Group by canal
  const canalMap: Record<string, number> = {}
  for (const c of conversacionesAll || []) {
    const key = c.canal || 'otro'
    canalMap[key] = (canalMap[key] || 0) + 1
  }
  const canales: CanalStat[] = Object.entries(canalMap)
    .map(([label, value]) => ({ label, value, color: CANAL_COLORS[label] ?? '#4A5C6A' }))
    .sort((a, b) => b.value - a.value)

  // Group by estado
  const estadoMap: Record<string, number> = {}
  for (const l of leadsAll || []) {
    const key = l.estado || 'curioso'
    estadoMap[key] = (estadoMap[key] || 0) + 1
  }
  const estados: EstadoStat[] = Object.entries(estadoMap)
    .map(([label, value]) => ({ label, value, color: ESTADO_COLORS[label] ?? '#3D5166' }))
    .sort((a, b) => b.value - a.value)

  const pagosVerificados = (pagosAll || []).filter(p => p.estado === 'verificado').length
  const pagosMontoMes = (pagosAll || [])
    .filter(p => p.estado === 'verificado')
    .reduce((sum, p) => sum + (Number(p.monto) || 0), 0)

  return {
    kpis: { mensajesMes: mensajesMes || 0, leadsMes: leadsMes || 0, citasMes: citasMes || 0, pagosVerificados, pagosMontoMes },
    mensajesPorDia: days,
    canales,
    estados,
  }
}

/* ── Bar Chart (SVG) ───────────────────────────────── */
function BarChart({ data }: { data: DayCount[] }) {
  const maxVal = Math.max(...data.map(d => d.value), 1)
  const BAR_W = 28
  const GAP = 12
  const CHART_H = 72
  const TOTAL_W = data.length * (BAR_W + GAP) - GAP + 2

  return (
    <svg
      viewBox={`0 0 ${TOTAL_W} ${CHART_H + 22}`}
      className="w-full"
      aria-label="Mensajes por día"
    >
      {/* Baseline */}
      <line x1={0} y1={CHART_H} x2={TOTAL_W} y2={CHART_H} stroke="rgba(255,255,255,0.06)" strokeWidth={1} />

      {data.map((d, i) => {
        const barH = Math.max((d.value / maxVal) * CHART_H, d.value > 0 ? 4 : 0)
        const x = i * (BAR_W + GAP)
        const y = CHART_H - barH

        return (
          <g key={`${d.label}-${i}`}>
            {/* Bar background (track) */}
            <rect x={x} y={0} width={BAR_W} height={CHART_H} rx={4} fill="rgba(255,255,255,0.03)" />
            {/* Bar fill */}
            {d.value > 0 && (
              <rect x={x} y={y} width={BAR_W} height={barH} rx={4} fill="rgba(56,189,248,0.35)" />
            )}
            {/* Value label */}
            {d.value > 0 && (
              <text x={x + BAR_W / 2} y={y - 5} textAnchor="middle" fontSize={8} fill="#7A8FA0">
                {d.value}
              </text>
            )}
            {/* Day label */}
            <text x={x + BAR_W / 2} y={CHART_H + 14} textAnchor="middle" fontSize={9} fill="#3D5166" style={{ textTransform: 'capitalize' }}>
              {d.label}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

/* ── Donut Chart (SVG) ─────────────────────────────── */
function DonutChart({ segments }: { segments: CanalStat[] }) {
  const total = segments.reduce((s, d) => s + d.value, 0)
  const R = 40
  const CX = 60
  const CY = 60
  const CIRC = 2 * Math.PI * R
  const STROKE_W = 14

  let dashOffset = 0
  const arcs = segments.map((seg) => {
    const pct = total > 0 ? seg.value / total : 0
    const dash = pct * CIRC
    const el = (
      <circle
        key={seg.label}
        cx={CX} cy={CY} r={R}
        fill="none"
        stroke={seg.color}
        strokeWidth={STROKE_W}
        strokeDasharray={`${dash} ${CIRC - dash}`}
        strokeDashoffset={-dashOffset}
        transform={`rotate(-90 ${CX} ${CY})`}
        strokeLinecap="butt"
      />
    )
    dashOffset += dash
    return { el, ...seg, pct }
  })

  return (
    <div className="flex items-center gap-5">
      <svg viewBox="0 0 120 120" className="w-28 h-28 shrink-0" aria-label="Conversaciones por canal">
        {total === 0 ? (
          <circle cx={CX} cy={CY} r={R} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={STROKE_W} />
        ) : (
          arcs.map(a => a.el)
        )}
        <text x={CX} y={CY - 5} textAnchor="middle" fontSize={18} fontWeight="700" fill="#E8EEF4">
          {total}
        </text>
        <text x={CX} y={CY + 12} textAnchor="middle" fontSize={8} fill="#7A8FA0">
          totales
        </text>
      </svg>
      <div className="space-y-2.5 min-w-0 flex-1">
        {arcs.length === 0 ? (
          <p className="text-text-muted text-sm">Sin datos</p>
        ) : (
          arcs.map(a => (
            <div key={a.label} className="flex items-center gap-2 text-sm">
              <span className="w-2 h-2 rounded-full shrink-0" style={{ background: a.color }} />
              <span className="text-text-secondary capitalize truncate">{a.label}</span>
              <span className="ml-auto text-text-primary font-semibold tabular-nums">{a.value}</span>
              <span className="text-text-muted text-xs w-9 text-right tabular-nums">
                {Math.round(a.pct * 100)}%
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

/* ── Horizontal bar (lead estados) ────────────────── */
function HorizontalBars({ items }: { items: EstadoStat[] }) {
  const maxVal = Math.max(...items.map(i => i.value), 1)

  if (items.length === 0) {
    return <p className="text-text-muted text-sm py-2">Sin leads aún</p>
  }

  return (
    <div className="space-y-3">
      {items.map(item => {
        const pct = (item.value / maxVal) * 100
        return (
          <div key={item.label}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-text-secondary">
                {ESTADO_LABELS[item.label] ?? item.label}
              </span>
              <span className="text-sm font-semibold text-text-primary tabular-nums">{item.value}</span>
            </div>
            <div className="h-1.5 rounded-full bg-surface overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{ width: `${pct}%`, background: item.color }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}

/* ── KPI card ──────────────────────────────────────── */
function KpiCard({
  label, value, sub, icon: Icon, iconBg, iconColor,
}: {
  label: string; value: string | number; sub: string
  icon: React.ElementType; iconBg: string; iconColor: string
}) {
  return (
    <div className="rounded-xl border border-border bg-card-bg p-5 hover:border-border-light transition-colors duration-200">
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs font-medium text-text-secondary uppercase tracking-wider">{label}</p>
        <span className={`flex h-8 w-8 items-center justify-center rounded-lg ${iconBg}`}>
          <Icon className={`h-4 w-4 ${iconColor}`} />
        </span>
      </div>
      <p className="text-3xl font-bold text-text-primary leading-none">{value}</p>
      <p className="text-xs text-text-muted mt-2">{sub}</p>
    </div>
  )
}

/* ── Section card wrapper ──────────────────────────── */
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-card-bg p-5">
      <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-5">{title}</h2>
      {children}
    </div>
  )
}

/* ── Page ──────────────────────────────────────────── */
export default async function AnalyticsPage() {
  const session = await getServerSession()
  if (!session?.cliente_id) redirect('/login')

  const { kpis, mensajesPorDia, canales, estados } = await getAnalyticsData(session.cliente_id)

  const mesNombre = new Date().toLocaleDateString('es', { month: 'long' })

  const kpiCards = [
    {
      label: 'Mensajes',
      value: kpis.mensajesMes.toLocaleString(),
      sub: `Este ${mesNombre}`,
      icon: MessageSquare,
      iconBg: 'bg-accent/10',
      iconColor: 'text-accent',
    },
    {
      label: 'Leads',
      value: kpis.leadsMes,
      sub: `Captados en ${mesNombre}`,
      icon: TrendingUp,
      iconBg: 'bg-success/10',
      iconColor: 'text-success',
    },
    {
      label: 'Citas',
      value: kpis.citasMes,
      sub: `Agendadas este mes`,
      icon: Calendar,
      iconBg: 'bg-warning/10',
      iconColor: 'text-warning',
    },
    {
      label: 'Pagos',
      value: kpis.pagosVerificados,
      sub: kpis.pagosMontoMes > 0 ? `$${kpis.pagosMontoMes.toLocaleString()} verificado` : 'Verificados este mes',
      icon: CreditCard,
      iconBg: 'bg-accent-indigo/10',
      iconColor: 'text-accent-indigo',
    },
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="stagger-1">
        <div className="flex items-center gap-3">
          <BarChart2 className="h-6 w-6 text-accent" />
          <h1 className="text-3xl md:text-4xl font-bold text-text-primary tracking-tight">Analytics</h1>
        </div>
        <p className="text-text-secondary mt-1.5 text-sm">
          Actividad de tu agente IA — mes de {mesNombre}
        </p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 stagger-2">
        {kpiCards.map(card => <KpiCard key={card.label} {...card} />)}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 stagger-3">
        <Section title="Mensajes — últimos 7 días">
          <BarChart data={mensajesPorDia} />
        </Section>
        <Section title="Conversaciones por canal">
          <DonutChart segments={canales} />
        </Section>
      </div>

      {/* Leads by estado */}
      <div className="stagger-4">
        <Section title="Leads por estado">
          <HorizontalBars items={estados} />
        </Section>
      </div>
    </div>
  )
}
