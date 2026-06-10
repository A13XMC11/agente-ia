'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  Bell,
  Flame,
  Snowflake,
  RefreshCw,
  ShoppingBag,
  CalendarCheck,
  Clock,
  Search,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { Input } from '@/components/ui/input'
import { formatTimestamp } from '@/lib/date-format'

/* ── Types ─────────────────────────────────────── */
type SeguimientoTipo =
  | 'seguimiento_frio'
  | 'seguimiento_caliente'
  | 'seguimiento_post_venta'
  | 'reactivacion'

interface Seguimiento {
  id: string
  tipo: SeguimientoTipo
  referencia_id: string
  mensaje: string
  canal_envio: string
  created_at: string
}

interface Stats {
  total: number
  seguimiento_frio: number
  seguimiento_caliente: number
  seguimiento_post_venta: number
  reactivacion: number
  cita_24h: number
  cita_1h: number
}

/* ── Metadata ──────────────────────────────────── */
const TIPO_META: Record<
  SeguimientoTipo,
  { label: string; icon: React.ElementType; color: string; bg: string; border: string; dot: string }
> = {
  seguimiento_frio: {
    label: 'Lead Frío',
    icon: Snowflake,
    color: '#60A5FA',
    bg: 'rgba(96,165,250,0.10)',
    border: 'rgba(96,165,250,0.22)',
    dot: '#60A5FA',
  },
  seguimiento_caliente: {
    label: 'Lead Caliente',
    icon: Flame,
    color: '#FB923C',
    bg: 'rgba(251,146,60,0.10)',
    border: 'rgba(251,146,60,0.22)',
    dot: '#FB923C',
  },
  seguimiento_post_venta: {
    label: 'Post-venta',
    icon: ShoppingBag,
    color: '#34D399',
    bg: 'rgba(52,211,153,0.10)',
    border: 'rgba(52,211,153,0.22)',
    dot: '#34D399',
  },
  reactivacion: {
    label: 'Reactivación',
    icon: RefreshCw,
    color: '#A78BFA',
    bg: 'rgba(167,139,250,0.10)',
    border: 'rgba(167,139,250,0.22)',
    dot: '#A78BFA',
  },
}

const TIPO_FILTERS: Array<{ value: SeguimientoTipo | 'todos'; label: string }> = [
  { value: 'todos', label: 'Todos' },
  { value: 'seguimiento_frio', label: 'Fríos' },
  { value: 'seguimiento_caliente', label: 'Calientes' },
  { value: 'seguimiento_post_venta', label: 'Post-venta' },
  { value: 'reactivacion', label: 'Reactivación' },
]

/* ── Sub-components ───────────────────────────── */
interface StatCardProps {
  icon: React.ElementType
  label: string
  value: number
  color?: string
  bg?: string
  border?: string
}

function StatCard({ icon: Icon, label, value, color, bg, border }: StatCardProps) {
  return (
    <div
      className="rounded-xl border px-4 py-3.5 flex items-center gap-3"
      style={{
        background: bg ?? 'var(--card-bg)',
        borderColor: border ?? 'var(--border)',
      }}
    >
      <div
        className="h-8 w-8 rounded-lg flex items-center justify-center shrink-0"
        style={{ background: bg ?? 'var(--surface)', border: `1px solid ${border ?? 'var(--border)'}` }}
      >
        <Icon className="h-4 w-4" style={{ color: color ?? 'var(--text-muted)' }} strokeWidth={1.75} />
      </div>
      <div>
        <p className="text-xs text-text-muted leading-none mb-1">{label}</p>
        <p className="text-lg font-bold text-text-primary tabular-nums leading-tight">{value}</p>
      </div>
    </div>
  )
}

function TipoBadge({ tipo }: { tipo: SeguimientoTipo }) {
  const meta = TIPO_META[tipo]
  const Icon = meta.icon
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-medium border"
      style={{ color: meta.color, background: meta.bg, borderColor: meta.border }}
    >
      <Icon className="h-3 w-3 shrink-0" strokeWidth={1.75} />
      {meta.label}
    </span>
  )
}

function MensajeExpandible({ texto }: { texto: string }) {
  const [expanded, setExpanded] = useState(false)
  const largo = texto.length > 100
  return (
    <div className="text-sm text-text-secondary leading-relaxed">
      {expanded || !largo ? texto : texto.slice(0, 100) + '…'}
      {largo && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="ml-1.5 inline-flex items-center gap-0.5 text-xs text-accent hover:text-accent/80 transition-colors"
        >
          {expanded ? (
            <>menos <ChevronUp className="h-3 w-3" /></>
          ) : (
            <>más <ChevronDown className="h-3 w-3" /></>
          )}
        </button>
      )}
    </div>
  )
}

