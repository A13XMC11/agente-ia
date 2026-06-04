'use client'

import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { TrendingUp, Zap, X, Search, Phone, MessageCircle, Clock, Users } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { formatTimestamp } from '@/lib/date-format'

type LeadState = 'curioso' | 'prospecto' | 'interesado' | 'caliente' | 'urgente'

interface SignalEvent {
  id: string
  score_before: number
  score_after: number
  delta: number
  signal_type: string
  signal_keywords: string[]
  message_excerpt: string
  created_at: string
}

interface Lead {
  id: string
  name?: string
  nombre?: string
  email?: string
  phone?: string
  telefono?: string
  score: number
  state?: LeadState
  estado?: LeadState
  urgency: number
  budget: number | null
  decision_power: number
  interaction_count: number
  last_interaction?: string
  created_at: string
}

/* ── Config ─────────────────────────────────────── */
const STATE_META: Record<LeadState, { label: string; color: string; bg: string; border: string; dot: string }> = {
  urgente:    { label: 'URGENTE',    color: '#F87171', bg: 'rgba(248,113,113,0.12)', border: 'rgba(248,113,113,0.22)', dot: '#F87171' },
  caliente:   { label: 'CALIENTE',   color: '#FB923C', bg: 'rgba(251,146,60,0.10)',  border: 'rgba(251,146,60,0.20)',  dot: '#FB923C' },
  interesado: { label: 'INTERESADO', color: '#FBBF24', bg: 'rgba(251,191,36,0.10)',  border: 'rgba(251,191,36,0.20)',  dot: '#FBBF24' },
  prospecto:  { label: 'PROSPECTO',  color: '#60A5FA', bg: 'rgba(96,165,250,0.10)',  border: 'rgba(96,165,250,0.20)',  dot: '#60A5FA' },
  curioso:    { label: 'CURIOSO',    color: 'rgba(255,255,255,0.35)', bg: 'rgba(255,255,255,0.06)', border: 'rgba(255,255,255,0.10)', dot: 'rgba(255,255,255,0.30)' },
}

const STATE_ORDER: LeadState[] = ['urgente', 'caliente', 'interesado', 'prospecto', 'curioso']

const AVATAR_PALETTE = [
  { bg: 'rgba(56,189,248,0.12)',  color: '#38BDF8', border: 'rgba(56,189,248,0.22)' },
  { bg: 'rgba(34,211,160,0.12)',  color: '#22D3A0', border: 'rgba(34,211,160,0.22)' },
  { bg: 'rgba(129,140,248,0.12)', color: '#818CF8', border: 'rgba(129,140,248,0.22)' },
  { bg: 'rgba(251,191,36,0.12)',  color: '#FBBF24', border: 'rgba(251,191,36,0.22)' },
  { bg: 'rgba(248,113,113,0.12)', color: '#F87171', border: 'rgba(248,113,113,0.22)' },
]

function pickPalette(seed: string) {
  let h = 0
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) & 0xffffffff
  return AVATAR_PALETTE[Math.abs(h) % AVATAR_PALETTE.length]
}

/* ── Helpers ────────────────────────────────────── */
function getDisplayName(lead: Lead): string {
  const n = lead.name || lead.nombre
  return n?.trim() || 'Sin nombre'
}

function getInitials(lead: Lead): string {
  const n = lead.name || lead.nombre
  if (n?.trim()) return n.trim().split(' ').slice(0, 2).map((w: string) => w[0]).join('').toUpperCase()
  return '?'
}

function getWhatsAppLink(phone: string | undefined): string | null {
  if (!phone) return null
  const digits = phone.replace(/\D/g, '')
  return digits ? `https://wa.me/${digits}` : null
}

