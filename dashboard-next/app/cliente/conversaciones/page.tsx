'use client'

import { Input } from '@/components/ui/input'
import { MessageSquare, ArrowLeft, Search } from 'lucide-react'
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

const CANAL_STYLES: Record<string, string> = {
  whatsapp: 'bg-success/10 text-success border-success/20',
  instagram: 'bg-accent-indigo/10 text-accent-indigo border-accent-indigo/20',
  facebook: 'bg-info/10 text-info border-info/20',
  email: 'bg-warning/10 text-warning border-warning/20',
}

const ESTADO_STYLES: Record<string, string> = {
  activa: 'bg-success/10 text-success',
  esperando: 'bg-warning/10 text-warning',
  cerrada: 'bg-surface text-text-muted',
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  const now = new Date()
  const isToday = date.toDateString() === now.toDateString()
  if (isToday) {
    return date.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString('es-MX', { day: 'numeric', month: 'short' })
}

function formatTime(dateString: string) {
  return new Date(dateString).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
}

function getConversationDisplayName(conversation: Pick<Conversacion, 'usuario_nombre'>) {
  return conversation.usuario_nombre?.trim() || 'Cliente sin nombre'
}

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
    } finally {
      setChatLoading(false)
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadConversaciones()
  }, [loadConversaciones])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatData?.messages])

  const filtradas = useMemo(() => {
    if (!search.trim()) return conversaciones
    const q = search.toLowerCase()
    return conversaciones.filter((c) =>
        c.usuario_id.toLowerCase().includes(q) ||
        c.usuario_nombre?.toLowerCase().includes(q) ||
        c.ultimo_mensaje.toLowerCase().includes(q),
    )
  }, [search, conversaciones])

  /* ── Chat view ────────────────────────────────── */
  if (selectedId && chatData) {
    return (
      <div className="flex flex-col h-[calc(100vh-4rem)] -mt-8 -mx-4 md:-mx-8 pt-8 px-4 md:px-8">
        {/* Chat header */}
        <div className="flex items-center gap-3 pb-4 border-b border-border">
          <button
            onClick={() => { setSelectedId(null); setChatData(null) }}
            className="h-9 w-9 flex items-center justify-center rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface transition-all duration-150 active:scale-[0.97] cursor-pointer shrink-0"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-text-primary truncate">
              {getConversationDisplayName(chatData.conversation)}
            </p>
            <p className="text-xs text-text-muted truncate">
              {chatData.conversation.canal.toUpperCase()} · {chatData.conversation.usuario_telefono}
            </p>
          </div>
          <span className={['px-2 py-0.5 rounded-md text-xs font-medium border', CANAL_STYLES[chatData.conversation.canal] ?? ''].join(' ')}>
            {chatData.conversation.canal}
          </span>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto py-6 space-y-3 min-h-0">
          {chatLoading ? (
            <div className="flex items-center justify-center h-full">
              <span className="h-6 w-6 rounded-full border-2 border-border border-t-accent animate-spin" />
            </div>
          ) : chatData.messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
              <MessageSquare className="h-10 w-10 text-text-muted" />
              <p className="text-text-secondary text-sm">Sin mensajes en esta conversación</p>
            </div>
          ) : (
            chatData.messages.map((msg) => {
              const isUser = msg.sender_type === 'user'
              return (
                <div key={msg.id} className={['flex', isUser ? 'justify-start' : 'justify-end'].join(' ')}>
                  <div
                    className={[
                      'max-w-xs lg:max-w-md px-4 py-2.5 rounded-2xl',
                      isUser
                        ? 'bg-surface text-text-primary rounded-bl-sm'
                        : 'bg-accent text-background rounded-br-sm',
                    ].join(' ')}
                  >
                    <p className="text-sm leading-relaxed wrap-break-word">{msg.contenido}</p>
                    <p className={['text-xs mt-1.5 select-none', isUser ? 'text-text-muted' : 'text-background/60'].join(' ')}>
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

  /* ── List view ────────────────────────────────── */
  return (
    <div className="space-y-5">
      <div className="stagger-1">
        <h1 className="text-3xl font-bold text-text-primary tracking-tight">Conversaciones</h1>
        <p className="text-text-secondary mt-1.5 text-sm">
          Monitorea todas las conversaciones con tus clientes
        </p>
      </div>

      {/* Search */}
      <div className="stagger-2 relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted pointer-events-none" />
        <Input
          placeholder="Buscar por usuario o mensaje..."
          className="pl-9"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* List */}
      <div className="stagger-3 rounded-xl border border-border bg-card-bg overflow-hidden">
        <div className="px-5 py-3.5 border-b border-border flex items-center justify-between">
          <p className="text-sm font-medium text-text-primary">Conversaciones</p>
          <p className="text-xs text-text-muted">{filtradas.length} resultados</p>
        </div>

        {loading ? (
          <div className="divide-y divide-border">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="px-5 py-4 flex gap-4 animate-pulse">
                <div className="flex-1 space-y-2">
                  <div className="h-3.5 w-32 rounded bg-surface" />
                  <div className="h-3 w-48 rounded bg-surface" />
                </div>
                <div className="h-5 w-16 rounded bg-surface" />
              </div>
            ))}
          </div>
        ) : filtradas.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-14 text-center">
            <MessageSquare className="h-10 w-10 text-text-muted mb-3" />
            <p className="text-text-secondary text-sm font-medium">No hay conversaciones</p>
            <p className="text-text-muted text-xs mt-1">
              Aparecerán aquí cuando los usuarios contacten a tu agente
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {filtradas.map((conv) => (
              <li key={conv.id}>
                <button
                  onClick={() => { setSelectedId(conv.id); loadChatData(conv.id) }}
                  className="w-full text-left px-5 py-4 hover:bg-surface/40 transition-colors duration-150 cursor-pointer group"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-text-primary text-sm group-hover:text-accent transition-colors duration-150">
                        {getConversationDisplayName(conv)}
                      </p>
                      <p className="text-xs text-text-muted mt-0.5 truncate max-w-xs">
                        {conv.ultimo_mensaje}
                      </p>
                      <div className="flex items-center gap-2 mt-2">
                        <span className={['px-2 py-0.5 rounded-md text-xs font-medium border', CANAL_STYLES[conv.canal] ?? 'bg-surface text-text-muted border-border'].join(' ')}>
                          {conv.canal}
                        </span>
                        <span className={['px-2 py-0.5 rounded-md text-xs font-medium', ESTADO_STYLES[conv.estado] ?? ''].join(' ')}>
                          {conv.estado}
                        </span>
                      </div>
                    </div>
                    <time className="text-xs text-text-muted shrink-0 mt-0.5">
                      {formatDate(conv.fecha_ultimo_mensaje)}
                    </time>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