/* ── Page ──────────────────────────────────────── */
export default function SeguimientosPage() {
  const [seguimientos, setSeguimientos] = useState<Seguimiento[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [filtroTipo, setFiltroTipo] = useState<SeguimientoTipo | 'todos'>('todos')
  const [busqueda, setBusqueda] = useState('')

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetch('/api/cliente/seguimientos')
        const json = await res.json()
        if (json.success) {
          setSeguimientos(json.data ?? [])
          setStats(json.stats ?? null)
        }
      } catch (err) {
        console.error('Error loading seguimientos:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const filtered = useMemo(() => {
    return seguimientos.filter((s) => {
      if (filtroTipo !== 'todos' && s.tipo !== filtroTipo) return false
      if (busqueda.trim()) {
        const q = busqueda.toLowerCase()
        return s.mensaje.toLowerCase().includes(q)
      }
      return true
    })
  }, [seguimientos, filtroTipo, busqueda])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-text-primary">Seguimientos Automáticos</h1>
        <p className="text-sm text-text-muted mt-1">
          Historial de mensajes enviados automáticamente por el agente a tus leads y clientes.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3">
        <StatCard icon={Bell} label="Total enviados" value={stats?.total ?? 0} />
        <StatCard
          icon={Snowflake}
          label="Leads fríos"
          value={stats?.seguimiento_frio ?? 0}
          color={TIPO_META.seguimiento_frio.color}
          bg={TIPO_META.seguimiento_frio.bg}
          border={TIPO_META.seguimiento_frio.border}
        />
        <StatCard
          icon={Flame}
          label="Leads calientes"
          value={stats?.seguimiento_caliente ?? 0}
          color={TIPO_META.seguimiento_caliente.color}
          bg={TIPO_META.seguimiento_caliente.bg}
          border={TIPO_META.seguimiento_caliente.border}
        />
        <StatCard
          icon={ShoppingBag}
          label="Post-venta"
          value={stats?.seguimiento_post_venta ?? 0}
          color={TIPO_META.seguimiento_post_venta.color}
          bg={TIPO_META.seguimiento_post_venta.bg}
          border={TIPO_META.seguimiento_post_venta.border}
        />
        <StatCard
          icon={RefreshCw}
          label="Reactivación"
          value={stats?.reactivacion ?? 0}
          color={TIPO_META.reactivacion.color}
          bg={TIPO_META.reactivacion.bg}
          border={TIPO_META.reactivacion.border}
        />
        <StatCard
          icon={CalendarCheck}
          label="Citas 24h"
          value={stats?.cita_24h ?? 0}
          color="#38BDF8"
          bg="rgba(56,189,248,0.10)"
          border="rgba(56,189,248,0.22)"
        />
        <StatCard
          icon={Clock}
          label="Citas 1h"
          value={stats?.cita_1h ?? 0}
          color="#38BDF8"
          bg="rgba(56,189,248,0.08)"
          border="rgba(56,189,248,0.18)"
        />
      </div>

      {/* Filters + search */}
      <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
        <div className="flex flex-wrap gap-1.5">
          {TIPO_FILTERS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setFiltroTipo(value)}
              className={[
                'px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-150',
                filtroTipo === value
                  ? 'bg-accent/10 text-accent border-accent/25'
                  : 'bg-surface text-text-muted border-border hover:text-text-primary hover:bg-white/[0.04]',
              ].join(' ')}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="relative sm:ml-auto sm:w-64">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-text-muted pointer-events-none" />
          <Input
            placeholder="Buscar en mensajes…"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="pl-8 h-8 text-sm bg-surface border-border text-text-primary placeholder:text-text-muted"
          />
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-border overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-text-muted text-sm">
            Cargando seguimientos…
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <div className="h-12 w-12 rounded-xl bg-surface border border-border flex items-center justify-center">
              <Bell className="h-5 w-5 text-text-muted" strokeWidth={1.5} />
            </div>
            <p className="text-sm text-text-muted">
              {seguimientos.length === 0
                ? 'Aún no se han enviado seguimientos automáticos.'
                : 'No hay resultados para este filtro.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface/60">
                  <th className="text-left px-4 py-3 text-xs font-medium text-text-muted w-36">Tipo</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-text-muted">Mensaje enviado</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-text-muted w-36 whitespace-nowrap">
                    Fecha y hora
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((s, i) => (
                  <tr
                    key={s.id}
                    className="border-b border-border/50 last:border-0 transition-colors hover:bg-white/[0.02]"
                    style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.012)' }}
                  >
                    <td className="px-4 py-3 align-top">
                      <TipoBadge tipo={s.tipo} />
                    </td>
                    <td className="px-4 py-3 align-top max-w-xl">
                      <MensajeExpandible texto={s.mensaje} />
                    </td>
                    <td className="px-4 py-3 align-top whitespace-nowrap text-xs text-text-muted">
                      {formatTimestamp(s.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {filtered.length > 0 && (
        <p className="text-xs text-text-muted text-right">
          Mostrando {filtered.length} de {seguimientos.length} seguimientos
        </p>
      )}
    </div>
  )
}
