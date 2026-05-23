import { MessageSquare, TrendingUp, Calendar, Star, ArrowUpRight, Clock } from 'lucide-react'
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
  lead_nombre?: string
  lead_score?: number
}

interface Lead {
  id: string
  nombre: string
  email: string
  score: number
  telefono?: string
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
  const { data: convs } = await supabase
    .from('conversaciones')
    .select('id, usuario_id, usuario_nombre, canal, estado, ultimo_mensaje, fecha_ultimo_mensaje')
    .eq('cliente_id', clienteId)
    .order('fecha_ultimo_mensaje', { ascending: false })
    .limit(5)

  if (!convs || convs.length === 0) return []

  const telefonos = convs.map((c) => c.usuario_id).filter(Boolean)

  const { data: leadsData } = await supabase
    .from('leads')
    .select('telefono, nombre, score')
    .eq('cliente_id', clienteId)
    .in('telefono', telefonos)

  const leadsByPhone = new Map(leadsData?.map((l) => [l.telefono, l]) ?? [])

  return convs.map((conv) => {
    const lead = leadsByPhone.get(conv.usuario_id)
    return {
      ...conv,
      lead_nombre: lead?.nombre,
      lead_score: lead?.score,
    }
  })
}

async function getTopLeads(clienteId: string): Promise<Lead[]> {
  const { data } = await supabase
    .from('leads')
    .select('id, nombre, email, score, telefono, estado')
    .eq('cliente_id', clienteId)
    .order('score', { ascending: false })
    .limit(5)
  return data || []
}

/* ── Helpers ────────────────────────────────────── */

function formatPhone(phone: string): string {
  const digits = phone.replace(/\D/g, '')
  if (digits.startsWith('593') && digits.length === 12) {
    return `+593 ${digits.slice(3, 5)} ${digits.slice(5, 8)} ${digits.slice(8)}`
  }
  if (digits.length >= 10) {
    return `+${digits.slice(0, digits.length - 10)} ${digits.slice(-10, -7)} ${digits.slice(-7, -4)} ${digits.slice(-4)}`
  }
  return `+${digits}`
}

function getInitials(name: string): string {
  return name
    .split(' ')
    .slice(0, 2)
    .map((n) => n[0]?.toUpperCase() ?? '')
    .join('')
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'ahora'
  if (mins < 60) return `hace ${mins}m`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `hace ${hrs}h`
  const days = Math.floor(hrs / 24)
  if (days === 1) return 'ayer'
  if (days < 7) return `hace ${days}d`
  return new Date(dateStr).toLocaleDateString('es-EC', { day: 'numeric', month: 'short' })
}

const AVATAR_COLORS = [
  ['bg-sky-500/20 text-sky-400', 'border-sky-500/30'],
  ['bg-emerald-500/20 text-emerald-400', 'border-emerald-500/30'],
  ['bg-violet-500/20 text-violet-400', 'border-violet-500/30'],
  ['bg-amber-500/20 text-amber-400', 'border-amber-500/30'],
  ['bg-rose-500/20 text-rose-400', 'border-rose-500/30'],
]

function pickColor(seed: string) {
  let h = 0
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) & 0xffffffff
  return AVATAR_COLORS[Math.abs(h) % AVATAR_COLORS.length]
}

/* ── Avatar ─────────────────────────────────────── */
function Avatar({ name, seed, size = 'md' }: { name: string; seed: string; size?: 'sm' | 'md' }) {
  const [bg, border] = pickColor(seed)
  const sz = size === 'sm' ? 'h-8 w-8 text-xs' : 'h-9 w-9 text-sm'
  return (
    <div
      className={[
        sz,
        'rounded-full flex items-center justify-center font-semibold shrink-0 border',
        bg,
        border,
      ].join(' ')}
    >
      {getInitials(name)}
    </div>
  )
}

/* ── Stat card ─────────────────────────────────── */
function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  accent,
  className,
}: {
  label: string
  value: string | number
  sub: string
  icon: React.ElementType
  accent: string
  className?: string
}) {
  return (
    <div
      className={[
        'relative rounded-2xl border border-white/5 bg-white/3 p-5 overflow-hidden',
        'transition-all duration-300 cursor-default group',
        'hover:border-white/10 hover:bg-white/5',
        className ?? '',
      ].join(' ')}
    >
      <div
        className={['absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300', accent].join(
          ' '
        )}
      />
      <div className="relative">
        <div className="flex items-start justify-between mb-4">
          <p className="text-[11px] font-semibold text-white/40 uppercase tracking-widest">{label}</p>
          <span
            className={[
              'flex h-7 w-7 items-center justify-center rounded-lg',
              'bg-white/5 border border-white/10',
            ].join(' ')}
          >
            <Icon className="h-3.5 w-3.5 text-white/60" />
          </span>
        </div>
        <p className="text-4xl font-bold text-white/90 leading-none tabular-nums">{value}</p>
        <p className="text-[11px] text-white/30 mt-2.5 font-medium">{sub}</p>
      </div>
    </div>
  )
}

