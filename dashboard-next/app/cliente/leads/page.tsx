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

const STATE_META: Record<LeadState, { label: string; cls: string; dot: string }> = {
  urgente:    { label: 'URGENTE',    cls: 'bg-error/15 text-error border-error/20 font-bold',        dot: 'bg-error' },
  caliente:   { label: 'CALIENTE',   cls: 'bg-error/10 text-error border-error/10',                  dot: 'bg-orange-400' },
  interesado: { label: 'INTERESADO', cls: 'bg-warning/10 text-warning border-warning/10',            dot: 'bg-warning' },
  prospecto:  { label: 'PROSPECTO',  cls: 'bg-info/10 text-info border-info/10',                     dot: 'bg-info' },
  curioso:    { label: 'CURIOSO',    cls: 'bg-surface text-text-muted border-border',                dot: 'bg-text-muted' },
}

const STATE_ORDER: LeadState[] = ['urgente', 'caliente', 'interesado', 'prospecto', 'curioso']

function getDisplayName(lead: Lead): string {
  const name = lead.name || lead.nombre
  if (name && name.trim()) return name.trim()
  return 'Sin nombre'
}

function getInitials(lead: Lead): string {
  const name = lead.name || lead.nombre
  if (name && name.trim()) {
    return name.trim().split(' ').slice(0, 2).map((w: string) => w[0]).join('').toUpperCase()
  }
  return '#'
}

function getWhatsAppLink(phone: string | undefined): string | null {
  if (!phone) return null
  const digits = phone.replace(/\D/g, '')
  if (!digits) return null
  return `https://wa.me/${digits}`
}

function ScoreBar({ score }: { score: number }) {
  const pct = (score / 10) * 100
  const color =
    score >= 9 ? 'bg-error' :
    score >= 7 ? 'bg-orange-400' :
    score >= 5 ? 'bg-warning' :
    score >= 3 ? 'bg-info' : 'bg-text-muted'

  return (
    <div className="flex items-center gap-2.5 min-w-0">
      <div className="flex-1 h-1.5 rounded-full bg-surface overflow-hidden">
        <div
          className={['h-full rounded-full transition-all duration-700', color].join(' ')}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-semibold tabular-nums text-text-primary w-8 text-right shrink-0">
        {score}/10
      </span>
    </div>
  )
}

function StateBadge({ state }: { state: LeadState | undefined }) {
  const meta = STATE_META[state ?? 'curioso']
  return (
    <span className={['inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-medium border', meta.cls].join(' ')}>
      <span className={['h-1.5 w-1.5 rounded-full shrink-0', meta.dot].join(' ')} />
      {meta.label}
    </span>
  )
}

function LeadAvatar({ lead }: { lead: Lead }) {
  const state = lead.state || lead.estado
  const meta = STATE_META[state ?? 'curioso']
  return (
    <div className={[
      'h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0',
      'border',
      meta.cls,
    ].join(' ')}>
      {getInitials(lead)}
    </div>
  )
}

