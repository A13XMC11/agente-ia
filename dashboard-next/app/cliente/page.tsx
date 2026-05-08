import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { MessageSquare, TrendingUp, Calendar, AlertCircle } from 'lucide-react'

export default function ClienteDashboard() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold text-text-primary">Dashboard</h1>
        <p className="text-text-secondary mt-2">Resumen de tu negocio y agente IA</p>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Chats Hoy</CardTitle>
            <MessageSquare className="h-4 w-4 text-accent" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">0</div>
            <p className="text-xs text-text-secondary mt-1">Conversaciones activas</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Leads</CardTitle>
            <TrendingUp className="h-4 w-4 text-warning" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">0</div>
            <p className="text-xs text-text-secondary mt-1">Nuevos hoy</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Citas</CardTitle>
            <Calendar className="h-4 w-4 text-info" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">0</div>
            <p className="text-xs text-text-secondary mt-1">Programadas</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Alertas</CardTitle>
            <AlertCircle className="h-4 w-4 text-error" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">0</div>
            <p className="text-xs text-text-secondary mt-1">Pendientes</p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Conversations */}
      <div>
        <h2 className="text-2xl font-bold text-text-primary mb-4">Conversaciones Recientes</h2>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-12">
              <p className="text-text-secondary">No hay conversaciones aún</p>
              <p className="text-sm text-text-muted mt-2">Las conversaciones aparecerán aquí cuando los usuarios contacten a tu agente</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Top Leads */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h2 className="text-2xl font-bold text-text-primary mb-4">Top Leads</h2>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center py-12">
                <p className="text-text-secondary">No hay leads aún</p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div>
          <h2 className="text-2xl font-bold text-text-primary mb-4">Próximas Citas</h2>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center py-12">
                <p className="text-text-secondary">No hay citas programadas</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