/* ── Canal badge ────────────────────────────────── */
const CANAL_META: Record<string, { label: string; cls: string }> = {
  whatsapp: { label: 'WhatsApp', cls: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' },
  instagram: { label: 'Instagram', cls: 'bg-violet-500/10 text-violet-400 border border-violet-500/20' },
  facebook: { label: 'Facebook', cls: 'bg-sky-500/10 text-sky-400 border border-sky-500/20' },
  email: { label: 'Email', cls: 'bg-amber-500/10 text-amber-400 border border-amber-500/20' },
}

/* ── Score pill ─────────────────────────────────── */
function ScorePill({ score }: { score: number }) {
  const cls =
    score >= 8
      ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
      : score >= 5
        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
        : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
  return (
    <span className={['px-2.5 py-1 rounded-lg text-xs font-bold tabular-nums', cls].join(' ')}>
      {score}
    </span>
  )
}

/* ── Section header ─────────────────────────────── */
function SectionHeader({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-base font-semibold text-white/80">{title}</h2>
      {sub && <p className="text-[11px] text-white/30 mt-0.5">{sub}</p>}
    </div>
  )
}

/* ── Empty state ────────────────────────────────── */
function EmptyState({ icon: Icon, text }: { icon: React.ElementType; text: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="h-12 w-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mb-3">
        <Icon className="h-5 w-5 text-white/20" />
      </div>
      <p className="text-white/30 text-sm">{text}</p>
    </div>
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
      accent: 'bg-gradient-to-br from-sky-500/5 to-transparent',
      className: 'stagger-1',
    },
    {
      label: 'Leads nuevos',
      value: metrics.leadsNuevos,
      sub: 'Captados hoy',
      icon: TrendingUp,
      accent: 'bg-gradient-to-br from-emerald-500/5 to-transparent',
      className: 'stagger-2',
    },
    {
      label: 'Citas',
      value: metrics.citasProgramadas,
      sub: 'Próximas programadas',
      icon: Calendar,
      accent: 'bg-gradient-to-br from-amber-500/5 to-transparent',
      className: 'stagger-3',
    },
    {
      label: 'Score promedio',
      value: metrics.scorePromedio,
      sub: 'Sobre todos los leads',
      icon: Star,
      accent: 'bg-gradient-to-br from-violet-500/5 to-transparent',
      className: 'stagger-4',
    },
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="stagger-1">
        <h1 className="text-3xl font-bold text-white/90 tracking-tight">Dashboard</h1>
        <p className="text-white/30 mt-1 text-sm font-medium">
          Resumen de tu negocio y agente IA
        </p>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        {metricCards.map((card) => (
          <StatCard key={card.label} {...card} />
        ))}
      </div>

      {/* Two columns on desktop */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent conversations */}
        <div className="stagger-3">
          <SectionHeader title="Conversaciones recientes" sub="Últimas interacciones con el agente" />
          <div className="rounded-2xl border border-white/5 bg-white/2 overflow-hidden">
            {conversacionesRecientes.length === 0 ? (
              <EmptyState icon={MessageSquare} text="Sin conversaciones aún" />
            ) : (
              <ul className="divide-y divide-white/5">
                {conversacionesRecientes.map((conv, i) => {
                  const displayName = conv.lead_nombre || conv.usuario_nombre
                  const fallback = formatPhone(conv.usuario_id)
                  const name = displayName || fallback
                  const avatarSeed = conv.usuario_id
                  const canalMeta = CANAL_META[conv.canal] ?? {
                    label: conv.canal,
                    cls: 'bg-white/5 text-white/40 border border-white/10',
                  }

                  return (
                    <li
                      key={conv.id}
                      className="flex items-center gap-3.5 px-4 py-3.5 hover:bg-white/3 transition-colors duration-150"
                    >
                      <Avatar name={displayName || fallback} seed={avatarSeed} />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-semibold text-white/80 text-sm truncate">{name}</p>
                          {conv.lead_score !== undefined && (
                            <span className="shrink-0 text-[10px] font-bold text-white/30">
                              {conv.lead_score}/10
                            </span>
                          )}
                        </div>
                        {!displayName && (
                          <p className="text-[10px] text-white/25 mt-0.5 font-mono">{conv.usuario_id}</p>
                        )}
                        {conv.ultimo_mensaje && (
                          <p className="text-xs text-white/30 truncate mt-0.5 max-w-50">
                            {conv.ultimo_mensaje}
                          </p>
                        )}
                      </div>
                      <div className="shrink-0 flex flex-col items-end gap-1.5">
                        <span className={['px-2 py-0.5 rounded-md text-[10px] font-semibold', canalMeta.cls].join(' ')}>
                          {canalMeta.label}
                        </span>
                        <span className="flex items-center gap-1 text-[10px] text-white/25">
                          <Clock className="h-2.5 w-2.5" />
                          {timeAgo(conv.fecha_ultimo_mensaje)}
                        </span>
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        </div>

        {/* Top leads */}
        <div className="stagger-4">
          <SectionHeader title="Top Leads" sub="Ordenados por score de calidad" />
          <div className="rounded-2xl border border-white/5 bg-white/2 overflow-hidden">
            {topLeads.length === 0 ? (
              <EmptyState icon={TrendingUp} text="Sin leads aún" />
            ) : (
              <ul className="divide-y divide-white/5">
                {topLeads.map((lead, i) => (
                  <li
                    key={lead.id}
                    className="flex items-center gap-3.5 px-4 py-3.5 hover:bg-white/3 transition-colors duration-150"
                  >
                    <div className="shrink-0 w-5 text-center">
                      <span className="text-xs font-bold text-white/20">#{i + 1}</span>
                    </div>
                    <Avatar name={lead.nombre || 'Lead'} seed={lead.id} />
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-white/80 text-sm truncate">{lead.nombre}</p>
                      <p className="text-xs text-white/30 truncate mt-0.5">
                        {lead.email || lead.telefono || '—'}
                      </p>
                    </div>
                    <ScorePill score={lead.score} />
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
