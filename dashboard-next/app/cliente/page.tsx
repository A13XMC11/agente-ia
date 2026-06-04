import {
  MessageSquare, TrendingUp, Calendar, Star,
  Clock, ArrowUpRight, Bot, Zap,
} from 'lucide-react'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import Link from 'next/link'

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
    supabase.from('conversaciones').select('*', { count: 'exact', head: true }).eq('cliente_id', clienteId).gte('fecha_inicio', `${today}T00:00:00`),
    supabase.from('leads').select('*', { count: 'exact', head: true }).eq('cliente_id', clienteId).gte('created_at', `${today}T00:00:00`),
    supabase.from('citas').select('*', { count: 'exact', head: true }).eq('cliente_id', clienteId).gte('fecha', today),
    supabase.from('leads').select('score').eq('cliente_id', clienteId),
  ])
  const scorePromedio =
    leads && leads.length > 0
      ? Math.round((leads.reduce((s, l) => s + (l.score || 0), 0) / leads.length) * 10) / 10
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
    .select('id, usuario_id, usuario_nombre, canal, estado, fecha_ultimo_mensaje')
    .eq('cliente_id', clienteId)
    .order('fecha_ultimo_mensaje', { ascending: false })
    .limit(6)
  if (!convs || convs.length === 0) return []
  const telefonos = convs.map((c) => c.usuario_id).filter(Boolean)
  const { data: leadsData } = await supabase
    .from('leads').select('telefono, nombre, score').eq('cliente_id', clienteId).in('telefono', telefonos)
  const leadsByPhone = new Map(leadsData?.map((l) => [l.telefono, l]) ?? [])
  return convs.map((conv) => {
    const lead = leadsByPhone.get(conv.usuario_id)
    return { ...conv, lead_nombre: lead?.nombre, lead_score: lead?.score }
  })
}

async function getTopLeads(clienteId: string): Promise<Lead[]> {
  const { data } = await supabase
    .from('leads').select('id, nombre, email, score, telefono, estado').eq('cliente_id', clienteId).order('score', { ascending: false }).limit(5)
  return data || []
}

/* ── Helpers ────────────────────────────────────── */

