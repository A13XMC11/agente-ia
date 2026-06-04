'use client'

import { Input } from '@/components/ui/input'
import { MessageSquare, ArrowLeft, Search, Phone } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

interface Conversacion {
  id: string
  usuario_id: string
  usuario_nombre?: string
  canal: string
  ultimo_mensaje: string
  fecha_ultimo_mensaje: string
  estado: 'activa' | 'cerrada' | 'esperando'
}

interface Mensaje {
  id: string
  conversacion_id: string
  sender_id: string
  sender_type: 'user' | 'agent' | 'admin'
  contenido: string
  tipo: 'text' | 'image' | 'video' | 'document' | 'audio'
  created_at: string
}

interface ConversacionDetalle {
  conversation: Conversacion & { usuario_nombre: string; usuario_telefono: string }
  messages: Mensaje[]
}

/* ── Palette ────────────────────────────────────── */
const CANAL_STYLES: Record<string, { label: string; color: string; bg: string; border: string }> = {
  whatsapp: { label: 'WhatsApp', color: '#22D3A0', bg: 'rgba(34,211,160,0.10)', border: 'rgba(34,211,160,0.20)' },
  instagram: { label: 'Instagram', color: '#818CF8', bg: 'rgba(129,140,248,0.10)', border: 'rgba(129,140,248,0.20)' },
  facebook: { label: 'Facebook', color: '#60A5FA', bg: 'rgba(96,165,250,0.10)', border: 'rgba(96,165,250,0.20)' },
  email: { label: 'Email', color: '#FBBF24', bg: 'rgba(251,191,36,0.10)', border: 'rgba(251,191,36,0.20)' },
}

const ESTADO_STYLES: Record<string, { label: string; color: string; bg: string }> = {
  activa:    { label: 'activa',    color: '#22D3A0', bg: 'rgba(34,211,160,0.10)' },
  esperando: { label: 'esperando', color: '#FBBF24', bg: 'rgba(251,191,36,0.10)' },
  cerrada:   { label: 'cerrada',   color: 'rgba(255,255,255,0.30)', bg: 'rgba(255,255,255,0.05)' },
}

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

function getInitials(name: string): string {
  return name.split(' ').slice(0, 2).map((n) => n[0]?.toUpperCase() ?? '').join('')
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  const now = new Date()
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
  }
  const diffDays = Math.floor((now.getTime() - date.getTime()) / 86400000)
  if (diffDays === 1) return 'ayer'
  if (diffDays < 7) return `${diffDays}d`
  return date.toLocaleDateString('es-MX', { day: 'numeric', month: 'short' })
}

function formatTime(dateString: string) {
  return new Date(dateString).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
}

function getDisplayName(conv: Pick<Conversacion, 'usuario_nombre'>) {
  return conv.usuario_nombre?.trim() || 'Cliente'
}

/* ── Avatar ─────────────────────────────────────── */
function ConvAvatar({ seed, name, size = 'md' }: { seed: string; name: string; size?: 'sm' | 'md' }) {
  const { bg, color, border } = pickPalette(seed)
  const sz = size === 'sm' ? 'h-8 w-8 text-[11px]' : 'h-10 w-10 text-xs'
  return (
    <div
      className={[sz, 'rounded-full flex items-center justify-center font-bold shrink-0 select-none'].join(' ')}
      style={{ background: bg, color, border: `1px solid ${border}` }}
    >
      {getInitials(name)}
    </div>
  )
}

/* ── Canal badge ────────────────────────────────── */
function CanalBadge({ canal }: { canal: string }) {
  const s = CANAL_STYLES[canal] ?? { label: canal, color: 'rgba(255,255,255,0.4)', bg: 'rgba(255,255,255,0.06)', border: 'rgba(255,255,255,0.10)' }
  return (
    <span
      className="px-2 py-0.5 rounded-md text-[10px] font-semibold"
      style={{ color: s.color, background: s.bg, border: `1px solid ${s.border}` }}
    >
      {s.label}
    </span>
  )
}

/* ── Estado dot ─────────────────────────────────── */
function EstadoDot({ estado }: { estado: string }) {
  const s = ESTADO_STYLES[estado] ?? ESTADO_STYLES.cerrada
  return (
    <span className="flex items-center gap-1 text-[10px] font-medium" style={{ color: s.color }}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: s.color }} />
      {s.label}
    </span>
  )
}