function StatCard({ icon: Icon, label, value, sub }: {
  icon: React.ElementType
  label: string
  value: string | number
  sub?: string
}) {
  return (
    <div className="rounded-xl border border-border bg-card-bg px-4 py-3.5 flex items-center gap-3">
      <div className="h-8 w-8 rounded-lg bg-surface flex items-center justify-center shrink-0">
        <Icon className="h-4 w-4 text-text-muted" />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-text-muted">{label}</p>
        <p className="text-lg font-bold text-text-primary tabular-nums leading-tight">{value}</p>
        {sub && <p className="text-xs text-text-muted">{sub}</p>}
      </div>
    </div>
  )
}

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
      /* silent — UI shows empty state */
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
    const urgentes = leads.filter((l) => (l.state || l.estado) === 'urgente' || (l.state || l.estado) === 'caliente').length
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
      result = result.filter((l) =>
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
    <div className="space-y-5">
      <div className="stagger-1">
        <h1 className="text-3xl font-bold text-text-primary tracking-tight">Leads</h1>
        <p className="text-text-secondary mt-1.5 text-sm">
          Calificación automática con inteligencia artificial
        </p>
      </div>

      {/* Stats */}
      {!loading && leads.length > 0 && (
        <div className="stagger-2 grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard icon={Users} label="Total leads" value={stats.total} />
          <StatCard icon={Zap} label="Alta prioridad" value={stats.urgentes} sub="urgentes + calientes" />
          <StatCard icon={TrendingUp} label="Score promedio" value={stats.avgScore} sub="sobre 10" />
          <StatCard icon={MessageCircle} label="Con interacción" value={stats.withInteraction} />
        </div>
      )}

      {/* State filter pills */}
      <div className="stagger-3 flex flex-wrap gap-2 items-center">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted pointer-events-none" />
          <Input
            placeholder="Buscar por nombre o teléfono..."
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => setFilterState('todos')}
            className={[
              'px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-150',
              filterState === 'todos'
                ? 'bg-accent text-accent-foreground border-accent'
                : 'bg-card-bg text-text-secondary border-border hover:border-border-light',
            ].join(' ')}
          >
            Todos
            <span className="ml-1.5 tabular-nums opacity-70">{leads.length}</span>
          </button>
          {STATE_ORDER.map((s) => {
            const meta = STATE_META[s]
            const active = filterState === s
            return (
              <button
                key={s}
                onClick={() => setFilterState(active ? 'todos' : s)}
                className={[
                  'px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-150 flex items-center gap-1.5',
                  active ? meta.cls : 'bg-card-bg text-text-secondary border-border hover:border-border-light',
                ].join(' ')}
              >
                <span className={['h-1.5 w-1.5 rounded-full', meta.dot].join(' ')} />
                {meta.label}
                <span className="tabular-nums opacity-70">{stateCounts[s] || 0}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Table card */}
      <div className="stagger-4 rounded-xl border border-border bg-card-bg overflow-hidden">
        <div className="px-5 py-3.5 border-b border-border flex items-center justify-between">
          <p className="text-sm font-medium text-text-primary">Leads calificados</p>
          <p className="text-xs text-text-muted">{filtrados.length} encontrados</p>
        </div>

        {loading ? (
          <div className="divide-y divide-border">
            {[1, 2, 3].map((i) => (
              <div key={i} className="px-5 py-4 flex gap-4 animate-pulse">
                <div className="h-8 w-8 rounded-full bg-surface shrink-0" />
                <div className="flex-1 space-y-2 py-0.5">
                  <div className="h-3.5 w-32 rounded bg-surface" />
                  <div className="h-3 w-24 rounded bg-surface" />
                </div>
                <div className="h-5 w-20 rounded bg-surface self-center" />
              </div>
            ))}
          </div>
        ) : filtrados.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-14 text-center">
            <TrendingUp className="h-10 w-10 text-text-muted mb-3" />
            <p className="text-text-secondary text-sm font-medium">No hay leads</p>
            <p className="text-text-muted text-xs mt-1 max-w-xs">
              Los leads aparecerán aquí conforme tu agente califique contactos
            </p>
          </div>
        ) : (
          <>
            {/* Mobile cards */}
            <ul className="md:hidden divide-y divide-border">
              {filtrados.map((lead) => {
                const state = lead.state || lead.estado
                const phone = lead.phone || lead.telefono
                const waLink = getWhatsAppLink(phone)
                return (
                  <li key={lead.id} className="p-4 space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <LeadAvatar lead={lead} />
                        <div className="min-w-0">
                          <p className="font-medium text-text-primary text-sm truncate">{getDisplayName(lead)}</p>
                          {phone && (
                            <p className="text-xs text-text-muted flex items-center gap-1">
                              <Phone className="h-3 w-3 shrink-0" />
                              {phone}
                            </p>
                          )}
                        </div>
                      </div>
                      <StateBadge state={state} />
                    </div>
                    <ScoreBar score={lead.score} />
                    <div className="flex gap-2">
                      {waLink && (
                        <a
                          href={waLink}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex-1 text-xs flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg border border-success/20 bg-success/10 text-success hover:bg-success/20 transition-colors duration-150"
                        >
                          <MessageCircle className="h-3 w-3" />
                          WhatsApp
                        </a>
                      )}
                      <Button size="sm" variant="outline" onClick={() => openSignals(lead)} className="flex-1 text-xs">
                        <Zap className="h-3 w-3" />
                        Señales
                      </Button>
                    </div>
                  </li>
                )
              })}
            </ul>

            {/* Desktop table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    {['Lead', 'Teléfono', 'Interacciones', 'Último contacto', 'Score', 'Estado', ''].map((h) => (
                      <th key={h} className="text-left py-3 px-5 text-xs font-semibold text-text-muted uppercase tracking-wider whitespace-nowrap">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filtrados.map((lead) => {
                    const state = lead.state || lead.estado
                    const phone = lead.phone || lead.telefono
                    const waLink = getWhatsAppLink(phone)
                    return (
                      <tr key={lead.id} className="hover:bg-surface/40 transition-colors duration-150 group">
                        <td className="py-3.5 px-5">
                          <div className="flex items-center gap-2.5">
                            <LeadAvatar lead={lead} />
                            <span className="font-medium text-text-primary group-hover:text-accent transition-colors duration-150 truncate max-w-35">
                              {getDisplayName(lead)}
                            </span>
                          </div>
                        </td>
                        <td className="py-3.5 px-5">
                          {phone ? (
                            <div className="flex items-center gap-2">
                              <span className="text-text-secondary tabular-nums">{phone}</span>
                              {waLink && (
                                <a
                                  href={waLink}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  title="Abrir en WhatsApp"
                                  className="opacity-0 group-hover:opacity-100 h-6 w-6 flex items-center justify-center rounded-md bg-success/10 text-success hover:bg-success/20 transition-all duration-150"
                                >
                                  <MessageCircle className="h-3.5 w-3.5" />
                                </a>
                              )}
                            </div>
                          ) : (
                            <span className="text-text-muted">—</span>
                          )}
                        </td>
                        <td className="py-3.5 px-5">
                          {lead.interaction_count > 0 ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-surface border border-border text-xs text-text-secondary tabular-nums">
                              <MessageCircle className="h-3 w-3" />
                              {lead.interaction_count}
                            </span>
                          ) : (
                            <span className="text-text-muted text-xs">—</span>
                          )}
                        </td>
                        <td className="py-3.5 px-5">
                          {lead.last_interaction ? (
                            <span className="flex items-center gap-1 text-xs text-text-secondary">
                              <Clock className="h-3 w-3 shrink-0 text-text-muted" />
                              {formatTimestamp(lead.last_interaction)}
                            </span>
                          ) : (
                            <span className="text-text-muted text-xs">—</span>
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
                            className="text-xs opacity-0 group-hover:opacity-100 transition-opacity duration-150 whitespace-nowrap"
                          >
                            <Zap className="h-3 w-3" />
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
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            onClick={closeSignals}
          />
          <aside
            className="fixed right-0 top-0 z-50 h-full w-full max-w-md flex flex-col glass shadow-2xl"
            style={{ animation: 'slideInRight 250ms cubic-bezier(0.32,0.72,0,1) both' }}
          >
            <style>{`
              @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0.4; }
                to   { transform: translateX(0);    opacity: 1; }
              }
              @keyframes fadeInUp {
                from { opacity:0; transform:translateY(6px); }
                to   { opacity:1; transform:translateY(0); }
              }
            `}</style>

            <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
              <div className="flex items-center gap-3 min-w-0">
                <LeadAvatar lead={selectedLead} />
                <div className="min-w-0">
                  <h2 className="text-base font-semibold text-text-primary truncate">{getDisplayName(selectedLead)}</h2>
                  <p className="text-xs text-text-muted mt-0.5 flex items-center gap-1">
                    <TrendingUp className="h-3 w-3" />
                    Historial de scoring
                  </p>
                </div>
              </div>
              <button
                onClick={closeSignals}
                className="h-8 w-8 flex items-center justify-center rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface transition-all duration-150 active:scale-[0.97] cursor-pointer shrink-0"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Lead mini-stats */}
            <div className="px-6 py-3 border-b border-border shrink-0 flex gap-4">
              <div className="text-center">
                <p className="text-xs text-text-muted">Score</p>
                <p className="text-lg font-bold text-text-primary tabular-nums">{selectedLead.score}/10</p>
              </div>
              <div className="w-px bg-border" />
              <div className="text-center">
                <p className="text-xs text-text-muted">Mensajes</p>
                <p className="text-lg font-bold text-text-primary tabular-nums">{selectedLead.interaction_count || 0}</p>
              </div>
              <div className="w-px bg-border" />
              <div className="text-center">
                <p className="text-xs text-text-muted">Estado</p>
                <div className="mt-0.5">
                  <StateBadge state={selectedLead.state || selectedLead.estado} />
                </div>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-3">
              {signalsLoading ? (
                <div className="flex items-center justify-center py-12">
                  <span className="h-6 w-6 rounded-full border-2 border-border border-t-accent animate-spin" />
                </div>
              ) : signals.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Zap className="h-8 w-8 text-text-muted mb-3" />
                  <p className="text-text-secondary text-sm">Sin historial de señales</p>
                </div>
              ) : (
                signals.map((event, idx) => (
                  <div
                    key={event.id}
                    className="rounded-xl border border-border bg-card-bg p-4 space-y-2.5"
                    style={{ animation: `fadeInUp 280ms cubic-bezier(0.23,1,0.32,1) ${idx * 40}ms both` }}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-text-primary tabular-nums">
                          {event.score_before.toFixed(1)} → {event.score_after.toFixed(1)}
                        </p>
                        <p className={[
                          'text-xs font-medium',
                          event.delta > 0 ? 'text-success' : event.delta < 0 ? 'text-error' : 'text-text-muted',
                        ].join(' ')}>
                          {event.delta > 0 ? '↑' : event.delta < 0 ? '↓' : '='} {Math.abs(event.delta).toFixed(1)} pts
                        </p>
                      </div>
                      <span className={[
                        'px-2 py-0.5 rounded-md text-xs font-medium border',
                        event.delta > 0 ? 'bg-success/10 text-success border-success/20' :
                        event.delta < 0 ? 'bg-error/10 text-error border-error/20' :
                                          'bg-surface text-text-muted border-border',
                      ].join(' ')}>
                        {event.signal_type || 'n/a'}
                      </span>
                    </div>

                    {event.signal_keywords?.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {event.signal_keywords.map((kw, i) => (
                          <span key={i} className="px-2 py-0.5 rounded-md text-xs bg-accent/8 text-accent border border-accent/15">
                            {kw}
                          </span>
                        ))}
                      </div>
                    )}

                    <p className="text-xs text-text-secondary italic leading-relaxed">
                      &quot;{event.message_excerpt}&quot;
                    </p>

                    <p className="text-xs text-text-muted">{formatTimestamp(event.created_at)}</p>
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