function getInitials(name: string): string {
  return name.split(' ').slice(0, 2).map((n) => n[0]?.toUpperCase() ?? '').join('')
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'ahora'
  if (mins < 60) return `${mins}m`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h`
  const days = Math.floor(hrs / 24)
  if (days === 1) return 'ayer'
  if (days < 7) return `${days}d`
  return new Date(dateStr).toLocaleDateString('es-EC', { day: 'numeric', month: 'short' })
}

const AVATAR_PALETTE = [
  { bg: 'rgba(56,189,248,0.12)', color: '#38BDF8', border: 'rgba(56,189,248,0.22)' },
  { bg: 'rgba(34,211,160,0.12)', color: '#22D3A0', border: 'rgba(34,211,160,0.22)' },
  { bg: 'rgba(129,140,248,0.12)', color: '#818CF8', border: 'rgba(129,140,248,0.22)' },
  { bg: 'rgba(251,191,36,0.12)', color: '#FBBF24', border: 'rgba(251,191,36,0.22)' },
  { bg: 'rgba(248,113,113,0.12)', color: '#F87171', border: 'rgba(248,113,113,0.22)' },
]

function pickPalette(seed: string) {
  let h = 0
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) & 0xffffffff
  return AVATAR_PALETTE[Math.abs(h) % AVATAR_PALETTE.length]
}

/* ── UI primitives ──────────────────────────────── */

function Avatar({ name, seed, size = 'md' }: { name: string; seed: string; size?: 'sm' | 'md' }) {
  const { bg, color, border } = pickPalette(seed)
  const sz = size === 'sm' ? 'h-7 w-7 text-[10px]' : 'h-9 w-9 text-xs'
  return (
    <div
      className={[sz, 'rounded-full flex items-center justify-center font-semibold shrink-0'].join(' ')}
      style={{ background: bg, color, border: `1px solid ${border}` }}
    >
      {getInitials(name)}
    </div>
  )
}

const CANAL_META: Record<string, { label: string; color: string; bg: string; border: string }> = {
  whatsapp: { label: 'WA', color: '#22D3A0', bg: 'rgba(34,211,160,0.10)', border: 'rgba(34,211,160,0.20)' },
  instagram: { label: 'IG', color: '#818CF8', bg: 'rgba(129,140,248,0.10)', border: 'rgba(129,140,248,0.20)' },
  facebook: { label: 'FB', color: '#60A5FA', bg: 'rgba(96,165,250,0.10)', border: 'rgba(96,165,250,0.20)' },
  email: { label: 'EM', color: '#FBBF24', bg: 'rgba(251,191,36,0.10)', border: 'rgba(251,191,36,0.20)' },
}

function CanalBadge({ canal }: { canal: string }) {
  const meta = CANAL_META[canal] ?? { label: canal.slice(0, 2).toUpperCase(), color: 'var(--text-muted)', bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.08)' }
  return (
    <span
      className="px-2 py-0.5 rounded-md text-[10px] font-bold tabular-nums shrink-0"
      style={{ color: meta.color, background: meta.bg, border: `1px solid ${meta.border}` }}
    >
      {meta.label}
    </span>
  )
}

function ScorePill({ score }: { score: number }) {
  const color = score >= 8 ? '#F87171' : score >= 5 ? '#FBBF24' : '#22D3A0'
  const bg = score >= 8 ? 'rgba(248,113,113,0.10)' : score >= 5 ? 'rgba(251,191,36,0.10)' : 'rgba(34,211,160,0.10)'
  const border = score >= 8 ? 'rgba(248,113,113,0.20)' : score >= 5 ? 'rgba(251,191,36,0.20)' : 'rgba(34,211,160,0.20)'
  return (
    <span
      className="px-2.5 py-1 rounded-lg text-xs font-bold tabular-nums shrink-0"
      style={{ color, background: bg, border: `1px solid ${border}` }}
    >
      {score}
    </span>
  )
}

/* ── Stat Card ──────────────────────────────────── */
const CARD_ACCENTS = [
  { from: 'rgba(56,189,248,0.07)', glow: 'rgba(56,189,248,0.12)', icon: 'rgba(56,189,248,0.15)', iconColor: '#38BDF8' },
  { from: 'rgba(34,211,160,0.07)', glow: 'rgba(34,211,160,0.12)', icon: 'rgba(34,211,160,0.15)', iconColor: '#22D3A0' },
  { from: 'rgba(251,191,36,0.07)', glow: 'rgba(251,191,36,0.12)', icon: 'rgba(251,191,36,0.15)', iconColor: '#FBBF24' },
  { from: 'rgba(129,140,248,0.07)', glow: 'rgba(129,140,248,0.12)', icon: 'rgba(129,140,248,0.15)', iconColor: '#818CF8' },
]

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  accentIdx,
  delay,
}: {
  label: string
  value: string | number
  sub: string
  icon: React.ElementType
  accentIdx: number
  delay: number
}) {
  const accent = CARD_ACCENTS[accentIdx]
  return (
    <div
      className="card-hover card-accent-hover relative min-w-0 overflow-hidden rounded-2xl p-4 sm:p-5 group"
      style={{
        background: 'rgba(9,21,33,0.6)',
        border: '1px solid rgba(255,255,255,0.06)',
        animation: `fadeInUp 340ms cubic-bezier(0.23,1,0.32,1) ${delay}ms both`,
      }}
    >
      {/* Hover gradient glow */}
      <div
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
        style={{ background: `radial-gradient(ellipse 80% 80% at 50% 0%, ${accent.from}, transparent)` }}
      />
      <div className="relative">
        <div className="flex items-start justify-between mb-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-white/35 select-none">
            {label}
          </p>
          <span
            className="flex h-7 w-7 items-center justify-center rounded-lg shrink-0"
            style={{ background: accent.icon, border: `1px solid ${accent.glow}` }}
          >
            <Icon className="h-3.5 w-3.5" style={{ color: accent.iconColor }} strokeWidth={2} />
          </span>
        </div>
        <p
          className="text-3xl font-bold leading-none tabular-nums sm:text-4xl"
          style={{ color: 'rgba(255,255,255,0.92)', animation: `count-in 500ms cubic-bezier(0.23,1,0.32,1) ${delay + 80}ms both` }}
        >
          {value}
        </p>
        <p className="text-[11px] mt-2.5 font-medium" style={{ color: 'rgba(255,255,255,0.28)' }}>
          {sub}
        </p>
      </div>
    </div>
  )
}

/* ── Section header ─────────────────────────────── */
function SectionHeader({
  title,
  sub,
  href,
  linkLabel,
}: {
  title: string
  sub?: string
  href?: string
  linkLabel?: string
}) {
  return (
    <div className="flex items-start justify-between mb-4">
      <div>
        <h2 className="text-sm font-semibold text-white/75 tracking-tight">{title}</h2>
        {sub && <p className="text-[11px] text-white/28 mt-0.5">{sub}</p>}
      </div>
      {href && linkLabel && (
        <Link
          href={href}
          className="flex items-center gap-1 text-[11px] font-medium text-accent/60 hover:text-accent transition-colors duration-150 cursor-pointer shrink-0"
        >
          {linkLabel}
          <ArrowUpRight className="h-3 w-3" strokeWidth={2.5} />
        </Link>
      )}
    </div>
  )
}

/* ── Empty state ────────────────────────────────── */
function EmptyState({ icon: Icon, text }: { icon: React.ElementType; text: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-4 py-12 text-center sm:py-14">
      <div
        className="h-11 w-11 rounded-xl flex items-center justify-center"
        style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
      >
        <Icon className="h-5 w-5 text-white/20" strokeWidth={1.5} />
      </div>
      <p className="text-white/28 text-xs">{text}</p>
    </div>
  )
}

/* ── Agent status bar ───────────────────────────── */
function AgentStatus() {
  return (
    <div
      className="stagger-5 flex min-w-0 flex-col gap-3 rounded-2xl p-4 min-[430px]:flex-row min-[430px]:items-center min-[430px]:gap-4"
      style={{
        background: 'rgba(34,211,160,0.05)',
        border: '1px solid rgba(34,211,160,0.12)',
      }}
    >
      <div
        className="h-9 w-9 rounded-xl flex items-center justify-center shrink-0"
        style={{ background: 'rgba(34,211,160,0.10)', border: '1px solid rgba(34,211,160,0.20)' }}
      >
        <Bot className="h-4 w-4 text-success" strokeWidth={2} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-white/80 leading-none">Agente IA activo</p>
        <p className="text-[11px] text-white/30 mt-0.5">Respondiendo en todos los canales</p>
      </div>
      <div className="flex shrink-0 items-center gap-1.5">
        <span className="relative flex h-2 w-2">
          <span
            className="absolute inline-flex h-full w-full rounded-full bg-success opacity-75"
            style={{ animation: 'ping-slow 2.4s cubic-bezier(0,0,0.2,1) infinite' }}
          />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
        </span>
        <span className="text-[11px] font-semibold text-success">Online</span>
      </div>
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

  const today = new Date().toLocaleDateString('es-EC', {
    weekday: 'long', day: 'numeric', month: 'long',
  })

  return (
    <div className="min-w-0 space-y-7">
      {/* Page header */}
      <div className="stagger-1 flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-white/30 mb-1.5 capitalize">
            {today}
          </p>
          <h1 className="text-2xl font-bold text-white/90 tracking-tight leading-none">
            Panel principal
          </h1>
          <p className="text-white/35 mt-1.5 text-sm">
            Resumen de tu agente y negocio
          </p>
        </div>
        <div
          className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg shrink-0"
          style={{ background: 'rgba(56,189,248,0.08)', border: '1px solid rgba(56,189,248,0.16)' }}
        >
          <Zap className="h-3.5 w-3.5 text-accent" strokeWidth={2} />
          <span className="text-xs font-semibold text-accent">IA activa</span>
        </div>
      </div>

      {/* Metric cards — 2×2 on mobile, 4-col on desktop */}
      <div className="grid grid-cols-1 gap-3 min-[430px]:grid-cols-2 md:gap-4 lg:grid-cols-4">
        <StatCard label="Chats hoy"       value={metrics.conversacionesHoy}  sub="Conversaciones activas"  icon={MessageSquare} accentIdx={0} delay={60} />
        <StatCard label="Leads nuevos"    value={metrics.leadsNuevos}         sub="Captados hoy"            icon={TrendingUp}    accentIdx={1} delay={120} />
        <StatCard label="Citas"           value={metrics.citasProgramadas}    sub="Próximas programadas"    icon={Calendar}      accentIdx={2} delay={180} />
        <StatCard label="Score promedio"  value={metrics.scorePromedio}       sub="Promedio de todos los leads" icon={Star}      accentIdx={3} delay={240} />
      </div>

      {/* Agent online status */}
      <AgentStatus />

      {/* Two-column feed */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent conversations */}
        <div className="stagger-6">
          <SectionHeader
            title="Conversaciones recientes"
            sub="Últimas interacciones con el agente"
            href="/cliente/conversaciones"
            linkLabel="Ver todas"
          />
          <div
            className="min-w-0 overflow-hidden rounded-2xl"
            style={{ border: '1px solid rgba(255,255,255,0.05)', background: 'rgba(9,21,33,0.4)' }}
          >
            {conversacionesRecientes.length === 0 ? (
              <EmptyState icon={MessageSquare} text="Aún no hay conversaciones" />
            ) : (
              <ul className="divide-y" style={{ '--tw-divide-opacity': 1 } as React.CSSProperties}>
                {conversacionesRecientes.map((conv) => {
                  const displayName = conv.lead_nombre || conv.usuario_nombre
                  const name = displayName || conv.usuario_id.slice(-8)
                  return (
                    <li
                      key={conv.id}
                      className="flex min-w-0 items-center gap-3 px-3 py-3 transition-colors duration-150 hover:bg-white/[0.02] sm:px-4"
                      style={{ borderColor: 'rgba(255,255,255,0.04)' }}
                    >
                      <Avatar name={displayName || conv.usuario_id} seed={conv.usuario_id} />
                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-white/78 text-sm truncate leading-none">{name}</p>
                        {conv.lead_score !== undefined && (
                          <p className="text-[10px] text-white/28 mt-0.5 font-mono">score {conv.lead_score}/10</p>
                        )}
                      </div>
                      <div className="flex shrink-0 flex-col items-end gap-1.5">
                        <CanalBadge canal={conv.canal} />
                        <span className="flex items-center gap-1 text-[10px] text-white/22">
                          <Clock className="h-2.5 w-2.5" strokeWidth={1.75} />
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
        <div className="stagger-7">
          <SectionHeader
            title="Top Leads"
            sub="Ordenados por score de calidad"
            href="/cliente/leads"
            linkLabel="Ver todos"
          />
          <div
            className="min-w-0 overflow-hidden rounded-2xl"
            style={{ border: '1px solid rgba(255,255,255,0.05)', background: 'rgba(9,21,33,0.4)' }}
          >
            {topLeads.length === 0 ? (
              <EmptyState icon={TrendingUp} text="Aún no hay leads calificados" />
            ) : (
              <ul className="divide-y">
                {topLeads.map((lead, i) => (
                  <li
                    key={lead.id}
                    className="flex min-w-0 items-center gap-3 px-3 py-3 transition-colors duration-150 hover:bg-white/[0.02] sm:px-4"
                    style={{ borderColor: 'rgba(255,255,255,0.04)' }}
                  >
                    <span
                      className="w-5 text-center text-[11px] font-bold shrink-0 select-none"
                      style={{ color: i < 3 ? 'rgba(56,189,248,0.5)' : 'rgba(255,255,255,0.15)' }}
                    >
                      {i + 1}
                    </span>
                    <Avatar name={lead.nombre || 'Lead'} seed={lead.id} />
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-white/78 text-sm truncate leading-none">{lead.nombre}</p>
                      <p className="text-[11px] text-white/28 truncate mt-0.5">
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
