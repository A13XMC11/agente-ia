import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { MessageSquare } from 'lucide-react'

export default function ConversacionesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Conversaciones</h1>
        <p className="text-text-secondary mt-2">Monitorea y gestiona todas las conversaciones con tus clientes</p>
      </div>

      <div className="flex gap-2">
        <Input placeholder="Buscar conversación..." className="flex-1" />
        <Button variant="outline">Filtrar</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Conversaciones Activas</CardTitle>
          <CardDescription>Todas las conversaciones en tiempo real</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12">
            <MessageSquare className="h-12 w-12 text-text-muted mb-4" />
            <p className="text-text-secondary">No hay conversaciones aún</p>
            <p className="text-sm text-text-muted mt-2">Las conversaciones aparecerán aquí cuando los usuarios contacten</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
