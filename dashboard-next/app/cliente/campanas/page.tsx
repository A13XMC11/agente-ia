'use client'

import { useState, useEffect, useMemo } from 'react'
import { Megaphone, Plus, X, Send, Ban, Clock, CheckCircle2, FileText, Users, MessageCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

type CampanaStatus = 'draft' | 'scheduled' | 'sent' | 'cancelled'
type Segment = 'all' | 'hot_leads' | 'inactive' | 'customers'

interface Campana {
  id: string
  title: string
  message: string
  target_segment: Segment
  channel: string
  status: CampanaStatus
  scheduled_for: string
  recipients_count: number | null
  created_at: string
  launched_at?: string
  sent_at?: string
}

const STATUS_META: Record<CampanaStatus, { label: string; icon: React.ElementType; cls: string; dot: string }> = {
  draft:     { label: 'Borrador',   icon: FileText,      cls: 'bg-surface text-text-muted border-border',            dot: 'bg-text-muted' },
  scheduled: { label: 'Programada', icon: Clock,         cls: 'bg-accent/10 text-accent border-accent/20',           dot: 'bg-accent' },
  sent:      { label: 'Enviada',    icon: CheckCircle2,  cls: 'bg-success/10 text-success border-success/20',        dot: 'bg-success' },
  cancelled: { label: 'Cancelada',  icon: Ban,           cls: 'bg-error/10 text-error border-error/20',              dot: 'bg-error' },
}

const SEGMENT_LABELS: Record<Segment, string> = {
  all:       'Todos los contactos',
  hot_leads: 'Leads calientes',
  inactive:  'Inactivos +7 días',
  customers: 'Clientes activos',
}

function StatusBadge({ status }: { status: CampanaStatus }) {
  const meta = STATUS_META[status]
  return (
    <span className={['inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-medium border', meta.cls].join(' ')}>
      <span className={['h-1.5 w-1.5 rounded-full shrink-0', meta.dot].join(' ')} />
      {meta.label}
    </span>
  )
}

function StatCard({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: number }) {
  return (
    <div className="rounded-xl border border-border bg-card-bg px-4 py-3.5 flex items-center gap-3">
      <div className="h-8 w-8 rounded-lg bg-surface flex items-center justify-center shrink-0">
        <Icon className="h-4 w-4 text-text-muted" />
      </div>
      <div>
        <p className="text-xs text-text-muted">{label}</p>
        <p className="text-lg font-bold text-text-primary tabular-nums leading-tight">{value}</p>
      </div>
    </div>
  )
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('es-EC', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function CampanasPage() {
  const [campanas, setCampanas] = useState<Campana[]>([])
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState<CampanaStatus | 'todas'>('todas')
  const [showModal, setShowModal] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Form state
  const [titulo, setTitulo] = useState('')
  const [mensaje, setMensaje] = useState('')
  const [segment, setSegment] = useState<Segment>('all')
  const [programada, setProgramada] = useState('')
  const [creating, setCreating] = useState(false)
  const [formError, setFormError] = useState('')

  useEffect(() => { loadCampanas() }, [])

  async function loadCampanas() {
    try {
      const res = await fetch('/api/cliente/campanas')
      if (!res.ok) throw new Error('Failed')
      const json = await res.json()
      setCampanas(json.data || [])
    } catch {
      /* silent */
    } finally {
      setLoading(false)
    }
  }

  async function createCampana() {
    if (!titulo.trim() || !mensaje.trim()) {
      setFormError('El título y el mensaje son requeridos')
      return
    }
    setCreating(true)
    setFormError('')
    try {
      const res = await fetch('/api/cliente/campanas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ titulo, mensaje, target_segment: segment, canal: 'whatsapp', programada_para: programada || undefined }),
      })
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      setCampanas((prev) => [json.data, ...prev])
      setShowModal(false)
      resetForm()
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : 'Error al crear campaña')
    } finally {
      setCreating(false)
    }
  }

  async function patchCampana(id: string, action: 'launch' | 'cancel') {
    setActionLoading(id + action)
    try {
      const res = await fetch(`/api/cliente/campanas/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      })
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      setCampanas((prev) => prev.map((c) => (c.id === id ? json.data : c)))
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Error')
    } finally {
      setActionLoading(null)
    }
  }

  function resetForm() {
    setTitulo('')
    setMensaje('')
    setSegment('all')
    setProgramada('')
    setFormError('')
  }

  const stats = useMemo(() => ({
    total:     campanas.length,
    borradores: campanas.filter((c) => c.status === 'draft').length,
    enviadas:  campanas.filter((c) => c.status === 'sent').length,
    programadas: campanas.filter((c) => c.status === 'scheduled').length,
  }), [campanas])

  const filtradas = useMemo(() =>
    filterStatus === 'todas' ? campanas : campanas.filter((c) => c.status === filterStatus),
  [campanas, filterStatus])

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="stagger-1 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-text-primary tracking-tight">Campañas</h1>
          <p className="text-text-secondary mt-1.5 text-sm">Mensajes masivos de WhatsApp a tus contactos</p>
        </div>
        <Button onClick={() => setShowModal(true)} className="shrink-0">
          <Plus className="h-4 w-4" />
          Nueva campaña
        </Button>
      </div>

      {/* Stats */}
      {!loading && campanas.length > 0 && (
        <div className="stagger-2 grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard icon={Megaphone}    label="Total"       value={stats.total} />
          <StatCard icon={CheckCircle2} label="Enviadas"    value={stats.enviadas} />
          <StatCard icon={Clock}        label="Programadas" value={stats.programadas} />
          <StatCard icon={FileText}     label="Borradores"  value={stats.borradores} />
        </div>
      )}

      {/* Status filter */}
      <div className="stagger-3 flex flex-wrap gap-1.5">
        {(['todas', 'draft', 'scheduled', 'sent', 'cancelled'] as const).map((s) => {
          const active = filterStatus === s
          const meta = s !== 'todas' ? STATUS_META[s] : null
          return (
            <button
              key={s}
              onClick={() => setFilterStatus(s)}
              className={[
                'px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-150 flex items-center gap-1.5',
                active
                  ? (meta ? meta.cls : 'bg-accent text-accent-foreground border-accent')
                  : 'bg-card-bg text-text-secondary border-border hover:border-border-light',
              ].join(' ')}
            >
              {meta && <span className={['h-1.5 w-1.5 rounded-full', meta.dot].join(' ')} />}
              {meta ? meta.label : 'Todas'}
              <span className="tabular-nums opacity-70">
                {s === 'todas' ? campanas.length : campanas.filter((c) => c.status === s).length}
              </span>
            </button>
          )
        })}
      </div>

      {/* List */}
      <div className="stagger-4 rounded-xl border border-border bg-card-bg overflow-hidden">
        <div className="px-5 py-3.5 border-b border-border flex items-center justify-between">
          <p className="text-sm font-medium text-text-primary">Campañas</p>
          <p className="text-xs text-text-muted">{filtradas.length} resultado{filtradas.length !== 1 ? 's' : ''}</p>
        </div>

        {loading ? (
          <div className="divide-y divide-border">
            {[1, 2, 3].map((i) => (
              <div key={i} className="px-5 py-4 flex gap-4 animate-pulse">
                <div className="h-9 w-9 rounded-lg bg-surface shrink-0" />
                <div className="flex-1 space-y-2 py-1">
                  <div className="h-3.5 w-48 rounded bg-surface" />
                  <div className="h-3 w-64 rounded bg-surface" />
                </div>
              </div>
            ))}
          </div>
        ) : filtradas.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-14 text-center">
            <Megaphone className="h-10 w-10 text-text-muted mb-3" />
            <p className="text-text-secondary text-sm font-medium">
              {filterStatus === 'todas' ? 'Sin campañas aún' : 'Sin campañas con este estado'}
            </p>
            <p className="text-text-muted text-xs mt-1">
              {filterStatus === 'todas' && 'Crea tu primera campaña para enviar mensajes masivos'}
            </p>
            {filterStatus === 'todas' && (
              <Button size="sm" className="mt-4" onClick={() => setShowModal(true)}>
                <Plus className="h-3.5 w-3.5" />
                Crear campaña
              </Button>
            )}
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {filtradas.map((c) => {
              const meta = STATUS_META[c.status]
              const isLaunching = actionLoading === c.id + 'launch'
              const isCancelling = actionLoading === c.id + 'cancel'
              return (
                <li key={c.id} className="px-5 py-4 flex items-start gap-4 group hover:bg-surface/30 transition-colors duration-150">
                  <div className="h-9 w-9 rounded-lg bg-surface border border-border flex items-center justify-center shrink-0">
                    <meta.icon className="h-4 w-4 text-text-muted" />
                  </div>

                  <div className="flex-1 min-w-0 space-y-1">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <p className="font-semibold text-text-primary text-sm truncate">{c.title}</p>
                      <StatusBadge status={c.status} />
                    </div>
                    <p className="text-xs text-text-secondary line-clamp-2 leading-relaxed">{c.message}</p>
                    <div className="flex flex-wrap gap-3 pt-0.5">
                      <span className="inline-flex items-center gap-1 text-xs text-text-muted">
                        <Users className="h-3 w-3" />
                        {SEGMENT_LABELS[c.target_segment as Segment] || c.target_segment}
                      </span>
                      {c.recipients_count != null && c.recipients_count > 0 && (
                        <span className="inline-flex items-center gap-1 text-xs text-text-muted">
                          <MessageCircle className="h-3 w-3" />
                          {c.recipients_count} destinatarios
                        </span>
                      )}
                      <span className="text-xs text-text-muted">{formatDate(c.created_at)}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                    {c.status === 'draft' && (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => patchCampana(c.id, 'launch')}
                          disabled={isLaunching}
                          className="text-xs"
                        >
                          {isLaunching ? (
                            <span className="h-3 w-3 rounded-full border border-border border-t-accent animate-spin" />
                          ) : (
                            <Send className="h-3 w-3" />
                          )}
                          Lanzar
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => patchCampana(c.id, 'cancel')}
                          disabled={isCancelling}
                          className="text-xs text-error hover:text-error hover:border-error/30"
                        >
                          <Ban className="h-3 w-3" />
                        </Button>
                      </>
                    )}
                    {c.status === 'scheduled' && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => patchCampana(c.id, 'cancel')}
                        disabled={isCancelling}
                        className="text-xs text-error hover:text-error hover:border-error/30"
                      >
                        {isCancelling ? (
                          <span className="h-3 w-3 rounded-full border border-border border-t-error animate-spin" />
                        ) : (
                          <Ban className="h-3 w-3" />
                        )}
                        Cancelar
                      </Button>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      {/* Create modal */}
      {showModal && (
        <>
          <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" onClick={() => { setShowModal(false); resetForm() }} />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
              className="w-full max-w-lg glass rounded-2xl shadow-2xl flex flex-col"
              style={{ animation: 'fadeInUp 200ms cubic-bezier(0.23,1,0.32,1) both' }}
            >
              <style>{`
                @keyframes fadeInUp {
                  from { opacity:0; transform:translateY(12px) scale(0.98); }
                  to   { opacity:1; transform:translateY(0) scale(1); }
                }
              `}</style>

              <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                <h2 className="text-base font-semibold text-text-primary">Nueva campaña</h2>
                <button
                  onClick={() => { setShowModal(false); resetForm() }}
                  className="h-8 w-8 flex items-center justify-center rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface transition-all duration-150 cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="px-6 py-5 space-y-4">
                {/* Title */}
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-text-secondary">Título de la campaña</label>
                  <Input
                    placeholder="Ej: Promoción mayo 2026"
                    value={titulo}
                    onChange={(e) => setTitulo(e.target.value)}
                  />
                </div>

                {/* Segment */}
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-text-secondary">Audiencia</label>
                  <div className="grid grid-cols-2 gap-2">
                    {(Object.entries(SEGMENT_LABELS) as [Segment, string][]).map(([val, label]) => (
                      <button
                        key={val}
                        type="button"
                        onClick={() => setSegment(val)}
                        className={[
                          'px-3 py-2.5 rounded-lg text-left text-xs font-medium border transition-all duration-150',
                          segment === val
                            ? 'bg-accent/10 text-accent border-accent/30'
                            : 'bg-surface text-text-secondary border-border hover:border-border-light',
                        ].join(' ')}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Message */}
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-text-secondary">
                    Mensaje
                    <span className="ml-2 text-text-muted font-normal">{mensaje.length}/1000</span>
                  </label>
                  <textarea
                    rows={4}
                    maxLength={1000}
                    placeholder="Hola 👋 Tenemos una oferta especial para ti..."
                    value={mensaje}
                    onChange={(e) => setMensaje(e.target.value)}
                    className="w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-text-primary placeholder:text-text-muted resize-none focus:outline-none focus:ring-1 focus:ring-accent/50 focus:border-accent/50 transition-colors duration-150"
                  />
                </div>

                {/* Schedule (optional) */}
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-text-secondary">
                    Programar para <span className="text-text-muted font-normal">(opcional — vacío = inmediato)</span>
                  </label>
                  <Input
                    type="datetime-local"
                    value={programada}
                    onChange={(e) => setProgramada(e.target.value)}
                    min={new Date().toISOString().slice(0, 16)}
                  />
                </div>

                {formError && (
                  <p className="text-xs text-error bg-error/8 border border-error/20 rounded-lg px-3 py-2">{formError}</p>
                )}
              </div>

              <div className="px-6 pb-5 flex gap-3 justify-end">
                <Button variant="outline" onClick={() => { setShowModal(false); resetForm() }} disabled={creating}>
                  Cancelar
                </Button>
                <Button onClick={createCampana} disabled={creating}>
                  {creating ? (
                    <span className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                  ) : (
                    <Plus className="h-4 w-4" />
                  )}
                  Crear borrador
                </Button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
