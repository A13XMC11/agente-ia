'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { MessageSquare, Users, Calendar, Settings, ArrowLeft } from 'lucide-react'
import Link from 'next/link'

interface Cliente {
  id: string
  nombre: string
  email: string
}

interface Conversacion {
  id: string
  usuario_id: string
  usuario_nombre: string
  ultimo_mensaje: string
  canal: string
  created_at: string
  updated_at: string
}

interface Lead {
  id: string
  usuario_id: string
  usuario_nombre: string
  calificacion: number
  estado: string
  created_at: string
}

interface Cita {
  id: string
  usuario_nombre: string
  fecha: string
  hora: string
  estado: 'confirmada' | 'pendiente' | 'cancelada'
  created_at: string
}

export default function ClientePanelPage() {
  const params = useParams()
  const clienteId = params.id as string

  const [cliente, setCliente] = useState<Cliente | null>(null)
  const [conversaciones, setConversaciones] = useState<Conversacion[]>([])
  const [leads, setLeads] = useState<Lead[]>([])
  const [citas, setCitas] = useState<Cita[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('conversaciones')

  useEffect(() => {
    loadData()
  }, [clienteId])

  async function loadData() {
    try {
      setLoading(true)
      const [clienteRes, conversacionesRes, leadsRes, citasRes] = await Promise.all([
        fetch(`/api/clientes/${clienteId}`),
        fetch(`/api/clientes/${clienteId}/conversaciones`),
        fetch(`/api/clientes/${clienteId}/leads`),
        fetch(`/api/clientes/${clienteId}/citas`),
      ])

      if (clienteRes.ok) {
        const data = await clienteRes.json()
        setCliente(data.data)
      }

      if (conversacionesRes.ok) {
        const data = await conversacionesRes.json()
        setConversaciones(data.data || [])
      }

      if (leadsRes.ok) {
        const data = await leadsRes.json()
        setLeads(data.data || [])
      }

      if (citasRes.ok) {
        const data = await citasRes.json()
        setCitas(data.data || [])
      }
    } catch (error) {
      console.error('Error loading panel data:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-CO')
  }

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString('es-CO', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link href={`/admin/clientes/${clienteId}`}>
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Volver
            </Button>
          </Link>
          <h1 className="text-3xl font-bold text-text-primary">Panel del Cliente</h1>
        </div>
        <Card>
          <CardContent className="pt-6">
            <p className="text-text-secondary">Cargando panel...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!cliente) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-text-primary">Cliente no encontrado</h1>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href={`/admin/clientes/${clienteId}`}>
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Panel de {cliente.nombre}</h1>
          <p className="text-text-secondary mt-1">Acceso administrativo al panel del cliente</p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="conversaciones" className="gap-2">
            <MessageSquare className="h-4 w-4" />
            Conversaciones ({conversaciones.length})
          </TabsTrigger>
          <TabsTrigger value="leads" className="gap-2">
            <Users className="h-4 w-4" />
            Leads ({leads.length})
          </TabsTrigger>
          <TabsTrigger value="citas" className="gap-2">
            <Calendar className="h-4 w-4" />
            Citas ({citas.length})
          </TabsTrigger>
          <TabsTrigger value="configuracion" className="gap-2">
            <Settings className="h-4 w-4" />
            Configuración
          </TabsTrigger>
        </TabsList>

        <TabsContent value="conversaciones" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Conversaciones</CardTitle>
              <CardDescription>Historial de conversaciones con usuarios</CardDescription>
            </CardHeader>
            <CardContent>
              {conversaciones.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-text-secondary">No hay conversaciones aún</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {conversaciones.map((conv) => (
                    <div
                      key={conv.id}
                      className="p-4 border rounded-lg hover:bg-surface/50 transition"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <h3 className="font-medium text-text-primary">{conv.usuario_nombre}</h3>
                          <p className="text-sm text-text-secondary">{conv.canal}</p>
                        </div>
                        <span className="text-xs text-text-muted">{formatDate(conv.created_at)}</span>
                      </div>
                      <p className="text-sm text-text-secondary truncate">{conv.ultimo_mensaje}</p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="leads" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Leads</CardTitle>
              <CardDescription>Clientes potenciales y su calificación</CardDescription>
            </CardHeader>
            <CardContent>
              {leads.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-text-secondary">No hay leads aún</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-3 px-4 font-semibold text-text-primary">
                          Usuario
                        </th>
                        <th className="text-left py-3 px-4 font-semibold text-text-primary">
                          Calificación
                        </th>
                        <th className="text-left py-3 px-4 font-semibold text-text-primary">
                          Estado
                        </th>
                        <th className="text-left py-3 px-4 font-semibold text-text-primary">Fecha</th>
                      </tr>
                    </thead>
                    <tbody>
                      {leads.map((lead) => (
                        <tr key={lead.id} className="border-b hover:bg-surface">
                          <td className="py-3 px-4 text-text-primary">{lead.usuario_nombre}</td>
                          <td className="py-3 px-4 text-text-secondary">{lead.calificacion}/10</td>
                          <td className="py-3 px-4">
                            <span
                              className={`px-2 py-1 rounded text-xs font-medium ${
                                lead.estado === 'calificado'
                                  ? 'bg-success/10 text-success'
                                  : 'bg-warning/10 text-warning'
                              }`}
                            >
                              {lead.estado}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-text-secondary text-sm">
                            {formatDate(lead.created_at)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="citas" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Citas Agendadas</CardTitle>
              <CardDescription>Citas y agendamientos con usuarios</CardDescription>
            </CardHeader>
            <CardContent>
              {citas.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-text-secondary">No hay citas agendadas</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {citas.map((cita) => (
                    <div
                      key={cita.id}
                      className="p-4 border rounded-lg hover:bg-surface/50 transition"
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="font-medium text-text-primary">{cita.usuario_nombre}</h3>
                          <p className="text-sm text-text-secondary">
                            {formatDate(cita.fecha)} a las {cita.hora}
                          </p>
                        </div>
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${
                            cita.estado === 'confirmada'
                              ? 'bg-success/10 text-success'
                              : cita.estado === 'pendiente'
                                ? 'bg-warning/10 text-warning'
                                : 'bg-error/10 text-error'
                          }`}
                        >
                          {cita.estado}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="configuracion" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Información del Cliente</CardTitle>
              <CardDescription>Datos generales del cliente</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-text-secondary">Nombre</p>
                  <p className="text-text-primary font-medium">{cliente.nombre}</p>
                </div>
                <div>
                  <p className="text-sm text-text-secondary">Email</p>
                  <p className="text-text-primary font-medium">{cliente.email}</p>
                </div>
                <div>
                  <p className="text-sm text-text-secondary">ID del Cliente</p>
                  <p className="text-text-primary font-medium font-mono text-sm">{cliente.id}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="flex gap-2">
            <Link href={`/admin/clientes/${clienteId}`}>
              <Button variant="outline">Editar Configuración</Button>
            </Link>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
