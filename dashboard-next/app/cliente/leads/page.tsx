'use client'

import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { TrendingUp, Zap, X, Search } from 'lucide-react'
import { useState, useEffect } from 'react'
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
  email: string
  phone?: string
  telefono?: string
  score: number
  state?: LeadState
  estado?: LeadState
  urgency: number
  budget: number | null
  decision_power: number
  interaction_count: number
  created_at: string
}

const STATE_META: Record<LeadState, { label: string; cls: string }> = {
  urgente:    { label: 'URGENTE',    cls: 'bg-error/15 text-error border-error/20 font-bold' },
  caliente:   { label: 'CALIENTE',   cls: 'bg-error/10 text-error border-error/10' },
  interesado: { label: 'INTERESADO', cls: 'bg-warning/10 text-warning border-warning/10' },
  prospecto:  { label: 'PROSPECTO',  cls: 'bg-info/10 text-info border-info/10' },
  curioso:    { label: 'CURIOSO',    cls: 'bg-surface text-text-muted border-border' },
}

function ScoreBar({ score }: { score: number }) {
  const pct = (score / 10) * 100
  const color =
    score >= 9 ? 'bg-error' :
    score >= 7 ? 'bg-warning' :
    score >= 5 ? 'bg-info' : 'bg-success'

  return (
    <div className="flex items-center gap-2.5 min-w-0">
      <div className="flex-1 h-1.5 rounded-full bg-surface overflow-hidden">
        <div
          className={['h-full rounded-full transition-all duration-500', color].join(' ')}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-semibold tabular-nums text-text-primary w-8 text-right">
        {score}/10
      </span>
    </div>
  )
}

function StateBadge({ state }: { state: LeadState | undefined }) {
  const meta = STATE_META[state ?? 'curioso']
  return (
    <span className={['px-2 py-0.5 rounded-md text-xs font-medium border', meta.cls].join(' ')}>
      {meta.label}
    </span>
  )
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [filtrados, setFiltrados] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterState, setFilterState] = useState<LeadState | 'todos'>('todos')
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null)
  const [signals, setSignals] = useState<SignalEvent[]>([])
  const [signalsLoading, setSignalsLoading] = useState(false)

  useEffect(() => { loadLeads() }, [])

  async function loadLeads() {
    try {
      const res = await fetch('/api/cliente/leads')
      if (!res.ok) throw new Error('Failed')
      const data = await res.json()
      setLeads(data.data || [])
      setFiltrados(data.data || [])
    } catch {
    } finally {
      setLoading(false)
    }
  }

  async function loadSignals(leadId: string) {
    setSignalsLoading(true)
    try {
      const res = await fetch(`/api/cliente/leads/${leadId}/signals`)
      if (!res.ok) throw new Error('Failed')
      const data = await res.json()
      setSignals(data.data || [])
    } catch {
      setSignals([])
    } finally {
      setSignalsLoading(false)
    }
  }

  useEffect(() => {
    let result = leads
    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter((l) =>
        (l.name || l.nombre || '').toLowerCase().includes(q) ||
        l.email.toLowerCase().includes(q) ||
        (l.phone || l.telefono || '').includes(q),
      )
    }
    if (filterState !== 'todos') {
      result = result.filter((l) => (l.state || l.estado) === filterState)
    }
    setFiltrados(result)
  }, [search, filterState, leads])

  const openSignals = (leadId: string) => {
    setSelectedLeadId(leadId)
    loadSignals(leadId)
  }

  const closeSignals = () => {
    setSelectedLeadId(null)
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

      {/* Filters */}
      <div className="stagger-2 flex flex-wrap gap-2">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted pointer-events-none" />
          <Input
            placeholder="Buscar por nombre, email o teléfono..."
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          value={filterState}
          onChange={(e) => setFilterState(e.target.value as LeadState | 'todos')}
          className="px-3 py-2 rounded-lg border border-border bg-card-bg text-text-secondary text-sm cursor-pointer hover:border-border-light transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-accent/30"
        >
          <option value="todos">Todos los estados</option>
          <option value="urgente">URGENTE</option>
          <option value="caliente">CALIENTE</option>
          <option value="interesado">INTERESADO</option>
          <option value="prospecto">PROSPECTO</option>
          <option value="curioso">CURIOSO</option>
        </select>
      </div>

      {/* Table card */}
      <div className="stagger-3 rounded-xl border border-border bg-card-bg overflow-hidden">
        <div className="px-5 py-3.5 border-b border-border flex items-center justify-between">
          <p className="text-sm font-medium text-text-primary">Leads calificados</p>
          <p className="text-xs text-text-muted">{filtrados.length} encontrados</p>
        </div>

        {loading ? (
          <div className="divide-y divide-border">
            {[1, 2, 3].map((i) => (
              <div key={i} className="px-5 py-4 flex gap-4 animate-pulse">
                <div className="flex-1 space-y-2">
                  <div className="h-3.5 w-36 rounded bg-surface" />
                  <div className="h-3 w-52 rounded bg-surface" />
                </div>
                <div className="h-5 w-24 rounded bg-surface" />
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
                const name = lead.name || lead.nombre || 'Sin nombre'
                const phone = lead.phone || lead.telefono || '—'
                return (
                  <li key={lead.id} className="p-4 space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-medium text-text-primary text-sm">{name}</p>
                        <p className="text-xs text-text-muted truncate">{lead.email}</p>
                        <p className="text-xs text-text-muted">{phone}</p>
                      </div>
                      <StateBadge state={state} />
                    </div>
                    <ScoreBar score={lead.score} />
                    <Button size="sm" variant="outline" onClick={() => openSignals(lead.id)} className="w-full text-xs">
                      <Zap className="h-3 w-3" />
                      Ver señales
                    </Button>
                  </li>
                )
              })}
            </ul>

            {/* Desktop table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    {['Nombre', 'Email', 'Teléfono', 'Score', 'Estado', ''].map((h) => (
                      <th key={h} className="text-left py-3 px-5 text-xs font-semibold text-text-muted uppercase tracking-wider">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filtrados.map((lead) => {
                    const state = lead.state || lead.estado
                    const name = lead.name || lead.nombre || 'Sin nombre'
                    const phone = lead.phone || lead.telefono || '—'
                    return (
                      <tr key={lead.id} className="hover:bg-surface/40 transition-colors duration-150 group">
                        <td className="py-3.5 px-5 font-medium text-text-primary group-hover:text-accent transition-colors duration-150">{name}</td>
                        <td className="py-3.5 px-5 text-text-secondary">{lead.email}</td>
                        <td className="py-3.5 px-5 text-text-secondary">{phone}</td>
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
                            onClick={() => openSignals(lead.id)}
                            className="text-xs opacity-0 group-hover:opacity-100 transition-opacity duration-150"
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
      {selectedLeadId && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            onClick={closeSignals}
          />
          <aside
            className="fixed right-0 top-0 z-50 h-full w-full max-w-md flex flex-col glass shadow-2xl"
            style={{
              animation: 'slideInRight 250ms cubic-bezier(0.32,0.72,0,1) both',
            }}
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
              <div>
                <h2 className="text-base font-semibold text-text-primary">Análisis de Señales</h2>
                <p className="text-xs text-text-muted mt-0.5">Historial de scoring automático</p>
              </div>
              <button
                onClick={closeSignals}
                className="h-8 w-8 flex items-center justify-center rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface transition-all duration-150 active:scale-[0.97] cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
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
                        <p className="text-xs text-text-muted">
                          Delta: {event.delta > 0 ? '+' : ''}{event.delta.toFixed(1)}
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
