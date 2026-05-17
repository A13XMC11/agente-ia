'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { TrendingUp, Zap, X } from 'lucide-react'
import { useState, useEffect } from 'react'
import { formatTimestamp } from '@/lib/date-format'

type LeadState = 'curioso' | 'prospecto' | 'interesado' | 'caliente' | 'urgente'

interface Signal {
  name: string
  delta: number
  keywords: string[]
}

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
  last_interaction?: string
  interaction_count: number
  score_updated_at?: string
  created_at: string
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

  useEffect(() => {
    loadLeads()
  }, [])

  async function loadLeads() {
    try {
      const response = await fetch('/api/cliente/leads')
      if (!response.ok) throw new Error('Failed to load')
      const data = await response.json()
      setLeads(data.data || [])
      setFiltrados(data.data || [])
    } catch (error) {
      console.error('Error loading leads:', error)
    } finally {
      setLoading(false)
    }
  }

  async function loadSignals(leadId: string) {
    setSignalsLoading(true)
    try {
      const response = await fetch(`/api/cliente/leads/${leadId}/signals`)
      if (!response.ok) throw new Error('Failed to load signals')
      const data = await response.json()
      setSignals(data.data || [])
    } catch (error) {
      console.error('Error loading signals:', error)
      setSignals([])
    } finally {
      setSignalsLoading(false)
    }
  }

  const handleViewSignals = (leadId: string) => {
    setSelectedLeadId(leadId)
    loadSignals(leadId)
  }

  useEffect(() => {
    let resultado = leads

    if (search.trim()) {
      const query = search.toLowerCase()
      const leadName = (l: Lead) => (l.name || l.nombre || '').toLowerCase()
      resultado = resultado.filter(l =>
        leadName(l).includes(query) ||
        l.email.toLowerCase().includes(query) ||
        (l.phone || l.telefono || '').includes(query)
      )
    }

    if (filterState !== 'todos') {
      resultado = resultado.filter(l => (l.state || l.estado) === filterState)
    }

    setFiltrados(resultado)
  }, [search, filterState, leads])

  const getStateBadge = (state: LeadState | undefined) => {
    const currentState = state || 'curioso'
    switch (currentState) {
      case 'urgente':
        return {
          class: 'bg-error/20 text-error font-bold',
          label: 'URGENTE 🔥🔥'
        }
      case 'caliente':
        return {
          class: 'bg-error/10 text-error',
          label: 'CALIENTE 🔥'
        }
      case 'interesado':
        return {
          class: 'bg-warning/10 text-warning',
          label: 'INTERESADO'
        }
      case 'prospecto':
        return {
          class: 'bg-info/10 text-info',
          label: 'PROSPECTO'
        }
      case 'curioso':
      default:
        return {
          class: 'bg-text-muted/10 text-text-muted',
          label: 'CURIOSO'
        }
    }
  }

  const getScoreBar = (score: number) => {
    const percentage = (score / 10) * 100
    let barColor = 'bg-error'
    if (score >= 9) barColor = 'bg-error'
    else if (score >= 7) barColor = 'bg-warning'
    else if (score >= 5) barColor = 'bg-info'
    else barColor = 'bg-success'

    return { percentage, barColor }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Leads</h1>
        <p className="text-text-secondary mt-2">Calificación automática de leads con inteligencia artificial</p>
      </div>

      <div className="flex gap-2 flex-wrap">
        <Input
          placeholder="Buscar por nombre, email o teléfono..."
          className="flex-1 min-w-64"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          value={filterState}
          onChange={(e) => setFilterState(e.target.value as LeadState | 'todos')}
          className="px-3 py-2 border rounded-lg bg-background text-text-primary"
        >
          <option value="todos">Todos los estados</option>
          <option value="urgente">🔥🔥 URGENTE (9-10)</option>
          <option value="caliente">🔥 CALIENTE (7-8)</option>
          <option value="interesado">INTERESADO (5-6)</option>
          <option value="prospecto">PROSPECTO (3-4)</option>
          <option value="curioso">CURIOSO (0-2)</option>
        </select>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Leads Calificados</CardTitle>
          <CardDescription>{filtrados.length} leads encontrados</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-12">
              <p className="text-text-secondary">Cargando leads...</p>
            </div>
          ) : filtrados.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <TrendingUp className="h-12 w-12 text-text-muted mb-4" />
              <p className="text-text-secondary">No hay leads</p>
              <p className="text-sm text-text-muted mt-2">Los leads se mostrarán aquí conforme tu agente califique contactos</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Nombre</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Email</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Teléfono</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Score</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Estado</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {filtrados.map((lead) => {
                    const state = lead.state || lead.estado
                    const stateBadge = getStateBadge(state)
                    const leadName = lead.name || lead.nombre || 'Sin nombre'
                    const leadPhone = lead.phone || lead.telefono || '-'
                    const scoreBar = getScoreBar(lead.score)
                    return (
                      <tr key={lead.id} className="border-b hover:bg-surface">
                        <td className="py-3 px-4 text-text-primary font-medium">{leadName}</td>
                        <td className="py-3 px-4 text-text-secondary">{lead.email}</td>
                        <td className="py-3 px-4 text-text-secondary">{leadPhone}</td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <div className="flex-1">
                              <div className="relative h-2 bg-surface rounded-full overflow-hidden">
                                <div
                                  className={`h-full ${scoreBar.barColor} transition-all`}
                                  style={{ width: `${scoreBar.percentage}%` }}
                                />
                              </div>
                            </div>
                            <span className="text-xs font-medium min-w-10">{lead.score}/10</span>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${stateBadge.class}`}>
                            {stateBadge.label}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleViewSignals(lead.id)}
                            className="text-xs"
                          >
                            <Zap className="h-3 w-3 mr-1" />
                            Ver señales
                          </Button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Signals Drawer */}
      {selectedLeadId && (
        <div className="fixed inset-0 z-50 bg-black/50 flex justify-end">
          <div className="bg-background w-full max-w-md h-full overflow-y-auto shadow-lg animate-in slide-in-from-right">
            <div className="p-6 border-b flex justify-between items-center sticky top-0 bg-background">
              <div>
                <h2 className="text-lg font-semibold text-text-primary">Análisis de Señales</h2>
                <p className="text-sm text-text-secondary">Historial de scoring automático</p>
              </div>
              <button
                onClick={() => {
                  setSelectedLeadId(null)
                  setSignals([])
                }}
                className="p-1 hover:bg-surface rounded-lg transition-colors"
              >
                <X className="h-5 w-5 text-text-secondary" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              {signalsLoading ? (
                <div className="text-center py-8">
                  <p className="text-text-secondary">Cargando señales...</p>
                </div>
              ) : signals.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-text-secondary">Sin historial de señales</p>
                </div>
              ) : (
                signals.map((event) => (
                  <div
                    key={event.id}
                    className="p-4 bg-surface rounded-lg border border-border"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <p className="font-medium text-text-primary text-sm">
                          {event.score_before.toFixed(1)} → {event.score_after.toFixed(1)}
                        </p>
                        <p className="text-xs text-text-secondary">
                          Delta: {event.delta > 0 ? '+' : ''}{event.delta.toFixed(1)}
                        </p>
                      </div>
                      <span className={`text-xs font-medium px-2 py-1 rounded ${
                        event.delta > 0
                          ? 'bg-success/10 text-success'
                          : event.delta < 0
                            ? 'bg-error/10 text-error'
                            : 'bg-text-muted/10 text-text-muted'
                      }`}>
                        {event.signal_type || 'Sin señal'}
                      </span>
                    </div>

                    {event.signal_keywords && event.signal_keywords.length > 0 && (
                      <div className="mb-2">
                        <div className="flex flex-wrap gap-1">
                          {event.signal_keywords.map((keyword, idx) => (
                            <span
                              key={idx}
                              className="text-xs bg-info/10 text-info px-2 py-1 rounded"
                            >
                              {keyword}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    <p className="text-xs text-text-secondary italic mb-2">
                      &quot;{event.message_excerpt}&quot;
                    </p>

                    <p className="text-xs text-text-muted">
                      {formatTimestamp(event.created_at)}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