/* ── Score bar ──────────────────────────────────── */
function ScoreBar({ score }: { score: number }) {
  const pct = (score / 10) * 100
  const color =
    score >= 9 ? '#F87171' :
    score >= 7 ? '#FB923C' :
    score >= 5 ? '#FBBF24' :
    score >= 3 ? '#60A5FA' : 'rgba(255,255,255,0.20)'
  const glow =
    score >= 9 ? 'rgba(248,113,113,0.4)' :
    score >= 7 ? 'rgba(251,146,60,0.4)' :
    score >= 5 ? 'rgba(251,191,36,0.3)' : 'transparent'

  return (
    <div className="flex items-center gap-2.5 min-w-0">
      <div
        className="flex-1 h-1.5 rounded-full overflow-hidden"
        style={{ background: 'rgba(255,255,255,0.06)' }}
      >
        <div
          className="h-full rounded-full score-bar-fill"
          style={{
            width: `${pct}%`,
            background: color,
            boxShadow: `0 0 8px ${glow}`,
          }}
        />
      </div>
      <span className="text-xs font-bold tabular-nums w-8 text-right shrink-0" style={{ color }}>
        {score}/10
      </span>
    </div>
  )
}

/* ── State badge ────────────────────────────────── */
function StateBadge({ state }: { state: LeadState | undefined }) {
  const m = STATE_META[state ?? 'curioso']
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-semibold"
      style={{ color: m.color, background: m.bg, border: `1px solid ${m.border}` }}
    >
      <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ background: m.dot }} />
      {m.label}
    </span>
  )
}

/* ── Lead avatar ────────────────────────────────── */
function LeadAvatar({ lead, size = 'md' }: { lead: Lead; size?: 'sm' | 'md' }) {
  const { bg, color, border } = pickPalette(lead.id)
  const sz = size === 'sm' ? 'h-8 w-8 text-[11px]' : 'h-9 w-9 text-xs'
  return (
    <div
      className={[sz, 'rounded-full flex items-center justify-center font-bold shrink-0 select-none'].join(' ')}
      style={{ background: bg, color, border: `1px solid ${border}` }}
    >
      {getInitials(lead)}
    </div>
  )
}

/* ── Stat mini-card ─────────────────────────────── */
function StatMini({ icon: Icon, label, value, sub }: {
  icon: React.ElementType
  label: string
  value: string | number
  sub?: string
}) {
  return (
    <div
      className="rounded-xl px-4 py-3.5 flex items-center gap-3"
      style={{ border: '1px solid rgba(255,255,255,0.06)', background: 'rgba(9,21,33,0.6)' }}
    >
      <div
        className="h-8 w-8 rounded-lg flex items-center justify-center shrink-0"
        style={{ background: 'rgba(255,255,255,0.05)' }}
      >
        <Icon className="h-4 w-4 text-white/35" strokeWidth={1.75} />
      </div>
      <div className="min-w-0">
        <p className="text-[10px] text-white/30 font-medium">{label}</p>
        <p className="text-lg font-bold text-white/85 tabular-nums leading-tight">{value}</p>
        {sub && <p className="text-[10px] text-white/25">{sub}</p>}
      </div>
    </div>
  )
}

/* ── Skeleton rows ──────────────────────────────── */
function SkeletonTableRow() {
  return (
    <div className="flex items-center gap-4 px-5 py-4">
      <div className="skeleton h-9 w-9 rounded-full shrink-0" />
      <div className="flex-1 space-y-2">
        <div className="skeleton h-3 w-28 rounded" />
        <div className="skeleton h-2.5 w-20 rounded" />
      </div>
      <div className="skeleton h-4 w-16 rounded" />
    </div>
  )
}

