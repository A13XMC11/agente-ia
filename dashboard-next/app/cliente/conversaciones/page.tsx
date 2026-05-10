'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { MessageSquare } from 'lucide-react'
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

export default function ConversacionesPage() {
  const [conversaciones, setConversaciones] = useState<Conversacion[]>([])
  const [filtradas, setFiltradas] = useState<Conversacion[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Conversaciones</h1>
        <p className="text-text-secondary mt-2">Monitorea y gestiona todas las conversaciones con tus clientes</p>
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
          <CardTitle>Conversaciones Activas</CardTitle>
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
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Usuario</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Canal</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Último Mensaje</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Fecha</th>
                    <th className="text-left py-3 px-4 font-semibold text-text-primary">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {filtradas.map((conv) => (
                    <tr key={conv.id} className="border-b hover:bg-surface">
                      <td className="py-3 px-4 text-text-primary">{conv.usuario_nombre || conv.usuario_id}</td>
                      <td className="py-3 px-4 text-text-secondary capitalize">{conv.canal}</td>
                      <td className="py-3 px-4 text-text-secondary max-w-xs truncate">{conv.ultimo_mensaje}</td>
                      <td className="py-3 px-4 text-text-muted text-xs">{formatDate(conv.fecha_ultimo_mensaje)}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getEstadoBg(conv.estado)}`}>
                          {conv.estado}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