/* ── Skeleton row ───────────────────────────────── */
function SkeletonRow() {
  return (
    <div className="flex items-center gap-3.5 px-5 py-4">
      <div className="skeleton h-10 w-10 rounded-full shrink-0" />
      <div className="flex-1 space-y-2">
        <div className="skeleton h-3 w-32 rounded" />
        <div className="skeleton h-2.5 w-48 rounded" />
        <div className="skeleton h-2 w-20 rounded mt-1" />
      </div>
      <div className="skeleton h-4 w-14 rounded" />
    </div>
  )
}

/* ── Page ───────────────────────────────────────── */
export default function ConversacionesPage() {
  const [conversaciones, setConversaciones] = useState<Conversacion[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [chatData, setChatData] = useState<ConversacionDetalle | null>(null)
  const [chatLoading, setChatLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const loadConversaciones = useCallback(async () => {
    try {
      const res = await fetch('/api/cliente/conversaciones')
      if (!res.ok) throw new Error('Failed')
      const data = await res.json()
      setConversaciones(data.data || [])
    } catch {
      // silently handled — empty state shown
    } finally {
      setLoading(false)
    }
  }, [])

  async function loadChatData(convId: string) {
    setChatLoading(true)
    try {
      const res = await fetch(`/api/cliente/conversaciones/${convId}`)
      if (!res.ok) throw new Error('Failed')
      const data = await res.json()
      setChatData(data.data)
    } catch {
      setChatData(null)
    } finally {
      setChatLoading(false)
    }
  }

  useEffect(() => {
    loadConversaciones()
  }, [loadConversaciones])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatData?.messages])

  const filtradas = useMemo(() => {
    if (!search.trim()) return conversaciones
    const q = search.toLowerCase()
    return conversaciones.filter(
      (c) =>
        c.usuario_id.toLowerCase().includes(q) ||
        c.usuario_nombre?.toLowerCase().includes(q) ||
        c.ultimo_mensaje?.toLowerCase().includes(q),
    )
  }, [search, conversaciones])

  /* ── Chat view ──────────────────────────────── */
  if (selectedId && (chatData || chatLoading)) {
    const conv = chatData?.conversation
    return (
      <div className="flex flex-col h-[calc(100dvh-4rem)] -mt-5 md:-mt-8 -mx-5 md:-mx-8 pt-5 md:pt-8 px-5 md:px-8"
           style={{ animation: 'scale-in 220ms cubic-bezier(0.23,1,0.32,1) both' }}>
        {/* Chat header */}
        <div
          className="flex items-center gap-3 pb-4 border-b shrink-0"
          style={{ borderColor: 'rgba(255,255,255,0.07)' }}
        >
          <button
            onClick={() => { setSelectedId(null); setChatData(null) }}
            className="h-9 w-9 flex items-center justify-center rounded-xl text-white/50 hover:text-white/80 hover:bg-white/5 transition-all duration-150 active:scale-[0.96] cursor-pointer shrink-0"
            aria-label="Volver"
          >
            <ArrowLeft className="h-5 w-5" strokeWidth={1.75} />
          </button>

          {conv ? (
            <>
              <ConvAvatar seed={conv.usuario_id} name={getDisplayName(conv)} size="sm" />
              <div className="min-w-0 flex-1">
                <p className="font-semibold text-white/85 text-sm truncate leading-none">
                  {getDisplayName(conv)}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  {conv.usuario_telefono && (
                    <span className="text-[11px] text-white/30 flex items-center gap-1 font-mono">
                      <Phone className="h-3 w-3" strokeWidth={1.5} />
                      {conv.usuario_telefono}
                    </span>
                  )}
                </div>
              </div>
              <CanalBadge canal={conv.canal} />
            </>
          ) : (
            <div className="flex-1 flex items-center gap-3">
              <div className="skeleton h-8 w-8 rounded-full" />
              <div className="skeleton h-4 w-32 rounded" />
            </div>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto py-5 space-y-2.5 min-h-0">
          {chatLoading ? (
            <div className="flex items-center justify-center h-full">
              <span
                className="h-6 w-6 rounded-full border-2 animate-spin"
                style={{ borderColor: 'rgba(255,255,255,0.08)', borderTopColor: 'var(--accent)' }}
              />
            </div>
          ) : !chatData || chatData.messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
              <div
                className="h-12 w-12 rounded-2xl flex items-center justify-center"
                style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
              >
                <MessageSquare className="h-5 w-5 text-white/20" strokeWidth={1.5} />
              </div>
              <p className="text-white/30 text-sm">Sin mensajes en esta conversación</p>
            </div>
          ) : (
            chatData.messages.map((msg) => {
              const isUser = msg.sender_type === 'user'
              return (
                <div key={msg.id} className={['flex', isUser ? 'justify-start' : 'justify-end'].join(' ')}>
                  <div
                    className="max-w-[75%] px-3.5 py-2.5 rounded-2xl"
                    style={isUser ? {
                      background: 'rgba(255,255,255,0.06)',
                      border: '1px solid rgba(255,255,255,0.07)',
                      borderBottomLeftRadius: '4px',
                    } : {
                      background: 'var(--accent)',
                      color: '#060D13',
                      borderBottomRightRadius: '4px',
                    }}
                  >
                    <p className="text-sm leading-relaxed break-words" style={isUser ? { color: 'rgba(255,255,255,0.80)' } : {}}>
                      {msg.contenido}
                    </p>
                    <p
                      className="text-[10px] mt-1.5 select-none"
                      style={{ color: isUser ? 'rgba(255,255,255,0.25)' : 'rgba(6,13,19,0.55)' }}
                    >
                      {formatTime(msg.created_at)}
                    </p>
                  </div>
                </div>
              )
            })
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
    )
  }

  /* ── List view ──────────────────────────────── */
  return (
    <div className="space-y-5">
      <div className="stagger-1">
        <h1 className="text-2xl font-bold text-white/88 tracking-tight">Conversaciones</h1>
        <p className="text-white/35 mt-1 text-sm">
          Monitorea todas las interacciones con tu agente
        </p>
      </div>

      {/* Search */}
      <div className="stagger-2 relative">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-white/25 pointer-events-none" strokeWidth={1.75} />
        <Input
          placeholder="Buscar por nombre o mensaje..."
          className="pl-10"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* List container */}
      <div
        className="stagger-3 rounded-2xl overflow-hidden"
        style={{ border: '1px solid rgba(255,255,255,0.06)', background: 'rgba(9,21,33,0.5)' }}
      >
        <div
          className="px-5 py-3 flex items-center justify-between border-b"
          style={{ borderColor: 'rgba(255,255,255,0.05)' }}
        >
          <p className="text-sm font-medium text-white/55">Conversaciones</p>
          <p className="text-xs font-mono text-white/28">{filtradas.length}</p>
        </div>

        {loading ? (
          <div className="divide-y" style={{ '--tw-divide-opacity': 1 } as React.CSSProperties}>
            {[1, 2, 3, 4].map((i) => <SkeletonRow key={i} />)}
          </div>
        ) : filtradas.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
            <div
              className="h-12 w-12 rounded-2xl flex items-center justify-center"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
            >
              <MessageSquare className="h-5 w-5 text-white/20" strokeWidth={1.5} />
            </div>
            <div>
              <p className="text-white/45 text-sm font-medium">
                {search ? 'Sin resultados' : 'Sin conversaciones'}
              </p>
              <p className="text-white/22 text-xs mt-0.5">
                {search ? 'Prueba con otro término' : 'Aparecerán cuando usuarios contacten al agente'}
              </p>
            </div>
          </div>
        ) : (
          <ul>
            {filtradas.map((conv, idx) => {
              const name = getDisplayName(conv)
              return (
                <li
                  key={conv.id}
                  style={{
                    borderTop: idx > 0 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                    animation: `fadeInUp 280ms cubic-bezier(0.23,1,0.32,1) ${idx * 30}ms both`,
                  }}
                >
                  <button
                    onClick={() => { setSelectedId(conv.id); loadChatData(conv.id) }}
                    className="w-full text-left px-5 py-4 transition-colors duration-150 group cursor-pointer"
                    style={{ background: 'transparent' }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,0.02)' }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'transparent' }}
                  >
                    <div className="flex items-start gap-3.5">
                      <ConvAvatar seed={conv.usuario_id} name={name} />
                      <div className="flex-1 min-w-0 pt-0.5">
                        <div className="flex items-center gap-2 mb-0.5">
                          <p className="font-semibold text-white/78 text-sm truncate group-hover:text-white/92 transition-colors duration-150">
                            {name}
                          </p>
                        </div>
                        <p className="text-xs text-white/30 truncate max-w-xs">
                          {conv.ultimo_mensaje || 'Sin mensajes'}
                        </p>
                        <div className="flex items-center gap-2 mt-1.5">
                          <CanalBadge canal={conv.canal} />
                          <EstadoDot estado={conv.estado} />
                        </div>
                      </div>
                      <time className="text-[11px] text-white/25 shrink-0 pt-0.5 font-mono">
                        {formatDate(conv.fecha_ultimo_mensaje)}
                      </time>
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
