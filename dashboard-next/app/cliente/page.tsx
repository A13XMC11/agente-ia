import { MessageSquare, TrendingUp, Calendar, Star } from 'lucide-react'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

interface Metrics {
  conversacionesHoy: number
  leadsNuevos: number
  citasProgramadas: number
  scorePromedio: number
}

interface Conversacion {
  id: string
  usuario_id: string
  usuario_nombre?: string
  canal: string
  estado?: string
  ultimo_mensaje?: string
  fecha_ultimo_mensaje: string
}

interface Lead {
  id: string
  nombre: string
  email: string
  score: number
  state?: string
  estado?: string
}

async function getMetrics(clienteId: string): Promise<Metrics> {
  const today = new Date().toISOString().split('T')[0]

  const [
    { count: conversacionesHoy },
    { count: leadsNuevos },
    { count: citasProgramadas },
    { data: leads },
  ] = await Promise.all([
    supabase
      .from('conversaciones')
      .select('*', { count: 'exact', head: true })
      .eq('cliente_id', clienteId)
      .gte('fecha_inicio', `${today}T00:00:00`),
    supabase
      .from('leads')
      .select('*', { count: 'exact', head: true })
      .eq('cliente_id', clienteId)
      .gte('created_at', `${today}T00:00:00`),
    supabase
      .from('citas')
      .select('*', { count: 'exact', head: true })
      .eq('cliente_id', clienteId)
      .gte('fecha', today),
    supabase.from('leads').select('score').eq('cliente_id', clienteId),
  ])

  const scorePromedio =
    leads && leads.length > 0
      ? Math.round((leads.reduce((sum, l) => sum + (l.score || 0), 0) / leads.length) * 10) / 10
      : 0

  return {
    conversacionesHoy: conversacionesHoy || 0,
    leadsNuevos: leadsNuevos || 0,
    citasProgramadas: citasProgramadas || 0,
    scorePromedio,
  }
}

async function getConversacionesRecientes(clienteId: string): Promise<Conversacion[]> {
  const { data } = await supabase
    .from('conversaciones')
    .select('id, usuario_id, usuario_nombre, canal, estado, fecha_ultimo_mensaje')
    .eq('cliente_id', clienteId)
    .order('fecha_ultimo_mensaje', { ascending: false })
    .limit(5)
  return data || []
}

async function getTopLeads(clienteId: string): Promise<Lead[]> {
  const { data } = await supabase
    .from('leads')
    .select('id, nombre, email, score, state, estado')
    .eq('cliente_id', clienteId)
    .order('score', { ascending: false })
    .limit(5)
  return data || []
}

/* ── Stat card ─────────────────────────────────── */
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
        'transition-all duration-200 group cursor-default',
        'hover:border-border-light hover:shadow-[0_0_0_1px_rgba(56,189,248,0.06),0_8px_32px_rgba(0,0,0,0.4)]',
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

/* ── Canal badge ────────────────────────────────── */
const CANAL_COLORS: Record<string, string> = {
  whatsapp: 'bg-success/10 text-success',
  instagram: 'bg-accent-indigo/10 text-accent-indigo',
  facebook: 'bg-info/10 text-info',
  email: 'bg-warning/10 text-warning',
}

/* ── Score badge ────────────────────────────────── */
function ScoreBadge({ score }: { score: number }) {
  const cls =
    score >= 8 ? 'bg-error/10 text-error' : score >= 5 ? 'bg-warning/10 text-warning' : 'bg-success/10 text-success'
  return (
    <span className={['px-2 py-0.5 rounded-md text-xs font-semibold tabular-nums', cls].join(' ')}>
      {score}
    </span>
  )
}