/* ── Page ───────────────────────────────────────── */
export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterState, setFilterState] = useState<LeadState | 'todos'>('todos')
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null)
  const [signals, setSignals] = useState<SignalEvent[]>([])
  const [signalsLoading, setSignalsLoading] = useState(false)

  const loadLeads = useCallback(async () => {
    try {
      const res = await fetch('/api/cliente/leads')
      if (!res.ok) throw new Error('Failed')
      const json = await res.json()
      setLeads(json.data || [])
    } catch {
      // silent — empty state shown
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadLeads()
  }, [loadLeads])

  async function loadSignals(leadId: string) {
    setSignalsLoading(true)
    try {
      const res = await fetch(`/api/cliente/leads/${leadId}/signals`)
      if (!res.ok) throw new Error('Failed')
      const json = await res.json()
      setSignals(json.data || [])
    } catch {
      setSignals([])
    } finally {
      setSignalsLoading(false)
    }
  }

  const stats = useMemo(() => {
    const total = leads.length
    const urgentes = leads.filter((l) => {
      const s = l.state || l.estado
      return s === 'urgente' || s === 'caliente'
    }).length
    const avgScore = total > 0 ? (leads.reduce((s, l) => s + l.score, 0) / total).toFixed(1) : '0'
    const withInteraction = leads.filter((l) => l.interaction_count > 0).length
    return { total, urgentes, avgScore, withInteraction }
  }, [leads])

  const stateCounts = useMemo(() =>
    STATE_ORDER.reduce<Record<string, number>>((acc, s) => {
      acc[s] = leads.filter((l) => (l.state || l.estado) === s).length
      return acc
    }, {}),
  [leads])

  const filtrados = useMemo(() => {
    let result = leads
    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(
        (l) =>
          getDisplayName(l).toLowerCase().includes(q) ||
          (l.email || '').toLowerCase().includes(q) ||
          (l.phone || l.telefono || '').includes(q),
      )
    }
    if (filterState !== 'todos') {
      result = result.filter((l) => (l.state || l.estado) === filterState)
    }
    return result
  }, [search, filterState, leads])

  function openSignals(lead: Lead) {
    setSelectedLead(lead)
    loadSignals(lead.id)
  }

  function closeSignals() {
    setSelectedLead(null)
    setSignals([])
  }

  return (
    <div className="min-w-0 space-y-5">
      {/* Header */}
      <div className="stagger-1">
        <h1 className="text-2xl font-bold text-white/88 tracking-tight">Leads</h1>
        <p className="text-white/35 mt-1 text-sm">
          Calificación automática con inteligencia artificial
        </p>
      </div>

      {/* Stats row */}
      {!loading && leads.length > 0 && (
        <div className="stagger-2 grid grid-cols-1 gap-3 min-[430px]:grid-cols-2 lg:grid-cols-4">
          <StatMini icon={Users}         label="Total leads"     value={stats.total} />
          <StatMini icon={Zap}           label="Alta prioridad"  value={stats.urgentes}        sub="urgente + caliente" />
          <StatMini icon={TrendingUp}    label="Score promedio"  value={stats.avgScore}         sub="sobre 10" />
          <StatMini icon={MessageCircle} label="Con interacción" value={stats.withInteraction} />
        </div>
      )}

      {/* Filters row */}
      <div className="stagger-3 flex min-w-0 flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <div className="relative w-full min-w-0 flex-1 sm:min-w-44">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-white/25 pointer-events-none" strokeWidth={1.75} />
          <Input
            placeholder="Buscar por nombre o teléfono..."
            className="pl-10"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex w-full gap-1.5 overflow-x-auto pb-1 sm:w-auto sm:flex-wrap sm:overflow-visible sm:pb-0">
          {/* All filter */}
          <button
            onClick={() => setFilterState('todos')}
            className="shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition-all duration-150 cursor-pointer"
            style={filterState === 'todos' ? {
              background: 'var(--accent)', color: '#060D13', border: '1px solid var(--accent)',
            } : {
              background: 'rgba(9,21,33,0.6)', color: 'rgba(255,255,255,0.45)', border: '1px solid rgba(255,255,255,0.08)',
            }}
          >
            Todos
            <span className="ml-1.5 tabular-nums opacity-60">{leads.length}</span>
          </button>
          {STATE_ORDER.map((s) => {
            const m = STATE_META[s]
            const active = filterState === s
            return (
              <button
                key={s}
                onClick={() => setFilterState(active ? 'todos' : s)}
                className="flex shrink-0 cursor-pointer items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all duration-150"
                style={active ? {
                  color: m.color, background: m.bg, border: `1px solid ${m.border}`,
                } : {
                  color: 'rgba(255,255,255,0.40)', background: 'rgba(9,21,33,0.6)', border: '1px solid rgba(255,255,255,0.07)',
                }}
              >
                <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ background: m.dot }} />
                {m.label}
                <span className="tabular-nums opacity-55">{stateCounts[s] || 0}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Table card */}
      <div
        className="stagger-4 rounded-2xl overflow-hidden"
        style={{ border: '1px solid rgba(255,255,255,0.06)', background: 'rgba(9,21,33,0.5)' }}
      >
        <div
          className="flex items-center justify-between border-b px-4 py-3 sm:px-5"
          style={{ borderColor: 'rgba(255,255,255,0.05)' }}
        >
          <p className="text-sm font-medium text-white/55">Leads calificados</p>
          <p className="text-xs font-mono text-white/28">{filtrados.length}</p>
        </div>

        {loading ? (
          <div>{[1, 2, 3].map((i) => <SkeletonTableRow key={i} />)}</div>
        ) : filtrados.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
            <div
              className="h-12 w-12 rounded-2xl flex items-center justify-center"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
            >
              <TrendingUp className="h-5 w-5 text-white/20" strokeWidth={1.5} />
            </div>
            <div>
              <p className="text-white/45 text-sm font-medium">No hay leads</p>
              <p className="text-white/22 text-xs mt-0.5 max-w-xs">
                {search ? 'Prueba con otro término de búsqueda' : 'Aparecerán conforme tu agente califique contactos'}
              </p>
            </div>
          </div>
        ) : (
          <>
            {/* Mobile cards */}
            <ul className="md:hidden">
              {filtrados.map((lead, idx) => {
                const state = lead.state || lead.estado
                const phone = lead.phone || lead.telefono
                const waLink = getWhatsAppLink(phone)
                return (
                  <li
                    key={lead.id}
                    className="space-y-3 p-4"
                    style={{
                      borderTop: idx > 0 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                      animation: `fadeInUp 280ms cubic-bezier(0.23,1,0.32,1) ${idx * 30}ms both`,
                    }}
                  >
                    <div className="flex min-w-0 items-start justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-2.5">
                        <LeadAvatar lead={lead} />
                        <div className="min-w-0">
                          <p className="font-semibold text-white/80 text-sm truncate">{getDisplayName(lead)}</p>
                          {phone && (
                            <p className="text-xs text-white/30 flex items-center gap-1 mt-0.5 font-mono">
                              <Phone className="h-3 w-3 shrink-0" />
                              {phone}
                            </p>
                          )}
                        </div>
                      </div>
                      <StateBadge state={state} />
                    </div>
                    <ScoreBar score={lead.score} />
                    <div className="flex flex-col gap-2 min-[430px]:flex-row">
                      {waLink && (
                        <a
                          href={waLink}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs transition-colors duration-150"
                          style={{ color: '#22D3A0', background: 'rgba(34,211,160,0.10)', border: '1px solid rgba(34,211,160,0.20)' }}
                        >
                          <MessageCircle className="h-3.5 w-3.5" strokeWidth={1.75} />
                          WhatsApp
                        </a>
                      )}
                      <Button size="sm" variant="outline" onClick={() => openSignals(lead)} className="flex-1 text-xs">
                        <Zap className="h-3.5 w-3.5" strokeWidth={1.75} />
                        Señales
                      </Button>
                    </div>
                  </li>
                )
              })}
            </ul>

            {/* Desktop table */}
            <div className="hidden overflow-x-auto overscroll-x-contain md:block">
              <table className="min-w-[900px] w-full text-sm">
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    {['Lead', 'Teléfono', 'Interacciones', 'Último contacto', 'Score', 'Estado', ''].map((h) => (
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
                  {filtrados.map((lead, idx) => {
                    const state = lead.state || lead.estado
                    const phone = lead.phone || lead.telefono
                    const waLink = getWhatsAppLink(phone)
                    return (
                      <tr
                        key={lead.id}
                        className="group transition-colors duration-150"
                        style={{
                          borderTop: idx > 0 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                          animation: `fadeInUp 280ms cubic-bezier(0.23,1,0.32,1) ${idx * 25}ms both`,
                        }}
                        onMouseEnter={(e) => { (e.currentTarget as HTMLTableRowElement).style.background = 'rgba(255,255,255,0.02)' }}
                        onMouseLeave={(e) => { (e.currentTarget as HTMLTableRowElement).style.background = '' }}
                      >
                        <td className="py-3.5 px-5">
                          <div className="flex items-center gap-2.5">
                            <LeadAvatar lead={lead} size="sm" />
                            <span className="font-semibold text-white/78 group-hover:text-white/92 transition-colors duration-150 truncate max-w-36">
                              {getDisplayName(lead)}
                            </span>
                          </div>
                        </td>
                        <td className="py-3.5 px-5">
                          {phone ? (
                            <div className="flex items-center gap-2">
                              <span className="text-white/40 tabular-nums text-xs font-mono">{phone}</span>
                              {waLink && (
                                <a
                                  href={waLink}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="opacity-0 group-hover:opacity-100 h-6 w-6 flex items-center justify-center rounded-lg transition-all duration-150 cursor-pointer"
                                  style={{ color: '#22D3A0', background: 'rgba(34,211,160,0.10)' }}
                                  title="Abrir en WhatsApp"
                                >
                                  <MessageCircle className="h-3.5 w-3.5" strokeWidth={1.75} />
                                </a>
                              )}
                            </div>
                          ) : (
                            <span className="text-white/20 text-xs">—</span>
                          )}
                        </td>
                        <td className="py-3.5 px-5">
                          {lead.interaction_count > 0 ? (
                            <span
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium tabular-nums"
                              style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.45)' }}
                            >
                              <MessageCircle className="h-3 w-3" strokeWidth={1.75} />
                              {lead.interaction_count}
                            </span>
                          ) : (
                            <span className="text-white/20 text-xs">—</span>
                          )}
                        </td>
                        <td className="py-3.5 px-5">
                          {lead.last_interaction ? (
                            <span className="flex items-center gap-1 text-xs text-white/35">
                              <Clock className="h-3 w-3 shrink-0 text-white/20" strokeWidth={1.75} />
                              {formatTimestamp(lead.last_interaction)}
                            </span>
                          ) : (
                            <span className="text-white/20 text-xs">—</span>
                          )}
                        </td>
                        <td className="py-3.5 px-5 w-40">
                          <ScoreBar score={lead.score} />
                        </td>
                        <td className="py-3.5 px-5">
                          <StateBadge state={state} />
                        </td>
                        <td className="py-3.5 px-5">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openSignals(lead)}
                            className="text-xs opacity-0 group-hover:opacity-100 transition-opacity duration-150 whitespace-nowrap cursor-pointer"
                          >
                            <Zap className="h-3.5 w-3.5" strokeWidth={1.75} />
                            Señales
                          </Button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {/* Signals drawer */}
      {selectedLead && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/65 backdrop-blur-sm"
            onClick={closeSignals}
          />
          <aside
            className="fixed right-0 top-0 z-50 flex h-[100dvh] w-full max-w-[min(24rem,100vw)] flex-col"
            style={{
              animation: 'slide-in-right 260ms cubic-bezier(0.32,0.72,0,1) both',
              background: 'rgba(6,13,19,0.96)',
              backdropFilter: 'blur(24px) saturate(160%)',
              borderLeft: '1px solid rgba(255,255,255,0.08)',
              boxShadow: 'inset 1px 0 0 rgba(255,255,255,0.04), -32px 0 80px rgba(0,0,0,0.6)',
            }}
          >
            {/* Drawer header */}
            <div
              className="flex shrink-0 items-center justify-between px-4 py-4 sm:px-5"
              style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
            >
              <div className="flex min-w-0 items-center gap-3">
                <LeadAvatar lead={selectedLead} size="sm" />
                <div className="min-w-0">
                  <h2 className="text-sm font-semibold text-white/85 truncate">{getDisplayName(selectedLead)}</h2>
                  <p className="text-[10px] text-white/30 mt-0.5 flex items-center gap-1">
                    <TrendingUp className="h-3 w-3" strokeWidth={1.75} />
                    Historial de scoring
                  </p>
                </div>
              </div>
              <button
                onClick={closeSignals}
                className="h-8 w-8 flex items-center justify-center rounded-xl text-white/40 hover:text-white/70 hover:bg-white/5 transition-all duration-150 active:scale-[0.96] cursor-pointer shrink-0"
                aria-label="Cerrar"
              >
                <X className="h-4 w-4" strokeWidth={1.75} />
              </button>
            </div>

            {/* Lead mini-stats */}
            <div
              className="grid shrink-0 grid-cols-3 gap-2 px-4 py-3 sm:gap-3 sm:px-5"
              style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}
            >
              {[
                { label: 'Score', value: `${selectedLead.score}/10` },
                { label: 'Mensajes', value: selectedLead.interaction_count || 0 },
                { label: 'Estado', value: (selectedLead.state || selectedLead.estado || 'curioso').toUpperCase() },
              ].map(({ label, value }) => (
                <div key={label} className="text-center">
                  <p className="text-[10px] text-white/28">{label}</p>
                  <p className="text-sm font-bold text-white/80 tabular-nums mt-0.5">{value}</p>
                </div>
              ))}
            </div>

            {/* Signal timeline */}
            <div className="flex-1 space-y-3 overflow-y-auto p-4 sm:p-5">
              {signalsLoading ? (
                <div className="flex items-center justify-center py-12">
                  <span
                    className="h-6 w-6 rounded-full border-2 animate-spin"
                    style={{ borderColor: 'rgba(255,255,255,0.08)', borderTopColor: 'var(--accent)' }}
                  />
                </div>
              ) : signals.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
                  <div
                    className="h-11 w-11 rounded-xl flex items-center justify-center"
                    style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
                  >
                    <Zap className="h-5 w-5 text-white/20" strokeWidth={1.5} />
                  </div>
                  <p className="text-white/35 text-sm">Sin historial de señales</p>
                </div>
              ) : (
                signals.map((event, idx) => (
                  <div
                    key={event.id}
                    className="rounded-xl p-4 space-y-2.5"
                    style={{
                      background: 'rgba(255,255,255,0.03)',
                      border: '1px solid rgba(255,255,255,0.06)',
                      animation: `fadeInUp 260ms cubic-bezier(0.23,1,0.32,1) ${idx * 40}ms both`,
                    }}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-bold text-white/80 tabular-nums">
                          {event.score_before.toFixed(1)} → {event.score_after.toFixed(1)}
                        </p>
                        <p
                          className="text-xs font-semibold mt-0.5"
                          style={{
                            color: event.delta > 0 ? '#22D3A0' : event.delta < 0 ? '#F87171' : 'rgba(255,255,255,0.35)',
                          }}
                        >
                          {event.delta > 0 ? '↑' : event.delta < 0 ? '↓' : '='} {Math.abs(event.delta).toFixed(1)} pts
                        </p>
                      </div>
                      <span
                        className="px-2 py-0.5 rounded-md text-[10px] font-semibold shrink-0"
                        style={event.delta > 0 ? {
                          color: '#22D3A0', background: 'rgba(34,211,160,0.10)', border: '1px solid rgba(34,211,160,0.20)',
                        } : event.delta < 0 ? {
                          color: '#F87171', background: 'rgba(248,113,113,0.10)', border: '1px solid rgba(248,113,113,0.20)',
                        } : {
                          color: 'rgba(255,255,255,0.35)', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)',
                        }}
                      >
                        {event.signal_type || 'n/a'}
                      </span>
                    </div>

                    {event.signal_keywords?.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {event.signal_keywords.map((kw, i) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 rounded-md text-[10px] font-medium"
                            style={{ color: 'var(--accent)', background: 'rgba(56,189,248,0.08)', border: '1px solid rgba(56,189,248,0.15)' }}
                          >
                            {kw}
                          </span>
                        ))}
                      </div>
                    )}

                    <p className="text-xs text-white/35 italic leading-relaxed">
                      &quot;{event.message_excerpt}&quot;
                    </p>

                    <p className="text-[10px] text-white/22">{formatTimestamp(event.created_at)}</p>
                  </div>
                ))
              )}
            </div>
          </aside>
        </>
      )}
    </div>
  )
}
