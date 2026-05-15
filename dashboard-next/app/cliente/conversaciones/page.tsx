'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { MessageSquare, X, ArrowLeft } from 'lucide-react'
import { useState, useEffect } from 'react'

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

export default function ConversacionesPage() {
  const [conversaciones, setConversaciones] = useState<Conversacion[]>([])
  const [filtradas, setFiltradas] = useState<Conversacion[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [chatData, setChatData] = useState<ConversacionDetalle | null>(null)
  const [chatLoading, setChatLoading] = useState(false)

  useEffect(() => {
    loadConversaciones()
  }, [])

  async function loadConversaciones() {
    try {
      const response = await fetch('/api/cliente/conversaciones')
      if (!response.ok) throw new Error('Failed to load')
      const data = await response.json()
      setConversaciones(data.data || [])
      setFiltradas(data.data || [])
    } catch (error) {
      console.error('Error loading conversaciones:', error)
    } finally {
      setLoading(false)
    }
  }

  async function loadChatData(convId: string) {
    setChatLoading(true)
    try {
      const response = await fetch(`/api/cliente/conversaciones/${convId}`)
      if (!response.ok) throw new Error('Failed to load chat')
      const data = await response.json()
      setChatData(data.data)
    } catch (error) {
      console.error('Error loading chat:', error)
    } finally {
      setChatLoading(false)
    }
  }

  const handleSelectConversacion = (convId: string) => {
    setSelectedId(convId)
    loadChatData(convId)
  }

  useEffect(() => {
    if (!search.trim()) {
      setFiltradas(conversaciones)
      return
    }

    const query = search.toLowerCase()
    setFiltradas(
      conversaciones.filter(c =>
        c.usuario_id.toLowerCase().includes(query) ||
        c.usuario_nombre?.toLowerCase().includes(query) ||
        c.ultimo_mensaje.toLowerCase().includes(query)
      )
    )
  }, [search, conversaciones])

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-CO', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatMessageTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString('es-CO', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getEstadoBg = (estado: string) => {
    switch (estado) {
      case 'activa':
        return 'bg-success/10 text-success'
      case 'esperando':
        return 'bg-warning/10 text-warning'
      default:
        return 'bg-text-muted/10 text-text-muted'
    }
  }

  if (selectedId && chatData) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setSelectedId(null)
              setChatData(null)
            }}
            className="p-2 hover:bg-surface rounded-lg transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-text-secondary" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-text-primary">
              {chatData.conversation.usuario_nombre || chatData.conversation.usuario_id}
            </h1>
            <p className="text-sm text-text-secondary">
              {chatData.conversation.canal.toUpperCase()} • {chatData.conversation.usuario_telefono}
            </p>
          </div>
        </div>

        <Card className="min-h-96 max-h-96 md:max-h-[600px] overflow-hidden flex flex-col">
          <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
            {chatLoading ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-text-secondary">Cargando mensajes...</p>
              </div>
            ) : chatData.messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full">
                <MessageSquare className="h-12 w-12 text-text-muted mb-4" />
                <p className="text-text-secondary">Sin mensajes</p>
              </div>
            ) : (
              chatData.messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.sender_type === 'user' ? 'justify-start' : 'justify-end'}`}
                >
                  <div
                    className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                      msg.sender_type === 'user'
                        ? 'bg-surface text-text-primary rounded-bl-none'
                        : 'bg-accent text-white rounded-br-none'
                    }`}
                  >
                    <p className="break-words text-sm">{msg.contenido}</p>
                    <p className={`text-xs mt-1 ${msg.sender_type === 'user' ? 'text-text-muted' : 'text-white/70'}`}>
                      {formatMessageTime(msg.created_at)}
                    </p>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Conversaciones</h1>
        <p className="text-text-secondary mt-2">Monitorea todas las conversaciones con tus clientes</p>
      </div>

      <div className="flex gap-2">
        <Input
          placeholder="Buscar por usuario o mensaje..."
          className="flex-1"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Conversaciones</CardTitle>
          <CardDescription>{filtradas.length} conversaciones</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-12">
              <p className="text-text-secondary">Cargando...</p>
            </div>
          ) : filtradas.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <MessageSquare className="h-12 w-12 text-text-muted mb-4" />
              <p className="text-text-secondary">No hay conversaciones</p>
              <p className="text-sm text-text-muted mt-2">Las conversaciones aparecerán aquí cuando los usuarios contacten</p>
            </div>
          ) : (
            <div className="space-y-2">
              {filtradas.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => handleSelectConversacion(conv.id)}
                  className="w-full text-left p-4 border rounded-lg hover:bg-surface transition-colors"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <p className="font-medium text-text-primary">{conv.usuario_nombre || conv.usuario_id}</p>
                      <p className="text-sm text-text-secondary mt-1 truncate">{conv.ultimo_mensaje}</p>
                      <div className="flex gap-2 items-center mt-2">
                        <span className="text-xs text-text-muted capitalize">{conv.canal}</span>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getEstadoBg(conv.estado)}`}>
                          {conv.estado}
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-text-muted">{formatDate(conv.fecha_ultimo_mensaje)}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