/* ── Page ───────────────────────────────────────── */
export default async function ClienteDashboard() {
  const session = await getServerSession()
  if (!session?.cliente_id) redirect('/login')

  const [metrics, conversacionesRecientes, topLeads] = await Promise.all([
    getMetrics(session.cliente_id),
    getConversacionesRecientes(session.cliente_id),
    getTopLeads(session.cliente_id),
  ])

  const metricCards = [
    {
      label: 'Chats hoy',
      value: metrics.conversacionesHoy,
      sub: 'Conversaciones activas',
      icon: MessageSquare,
      iconBg: 'bg-accent/10',
      iconColor: 'text-accent',
      className: 'stagger-1',
    },
    {
      label: 'Leads nuevos',
      value: metrics.leadsNuevos,
      sub: 'Captados hoy',
      icon: TrendingUp,
      iconBg: 'bg-success/10',
      iconColor: 'text-success',
      className: 'stagger-2',
    },
    {
      label: 'Citas',
      value: metrics.citasProgramadas,
      sub: 'Próximas programadas',
      icon: Calendar,
      iconBg: 'bg-warning/10',
      iconColor: 'text-warning',
      className: 'stagger-3',
    },
    {
      label: 'Score promedio',
      value: metrics.scorePromedio,
      sub: 'De todos los leads',
      icon: Star,
      iconBg: 'bg-accent-indigo/10',
      iconColor: 'text-accent-indigo',
      className: 'stagger-4',
    },
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="stagger-1">
        <h1 className="text-3xl md:text-4xl font-bold text-text-primary tracking-tight">
          Dashboard
        </h1>
        <p className="text-text-secondary mt-1.5 text-sm">
          Resumen de tu negocio y agente IA
        </p>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        {metricCards.map((card) => (
          <StatCard key={card.label} {...card} />
        ))}
      </div>

      {/* Recent conversations */}
      <div className="stagger-3">
        <h2 className="text-lg font-semibold text-text-primary mb-3">Conversaciones recientes</h2>
        <div className="rounded-xl border border-border bg-card-bg overflow-hidden">
          {conversacionesRecientes.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-14 text-center">
              <MessageSquare className="h-10 w-10 text-text-muted mb-3" />
              <p className="text-text-secondary text-sm font-medium">Sin conversaciones aún</p>
              <p className="text-text-muted text-xs mt-1 max-w-xs">
                Aparecerán aquí cuando los usuarios contacten a tu agente
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-border">
              {conversacionesRecientes.map((conv) => (
                <li
                  key={conv.id}
                  className="flex items-center justify-between gap-4 px-5 py-3.5 hover:bg-surface/40 transition-colors duration-150"
                >
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-text-primary text-sm truncate">
                      {conv.usuario_nombre || conv.usuario_id}
                    </p>
                    <p className="text-xs text-text-muted truncate mt-0.5">{conv.ultimo_mensaje}</p>
                  </div>
                  <span
                    className={[
                      'shrink-0 px-2 py-0.5 rounded-md text-xs font-medium capitalize',
                      CANAL_COLORS[conv.canal] ?? 'bg-surface text-text-secondary',
                    ].join(' ')}
                  >
                    {conv.canal}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Top leads */}
      <div className="stagger-4">
        <h2 className="text-lg font-semibold text-text-primary mb-3">Top Leads</h2>
        <div className="rounded-xl border border-border bg-card-bg overflow-hidden">
          {topLeads.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-14 text-center">
              <TrendingUp className="h-10 w-10 text-text-muted mb-3" />
              <p className="text-text-secondary text-sm font-medium">Sin leads aún</p>
            </div>
          ) : (
            <ul className="divide-y divide-border">
              {topLeads.map((lead) => (
                <li
                  key={lead.id}
                  className="flex items-center justify-between gap-4 px-5 py-3.5 hover:bg-surface/40 transition-colors duration-150"
                >
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-text-primary text-sm">{lead.nombre}</p>
                    <p className="text-xs text-text-muted mt-0.5 truncate">{lead.email}</p>
                  </div>
                  <ScoreBadge score={lead.score} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
