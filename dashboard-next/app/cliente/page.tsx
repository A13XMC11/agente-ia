import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { MessageSquare, TrendingUp, Calendar, AlertCircle } from 'lucide-react'
import { getClienteId } from '@/lib/get-user'
import { supabase } from '@/lib/supabase/server'

interface Metrics {
  conversacionesHoy: number
  leadsNuevos: number
  citasProgramadas: number
  alertasPendientes: number
  scorePromedio: number
}

interface Conversacion {
  id: string
  usuario_id: string
  canal: string
  ultimo_mensaje: string
  fecha_ultimo_mensaje: string
}

interface Lead {
  id: string
  nombre: string
  email: string
  telefono: string
  score: number
}

async function getMetrics(clienteId: string): Promise<Metrics> {
  const today = new Date().toISOString().split('T')[0]

  const [
    { count: conversacionesHoy },
    { count: leadsNuevos },
    { count: citasProgramadas },
    { count: alertasPendientes },
    { data: leads }
  ] = await Promise.all([
    supabase
      .from('conversaciones')
      .select('*', { count: 'exact', head: true })
      .eq('cliente_id', clienteId)
      .gte('fecha_inicio', `${today}T00:00:00`),
    supabase
      .from('leads')
      .select('*', { count: 'exact', head: true })
      .eq('cliente_id', clienteId)
      .gte('created_at', `${today}T00:00:00`),
    supabase
      .from('citas')
      .select('*', { count: 'exact', head: true })
      .eq('cliente_id', clienteId)
      .gte('fecha', today),
    supabase
      .from('alertas_log')
      .select('*', { count: 'exact', head: true })
      .eq('cliente_id', clienteId)
      .eq('leida', false),
    supabase
      .from('leads')
      .select('score')
      .eq('cliente_id', clienteId)
  ])

  const scorePromedio = leads && leads.length > 0
    ? Math.round((leads.reduce((sum, l) => sum + (l.score || 0), 0) / leads.length) * 10) / 10
    : 0

  return {
    conversacionesHoy: conversacionesHoy || 0,
    leadsNuevos: leadsNuevos || 0,
    citasProgramadas: citasProgramadas || 0,
    alertasPendientes: alertasPendientes || 0,
    scorePromedio
  }
}

async function getConversacionesRecientes(clienteId: string): Promise<Conversacion[]> {
  const { data } = await supabase
    .from('conversaciones')
    .select('id, usuario_id, canal, ultimo_mensaje, fecha_ultimo_mensaje')
    .eq('cliente_id', clienteId)
    .order('fecha_ultimo_mensaje', { ascending: false })
    .limit(5)

  return data || []
}

async function getTopLeads(clienteId: string): Promise<Lead[]> {
  const { data } = await supabase
    .from('leads')
    .select('id, nombre, email, telefono, score')
    .eq('cliente_id', clienteId)
    .order('score', { ascending: false })
    .limit(5)

  return data || []
}

async function getProximasCitas(clienteId: string): Promise<Conversacion[]> {
  const today = new Date().toISOString().split('T')[0]

  const { data } = await supabase
    .from('citas')
    .select('id, usuario_id:usuario(nombre), canal:null, ultimo_mensaje:descripcion, fecha_ultimo_mensaje:fecha')
    .eq('cliente_id', clienteId)
    .gte('fecha', today)
    .order('fecha', { ascending: true })
    .limit(5)

  return data || []
}

export default async function ClienteDashboard() {
  const clienteId = await getClienteId()

  if (!clienteId) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-4xl font-bold text-text-primary">Dashboard</h1>
          <p className="text-text-secondary mt-2">Resumen de tu negocio y agente IA</p>
        </div>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-12">
              <p className="text-text-secondary">No hay cliente asociado a tu cuenta</p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const [metrics, conversacionesRecientes, topLeads, proximasCitas] = await Promise.all([
    getMetrics(clienteId),
    getConversacionesRecientes(clienteId),
    getTopLeads(clienteId),
    getProximasCitas(clienteId)
  ])

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-bold text-text-primary">Dashboard</h1>
        <p className="text-text-secondary mt-2">Resumen de tu negocio y agente IA</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Chats Hoy</CardTitle>
            <MessageSquare className="h-4 w-4 text-accent" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{metrics.conversacionesHoy}</div>
            <p className="text-xs text-text-secondary mt-1">Conversaciones activas</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Leads</CardTitle>
            <TrendingUp className="h-4 w-4 text-warning" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{metrics.leadsNuevos}</div>
            <p className="text-xs text-text-secondary mt-1">Nuevos hoy</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Citas</CardTitle>
            <Calendar className="h-4 w-4 text-info" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{metrics.citasProgramadas}</div>
            <p className="text-xs text-text-secondary mt-1">Programadas</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Score Promedio</CardTitle>
            <AlertCircle className="h-4 w-4 text-error" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{metrics.scorePromedio}</div>
            <p className="text-xs text-text-secondary mt-1">Leads</p>
          </CardContent>
        </Card>
      </div>

      <div>
        <h2 className="text-2xl font-bold text-text-primary mb-4">Conversaciones Recientes</h2>
        <Card>
          <CardContent className="pt-6">
            {conversacionesRecientes.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-text-secondary">No hay conversaciones aún</p>
                <p className="text-sm text-text-muted mt-2">Las conversaciones aparecerán aquí cuando los usuarios contacten a tu agente</p>
              </div>
            ) : (
              <div className="space-y-2">
                {conversacionesRecientes.map((conv) => (
                  <div key={conv.id} className="p-3 border rounded-lg hover:bg-surface">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-medium text-text-primary">{conv.usuario_id}</p>
                        <p className="text-sm text-text-secondary">{conv.ultimo_mensaje}</p>
                      </div>
                      <span className="text-xs text-text-muted">{conv.canal}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h2 className="text-2xl font-bold text-text-primary mb-4">Top Leads</h2>
          <Card>
            <CardContent className="pt-6">
              {topLeads.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-text-secondary">No hay leads aún</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {topLeads.map((lead) => (
                    <div key={lead.id} className="p-3 border rounded-lg">
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-medium text-text-primary">{lead.nombre}</p>
                          <p className="text-xs text-text-secondary">{lead.email}</p>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          lead.score >= 8 ? 'bg-success/10 text-success' :
                          lead.score >= 5 ? 'bg-warning/10 text-warning' :
                          'bg-error/10 text-error'
                        }`}>
                          {lead.score}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div>
          <h2 className="text-2xl font-bold text-text-primary mb-4">Próximas Citas</h2>
          <Card>
            <CardContent className="pt-6">
              {proximasCitas.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-text-secondary">No hay citas programadas</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {proximasCitas.map((cita) => (
                    <div key={cita.id} className="p-3 border rounded-lg">
                      <p className="font-medium text-text-primary">{cita.ultimo_mensaje}</p>
                      <p className="text-xs text-text-muted">{cita.fecha_ultimo_mensaje}</p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
